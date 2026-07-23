# Quant Learning Simulator

一个用于学习量化交易和计算金融工程的小型前后端分离项目。项目只使用模拟资金，不接入真实下单，不托管真实交易密钥；市场价格可以来自真实行情 API，也可以在开发阶段使用内置 mock provider。

## 项目目标

- 支持用户注册、登录和创建多个模拟任务。
- 每个任务拥有独立模拟资金、关注资产、策略模板和运行状态。
- 后台根据真实或模拟行情价格计算买入、卖出、持仓、现金和收益。
- 保存每次模拟交易日志，并生成每日、每月汇总分析。
- 支持手动控制：冻结/恢复买入卖出、追加/减少资金、结束模拟。
- 预留税率、手续费、滑点、T+1、交易日历、资产类型差异等规则。

## 当前框架

```text
backend/   FastAPI 后端，负责用户、模拟账户、策略任务、行情、交易日志和汇总
frontend/  React 前端，负责注册登录、任务配置、仪表盘、日志和分析页面
docs/      架构、配置和开发路线说明
```

## 第一版技术选择

- 后端：FastAPI、SQLAlchemy、Pydantic
- 数据库：开发和生产均支持 MySQL，SQLite 仅作为本地轻量测试或历史迁移源
- 前端：Vite、React、TypeScript、React Router
- 市场数据：支持 mock、Yahoo Finance、Futu OpenAPI provider，预留 Finnhub、Alpha Vantage、Polygon、Twelve Data、CCXT 等扩展位
- 任务运行：第一阶段使用进程内调度器，后续可替换为 Redis Queue / Celery / APScheduler

## 快速开始

后端：

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e .
copy ..\.env.example .env
uvicorn app.main:app --reload --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev
```

默认前端访问 `http://localhost:5173`，后端 API 访问 `http://localhost:8000`。

## 需要配置什么

最小开发配置只需要一个数据库连接和 JWT 密钥。若要接入真实行情，需要配置对应行情 API key。完整说明见 [docs/CONFIGURATION.md](docs/CONFIGURATION.md)，生产 Docker 部署见 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)。

当前行情看板默认使用 Futu OpenAPI，需要先在本机启动 FutuOpenD，默认连接 `127.0.0.1:11111`。看板暂时锁定为 `股票.txt` 中的港股和美股，后台每 30 秒检查一次，只自动刷新处于常规交易时段的市场；手动刷新会立即读取并把成功返回的数据保存到数据库。富途快照请求会按 provider 批量合并，低于每分钟 30 次快照请求限制。

## 当前已搭建的能力

- 后端 API 骨架：注册、登录、模拟任务、关注资产、策略模板、模拟订单、交易日志。
- 后端领域模型：用户、模拟任务、模拟账户、关注资产、持仓、交易日志、控制事件、日/月汇总。
- 模拟撮合引擎：预留税率、手续费、滑点、T+1 检查、现金和持仓更新。
- 行情看板：支持配置行情资产，后台定期刷新报价并保存历史。
- 历史回测：只使用 yfinance 下载历史 OHLCV 数据，不使用行情看板保存的实时节点数据。
- yfinance 代理：本地测试可在 `backend/.env` 配置 `YFINANCE_PROXY_URL`，正式环境按实际代理端口调整。
- 前端路由骨架：总览、行情看板、任务、创建任务、任务详情、关注资产、日志、分析、设置。
- 配置文档：数据库、日志、行情 API key、前端路由、模拟交易参数。

## 重要边界

本项目用于学习和展示工程能力，不提供投资建议，不执行真实交易，不连接真实券商下单接口。所有资金、订单、成交、收益和风险指标均为模拟结果。

## License

MIT License. See [LICENSE](LICENSE).
