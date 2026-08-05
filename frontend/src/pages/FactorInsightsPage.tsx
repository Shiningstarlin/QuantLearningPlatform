import { ExternalLink, RefreshCw, Sparkles } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { apiRequest, FactorInsights, InsightFactor, MarketBoardRow, InsightScore, OverallInsightScore } from "../lib/api";
import { PageHeader } from "../ui/PageHeader";

export function FactorInsightsPage() {
  const [searchParams] = useSearchParams();
  const [rows, setRows] = useState<MarketBoardRow[]>([]);
  const [assetId, setAssetId] = useState(searchParams.get("assetId") ?? "");
  const [insights, setInsights] = useState<FactorInsights | null>(null);
  const [loadingAssets, setLoadingAssets] = useState(true);
  const [loadingInsights, setLoadingInsights] = useState(false);
  const [showAllFactors, setShowAllFactors] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    apiRequest<MarketBoardRow[]>("/api/market-board/quotes?limit=120")
      .then((data) => {
        setRows(data);
        const requestedId = searchParams.get("assetId");
        const requestedExists = requestedId && data.some((row) => String(row.asset.id) === requestedId);
        setAssetId(requestedExists ? requestedId : data[0] ? String(data[0].asset.id) : "");
      })
      .catch((err) => setError(err instanceof Error ? err.message : "无法读取行情看板资产"))
      .finally(() => setLoadingAssets(false));
  }, [searchParams]);

  async function loadInsights(event?: FormEvent) {
    event?.preventDefault();
    if (!assetId) {
      setError("请先选择一个行情看板资产。");
      return;
    }
    setLoadingInsights(true);
    setError("");
    setShowAllFactors(false);
    try {
      const data = await apiRequest<FactorInsights>(`/api/market-board/assets/${assetId}/insights`);
      setInsights(data);
      if (data.overall.status === "error") {
        setError(userFacingError(data.overall.summary || "AI 评估请求失败"));
      }
    } catch (err) {
      setError(userFacingError(err));
    } finally {
      setLoadingInsights(false);
    }
  }

  const selectedAsset = useMemo(() => rows.find((row) => String(row.asset.id) === assetId)?.asset, [rows, assetId]);

  return (
    <>
      <PageHeader title="因子雷达" subtitle="从行情看板资产出发，汇总量化因子、财报、宏观指标、市场情绪与相关新闻。">
      </PageHeader>

      <form className="insight-control-panel" onSubmit={loadInsights}>
        <label>
          <span>行情看板资产</span>
          <select value={assetId} onChange={(event) => setAssetId(event.target.value)} disabled={loadingAssets}>
            {!rows.length ? <option value="">{loadingAssets ? "正在读取资产…" : "暂无可用资产"}</option> : null}
            {rows.map((row) => (
              <option key={row.asset.id} value={row.asset.id}>
                {row.asset.symbol} {row.asset.name ? `· ${row.asset.name}` : ""}
              </option>
            ))}
          </select>
        </label>
        <button className="button primary" type="submit" disabled={loadingInsights || !assetId}>
          {loadingInsights ? <RefreshCw className="spin-icon" size={16} /> : <Sparkles size={16} />}
          {loadingInsights ? "正在分析…" : "查询并评估"}
        </button>
      </form>

      {error ? <div className="error-text">{error}</div> : null}

      {insights ? (
        <>
          <section className="insight-hero-panel">
            <div>
              <span className="eyebrow">研究对象</span>
              <h2>
                {insights.asset.symbol} <small>{insights.asset.name || selectedAsset?.exchange || ""}</small>
              </h2>
              <p>
                数据区间 {insights.start_date} 至 {insights.end_date} · 数据源 Futu OpenAPI
              </p>
            </div>
            <ScoreCard label="综合 AI 评估" score={insights.overall} scale="overall" />
          </section>

          <section className="insight-score-grid">
            <ScoreCard label="量化 / 财务 / 宏观因子" score={averageFactorScore(insights.factors)} />
            <ScoreCard label="市场情绪代理" score={insights.market_sentiment.ai} />
            <ScoreCard label="资产相关新闻" score={insights.asset_news.ai} />
          </section>

          <section className="insight-panel">
            <div className="insight-panel-heading">
              <div>
                <span className="eyebrow">因子观测</span>
                <h2>量化与基本面数据</h2>
              </div>
              <span>{insights.factors.length} 项</span>
            </div>
            {insights.factors.length ? (
              <>
                <div className="factor-table">
                  {(showAllFactors ? insights.factors : insights.factors.slice(0, 5)).map((factor) => (
                    <FactorRow key={factor.key} factor={factor} />
                  ))}
                </div>
                {insights.factors.length > 5 ? (
                  <button
                    className="button subtle-button factor-expand-button"
                    type="button"
                    onClick={() => setShowAllFactors((value) => !value)}
                  >
                    {showAllFactors ? "收起因子" : `展开其余 ${insights.factors.length - 5} 项`}
                  </button>
                ) : null}
              </>
            ) : (
              <div className="insight-empty">当前区间没有可用因子数据。</div>
            )}
          </section>

          <section className="insight-split-grid">
            <SentimentPanel insights={insights} />
            <NewsPanel insights={insights} />
          </section>

          {insights.warnings.length ? (
            <section className="insight-warning-panel">
              <strong>数据提示</strong>
              {insights.warnings.map((warning) => <span key={warning}>{warning}</span>)}
            </section>
          ) : null}
        </>
      ) : (
        <section className="insight-empty-state">
          <Sparkles size={30} />
          <h2>{loadingInsights ? "正在构建因子情报…" : "选择资产开始查询"}</h2>
          <p>查询默认覆盖最近 7 天，结果生成后会展示因子观测、市场情绪和相关新闻。</p>
        </section>
      )}
    </>
  );
}

