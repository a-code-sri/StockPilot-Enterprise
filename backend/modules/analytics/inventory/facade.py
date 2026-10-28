from backend.modules.analytics.inventory.infrastructure.repository import InventoryAnalyticsRepository
from backend.modules.analytics.inventory.application.services import InventoryAnalyticsService


class InventoryAnalyticsFacade:
    def __init__(self, db):
        repo = InventoryAnalyticsRepository(db)
        self.service = InventoryAnalyticsService(repo)

    def alerts(self, dead_days: int, expiry_days: int, consumption_days: int):
        return self.service.get_alerts(dead_days, expiry_days, consumption_days)

    def reorder(self, consumption_days: int, coverage_days: int):
        return self.service.get_reorder_suggestions(consumption_days, coverage_days)

    def stockout(self, consumption_days: int):
        return self.service.get_stockout_predictions(consumption_days)

    def series(self, consumption_days: int, order_months: int):
        return self.service.get_series(consumption_days, order_months)