const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export function getToken() {
  return localStorage.getItem("access_token");
}

export function setToken(token: string) {
  localStorage.setItem("access_token", token);
}

export function clearToken() {
  localStorage.removeItem("access_token");
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");

  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers
  });

  if (!response.ok) {
    let message = `Request failed with ${response.status}`;
    try {
      const data = (await response.json()) as { detail?: string };
      message = data.detail ?? message;
    } catch {
      // Keep status-based message.
    }
    throw new Error(message);
  }

  return (await response.json()) as T;
}

export type SimulationTask = {
  id: number;
  paper_account_id?: number | null;
  market_asset_id?: number | null;
  name: string;
  status: string;
  mode: string;
  strategy_key: string;
  symbol: string;
  asset_name: string;
  asset_type: string;
  exchange: string;
  base_currency: string;
  allocated_cash: number;
  allocated_cash_hkd: number;
  manual_target_exposure: number;
  fee_profile: string;
  settlement_days: number;
  buy_frozen: boolean;
  sell_frozen: boolean;
  t_plus_one_enabled: boolean;
  tax_rate: number;
  commission_rate: number;
  slippage_rate: number;
  account?: {
    initial_cash: number;
    cash: number;
    frozen_cash: number;
    market_value: number;
    equity: number;
    realized_pnl: number;
    cash_available_on?: string | null;
  };
};

export type PaperAccount = {
  id: number;
  name: string;
  base_currency: string;
  initial_equity_hkd: number;
  cash_hkd: number;
  cash_usd: number;
  market_value_hkd: number;
  equity_hkd: number;
  fx_usd_hkd: number;
  max_processes: number;
  status: string;
  created_at: string;
  updated_at: string;
  tasks: SimulationTask[];
};

export type FeeSchedule = {
  market: string;
  title: string;
  lines: Array<{ name: string; value: string }>;
  settlement_note: string;
  source_url: string;
};

export type SimulationFeeSchedules = {
  schedules: FeeSchedule[];
};

export type CurrentUser = {
  id: number;
  email: string;
  display_name: string;
};

export type MarketBoardRow = {
  asset: {
    id: number;
    symbol: string;
    name: string;
    asset_type: string;
  exchange: string;
  provider: string;
  currency: string;
  settlement_days: number;
  enabled: boolean;
  };
  latest_quote: {
    symbol: string;
    provider: string;
    price: number;
    currency: string;
    quote_time: string;
  } | null;
  history: Array<{
    symbol: string;
    provider: string;
    price: number;
    currency: string;
    quote_time: string;
  }>;
  market_status?: {
    market: string;
    is_open: boolean;
    timezone: string;
    local_time: string;
    reason: string;
  } | null;
};

export type MarketAsset = MarketBoardRow["asset"];

export type WatchAsset = {
  id: number;
  symbol: string;
  name: string;
  asset_type: string;
  exchange: string;
  enabled: boolean;
};

export type TradeLog = {
  id: number;
  symbol: string;
  side: string;
  quantity: number;
  price: number;
  gross_amount: number;
  tax: number;
  commission: number;
  slippage: number;
  net_amount: number;
  reason: string;
  traded_at: string;
};

export type BacktestRun = {
  id: number;
  backtest_task_id?: number | null;
  name: string;
  symbol: string;
  asset_name: string;
  asset_type: string;
  exchange: string;
  provider: string;
  strategy_key: string;
  status: string;
  start_date: string;
  end_date: string;
  initial_cash: number;
  final_cash: number;
  final_market_value: number;
  final_equity: number;
  total_return: number;
  max_drawdown: number;
  trade_count: number;
  win_rate: number;
  tax_rate: number;
  commission_rate: number;
  slippage_rate: number;
  t_plus_one_enabled: boolean;
  error_message: string;
  created_at: string;
  completed_at?: string | null;
};

export type BacktestAsset = {
  key: string;
  name: string;
  symbol: string;
  yfinance_symbol: string;
  asset_type: string;
  exchange: string;
  provider: string;
  currency: string;
  market_asset_id?: number | null;
};

export type BacktestTask = {
  id: number;
  name: string;
  symbol: string;
  asset_name: string;
  asset_type: string;
  exchange: string;
  provider: string;
  currency: string;
  status: string;
  start_date: string;
  end_date: string;
  initial_cash: number;
  strategy_count: number;
  best_run_id?: number | null;
  created_at: string;
  completed_at?: string | null;
  runs: BacktestRun[];
};

export type BacktestEquityPoint = {
  id: number;
  point_date: string;
  open_price: number;
  high_price: number;
  low_price: number;
  close_price: number;
  volume: number;
  cash: number;
  market_value: number;
  equity: number;
  position_quantity: number;
};

export type BacktestTrade = {
  id: number;
  symbol: string;
  side: string;
  quantity: number;
  price: number;
  gross_amount: number;
  tax: number;
  commission: number;
  slippage: number;
  net_amount: number;
  realized_pnl: number;
  reason: string;
  traded_on: string;
};

export type BacktestAssetMetrics = {
  start_price: number;
  end_price: number;
  raw_return: number;
  annualized_volatility: number;
  max_drawdown: number;
  high_price: number;
  low_price: number;
};

export type BacktestPreviewPoint = {
  point_date: string;
  open_price: number;
  high_price: number;
  low_price: number;
  close_price: number;
  volume: number;
};

export type BacktestPreview = {
  symbol: string;
  name: string;
  currency: string;
  points: BacktestPreviewPoint[];
  asset_metrics?: BacktestAssetMetrics | null;
};

export type BacktestDetail = {
  task?: BacktestTask | null;
  run: BacktestRun;
  sibling_runs: BacktestRun[];
  equity_points: BacktestEquityPoint[];
  trades: BacktestTrade[];
  asset_metrics?: BacktestAssetMetrics | null;
};

export type BacktestBatch = {
  task?: BacktestTask | null;
  runs: BacktestRun[];
};

export type BacktestComparison = {
  runs: BacktestRun[];
};
