from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests as http_requests

from .serializers import TripPlanRequestSerializer
from .services.trip_planner import TripPlanner


class GeocodeView(APIView):
    """
    GET /api/geocode/?q=Dallas, TX

    Server-side proxy for Nominatim geocoding.
    Avoids CORS issues when calling OpenStreetMap from the browser.
    Returns: { lat, lng, name }
    """

    def get(self, request, *args, **kwargs):
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response(
                {"error": "Missing query parameter 'q'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            resp = http_requests.get(
                'https://nominatim.openstreetmap.org/search',
                params={'q': query, 'format': 'json', 'limit': 1},
                headers={'User-Agent': 'HaulSync/1.0 (fleet-route-planner)'},
                timeout=10,
            )
            resp.raise_for_status()
            results = resp.json()
        except Exception as e:
            return Response(
                {"error": "Geocoding service unavailable", "details": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if not results:
            return Response(
                {"error": f"Location not found: {query}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        place = results[0]
        return Response({
            "lat": float(place['lat']),
            "lng": float(place['lon']),
            "name": query,
            "display_name": place.get('display_name', query),
        }, status=status.HTTP_200_OK)


class PlanTripView(APIView):
    """
    POST /api/trips/plan

    Takes trip inputs and returns the full structured trip plan:
    { trip, route, timeline, hos, eld_logs, summary }
    """

    def post(self, request, *args, **kwargs):
        serializer = TripPlanRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"error": "Invalid input", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        planner = TripPlanner()

        try:
            result = planner.plan(
                current={
                    "lat": data["current_location"]["lat"],
                    "lng": data["current_location"]["lng"],
                    "name": data["current_location"]["name"],
                },
                pickup={
                    "lat": data["pickup_location"]["lat"],
                    "lng": data["pickup_location"]["lng"],
                    "name": data["pickup_location"]["name"],
                },
                dropoff={
                    "lat": data["dropoff_location"]["lat"],
                    "lng": data["dropoff_location"]["lng"],
                    "name": data["dropoff_location"]["name"],
                },
                cycle_used_hours=data["cycle_used_hours"],
            )
        except RuntimeError as e:
            return Response(
                {"error": "Trip planning failed", "details": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as e:
            return Response(
                {"error": "Internal server error", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(result, status=status.HTTP_200_OK)
