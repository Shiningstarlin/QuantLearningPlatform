import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { apiRequest, WatchAsset } from "../lib/api";
import { PageHeader } from "../ui/PageHeader";

export function AssetsPage() {
  const { taskId } = useParams();
  const [assets, setAssets] = useState<WatchAsset[]>([]);
  const [symbol, setSymbol] = useState("");
  const [assetType, setAssetType] = useState("stock");
  const [error, setError] = useState("");

  async function loadAssets() {
    if (!taskId) return;
    setAssets(await apiRequest<WatchAsset[]>(`/api/tasks/${taskId}/assets`));
  }

  async function addAsset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!taskId || !symbol.trim()) return;
    setError("");
    try {
      await apiRequest<WatchAsset>(`/api/tasks/${taskId}/assets`, {
        method: "POST",
        body: JSON.stringify({ symbol: symbol.trim(), asset_type: assetType })
      });
      setSymbol("");
      await loadAssets();
    } catch (err) {
      setError(err instanceof Error ? err.message : "添加资产失败");
    }
  }

  useEffect(() => {
    loadAssets().catch((err) => setError(err instanceof Error ? err.message : "加载资产失败"));
  }, [taskId]);

  return (
    <>
      <PageHeader title="关注资产" subtitle="当前模拟任务绑定和关注的产品。">
        <Link className="button" to={`/tasks/${taskId}`}>
          返回任务
        </Link>
      </PageHeader>
      <form className="form-panel compact" onSubmit={addAsset}>
        <div className="form-row">
          <input value={symbol} onChange={(event) => setSymbol(event.target.value)} placeholder="AAPL / SPY / BTC-USD" />
          <select value={assetType} onChange={(event) => setAssetType(event.target.value)}>
            <option value="stock">股票</option>
            <option value="etf">ETF</option>
            <option value="future">期货</option>
            <option value="forex">外汇</option>
            <option value="crypto">加密货币</option>
          </select>
          <button className="button primary" type="submit">
            添加
          </button>
        </div>
      </form>
      {error ? <div className="error-text">{error}</div> : null}
      <section className="task-list">
        {assets.map((asset) => (
          <div className="task-row" key={asset.id}>
            <div>
              <strong>{asset.symbol}</strong>
              <span>{asset.asset_type}</span>
            </div>
            <div>{asset.exchange || "-"}</div>
            <div>{asset.enabled ? "启用" : "停用"}</div>
          </div>
        ))}
      </section>
    </>
  );
}
