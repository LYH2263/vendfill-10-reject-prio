from app.services.fill_engine import (
    REJECT_BLOCKED,
    REJECT_FULL,
    REJECT_OVERBOOKED,
    build_fill_lines,
    compute_gap,
    resolve_reject_reason,
    summarize,
)


def _lane(id=1, cap=10, stock=0, transit=0, blocked=None, slot="A1", sku="水"):
    return {"id": id, "slot_no": slot, "sku_name": sku, "capacity": cap,
            "stock": stock, "in_transit": transit, "blocked": blocked}


def test_gap_basic():
    assert compute_gap(20, 5, 0) == 15
    assert compute_gap(20, 10, 5) == 5


def test_no_negative_fill():
    lines = build_fill_lines([_lane(cap=10, stock=12)])
    assert lines[0].fill_qty == 0
    assert lines[0].status == REJECT_OVERBOOKED
    assert lines[0].reject_reason == REJECT_OVERBOOKED


def test_cap_by_gap():
    lines = build_fill_lines([_lane(cap=20, stock=5)], requested={1: 100})
    assert lines[0].fill_qty == 15
    assert lines[0].gap == 15
    assert lines[0].reject_reason == ""


def test_full_zero_fill():
    s = summarize(build_fill_lines([_lane(cap=10, stock=8, transit=2)]))
    assert s["full_count"] == 1
    assert s["total_fill"] == 0


# ---------- 互斥拒因：每行至多一个码，正补量行为空 ----------

def test_overbooked_has_only_one_code_and_wins_over_blocked():
    # gap = 10 - 9 - 3 = -2，同时封锁：只能出超占码
    lines = build_fill_lines([_lane(cap=10, stock=9, transit=3, blocked=True)])
    l = lines[0]
    assert l.fill_qty == 0
    assert l.reject_reason == REJECT_OVERBOOKED
    assert l.status == REJECT_OVERBOOKED
    s = summarize(lines)
    assert s["overbooked_count"] == 1
    assert s["blocked_count"] == 0
    assert s["full_count"] == 0


def test_blocked_with_gap_only_emits_blocked():
    # gap = 12 - 3 - 2 = 7 > 0，只封锁不超占：只能出封锁码，且不补
    lines = build_fill_lines([_lane(cap=12, stock=3, transit=2, blocked=True)])
    l = lines[0]
    assert l.fill_qty == 0
    assert l.reject_reason == REJECT_BLOCKED
    assert l.status == REJECT_BLOCKED
    s = summarize(lines)
    assert s["blocked_count"] == 1
    assert s["overbooked_count"] == 0
    assert s["full_count"] == 0
    assert s["need_fill_count"] == 0


def test_blocked_at_zero_gap_wins_over_full():
    # gap = 0 且封锁：封锁优先于满仓，禁止写成已满仓
    lines = build_fill_lines([_lane(cap=10, stock=10, transit=0, blocked=True)])
    assert lines[0].reject_reason == REJECT_BLOCKED
    s = summarize(lines)
    assert s["blocked_count"] == 1 and s["full_count"] == 0


def test_plain_full_emits_full():
    # 不超占、未封锁、缺口为 0：才是满仓
    lines = build_fill_lines([_lane(cap=10, stock=8, transit=2)])
    assert lines[0].reject_reason == REJECT_FULL
    assert lines[0].status == REJECT_FULL


def test_positive_fill_never_has_reason():
    # 即使配了 blocked=False（已配置但未封锁），有缺口就是正常补货，拒因为空
    lines = build_fill_lines([_lane(cap=20, stock=5, blocked=False)])
    l = lines[0]
    assert l.fill_qty > 0
    assert l.reject_reason == ""
    assert l.status == "need_fill"
    s = summarize(lines)
    assert s["need_fill_count"] == 1
    assert s["total_fill"] == 15


def test_unconfigured_blocked_field_never_emits_blocked_code():
    # blocked 缺省 / None / 0 / False 都不得冒出封锁码
    for blocked in (None, 0, False):
        lane = _lane(cap=12, stock=3, transit=2, blocked=blocked)
        if blocked is None:
            lane.pop("blocked") if False else None
        lines = build_fill_lines([lane])
        assert lines[0].reject_reason == "", blocked
        assert lines[0].fill_qty == 7

    # 缺省整个字段（未配置封锁）同样不能命中封锁
    lane = _lane(cap=12, stock=3, transit=2)
    del lane["blocked"]
    assert build_fill_lines([lane])[0].reject_reason == ""


def test_resolve_priority_order():
    assert resolve_reject_reason(-1, True) == REJECT_OVERBOOKED
    assert resolve_reject_reason(0, True) == REJECT_BLOCKED
    assert resolve_reject_reason(0, False) == REJECT_FULL
    assert resolve_reject_reason(0, None) == REJECT_FULL
    assert resolve_reject_reason(5, None) == ""
    assert resolve_reject_reason(5, 1) == REJECT_BLOCKED


def test_counts_are_mutex_and_partition_lines():
    lanes = [
        _lane(id=1, cap=20, stock=5),              # 待补
        _lane(id=2, cap=18, stock=18),             # 满仓
        _lane(id=3, cap=12, stock=3, transit=2, blocked=True),  # 封锁(有缺口)
        _lane(id=4, cap=24, stock=24, transit=2),  # 超占
        _lane(id=5, cap=15, stock=10, transit=5, blocked=True),  # gap0 但封锁→封锁
    ]
    s = summarize(build_fill_lines(lanes))
    assert s["need_fill_count"] == 1
    assert s["full_count"] == 1
    assert s["blocked_count"] == 2
    assert s["overbooked_count"] == 1
    # 互斥：每行恰属于一类，合计等于总行数
    total = s["need_fill_count"] + s["full_count"] + s["blocked_count"] + s["overbooked_count"]
    assert total == len(lanes)
    # 满仓名单不得混入超占/封锁
    full = {l["lane_id"] for l in s["lines"] if l["reject_reason"] == REJECT_FULL}
    assert full == {2}
    assert 4 not in full and 3 not in full and 5 not in full


def test_seed_shapes():
    # 复刻种子：C2 超占（24 容量 / 24 库存 / 2 在途）；B1 只封锁不超占
    seed_lanes = [
        ("A1", 20, 5, 0, None),
        ("A2", 18, 18, 0, None),
        ("B1", 12, 3, 2, True),
        ("B2", 15, 10, 5, None),
        ("C1", 10, 0, 0, None),
        ("C2", 24, 24, 2, None),
    ]
    payload = [_lane(id=i + 1, slot=slot, cap=cap, stock=stock, transit=t, blocked=b)
               for i, (slot, cap, stock, t, b) in enumerate(seed_lanes)]
    lines = build_fill_lines(payload)
    by_slot = {l.slot_no: l for l in lines}
    # C2 超占时只能出超占码
    assert by_slot["C2"].reject_reason == REJECT_OVERBOOKED
    assert by_slot["C2"].fill_qty == 0
    # B1 只封锁不超占 → 只能出封锁码
    assert by_slot["B1"].reject_reason == REJECT_BLOCKED
    # A2/B2 两者都不成立且缺口为 0 → 满仓
    assert by_slot["A2"].reject_reason == REJECT_FULL
    assert by_slot["B2"].reject_reason == REJECT_FULL
    # 满仓页无 C2（也无 B1）
    full_slots = {l.slot_no for l in lines if l.reject_reason == REJECT_FULL}
    assert "C2" not in full_slots
    assert "B1" not in full_slots
    assert full_slots == {"A2", "B2"}
