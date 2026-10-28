from datetime import timedelta
from fastapi import HTTPException, status


class ProjectsService:
    def __init__(self, repo):
        self.repo = repo

    # ---------------- Projects ----------------
    def create_project(self, dto):
        if dto.deadline < dto.start_date:
            raise HTTPException(status_code=400, detail="Deadline must be >= start_date.")

        try:
            project = self.repo.create_project(dto.title.strip(), dto.description, dto.start_date, dto.deadline)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not create project: {str(e)}")

        try:
            self.repo.set_project_resources(project.id, dto.resource_employee_ids)
        except ValueError as e:
            # rollback project if resources invalid
            self.repo.delete_project(project.id)
            raise HTTPException(status_code=400, detail=str(e))

        return project

    def list_projects(self):
        return self.repo.list_projects()

    def get_project(self, project_id: int):
        p = self.repo.get_project(project_id)
        if not p:
            raise HTTPException(status_code=404, detail="Project not found.")
        return p

    def delete_project(self, project_id: int):
        p = self.repo.get_project(project_id)
        if not p:
            raise HTTPException(status_code=404, detail="Project not found.")
        self.repo.delete_project(project_id)

    # ---------------- Tasks ----------------
    def create_task(self, project_id: int, dto):
        _ = self.get_project(project_id)

        # PERT validation (if any estimate present, all must be present)
        any_pert = any(x is not None for x in [dto.optimistic, dto.most_likely, dto.pessimistic])
        all_pert = all(x is not None for x in [dto.optimistic, dto.most_likely, dto.pessimistic])
        if any_pert and not all_pert:
            raise HTTPException(status_code=400, detail="PERT requires optimistic, most_likely, and pessimistic together.")

        try:
            return self.repo.create_task(
                project_id=project_id,
                name=dto.name.strip(),
                description=dto.description,
                duration_days=float(dto.duration_days),
                optimistic=dto.optimistic,
                most_likely=dto.most_likely,
                pessimistic=dto.pessimistic,
                predecessor_task_ids=dto.predecessor_task_ids,
                resource_employee_ids=dto.resource_employee_ids,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not create task: {str(e)}")

    def list_tasks(self, project_id: int):
        _ = self.get_project(project_id)
        return self.repo.list_tasks(project_id)

    def delete_task(self, project_id: int, task_id: int):
        _ = self.get_project(project_id)
        self.repo.delete_task(project_id, task_id)

    # ---------------- Simulation (CPM/PERT) ----------------
    def simulate(self, project_id: int):
        project = self.get_project(project_id)
        tasks = self.repo.list_tasks(project_id)

        if not tasks:
            return {
                "project_id": project_id,
                "project_duration_days": 0,
                "critical_path_task_ids": [],
                "tasks": [],
                "resource_conflicts": {},
                "deadline_days_remaining": (project.deadline - project.start_date).days
            }

        # Build maps
        task_by_id = {t.id: t for t in tasks}

        def expected_duration(t):
            if t.optimistic is not None:
                # PERT expected time
                return (t.optimistic + 4 * t.most_likely + t.pessimistic) / 6.0
            return float(t.duration_days)

        durations = {tid: expected_duration(t) for tid, t in task_by_id.items()}

        # Predecessor graph
        preds = {t.id: [p.id for p in (t.predecessors or [])] for t in tasks}

        # Kahn topological sort + cycle detection
        indeg = {tid: 0 for tid in task_by_id}
        succ = {tid: [] for tid in task_by_id}
        for tid, pids in preds.items():
            for pid in pids:
                if pid not in task_by_id:
                    raise HTTPException(status_code=400, detail=f"Invalid predecessor id {pid} in task {tid}.")
                indeg[tid] += 1
                succ[pid].append(tid)

        q = [tid for tid in indeg if indeg[tid] == 0]
        topo = []
        while q:
            n = q.pop(0)
            topo.append(n)
            for s in succ[n]:
                indeg[s] -= 1
                if indeg[s] == 0:
                    q.append(s)

        if len(topo) != len(task_by_id):
            raise HTTPException(status_code=400, detail="Cycle detected in task predecessors. CPM/PERT requires a DAG.")

        # Forward pass
        ES, EF = {}, {}
        for tid in topo:
            if not preds[tid]:
                ES[tid] = 0.0
            else:
                ES[tid] = max(EF[pid] for pid in preds[tid])
            EF[tid] = ES[tid] + durations[tid]

        project_duration = max(EF.values())

        # Backward pass
        LF, LS = {}, {}
        for tid in reversed(topo):
            if not succ[tid]:
                LF[tid] = project_duration
            else:
                LF[tid] = min(LS[sid] for sid in succ[tid])
            LS[tid] = LF[tid] - durations[tid]

        total_float = {tid: round(LS[tid] - ES[tid], 6) for tid in task_by_id}
        critical_tasks = [tid for tid, fl in total_float.items() if abs(fl) < 1e-6]

        # Build critical path (simple: follow successors among critical tasks by earliest finish)
        critical_path = []
        start_crit = [tid for tid in critical_tasks if not preds[tid]]
        if start_crit:
            cur = min(start_crit, key=lambda x: ES[x])
            critical_path.append(cur)
            while True:
                nxt = [s for s in succ[cur] if s in critical_tasks and abs(ES[s] - EF[cur]) < 1e-6]
                if not nxt:
                    break
                cur = min(nxt, key=lambda x: ES[x])
                critical_path.append(cur)

        # Timeline dates from project.start_date
        def to_date(offset_days: float):
            return (project.start_date + timedelta(days=float(offset_days))).isoformat()

        # Resource conflict check (based on ES/EF schedule)
        resource_intervals = {}  # employee_id -> [(tid, start, end)]
        for t in tasks:
            tid = t.id
            for emp in (t.resources or []):
                resource_intervals.setdefault(emp.employee_id, []).append((tid, ES[tid], EF[tid]))

        conflicts = {}
        for emp_id, intervals in resource_intervals.items():
            intervals.sort(key=lambda x: x[1])
            emp_conf = []
            for i in range(len(intervals)):
                for j in range(i + 1, len(intervals)):
                    a = intervals[i]
                    b = intervals[j]
                    # if b starts after a ends, no more overlaps (since sorted)
                    if b[1] >= a[2]:
                        break
                    overlap = min(a[2], b[2]) - max(a[1], b[1])
                    if overlap > 0:
                        emp_conf.append({
                            "task_a": a[0],
                            "task_b": b[0],
                            "overlap_days": overlap
                        })
            if emp_conf:
                conflicts[emp_id] = emp_conf

        # Output tasks schedule
        task_outputs = []
        for t in tasks:
            tid = t.id
            task_outputs.append({
                "id": tid,
                "name": t.name,
                "expected_duration_days": durations[tid],
                "ES": ES[tid],
                "EF": EF[tid],
                "LS": LS[tid],
                "LF": LF[tid],
                "float": total_float[tid],
                "planned_start": to_date(ES[tid]),
                "planned_end": to_date(EF[tid]),
                "predecessor_task_ids": preds[tid],
                "resource_employee_ids": [e.employee_id for e in (t.resources or [])],
            })

        # Deadline comparison
        available_days = (project.deadline - project.start_date).days
        deadline_remaining = available_days - project_duration

        return {
            "project_id": project_id,
            "project_duration_days": project_duration,
            "critical_path_task_ids": critical_path,
            "tasks": sorted(task_outputs, key=lambda x: x["ES"]),
            "resource_conflicts": conflicts,
            "deadline_days_remaining": deadline_remaining,
        }