"""
timeline_builder.py

Converts the flat stop/event list from StopPlanner into a richly annotated
time-ordered timeline with absolute timestamps and status metadata.
"""
from datetime import datetime, timedelta


class TimelineBuilder:
    def build(self, stops: list, departure_time: datetime = None) -> list:
        """
        Takes the stop events list and enriches each entry with:
        - absolute_time: ISO 8601 timestamp
        - status: icon/color hint for the frontend
        - is_hos_critical: bool
        """
        if departure_time is None:
            departure_time = datetime.utcnow().replace(hour=6, minute=0, second=0, microsecond=0)

        timeline = []
        for event in stops:
            abs_time = departure_time + timedelta(hours=event["elapsed_hours"])
            timeline.append({
                **event,
                "absolute_time": abs_time.isoformat() + "Z",
                "status": self._get_status(event["type"]),
                "is_hos_critical": event["type"] in ("sleep", "break"),
                "icon": self._get_icon(event["type"]),
            })

        return timeline

    def _get_status(self, event_type: str) -> str:
        mapping = {
            "current": "info",
            "pickup": "success",
            "dropoff": "success",
            "drive": "active",
            "fuel": "warning",
            "break": "warning",
            "sleep": "critical",
            "on_duty": "info",
        }
        return mapping.get(event_type, "info")

    def _get_icon(self, event_type: str) -> str:
        mapping = {
            "current": "map-pin",
            "pickup": "package",
            "dropoff": "flag",
            "drive": "truck",
            "fuel": "fuel",
            "break": "coffee",
            "sleep": "moon",
            "on_duty": "clipboard",
        }
        return mapping.get(event_type, "circle")
