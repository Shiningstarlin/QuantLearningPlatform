import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { apiRequest, getToken, PaperAccount } from "../lib/api";
import { PageHeader } from "../ui/PageHeader";

function statusLabel(status: string) {
  if (status === "running") return "进行中";
  if (status === "paused") return "已暂停";
  if (status === "ended") return "已结束";
  return status;
}

function modeLabel(mode: string) {
  if (mode === "manual") return "手动";
  if (mode === "quant") return "量化";
  return mode;
}

function money(value: number, currency = "HKD") {
  return `${value.toLocaleString(undefined, { maximumFractionDigits: 2 })} ${currency}`;
}

function accountAllocatedHkd(account: PaperAccount) {
  return Math.max(account.equity_hkd - account.cash_hkd, 0);
}

function AccountDemoPreview() {
  const allocations = [
    { label: "HK.00700", detail: "量化策略 · 均线回溯", amount: 286730, tone: "teal", duration: "运行 42 天", returnLabel: "+2.18%" },
    { label: "US.NVDA", detail: "手动仓位 · 65% 持仓", amount: 213480, tone: "indigo", duration: "运行 28 天", returnLabel: "+5.64%" },
    { label: "SI=F", detail: "商品观察 · 白银期货", amount: 152960, tone: "amber", duration: "运行 16 天", returnLabel: "-1.12%" },
    { label: "未分配", detail: "现金池 · 等待机会", amount: 321875, tone: "slate", duration: "可随时分配", returnLabel: "0.00%" }
  ];
  const total = allocations.reduce((sum, item) => sum + item.amount, 0);
  const allocatedTotal = allocations
    .filter((item) => item.label !== "未分配")
    .reduce((sum, item) => sum + item.amount, 0);

  return (
    <div className="account-demo-preview" aria-hidden="true">
      <div className="demo-window-bar">
        <span />
        <span />
        <span />
      </div>
      <div className="demo-account-head">
        <div>
          <small>模拟账户示例</small>
          <strong>{money(total, "HKD")}</strong>
        </div>
        <b>3 项进行中的投资</b>
      </div>
      <div className="demo-allocation">
        {allocations.map((item) => (
          <span className={`demo-segment ${item.tone}`} key={item.label} style={{ width: `${(item.amount / total) * 100}%` }} />
        ))}
      </div>
      <div className="demo-process-summary">
        <div>
          <span>已分配资金</span>
          <strong>{money(allocatedTotal, "HKD")}</strong>
        </div>
        <div>
          <span>剩余现金</span>
          <strong>{money(total - allocatedTotal, "HKD")}</strong>
        </div>
      </div>
      <div className="demo-allocation-legend">
        {allocations.map((item) => (
          <div key={item.label}>
            <span className={`demo-swatch ${item.tone}`} />
            <p>
              <strong>{item.label}</strong>
              <small>{item.detail}</small>
              <small>{item.duration} · 收益率 {item.returnLabel}</small>
            </p>
            <b>{money(item.amount, "HKD")}</b>
          </div>
        ))}
      </div>
    </div>
  );
}

function AccountEmptyDemo({ onCreateAccount }: { onCreateAccount: () => void }) {
  return (
    <section className="empty-demo-panel account-empty-demo">
      <div className="empty-demo-copy">
        <span className="eyebrow">账户工作台</span>
        <h2>从第一笔模拟资金开始，搭建你的交易实验室</h2>
        <p>创建账户后，你可以把资金分配给不同资产，分别运行手动或量化投资项目，并在同一页观察现金、持仓和账户总价值。</p>
        <div className="guest-actions">
          <button className="button primary" type="button" onClick={onCreateAccount}>
            创建 100 万 HKD 模拟账户
          </button>
        </div>
      </div>
      <AccountDemoPreview />
    </section>
  );
}

export function TasksPage() {
  const navigate = useNavigate();
  const [accounts, setAccounts] = useState<PaperAccount[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const loggedIn = Boolean(getToken());

  async function loadAccounts() {
    if (!getToken()) {
      setAccounts([]);
      return;
    }
    setLoading(true);
    setError("");
    try {
      setAccounts(await apiRequest<PaperAccount[]>("/api/tasks/accounts"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载模拟账户失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAccounts();
  }, []);

  async function createAccount() {
    setCreating(true);
    setError("");
    try {
      const account = await apiRequest<PaperAccount>("/api/tasks/accounts", {
        method: "POST",
        body: JSON.stringify({ name: `模拟账户 ${accounts.length + 1}` })
      });
      setAccounts((current) => [account, ...current]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建模拟账户失败");
    } finally {
      setCreating(false);
    }
  }

  return (
    <>
      <PageHeader title="我的账户" subtitle="管理实时模拟账户、资金概况和投资项目。">
        {loggedIn ? (
          <div className="page-actions">
            <button className="button" type="button" onClick={createAccount} disabled={creating || accounts.length >= 3}>
              {accounts.length >= 3 ? "账户已达上限" : "新建模拟账户"}
            </button>
          </div>
        ) : null}
      </PageHeader>

      {!loggedIn ? (
        <section className="guest-account-panel">
          <div>
            <span className="eyebrow">Quant Lab</span>
            <h2>把实时行情变成一套可复盘的模拟账户</h2>
            <p>
              用独立账户管理模拟资金，为每个资产建立投资项目，观察策略、仓位和费用如何共同影响最终结果。
            </p>
            <div className="guest-login-options">
              <p>当前您未登录，请</p>
              <div className="guest-actions compact-actions">
                <button className="button primary" type="button" onClick={() => navigate("/register")}>
                  注册账户
                </button>
                <button className="button" type="button" onClick={() => navigate("/login")}>
                  登录账户
                </button>
              </div>
              <p>或以游客身份</p>
              <Link className="button" to="/backtests">
                进行策略回测
              </Link>
            </div>
          </div>
          <AccountDemoPreview />
        </section>
      ) : (
        <>
          {error ? <div className="error-text">{error}</div> : null}
          {loading ? <div className="empty-state">正在加载模拟账户...</div> : null}
          {!loading && !error && accounts.length === 0 ? <AccountEmptyDemo onCreateAccount={createAccount} /> : null}

          <section className="account-list">
            {accounts.map((account) => {
              const activeTaskCount = account.tasks.filter((task) => task.status !== "ended").length;
              const allocatedHkd = accountAllocatedHkd(account);
              const cashHkdRatio = account.equity_hkd > 0 ? (account.cash_hkd / account.equity_hkd) * 100 : 0;
              const allocatedRatio = account.equity_hkd > 0 ? (allocatedHkd / account.equity_hkd) * 100 : 0;
              return (
                <article className="account-card" key={account.id}>
                  <div className="account-card-header">
                    <div>
                      <h2>{account.name}</h2>
                      <span>参考汇率：1 USD = {account.fx_usd_hkd.toFixed(4)} HKD</span>
                    </div>
                    <strong>{activeTaskCount} 项进行中的投资</strong>
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
                      <span className="demo-segment slate" style={{ width: `${cashHkdRatio}%` }} />
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

                  <div className="account-card-actions">
                    <Link className="button primary" to={`/tasks/accounts/${account.id}`}>
                      查看详情
                    </Link>
                  </div>
                </article>
              );
            })}
          </section>
        </>
      )}
    </>
  );
}
