import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { apiRequest, BacktestTask } from "../lib/api";
import { PageHeader } from "../ui/PageHeader";

function statusLabel(status: string) {
  if (status === "completed") return "已完成";
  if (status === "failed") return "失败";
  if (status === "pending") return "计算中";
  return status;
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(2)}%`;
}

function BacktestEmptyDemo() {
  const strategyNotes = [
    {
      name: "定投",
      className: "dca",
      result: "+13.08%",
      formula: "每月投入 = 起始资金 × 8%，持仓比例随时间累积。",
      example: "不判断高低点。在 1 月、3 月、6 月、9 月固定买入，用纪律换取较低择时压力。",
      events: [
        { date: "2025-01-15", x: 72, y: 141, side: "buy", quantity: "18 股", reason: "月度定额投入" },
        { date: "2025-03-17", x: 132, y: 96, side: "buy", quantity: "16 股", reason: "月度定额投入" },
        { date: "2025-06-16", x: 254, y: 74, side: "buy", quantity: "14 股", reason: "月度定额投入" },
        { date: "2025-09-15", x: 382, y: 50, side: "buy", quantity: "12 股", reason: "月度定额投入" }
      ]
    },
    {
      name: "技术回溯",
      className: "technical",
      result: "+18.42%",
      formula: "买入：MA20 上穿 MA60 且 RSI < 70；卖出：MA20 下穿 MA60 或 RSI > 78。",
      example: "在回调后趋势重新向上时买入，在短期过热或趋势走弱时减仓。",
      events: [
        { date: "2025-02-21", x: 104, y: 130, side: "buy", quantity: "42 股", reason: "MA20 上穿 MA60" },
        { date: "2025-09-19", x: 388, y: 45, side: "sell", quantity: "28 股", reason: "RSI > 78" },
        { date: "2025-10-24", x: 456, y: 62, side: "buy", quantity: "19 股", reason: "趋势恢复" }
      ]
    },
    {
      name: "信息因子 AI",
      className: "factor",
      result: "+26.54%",
      formula: "综合分 = 0.45 × 新闻情绪 + 0.35 × 财报因子 + 0.20 × 市场热度。",
      example: "例如财报指引上调、产业新闻偏正面时提高仓位；重大监管或负面舆情出现时降低暴露。",
      events: [
        { date: "2025-04-30", x: 196, y: 92, side: "buy", quantity: "24 股", reason: "财报指引上调" },
        { date: "2025-07-31", x: 318, y: 76, side: "buy", quantity: "18 股", reason: "产业新闻偏正面" },
        { date: "2025-10-10", x: 430, y: 72, side: "sell", quantity: "15 股", reason: "负面舆情降仓" }
      ]
    }
  ];
  const rawAssetChangeRate = "+21.76%";
  const eventMarkers = strategyNotes.flatMap((strategy) =>
    strategy.events.map((event) => ({
      ...event,
      strategy: strategy.className,
      strategyName: strategy.name,
      label: `${strategy.name} · ${event.date} · ${event.side === "buy" ? "买入" : "卖出"} ${event.quantity} · ${event.reason}`
    }))
  );

  const [hoveredMarker, setHoveredMarker] = useState<(typeof eventMarkers)[number] | null>(null);

  return (
    <section className="empty-demo-panel backtest-empty-demo">
      <div className="empty-demo-copy">
        <span className="eyebrow simulation-label">策略回测演示</span>
        <h2>先看看策略如何影响买卖决策</h2>
        <p>这是一个可交互的示例：在同一段行情中对比定投、技术信号和信息因子三种策略。把鼠标移到图表节点上，即可查看每次买入或卖出的原因。</p>
      </div>

      <div className="demo-comparison-layout">
        <div className="demo-chart-frame strategy-comparison-chart">
          <div className="demo-board-header">
            <div>
              <span className="simulation-label">示例行情 · US.NVDA · 2025</span>
              <strong>悬停买卖节点，查看策略判断</strong>
            </div>
            <div className="demo-benchmark-stat">
              <span>资产价格原始变化率</span>
              <strong>{rawAssetChangeRate}</strong>
              <small>仅持有资产的价格变化</small>
            </div>
            <span className="demo-interaction-hint">移入节点查看详情</span>
          </div>

            <div className="demo-chart-stage">
            <svg viewBox="0 0 620 260" role="img" aria-label="策略示例价格走势与交易节点">
              <path className="demo-grid" d="M56 38H594 M56 76H594 M56 114H594 M56 152H594 M56 190H594" />
              <path className="demo-axis" d="M56 28V214H594" />
              <text className="demo-axis-label" x="16" y="42">240</text>
              <text className="demo-axis-label" x="16" y="80">220</text>
              <text className="demo-axis-label" x="16" y="118">200</text>
              <text className="demo-axis-label" x="16" y="156">180</text>
              <text className="demo-axis-label" x="16" y="194">160</text>
              <text className="demo-axis-label unit" x="16" y="22">USD</text>
              <text className="demo-axis-label" x="70" y="240">1月</text>
              <text className="demo-axis-label" x="176" y="240">3月</text>
              <text className="demo-axis-label" x="282" y="240">6月</text>
              <text className="demo-axis-label" x="422" y="240">9月</text>
              <text className="demo-axis-label" x="552" y="240">12月</text>
              <path className="demo-price-area" d="M56 146 L72 141 L104 130 L132 96 L166 124 L196 92 L254 74 L318 76 L382 50 L430 72 L456 62 L520 42 L594 34 L594 214 L56 214 Z" />
              <path className="demo-price-line" d="M56 146 L72 141 L104 130 L132 96 L166 124 L196 92 L254 74 L318 76 L382 50 L430 72 L456 62 L520 42 L594 34" />
              {eventMarkers.map((marker, index) => (
                <g
                  className={`demo-event-marker ${marker.strategy} ${marker.side}`}
                  key={`${marker.strategy}-${marker.side}-${index}`}
                  tabIndex={0}
                  role="button"
                  aria-label={marker.label}
                  onMouseEnter={() => setHoveredMarker(marker)}
                  onMouseMove={() => setHoveredMarker(marker)}
                  onMouseLeave={() => setHoveredMarker(null)}
                  onFocus={() => setHoveredMarker(marker)}
                  onBlur={() => setHoveredMarker(null)}
                >
                  <circle className="marker-halo" cx={marker.x} cy={marker.y} r="11" />
                  <circle className="marker-core" cx={marker.x} cy={marker.y} r="6" />
                  {marker.side === "buy" ? (
                    <path className="marker-direction" d={`M ${marker.x} ${marker.y - 15} l -6 9 h 12 z`} />
                  ) : (
                    <path className="marker-direction" d={`M ${marker.x} ${marker.y + 15} l -6 -9 h 12 z`} />
                  )}
                </g>
              ))}
            </svg>
            {hoveredMarker ? (
              <div
                className={`demo-marker-tooltip ${hoveredMarker.side}`}
                style={{
                  left: `${Math.min(Math.max((hoveredMarker.x / 620) * 100 + 2, 4), 70)}%`,
                  top: `${Math.min(Math.max((hoveredMarker.y / 260) * 100 + 8, 12), 82)}%`
                }}
              >
                <strong>{hoveredMarker.side === "buy" ? "买入" : "卖出"} · {hoveredMarker.strategyName}</strong>
                <span>{hoveredMarker.date} · {hoveredMarker.quantity}</span>
                <small>{hoveredMarker.reason}</small>
              </div>
            ) : null}
            </div>
            <div className="demo-chart-legend" aria-hidden="true">
              <span><i className="legend-dot dca" />定投</span>
              <span><i className="legend-dot technical" />技术回溯</span>
              <span><i className="legend-dot factor" />信息因子 AI</span>
              <span><i className="legend-arrow buy" />向上：买入</span>
              <span><i className="legend-arrow sell" />向下：卖出</span>
            </div>
        </div>

        <div className="demo-strategy-grid">
            {strategyNotes.map((strategy) => (
            <div className={`demo-strategy-card ${strategy.className}`} key={strategy.name}>
              <div className="demo-strategy-copy">
                <span>{strategy.name}</span>
                <strong>{strategy.result}</strong>
                <small>{strategy.formula}</small>
              </div>
              <p>{strategy.example}</p>
              <div className="demo-event-list">
                {strategy.events.map((event) => (
                  <div key={`${strategy.name}-${event.date}`}>
                    <span>{event.date}</span>
                    <strong>{event.side === "buy" ? "买入" : "卖出"} {event.quantity}</strong>
                    <small>{event.reason}</small>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export function BacktestsPage() {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState<BacktestTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    apiRequest<BacktestTask[]>("/api/backtests")
      .then(setTasks)
      .catch((err) => setError(err instanceof Error ? err.message : "加载策略回测失败"))
      .finally(() => setLoading(false));
  }, []);

  function handleNewBacktest() {
    navigate("/backtests/new");
  }

  return (
    <>
      <PageHeader title="策略回测" subtitle="选择标的、策略和时间区间，复盘一段历史市场中的模拟交易。">
        <button className="button primary" type="button" onClick={handleNewBacktest}>
          新建策略回测
        </button>
      </PageHeader>

      {error ? <div className="error-text">{error}</div> : null}
      {loading ? <div className="empty-state">正在加载策略回测...</div> : null}
      {!loading && !error && tasks.length === 0 ? (
        <>
          <div className="empty-state">还没有策略回测记录。点击“新建策略回测”开始一次实验。</div>
          <BacktestEmptyDemo />
        </>
      ) : null}

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