function ScoreCard({ label, score, scale = "single" }: { label: string; score: InsightScore | OverallInsightScore | null; scale?: ScoreScale }) {
  const value = score?.score;
  return (
    <article className={`insight-score-card ${scoreTone(value, scale)}`}>
      <span>{label}</span>
      <strong>{value === null || value === undefined ? "--" : formatScore(value, scale)}</strong>
      {scale === "single" ? <SingleScoreGrid score={value} /> : <OverallScoreLine score={value} />}
      <small>{scoreStatus(score)}</small>
    </article>
  );
}

function SingleScoreGrid({ score }: { score: number | null | undefined }) {
  const normalized = score === null || score === undefined ? null : Math.max(-10, Math.min(10, Math.round(score)));
  const values = Array.from({ length: 21 }, (_, index) => index - 10);
  const direction = normalized === null ? "neutral" : normalized > 0 ? "positive" : normalized < 0 ? "negative" : "neutral";

  return (
    <div
      className="single-score-grid"
      role="meter"
      aria-label="单项评分刻度"
      aria-valuemin={-10}
      aria-valuemax={10}
      aria-valuenow={normalized ?? undefined}
    >
      {values.map((value) => {
        const filled = normalized !== null && (
          normalized > 0 ? value >= 0 && value <= normalized :
          normalized < 0 ? value <= 0 && value >= normalized :
          value === 0
        );
        const active = normalized === value;
        return (
          <span
            className={`score-cell ${direction} ${filled ? "filled" : ""} ${active ? "active" : ""}`}
            key={value}
            title={`单项评分 ${value >= 0 ? "+" : ""}${value}`}
          />
        );
      })}
    </div>
  );
}

function OverallScoreLine({ score }: { score: number | null | undefined }) {
  const normalized = score === null || score === undefined ? null : Math.max(-1, Math.min(1, score));
  const markerPosition = normalized === null ? undefined : `${((normalized + 1) / 2) * 100}%`;

  return (
    <div className="overall-score-line-wrap">
      <div
        className="overall-score-line"
        role="meter"
        aria-label="综合评分刻度"
        aria-valuemin={-1}
        aria-valuemax={1}
        aria-valuenow={normalized ?? undefined}
      >
        {markerPosition ? <span className="overall-score-marker" style={{ left: markerPosition }} /> : null}
      </div>
      <div className="overall-score-line-labels" aria-hidden="true">
        <span>-1</span>
        <span>0</span>
        <span>1</span>
      </div>
    </div>
  );
}

function FactorRow({ factor }: { factor: InsightFactor }) {
  return (
    <div className="factor-row">
      <div className="factor-main">
        <strong>{factor.label}</strong>
        <span>{categoryLabel(factor.category)} · {factor.source}</span>
      </div>
      <div className="factor-value">
        <strong>{formatValue(factor.value, factor.unit)}</strong>
        <span>{factor.observed_at || factor.period || "当前快照"}</span>
      </div>
      <div className={`factor-ai-score ${scoreTone(factor.ai.score, "single")}`}>
        <span>AI</span>
        <strong>{factor.ai.score === null ? "--" : formatScore(factor.ai.score, "single")}</strong>
        <SingleScoreGrid score={factor.ai.score} />
      </div>
      <div className="factor-note">{factor.ai.summary || factor.note || "等待评估"}</div>
    </div>
  );
}

