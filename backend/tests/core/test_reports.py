"""Unit tests for report generation - pure functions, no mocks needed."""

from datetime import date

from src.core.models import FoodEntry, DailyLog, UserSettings
from src.core.reports import (
    generate_day_summary,
    calculate_fat_added,
    generate_weekly_report,
)


class TestGenerateDaySummary:
    """Tests for generate_day_summary."""

    def test_empty_log(self):
        """Empty log returns zero totals."""
        log = DailyLog(log_date=date(2024, 12, 28), entries=[])
        summary = generate_day_summary(log)

        assert summary.log_date == date(2024, 12, 28)
        assert summary.total_calories == 0
        assert summary.total_protein == 0
        assert summary.entry_count == 0

    def test_log_with_entries(self):
        """Log with entries is summarized correctly."""
        log = DailyLog(
            log_date=date(2024, 12, 28),
            entries=[
                FoodEntry(name="A", calories=100, protein=10, carbs=10, fat=5),
                FoodEntry(name="B", calories=200, protein=20, carbs=20, fat=10),
            ],
        )
        summary = generate_day_summary(log)

        assert summary.total_calories == 300
        assert summary.total_protein == 30
        assert summary.total_carbs == 30
        assert summary.total_fat == 15
        assert summary.entry_count == 2


class TestCalculateFatAdded:
    """Tests for calculate_fat_added."""

    def test_caloric_surplus(self):
        """Eating more than burning results in positive fat_added."""
        # 14000 calories over 7 days, 1800 resting = 12600 burn
        fat_added = calculate_fat_added(
            total_calories=14000,
            days=7,
            resting_energy=1800,
        )
        assert fat_added == 1400  # 14000 - 12600

    def test_caloric_deficit(self):
        """Eating less than burning results in negative fat_added."""
        # 10000 calories over 7 days, 1800 resting = 12600 burn
        fat_added = calculate_fat_added(
            total_calories=10000,
            days=7,
            resting_energy=1800,
        )
        assert fat_added == -2600  # 10000 - 12600

    def test_caloric_balance(self):
        """Eating exactly what you burn results in zero."""
        fat_added = calculate_fat_added(
            total_calories=12600,
            days=7,
            resting_energy=1800,
        )
        assert fat_added == 0

    def test_single_day(self):
        """Works correctly for single day."""
        fat_added = calculate_fat_added(
            total_calories=2500,
            days=1,
            resting_energy=1800,
        )
        assert fat_added == 700


class TestGenerateWeeklyReport:
    """Tests for generate_weekly_report."""

    def test_empty_week(self):
        """Empty week returns zeros."""
        settings = UserSettings(
            calorie_goal=2000,
            protein_goal=150,
            carb_goal=200,
            resting_energy=1800,
        )
        report = generate_weekly_report(
            logs=[],
            settings=settings,
            week_start=date(2024, 12, 22),
        )

        assert report.week_start == date(2024, 12, 22)
        assert report.week_end == date(2024, 12, 28)
        assert report.days_logged == 0
        assert report.total_calories == 0
        assert report.fat_added == 0
        assert len(report.daily_summaries) == 0

    def test_partial_week(self):
        """Partial week calculates correctly."""
        settings = UserSettings(
            calorie_goal=2000,
            protein_goal=150,
            carb_goal=200,
            resting_energy=1800,
        )
        logs = [
            DailyLog(
                log_date=date(2024, 12, 25),
                entries=[
                    FoodEntry(name="A", calories=2000, protein=100, carbs=200, fat=50),
                ],
            ),
            DailyLog(
                log_date=date(2024, 12, 26),
                entries=[
                    FoodEntry(name="B", calories=2200, protein=120, carbs=220, fat=60),
                ],
            ),
        ]
        report = generate_weekly_report(
            logs=logs,
            settings=settings,
            week_start=date(2024, 12, 22),
        )

        assert report.days_logged == 2
        assert report.total_calories == 4200
        assert report.avg_daily_calories == 2100
        # fat_added = 4200 - (2 days * 1800) = 4200 - 3600 = 600
        assert report.fat_added == 600

    def test_full_week(self):
        """Full week calculates correctly."""
        settings = UserSettings(
            calorie_goal=2000,
            protein_goal=150,
            carb_goal=200,
            resting_energy=1800,
        )

        # Create 7 days of logs, each with 2000 calories
        logs = []
        for day_offset in range(7):
            the_date = date(2024, 12, 22 + day_offset)
            logs.append(
                DailyLog(
                    log_date=the_date,
                    entries=[
                        FoodEntry(name="Day food", calories=2000, protein=100, carbs=200, fat=50),
                    ],
                )
            )

        report = generate_weekly_report(
            logs=logs,
            settings=settings,
            week_start=date(2024, 12, 22),
        )

        assert report.days_logged == 7
        assert report.total_calories == 14000
        assert report.avg_daily_calories == 2000
        # fat_added = 14000 - (7 * 1800) = 14000 - 12600 = 1400
        assert report.fat_added == 1400

    def test_logs_outside_week_excluded(self):
        """Logs outside the requested week are excluded."""
        settings = UserSettings(
            calorie_goal=2000,
            protein_goal=150,
            carb_goal=200,
            resting_energy=1800,
        )
        logs = [
            # This log is before the week
            DailyLog(
                log_date=date(2024, 12, 20),
                entries=[
                    FoodEntry(name="Old", calories=5000, protein=100, carbs=200, fat=50),
                ],
            ),
            # This log is within the week
            DailyLog(
                log_date=date(2024, 12, 25),
                entries=[
                    FoodEntry(name="Current", calories=2000, protein=100, carbs=200, fat=50),
                ],
            ),
        ]
        report = generate_weekly_report(
            logs=logs,
            settings=settings,
            week_start=date(2024, 12, 22),
        )

        assert report.days_logged == 1
        assert report.total_calories == 2000

    def test_daily_summaries_sorted_by_date(self):
        """Daily summaries are sorted by date."""
        settings = UserSettings(
            calorie_goal=2000,
            protein_goal=150,
            carb_goal=200,
            resting_energy=1800,
        )
        # Add logs out of order
        logs = [
            DailyLog(
                log_date=date(2024, 12, 27),
                entries=[FoodEntry(name="C", calories=300, protein=30, carbs=30, fat=15)],
            ),
            DailyLog(
                log_date=date(2024, 12, 25),
                entries=[FoodEntry(name="A", calories=100, protein=10, carbs=10, fat=5)],
            ),
            DailyLog(
                log_date=date(2024, 12, 26),
                entries=[FoodEntry(name="B", calories=200, protein=20, carbs=20, fat=10)],
            ),
        ]
        report = generate_weekly_report(
            logs=logs,
            settings=settings,
            week_start=date(2024, 12, 22),
        )

        dates = [s.log_date for s in report.daily_summaries]
        assert dates == [date(2024, 12, 25), date(2024, 12, 26), date(2024, 12, 27)]
