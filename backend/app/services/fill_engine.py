"""Vending refill: gap = capacity - stock - in_transit; fills capped by gap; no negative fills.

补量为 0 的行只允许命中一个互斥拒因码，优先级固定：
超占(overbooked) > 封锁(blocked) > 满仓(full)；正补量行拒因必须为空。
单行、满仓页、汇总附注共用这一套码，禁止分叉、禁止并写两码。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

# 互斥拒因码：补货单行、满仓页、汇总必须共用同一套
REJECT_OVERBOOKED = "overbooked"  # 超占不可补（缺口为负）
REJECT_BLOCKED = "blocked"        # 货道封锁（点位已配置封锁字段且该道被封锁）
REJECT_FULL = "full"              # 已满仓（缺口为 0）
REJECT_NONE = ""                  # 正补量行：无拒因

REJECT_LABELS: dict[str, str] = {
    REJECT_OVERBOOKED: "超占不可补",
    REJECT_BLOCKED: "货道封锁",
    REJECT_FULL: "已满仓",
}

# 零补量行的唯一判定顺序：先超占，再封锁，最后才是缺口为 0 的满仓
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
    status: str  # need_fill | full | overbooked | blocked
    reject_code: str  # 零补量时为 REJECT_PRIORITY 中唯一一码；正补量时为 REJECT_NONE


def compute_gap(capacity: int, stock: int, in_transit: int) -> int:
    return capacity - stock - in_transit


def resolve_reject(gap: int, blocked: bool) -> str:
    """零补量行的互斥判定。同一行只返回一码：超占 > 封锁 > 满仓。"""
    if gap < 0:
        return REJECT_OVERBOOKED
    if blocked:
        return REJECT_BLOCKED
    return REJECT_FULL


def build_fill_lines(lanes: list[dict], requested: dict[int, int] | None = None) -> list[FillLine]:
    """requested optional desired fill per lane_id; capped by gap; never negative.

    lane 可带 "blocked" 键；未配置封锁字段（键缺失或为 None）的点位一律视为未封锁，
    不得冒出封锁码。
    """
    lines: list[FillLine] = []
    for lane in lanes:
        gap = compute_gap(int(lane["capacity"]), int(lane["stock"]), int(lane["in_transit"]))
        blocked_raw = lane.get("blocked")
        blocked = bool(blocked_raw) if blocked_raw is not None else False
        if gap < 0:
            # 超占优先：即使被封锁也只记超占码
            reject_code = REJECT_OVERBOOKED
            fill = 0
        elif blocked:
            # 其次封锁：缺口为 0 或正都不可补，但不得写成满仓
            reject_code = REJECT_BLOCKED
            fill = 0
        elif gap == 0:
            reject_code = REJECT_FULL
            fill = 0
        else:
            reject_code = REJECT_NONE
            desire = gap if requested is None else int(requested.get(lane["id"], gap))
            fill = max(0, min(desire, gap))
        lines.append(FillLine(
            lane_id=lane["id"], slot_no=lane["slot_no"], sku_name=lane["sku_name"],
            capacity=lane["capacity"], stock=lane["stock"], in_transit=lane["in_transit"],
            gap=gap, fill_qty=fill, status=reject_code or "need_fill",
            reject_code=reject_code,
        ))
    return lines


def summarize(lines: list[FillLine]) -> dict:
    return {
        "total_fill": sum(l.fill_qty for l in lines),
        "need_fill_count": sum(1 for l in lines if l.reject_code == REJECT_NONE),
        "full_count": sum(1 for l in lines if l.reject_code == REJECT_FULL),
        "blocked_count": sum(1 for l in lines if l.reject_code == REJECT_BLOCKED),
        "overbooked_count": sum(1 for l in lines if l.reject_code == REJECT_OVERBOOKED),
        "lines": [asdict(l) for l in lines],
    }
