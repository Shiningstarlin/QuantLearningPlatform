import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { apiRequest, TradeLog } from "../lib/api";
import { PageHeader } from "../ui/PageHeader";

export function LogsPage() {
  const { taskId } = useParams();
  const [logs, setLogs] = useState<TradeLog[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!taskId) return;
    apiRequest<TradeLog[]>(`/api/tasks/${taskId}/trades`)
      .then(setLogs)
      .catch((err) => setError(err instanceof Error ? err.message : "加载交易日志失败"));
  }, [taskId]);

  return (
    <>
      <PageHeader title="交易日志" subtitle="记录每一次模拟成交、费用、税费和成交原因。">
        <Link className="button" to={`/tasks/${taskId}`}>
          返回任务
        </Link>
      </PageHeader>
      {error ? <div className="error-text">{error}</div> : null}
      <div className="data-table">
        <div className="data-row header">
          <span>时间</span>
          <span>标的</span>
          <span>方向</span>
          <span>数量</span>
          <span>价格</span>
          <span>净额</span>
        </div>
        {logs.map((log) => (
          <div className="data-row" key={log.id}>
            <span>{new Date(log.traded_at).toLocaleString()}</span>
            <span>{log.symbol}</span>
            <span>{log.side}</span>
            <span>{log.quantity}</span>
            <span>{log.price.toFixed(2)}</span>
            <span>{log.net_amount.toFixed(2)}</span>
          </div>
        ))}
      </div>
    </>
  );
}
