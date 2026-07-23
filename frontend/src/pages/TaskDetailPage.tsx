import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { apiRequest, SimulationTask } from "../lib/api";
import { PageHeader } from "../ui/PageHeader";

function statusLabel(status?: string) {
  if (status === "running") return "进行中";
  if (status === "paused") return "已暂停";
  if (status === "ended") return "已结束";
  return status ?? "-";
}

export function TaskDetailPage() {
  const { taskId } = useParams();
  const [task, setTask] = useState<SimulationTask | null>(null);
  const [cashAmount, setCashAmount] = useState("");
  const [targetExposure, setTargetExposure] = useState("0");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function loadTask() {
    if (!taskId) return;
    setError("");
    try {
      const loadedTask = await apiRequest<SimulationTask>(`/api/tasks/${taskId}`);
      setTask(loadedTask);
      setTargetExposure(String(Math.round((loadedTask.manual_target_exposure ?? 0) * 100)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载任务失败");
    }
  }

  async function control(eventType: string, amount?: number) {
    if (!taskId) return;
    setLoading(true);
    setError("");
    try {
      const updated = await apiRequest<SimulationTask>(`/api/tasks/${taskId}/control`, {
        method: "POST",
        body: JSON.stringify({ event_type: eventType, amount, note: "manual control" })
      });
      setTask(updated);
      if (eventType === "add_cash" || eventType === "remove_cash") {
        setCashAmount("");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    } finally {
      setLoading(false);
    }
  }

  async function updateExposure() {
    if (!taskId) return;
    setLoading(true);
    setError("");
    try {
      const updated = await apiRequest<SimulationTask>(`/api/tasks/${taskId}/manual-exposure`, {
        method: "POST",
        body: JSON.stringify({ target_exposure: Number(targetExposure) / 100 })
      });
      setTask(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "调整投入比例失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadTask();
  }, [taskId]);

  const account = task?.account;
  const amount = Number(cashAmount);
  const canAdjustCash = Number.isFinite(amount) && amount > 0;

  return (
    <>
      <PageHeader title={task?.name ?? `任务 #${taskId}`} subtitle="查看账户、策略和手动控制。">
        <Link className="button" to="/tasks">
          返回任务列表
        </Link>
      </PageHeader>

      {error ? <div className="error-text">{error}</div> : null}

      <section className="metric-grid">
        <div className="metric-card">
          <span>状态</span>
          <strong>{statusLabel(task?.status)}</strong>
        </div>
        <div className="metric-card">
          <span>进程净值</span>
          <strong>{account ? `${account.equity.toFixed(2)} ${task?.base_currency ?? ""}` : "-"}</strong>
        </div>
        <div className="metric-card">
          <span>可用现金</span>
          <strong>{account ? `${account.cash.toFixed(2)} ${task?.base_currency ?? ""}` : "-"}</strong>
        </div>
        <div className="metric-card">
          <span>冻结现金</span>
          <strong>
            {account
              ? `${account.frozen_cash.toFixed(2)} ${task?.base_currency ?? ""}${account.cash_available_on ? ` · ${account.cash_available_on} 释放` : ""}`
              : "-"}
          </strong>
        </div>
      </section>

      <section className="control-panel">
        <div className="action-row">
          {task?.status === "running" ? (
            <button className="button" type="button" disabled={loading} onClick={() => control("pause")}>
              暂停项目
            </button>
          ) : (
            <button className="button primary" type="button" disabled={loading || task?.status === "ended"} onClick={() => control("start")}>
              启动项目
            </button>
          )}
          <button className="button danger" type="button" disabled={loading || task?.status === "ended"} onClick={() => control("end")}>
            结束模拟
          </button>
        </div>
        <div className="form-row cash-control">
          <input
            type="number"
            min="0"
            value={cashAmount}
            onChange={(event) => setCashAmount(event.target.value)}
            placeholder="资金调整金额"
          />
          <button className="button" type="button" disabled={loading || !canAdjustCash} onClick={() => control("add_cash", amount)}>
            追加资金
          </button>
          <button className="button" type="button" disabled={loading || !canAdjustCash} onClick={() => control("remove_cash", amount)}>
            减少资金
          </button>
        </div>
      </section>

      {task?.mode === "manual" ? (
        <section className="control-panel">
          <label>
            实际投入该资产的比例：{targetExposure}%
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={targetExposure}
              onChange={(event) => setTargetExposure(event.target.value)}
            />
          </label>
          <button className="button primary" type="button" disabled={loading} onClick={updateExposure}>
            按目标比例调整
          </button>
        </section>
      ) : null}

      <section className="tabs">
        <Link to={`/tasks/${taskId}/assets`}>关注资产</Link>
        <Link to={`/tasks/${taskId}/logs`}>交易日志</Link>
        <Link to={`/tasks/${taskId}/analytics`}>汇总分析</Link>
      </section>

      <div className="task-info-grid">
        <div className="info-block">
          <span>模式 / 策略</span>
          <strong>{task ? `${task.mode === "manual" ? "手动" : "量化"} / ${task.strategy_key}` : "-"}</strong>
        </div>
        <div className="info-block">
          <span>绑定资产</span>
          <strong>{task ? `${task.symbol} · ${task.exchange}` : "-"}</strong>
        </div>
        <div className="info-block">
          <span>费率模型 / 滑点</span>
          <strong>
            {task ? `${task.fee_profile} / ${task.slippage_rate}` : "-"}
          </strong>
        </div>
        <div className="info-block">
          <span>交易限制</span>
          <strong>{task ? (task.settlement_days > 0 ? `T+${task.settlement_days}` : "T+0") : "-"}</strong>
        </div>
      </div>
    </>
  );
}
