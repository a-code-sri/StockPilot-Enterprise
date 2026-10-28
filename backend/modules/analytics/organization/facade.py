from backend.modules.analytics.organization.infrastructure.repository import OrganizationAnalyticsRepository
from backend.modules.analytics.organization.application.services import OrganizationAnalyticsService


class OrganizationAnalyticsFacade:
    def __init__(self, db):
        repo = OrganizationAnalyticsRepository(db)
        self.service = OrganizationAnalyticsService(repo)

    def overview(self, histogram_bins: int = 10):
        return self.service.overview(histogram_bins=histogram_bins)