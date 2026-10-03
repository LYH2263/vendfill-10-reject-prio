"""Vending refill: gap = capacity - stock - in_transit; fills capped by gap; no negative fills.

零补量行的拒因在全系统内共用同一套互斥码（REJECT_*），优先级固定：
超占 > 封锁 > 满仓。同一行至多命中一个码；正补量行拒因恒为空。
补货行、满仓页收录、汇总计数都必须以 resolve_reject_reason 的结果为唯一来源，
禁止任何页面/名单自行另写一套判断而与该码分叉。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

# 三种互斥拒因码（零补量行三选一；正补量行为空串）
REJECT_OVERBOOKED = "overbooked"  # 超占不可补：缺口 < 0（库存 + 在途已超容量）
REJECT_BLOCKED = "blocked"        # 货道封锁：封锁字段显式为真（未配置/为空不得命中）
REJECT_FULL = "full"              # 已满仓：不超占、未封锁，但缺口为 0

REJECT_REASONS = (REJECT_OVERBOOKED, REJECT_BLOCKED, REJECT_FULL)

# 优先级：超占最先判定，其次封锁，最后才是缺口为 0 的满仓
REJECT_PRIORITY = (REJECT_OVERBOOKED, REJECT_BLOCKED, REJECT_FULL)


@dataclass
class FillLine:
    lane_id: int
    slot_no: str
    sku_name: str
    capacity: int
    stock: int
    in_transit: int
    gap: int
    fill_qty: int
    status: str  # need_fill | overbooked | blocked | full
    reject_reason: str  # ""（正补量）| overbooked | blocked | full，互斥三选一


def compute_gap(capacity: int, stock: int, in_transit: int) -> int:
    return capacity - stock - in_transit


def resolve_reject_reason(gap: int, blocked: bool | int | None) -> str:
    """零补量行拒因的唯一判定入口。

    优先级：超占（gap<0） > 封锁（blocked 显式为真） > 满仓（gap==0）。
    blocked 仅在显式为真时成立——None/0/假值都不算封锁，
    因此“未配置封锁字段”的点位绝不会冒出 blocked 码。
    """
    if gap < 0:
        return REJECT_OVERBOOKED
    if blocked is True or blocked == 1:
        return REJECT_BLOCKED
    if gap == 0:
        return REJECT_FULL
    return ""


def build_fill_lines(
    lanes: list[dict],
    requested: dict[int, int] | None = None,
) -> list[FillLine]:
    """requested optional desired fill per lane_id; capped by gap; never negative.

    lane 可携带 blocked 字段；缺省（未配置）按未封锁处理。
    """
    lines: list[FillLine] = []
    for lane in lanes:
        gap = compute_gap(int(lane["capacity"]), int(lane["stock"]), int(lane["in_transit"]))
        blocked = lane.get("blocked")
        reason = resolve_reject_reason(gap, blocked)
        if reason:
            # 超占 / 封锁 / 满仓 一律不补
            fill = 0
            status = reason
        else:
            desire = gap if requested is None else int(requested.get(lane["id"], gap))
            fill = max(0, min(desire, gap))
            status = "need_fill"
        lines.append(
            FillLine(
                lane_id=lane["id"], slot_no=lane["slot_no"], sku_name=lane["sku_name"],
                capacity=lane["capacity"], stock=lane["stock"], in_transit=lane["in_transit"],
                gap=gap, fill_qty=fill, status=status, reject_reason=reason,
            )
        )
    return lines


def summarize(lines: list[FillLine]) -> dict:
    """所有计数都以同一拒因码为准，互斥不重叠。"""
    reject_counts = {reason: 0 for reason in REJECT_PRIORITY}
    need_fill_count = 0
    for line in lines:
        if line.reject_reason:
            reject_counts[line.reject_reason] += 1
        else:
            need_fill_count += 1
    return {
        "total_fill": sum(l.fill_qty for l in lines),
        "need_fill_count": need_fill_count,
        "full_count": reject_counts[REJECT_FULL],
        "overbooked_count": reject_counts[REJECT_OVERBOOKED],
        "blocked_count": reject_counts[REJECT_BLOCKED],
        "reject_counts": dict(reject_counts),
        "lines": [asdict(l) for l in lines],
    }
