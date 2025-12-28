"""Unit tests for macro calculations - pure functions, no mocks needed."""

from src.core.models import FoodEntry, UserSettings
from src.core.macros import (
    calculate_daily_totals,
    calculate_daily_summary,
    calculate_calories_from_macros,
)


class TestCalculateDailyTotals:
    """Tests for calculate_daily_totals."""

    def test_empty_entries(self):
        """Empty list returns zeros."""
        totals = calculate_daily_totals([])
        assert totals == (0, 0, 0, 0)

    def test_single_entry(self):
        """Single entry returns its values."""
        entry = FoodEntry(
            name="Coffee",
            calories=65,
            protein=4.0,
            carbs=6.5,
            fat=2.5,
        )
        totals = calculate_daily_totals([entry])
        assert totals == (65, 4.0, 6.5, 2.5)

    def test_multiple_entries(self):
        """Multiple entries are summed correctly."""
        entries = [
            FoodEntry(name="Coffee", calories=65, protein=4, carbs=6.5, fat=2.5),
            FoodEntry(name="Eggs", calories=140, protein=12, carbs=0, fat=10),
            FoodEntry(name="Bread", calories=120, protein=3, carbs=20, fat=3),
        ]
        totals = calculate_daily_totals(entries)
        assert totals == (325, 19.0, 26.5, 15.5)


class TestCalculateDailySummary:
    """Tests for calculate_daily_summary."""

    def test_empty_day_shows_full_remaining(self):
        """Empty day shows all goals as remaining."""
        settings = UserSettings(
            calorie_goal=2000,
            protein_goal=150,
            carb_goal=200,
            resting_energy=1800,
        )
        summary = calculate_daily_summary([], settings)

        assert summary.total_calories == 0
        assert summary.calories_remaining == 2000
        assert summary.protein_remaining == 150
        assert summary.carbs_remaining == 200

    def test_partial_day_shows_correct_remaining(self):
        """Partial day shows correct remaining amounts."""
        settings = UserSettings(
            calorie_goal=2000,
            protein_goal=150,
            carb_goal=200,
            resting_energy=1800,
        )
        entries = [
            FoodEntry(name="Breakfast", calories=500, protein=30, carbs=50, fat=20),
        ]
        summary = calculate_daily_summary(entries, settings)

        assert summary.total_calories == 500
        assert summary.calories_remaining == 1500
        assert summary.protein_remaining == 120
        assert summary.carbs_remaining == 150

    def test_over_goal_shows_negative_remaining(self):
        """Going over goal shows negative remaining."""
        settings = UserSettings(
            calorie_goal=2000,
            protein_goal=150,
            carb_goal=200,
            resting_energy=1800,
        )
        entries = [
            FoodEntry(name="Big meal", calories=2500, protein=200, carbs=250, fat=100),
        ]
        summary = calculate_daily_summary(entries, settings)

        assert summary.total_calories == 2500
        assert summary.calories_remaining == -500
        assert summary.protein_remaining == -50
        assert summary.carbs_remaining == -50

    def test_fat_goal_when_set(self):
        """Fat remaining is calculated when fat_goal is set."""
        settings = UserSettings(
            calorie_goal=2000,
            protein_goal=150,
            carb_goal=200,
            fat_goal=65,
            resting_energy=1800,
        )
        entries = [
            FoodEntry(name="Food", calories=500, protein=30, carbs=50, fat=20),
        ]
        summary = calculate_daily_summary(entries, settings)

        assert summary.fat_remaining == 45

    def test_fat_remaining_none_when_no_goal(self):
        """Fat remaining is None when fat_goal not set."""
        settings = UserSettings(
            calorie_goal=2000,
            protein_goal=150,
            carb_goal=200,
            resting_energy=1800,
        )
        summary = calculate_daily_summary([], settings)

        assert summary.fat_remaining is None


class TestCalculateCaloriesFromMacros:
    """Tests for calculate_calories_from_macros."""

    def test_protein_only(self):
        """4 cal per gram of protein."""
        assert calculate_calories_from_macros(protein=25, carbs=0, fat=0) == 100

    def test_carbs_only(self):
        """4 cal per gram of carbs."""
        assert calculate_calories_from_macros(protein=0, carbs=50, fat=0) == 200

    def test_fat_only(self):
        """9 cal per gram of fat."""
        assert calculate_calories_from_macros(protein=0, carbs=0, fat=10) == 90

    def test_mixed_macros(self):
        """Mixed macros calculate correctly."""
        # 10g protein (40) + 20g carbs (80) + 5g fat (45) = 165
        assert calculate_calories_from_macros(protein=10, carbs=20, fat=5) == 165

    def test_rounds_to_nearest_integer(self):
        """Result is rounded to nearest integer."""
        # 1g protein (4) + 1g carbs (4) + 1g fat (9) = 17
        assert calculate_calories_from_macros(protein=1, carbs=1, fat=1) == 17
