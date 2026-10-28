from fastapi import APIRouter, Depends

from backend.modules.analytics.inventory.router import router as inventory_router
from backend.modules.analytics.accounts.router import router as accounts_analytics_router
from backend.modules.analytics.organization.router import router as organization_analytics_router
from backend.modules.analytics.delivery.router import router as delivery_analytics
router = APIRouter()

router.include_router(inventory_router , prefix="/inventory" , tags=["Inventory analytics"])
router.include_router(accounts_analytics_router, prefix="/accounts", tags=["Analytics - Accounts"] )
router.include_router(organization_analytics_router , prefix= "/organization" , tags = ["Organization analytics"])
router.include_router(delivery_analytics , prefix = "/delivery" , tags = ["Delivery Analytics"])