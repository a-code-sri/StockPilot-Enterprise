from datetime import date
from math import inf


class InventoryAnalyticsService:
    def __init__(self, repo):
        self.repo = repo

    def get_alerts(self, dead_days: int, expiry_days: int, consumption_days: int):
        items = self.repo.list_items()
        last_movement = self.repo.get_item_last_movement()
        rates, _ = self.repo.get_consumption_rates(consumption_days)

        today = date.today()

        exhausted = []
        dead_stock = []
        expiry_risk = []

        for it in items:
            # exhausted
            if it.quantity == 0:
                exhausted.append({"name": it.name, "quantity": it.quantity, "status": str(it.status)})

            # dead stock (no movement in dead_days)
            lm = last_movement.get(it.id) or it.created_at
            days_inactive = (today - lm.date()).days
            if it.quantity > 0 and days_inactive >= dead_days:
                dead_stock.append({
                    "name": it.name,
                    "quantity": it.quantity,
                    "days_inactive": days_inactive
                })

            # expiry risk
            if it.expiry_date:
                days_to_expiry = (it.expiry_date - today).days
                rate = rates.get(it.id, 0.0)

                if rate <= 0:
                    days_to_consume = inf
                else:
                    days_to_consume = it.quantity / rate

                risky = (days_to_expiry <= expiry_days) or (days_to_consume > days_to_expiry)
                if risky:
                    expiry_risk.append({
                        "name": it.name,
                        "quantity": it.quantity,
                        "expiry_date": it.expiry_date.isoformat(),
                        "days_to_expiry": days_to_expiry,
                        "avg_daily_consumption": round(rate, 4)
                    })

        return {
            "exhausted": exhausted,
            "dead_stock": dead_stock,
            "expiry_risk": expiry_risk
        }

    def get_reorder_suggestions(self, consumption_days: int, coverage_days: int):
        items = self.repo.list_items()
        rates, consumed_totals = self.repo.get_consumption_rates(consumption_days)

        suggestions = []
        for it in items:
            rate = rates.get(it.id, 0.0)

            target_qty = rate * coverage_days
            available_plus_on_order = it.quantity + it.on_order_quantity
            suggestion_qty = max(0.0, target_qty - available_plus_on_order)

            suggestions.append({
                "name": it.name,
                "current_quantity": it.quantity,
                "on_order_quantity": it.on_order_quantity,
                "avg_daily_consumption": round(rate, 4),
                "consumed_last_window": round(consumed_totals.get(it.id, 0.0), 2),
                "suggested_reorder_quantity": round(suggestion_qty, 2),
            })

        # sort most urgent first
        suggestions.sort(key=lambda x: x["suggested_reorder_quantity"], reverse=True)
        return suggestions

    def get_stockout_predictions(self, consumption_days: int):
        items = self.repo.list_items()
        rates, _ = self.repo.get_consumption_rates(consumption_days)

        today = date.today()
        predictions = []

        for it in items:
            rate = rates.get(it.id, 0.0)
            if rate <= 0:
                predictions.append({
                    "name": it.name,
                    "avg_daily_consumption": round(rate, 4),
                    "days_to_stockout": None,
                    "predicted_stockout_date": None,
                    "current_quantity": it.quantity,
                })
                continue

            days_to_stockout = it.quantity / rate if it.quantity > 0 else 0
            predicted_date = today.toordinal() + int(days_to_stockout)
            predictions.append({
                "name": it.name,
                "avg_daily_consumption": round(rate, 4),
                "days_to_stockout": round(days_to_stockout, 2),
                "predicted_stockout_date": date.fromordinal(predicted_date).isoformat(),
                "current_quantity": it.quantity,
            })

        # sort soonest stockout first (None last)
        predictions.sort(key=lambda x: (x["days_to_stockout"] is None, x["days_to_stockout"] or 10**9))
        return predictions

    def get_series(self, consumption_days: int, order_months: int):
        return {
            "consumption_daily": self.repo.series_consumption_daily(consumption_days),
            "orders_monthly": self.repo.series_orders_monthly(order_months)
        }