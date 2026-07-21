from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import TripPlanRequestSerializer
from .services.trip_planner import TripPlanner


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
