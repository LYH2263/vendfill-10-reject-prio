from app.services.fill_engine import (
    REJECT_BLOCKED,
    REJECT_FULL,
    REJECT_NONE,
    REJECT_OVERBOOKED,
    build_fill_lines,
    compute_gap,
    resolve_reject,
    summarize,
)


def _lane(id=1, cap=10, stock=0, transit=0, blocked=None):
    lane = {"id": id, "slot_no": "A1", "sku_name": "水",
            "capacity": cap, "stock": stock, "in_transit": transit}
    if blocked is not None:
        lane["blocked"] = blocked
    return lane


def test_gap_basic():
    assert compute_gap(20, 5, 0) == 15
    assert compute_gap(20, 10, 5) == 5


def test_no_negative_fill():
    lines = build_fill_lines([_lane(cap=10, stock=12)])
    assert lines[0].fill_qty == 0
    assert lines[0].status == "overbooked"
    assert lines[0].reject_code == REJECT_OVERBOOKED


def test_cap_by_gap():
    lines = build_fill_lines([_lane(cap=20, stock=5)], requested={1: 100})
    assert lines[0].fill_qty == 15
    assert lines[0].gap == 15
    assert lines[0].reject_code == REJECT_NONE


def test_full_zero_fill():
    s = summarize(build_fill_lines([_lane(cap=10, stock=8, transit=2)]))
    assert s["full_count"] == 1
    assert s["blocked_count"] == 0
    assert s["overbooked_count"] == 0
    assert s["total_fill"] == 0


def test_positive_fill_reject_code_is_empty():
    """正补量行拒因必须为空，即使显式带 blocked 也不参与（blocked 行补量为 0 走封锁码）。"""
    line = build_fill_lines([_lane(cap=10, stock=4, blocked=False)])[0]
    assert line.fill_qty > 0
    assert line.reject_code == REJECT_NONE
    assert line.status == "need_fill"


def test_blocked_only_gap_zero_is_blocked_not_full():
    """缺口为 0 且被封锁：只能出封锁码，不得写成满仓。"""
    line = build_fill_lines([_lane(cap=10, stock=8, transit=2, blocked=True)])[0]
    assert line.fill_qty == 0
    assert line.reject_code == REJECT_BLOCKED
    assert line.status == "blocked"
    s = summarize(build_fill_lines([_lane(cap=10, stock=8, transit=2, blocked=True)]))
    assert s["blocked_count"] == 1
    assert s["full_count"] == 0


def test_blocked_with_positive_gap_still_blocked():
    """有缺口但被封锁：补量仍为 0，只记封锁码，不并写满仓/超占。"""
    line = build_fill_lines([_lane(cap=10, stock=3, blocked=True)])[0]
    assert line.gap == 7
    assert line.fill_qty == 0
    assert line.reject_code == REJECT_BLOCKED


def test_overbooked_takes_priority_over_blocked():
    """既超占又封锁：优先判定超占，只能出超占码。"""
    line = build_fill_lines([_lane(cap=10, stock=9, transit=2, blocked=True)])[0]
    assert line.gap == -1
    assert line.fill_qty == 0
    assert line.reject_code == REJECT_OVERBOOKED


def test_resolve_reject_priority_order():
    assert resolve_reject(-1, blocked=True) == REJECT_OVERBOOKED
    assert resolve_reject(-1, blocked=False) == REJECT_OVERBOOKED
    assert resolve_reject(0, blocked=True) == REJECT_BLOCKED
    assert resolve_reject(5, blocked=True) == REJECT_BLOCKED
    assert resolve_reject(0, blocked=False) == REJECT_FULL


def test_missing_blocked_field_never_emits_blocked_code():
    """未配置封锁字段（payload 无 blocked 键）的点位不得冒出封锁码。"""
    lines = build_fill_lines([_lane(cap=10, stock=8, transit=2)])  # 不传 blocked
    assert lines[0].reject_code == REJECT_FULL
    assert summarize(lines)["blocked_count"] == 0


def test_each_zero_line_has_exactly_one_code_and_counters_partition():
    """混合场景：每行至多一个拒因码；三类计数 + 待补 = 总行数，名单不与码分叉。"""
    lanes = [
        _lane(id=1, cap=20, stock=5),                       # 待补
        _lane(id=2, cap=10, stock=8, transit=2),            # 满仓
        _lane(id=3, cap=10, stock=8, transit=2, blocked=True),  # 封锁压满仓
        _lane(id=4, cap=10, stock=9, transit=2),            # 超占
        _lane(id=5, cap=10, stock=9, transit=2, blocked=True),  # 超占压封锁
    ]
    lines = build_fill_lines(lanes)
    codes = [l.reject_code for l in lines]
    assert codes == [
        REJECT_NONE, REJECT_FULL, REJECT_BLOCKED, REJECT_OVERBOOKED, REJECT_OVERBOOKED,
    ]
    # 零补量行有且仅有一个互斥码
    for l in lines:
        if l.fill_qty == 0:
            assert l.reject_code in (REJECT_OVERBOOKED, REJECT_BLOCKED, REJECT_FULL)
        else:
            assert l.reject_code == REJECT_NONE
    s = summarize(lines)
    assert (s["need_fill_count"] + s["full_count"] + s["blocked_count"]
            + s["overbooked_count"]) == len(lines)
    assert s["full_count"] == 1
    assert s["blocked_count"] == 1
    assert s["overbooked_count"] == 2


def test_seed_scenarios_c2_overbooked_and_d1_blocked_and_a2_full():
    """种子三类代表：C2 超占只出超占码；D1 只封锁不超占出封锁码；A2 缺口 0 不封锁才满仓。"""
    seed_lanes = [
        {"id": 1, "slot_no": "A1", "sku_name": "矿泉水", "capacity": 20, "stock": 5, "in_transit": 0, "blocked": False},
        {"id": 2, "slot_no": "A2", "sku_name": "可乐", "capacity": 18, "stock": 18, "in_transit": 0, "blocked": False},
        {"id": 3, "slot_no": "B1", "sku_name": "薯片", "capacity": 12, "stock": 3, "in_transit": 2, "blocked": False},
        {"id": 4, "slot_no": "B2", "sku_name": "巧克力", "capacity": 15, "stock": 10, "in_transit": 5, "blocked": False},
        {"id": 5, "slot_no": "C1", "sku_name": "能量棒", "capacity": 10, "stock": 0, "in_transit": 0, "blocked": False},
        {"id": 6, "slot_no": "C2", "sku_name": "口香糖", "capacity": 24, "stock": 24, "in_transit": 2, "blocked": False},
        {"id": 7, "slot_no": "D1", "sku_name": "坚果", "capacity": 16, "stock": 16, "in_transit": 0, "blocked": True},
    ]
    by_slot = {l.slot_no: l for l in build_fill_lines(seed_lanes)}
    # C2 超占：只出超占码，且不进满仓名单
    assert by_slot["C2"].reject_code == REJECT_OVERBOOKED
    assert by_slot["C2"].fill_qty == 0
    full_slots = {l.slot_no for l in build_fill_lines(seed_lanes) if l.reject_code == REJECT_FULL}
    assert "C2" not in full_slots
    # D1 只封锁不超占：只出封锁码，既不满仓也不超占
    assert by_slot["D1"].reject_code == REJECT_BLOCKED
    assert "D1" not in full_slots
    # A2 两者都不成立且缺口为 0：才是满仓
    assert by_slot["A2"].reject_code == REJECT_FULL
    assert "A2" in full_slots
