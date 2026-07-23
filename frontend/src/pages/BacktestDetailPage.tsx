import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { apiRequest, BacktestDetail } from "../lib/api";
import { LineChart } from "../ui/LineChart";
import { PageHeader } from "../ui/PageHeader";

function formatPercent(value: number) {
  return `${(value * 100).toFixed(2)}%`;
}

function formatNumber(value: number) {
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function statusLabel(status?: string) {
  if (status === "completed") return "已完成";
  if (status === "failed") return "失败";
  if (status === "pending") return "运行中";
  return status ?? "-";
}

function strategyLabel(strategyKey: string) {
  if (strategyKey === "ma_crossover") return "均线交叉";
  if (strategyKey === "rsi_reversal") return "RSI 反转";
  if (strategyKey === "dca") return "定投";
  return strategyKey;
}

export function BacktestDetailPage() {
  const { backtestId } = useParams();
  const [detail, setDetail] = useState<BacktestDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!backtestId) return;
    apiRequest<BacktestDetail>(`/api/backtests/${backtestId}`)
      .then(setDetail)
      .catch((err) => setError(err instanceof Error ? err.message : "加载回测失败"));
  }, [backtestId]);

  const run = detail?.run;
  const task = detail?.task;
  const siblingRuns = detail?.sibling_runs ?? [];
  const equityPoints = detail?.equity_points ?? [];
  const trades = detail?.trades ?? [];
  const chartPoints = equityPoints.map((point) => ({
    price: point.equity,
    quote_time: point.point_date
  }));
  const assetPricePoints = equityPoints.map((point) => ({
    price: point.close_price,
    quote_time: point.point_date
  }));
  const tradeMarkers = trades.map((trade) => ({
    price: trade.price,
    quote_time: trade.traded_on,
    side: trade.side === "buy" ? ("buy" as const) : ("sell" as const),
    label: `${trade.side === "buy" ? "买入" : "卖出"} ${trade.price.toFixed(2)} · ${trade.traded_on}`
  }));
  const assetMetrics = detail?.asset_metrics;

  return (
    <>
      <PageHeader title={run?.name ?? `回测 #${backtestId}`} subtitle={run ? `${run.symbol} · ${run.provider} · ${run.start_date} 至 ${run.end_date}` : "加载中"}>
        <Link className="button" to="/backtests">
          返回回测列表
        </Link>
      </PageHeader>

      {error ? <div className="error-text">{error}</div> : null}
      {run?.status === "failed" ? <div className="error-text">{run.error_message || "回测失败"}</div> : null}

      {siblingRuns.length > 1 ? (
        <section className="run-switcher">
          <div>
            <strong>{task?.name ?? "同一回测任务"}</strong>
            <span>切换查看同一任务下的其它策略结果</span>
          </div>
          <div className="run-switcher-actions">
            {siblingRuns.map((sibling) => (
              <Link className={sibling.id === run?.id ? "button primary" : "button"} to={`/backtests/${sibling.id}`} key={sibling.id}>
                {strategyLabel(sibling.strategy_key)}
              </Link>
            ))}
          </div>
        </section>
      ) : null}

      <section className="metric-grid">
        <div className="metric-card">
          <span>状态</span>
          <strong>{statusLabel(run?.status)}</strong>
        </div>
        <div className="metric-card">
          <span>总收益率</span>
          <strong>{run ? formatPercent(run.total_return) : "-"}</strong>
        </div>
        <div className="metric-card">
          <span>期末净值</span>
          <strong>{run ? run.final_equity.toFixed(2) : "-"}</strong>
        </div>
      </section>

      <section className="chart-panel">
        <div className="chart-panel-header">
          <div>
            <strong>每日权益曲线</strong>
            <span>现金与持仓市值合计，按历史交易日记录。</span>
          </div>
          <div className="price">{run ? `最大回撤 ${formatPercent(run.max_drawdown)}` : ""}</div>
        </div>
        <LineChart points={chartPoints} />
      </section>

      <section className="chart-panel">
        <div className="chart-panel-header">
          <div>
            <strong>资产原始价格走势</strong>
            <span>只展示资产自身收盘价，并标记本次策略产生的买入与卖出点。</span>
          </div>
          <div className="price">{assetMetrics ? `原始涨跌 ${formatPercent(assetMetrics.raw_return)}` : ""}</div>
        </div>
        <LineChart points={assetPricePoints} markers={tradeMarkers} />
      </section>

      <div className="task-info-grid">
        <div className="info-block">
          <span>策略模板 / 数据源</span>
          <strong>{run ? `${strategyLabel(run.strategy_key)} / ${run.provider}` : "-"}</strong>
        </div>
        <div className="info-block">
          <span>交易次数 / 胜率</span>
          <strong>{run ? `${run.trade_count} / ${formatPercent(run.win_rate)}` : "-"}</strong>
        </div>
        <div className="info-block">
          <span>期末现金 / 持仓市值</span>
          <strong>{run ? `${run.final_cash.toFixed(2)} / ${run.final_market_value.toFixed(2)}` : "-"}</strong>
        </div>
        <div className="info-block">
          <span>资产原始价格变动</span>
          <strong>{assetMetrics ? formatPercent(assetMetrics.raw_return) : "-"}</strong>
        </div>
        <div className="info-block">
          <span>资产年化波动率</span>
          <strong>{assetMetrics ? formatPercent(assetMetrics.annualized_volatility) : "-"}</strong>
        </div>
        <div className="info-block">
          <span>资产最大回撤</span>
          <strong>{assetMetrics ? formatPercent(assetMetrics.max_drawdown) : "-"}</strong>
        </div>
        <div className="info-block">
          <span>资产区间高低点</span>
          <strong>{assetMetrics ? `${formatNumber(assetMetrics.high_price)} / ${formatNumber(assetMetrics.low_price)}` : "-"}</strong>
        </div>
      </div>

      <section className="data-table backtest-trades">
        <div className="data-row header">
          <span>日期</span>
          <span>方向</span>
          <span>数量</span>
          <span>价格</span>
          <span>净额</span>
          <span>原因</span>
        </div>
        {trades.map((trade) => (
          <div className="data-row" key={trade.id}>
            <span>{trade.traded_on}</span>
            <span>{trade.side === "buy" ? "买入" : "卖出"}</span>
            <span>{trade.quantity.toFixed(4)}</span>
            <span>{trade.price.toFixed(2)}</span>
            <span>{trade.net_amount.toFixed(2)}</span>
            <span>{trade.reason}</span>
          </div>
        ))}
        {trades.length === 0 ? <div className="empty-state compact-empty">这次回测没有产生交易。</div> : null}
      </section>
    </>
  );
}
