# 配置说明

## 最小必需配置

开发阶段只需要：

| 配置 | 说明 | 示例 |
|---|---|---|
| `SECRET_KEY` | 登录 token 加密密钥 | `change-me` |
| `DATABASE_URL` | 数据库连接 | `mysql+pymysql://<user>:<password>@<mysql-host>:3306/quant_dev?charset=utf8mb4&ssl_disabled=true` |
| `MARKET_DATA_PROVIDER` | 行情来源 | `futu` |
| `FRONTEND_ORIGIN` | 前端地址，供 CORS 使用 | `http://localhost:5173` |

## 数据库

当前开发环境使用 MySQL，开发库为 `quant_dev`：

```env
DATABASE_URL=mysql+pymysql://<user>:<password>@<mysql-host>:3306/quant_dev?charset=utf8mb4&ssl_disabled=true
```

生产环境使用同一实例中的 `quant_prod`：

```env
DATABASE_URL=mysql+pymysql://<user>:<password>@<mysql-host>:3306/quant_prod?charset=utf8mb4&ssl_disabled=true
```

如果密码中包含 `@`，需要在 URL 中写为 `%40`。MySQL JDBC 风格的 `allowPublicKeyRetrieval=true&useSSL=false` 在 Python 的 PyMySQL 中不使用；这里用 `ssl_disabled=true`，字符集用 `charset=utf8mb4`。本地 SQLite 文件 `backend/quant_simulator.db` 仅作为历史数据迁移源保留。

数据库中会存储：

- 用户账号
- 模拟任务
- 模拟账户资金
- 关注资产
- 持仓
- 交易日志
- 手动控制事件
- 每日/月度汇总

## 日志

第一版交易日志直接进入数据库 `trade_logs` 表。应用运行日志先输出到控制台。后续可以增加：

- `logs/app.log`
- `logs/simulation_worker.log`
- 结构化 JSON 日志
- Sentry / OpenTelemetry

## 市场数据

当前配置默认接入 Futu OpenAPI provider，不需要云端 API key，但需要本机先运行 FutuOpenD：

```env
MARKET_DATA_PROVIDER=futu
FUTU_HOST=127.0.0.1
FUTU_PORT=11111
FUTU_SNAPSHOT_MAX_REQUESTS_PER_MINUTE=30
MARKET_BOARD_REFRESH_SECONDS=30
MARKET_BOARD_DEFAULT_SYMBOLS=HK.00700:腾讯控股,HK.03750:宁德时代,HK.01398:工商银行,HK.09988:阿里巴巴-W,HK.01211:比亚迪股份,US.NVDA:英伟达,US.AAPL:苹果,US.GOOGL:谷歌-A,US.GOOG:谷歌-C,US.MSFT:微软,US.AMZN:亚马逊,US.SPCX:SpaceX,US.TSLA:特斯拉
MARKET_BOARD_DEFAULT_ONLY=true
```

行情看板会按 provider 合并为批量 `get_market_snapshot` 请求。后台每 30 秒检查一次，只自动刷新处于常规交易时段的市场；手动刷新会强制读取并保存成功返回的数据。当前交易时段判断使用常规工作日时间：港股为香港时间 `09:30-12:00`、`13:00-16:00`，美股为纽约时间 `09:30-16:00`。

如果你在离线环境或不想请求外部行情，可以切换回 mock：

```env
MARKET_DATA_PROVIDER=mock
```

真实行情可以逐步接入：

| Provider | 适合资产 | 是否通常需要 key |
|---|---|---|
| Futu OpenAPI | 港股、美股、A 股等富途支持市场 | 不需要云端 key，需要本机 FutuOpenD |
| Yahoo Finance / yfinance | 美股、ETF、部分指数 | 否 |
| Finnhub | 美股、外汇、加密货币 | 是 |
| Alpha Vantage | 美股、外汇、加密货币 | 是 |
| Polygon | 美股、期权、外汇、加密货币 | 是 |
| Twelve Data | 股票、ETF、外汇、加密货币 | 是 |
| CCXT | 加密货币交易所行情 | 部分公开行情不需要 |
| AkShare | A 股、港股、期货等中文数据源 | 多数不需要 |

第一版已实现 `mock`、`yahoo` 和 `futu`。

## API Key 获取入口

