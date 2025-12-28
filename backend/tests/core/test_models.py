"""Unit tests for data models - validation and defaults."""

import pytest
from datetime import date
from pydantic import ValidationError

from src.core.models import (
    UserSettings,
    FoodEntry,
    DailyLog,
    CachedFood,
)


class TestUserSettings:
    """Tests for UserSettings model."""

    def test_valid_settings(self):
        """Valid settings are created successfully."""
        settings = UserSettings(
            calorie_goal=2000,
            protein_goal=150,
            carb_goal=200,
            resting_energy=1800,
        )
        assert settings.calorie_goal == 2000
        assert settings.fat_goal is None

    def test_with_fat_goal(self):
        """Fat goal can be optionally set."""
        settings = UserSettings(
            calorie_goal=2000,
            protein_goal=150,
            carb_goal=200,
            fat_goal=65,
            resting_energy=1800,
        )
        assert settings.fat_goal == 65

    def test_negative_goal_rejected(self):
        """Negative goals are rejected."""
        with pytest.raises(ValidationError):
            UserSettings(
                calorie_goal=-100,
                protein_goal=150,
                carb_goal=200,
                resting_energy=1800,
            )


class TestFoodEntry:
    """Tests for FoodEntry model."""

    def test_valid_entry(self):
        """Valid entry is created with defaults."""
        entry = FoodEntry(
            name="Coffee",
            calories=65,
            protein=4.0,
            carbs=6.5,
            fat=2.5,
        )
        assert entry.name == "Coffee"
        assert entry.description is None
        assert entry.id is not None  # Auto-generated UUID

    def test_with_description(self):
        """Entry can include description."""
        entry = FoodEntry(
            name="Coffee",
            description="Cappuccino with 2% milk",
            calories=65,
            protein=4.0,
            carbs=6.5,
            fat=2.5,
        )
        assert entry.description == "Cappuccino with 2% milk"

    def test_empty_name_rejected(self):
        """Empty name is rejected."""
        with pytest.raises(ValidationError):
            FoodEntry(
                name="",
                calories=100,
                protein=10,
                carbs=10,
                fat=5,
            )

    def test_negative_macros_rejected(self):
        """Negative macros are rejected."""
        with pytest.raises(ValidationError):
            FoodEntry(
                name="Food",
                calories=-100,
                protein=10,
                carbs=10,
                fat=5,
            )


class TestDailyLog:
    """Tests for DailyLog model."""

    def test_empty_log(self):
        """Empty log is valid."""
        log = DailyLog(log_date=date(2024, 12, 28))
        assert log.log_date == date(2024, 12, 28)
        assert log.entries == []

    def test_log_with_entries(self):
        """Log can contain entries."""
        entry = FoodEntry(name="Food", calories=100, protein=10, carbs=10, fat=5)
        log = DailyLog(log_date=date(2024, 12, 28), entries=[entry])
        assert len(log.entries) == 1


class TestCachedFood:
    """Tests for CachedFood model."""

    def test_defaults(self):
        """Defaults are set correctly."""
        food = CachedFood(
            name="Coffee",
            calories=65,
            protein=4,
            carbs=6.5,
            fat=2.5,
        )
        assert food.use_count == 0
        assert food.description is None
        assert food.id is not None
