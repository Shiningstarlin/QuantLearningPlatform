from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from math import isfinite, sqrt
from pathlib import Path

import yfinance as yf
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.backtest import BacktestEquityPoint, BacktestRun, BacktestTask, BacktestTrade, HistoricalPrice
from app.models.market import MarketAsset
from app.schemas.backtest import (
    BacktestAssetMetricsRead,
    BacktestAssetRead,
    BacktestBatchCreate,
    BacktestCreate,
    BacktestPreviewPointRead,
    BacktestPreviewRead,
)
from app.strategies.templates import STRATEGY_TEMPLATES


@dataclass
class HistoricalBar:
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class ResolvedBacktestAsset:
    yfinance_symbol: str
    asset_name: str
    asset_type: str
    exchange: str
    market_asset_id: int | None
    currency: str


class BacktestService:
    YFINANCE_ONLY_ASSETS = [
        {
            "key": "yf:GC=F",
            "name": "黄金期货",
            "symbol": "GC=F",
            "yfinance_symbol": "GC=F",
            "asset_type": "commodity",
            "exchange": "COMEX",
            "provider": "yfinance",
            "currency": "USD",
            "market_asset_id": None,
        },
        {
            "key": "yf:SI=F",
            "name": "白银期货",
            "symbol": "SI=F",
            "yfinance_symbol": "SI=F",
            "asset_type": "commodity",
            "exchange": "COMEX",
            "provider": "yfinance",
            "currency": "USD",
            "market_asset_id": None,
        },
    ]
    YFINANCE_UNSUPPORTED_MARKET_SYMBOLS = {"US.SPCX", "SPCX"}

    def __init__(self, db: Session):
        self.db = db

    def list_assets(self) -> list[BacktestAssetRead]:
        rows: list[BacktestAssetRead] = []
        market_assets = self.db.scalars(
            select(MarketAsset).where(MarketAsset.enabled == True).order_by(MarketAsset.symbol)  # noqa: E712
        )
        for asset in market_assets:
            if asset.symbol.upper() in self.YFINANCE_UNSUPPORTED_MARKET_SYMBOLS:
                continue
            try:
                yfinance_symbol = self._to_yfinance_symbol(asset.symbol, asset.exchange)
            except HTTPException:
                continue
            rows.append(
                BacktestAssetRead(
                    key=f"market:{asset.id}",
                    name=asset.name or asset.symbol,
                    symbol=asset.symbol,
                    yfinance_symbol=yfinance_symbol,
                    asset_type=asset.asset_type,
                    exchange=asset.exchange,
                    provider="yfinance",
                    currency=self._currency_for_exchange(asset.exchange),
                    market_asset_id=asset.id,
                )
            )
        rows.extend(BacktestAssetRead(**asset) for asset in self.YFINANCE_ONLY_ASSETS)
        return rows

    def list_tasks(self, user_id: int) -> list[BacktestTask]:
        return list(
            self.db.scalars(
                select(BacktestTask)
                .where(BacktestTask.user_id == user_id)
                .options(selectinload(BacktestTask.runs))
                .order_by(BacktestTask.created_at.desc())
            )
        )

    def list_runs(self, user_id: int) -> list[BacktestRun]:
        return list(
            self.db.scalars(
                select(BacktestRun).where(BacktestRun.user_id == user_id).order_by(BacktestRun.created_at.desc())
            )
        )

    def get_run(self, user_id: int, backtest_id: int) -> BacktestRun:
        run = self.db.scalar(
            select(BacktestRun)
            .where(BacktestRun.id == backtest_id, BacktestRun.user_id == user_id)
            .options(selectinload(BacktestRun.task).selectinload(BacktestTask.runs), selectinload(BacktestRun.trades), selectinload(BacktestRun.equity_points))
        )
        if run is None:
            raise HTTPException(status_code=404, detail="Backtest not found")
        return run

    def create_and_run(self, user_id: int, payload: BacktestCreate) -> BacktestRun:
        batch_payload = BacktestBatchCreate(
            name=payload.name,
            market_asset_id=payload.market_asset_id,
            yfinance_symbol=payload.yfinance_symbol,
            strategy_keys=[payload.strategy_key],
            start_date=payload.start_date,
            end_date=payload.end_date,
            initial_cash=payload.initial_cash,
            tax_rate=payload.tax_rate,
            commission_rate=payload.commission_rate,
            slippage_rate=payload.slippage_rate,
            t_plus_one_enabled=payload.t_plus_one_enabled,
        )
        _, runs = self.create_batch_and_run(user_id, batch_payload)
        return runs[0]

    def create_batch_and_run(self, user_id: int, payload: BacktestBatchCreate) -> tuple[BacktestTask, list[BacktestRun]]:
        if payload.end_date < payload.start_date:
            raise HTTPException(status_code=400, detail="End date must be after start date")
        if payload.end_date > date.today():
            raise HTTPException(status_code=400, detail="Backtest end date cannot be in the future")

        strategy_keys = list(dict.fromkeys(payload.strategy_keys))
        supported_keys = {template["key"] for template in STRATEGY_TEMPLATES}
        unsupported_keys = [key for key in strategy_keys if key not in supported_keys]
        if unsupported_keys:
            raise HTTPException(status_code=400, detail=f"Unsupported strategies: {', '.join(unsupported_keys)}")
        if not strategy_keys:
            raise HTTPException(status_code=400, detail="Please choose at least one strategy")

        resolved_asset = self._resolve_payload_asset(payload.market_asset_id, payload.yfinance_symbol)
        task = BacktestTask(
            user_id=user_id,
            market_asset_id=resolved_asset.market_asset_id,
            name=payload.name,
            symbol=resolved_asset.yfinance_symbol,
            asset_name=resolved_asset.asset_name,
            asset_type=resolved_asset.asset_type,
            exchange=resolved_asset.exchange,
            provider="yfinance",
            start_date=payload.start_date,
            end_date=payload.end_date,
            initial_cash=payload.initial_cash,
            currency=resolved_asset.currency,
            status="running",
            strategy_count=len(strategy_keys),
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        runs = [
            self._create_run_for_task(task, strategy_key, payload)
            for strategy_key in strategy_keys
        ]
        completed_runs = [run for run in runs if run.status == "completed"]
        failed_runs = [run for run in runs if run.status == "failed"]
        task.status = "failed" if failed_runs and not completed_runs else "completed"
        task.completed_at = datetime.now(timezone.utc)
        if completed_runs:
            task.best_run_id = max(completed_runs, key=lambda run: run.total_return).id
        self.db.commit()
        self.db.refresh(task)
        return task, [self.get_run(user_id, run.id) for run in runs]

    def _create_run_for_task(self, task: BacktestTask, strategy_key: str, payload: BacktestBatchCreate) -> BacktestRun:
        run = BacktestRun(
            user_id=task.user_id,
            backtest_task_id=task.id,
            market_asset_id=task.market_asset_id,
            name=f"{task.name} · {strategy_key}",
            symbol=task.symbol,
            asset_name=task.asset_name,
            asset_type=task.asset_type,
            exchange=task.exchange,
            provider=task.provider,
            strategy_key=strategy_key,
            start_date=task.start_date,
            end_date=task.end_date,
            initial_cash=task.initial_cash,
            final_cash=task.initial_cash,
            final_equity=task.initial_cash,
            tax_rate=payload.tax_rate if payload.tax_rate is not None else settings.default_tax_rate,
            commission_rate=(
                payload.commission_rate if payload.commission_rate is not None else settings.default_commission_rate
            ),
            slippage_rate=payload.slippage_rate if payload.slippage_rate is not None else settings.default_slippage_rate,
            t_plus_one_enabled=(
                payload.t_plus_one_enabled if payload.t_plus_one_enabled is not None else settings.enable_t_plus_one
            ),
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        try:
            bars = self._load_history(task.symbol, task.start_date, task.end_date)
            self._run_strategy(run, bars)
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
        except Exception as exc:
            run.status = "failed"
            run.error_message = str(exc)
            run.completed_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(run)
        return run

    def get_runs_for_comparison(self, user_id: int, ids: list[int]) -> list[BacktestRun]:
        if not ids:
            return []
        runs = list(
            self.db.scalars(
                select(BacktestRun)
                .where(BacktestRun.user_id == user_id, BacktestRun.id.in_(ids))
                .order_by(BacktestRun.created_at.desc())
            )
        )
        run_by_id = {run.id: run for run in runs}
        return [run_by_id[run_id] for run_id in ids if run_id in run_by_id]

    def preview_history(
        self,
        market_asset_id: int | None,
        yfinance_symbol: str | None,
        start_date: date,
        end_date: date,
    ) -> BacktestPreviewRead:
        if end_date < start_date:
            raise HTTPException(status_code=400, detail="End date must be after start date")
        if end_date > date.today():
            raise HTTPException(status_code=400, detail="Backtest end date cannot be in the future")

        resolved_asset = self._resolve_payload_asset(market_asset_id, yfinance_symbol)
        bars = self._load_history(resolved_asset.yfinance_symbol, start_date, end_date)
        self.db.commit()
        points = [
            BacktestPreviewPointRead(
                point_date=bar.date,
                open_price=bar.open,
                high_price=bar.high,
                low_price=bar.low,
                close_price=bar.close,
                volume=bar.volume,
            )
            for bar in bars
        ]
        return BacktestPreviewRead(
            symbol=resolved_asset.yfinance_symbol,
            name=resolved_asset.asset_name,
            currency=resolved_asset.currency,
            points=points,
            asset_metrics=self.asset_metrics_from_bars(bars),
        )

    @staticmethod
    def asset_metrics_from_points(points: list[BacktestEquityPoint]) -> BacktestAssetMetricsRead | None:
        ordered_points = sorted(points, key=lambda point: point.point_date)
        closes = [point.close_price for point in ordered_points if point.close_price > 0]
        if len(closes) < 2:
            return None

        daily_returns = [
            (closes[index] - closes[index - 1]) / closes[index - 1]
            for index in range(1, len(closes))
            if closes[index - 1] > 0
        ]
        average_return = sum(daily_returns) / len(daily_returns) if daily_returns else 0
        variance = (
            sum((daily_return - average_return) ** 2 for daily_return in daily_returns) / (len(daily_returns) - 1)
            if len(daily_returns) > 1
            else 0
        )

        peak_price = closes[0]
        max_drawdown = 0.0
        for close in closes:
            peak_price = max(peak_price, close)
            if peak_price > 0:
                max_drawdown = min(max_drawdown, (close - peak_price) / peak_price)

        return BacktestAssetMetricsRead(
            start_price=closes[0],
            end_price=closes[-1],
            raw_return=(closes[-1] - closes[0]) / closes[0],
            annualized_volatility=sqrt(variance) * sqrt(252),
            max_drawdown=max_drawdown,
            high_price=max(point.high_price for point in ordered_points),
            low_price=min(point.low_price for point in ordered_points),
        )

    @staticmethod
    def asset_metrics_from_bars(bars: list[HistoricalBar]) -> BacktestAssetMetricsRead | None:
        points = [
            BacktestEquityPoint(
                point_date=bar.date,
                open_price=bar.open,
                high_price=bar.high,
                low_price=bar.low,
                close_price=bar.close,
                volume=bar.volume,
                cash=0,
                market_value=0,
                equity=0,
            )
            for bar in bars
        ]
        return BacktestService.asset_metrics_from_points(points)

    def _load_history(self, symbol: str, start_date: date, end_date: date) -> list[HistoricalBar]:
        """Load historical OHLCV bars only from yfinance for backtesting."""
        cached_bars = self._load_cached_history(symbol, start_date, end_date)
        if self._cache_covers_range(cached_bars, start_date, end_date):
            return cached_bars

        try:
            self._configure_yfinance()
            frame = yf.download(
                symbol,
                start=start_date.isoformat(),
                end=(end_date + timedelta(days=1)).isoformat(),
                interval="1d",
                auto_adjust=False,
                progress=False,
                threads=False,
                timeout=settings.yfinance_request_timeout,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Failed to load historical prices from yfinance: {exc}") from exc

        if frame is None or frame.empty:
            raise HTTPException(status_code=400, detail="No historical prices returned by yfinance")

        if hasattr(frame.columns, "nlevels") and frame.columns.nlevels > 1:
            symbols = list(frame.columns.get_level_values(-1))
            if symbol in symbols:
                frame = frame.xs(symbol, axis=1, level=-1)
            else:
                frame.columns = [column[0] for column in frame.columns]

        bars: list[HistoricalBar] = []
        for index, row in frame.iterrows():
            close = self._row_value(row, "Close", "Adj Close")
            if close is None:
                continue
            open_price = self._row_value(row, "Open") or close
            high = self._row_value(row, "High") or close
            low = self._row_value(row, "Low") or close
            volume = self._row_value(row, "Volume") or 0
            bars.append(
                HistoricalBar(
                    date=index.date(),
                    open=open_price,
                    high=high,
                    low=low,
                    close=close,
                    volume=volume,
                )
            )

        if len(bars) < 2:
            raise HTTPException(status_code=400, detail="Not enough historical bars for a backtest")
        self._save_historical_prices(symbol, bars)
        return bars

    def _load_cached_history(self, symbol: str, start_date: date, end_date: date) -> list[HistoricalBar]:
        rows = self.db.scalars(
            select(HistoricalPrice)
            .where(
                HistoricalPrice.provider == "yfinance",
                HistoricalPrice.symbol == symbol,
                HistoricalPrice.price_date >= start_date,
                HistoricalPrice.price_date <= end_date,
            )
            .order_by(HistoricalPrice.price_date)
        )
        return [
            HistoricalBar(
                date=row.price_date,
                open=row.open_price,
                high=row.high_price,
                low=row.low_price,
                close=row.close_price,
                volume=row.volume,
            )
            for row in rows
        ]

    @staticmethod
    def _cache_covers_range(bars: list[HistoricalBar], start_date: date, end_date: date) -> bool:
        if len(bars) < 2:
            return False
        # Allow weekends and market holidays at both edges of the requested range.
        return bars[0].date <= start_date + timedelta(days=7) and bars[-1].date >= end_date - timedelta(days=7)

    def _save_historical_prices(self, symbol: str, bars: list[HistoricalBar]) -> None:
        if not bars:
            return
        dates = [bar.date for bar in bars]
        existing_dates = set(
            self.db.scalars(
                select(HistoricalPrice.price_date).where(
                    HistoricalPrice.provider == "yfinance",
                    HistoricalPrice.symbol == symbol,
                    HistoricalPrice.price_date.in_(dates),
                )
            )
        )
        for bar in bars:
            if bar.date in existing_dates:
                continue
            self.db.add(
                HistoricalPrice(
                    provider="yfinance",
                    symbol=symbol,
                    price_date=bar.date,
                    open_price=bar.open,
                    high_price=bar.high,
                    low_price=bar.low,
                    close_price=bar.close,
                    volume=bar.volume,
                )
            )

    @staticmethod
    def _configure_yfinance() -> None:
        cache_dir = Path(settings.yfinance_cache_dir).expanduser()
        if not cache_dir.is_absolute():
            cache_dir = Path.cwd() / cache_dir
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            yf.set_tz_cache_location(str(cache_dir))
        except OSError:
            if not settings.yfinance_disable_persistent_cache:
                raise

        if settings.yfinance_disable_persistent_cache:
            BacktestService._disable_yfinance_persistent_cache()

        try:
            import yfinance.cache as yf_cache

            for cache_manager_name, cache_attr in (
                ("_TzCacheManager", "_tz_cache"),
                ("_CookieCacheManager", "_Cookie_cache"),
                ("_ISINCacheManager", "_isin_cache"),
            ):
                cache_manager = getattr(yf_cache, cache_manager_name, None)
                if cache_manager is not None:
                    setattr(cache_manager, cache_attr, None)

            for manager_name in ("_TzDBManager", "_CookieDBManager", "_ISINDBManager"):
                manager = getattr(yf_cache, manager_name, None)
                if manager is not None:
                    database = getattr(manager, "_db", None)
                    if database is not None and not database.is_closed():
                        database.close()
                    manager.set_location(str(cache_dir))
        except Exception:
            # yfinance can still try its default cache path if reset is unavailable.
            pass

        proxy_url = settings.yfinance_proxy_url.strip()
        if proxy_url:
            if hasattr(yf, "config") and hasattr(yf.config, "network"):
                yf.config.network.proxy = proxy_url
            else:
                yf.set_config(proxy=proxy_url)

    @staticmethod
    def _disable_yfinance_persistent_cache() -> None:
        class DummyTzCache:
            def lookup(self, ticker):
                return None

            def store(self, ticker, tz):
                return None

        class DummyCookieCache:
            def lookup(self, strategy):
                return None

            def store(self, strategy, cookie):
                return None

        class DummyIsinCache:
            def lookup(self, isin):
                return None

            def store(self, isin, ticker):
                return None

        try:
            import yfinance.base as yf_base
            import yfinance.cache as yf_cache
            import yfinance.data as yf_data

            tz_cache = DummyTzCache()
            cookie_cache = DummyCookieCache()
            isin_cache = DummyIsinCache()
            yf_cache.get_tz_cache = lambda: tz_cache
            yf_base.cache.get_tz_cache = lambda: tz_cache
            yf_cache.get_cookie_cache = lambda: cookie_cache
            yf_data.cache.get_cookie_cache = lambda: cookie_cache
            yf_cache.get_isin_cache = lambda: isin_cache
        except Exception:
            pass

    def _resolve_payload_asset(
        self,
        market_asset_id: int | None,
        yfinance_symbol: str | None,
    ) -> ResolvedBacktestAsset:
        if yfinance_symbol:
            symbol, asset_name, asset_type, exchange = self._resolve_yfinance_only_asset(yfinance_symbol)
            return ResolvedBacktestAsset(
                yfinance_symbol=symbol,
                asset_name=asset_name,
                asset_type=asset_type,
                exchange=exchange,
                market_asset_id=None,
                currency=self._currency_for_exchange(exchange),
            )

        if market_asset_id is None:
            raise HTTPException(status_code=400, detail="Please choose a backtest asset")
        asset = self.db.get(MarketAsset, market_asset_id)
        if asset is None or not asset.enabled:
            raise HTTPException(status_code=400, detail="Please choose an enabled market board asset")
        yfinance_symbol = self._to_yfinance_symbol(asset.symbol, asset.exchange)
        return ResolvedBacktestAsset(
            yfinance_symbol=yfinance_symbol,
            asset_name=asset.name or asset.symbol,
            asset_type=asset.asset_type,
            exchange=asset.exchange,
            market_asset_id=asset.id,
            currency=self._currency_for_exchange(asset.exchange),
        )

    @staticmethod
    def _currency_for_exchange(exchange: str) -> str:
        normalized_exchange = exchange.strip().upper()
        if normalized_exchange == "HK":
            return "HKD"
        if normalized_exchange in {"US", "COMEX", "NYMEX", "NASDAQ", "NYSE"}:
            return "USD"
        return "USD"

    @staticmethod
    def _to_yfinance_symbol(symbol: str, exchange: str) -> str:
        normalized_symbol = symbol.strip().upper()
        normalized_exchange = exchange.strip().upper()

        if normalized_symbol.startswith("US."):
            return normalized_symbol.split(".", 1)[1]
        if normalized_symbol.startswith("HK."):
            raw_code = normalized_symbol.split(".", 1)[1]
            return f"{raw_code[-4:]}.HK"
        if normalized_exchange == "US" and "." not in normalized_symbol:
            return normalized_symbol
        if normalized_exchange == "HK" and normalized_symbol.isdigit():
            return f"{normalized_symbol.zfill(5)[-4:]}.HK"
        if normalized_symbol.endswith(".HK"):
            return normalized_symbol
        if normalized_symbol.endswith("=F"):
            return normalized_symbol

        raise HTTPException(
            status_code=400,
            detail=f"Cannot convert {symbol} to a yfinance ticker. Please use US.<ticker> or HK.<code>.",
        )

    @classmethod
    def _resolve_yfinance_only_asset(cls, symbol: str) -> tuple[str, str, str, str]:
        normalized_symbol = symbol.strip().upper()
        for asset in cls.YFINANCE_ONLY_ASSETS:
            if normalized_symbol == asset["yfinance_symbol"]:
                return asset["yfinance_symbol"], asset["name"], asset["asset_type"], asset["exchange"]
        raise HTTPException(status_code=400, detail=f"Unsupported yfinance-only backtest asset: {symbol}")

    def _run_strategy(self, run: BacktestRun, bars: list[HistoricalBar]) -> None:
        cash = run.initial_cash
        quantity = 0.0
        average_cost = 0.0
        available_quantity = 0.0
        closes = [bar.close for bar in bars]
        peak_equity = run.initial_cash
        max_drawdown = 0.0
        sell_pnls: list[float] = []

        for index, bar in enumerate(bars):
            if run.t_plus_one_enabled:
                available_quantity = quantity
            signal = self._signal(run.strategy_key, closes, index, bar, bars[0].date)

            if signal == "buy" and cash > 0:
                cash, quantity, average_cost, available_quantity = self._buy(
                    run, bar, cash, quantity, average_cost, available_quantity
                )
            elif signal == "sell" and quantity > 0 and available_quantity > 0:
                sell_quantity = min(quantity, available_quantity)
                cash, quantity, average_cost, available_quantity, realized_pnl = self._sell(
                    run, bar, cash, quantity, average_cost, available_quantity, sell_quantity
                )
                sell_pnls.append(realized_pnl)

            market_value = quantity * bar.close
            equity = cash + market_value
            peak_equity = max(peak_equity, equity)
            if peak_equity > 0:
                max_drawdown = min(max_drawdown, (equity - peak_equity) / peak_equity)

            self.db.add(
                BacktestEquityPoint(
                    backtest_id=run.id,
                    point_date=bar.date,
                    open_price=bar.open,
                    high_price=bar.high,
                    low_price=bar.low,
                    close_price=bar.close,
                    volume=bar.volume,
                    cash=cash,
                    market_value=market_value,
                    equity=equity,
                    position_quantity=quantity,
                )
            )

        final_bar = bars[-1]
        run.final_cash = cash
        run.final_market_value = quantity * final_bar.close
        run.final_equity = cash + run.final_market_value
        run.total_return = (run.final_equity - run.initial_cash) / run.initial_cash
        run.max_drawdown = max_drawdown
        run.trade_count = len(run.trades)
        run.win_rate = len([pnl for pnl in sell_pnls if pnl > 0]) / len(sell_pnls) if sell_pnls else 0

    def _buy(
        self,
        run: BacktestRun,
        bar: HistoricalBar,
        cash: float,
        quantity: float,
        average_cost: float,
        available_quantity: float,
    ) -> tuple[float, float, float, float]:
        budget = cash * 0.95 if run.strategy_key != "dca" else min(cash, self._strategy_params(run.strategy_key)["amount"])
        execution_price = self._apply_slippage(bar.close, "buy", run.slippage_rate)
        per_share_cost = execution_price * (1 + run.commission_rate) + abs(execution_price - bar.close)
        buy_quantity = budget / per_share_cost if per_share_cost > 0 else 0
        if buy_quantity <= 0:
            return cash, quantity, average_cost, available_quantity

        gross_amount = execution_price * buy_quantity
        commission = gross_amount * run.commission_rate
        slippage = abs(execution_price - bar.close) * buy_quantity
        net_amount = gross_amount + commission + slippage
        if net_amount > cash:
            return cash, quantity, average_cost, available_quantity

        total_cost = average_cost * quantity + execution_price * buy_quantity
        new_quantity = quantity + buy_quantity
        new_average_cost = total_cost / new_quantity
        new_available_quantity = available_quantity if run.t_plus_one_enabled else available_quantity + buy_quantity

        self.db.add(
            BacktestTrade(
                backtest_id=run.id,
                symbol=run.symbol,
                side="buy",
                quantity=buy_quantity,
                price=execution_price,
                gross_amount=gross_amount,
                tax=0,
                commission=commission,
                slippage=slippage,
                net_amount=net_amount,
                realized_pnl=0,
                reason=self._reason(run.strategy_key, "buy"),
                traded_on=bar.date,
            )
        )
        self.db.flush()
        return cash - net_amount, new_quantity, new_average_cost, new_available_quantity

    def _sell(
        self,
        run: BacktestRun,
        bar: HistoricalBar,
        cash: float,
        quantity: float,
        average_cost: float,
        available_quantity: float,
        sell_quantity: float,
    ) -> tuple[float, float, float, float, float]:
        execution_price = self._apply_slippage(bar.close, "sell", run.slippage_rate)
        gross_amount = execution_price * sell_quantity
        commission = gross_amount * run.commission_rate
        tax = gross_amount * run.tax_rate
        slippage = abs(execution_price - bar.close) * sell_quantity
        net_amount = gross_amount - commission - tax - slippage
        realized_pnl = (execution_price - average_cost) * sell_quantity
        new_quantity = quantity - sell_quantity
        new_average_cost = average_cost if new_quantity > 0 else 0

        self.db.add(
            BacktestTrade(
                backtest_id=run.id,
                symbol=run.symbol,
                side="sell",
                quantity=sell_quantity,
                price=execution_price,
                gross_amount=gross_amount,
                tax=tax,
                commission=commission,
                slippage=slippage,
                net_amount=net_amount,
                realized_pnl=realized_pnl,
                reason=self._reason(run.strategy_key, "sell"),
                traded_on=bar.date,
            )
        )
        self.db.flush()
        return cash + net_amount, new_quantity, new_average_cost, available_quantity - sell_quantity, realized_pnl

    def _signal(self, strategy_key: str, closes: list[float], index: int, bar: HistoricalBar, start_date: date) -> str:
        if strategy_key == "ma_crossover":
            params = self._strategy_params(strategy_key)
            fast_period = params["fast_period"]
            slow_period = params["slow_period"]
            fast = self._moving_average(closes, index, fast_period)
            slow = self._moving_average(closes, index, slow_period)
            prev_fast = self._moving_average(closes, index - 1, fast_period)
            prev_slow = self._moving_average(closes, index - 1, slow_period)
            if None in (fast, slow, prev_fast, prev_slow):
                return "hold"
            if fast > slow and prev_fast <= prev_slow:
                return "buy"
            if fast < slow and prev_fast >= prev_slow:
                return "sell"
            return "hold"

        if strategy_key == "rsi_reversal":
            params = self._strategy_params(strategy_key)
            rsi = self._rsi(closes, index, params["period"])
            prev_rsi = self._rsi(closes, index - 1, params["period"])
            if rsi is None or prev_rsi is None:
                return "hold"
            if prev_rsi < params["oversold"] <= rsi:
                return "buy"
            if rsi >= params["overbought"]:
                return "sell"
            return "hold"

        if strategy_key == "dca":
            params = self._strategy_params(strategy_key)
            if (bar.date - start_date).days % params["interval_days"] == 0:
                return "buy"
            return "hold"

        return "hold"

    @staticmethod
    def _moving_average(closes: list[float], index: int, period: int) -> float | None:
        if index < period - 1:
            return None
        window = closes[index - period + 1 : index + 1]
        return sum(window) / period

    @staticmethod
    def _rsi(closes: list[float], index: int, period: int) -> float | None:
        if index < period:
            return None
        gains = 0.0
        losses = 0.0
        for cursor in range(index - period + 1, index + 1):
            change = closes[cursor] - closes[cursor - 1]
            if change >= 0:
                gains += change
            else:
                losses -= change
        if losses == 0:
            return 100.0
        rs = gains / losses
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _apply_slippage(price: float, side: str, rate: float) -> float:
        multiplier = 1 + rate if side == "buy" else 1 - rate
        return round(price * multiplier, 6)

    @staticmethod
    def _row_value(row, *names: str) -> float | None:
        for name in names:
            if name in row:
                value = row[name]
                if value is not None and isfinite(float(value)):
                    return float(value)
        return None

    @staticmethod
    def _strategy_params(strategy_key: str) -> dict:
        for template in STRATEGY_TEMPLATES:
            if template["key"] == strategy_key:
                return template["default_params"]
        return {}

    @staticmethod
    def _reason(strategy_key: str, side: str) -> str:
        if strategy_key == "ma_crossover":
            return "moving average crossover"
        if strategy_key == "rsi_reversal":
            return "rsi reversal"
        if strategy_key == "dca":
            return "scheduled dollar cost averaging"
        return f"{strategy_key} {side}"
