"""
eld_generator.py

Generates FMCSA-compliant Driver Daily Log data from timeline events.
Does NOT know about routing — it only consumes timeline events.

Output format:
[
  {
    "day": 1,
    "date": "2024-01-15",
    "total_miles": 550,
    "grid": [
      {
        "status": "off_duty" | "sleeper" | "driving" | "on_duty",
        "start_hour": 0.0,
        "end_hour": 6.0,
        "label": "Off Duty"
      },
      ...
    ],
    "totals": {
      "off_duty": 7.0,
      "sleeper": 0.0,
      "driving": 11.0,
      "on_duty": 6.0
    },
    "remarks": "Dallas, TX to Amarillo, TX"
  }
]
"""
from datetime import datetime, timedelta


# Map event types to ELD duty status rows
EVENT_TO_STATUS = {
    "current":  "off_duty",
    "pickup":   "on_duty",
    "dropoff":  "on_duty",
    "drive":    "driving",
    "fuel":     "on_duty",
    "break":    "off_duty",
    "sleep":    "sleeper",
    "on_duty":  "on_duty",
}

STATUS_LABELS = {
    "off_duty": "Off Duty",
    "sleeper":  "Sleeper Berth",
    "driving":  "Driving",
    "on_duty":  "On Duty (Not Driving)",
}


class ELDGenerator:
    def generate(self, timeline: list, departure_iso: str = None) -> list:
        """
        Converts a timeline into paginated daily log pages.
        """
        if not timeline:
            return []

        # Use departure time from first event
        departure_time = datetime.fromisoformat(timeline[0]["absolute_time"].replace("Z", ""))
        day_start = departure_time.replace(hour=0, minute=0, second=0, microsecond=0)

        # Bucket events by calendar day
        days = {}  # day_index -> list of (status, start_hours_into_day, end_hours_into_day)

        for event in timeline:
            abs_time = datetime.fromisoformat(event["absolute_time"].replace("Z", ""))
            status = EVENT_TO_STATUS.get(event["type"], "on_duty")
            duration = event["duration_hours"]

            if duration == 0:
                continue

            event_start = abs_time
            event_end = abs_time + timedelta(hours=duration)

            # Events can span multiple days — split them
            current_pos = event_start
            while current_pos < event_end:
                # Determine which day
                day_idx = (current_pos - day_start).days
                this_day_start = day_start + timedelta(days=day_idx)
                this_day_end = this_day_start + timedelta(hours=24)

                seg_end = min(event_end, this_day_end)
                seg_start_h = (current_pos - this_day_start).total_seconds() / 3600
                seg_end_h = (seg_end - this_day_start).total_seconds() / 3600

                if day_idx not in days:
                    days[day_idx] = {
                        "date": this_day_start.strftime("%Y-%m-%d"),
                        "segments": [],
                        "miles": 0.0,
                    }

                days[day_idx]["segments"].append({
                    "status": status,
                    "start_hour": round(seg_start_h, 4),
                    "end_hour": round(seg_end_h, 4),
                    "label": STATUS_LABELS.get(status, status),
                })

                if event["type"] == "drive":
                    seg_hours = (seg_end - current_pos).total_seconds() / 3600
                    days[day_idx]["miles"] += round(seg_hours * 55.0, 2)

                current_pos = seg_end

        # Build final log pages
        log_pages = []
        for day_idx in sorted(days.keys()):
            day_data = days[day_idx]
            segments = day_data["segments"]

            # Fill gaps with off_duty
            filled_segments = self._fill_gaps(segments)

            totals = {"off_duty": 0, "sleeper": 0, "driving": 0, "on_duty": 0}
            for seg in filled_segments:
                key = seg["status"]
                if key in totals:
                    totals[key] += round(seg["end_hour"] - seg["start_hour"], 4)

            log_pages.append({
                "day": day_idx + 1,
                "date": day_data["date"],
                "total_miles_driving": round(day_data["miles"], 1),
                "grid": filled_segments,
                "totals": {k: round(v, 2) for k, v in totals.items()},
            })

        return log_pages

    def _fill_gaps(self, segments: list) -> list:
        """Fill uncovered hour gaps with off_duty status."""
        if not segments:
            return [{"status": "off_duty", "start_hour": 0, "end_hour": 24, "label": "Off Duty"}]

        # Sort segments
        segments = sorted(segments, key=lambda s: s["start_hour"])
        filled = []

        # Gap before first segment
        if segments[0]["start_hour"] > 0:
            filled.append({
                "status": "off_duty",
                "start_hour": 0,
                "end_hour": segments[0]["start_hour"],
                "label": "Off Duty",
            })

        for seg in segments:
            # Fill gap between previous end and this start
            if filled and filled[-1]["end_hour"] < seg["start_hour"]:
                filled.append({
                    "status": "off_duty",
                    "start_hour": filled[-1]["end_hour"],
                    "end_hour": seg["start_hour"],
                    "label": "Off Duty",
                })
            filled.append(seg)

        # Gap after last segment
        if filled and filled[-1]["end_hour"] < 24:
            filled.append({
                "status": "off_duty",
                "start_hour": filled[-1]["end_hour"],
                "end_hour": 24,
                "label": "Off Duty",
            })

        return filled
