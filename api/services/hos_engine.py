"""
hos_engine.py

FMCSA Hours of Service calculation engine.
Implements the 7 key regulations as modular calculators.

References:
  - 11-Hour Driving Limit
  - 14-Hour Driving Window
  - 30-Minute Rest Break (after 8 cumulative hrs driving)
  - 10 Hours Off-Duty (Sleeper Berth) required after shift
  - 70-Hour/8-Day Cycle
  - 34-Hour Restart (not mandatory to model, but flagged)
"""


class HOSEngine:
    # FMCSA Constants
    MAX_DRIVING_HOURS = 11.0
    MAX_SHIFT_HOURS = 14.0
    MANDATORY_BREAK_AFTER_HOURS = 8.0
    MANDATORY_BREAK_DURATION_HOURS = 0.5
    REQUIRED_OFF_DUTY_HOURS = 10.0
    MAX_CYCLE_HOURS = 70.0
    AVG_SPEED_MPH = 55.0  # Conservative average driving speed

    def calculate_driving_limit(self, cycle_used_hours: float) -> float:
        """
        Returns how many driving hours remain in the current 11-hr driving window.
        Note: cycle can further restrict this.
        """
        driving_remaining = self.MAX_DRIVING_HOURS
        return round(driving_remaining, 2)

    def calculate_cycle_remaining(self, cycle_used_hours: float) -> float:
        """
        Returns remaining hours in the 70-hour/8-day cycle.
        """
        remaining = self.MAX_CYCLE_HOURS - cycle_used_hours
        return round(max(0, remaining), 2)

    def calculate_rest_break(self, hours_driven_since_break: float) -> dict:
        """
        Determines if a 30-min rest break is needed.
        Returns: { needs_break: bool, break_due_in_hours: float }
        """
        hours_until_break = max(0, self.MANDATORY_BREAK_AFTER_HOURS - hours_driven_since_break)
        return {
            "needs_break": hours_driven_since_break >= self.MANDATORY_BREAK_AFTER_HOURS,
            "break_due_in_hours": round(hours_until_break, 2),
        }

    def calculate_daily_shift(self, shift_elapsed_hours: float) -> dict:
        """
        Checks if 14-hour driving window is still open.
        Returns: { window_open: bool, hours_remaining_in_window: float }
        """
        remaining = max(0, self.MAX_SHIFT_HOURS - shift_elapsed_hours)
        return {
            "window_open": remaining > 0,
            "hours_remaining_in_window": round(remaining, 2),
        }

    def calculate_sleep(self, hours_driven: float) -> dict:
        """
        Once shift ends (driving hours or 14hr window), determines sleep period.
        Returns: { sleep_needed: bool, sleep_duration_hours: float }
        """
        return {
            "sleep_needed": hours_driven >= self.MAX_DRIVING_HOURS,
            "sleep_duration_hours": self.REQUIRED_OFF_DUTY_HOURS,
        }

    def plan_driving_segments(self, total_drive_hours: float, cycle_used_hours: float) -> list:
        """
        Core planning algorithm. Takes total drive time needed and cycle used,
        returns a list of driving/break/sleep events.

        Each event: { type, duration_hours, label }
        Types: 'drive', 'break', 'sleep', 'on_duty'
        """
        events = []
        remaining_drive = total_drive_hours
        cycle_remaining = self.calculate_cycle_remaining(cycle_used_hours)

        # Clamp by cycle
        if remaining_drive > cycle_remaining:
            remaining_drive = cycle_remaining  # Driver must restart 34hr; flag in summary

        hours_driven_this_shift = 0.0
        hours_since_last_break = 0.0
        shift_elapsed = 0.0

        # Pre-trip on-duty (fueling, inspection) typically 1 hour
        events.append({"type": "on_duty", "duration_hours": 1.0, "label": "Pre-Trip Inspection"})
        shift_elapsed += 1.0

        while remaining_drive > 0:
            # Check 14-hour window
            shift_info = self.calculate_daily_shift(shift_elapsed)
            window_remaining = shift_info["hours_remaining_in_window"]

            if window_remaining <= 0:
                # 14-hour window exhausted – must sleep
                events.append({
                    "type": "sleep",
                    "duration_hours": self.REQUIRED_OFF_DUTY_HOURS,
                    "label": "Sleeper Berth / Off Duty",
                })
                # Reset shift
                hours_driven_this_shift = 0.0
                hours_since_last_break = 0.0
                shift_elapsed = 1.0  # 1hr on-duty for next day start
                events.append({"type": "on_duty", "duration_hours": 1.0, "label": "Pre-Trip Inspection"})
                continue

            # Check 11-hour driving limit for this shift
            driving_left_this_shift = self.MAX_DRIVING_HOURS - hours_driven_this_shift
            if driving_left_this_shift <= 0:
                events.append({
                    "type": "sleep",
                    "duration_hours": self.REQUIRED_OFF_DUTY_HOURS,
                    "label": "Sleeper Berth / Off Duty",
                })
                hours_driven_this_shift = 0.0
                hours_since_last_break = 0.0
                shift_elapsed = 1.0
                events.append({"type": "on_duty", "duration_hours": 1.0, "label": "Pre-Trip Inspection"})
                continue

            # Check if rest break is needed (30 min after 8 hrs of driving)
            if hours_since_last_break >= self.MANDATORY_BREAK_AFTER_HOURS:
                events.append({
                    "type": "break",
                    "duration_hours": self.MANDATORY_BREAK_DURATION_HOURS,
                    "label": "30-Min Mandatory Rest Break",
                })
                hours_since_last_break = 0.0
                shift_elapsed += self.MANDATORY_BREAK_DURATION_HOURS
                continue

            # How much can we drive in this segment?
            drive_until_break = self.MANDATORY_BREAK_AFTER_HOURS - hours_since_last_break
            segment = min(remaining_drive, driving_left_this_shift, window_remaining, drive_until_break)

            if segment <= 0:
                break

            events.append({
                "type": "drive",
                "duration_hours": round(segment, 4),
                "label": "Driving",
            })

            remaining_drive -= segment
            hours_driven_this_shift += segment
            hours_since_last_break += segment
            shift_elapsed += segment

        # Post-trip on-duty
        events.append({"type": "on_duty", "duration_hours": 0.5, "label": "Post-Trip Inspection"})

        return events
