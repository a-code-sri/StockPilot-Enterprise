"""
CPM / PERT scheduling, as pure functions (no database), shared by the
simulation endpoint and the analytics snapshots.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional

EPS = 1e-6


@dataclass(frozen=True)
class TaskInput:
    id: int
    name: str
    duration_days: float
    optimistic: Optional[float] = None
    most_likely: Optional[float] = None
    pessimistic: Optional[float] = None
    predecessor_ids: tuple[int, ...] = ()
    resource_ids: tuple[str, ...] = ()


def expected_duration(t: TaskInput) -> float:
    """PERT expected time (o + 4m + p) / 6 when all three estimates exist, else duration_days."""
    if t.optimistic is not None and t.most_likely is not None and t.pessimistic is not None:
        return (t.optimistic + 4 * t.most_likely + t.pessimistic) / 6.0
    return float(t.duration_days)


def pert_std_dev(t: TaskInput) -> float:
    if t.optimistic is not None and t.pessimistic is not None:
        return (t.pessimistic - t.optimistic) / 6.0
    return 0.0


class CycleError(ValueError):
    pass


@dataclass
class Schedule:
    duration_days: float
    critical_path: list[int]
    tasks: dict[int, dict] = field(default_factory=dict)  # id -> ES/EF/LS/LF/float/duration
    std_dev_days: float = 0.0  # PERT std dev along the critical path


def topological_order(tasks: dict[int, TaskInput]) -> list[int]:
    indeg = {tid: 0 for tid in tasks}
    succ: dict[int, list[int]] = {tid: [] for tid in tasks}
    for t in tasks.values():
        for p in t.predecessor_ids:
            if p not in tasks:
                raise ValueError(f"Task {t.id} has unknown predecessor {p}")
            indeg[t.id] += 1
            succ[p].append(t.id)

    queue = sorted(tid for tid, d in indeg.items() if d == 0)
    order = []
    while queue:
        n = queue.pop(0)
        order.append(n)
        for s in sorted(succ[n]):
            indeg[s] -= 1
            if indeg[s] == 0:
                queue.append(s)

    if len(order) != len(tasks):
        raise CycleError("Cycle detected in task predecessors. CPM/PERT requires a DAG.")
    return order


def compute_schedule(task_list: Iterable[TaskInput]) -> Schedule:
    tasks = {t.id: t for t in task_list}
    if not tasks:
        return Schedule(duration_days=0.0, critical_path=[])

    order = topological_order(tasks)
    dur = {tid: expected_duration(t) for tid, t in tasks.items()}
    succ: dict[int, list[int]] = {tid: [] for tid in tasks}
    for t in tasks.values():
        for p in t.predecessor_ids:
            succ[p].append(t.id)

    es, ef = {}, {}
    for tid in order:
        es[tid] = max((ef[p] for p in tasks[tid].predecessor_ids), default=0.0)
        ef[tid] = es[tid] + dur[tid]
    project = max(ef.values())

    lf, ls = {}, {}
    for tid in reversed(order):
        lf[tid] = min((ls[s] for s in succ[tid]), default=project)
        ls[tid] = lf[tid] - dur[tid]

    slack = {tid: round(ls[tid] - es[tid], 6) for tid in tasks}
    critical = {tid for tid, s in slack.items() if abs(s) < EPS}

    # Walk one critical chain from a critical start task to a critical end task.
    path: list[int] = []
    starts = sorted((tid for tid in critical if not tasks[tid].predecessor_ids), key=lambda x: (es[x], x))
    if starts:
        cur = starts[0]
        path.append(cur)
        while True:
            nxt = sorted(
                (s for s in succ[cur] if s in critical and abs(es[s] - ef[cur]) < EPS), key=lambda x: (es[x], x)
            )
            if not nxt:
                break
            cur = nxt[0]
            path.append(cur)

    variance = sum(pert_std_dev(tasks[t]) ** 2 for t in path)

    return Schedule(
        duration_days=project,
        critical_path=path,
        tasks={
            tid: {"duration": dur[tid], "ES": es[tid], "EF": ef[tid], "LS": ls[tid], "LF": lf[tid], "float": slack[tid]}
            for tid in tasks
        },
        std_dev_days=variance ** 0.5,
    )


def resource_conflicts(tasks: Iterable[TaskInput], schedule: Schedule) -> dict[str, list[dict]]:
    """Employees assigned to tasks whose planned [ES, EF) intervals overlap."""
    intervals: dict[str, list[tuple[int, float, float]]] = {}
    for t in tasks:
        s = schedule.tasks[t.id]
        for emp in t.resource_ids:
            intervals.setdefault(emp, []).append((t.id, s["ES"], s["EF"]))

    conflicts: dict[str, list[dict]] = {}
    for emp, items in intervals.items():
        items.sort(key=lambda x: x[1])
        found = []
        for i, a in enumerate(items):
            for b in items[i + 1:]:
                if b[1] >= a[2]:
                    break
                overlap = min(a[2], b[2]) - max(a[1], b[1])
                if overlap > EPS:
                    found.append({"task_a": a[0], "task_b": b[0], "overlap_days": round(overlap, 4)})
        if found:
            conflicts[emp] = found
    return conflicts
