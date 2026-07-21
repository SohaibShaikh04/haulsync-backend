from django.urls import path
from .views import PlanTripView, GeocodeView

urlpatterns = [
    path('trips/plan', PlanTripView.as_view(), name='plan-trip'),
    path('trips/plan/', PlanTripView.as_view(), name='plan-trip-slash'),
    path('geocode/', GeocodeView.as_view(), name='geocode'),
]
