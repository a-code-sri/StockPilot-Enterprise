import pytest

from backend.modules.projects.domain.scheduling import (
    CycleError,
    TaskInput,
    compute_schedule,
    expected_duration,
    resource_conflicts,
)


def T(id, d, preds=(), res=(), pert=None):
    o, m, p = pert or (None, None, None)
    return TaskInput(id=id, name=f"t{id}", duration_days=d, optimistic=o, most_likely=m, pessimistic=p,
                     predecessor_ids=tuple(preds), resource_ids=tuple(res))


def test_empty_project():
    s = compute_schedule([])
    assert s.duration_days == 0 and s.critical_path == []


def test_chain_and_parallel_branch():
    # 1 -> 2 -> 4 (3 + 5 + 2 = 10) and 1 -> 3 -> 4 (3 + 1 + 2 = 6)
    tasks = [T(1, 3), T(2, 5, [1]), T(3, 1, [1]), T(4, 2, [2, 3])]
    s = compute_schedule(tasks)
    assert s.duration_days == 10
    assert s.critical_path == [1, 2, 4]
    assert s.tasks[3]["float"] == 4
    assert s.tasks[4]["ES"] == 8


def test_pert_expected_duration():
    t = T(1, 99, pert=(2, 4, 12))
    assert expected_duration(t) == pytest.approx((2 + 16 + 12) / 6)
    s = compute_schedule([t])
    assert s.duration_days == pytest.approx(5.0)
    assert s.std_dev_days == pytest.approx(10 / 6)


def test_cycle_detected():
    with pytest.raises(CycleError):
        compute_schedule([T(1, 1, [2]), T(2, 1, [1])])


def test_unknown_predecessor():
    with pytest.raises(ValueError):
        compute_schedule([T(1, 1, [99])])


def test_resource_conflicts_only_for_overlaps():
    tasks = [T(1, 4, res=["E1"]), T(2, 2, res=["E1"]), T(3, 1, [1], res=["E1"])]
    s = compute_schedule(tasks)
    conflicts = resource_conflicts(tasks, s)
    assert conflicts == {"E1": [{"task_a": 1, "task_b": 2, "overlap_days": 2}]}
