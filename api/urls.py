from django.urls import path
from .views import PlanTripView

urlpatterns = [
    path('trips/plan', PlanTripView.as_view(), name='plan-trip'),
    path('trips/plan/', PlanTripView.as_view(), name='plan-trip-slash'),
]
