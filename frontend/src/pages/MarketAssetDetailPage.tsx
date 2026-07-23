import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { apiRequest, MarketBoardRow } from "../lib/api";
import { LineChart } from "../ui/LineChart";
import { PageHeader } from "../ui/PageHeader";

const timeframeOptions = [
  { key: "intraday", label: "分时" },
  { key: "day", label: "日" },
  { key: "week", label: "周" },
  { key: "month", label: "月" }
];

export function MarketAssetDetailPage() {
  const { assetId } = useParams();
  const [timeframe, setTimeframe] = useState("intraday");
  const [row, setRow] = useState<MarketBoardRow | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      if (!assetId) {
        return;
      }
      setLoading(true);
      setError("");
      try {
        const data = await apiRequest<MarketBoardRow>(`/api/market-board/assets/${assetId}/history?timeframe=${timeframe}&limit=120`);
        setRow(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "加载资产行情失败");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [assetId, timeframe]);

  const firstPrice = row?.history[0]?.price ?? row?.latest_quote?.price ?? 0;
  const lastPrice = row?.latest_quote?.price ?? row?.history[row.history.length - 1]?.price ?? 0;
  const priceChange = firstPrice ? lastPrice - firstPrice : 0;
  const percentChange = firstPrice ? priceChange / firstPrice : 0;
  const positive = priceChange >= 0;

  return (
    <>
      <PageHeader title={row ? `${row.asset.symbol} 行情` : "资产行情"} subtitle="按分时、日、周、月查看已保存的报价走势。">
        <Link className="button" to="/market-board">
          返回看板
        </Link>
      </PageHeader>

      <div className="timeframe-tabs">
        {timeframeOptions.map((option) => (
          <button
            className={option.key === timeframe ? "active" : ""}
            key={option.key}
            type="button"
            onClick={() => setTimeframe(option.key)}
          >
            {option.label}
          </button>
        ))}
      </div>

      {error ? <div className="error-text">{error}</div> : null}

      <section className="chart-panel">
        <div className="quote-hero">
          <div>
            <div className={positive ? "quote-price positive" : "quote-price negative"}>
              {row?.latest_quote ? row.latest_quote.price.toFixed(2) : loading ? "加载中..." : "-"}
              <span>{row?.latest_quote?.currency ?? ""}</span>
            </div>
            <div className={positive ? "quote-change positive" : "quote-change negative"}>
              {row?.history.length ? `${priceChange >= 0 ? "+" : ""}${priceChange.toFixed(2)} · ${(percentChange * 100).toFixed(2)}%` : "等待更多报价"}
            </div>
            <div className="market-meta">
              {row?.latest_quote ? `交易时间 ${new Date(row.latest_quote.quote_time).toLocaleString()}` : ""}
            </div>
          </div>
          <div className="quote-side">
            <strong>{row?.asset.symbol ?? "-"}</strong>
            <span>{row?.asset.name || row?.asset.exchange || ""}</span>
            {row?.market_status ? (
              <span className={row.market_status.is_open ? "status-pill open" : "status-pill closed"}>
                {row.market_status.market} · {row.market_status.is_open ? "开盘" : "休市"}
              </span>
            ) : null}
          </div>
        </div>
        {row ? <LineChart points={row.history} height={320} /> : <div className="chart-empty">正在加载行情</div>}
      </section>
    </>
  );
}
