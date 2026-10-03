"""API 层一致性：补货行码、满仓收录、汇总计数必须同源，并随货道改动联动。"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.services.seed import seed_if_empty


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Session = sessionmaker(bind=engine, autoflush=False)
    Base.metadata.create_all(engine)
    db = Session()
    seed_if_empty(db)
    db.close()

    def override_get_db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    # 不进入 with：跳过连真实 Postgres 的 lifespan（建表/补列由本夹具完成）
    yield TestClient(app)
    app.dependency_overrides.clear()


def _by_slot(lines):
    return {l["slot_no"]: l for l in lines}


def test_seed_full_page_excludes_overbooked_and_blocked(client):
    r = client.get("/api/refills/full?location_id=1")
    assert r.status_code == 200
    slots = {l["slot_no"] for l in r.json()["lanes"]}
    # 只有纯满仓 A2/B2；C2 超占、B1 封锁都不得进入满仓页
    assert slots == {"A2", "B2"}


def test_seed_summary_counts_match_same_codes(client):
    s = client.get("/api/refills/summary?location_id=1").json()
    assert s["need_fill_count"] == 2   # A1, C1
    assert s["full_count"] == 2        # A2, B2
    assert s["blocked_count"] == 1     # B1
    assert s["overbooked_count"] == 1  # C2
    rc = s["reject_counts"]
    assert rc == {"overbooked": 1, "blocked": 1, "full": 2}


def test_seed_lines_c2_only_overbooked_and_positive_empty(client):
    data = client.get("/api/refills/latest?location_id=1").json()
    by = _by_slot(data["lines"])
    assert by["C2"]["reject_reason"] == "overbooked"
    assert by["C2"]["fill_qty"] == 0
    assert by["B1"]["reject_reason"] == "blocked"
    assert by["A2"]["reject_reason"] == "full"
    # 正补量行拒因必须为空
    assert by["A1"]["reject_reason"] == ""
    assert by["A1"]["fill_qty"] > 0


def test_create_overbooked_then_line_full_summary_all_follow(client):
    lanes = client.get("/api/lanes?location_id=1").json()
    a1 = next(l for l in lanes if l["slot_no"] == "A1")
    # 把 A1 改成超占（cap20，库存 25）
    r = client.patch(f"/api/lanes/{a1['id']}", json={"stock": 25})
    assert r.status_code == 200
    refill = r.json()["refill"]
    a1_line = next(l for l in refill["lines"] if l["slot_no"] == "A1")
    assert a1_line["reject_reason"] == "overbooked"
    assert a1_line["fill_qty"] == 0
    # 满仓页不得收录 A1；超占计数 +1
    full = {l["slot_no"] for l in client.get("/api/refills/full?location_id=1").json()["lanes"]}
    assert "A1" not in full
    s = client.get("/api/refills/summary?location_id=1").json()
    assert s["overbooked_count"] == 2
    assert s["need_fill_count"] == 1


def test_open_block_emits_blocked_and_close_restores(client):
    lanes = client.get("/api/lanes?location_id=1").json()
    c1 = next(l for l in lanes if l["slot_no"] == "C1")  # gap=10，未封锁
    # 打开封锁：只封锁不超占 → 封锁码
    r = client.patch(f"/api/lanes/{c1['id']}", json={"blocked": True})
    line = next(l for l in r.json()["refill"]["lines"] if l["slot_no"] == "C1")
    assert line["reject_reason"] == "blocked"
    assert line["fill_qty"] == 0
    s = client.get("/api/refills/summary?location_id=1").json()
    assert s["blocked_count"] == 2
    assert s["need_fill_count"] == 1
    # 关闭封锁（显式未配置 null）→ 恢复正补量，拒因为空
    r = client.patch(f"/api/lanes/{c1['id']}", json={"blocked": None})
    line = next(l for l in r.json()["refill"]["lines"] if l["slot_no"] == "C1")
    assert line["reject_reason"] == ""
    assert line["fill_qty"] == 10
    s = client.get("/api/refills/summary?location_id=1").json()
    assert s["blocked_count"] == 1
    assert s["need_fill_count"] == 2


def test_overbooked_and_blocked_together_only_overbooked(client):
    lanes = client.get("/api/lanes?location_id=1").json()
    c1 = next(l for l in lanes if l["slot_no"] == "C1")
    # 既超占又封锁：只能出超占码，不能并写，也不能写满仓/封锁
    r = client.patch(f"/api/lanes/{c1['id']}", json={"stock": 12, "blocked": True})
    line = next(l for l in r.json()["refill"]["lines"] if l["slot_no"] == "C1")
    assert line["reject_reason"] == "overbooked"
    s = client.get("/api/refills/summary?location_id=1").json()
    assert s["overbooked_count"] == 2
    # B1 仍是唯一纯封锁；C1 不进封锁计数
    assert s["blocked_count"] == 1
