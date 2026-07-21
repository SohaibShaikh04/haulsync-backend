"""
fuel_planner.py

Calculates fuel stop mile markers based on a truck's range.
Default range: 1000 miles per tank (industry standard for long-haul).
"""


class FuelPlanner:
    FUEL_RANGE_MILES = 1000.0

    def plan_fuel_stops(self, total_miles: float) -> list:
        """
        Returns a list of mile markers where fuel stops are needed.
        Example: for 2400 miles -> [1000, 2000]
        """
        stops = []
        mile = self.FUEL_RANGE_MILES
        while mile < total_miles:
            stops.append(round(mile, 2))
            mile += self.FUEL_RANGE_MILES
        return stops
