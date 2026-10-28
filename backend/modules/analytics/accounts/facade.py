from backend.modules.analytics.accounts.infrastructure.repository import AccountsAnalyticsRepository
from backend.modules.analytics.accounts.application.services import AccountsAnalyticsService


class AccountsAnalyticsFacade:
    def __init__(self, db):
        repo = AccountsAnalyticsRepository(db)
        self.service = AccountsAnalyticsService(repo)

    def overview(self, days: int, top_n: int):
        return self.service.overview(days, top_n)