"""Macro Calculations - Pure functions for nutrition math.

All functions are pure: same input always produces same output, no side effects.
"""

from .models import FoodEntry, UserSettings, DailySummary


def calculate_daily_totals(entries: list[FoodEntry]) -> tuple[int, float, float, float]:
    """Calculate total macros from a list of food entries.

    Args:
        entries: List of food entries for a day

    Returns:
        Tuple of (calories, protein, carbs, fat)
    """
    total_calories = sum(e.calories for e in entries)
    total_protein = sum(e.protein for e in entries)
    total_carbs = sum(e.carbs for e in entries)
    total_fat = sum(e.fat for e in entries)

    return total_calories, total_protein, total_carbs, total_fat


def calculate_daily_summary(entries: list[FoodEntry], settings: UserSettings) -> DailySummary:
    """Calculate daily summary with totals and remaining goals.

    Args:
        entries: List of food entries for the day
        settings: User's goal settings

    Returns:
        DailySummary with totals and remaining amounts
    """
    total_cal, total_pro, total_carb, total_fat = calculate_daily_totals(entries)

    fat_remaining = None
    if settings.fat_goal is not None:
        fat_remaining = settings.fat_goal - total_fat

    return DailySummary(
        total_calories=total_cal,
        total_protein=round(total_pro, 1),
        total_carbs=round(total_carb, 1),
        total_fat=round(total_fat, 1),
        calories_remaining=settings.calorie_goal - total_cal,
        protein_remaining=round(settings.protein_goal - total_pro, 1),
        carbs_remaining=round(settings.carb_goal - total_carb, 1),
        fat_remaining=round(fat_remaining, 1) if fat_remaining is not None else None,
    )


def calculate_calories_from_macros(protein: float, carbs: float, fat: float) -> int:
    """Calculate calories from macronutrients.

    Uses standard conversion: 4 cal/g protein, 4 cal/g carbs, 9 cal/g fat.

    Args:
        protein: Grams of protein
        carbs: Grams of carbohydrates
        fat: Grams of fat

    Returns:
        Estimated calories (rounded to nearest integer)
    """
    return round(protein * 4 + carbs * 4 + fat * 9)
