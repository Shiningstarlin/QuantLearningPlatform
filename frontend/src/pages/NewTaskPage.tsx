import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { apiRequest, getToken, MarketAsset, PaperAccount, SimulationFeeSchedules, SimulationTask } from "../lib/api";
import { PageHeader } from "../ui/PageHeader";

export function NewTaskPage() {
  const navigate = useNavigate();
  const [accounts, setAccounts] = useState<PaperAccount[]>([]);
  const [assets, setAssets] = useState<MarketAsset[]>([]);
  const [accountId, setAccountId] = useState("");
  const [marketAssetId, setMarketAssetId] = useState("");
  const [name, setName] = useState("");
  const [allocatedCash, setAllocatedCash] = useState("100000");
  const [mode, setMode] = useState<"manual" | "quant">("manual");
  const [strategyKey, setStrategyKey] = useState("ma_crossover");
  const [manualTargetExposure, setManualTargetExposure] = useState("0");
  const [fees, setFees] = useState<SimulationFeeSchedules | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      navigate("/login");
      return;
    }

    Promise.all([
      apiRequest<PaperAccount[]>("/api/tasks/accounts"),
      apiRequest<MarketAsset[]>("/api/market-board/assets"),
      apiRequest<SimulationFeeSchedules>("/api/tasks/fees")
    ])
      .then(([accountData, assetData, feeData]) => {
        setAccounts(accountData);
        setAssets(assetData);
        setFees(feeData);
        if (accountData[0]) setAccountId(String(accountData[0].id));
        if (assetData[0]) {
          setMarketAssetId(String(assetData[0].id));
          setName(`${assetData[0].symbol} 投资进程`);
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : "加载账户或行情资产失败"));
  }, [navigate]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accountId || !marketAssetId) {
      setError("请选择模拟账户和行情资产。");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const task = await apiRequest<SimulationTask>(`/api/tasks/accounts/${accountId}/processes`, {
        method: "POST",
        body: JSON.stringify({
          name,
          market_asset_id: Number(marketAssetId),
          allocated_cash: Number(allocatedCash),
          mode,
          strategy_key: mode === "quant" ? strategyKey : "manual",
          manual_target_exposure: mode === "manual" ? Number(manualTargetExposure) / 100 : 0
        })
      });
      navigate(`/tasks/${task.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建投资进程失败");
    } finally {
      setLoading(false);
    }
  }

  const selectedAccount = accounts.find((account) => String(account.id) === accountId);
  const selectedAsset = assets.find((asset) => String(asset.id) === marketAssetId);
  const processCount = selectedAccount?.tasks.filter((task) => task.status !== "ended").length ?? 0;
  const assetCurrency = selectedAsset?.currency ?? "HKD";
  const settlementLabel = selectedAsset ? (selectedAsset.settlement_days > 0 ? `T+${selectedAsset.settlement_days}` : "T+0") : "-";
  const feeSchedule = fees?.schedules.find((schedule) => schedule.market === selectedAsset?.exchange);

  return (
    <>
      <PageHeader title="新建投资进程" subtitle="在某个模拟账户下，为单个资产分配一笔独立资金。">
        <Link className="button" to="/tasks">
          返回账户总览
        </Link>
      </PageHeader>

      <form className="form-panel" onSubmit={handleSubmit}>
        <label>
          模拟账户
          <select value={accountId} onChange={(event) => setAccountId(event.target.value)} required>
            {accounts.map((account) => (
              <option value={account.id} key={account.id}>
                {account.name} · 可用 {account.cash_hkd.toFixed(2)} HKD · {account.tasks.length}/{account.max_processes} 进程
              </option>
            ))}
          </select>
        </label>
        {selectedAccount ? (
          <div className="empty-state compact-empty">
            当前账户可用 {selectedAccount.cash_hkd.toFixed(2)} HKD / {selectedAccount.cash_usd.toFixed(2)} USD，已有 {processCount} 个运行中进程。
          </div>
        ) : null}

        <label>
          绑定资产
          <select
            value={marketAssetId}
            onChange={(event) => {
              const nextId = event.target.value;
              setMarketAssetId(nextId);
              const asset = assets.find((item) => String(item.id) === nextId);
              if (asset) {
                setName(`${asset.symbol} 投资进程`);
              }
            }}
            required
          >
            {assets.map((asset) => (
              <option value={asset.id} key={asset.id}>
                {asset.symbol} · {asset.name || asset.asset_type} · {asset.exchange}
              </option>
            ))}
          </select>
        </label>
        {assets.length === 0 ? (
          <div className="empty-state compact-empty">
            当前没有可用的 Futu OpenAPI 行情资产。请检查行情看板默认资产配置。
          </div>
        ) : null}

        <label>
          进程名称
          <input value={name} onChange={(event) => setName(event.target.value)} required />
        </label>

        <div className="form-row">
          <label>
            分配资金
            <div className="input-with-unit">
              <input type="number" min="1" value={allocatedCash} onChange={(event) => setAllocatedCash(event.target.value)} required />
              <span>{assetCurrency}</span>
            </div>
          </label>
          <label>
            进程模式
            <select value={mode} onChange={(event) => setMode(event.target.value as "manual" | "quant")}>
              <option value="manual">手动</option>
              <option value="quant">量化策略</option>
            </select>
          </label>
          <div className="info-block inline-info">
            <span>交收限制</span>
            <strong>{settlementLabel}</strong>
          </div>
        </div>

        {mode === "quant" ? (
          <label>
            策略模板
            <select value={strategyKey} onChange={(event) => setStrategyKey(event.target.value)}>
              <option value="ma_crossover">均线交叉</option>
              <option value="rsi_reversal">RSI 反转</option>
              <option value="dca">定投</option>
            </select>
          </label>
        ) : (
          <label>
            初始投入比例：{manualTargetExposure}%
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={manualTargetExposure}
              onChange={(event) => setManualTargetExposure(event.target.value)}
            />
          </label>
        )}

        {feeSchedule ? (
          <section className="fee-panel inline-fee-panel">
            <h2>{feeSchedule.title}</h2>
            <div className="fee-card">
              {feeSchedule.lines.map((line) => (
                <span key={line.name}>
                  {line.name}：{line.value}
                </span>
              ))}
              <small>{feeSchedule.settlement_note}</small>
              <a href={feeSchedule.source_url} target="_blank" rel="noreferrer">
                查看官方说明
              </a>
            </div>
          </section>
        ) : null}

        {error ? <div className="error-text">{error}</div> : null}
        <button className="button primary" type="submit" disabled={loading || accounts.length === 0 || assets.length === 0}>
          {loading ? "创建中..." : "创建投资进程"}
        </button>
      </form>
    </>
  );
}
