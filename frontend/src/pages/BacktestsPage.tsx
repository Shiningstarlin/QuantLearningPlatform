import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { apiRequest, BacktestTask, getToken } from "../lib/api";
import { PageHeader } from "../ui/PageHeader";

function statusLabel(status: string) {
  if (status === "completed") return "已完成";
  if (status === "failed") return "失败";
  if (status === "pending") return "运行中";
  return status;
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(2)}%`;
}

export function BacktestsPage() {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState<BacktestTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!getToken()) {
      setTasks([]);
      return;
    }
    setLoading(true);
    apiRequest<BacktestTask[]>("/api/backtests")
      .then(setTasks)
      .catch((err) => setError(err instanceof Error ? err.message : "加载回测失败"))
      .finally(() => setLoading(false));
  }, []);

  function handleNewBacktest() {
    if (!getToken()) {
      navigate("/login");
      return;
    }
    navigate("/backtests/new");
  }

  return (
    <>
      <PageHeader title="历史回测" subtitle="选择资产、策略和时间区间，复盘一段历史市场中的模拟交易。">
        <button className="button primary" type="button" onClick={handleNewBacktest}>
          新建回测
        </button>
      </PageHeader>

      {error ? <div className="error-text">{error}</div> : null}
      {loading ? <div className="empty-state">正在加载回测...</div> : null}
      {!loading && tasks.length === 0 ? <div className="empty-state">还没有历史回测。点击“新建回测”开始一次实验。</div> : null}

      <section className="task-list">
        {tasks.map((task) => {
          const bestRun = task.runs.find((run) => run.id === task.best_run_id) ?? task.runs[0];
          return (
          <Link className="task-row backtest-row" to={bestRun ? `/backtests/${bestRun.id}` : "/backtests"} key={task.id}>
            <div>
              <strong>{task.name}</strong>
              <span>
                {task.symbol} · {task.strategy_count} 个策略 · {task.start_date} 至 {task.end_date}
              </span>
            </div>
            <div>{statusLabel(task.status)}</div>
            <div>{bestRun ? formatPercent(bestRun.total_return) : "-"}</div>
            <div>{bestRun ? bestRun.final_equity.toFixed(2) : "-"}</div>
          </Link>
          );
        })}
      </section>
    </>
  );
}
