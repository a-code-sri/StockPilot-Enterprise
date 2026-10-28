from statistics import median
from typing import List, Dict, Any


class OrganizationAnalyticsService:
    def __init__(self, repo):
        self.repo = repo

    def _histogram(self, values: List[float], bins: int = 10) -> Dict[str, Any]:
        if not values:
            return {
                "bins": [],
                "counts": [],
                "min": None,
                "max": None,
                "avg": None,
                "median": None,
            }

        vmin = min(values)
        vmax = max(values)
        avg = sum(values) / len(values)
        med = median(values)

        # Edge case: all salaries same
        if vmin == vmax:
            return {
                "bins": [vmin, vmax],
                "counts": [len(values)],
                "min": vmin,
                "max": vmax,
                "avg": round(avg, 2),
                "median": round(med, 2),
            }

        bins = max(1, int(bins))
        width = (vmax - vmin) / bins

        edges = [vmin + i * width for i in range(bins + 1)]
        counts = [0] * bins

        for x in values:
            idx = int((x - vmin) / width)
            if idx == bins:  # include max in last bin
                idx = bins - 1
            counts[idx] += 1

        # Round edges for cleaner UI display
        edges_rounded = [round(e, 2) for e in edges]

        return {
            "bins": edges_rounded,   # length bins+1
            "counts": counts,        # length bins
            "min": round(vmin, 2),
            "max": round(vmax, 2),
            "avg": round(avg, 2),
            "median": round(med, 2),
        }

    def overview(self, histogram_bins: int = 10):
        dept_counts = self.repo.department_headcount()
        total_employees = sum(x["headcount"] for x in dept_counts) or 0

        dept_share = []
        for x in dept_counts:
            percent = (x["headcount"] / total_employees * 100.0) if total_employees else 0.0
            dept_share.append({
                "department": x["department"],
                "headcount": x["headcount"],
                "percent": round(percent, 2),
            })

        salaries = self.repo.get_all_salaries()
        salary_hist = self._histogram(salaries, bins=histogram_bins)

        top_exec = self.repo.get_top_executive()
        top_exec_payload = None
        if top_exec:
            top_exec_payload = {
                "employee_id": top_exec.employee_id,
                "name": top_exec.name,
                "salary": float(top_exec.salary),
                "job_role": top_exec.job_role,
                "departments": [d.name for d in (top_exec.departments or [])],
            }

        return {
            "department_share": dept_share,              # for pie chart
            "salary_histogram": salary_hist,             # for histogram chart
            "top_executive": top_exec_payload,           # for dashboard card
            "total_employees": total_employees,
        }