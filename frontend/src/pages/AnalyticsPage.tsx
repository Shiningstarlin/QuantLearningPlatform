import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { apiRequest, SimulationTask, TradeLog } from "../lib/api";
import { PageHeader } from "../ui/PageHeader";

export function AnalyticsPage() {
  const { taskId } = useParams();
  const [task, setTask] = useState<SimulationTask | null>(null);
  const [logs, setLogs] = useState<TradeLog[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!taskId) return;
    Promise.all([
      apiRequest<SimulationTask>(`/api/tasks/${taskId}`),
      apiRequest<TradeLog[]>(`/api/tasks/${taskId}/trades`)
    ])
      .then(([taskData, logData]) => {
        setTask(taskData);
        setLogs(logData);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "加载汇总失败"));
  }, [taskId]);

  const equity = task?.account?.equity ?? 0;
  const initialCash = task?.account?.initial_cash ?? 0;
  const totalReturn = initialCash > 0 ? (equity - initialCash) / initialCash : 0;
  const buyCount = logs.filter((log) => log.side === "buy").length;
  const sellCount = logs.filter((log) => log.side === "sell").length;

  return (
    <>
      <PageHeader title="汇总分析" subtitle="当前先展示基础统计，后续会扩展日/月收益和回撤。">
        <Link className="button" to={`/tasks/${taskId}`}>
          返回任务
        </Link>
      </PageHeader>
      {error ? <div className="error-text">{error}</div> : null}
      <section className="metric-grid">
        <div className="metric-card">
          <span>累计收益率</span>
          <strong>{(totalReturn * 100).toFixed(2)}%</strong>
        </div>
        <div className="metric-card">
          <span>买入 / 卖出次数</span>
          <strong>{buyCount} / {sellCount}</strong>
        </div>
        <div className="metric-card">
          <span>交易次数</span>
          <strong>{logs.length}</strong>
        </div>
      </section>
    </>
  );
}
