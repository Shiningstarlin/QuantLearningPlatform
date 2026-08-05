import { CSSProperties, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { AccountPerformance, apiRequest, getToken, PaperAccount, SimulationTask } from "../lib/api";
import { PageHeader } from "../ui/PageHeader";
import { LineChart } from "../ui/LineChart";

function money(value: number, currency = "HKD") {
  return `${value.toLocaleString(undefined, { maximumFractionDigits: 2 })} ${currency}`;
}

function statusLabel(status: string) {
  if (status === "running") return "进行中";
  if (status === "paused") return "已暂停";
  if (status === "ended") return "已结束";
  return status;
}

function modeLabel(mode: string) {
  if (mode === "manual") return "手动";
  if (mode === "quant") return "量化策略";
  return mode;
}

function settlementLabel(task: SimulationTask) {
  return task.settlement_days > 0 ? `T+${task.settlement_days}` : "T+0";
}

function accountAllocatedHkd(account: PaperAccount) {
  return Math.max(account.equity_hkd - account.cash_hkd, 0);
}

function signedMoney(value: number) {
  return `${value >= 0 ? "+" : ""}${money(value, "HKD")}`;
}

function signedPercent(value: number) {
  return `${value >= 0 ? "+" : ""}${(value * 100).toFixed(2)}%`;
}

function pnlClass(value: number) {
  return value >= 0 ? "pnl-positive" : "pnl-negative";
}

type AllocationSegment = {
  label: string;
  value: number;
  color: string;
};

function toHkd(value: number, currency: string, fxUsdHkd: number) {
  return currency.toUpperCase() === "HKD" ? value : value * fxUsdHkd;
}

function AllocationPieChart({ account, tasks }: { account: PaperAccount; tasks: SimulationTask[] }) {
  const segments: AllocationSegment[] = [
    { label: "现金", value: Math.max(account.cash_hkd, 0), color: "#53647b" },
    ...tasks.map((task, index) => ({
      label: task.asset_name || task.symbol || task.name,
      value: Math.max(toHkd(task.account?.equity ?? task.allocated_cash, task.base_currency, account.fx_usd_hkd), 0),
      color: ["#00d7ff", "#8b5cf6", "#b7f34a", "#ffb547"][index % 4]
    }))
  ].filter((segment) => segment.value > 0);
  const total = segments.reduce((sum, segment) => sum + segment.value, 0);
  let cursor = 0;
  const gradientStops = segments.map((segment) => {
    const start = cursor;
    cursor += total > 0 ? (segment.value / total) * 100 : 0;
    return `${segment.color} ${start.toFixed(2)}% ${cursor.toFixed(2)}%`;
  });
  const chartGradient = gradientStops.length > 0 ? `conic-gradient(${gradientStops.join(", ")})` : "#1b2b43";

  return (
    <section className="allocation-pie-panel" aria-label="资产分配构成">
      <div className="section-heading compact-heading">
        <div>
          <h3>资产分配构成</h3>
          <span>按当前模拟账户净值拆分现金与各投资项目</span>
        </div>
        <span className="performance-basis">HKD</span>
      </div>
      <div className="allocation-pie-layout">
        <div className="allocation-pie-chart" style={{ background: chartGradient } as CSSProperties}>
          <div className="allocation-pie-center">
            <strong>{money(account.equity_hkd, "HKD")}</strong>
            <span>账户净值</span>
          </div>
        </div>
        <div className="allocation-pie-legend">
          {segments.map((segment) => (
            <div className="allocation-pie-legend-row" key={segment.label}>
              <span className="allocation-pie-swatch" style={{ background: segment.color }} />
              <span title={segment.label}>{segment.label}</span>
              <strong>{total > 0 ? `${((segment.value / total) * 100).toFixed(1)}%` : "0.0%"}</strong>
            </div>
          ))}
          {segments.length === 0 ? <div className="allocation-pie-empty">暂无可分配资产</div> : null}
        </div>
      </div>
    </section>
  );
}

function AccountPerformancePanel({ performance }: { performance: AccountPerformance }) {
  const latestDaily = performance.daily[performance.daily.length - 1];
  const latestMonthly = performance.monthly[performance.monthly.length - 1];
  const chartPoints = performance.daily.map((row) => ({
    price: row.equity_hkd,
    quote_time: `${row.summary_date}T06:00:00+08:00`
  }));

  return (
    <section className="account-performance">
      <div className="section-heading">
        <div>
          <h2>账户收益轨迹</h2>
          <span>所有资产统一按北京时间每日 06:00 结算，金额以 HKD 计价。</span>
        </div>
        <small>更新于 {new Date(performance.as_of).toLocaleString()}</small>
      </div>

      <div className="metric-grid performance-metrics">
        <div className="metric-card">
          <span>总体盈亏</span>
          <strong className={pnlClass(performance.overall.total_pnl_hkd)}>{signedMoney(performance.overall.total_pnl_hkd)}</strong>
          <small>{signedPercent(performance.overall.total_return)} · {performance.overall.total_trade_count} 笔成交</small>
        </div>
        <div className="metric-card">
          <span>本结算日盈亏</span>
          <strong className={pnlClass(latestDaily?.pnl_hkd ?? 0)}>{latestDaily ? signedMoney(latestDaily.pnl_hkd) : "等待结算"}</strong>
          <small>{latestDaily ? `${latestDaily.summary_date} · ${signedPercent(latestDaily.return_rate)}` : "首次结算后生成"}</small>
        </div>
        <div className="metric-card">
          <span>本月盈亏</span>
          <strong className={pnlClass(latestMonthly?.pnl_hkd ?? 0)}>{latestMonthly ? signedMoney(latestMonthly.pnl_hkd) : "等待结算"}</strong>
          <small>{latestMonthly ? `${latestMonthly.year}-${String(latestMonthly.month).padStart(2, "0")} · 最大回撤 ${(latestMonthly.max_drawdown * 100).toFixed(2)}%` : "首个完整月度周期后生成"}</small>
        </div>
        <div className="metric-card">
          <span>账户峰值 / 最大回撤</span>
          <strong>{money(performance.overall.peak_equity_hkd, "HKD")}</strong>
          <small>{(performance.overall.max_drawdown * 100).toFixed(2)}%</small>
        </div>
      </div>

      <div className="performance-chart-panel">
        <div className="section-heading compact-heading">
          <div>
            <h3>账户净值曲线</h3>
            <span>曲线上的每个点代表一个 06:00 结算快照。</span>
          </div>
          <span className="performance-basis">HKD · 结算口径</span>
        </div>
        {chartPoints.length >= 2 ? <LineChart points={chartPoints} height={280} /> : <div className="chart-empty">完成第二个结算日后，这里会显示账户净值走势。</div>}
      </div>

      <div className="performance-tables">
        <div>
          <h3>最近结算日</h3>
          <div className="performance-table">
            <div className="performance-table-head"><span>日期</span><span>账户净值</span><span>日盈亏</span><span>收益率</span></div>
            {performance.daily.slice(-7).reverse().map((row) => (
              <div className="performance-table-row" key={row.summary_date}>
                <span>{row.summary_date}</span>
                <strong>{money(row.equity_hkd, "HKD")}</strong>
                <strong className={pnlClass(row.pnl_hkd)}>{signedMoney(row.pnl_hkd)}</strong>
                <span className={pnlClass(row.return_rate)}>{signedPercent(row.return_rate)}</span>
              </div>
            ))}
          </div>
        </div>
        <div>
          <h3>最近月份</h3>
          <div className="performance-table">
            <div className="performance-table-head"><span>月份</span><span>期末净值</span><span>月盈亏</span><span>最大回撤</span></div>
            {performance.monthly.slice(-6).reverse().map((row) => (
              <div className="performance-table-row" key={`${row.year}-${row.month}`}>
                <span>{row.year}-{String(row.month).padStart(2, "0")}</span>
                <strong>{money(row.end_equity_hkd, "HKD")}</strong>
                <strong className={pnlClass(row.pnl_hkd)}>{signedMoney(row.pnl_hkd)}</strong>
                <span className="pnl-negative">{(row.max_drawdown * 100).toFixed(2)}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

export function AccountManagementPage() {
  const { accountId } = useParams();
  const navigate = useNavigate();
  const [account, setAccount] = useState<PaperAccount | null>(null);
  const [performance, setPerformance] = useState<AccountPerformance | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!getToken()) {
      navigate("/login");
      return;
    }

    setLoading(true);
    setError("");
    setPerformance(null);
    apiRequest<PaperAccount[]>("/api/tasks/accounts")
      .then((accounts) => {
        const found = accounts.find((item) => String(item.id) === accountId);
        if (!found) {
          throw new Error("没有找到这个模拟账户。");
        }
        setAccount(found);
        return apiRequest<AccountPerformance>(`/api/tasks/accounts/${found.id}/performance`);
      })
      .then((loadedPerformance) => setPerformance(loadedPerformance))
      .catch((err) => setError(err instanceof Error ? err.message : "加载账户管理页失败"))
      .finally(() => setLoading(false));
  }, [accountId, navigate]);

  const activeTasks = account?.tasks.filter((task) => task.status !== "ended") ?? [];
  const allocatedHkd = account ? accountAllocatedHkd(account) : 0;
  const allocatedRatio = account && account.equity_hkd > 0 ? (allocatedHkd / account.equity_hkd) * 100 : 0;
  const cashRatio = account && account.equity_hkd > 0 ? (account.cash_hkd / account.equity_hkd) * 100 : 0;

  return (
    <>
      <PageHeader title={account ? `${account.name} 管理页` : "账户管理页"} subtitle="查看资金结构，新增投资项目，或进入已有项目调整参数。">
        <div className="page-actions">
          <Link className="button" to="/tasks">
            返回我的账户
          </Link>
          {account ? (
            <Link className="button primary" to={`/tasks/new?accountId=${account.id}`}>
              新增投资项目
            </Link>
          ) : null}
        </div>
      </PageHeader>

      {error ? <div className="error-text">{error}</div> : null}
      {loading ? <div className="empty-state">正在加载账户数据...</div> : null}

      {account ? (
        <>
          <article className="account-card account-management-card">
            <div className="account-card-header">
              <div>
                <h2>{account.name}</h2>
                <span>参考汇率：1 USD = {account.fx_usd_hkd.toFixed(4)} HKD</span>
              </div>
              <strong>{activeTasks.length} 项进行中的投资</strong>
            </div>

            <div className="metric-grid account-metrics">
              <div className="metric-card">
                <span>实际持有 HKD</span>
                <strong>{money(account.cash_hkd, "HKD")}</strong>
              </div>
              <div className="metric-card">
                <span>实际持有 USD</span>
                <strong>{money(account.cash_usd, "USD")}</strong>
              </div>
              <div className="metric-card">
                <span>总资产</span>
                <strong>{money(account.equity_hkd, "HKD")}</strong>
                <small>{money(account.equity_hkd / account.fx_usd_hkd, "USD")}</small>
              </div>
            </div>

            <div className="account-allocation-panel">
              <div className="demo-allocation account-allocation-bar">
                <span className="demo-segment teal" style={{ width: `${allocatedRatio}%` }} />
                <span className="demo-segment slate" style={{ width: `${cashRatio}%` }} />
              </div>
              <div className="demo-process-summary">
                <div>
                  <span>已分配资金</span>
                  <strong>{money(allocatedHkd, "HKD")}</strong>
                </div>
                <div>
                  <span>未分配资金</span>
                  <strong>{money(account.cash_hkd, "HKD")}</strong>
                </div>
              </div>
            </div>

            <AllocationPieChart account={account} tasks={activeTasks} />
          </article>

          {performance ? <AccountPerformancePanel performance={performance} /> : <div className="empty-state">正在生成账户收益轨迹...</div>}

          <section className="account-project-section">
            <div className="section-heading">
              <div>
                <h2>进行中的投资项目</h2>
                <span>点击项目进入编辑与手动调整页面。</span>
              </div>
            </div>

            <div className="project-detail-list">
              {activeTasks.map((task) => {
                const marketValue = task.account ? Math.max(task.account.equity - task.account.cash - task.account.frozen_cash, 0) : 0;
                return (
                  <Link className="project-detail-row" to={`/tasks/${task.id}`} key={task.id}>
                    <div>
                      <strong>{task.name}</strong>
                      <span>{task.symbol} · {task.asset_name || task.exchange} · {modeLabel(task.mode)}</span>
                    </div>
                    <div>
                      <span>状态</span>
                      <strong>{statusLabel(task.status)}</strong>
                    </div>
                    <div>
                      <span>分配资金</span>
                      <strong>{money(task.allocated_cash, task.base_currency)}</strong>
                    </div>
                    <div>
                      <span>当前净值</span>
                      <strong>{task.account ? money(task.account.equity, task.base_currency) : "-"}</strong>
                    </div>
                    <div>
                      <span>持仓市值</span>
                      <strong>{money(marketValue, task.base_currency)}</strong>
                    </div>
                    <div>
                      <span>规则</span>
                      <strong>{settlementLabel(task)} · {task.mode === "manual" ? `${Math.round(task.manual_target_exposure * 100)}%` : task.strategy_key}</strong>
                    </div>
                  </Link>
                );
              })}
              {activeTasks.length === 0 ? (
                <div className="empty-state compact-empty">
                  这个账户还没有进行中的投资项目。可以先新增一个项目，把资金分配给具体标的。
                </div>
              ) : null}
            </div>
          </section>
        </>
      ) : null}
    </>
  );
}
