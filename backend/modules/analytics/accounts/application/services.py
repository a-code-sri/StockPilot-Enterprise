import math


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


class AccountsAnalyticsService:
    def __init__(self, repo):
        self.repo = repo

    def liquidity_score(self, days: int):
        # Data
        all_time = self.repo.totals_all_time()
        window = self.repo.totals_for_window(days)

        current_balance = all_time["current_balance"]
        total_debit = window["total_debit"]
        net = window["net"]

        # Average daily debit -> buffer days
        avg_daily_debit = total_debit / max(days, 1)

        if avg_daily_debit <= 0:
            buffer_days = 9999.0
        else:
            buffer_days = current_balance / avg_daily_debit

        # Score design (simple + explainable):
        # - Net score: based on net / debit (good if net positive and large vs expenses)
        # - Buffer score: based on how many days you can survive with current balance
        #
        # net_ratio in [-inf, +inf], squashed by tanh to [-1, +1]
        net_ratio = net / max(total_debit, 1.0)
        net_score = 30.0 + 30.0 * math.tanh(net_ratio)     # approx 0..60
        buffer_score = 40.0 * clamp(buffer_days / 60.0, 0.0, 1.0)  # 0..40, full if >=60 days buffer

        score = clamp(net_score + buffer_score, 0.0, 100.0)

        return {
            "days": days,
            "score": round(score, 2),
            "current_balance": round(current_balance, 2),
            "net": round(net, 2),
            "total_credit": round(window["total_credit"], 2),
            "total_debit": round(total_debit, 2),
            "avg_daily_debit": round(avg_daily_debit, 2),
            "buffer_days": round(buffer_days, 2) if buffer_days != 9999.0 else None,
        }

    def overview(self, days: int, top_n: int):
        pie = self.repo.totals_for_window(days)
        income_by_cat = self.repo.distribution_by_category(days, "credit")
        expense_by_cat = self.repo.distribution_by_category(days, "debit")
        rankings = self.repo.top_sources_targets(days, top_n)

        liquidity_30 = self.liquidity_score(30)
        liquidity_365 = self.liquidity_score(365)

        return {
            "window_days": days,
            "income_vs_expenses": {
                "income": pie["total_credit"],
                "expenses": pie["total_debit"],
                "net": pie["net"],
            },
            "income_by_category": income_by_cat,
            "expense_by_category": expense_by_cat,
            "rankings": rankings,
            "liquidity": {
                "score_30d": liquidity_30,
                "score_365d": liquidity_365,
            },
        }