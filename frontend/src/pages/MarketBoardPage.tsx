import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { apiRequest, MarketBoardRow } from "../lib/api";
import { LineChart } from "../ui/LineChart";
import { PageHeader } from "../ui/PageHeader";

export function MarketBoardPage() {
  const [rows, setRows] = useState<MarketBoardRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadQuotes(refresh = false) {
    setLoading(true);
    setError("");
    try {
      if (refresh) {
        await apiRequest<{ refreshed: number }>("/api/market-board/refresh", { method: "POST" });
      }
      const data = await apiRequest<MarketBoardRow[]>("/api/market-board/quotes?limit=40");
      setRows(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载行情失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadQuotes();
  }, []);

  return (
    <>
      <PageHeader title="行情看板" subtitle="仅使用 Futu OpenAPI 获取报价，后台会定期保存报价。">
        <button className="button" type="button" onClick={() => loadQuotes(true)} disabled={loading}>
          {loading ? "刷新中..." : "刷新报价"}
        </button>
      </PageHeader>

      {error ? <div className="error-text">{error}</div> : null}

      <section className="market-grid">
        {rows.map((row) => (
          <Link className="market-card market-card-link" key={`${row.asset.provider}:${row.asset.symbol}`} to={`/market-board/${row.asset.id}`}>
            <div className="market-card-header">
              <div>
                <strong>{row.asset.symbol}</strong>
                <span>
                  {row.asset.name ? `${row.asset.name} · ` : ""}
                  Futu OpenAPI
                </span>
              </div>
              <div className="price">
                {row.latest_quote ? `${row.latest_quote.price.toFixed(2)} ${row.latest_quote.currency}` : "无报价"}
              </div>
            </div>
            <LineChart points={row.history} compact height={96} />
            <div className="market-meta market-card-footer">
              <span>{row.latest_quote ? new Date(row.latest_quote.quote_time).toLocaleString() : "尚未刷新"}</span>
              {row.market_status ? (
                <span className={row.market_status.is_open ? "status-pill open" : "status-pill closed"}>
                  {row.market_status.market} · {row.market_status.is_open ? "开盘" : "休市"}
                </span>
              ) : null}
            </div>
          </Link>
        ))}
      </section>
    </>
  );
}
