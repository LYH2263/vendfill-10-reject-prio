import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Lane, Location, RefillOrder
from app.services.fill_engine import (
    REJECT_FULL,
    build_fill_lines,
    summarize,
)
router = APIRouter(prefix="/refills", tags=["refills"])

# 单据快照结构版本：含统一拒因码 reject_reason / blocked_count / reject_counts。
# 历史快照版本不符时按当前码规则重建，避免旧名单与新码分叉。
SNAPSHOT_VERSION = 2


def load_lane_payload(db: Session, location_id: int) -> list[dict]:
    """从货道当前状态构造引擎入参，blocked 原样透传（None=未配置封锁）。"""
    lanes = db.scalars(
        select(Lane).where(Lane.location_id == location_id).order_by(Lane.slot_no)
    ).all()
    return [
        {"id": l.id, "slot_no": l.slot_no, "sku_name": l.sku_name,
         "capacity": l.capacity, "stock": l.stock, "in_transit": l.in_transit,
         "blocked": l.blocked}
        for l in lanes
    ]


def build_summary(db: Session, location_id: int) -> dict:
    """以货道当前状态 + 同一套拒因码生成汇总（行、满仓、汇总的唯一数据源）。"""
    summary = summarize(build_fill_lines(load_lane_payload(db, location_id)))
    summary["code_version"] = SNAPSHOT_VERSION
    return summary


def rebuild_order(db: Session, location_id: int) -> dict:
    """按货道当前状态重算并落一份最新单据，返回汇总。

    货道页改出超占 / 打开封锁后调用，保证“最新单行码”立即是新码。
    """
    summary = build_summary(db, location_id)
    order = RefillOrder(location_id=location_id, created_at=datetime.utcnow(),
                        lines_json=json.dumps(summary, ensure_ascii=False))
    db.add(order)
    db.commit()
    return summary


def _latest_order(db: Session, location_id: int) -> RefillOrder | None:
    return db.scalars(
        select(RefillOrder).where(RefillOrder.location_id == location_id)
        .order_by(RefillOrder.id.desc())
    ).first()


def get_latest_summary(db: Session, location_id: int) -> dict:
    """取最新单据快照；无单据或快照结构过旧时按当前码重建。"""
    order = _latest_order(db, location_id)
    if order is None:
        return rebuild_order(db, location_id)
    data = json.loads(order.lines_json)
    if data.get("code_version") != SNAPSHOT_VERSION:
        return rebuild_order(db, location_id)
    return data


@router.post("/run")
def run_refill(location_id: int = 1, db: Session = Depends(get_db)):
    loc = db.get(Location, location_id)
    if not loc: raise HTTPException(404, "点位不存在")
    summary = rebuild_order(db, location_id)
    return {"id": _latest_order(db, location_id).id, "location_id": location_id, **summary}


@router.get("/latest")
def latest(location_id: int = 1, db: Session = Depends(get_db)):
    loc = db.get(Location, location_id)
    if not loc: raise HTTPException(404, "点位不存在")
    data = get_latest_summary(db, location_id)
    order = _latest_order(db, location_id)  # get_latest_summary 无单时已补建
    return {"id": order.id, "location_id": location_id, **data}


@router.get("/full")
def full_lanes(location_id: int = 1, db: Session = Depends(get_db)):
    data = get_latest_summary(db, location_id)
    # 满仓页只收录“已满仓”码；超占 / 封锁即使补量为 0 也不得混入。
    return {"location_id": location_id,
            "lanes": [l for l in data["lines"] if l["reject_reason"] == REJECT_FULL]}


@router.get("/summary")
def refill_summary(location_id: int = 1, db: Session = Depends(get_db)):
    data = get_latest_summary(db, location_id)
    # 计数与行内 reject_reason 同源，三类互斥不重叠。
    return {
        "location_id": location_id,
        "total_fill": data["total_fill"],
        "need_fill_count": data["need_fill_count"],
        "full_count": data["full_count"],
        "overbooked_count": data["overbooked_count"],
        "blocked_count": data["blocked_count"],
        "reject_counts": data["reject_counts"],
    }
