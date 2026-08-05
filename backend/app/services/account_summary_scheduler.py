import logging
import threading

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.simulation_tasks import SimulationTaskService

logger = logging.getLogger(__name__)


class AccountSummaryScheduler:
    def __init__(self):
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not settings.enable_background_worker or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="account-summary-scheduler", daemon=True)
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
                    SimulationTaskService(db).capture_all_accounts()
            except Exception:
                logger.exception("Failed to capture account performance snapshot")
            self._stop_event.wait(max(settings.simulation_tick_seconds, 30))


account_summary_scheduler = AccountSummaryScheduler()
