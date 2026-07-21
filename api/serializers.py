from rest_framework import serializers


class LocationSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lng = serializers.FloatField()
    name = serializers.CharField(max_length=255)


class TripPlanRequestSerializer(serializers.Serializer):
    current_location = LocationSerializer()
    pickup_location = LocationSerializer()
    dropoff_location = LocationSerializer()
    cycle_used_hours = serializers.FloatField(min_value=0, max_value=70)

    def validate_cycle_used_hours(self, value):
        if value >= 70:
            raise serializers.ValidationError(
                "Cycle used hours must be less than 70. Driver needs a 34-hour restart."
            )
        return value
