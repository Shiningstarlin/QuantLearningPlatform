import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { apiRequest, BacktestAsset, BacktestBatch, BacktestPreview, BacktestRun } from "../lib/api";
import { LineChart } from "../ui/LineChart";
import { PageHeader } from "../ui/PageHeader";

const STRATEGIES = [
  { key: "ma_crossover", name: "均线交叉", description: "用快慢均线交叉判断趋势切换。" },
  { key: "rsi_reversal", name: "RSI 反转", description: "在超卖回升时买入，过热时卖出。" },
  { key: "dca", name: "定投", description: "按固定间隔投入固定金额。" }
];

export function NewBacktestPage() {
  const navigate = useNavigate();
  const [assets, setAssets] = useState<BacktestAsset[]>([]);
  const [assetKey, setAssetKey] = useState("");
  const [name, setName] = useState("");
  const [strategyKeys, setStrategyKeys] = useState<string[]>([]);
  const [startDate, setStartDate] = useState("2023-01-01");
  const [endDate, setEndDate] = useState("2023-12-31");
  const [initialCash, setInitialCash] = useState("100000");
  const [taxRate, setTaxRate] = useState("0.001");
  const [commissionRate, setCommissionRate] = useState("0.0003");
  const [slippageRate, setSlippageRate] = useState("0.0005");
  const [tPlusOneEnabled, setTPlusOneEnabled] = useState(true);
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<BacktestPreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");
  const [error, setError] = useState("");
  const selectedAsset = assets.find((asset) => asset.key === assetKey);
  const currency = preview?.currency ?? selectedAsset?.currency ?? "USD";

  useEffect(() => {
    apiRequest<BacktestAsset[]>("/api/backtests/assets")
      .then((data) => {
        setAssets(data);
        if (data[0]) {
          setAssetKey(data[0].key);
          setName(`${data[0].name || data[0].symbol} 策略回测`);
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : "加载回测标的失败"));
  }, []);

  useEffect(() => {
    if (!selectedAsset || !startDate || !endDate) {
      setPreview(null);
      return;
    }

    const timer = window.setTimeout(() => {
      const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate
      });
      if (selectedAsset.market_asset_id) {
        params.set("market_asset_id", String(selectedAsset.market_asset_id));
      } else {
        params.set("yfinance_symbol", selectedAsset.yfinance_symbol);
      }

      setPreviewLoading(true);
      setPreviewError("");
      apiRequest<BacktestPreview>(`/api/backtests/preview?${params.toString()}`)
        .then(setPreview)
        .catch((err) => {
          setPreview(null);
          setPreviewError(err instanceof Error ? err.message : "加载历史价格预览失败");
        })
        .finally(() => setPreviewLoading(false));
    }, 450);

    return () => window.clearTimeout(timer);
  }, [selectedAsset, startDate, endDate]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedAsset) {
      setError("请选择一个回测标的。");
      return;
    }
    if (strategyKeys.length === 0) {
      setError("请至少选择一个策略模板。");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const basePayload = {
        name,
        market_asset_id: selectedAsset.market_asset_id ?? undefined,
        yfinance_symbol: selectedAsset.market_asset_id ? undefined : selectedAsset.yfinance_symbol,
        start_date: startDate,
        end_date: endDate,
        initial_cash: Number(initialCash),
        tax_rate: Number(taxRate),
        commission_rate: Number(commissionRate),
        slippage_rate: Number(slippageRate),
        t_plus_one_enabled: tPlusOneEnabled
      };

      if (strategyKeys.length > 1) {
        const batch = await apiRequest<BacktestBatch>("/api/backtests/batch", {
          method: "POST",
          body: JSON.stringify({
            ...basePayload,
            strategy_keys: strategyKeys
          })
        });
        const firstRun = batch.runs[0];
        navigate(firstRun ? `/backtests/${firstRun.id}` : "/backtests");
        return;
      }

      const run = await apiRequest<BacktestRun>("/api/backtests", {
        method: "POST",
        body: JSON.stringify({
          ...basePayload,
          strategy_key: strategyKeys[0]
        })
      });
      navigate(`/backtests/${run.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建策略回测失败");
    } finally {
      setLoading(false);
    }
  }

  function toggleStrategy(strategyKey: string) {
    setStrategyKeys((current) => {
      if (current.includes(strategyKey)) {
        return current.filter((key) => key !== strategyKey);
      }
      return [...current, strategyKey];
    });
  }

  const previewPoints = (preview?.points ?? []).map((point) => ({
    price: point.close_price,
    quote_time: point.point_date
  }));

  return (
    <>
      <PageHeader title="新建策略回测" subtitle="使用 yfinance 历史行情数据，复盘某段时间内策略会如何交易。">
        <Link className="button" to="/backtests">
          返回策略回测
        </Link>
      </PageHeader>

      <form className="form-panel" onSubmit={handleSubmit}>
        <label>
          回测标的
          <select
            value={assetKey}
            onChange={(event) => {
              const nextKey = event.target.value;
              setAssetKey(nextKey);
              const nextAsset = assets.find((asset) => asset.key === nextKey);
              if (nextAsset) {
                setName(`${nextAsset.name || nextAsset.symbol} 策略回测`);
              }
            }}
            required
          >
            {assets.map((asset) => (
              <option value={asset.key} key={asset.key}>
                {asset.name} · {asset.symbol} · yfinance: {asset.yfinance_symbol}
              </option>
            ))}
          </select>
        </label>
        {assets.length === 0 ? (
          <div className="empty-state compact-empty">
            当前没有可回测标的。请检查后端回测标的配置，或确认行情看板默认标的已同步。
          </div>
        ) : null}
        <label>
          回测名称
          <input value={name} onChange={(event) => setName(event.target.value)} required />
        </label>
        <div className="strategy-picker">
          策略模板
          <div className="strategy-options">
            {STRATEGIES.map((strategy) => (
              <label className="strategy-option" key={strategy.key}>
                <input
                  type="checkbox"
                  checked={strategyKeys.includes(strategy.key)}
                  onChange={() => toggleStrategy(strategy.key)}
                />
                <span>
                  <strong>{strategy.name}</strong>
                  <small>{strategy.description}</small>
                </span>
              </label>
            ))}
          </div>
        </div>
        <div className="form-row">
          <label>
            起始日
            <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} required />
          </label>
          <label>
            结束日
            <input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} required />
          </label>
          <label>
            起始资金
            <div className="input-with-unit">
              <input type="number" min="1" value={initialCash} onChange={(event) => setInitialCash(event.target.value)} required />
              <span>{currency}</span>
            </div>
          </label>
        </div>

        <section className="preview-panel">
          <div className="chart-panel-header">
            <div>
              <strong>标的价格预览</strong>
              <span>{selectedAsset ? `${selectedAsset.name} · ${startDate} 至 ${endDate}` : "选择标的后预览历史价格"}</span>
            </div>
            <div className="price">
              {preview?.asset_metrics ? `区间涨跌 ${(preview.asset_metrics.raw_return * 100).toFixed(2)}%` : ""}
            </div>
          </div>
          {previewLoading ? <div className="chart-empty">正在加载历史价格...</div> : <LineChart points={previewPoints} />}
          {previewError ? <div className="error-text">{previewError}</div> : null}
        </section>

        <div className="form-row">
          <label>
            税率
            <input type="number" step="0.0001" value={taxRate} onChange={(event) => setTaxRate(event.target.value)} />
          </label>
          <label>
            手续费率
            <input type="number" step="0.0001" value={commissionRate} onChange={(event) => setCommissionRate(event.target.value)} />
          </label>
          <label>
            滑点率
            <input type="number" step="0.0001" value={slippageRate} onChange={(event) => setSlippageRate(event.target.value)} />
          </label>
        </div>
        <label className="checkbox-label">
          <input type="checkbox" checked={tPlusOneEnabled} onChange={(event) => setTPlusOneEnabled(event.target.checked)} />
          启用 T+1 限制
        </label>
        {error ? <div className="error-text">{error}</div> : null}
        <button className="button primary" type="submit" disabled={loading || assets.length === 0 || strategyKeys.length === 0}>
          {loading ? "正在计算..." : strategyKeys.length > 1 ? "运行并对比策略" : "开始策略回测"}
        </button>
      </form>
    </>
  );
}
