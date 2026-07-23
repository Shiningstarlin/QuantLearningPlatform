from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Quant Learning Simulator"
    app_env: str = "development"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    frontend_origin: str = "http://localhost:5173"

    secret_key: str = "change-me-in-local-dev"
    access_token_expire_minutes: int = 120

    database_url: str = "sqlite:///./quant_simulator.db"

    market_data_provider: str = "mock"
    futu_host: str = "127.0.0.1"
    futu_port: int = 11111
    futu_snapshot_max_requests_per_minute: int = 30
    yfinance_proxy_url: str = ""
    yfinance_request_timeout: int = 20
    yfinance_cache_dir: str = ".yfinance-cache"
    yfinance_disable_persistent_cache: bool = True
    finnhub_api_key: str = ""
    alphavantage_api_key: str = ""
    polygon_api_key: str = ""
    twelvedata_api_key: str = ""

    default_tax_rate: float = 0.001
    default_commission_rate: float = 0.0003
    default_slippage_rate: float = 0.0005
    enable_t_plus_one: bool = True
    default_base_currency: str = "USD"

    simulation_tick_seconds: int = 60
    enable_background_worker: bool = True
    market_board_enabled: bool = True
    market_board_refresh_seconds: int = 300
    market_board_default_symbols: str = "AAPL,MSFT,SPY,QQQ,BTC-USD"
    market_board_default_only: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
