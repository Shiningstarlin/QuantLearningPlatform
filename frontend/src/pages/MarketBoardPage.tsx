import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { apiRequest, MarketBoardRow } from "../lib/api";
import { LineChart } from "../ui/LineChart";
import { PageHeader } from "../ui/PageHeader";

const QUOTE_REFRESH_INTERVAL_MS = 60_000;

export function MarketBoardPage() {
  const [rows, setRows] = useState<MarketBoardRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [feedHealthy, setFeedHealthy] = useState<boolean | null>(null);
  const [latestQuoteAge, setLatestQuoteAge] = useState<number | null>(null);
  const latestQuoteTimeRef = useRef<number | null>(null);
  const allMarketsClosedRef = useRef(false);

  function refreshQuoteAge(currentTime = Date.now()) {
    if (allMarketsClosedRef.current) {
      return;
    }
    const latestQuoteTime = latestQuoteTimeRef.current;
    setLatestQuoteAge(latestQuoteTime === null ? null : quoteAgeSecondsFromTimestamp(latestQuoteTime, currentTime));
  }

  async function loadQuotes(showLoading = false) {
    if (showLoading) {
      setLoading(true);
    }
    setError("");
    try {
      const data = await apiRequest<MarketBoardRow[]>("/api/market-board/quotes?limit=40");
      setRows(data);
      const allMarketsClosed = areAllMarketsClosed(data);
      allMarketsClosedRef.current = allMarketsClosed;
      if (!allMarketsClosed) {
        const latestQuoteTime = latestQuoteTimestamp(data);
        if (latestQuoteTime !== null) {
          latestQuoteTimeRef.current = latestQuoteTime;
        }
        refreshQuoteAge();
      }
      setFeedHealthy(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载行情失败");
      setFeedHealthy(false);
      refreshQuoteAge();
    } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    loadQuotes(true);
    const refreshTimer = window.setInterval(() => loadQuotes(false), QUOTE_REFRESH_INTERVAL_MS);
    return () => {
      window.clearInterval(refreshTimer);
    };
  }, []);

  const allMarketsClosed = areAllMarketsClosed(rows);
  const feedStatus = feedHealthy === false ? "error" : feedHealthy === true ? "healthy" : "pending";

  return (
    <>
      <PageHeader title="行情看板" subtitle="读取后台已保存报价；后台任务会定期拉取 Futu OpenAPI 并写入数据库。">
        <div className={`market-feed-status ${feedStatus}`} aria-live="polite">
          <span className="breathing-light" aria-hidden="true" />
          <span>
            {feedHealthy === false ? "后端通信异常" : feedHealthy === true ? "后端通信正常" : "正在连接行情服务"}
          </span>
          <strong>
            {latestQuoteAge === null
              ? allMarketsClosed
                ? "全部资产休市，暂无报价状态"
                : "暂无报价时间"
              : allMarketsClosed
                ? `休市中，保持上次更新 · ${formatQuoteAge(latestQuoteAge)}`
                : `最新报价延迟 ${formatQuoteAge(latestQuoteAge)}`}
          </strong>
        </div>
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
              <span>
                {row.latest_quote ? (
                  <>
                    更新于 {formatQuoteTime(row.latest_quote.quote_time)}
                  </>
                ) : (
                  "暂无保存报价"
                )}
              </span>
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

function areAllMarketsClosed(rows: MarketBoardRow[]) {
  return rows.length > 0 && rows.every((row) => row.market_status?.is_open === false);
}

function latestQuoteTimestamp(rows: MarketBoardRow[]) {
  return rows.reduce<number | null>((latest, row) => {
    if (!row.latest_quote) {
      return latest;
    }
    const timestamp = parseQuoteTime(row.latest_quote.quote_time).getTime();
    if (Number.isNaN(timestamp)) {
      return latest;
    }
    return latest === null ? timestamp : Math.max(latest, timestamp);
  }, null);
}

function quoteAgeSecondsFromTimestamp(timestamp: number, currentTime: number) {
  return Math.max(0, Math.floor((currentTime - timestamp) / 1000));
}

function parseQuoteTime(value: string) {
  const hasTimezone = /[zZ]|[+-]\d{2}:?\d{2}$/.test(value);
  return new Date(hasTimezone ? value : `${value}Z`);
}

function formatQuoteTime(value: string) {
  const date = parseQuoteTime(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function formatQuoteAge(age: number | null) {
  if (age === null) {
    return "--";
  }
  return `${age} 秒`;
}
