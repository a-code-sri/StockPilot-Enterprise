from datetime import datetime, timedelta


class DeliveryAnalyticsService:
    def __init__(self, repo):
        self.repo = repo

    def _fill_missing_days(self, series, days: int):
        """
        series: list of {"day": "YYYY-MM-DD", "count": int} sorted ascending.
        Fill missing dates with count=0 so moving average is correct.
        """
        if days <= 0:
            return []

        end = datetime.utcnow().date()
        start = end - timedelta(days=days - 1)

        lookup = {s["day"]: s["count"] for s in series}

        out = []
        cur = start
        while cur <= end:
            key = cur.isoformat()
            out.append({"day": key, "count": int(lookup.get(key, 0))})
            cur = cur + timedelta(days=1)

        return out

    def _moving_average(self, filled_series, window: int):
        """
        Add moving average field 'ma' to each day.
        """
        if not filled_series:
            return []

        window = max(1, int(window))
        counts = [x["count"] for x in filled_series]

        out = []
        for i in range(len(filled_series)):
            lo = max(0, i - window + 1)
            avg = sum(counts[lo : i + 1]) / (i - lo + 1)
            out.append({
                "day": filled_series[i]["day"],
                "count": filled_series[i]["count"],
                "moving_avg": round(avg, 4)
            })
        return out

    def daily_moving_average(self, days: int, window: int):
        raw = self.repo.daily_delivered_counts(days)
        filled = self._fill_missing_days(raw, days)
        return self._moving_average(filled, window)

    def peak_delivery_time_histogram(self, days: int):
        """
        Histogram by hour-of-day (0..23) using delivered completed_at timestamps.
        """
        timestamps = self.repo.delivered_completion_timestamps(days)

        buckets = {h: 0 for h in range(24)}
        for ts in timestamps:
            try:
                buckets[int(ts.hour)] += 1
            except Exception:
                continue

        return [{"hour": h, "count": buckets[h]} for h in range(24)]

    def overview(self, days_month: int, days_year: int, top_n: int, ma_window_month: int, ma_window_year: int):
        return {
            "moving_average": {
                "month": {
                    "days": days_month,
                    "window": ma_window_month,
                    "series": self.daily_moving_average(days_month, ma_window_month),
                },
                "year": {
                    "days": days_year,
                    "window": ma_window_year,
                    "series": self.daily_moving_average(days_year, ma_window_year),
                },
            },
            "most_ordered_items": {
                "month": {
                    "days": days_month,
                    "top_n": top_n,
                    "items": self.repo.most_ordered_items(days_month, top_n),
                },
                "year": {
                    "days": days_year,
                    "top_n": top_n,
                    "items": self.repo.most_ordered_items(days_year, top_n),
                },
            },
            "status_distribution": {
                "month": self.repo.status_distribution(days_month),
                "year": self.repo.status_distribution(days_year),
            },
            "peak_delivery_time_histogram": {
                "month": {
                    "days": days_month,
                    "hours": self.peak_delivery_time_histogram(days_month),
                },
                "year": {
                    "days": days_year,
                    "hours": self.peak_delivery_time_histogram(days_year),
                },
            }
        }