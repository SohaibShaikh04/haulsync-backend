"""
trip_planner.py

Main orchestrator. The view only calls TripPlanner.plan().
Coordinates: routing_service -> stop_planner -> timeline_builder -> eld_generator.
"""
from datetime import datetime
from .routing_service import RoutingService
from .stop_planner import StopPlanner
from .timeline_builder import TimelineBuilder
from .eld_generator import ELDGenerator
from .hos_engine import HOSEngine


class TripPlanner:
    def __init__(self):
        self.routing = RoutingService()
        self.stop_planner = StopPlanner()
        self.timeline_builder = TimelineBuilder()
        self.eld_generator = ELDGenerator()
        self.hos = HOSEngine()

    def plan(
        self,
        current: dict,   # { lat, lng, name }
        pickup: dict,    # { lat, lng, name }
        dropoff: dict,   # { lat, lng, name }
        cycle_used_hours: float,
    ) -> dict:
        """
        Full trip planning pipeline.

        Returns:
        {
            trip: { current, pickup, dropoff, cycle_used_hours },
            route: { coordinates, distance_miles, duration_seconds, legs },
            timeline: [ ...enriched events... ],
            hos: { cycle_remaining, driving_limit, rest_break_info, ... },
            eld_logs: [ ...daily log pages... ],
            summary: { distance, drive_time_hours, total_duration_hours, fuel_stops, breaks, sleep_stops, days, eta, cycle_remaining }
        }
        """
        # Step 1: Get route from OSRM
        route_data = self.routing.get_route(current, pickup, dropoff)

        # Step 2: Plan stops (HOS + fuel merged)
        stops = self.stop_planner.plan_stops(
            route_data=route_data,
            cycle_used_hours=cycle_used_hours,
            pickup_coords={"lng": pickup["lng"], "lat": pickup["lat"]},
            dropoff_coords={"lng": dropoff["lng"], "lat": dropoff["lat"]},
            current_coords={"lng": current["lng"], "lat": current["lat"]},
        )

        # Step 3: Build enriched timeline
        departure_time = datetime.utcnow().replace(hour=6, minute=0, second=0, microsecond=0)
        timeline = self.timeline_builder.build(stops, departure_time=departure_time)

        # Step 4: Generate ELD log pages
        eld_logs = self.eld_generator.generate(timeline, departure_iso=departure_time.isoformat())

        # Step 5: Build HOS summary
        cycle_remaining = self.hos.calculate_cycle_remaining(cycle_used_hours)
        driving_limit = self.hos.calculate_driving_limit(cycle_used_hours)
        total_drive_hours = route_data["distance_miles"] / 55.0

        hos_summary = {
            "cycle_used_hours": round(cycle_used_hours, 2),
            "cycle_remaining_hours": cycle_remaining,
            "driving_limit_hours": driving_limit,
            "shift_window_hours": self.hos.MAX_SHIFT_HOURS,
            "required_off_duty_hours": self.hos.REQUIRED_OFF_DUTY_HOURS,
            "cycle_percent_used": round((cycle_used_hours / self.hos.MAX_CYCLE_HOURS) * 100, 1),
        }

        # Step 6: Build summary
        fuel_stops = [e for e in timeline if e["type"] == "fuel"]
        breaks = [e for e in timeline if e["type"] == "break"]
        sleeps = [e for e in timeline if e["type"] == "sleep"]
        eta_event = timeline[-1] if timeline else None
        eta_iso = eta_event["absolute_time"] if eta_event else None

        summary = {
            "distance_miles": route_data["distance_miles"],
            "drive_time_hours": round(total_drive_hours, 2),
            "total_duration_hours": round(eta_event["elapsed_hours"] if eta_event else 0, 2),
            "fuel_stops": len(fuel_stops),
            "breaks": len(breaks),
            "sleep_stops": len(sleeps),
            "days": len(eld_logs),
            "eta": eta_iso,
            "cycle_remaining_hours": cycle_remaining,
            "avg_speed_mph": 55,
        }

        return {
            "trip": {
                "current": current,
                "pickup": pickup,
                "dropoff": dropoff,
                "cycle_used_hours": cycle_used_hours,
            },
            "route": {
                "coordinates": route_data["coordinates"],
                "distance_miles": route_data["distance_miles"],
                "duration_seconds": route_data["duration_seconds"],
                "legs": route_data["legs"],
            },
            "timeline": timeline,
            "hos": hos_summary,
            "eld_logs": eld_logs,
            "summary": summary,
        }
