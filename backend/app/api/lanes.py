from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Lane
from app.services.fill_engine import compute_gap
router = APIRouter(prefix="/lanes", tags=["lanes"])


def lane_out(r: Lane) -> dict:
    gap = compute_gap(r.capacity, r.stock, r.in_transit)
    return {"id": r.id, "location_id": r.location_id, "slot_no": r.slot_no, "sku_name": r.sku_name,
            "capacity": r.capacity, "stock": r.stock, "in_transit": r.in_transit, "gap": gap,
            "blocked": bool(r.blocked),
            "fill_pct": round(r.stock / r.capacity * 100, 1) if r.capacity else 0}


@router.get("")
def list_lanes(location_id: int | None = None, db: Session = Depends(get_db)):
    q = select(Lane).order_by(Lane.slot_no)
    if location_id is not None: q = q.where(Lane.location_id == location_id)
    return [lane_out(r) for r in db.scalars(q).all()]


class LanePatch(BaseModel):
    blocked: bool | None = None
    stock: int | None = None
    in_transit: int | None = None


@router.patch("/{lane_id}")
def patch_lane(lane_id: int, body: LanePatch, db: Session = Depends(get_db)):
    lane = db.get(Lane, lane_id)
    if not lane:
        raise HTTPException(404, "货道不存在")
    if body.blocked is not None:
        lane.blocked = body.blocked
    if body.stock is not None:
        if body.stock < 0:
            raise HTTPException(400, "库存不可为负")
        lane.stock = body.stock
    if body.in_transit is not None:
        if body.in_transit < 0:
            raise HTTPException(400, "在途不可为负")
        lane.in_transit = body.in_transit
    db.commit(); db.refresh(lane)
    return lane_out(lane)
