"""
stop_planner.py

Merges HOS-driven events with fuel stops and assigns geographic coordinates
to every stop by interpolating along the route polyline.
"""
from .hos_engine import HOSEngine
from .fuel_planner import FuelPlanner
from .routing_service import RoutingService


class StopPlanner:
    AVG_SPEED_MPH = 55.0

    def __init__(self):
        self.hos = HOSEngine()
        self.fuel = FuelPlanner()
        self.routing = RoutingService()

    def plan_stops(
        self,
        route_data: dict,
        cycle_used_hours: float,
        pickup_coords: dict,
        dropoff_coords: dict,
        current_coords: dict,
    ) -> list:
        """
        Produces a flat, time-ordered list of stop/event objects.

        Each event:
        {
            type: 'pickup' | 'dropoff' | 'drive' | 'fuel' | 'break' | 'sleep' | 'on_duty',
            label: str,
            duration_hours: float,
            mile_marker: float,
            coordinates: { lng, lat },
            elapsed_hours: float,   # cumulative time from trip start
        }
        """
        total_miles = route_data["distance_miles"]
        total_drive_hours = total_miles / self.AVG_SPEED_MPH
        coordinates = route_data["coordinates"]

        # 1. Get HOS driving segment plan
        hos_events = self.hos.plan_driving_segments(total_drive_hours, cycle_used_hours)

        # 2. Get fuel stop mile markers
        fuel_mile_markers = set(self.fuel.plan_fuel_stops(total_miles))

        # 3. Build final event list by walking through HOS events and injecting fuel stops
        final_events = []
        elapsed_hours = 0.0
        miles_driven = 0.0

        # Start: current location
        final_events.append({
            "type": "current",
            "label": "Current Location",
            "duration_hours": 0,
            "mile_marker": 0,
            "coordinates": current_coords,
            "elapsed_hours": 0,
        })

        # Pickup (first stop)
        pickup_mile = route_data["legs"][0]["distance_miles"]
        pickup_drive_hours = pickup_mile / self.AVG_SPEED_MPH
        final_events.append({
            "type": "pickup",
            "label": "Pickup",
            "duration_hours": 1.0,  # 1hr for loading
            "mile_marker": round(pickup_mile, 2),
            "coordinates": pickup_coords,
            "elapsed_hours": round(pickup_drive_hours, 2),
        })
        elapsed_hours = pickup_drive_hours + 1.0
        miles_driven = pickup_mile

        # Walk through HOS events
        for event in hos_events:
            if event["type"] == "drive":
                seg_miles = event["duration_hours"] * self.AVG_SPEED_MPH
                next_mile = miles_driven + seg_miles

                # Check if any fuel stops fall in this drive segment
                for fuel_mile in sorted(fuel_mile_markers):
                    if miles_driven < fuel_mile <= next_mile:
                        # Insert fuel stop
                        drive_to_fuel_hours = (fuel_mile - miles_driven) / self.AVG_SPEED_MPH
                        fuel_coords = self.routing.interpolate_point_at_mile(coordinates, fuel_mile)
                        elapsed_hours += drive_to_fuel_hours
                        final_events.append({
                            "type": "fuel",
                            "label": "Fuel Stop",
                            "duration_hours": 0.5,
                            "mile_marker": round(fuel_mile, 2),
                            "coordinates": fuel_coords,
                            "elapsed_hours": round(elapsed_hours, 2),
                        })
                        elapsed_hours += 0.5
                        fuel_mile_markers.discard(fuel_mile)

                # Drive segment itself
                elapsed_hours += event["duration_hours"]
                stop_coords = self.routing.interpolate_point_at_mile(coordinates, min(next_mile, total_miles))
                final_events.append({
                    "type": "drive",
                    "label": "Driving",
                    "duration_hours": round(event["duration_hours"], 2),
                    "mile_marker": round(min(next_mile, total_miles), 2),
                    "coordinates": stop_coords,
                    "elapsed_hours": round(elapsed_hours, 2),
                })
                miles_driven = min(next_mile, total_miles)

            else:
                # Non-drive event (break, sleep, on_duty)
                event_coords = self.routing.interpolate_point_at_mile(coordinates, miles_driven)
                elapsed_hours += event["duration_hours"]
                final_events.append({
                    "type": event["type"],
                    "label": event["label"],
                    "duration_hours": event["duration_hours"],
                    "mile_marker": round(miles_driven, 2),
                    "coordinates": event_coords,
                    "elapsed_hours": round(elapsed_hours, 2),
                })

        # Final: Dropoff
        final_events.append({
            "type": "dropoff",
            "label": "Dropoff",
            "duration_hours": 1.0,
            "mile_marker": round(total_miles, 2),
            "coordinates": dropoff_coords,
            "elapsed_hours": round(elapsed_hours + 1.0, 2),
        })

        return final_events
