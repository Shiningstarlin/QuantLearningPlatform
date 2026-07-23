import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { apiRequest, BacktestComparison, BacktestRun } from "../lib/api";
import { PageHeader } from "../ui/PageHeader";

function formatPercent(value: number) {
  return `${(value * 100).toFixed(2)}%`;
}

function formatMoney(value: number) {
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function strategyLabel(strategyKey: string) {
  if (strategyKey === "ma_crossover") return "均线交叉";
  if (strategyKey === "rsi_reversal") return "RSI 反转";
  if (strategyKey === "dca") return "定投";
  return strategyKey;
}

function bestBy(runs: BacktestRun[], selector: (run: BacktestRun) => number, smallerIsBetter = false) {
  if (runs.length === 0) return null;
  return runs.reduce((best, run) => {
    const bestValue = selector(best);
    const currentValue = selector(run);
    return smallerIsBetter ? (currentValue < bestValue ? run : best) : currentValue > bestValue ? run : best;
  }, runs[0]);
}

export function BacktestComparePage() {
  const [params] = useSearchParams();
  const ids = params.get("ids") ?? "";
  const [runs, setRuns] = useState<BacktestRun[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!ids) {
      setRuns([]);
      return;
    }
    apiRequest<BacktestComparison>(`/api/backtests/compare?ids=${encodeURIComponent(ids)}`)
      .then((data) => setRuns(data.runs))
      .catch((err) => setError(err instanceof Error ? err.message : "加载回测对比失败"));
  }, [ids]);

  const bestReturn = useMemo(() => bestBy(runs, (run) => run.total_return), [runs]);
  const bestDrawdown = useMemo(() => bestBy(runs, (run) => Math.abs(run.max_drawdown), true), [runs]);
  const bestWinRate = useMemo(() => bestBy(runs, (run) => run.win_rate), [runs]);

  return (
    <>
      <PageHeader title="历史回测对比" subtitle="同一资产与时间区间下，对比不同策略模板的模拟结果。">
        <Link className="button" to="/backtests">
          返回回测列表
        </Link>
      </PageHeader>

      {error ? <div className="error-text">{error}</div> : null}

      <section className="metric-grid">
        <div className="metric-card">
          <span>最高收益</span>
          <strong>{bestReturn ? `${strategyLabel(bestReturn.strategy_key)} ${formatPercent(bestReturn.total_return)}` : "-"}</strong>
        </div>
        <div className="metric-card">
          <span>最小回撤</span>
          <strong>{bestDrawdown ? `${strategyLabel(bestDrawdown.strategy_key)} ${formatPercent(bestDrawdown.max_drawdown)}` : "-"}</strong>
        </div>
        <div className="metric-card">
          <span>最高胜率</span>
          <strong>{bestWinRate ? `${strategyLabel(bestWinRate.strategy_key)} ${formatPercent(bestWinRate.win_rate)}` : "-"}</strong>
        </div>
      </section>

      <section className="data-table comparison-table">
        <div className="data-row header">
          <span>策略</span>
          <span>资产</span>
          <span>总收益</span>
          <span>最大回撤</span>
          <span>交易/胜率</span>
          <span>期末净值</span>
        </div>
        {runs.map((run) => (
          <Link className="data-row" to={`/backtests/${run.id}`} key={run.id}>
            <span>
              <strong>{strategyLabel(run.strategy_key)}</strong>
              <small>{run.name}</small>
            </span>
            <span>{run.symbol}</span>
            <span className={run.total_return >= 0 ? "positive-text" : "negative-text"}>{formatPercent(run.total_return)}</span>
            <span>{formatPercent(run.max_drawdown)}</span>
            <span>
              {run.trade_count} / {formatPercent(run.win_rate)}
            </span>
            <span>{formatMoney(run.final_equity)}</span>
          </Link>
        ))}
        {runs.length === 0 ? <div className="empty-state compact-empty">还没有可对比的回测结果。</div> : null}
      </section>
    </>
  );
}
