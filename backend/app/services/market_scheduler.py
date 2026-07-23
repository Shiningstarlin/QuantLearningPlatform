import logging
import threading
import time

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.market_board import MarketBoardService

logger = logging.getLogger(__name__)


class MarketBoardScheduler:
    def __init__(self):
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not settings.market_board_enabled or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="market-board-scheduler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                with SessionLocal() as db:
                    MarketBoardService(db).refresh_all()
            except Exception:
                logger.exception("Failed to refresh market board quotes")
            self._stop_event.wait(settings.market_board_refresh_seconds)


market_board_scheduler = MarketBoardScheduler()
