"""Core Data Models - Pydantic models for type safety.

All models are immutable value objects with no behavior beyond validation.
"""

from datetime import datetime
from datetime import date as DateType
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class UserSettings(BaseModel):
    """User configuration for daily goals and metrics."""

    calorie_goal: int = Field(ge=0, description="Daily calorie target")
    protein_goal: int = Field(ge=0, description="Daily protein target in grams")
    carb_goal: int = Field(ge=0, description="Daily carbohydrate target in grams")
    fat_goal: Optional[int] = Field(default=None, ge=0, description="Daily fat target in grams")
    resting_energy: int = Field(ge=0, description="Daily resting energy expenditure in calories")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class FoodEntry(BaseModel):
    """A single food item logged by the user."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(min_length=1, description="Name of the food")
    description: Optional[str] = Field(default=None, description="Details about preparation/quantity")
    calories: int = Field(ge=0, description="Total calories")
    protein: float = Field(ge=0, description="Protein in grams")
    carbs: float = Field(ge=0, description="Carbohydrates in grams")
    fat: float = Field(ge=0, description="Fat in grams")
    logged_at: datetime = Field(default_factory=datetime.utcnow)


class DailyLog(BaseModel):
    """A day's food log containing all entries."""

    log_date: DateType = Field(description="Date of this log (YYYY-MM-DD)")
    entries: list[FoodEntry] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CachedFood(BaseModel):
    """A frequently used food item saved for quick reuse."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(min_length=1, description="Name of the food (used for searching)")
    description: Optional[str] = Field(default=None, description="Default description")
    calories: int = Field(ge=0, description="Calories per serving")
    protein: float = Field(ge=0, description="Protein in grams")
    carbs: float = Field(ge=0, description="Carbohydrates in grams")
    fat: float = Field(ge=0, description="Fat in grams")
    use_count: int = Field(default=0, ge=0, description="Times this food has been logged")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used: datetime = Field(default_factory=datetime.utcnow)


class DailySummary(BaseModel):
    """Summary of daily intake calculated from entries."""

    total_calories: int = Field(ge=0)
    total_protein: float = Field(ge=0)
    total_carbs: float = Field(ge=0)
    total_fat: float = Field(ge=0)
    calories_remaining: int = Field(description="Negative if over goal")
    protein_remaining: float = Field(description="Negative if over goal")
    carbs_remaining: float = Field(description="Negative if over goal")
    fat_remaining: Optional[float] = Field(default=None, description="None if no fat goal set")


class DaySummary(BaseModel):
    """Summary for a single day in weekly report."""

    log_date: DateType
    total_calories: int
    total_protein: float
    total_carbs: float
    total_fat: float
    entry_count: int


class WeeklyReport(BaseModel):
    """Weekly report with daily summaries and aggregate metrics."""

    week_start: DateType
    week_end: DateType
    daily_summaries: list[DaySummary]
    total_calories: int
    avg_daily_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    fat_added: int = Field(description="Total calories - (days * resting_energy). Negative = deficit.")
    days_logged: int


class User(BaseModel):
    """User record stored in Firestore."""

    email: str
    api_key_hash: str = Field(description="SHA256 hash of API key - never store plaintext")
    created_at: datetime = Field(default_factory=datetime.utcnow)
