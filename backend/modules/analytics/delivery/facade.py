from backend.modules.analytics.delivery.infrastructure.repository import DeliveryAnalyticsRepository
from backend.modules.analytics.delivery.application.services import DeliveryAnalyticsService


class DeliveryAnalyticsFacade:
    def __init__(self, db):
        repo = DeliveryAnalyticsRepository(db)
        self.service = DeliveryAnalyticsService(repo)

    def overview(self, days_month: int, days_year: int, top_n: int, ma_window_month: int, ma_window_year: int):
        return self.service.overview(days_month, days_year, top_n, ma_window_month, ma_window_year)