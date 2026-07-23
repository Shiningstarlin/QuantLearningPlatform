from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.core.config import settings
from app.core.database import Base, engine
from app.models import asset, backtest, market, position, simulation, user  # noqa: F401
from app.routers import assets, auth, backtests, health, market_board, simulation_tasks, strategy_templates, trading
from app.services.market_scheduler import market_board_scheduler


def apply_lightweight_migrations() -> None:
    inspector = inspect(engine)
    if "backtest_runs" not in inspector.get_table_names():
        backtest_columns = set()
    else:
        backtest_columns = {column["name"] for column in inspector.get_columns("backtest_runs")}
    with engine.begin() as connection:
        if "backtest_task_id" not in backtest_columns and backtest_columns:
            connection.execute(text("ALTER TABLE backtest_runs ADD COLUMN backtest_task_id INTEGER"))

        if "simulation_tasks" in inspector.get_table_names():
            simulation_columns = {column["name"] for column in inspector.get_columns("simulation_tasks")}
            simulation_additions = {
                "paper_account_id": "INTEGER",
                "market_asset_id": "INTEGER",
                "mode": "VARCHAR(32) DEFAULT 'quant'",
                "symbol": "VARCHAR(64) DEFAULT ''",
                "asset_name": "VARCHAR(120) DEFAULT ''",
                "asset_type": "VARCHAR(32) DEFAULT 'stock'",
                "exchange": "VARCHAR(64) DEFAULT ''",
                "allocated_cash": "FLOAT DEFAULT 0",
                "allocated_cash_hkd": "FLOAT DEFAULT 0",
                "manual_target_exposure": "FLOAT DEFAULT 0",
                "fee_profile": "VARCHAR(32) DEFAULT 'futu'",
                "settlement_days": "INTEGER DEFAULT 0",
            }
            for column_name, column_type in simulation_additions.items():
                if column_name not in simulation_columns:
                    connection.execute(text(f"ALTER TABLE simulation_tasks ADD COLUMN {column_name} {column_type}"))

        if "positions" in inspector.get_table_names():
            position_columns = {column["name"] for column in inspector.get_columns("positions")}
            if "available_on" not in position_columns:
                connection.execute(text("ALTER TABLE positions ADD COLUMN available_on DATE"))

        if "simulated_accounts" in inspector.get_table_names():
            account_columns = {column["name"] for column in inspector.get_columns("simulated_accounts")}
            if "cash_available_on" not in account_columns:
                connection.execute(text("ALTER TABLE simulated_accounts ADD COLUMN cash_available_on DATE"))


def create_app() -> FastAPI:
    Base.metadata.create_all(bind=engine)
    apply_lightweight_migrations()

    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(simulation_tasks.router, prefix="/api/tasks", tags=["simulation tasks"])
    app.include_router(assets.router, prefix="/api/tasks", tags=["watch assets"])
    app.include_router(trading.router, prefix="/api/tasks", tags=["paper trading"])
    app.include_router(backtests.router, prefix="/api/backtests", tags=["backtests"])
    app.include_router(strategy_templates.router, prefix="/api/strategy-templates", tags=["strategy templates"])
    app.include_router(market_board.router, prefix="/api/market-board", tags=["market board"])

    @app.on_event("startup")
    def start_market_board_scheduler() -> None:
        market_board_scheduler.start()

    @app.on_event("shutdown")
    def stop_market_board_scheduler() -> None:
        market_board_scheduler.stop()

    return app


app = create_app()
