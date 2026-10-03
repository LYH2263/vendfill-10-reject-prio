from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Lane
from app.services.fill_engine import compute_gap
router = APIRouter(prefix="/lanes", tags=["lanes"])


def lane_to_dict(r: Lane) -> dict:
    gap = compute_gap(r.capacity, r.stock, r.in_transit)
    return {"id": r.id, "location_id": r.location_id, "slot_no": r.slot_no, "sku_name": r.sku_name,
            "capacity": r.capacity, "stock": r.stock, "in_transit": r.in_transit,
            "blocked": r.blocked, "gap": gap,
            "fill_pct": round(r.stock / r.capacity * 100, 1) if r.capacity else 0}


@router.get("")
def list_lanes(location_id: int | None = None, db: Session = Depends(get_db)):
    q = select(Lane).order_by(Lane.slot_no)
    if location_id is not None: q = q.where(Lane.location_id == location_id)
    return [lane_to_dict(r) for r in db.scalars(q).all()]


class LanePatch(BaseModel):
    stock: int | None = None
    in_transit: int | None = None
    # None=未配置封锁（不冒封锁码）；显式 True 才封锁
    blocked: bool | None = None


@router.patch("/{lane_id}")
def update_lane(lane_id: int, patch: LanePatch, db: Session = Depends(get_db)):
    """改货道库存/在途（可改出超占或补满）或开关封锁。

    落库后立刻按新状态重算并持久化该点位补货单，
    使最新单行码、满仓页收录、汇总计数与货道状态同源同步，不留分叉。
    """
    lane = db.get(Lane, lane_id)
    if lane is None:
        raise HTTPException(404, "货道不存在")
    if patch.stock is not None:
        lane.stock = max(0, patch.stock)
    if patch.in_transit is not None:
        lane.in_transit = max(0, patch.in_transit)
    if patch.blocked is not None or "blocked" in patch.model_fields_set:
        lane.blocked = patch.blocked
    db.commit()
    db.refresh(lane)

    # 重算该点位最新补货单（延迟导入避免循环依赖）
    from app.api.refills import rebuild_order
    summary = rebuild_order(db, lane.location_id)
    return {"lane": lane_to_dict(lane), "refill": {"location_id": lane.location_id, **summary}}
