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

export function TasksPage() {
  const navigate = useNavigate();
  const [accounts, setAccounts] = useState<PaperAccount[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

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

  function handleNewTask() {
    if (!getToken()) {
      navigate("/login");
      return;
    }
    navigate("/tasks/new");
  }

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
      <PageHeader title="实时模拟账户" subtitle="一个账号最多创建 3 个模拟账户；每个账户最多运行 20 个投资进程。">
        <div className="page-actions">
          <button className="button" type="button" onClick={createAccount} disabled={creating || accounts.length >= 3}>
            {accounts.length >= 3 ? "账户已达上限" : "新建模拟账户"}
          </button>
          <button className="button primary" type="button" onClick={handleNewTask}>
            新建投资进程
          </button>
        </div>
      </PageHeader>
      {error ? <div className="error-text">{error}</div> : null}
      {loading ? <div className="empty-state">正在加载模拟账户...</div> : null}
      {!loading && accounts.length === 0 ? <div className="empty-state">还没有模拟账户。先创建一个 100 万港币账户。</div> : null}

      <section className="account-list">
        {accounts.map((account) => (
          <article className="account-card" key={account.id}>
            <div className="account-card-header">
              <div>
                <h2>{account.name}</h2>
                <span>汇率 fallback：1 USD = {account.fx_usd_hkd.toFixed(4)} HKD</span>
              </div>
              <strong>{account.tasks.filter((task) => task.status !== "ended").length}/{account.max_processes} 进程</strong>
            </div>

            <div className="metric-grid account-metrics">
              <div className="metric-card">
                <span>账户总价值（HKD）</span>
                <strong>{money(account.equity_hkd, "HKD")}</strong>
              </div>
              <div className="metric-card">
                <span>账户总价值（USD）</span>
                <strong>{money(account.equity_hkd / account.fx_usd_hkd, "USD")}</strong>
              </div>
              <div className="metric-card">
                <span>未分配资金</span>
                <strong>{money(account.cash_hkd, "HKD")}</strong>
              </div>
            </div>

            <div className="process-list">
              {account.tasks.map((task) => (
                <Link className="process-row" to={`/tasks/${task.id}`} key={task.id}>
                  <div>
                    <strong>{task.name}</strong>
                    <span>
                      {task.symbol} · {modeLabel(task.mode)} · {task.base_currency} {task.allocated_cash.toFixed(2)}
                    </span>
                  </div>
                  <div>{statusLabel(task.status)}</div>
                  <div>{task.account ? money(task.account.equity, task.base_currency) : "-"}</div>
                </Link>
              ))}
              {account.tasks.length === 0 ? <div className="empty-state compact-empty">这个账户还没有投资进程。</div> : null}
            </div>
          </article>
        ))}
      </section>
    </>
  );
}
