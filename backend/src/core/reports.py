"""Report Generation - Pure functions for generating reports.

All functions are pure: same input always produces same output, no side effects.
"""

from datetime import date, timedelta

from .models import DailyLog, UserSettings, WeeklyReport, DaySummary
from .macros import calculate_daily_totals


def generate_day_summary(log: DailyLog) -> DaySummary:
    """Generate a summary for a single day's log.

    Args:
        log: The daily log to summarize

    Returns:
        DaySummary with totals for the day
    """
    total_cal, total_pro, total_carb, total_fat = calculate_daily_totals(log.entries)

    return DaySummary(
        log_date=log.log_date,
        total_calories=total_cal,
        total_protein=round(total_pro, 1),
        total_carbs=round(total_carb, 1),
        total_fat=round(total_fat, 1),
        entry_count=len(log.entries),
    )


def calculate_fat_added(total_calories: int, days: int, resting_energy: int) -> int:
    """Calculate fat added/lost based on caloric balance.

    Positive value = caloric surplus (potential fat gain)
    Negative value = caloric deficit (potential fat loss)

    Args:
        total_calories: Total calories consumed over the period
        days: Number of days in the period
        resting_energy: Daily resting energy expenditure

    Returns:
        Net calories (surplus or deficit)
    """
    expected_burn = days * resting_energy
    return total_calories - expected_burn


def generate_weekly_report(
    logs: list[DailyLog],
    settings: UserSettings,
    week_start: date | None = None,
) -> WeeklyReport:
    """Generate a weekly report from daily logs.

    Args:
        logs: List of daily logs (may be empty or partial week)
        settings: User settings for resting energy calculation
        week_start: Start date of the week (defaults to 7 days ago)

    Returns:
        WeeklyReport with daily summaries and aggregate metrics
    """
    if week_start is None:
        week_start = date.today() - timedelta(days=6)

    week_end = week_start + timedelta(days=6)

    # Filter logs to the requested week
    week_logs = [
        log for log in logs
        if week_start <= log.log_date <= week_end
    ]

    # Generate daily summaries
    daily_summaries = [generate_day_summary(log) for log in sorted(week_logs, key=lambda x: x.log_date)]

    # Calculate aggregates
    total_calories = sum(s.total_calories for s in daily_summaries)
    total_protein = sum(s.total_protein for s in daily_summaries)
    total_carbs = sum(s.total_carbs for s in daily_summaries)
    total_fat = sum(s.total_fat for s in daily_summaries)
    days_logged = len(daily_summaries)

    avg_daily_calories = total_calories / days_logged if days_logged > 0 else 0

    # Calculate fat added using days logged (not full week)
    fat_added = calculate_fat_added(total_calories, days_logged, settings.resting_energy)

    return WeeklyReport(
        week_start=week_start,
        week_end=week_end,
        daily_summaries=daily_summaries,
        total_calories=total_calories,
        avg_daily_calories=round(avg_daily_calories, 1),
        total_protein=round(total_protein, 1),
        total_carbs=round(total_carbs, 1),
        total_fat=round(total_fat, 1),
        fat_added=fat_added,
        days_logged=days_logged,
    )
