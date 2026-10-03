# VendFill 售货机补货

按货道容量、库存与在途量计算缺口，生成不超缺口、非负的补货单。

技术栈：Python 3.12 / FastAPI / SQLAlchemy / PostgreSQL / Vue 3 / TypeScript / Vite

## 启动

```bash
docker compose up --build
```

| 服务 | 地址 |
| --- | --- |
| 前端 | http://localhost:4800 |
| API | http://localhost:9800 |
| API 文档 | http://localhost:9800/docs |
| Postgres | localhost:5449 |

健康检查：`GET http://localhost:9800/api/health`

## 使用说明

1. 在「点位」「货道」查看售货机布局与库存。
2. 在「销量」了解近期出货。
3. 打开「补货单」按缺口生成建议补货量。
4. 在「满仓」「汇总」查看已满货道与补货合计。

## 零补量拒因（互斥码）

补量为 0 的货道只命中一个拒因，优先级固定：**超占不可补（overbooked） > 货道封锁（blocked） > 已满仓（full）**。
补货单行、满仓页收录、汇总计数共用同一套码；正补量行拒因为空；
`blocked` 仅在显式为真时成立（未配置不冒封锁码）。在「货道格子」可改库存/在途制造超占、开关封锁，单据会按新码即时重算。

## 开发与测试

```bash
docker compose exec api pytest -q
```