function SentimentPanel({ insights }: { insights: FactorInsights }) {
  return (
    <section className="insight-panel split-panel">
      <div className="insight-panel-heading">
        <div>
          <span className="eyebrow">AI 分屏 01</span>
          <h2>{insights.market_sentiment.title}</h2>
        </div>
        <strong className={`inline-score ${scoreTone(insights.market_sentiment.ai.score, "single")}`}>
          {insights.market_sentiment.ai.score === null ? "--" : formatScore(insights.market_sentiment.ai.score, "single")}
        </strong>
      </div>
      <SingleScoreGrid score={insights.market_sentiment.ai.score} />
      <p className="panel-caption">{insights.market_sentiment.source}；Futu 暂无独立情绪指数，这里使用热度变化做代理。</p>
      <div className="mini-factor-list">
        {insights.market_sentiment.indicators.length ? insights.market_sentiment.indicators.map((factor) => (
          <div key={factor.key}><span>{factor.label}</span><strong>{formatValue(factor.value, factor.unit)}</strong></div>
        )) : <div className="insight-empty">热议榜暂未返回该资产。</div>}
      </div>
      <ScoreMessage score={insights.market_sentiment.ai} />
    </section>
  );
}

function NewsPanel({ insights }: { insights: FactorInsights }) {
  return (
    <section className="insight-panel split-panel">
      <div className="insight-panel-heading">
        <div>
          <span className="eyebrow">AI 分屏 02</span>
          <h2>{insights.asset_news.title}</h2>
        </div>
        <strong className={`inline-score ${scoreTone(insights.asset_news.ai.score, "single")}`}>
          {insights.asset_news.ai.score === null ? "--" : formatScore(insights.asset_news.ai.score, "single")}
        </strong>
      </div>
      <SingleScoreGrid score={insights.asset_news.ai.score} />
      <p className="panel-caption">Futu get_search_news 返回新闻、公告、评级；默认按资产代码搜索。</p>
      <div className="news-list">
        {insights.asset_news.items.length ? insights.asset_news.items.map((item) => (
          <a href={item.url || undefined} target="_blank" rel="noreferrer" key={`${item.publish_time}-${item.title}`}>
            <div><strong>{item.title}</strong><span>{item.source} · {item.publish_time}</span></div>
            <ExternalLink size={15} />
          </a>
        )) : <div className="insight-empty">查询区间内没有相关新闻。</div>}
      </div>
      <ScoreMessage score={insights.asset_news.ai} />
    </section>
  );
}

function ScoreMessage({ score }: { score: InsightScore }) {
  return <p className="score-message">{score.summary || scoreStatus(score)}</p>;
}

function averageFactorScore(factors: InsightFactor[]): InsightScore {
  const scores = factors.map((factor) => factor.ai.score).filter((score): score is number => score !== null && score !== undefined);
  if (!scores.length) {
    return factors[0]?.ai ?? { score: null, status: "not_configured", summary: "评估暂不可用" };
  }
  return { score: Math.round(scores.reduce((sum, score) => sum + score, 0) / scores.length), status: "ready", summary: "各因子 AI 评估的平均值" };
}

function scoreStatus(score: InsightScore | null) {
  if (!score) return "等待评估";
  if (score.status === "ready") return "AI 已生成评估值";
  if (score.status === "not_configured") return "评估暂不可用";
  if (score.status === "error") return "评估请求失败，请联系管理员";
  return "暂无足够数据";
}

type ScoreScale = "single" | "overall";

function scoreTone(score: number | null | undefined, scale: ScoreScale = "single") {
  if (score === null || score === undefined) return "neutral";
  const threshold = scale === "overall" ? 0.1 : 1;
  return score > threshold ? "positive" : score < -threshold ? "negative" : "neutral";
}

function formatScore(score: number, scale: ScoreScale = "single") {
  return scale === "overall"
    ? `${score >= 0 ? "+" : ""}${score.toFixed(2)}`
    : `${score >= 0 ? "+" : ""}${Math.round(score)}`;
}

function formatValue(value: number | string | null, unit: string) {
  if (value === null || value === undefined || value === "") return "--";
  if (typeof value === "number") {
    const formatted = Math.abs(value) >= 1000 ? value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : value.toFixed(2);
    return `${formatted}${unit === "%" ? "%" : unit ? ` ${unit}` : ""}`;
  }
  return value;
}

function categoryLabel(category: InsightFactor["category"]) {
  return { quant: "量化", financial: "财务", macro: "宏观", flow: "资金流", earnings: "财报" }[category];
}

function userFacingError(error: unknown) {
  const reason = error instanceof Error && error.message ? error.message : "请求失败";
  return reason.includes("请联系管理员") ? reason : `${reason}。请联系管理员。`;
}