| Provider | 入口 | 基本流程 |
|---|---|---|
| Futu OpenAPI | https://openapi.futunn.com/futu-api-doc/ | 安装并启动 FutuOpenD，确认监听 `127.0.0.1:11111`，项目通过本地 OpenD 调用行情接口。 |
| Yahoo Finance / yfinance | https://github.com/ranaroussi/yfinance | 无需申请 key；安装依赖后通过 yfinance 获取 Yahoo Finance 公开数据。适合个人学习和研究。 |
| Finnhub | https://finnhub.io/register | 注册账号，登录后在 dashboard/API 页面查看 token，填入 `FINNHUB_API_KEY`。 |
| Alpha Vantage | https://www.alphavantage.co/support/#api-key | 在页面填写身份、机构和邮箱领取 free API key，填入 `ALPHAVANTAGE_API_KEY`。 |
| Polygon / Massive | https://massive.com/dashboard/signup | 注册或登录后进入 Dashboard 获取 API key，填入 `POLYGON_API_KEY`。 |
| Twelve Data | https://twelvedata.com/register | 创建账号后在账户/API 页面查看 key，填入 `TWELVEDATA_API_KEY`。 |

注意：免费或无需 key 的数据源通常有频率限制、延迟、覆盖范围或服务条款限制。项目用于学习时可以先用 `yahoo`，如果将来要展示更稳定的准实时能力，再切到 Finnhub、Polygon/Massive 或 Twelve Data。

## 历史回测数据源

历史回测模块只使用 `yfinance` 获取指定起止日期之间的日线 OHLCV 历史数据，不读取行情看板中由 Futu OpenAPI 保存的实时快照。这样可以避免用离散实时节点去近似历史行情。

如果 yfinance 频繁出现 `Too Many Requests`，可以配置代理：

```env
YFINANCE_PROXY_URL=http://127.0.0.1:7890
YFINANCE_REQUEST_TIMEOUT=20
YFINANCE_CACHE_DIR=var/yfinance-cache
YFINANCE_DISABLE_PERSISTENT_CACHE=true
```

`YFINANCE_PROXY_URL` 在正式环境中应改成该环境可访问的代理地址和端口。当前项目默认禁用 yfinance 的持久化缓存，因为部分 Windows/Python 环境下 yfinance 内部 SQLite 缓存会出现 `unable to open database file`，禁用后仍可正常下载历史行情。

看板资产代码会在后端自动转换为 yfinance ticker：

| 看板代码 | yfinance ticker |
|---|---|
| `US.NVDA` | `NVDA` |
| `US.AAPL` | `AAPL` |
| `HK.00700` | `0700.HK` |
| `HK.09988` | `9988.HK` |

回测资产列表还额外提供两个不进入行情看板的 yfinance-only 商品期货：

| 资产 | yfinance ticker |
|---|---|
| 黄金期货 | `GC=F` |
| 白银期货 | `SI=F` |

`US.SPCX` 当前在 Yahoo Finance / yfinance 没有可用历史价格，因此会保留在实时行情看板中，但不会出现在历史回测资产列表里。`HK.03750` 在 2025 年之后可以取到历史数据，若选择早于上市前的区间，回测会提示没有历史价格。

## 前端路由

建议第一版包含：

| 路由 | 用途 |
|---|---|
| `/login` | 登录 |
| `/register` | 注册 |
| `/dashboard` | 总览 |
| `/market-board` | 行情看板 |
| `/market-board/:id` | 行情资产详情 |
| `/tasks` | 模拟任务列表 |
| `/tasks/new` | 创建模拟任务 |
| `/tasks/:id` | 单个任务详情 |
| `/tasks/:id/assets` | 关注资产 |
| `/tasks/:id/logs` | 交易日志 |
| `/tasks/:id/analytics` | 汇总分析 |
| `/backtests` | 历史回测列表 |
| `/backtests/new` | 新建历史回测 |
| `/backtests/:id` | 回测结果详情 |
| `/settings` | 用户设置 |

## 模拟交易参数

| 配置 | 说明 |
|---|---|
| `DEFAULT_TAX_RATE` | 默认税率 |
| `DEFAULT_COMMISSION_RATE` | 默认手续费率 |
| `DEFAULT_SLIPPAGE_RATE` | 默认滑点率 |
| `ENABLE_T_PLUS_ONE` | 是否启用 T+1 限制 |
| `SIMULATION_TICK_SECONDS` | 后台任务轮询间隔 |
| `MARKET_BOARD_ENABLED` | 是否启用行情看板后台刷新 |
| `MARKET_BOARD_REFRESH_SECONDS` | 行情看板刷新间隔 |
| `MARKET_BOARD_DEFAULT_SYMBOLS` | 首次启动时自动加入看板的默认资产 |
| `MARKET_BOARD_DEFAULT_ONLY` | 是否只启用默认资产 |

这些配置只是默认值。后续每个模拟任务可以拥有自己的税率、手续费率和交易规则。
