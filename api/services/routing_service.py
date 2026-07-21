"""
routing_service.py

Fetches a route from OSRM and returns structured data:
- polyline coordinates (list of [lng, lat])
- total distance in miles
- total duration in seconds
- step-by-step geometry for stop injection
"""
import requests


OSRM_BASE_URL = "http://router.project-osrm.org/route/v1/driving"


class RoutingService:
    def get_route(self, current: dict, pickup: dict, dropoff: dict) -> dict:
        """
        Fetch multi-waypoint route: current -> pickup -> dropoff.
        Returns:
            {
                coordinates: [[lng, lat], ...],
                distance_miles: float,
                duration_seconds: float,
                legs: [{ distance_miles, duration_seconds, coordinates }]
            }
        """
        waypoints = [
            f"{current['lng']},{current['lat']}",
            f"{pickup['lng']},{pickup['lat']}",
            f"{dropoff['lng']},{dropoff['lat']}",
        ]
        coords_str = ";".join(waypoints)
        url = f"{OSRM_BASE_URL}/{coords_str}"

        params = {
            "overview": "full",
            "geometries": "geojson",
            "steps": "true",
            "annotations": "false",
        }

        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            raise RuntimeError(f"OSRM routing failed: {str(e)}")

        if data.get("code") != "Ok" or not data.get("routes"):
            raise RuntimeError(f"OSRM returned no valid routes: {data.get('code')}")

        route = data["routes"][0]
        all_coords = route["geometry"]["coordinates"]  # [lng, lat]

        legs_data = []
        for leg in route["legs"]:
            leg_coords = []
            for step in leg.get("steps", []):
                leg_coords.extend(step["geometry"]["coordinates"])
            legs_data.append({
                "distance_miles": self._meters_to_miles(leg["distance"]),
                "duration_seconds": leg["duration"],
                "coordinates": leg_coords,
            })

        return {
            "coordinates": all_coords,
            "distance_miles": self._meters_to_miles(route["distance"]),
            "duration_seconds": route["duration"],
            "legs": legs_data,
        }

    def _meters_to_miles(self, meters: float) -> float:
        return round(meters * 0.000621371, 2)

    def interpolate_point_at_mile(self, coordinates: list, target_mile: float) -> dict:
        """
        Walk along a polyline and return [lng, lat] at a given mile marker.
        """
        accumulated = 0.0
        for i in range(1, len(coordinates)):
            p1 = coordinates[i - 1]
            p2 = coordinates[i]
            seg_dist = self._haversine_miles(p1, p2)
            if accumulated + seg_dist >= target_mile:
                fraction = (target_mile - accumulated) / seg_dist if seg_dist > 0 else 0
                lng = p1[0] + fraction * (p2[0] - p1[0])
                lat = p1[1] + fraction * (p2[1] - p1[1])
                return {"lng": round(lng, 6), "lat": round(lat, 6)}
            accumulated += seg_dist
        # Return last point if beyond route
        last = coordinates[-1]
        return {"lng": last[0], "lat": last[1]}

    def _haversine_miles(self, p1: list, p2: list) -> float:
        import math
        lng1, lat1 = p1
        lng2, lat2 = p2
        R = 3958.8  # Earth radius in miles
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
        return R * 2 * math.asin(math.sqrt(a))
