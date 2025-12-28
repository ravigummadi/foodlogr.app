"""MCP Server - Tool definitions for Claude integration.

Defines all MCP tools that Claude can invoke for food logging.
Handles authentication via API key in Authorization header.
"""

import logging
import os
from contextvars import ContextVar
from datetime import date, timedelta

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from ..core.models import UserSettings, FoodEntry, CachedFood, DailyLog
from ..core.macros import calculate_daily_summary
from ..core.reports import generate_weekly_report
from .firestore_client import FoodLogFirestoreClient, FirestoreConfig
from .auth import AuthClient, validate_api_key_format, hash_api_key


logger = logging.getLogger(__name__)

# Context variable to store current user_id per request
current_user_id: ContextVar[str | None] = ContextVar("current_user_id", default=None)

# Configure transport security for Cloud Run deployment
transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=[
        "localhost:*",
        "127.0.0.1:*",
        "*.run.app:*",
        "*.run.app",
        "foodlogr-mcp-504360050716.us-central1.run.app:*",
        "foodlogr-mcp-504360050716.us-central1.run.app",
    ],
)

# Initialize FastMCP server with stateless HTTP for cloud deployments
mcp = FastMCP(
    "foodlogr",
    instructions="""FoodLogr - Personal food logging assistant.

Use these tools to help users track their daily food intake, monitor macros,
and generate reports on their eating habits.

On first use, call setup_user to configure the user's goals.
When logging food, use search_cache first to find previously logged foods.
After logging, always show the updated daily summary.""",
    stateless_http=True,
    transport_security=transport_security,
)

# Lazy-initialized clients
_firestore_client: FoodLogFirestoreClient | None = None
_auth_client: AuthClient | None = None


def get_firestore_client() -> FoodLogFirestoreClient:
    """Get or create Firestore client."""
    global _firestore_client
    if _firestore_client is None:
        config = FirestoreConfig(
            database=os.environ.get("FIRESTORE_DATABASE", "foodlogr"),
        )
        _firestore_client = FoodLogFirestoreClient(config)
    return _firestore_client


def get_auth_client() -> AuthClient:
    """Get or create Auth client."""
    global _auth_client
    if _auth_client is None:
        _auth_client = AuthClient(get_firestore_client().client)
    return _auth_client


def get_user_id() -> str:
    """Get current authenticated user ID.

    Raises:
        RuntimeError: If no user is authenticated
    """
    user_id = current_user_id.get()
    if user_id is None:
        raise RuntimeError("No authenticated user. Ensure API key is provided.")
    return user_id


# ==================== Settings Tools ====================


@mcp.tool()
def setup_user(
    calorie_goal: int,
    protein_goal: int,
    carb_goal: int,
    resting_energy: int,
    fat_goal: int | None = None,
) -> str:
    """Configure user's daily goals and resting energy.

    Call this on first use or when user wants to update their goals.

    Args:
        calorie_goal: Daily calorie target (e.g., 2000)
        protein_goal: Daily protein target in grams (e.g., 150)
        carb_goal: Daily carbohydrate target in grams (e.g., 200)
        resting_energy: Daily resting metabolic rate in calories (e.g., 1800)
        fat_goal: Optional daily fat target in grams

    Returns:
        Confirmation message with stored settings
    """
    user_id = get_user_id()
    db = get_firestore_client()

    settings = UserSettings(
        calorie_goal=calorie_goal,
        protein_goal=protein_goal,
        carb_goal=carb_goal,
        fat_goal=fat_goal,
        resting_energy=resting_energy,
    )

    if db.save_settings(user_id, settings):
        fat_str = f", Fat: {fat_goal}g" if fat_goal else ""
        return f"""Settings saved!
Goals: {calorie_goal} cal, {protein_goal}g protein, {carb_goal}g carbs{fat_str}
Resting energy: {resting_energy} cal/day"""
    else:
        return "Failed to save settings. Please try again."


@mcp.tool()
def get_settings() -> dict:
    """Retrieve the user's current settings and goals.

    Returns:
        Dictionary with all configured goals, or error message if not set up
    """
    user_id = get_user_id()
    db = get_firestore_client()

    settings = db.get_settings(user_id)
    if settings is None:
        return {"error": "No settings found. Please use setup_user first."}

    return {
        "calorie_goal": settings.calorie_goal,
        "protein_goal": settings.protein_goal,
        "carb_goal": settings.carb_goal,
        "fat_goal": settings.fat_goal,
        "resting_energy": settings.resting_energy,
    }


# ==================== Logging Tools ====================


@mcp.tool()
def log_food(
    name: str,
    calories: int,
    protein: float,
    carbs: float,
    fat: float,
    description: str | None = None,
) -> dict:
    """Add a food entry to today's log.

    Args:
        name: Name of the food (e.g., "Cappuccino", "Scrambled eggs")
        calories: Total calories for this serving
        protein: Protein in grams
        carbs: Carbohydrates in grams
        fat: Fat in grams
        description: Optional details about quantity/preparation

    Returns:
        The created entry with ID and updated daily summary
    """
    user_id = get_user_id()
    db = get_firestore_client()

    entry = FoodEntry(
        name=name,
        calories=calories,
        protein=protein,
        carbs=carbs,
        fat=fat,
        description=description,
    )

    log = db.add_entry(user_id, entry)
    if log is None:
        return {"error": "Failed to log food. Please try again."}

    # Get settings for summary calculation
    settings = db.get_settings(user_id)
    if settings is None:
        return {
            "entry": entry.model_dump(),
            "warning": "No settings configured. Use setup_user to see remaining goals.",
        }

    summary = calculate_daily_summary(log.entries, settings)

    return {
        "entry": {
            "id": entry.id,
            "name": entry.name,
            "calories": entry.calories,
            "protein": entry.protein,
            "carbs": entry.carbs,
            "fat": entry.fat,
        },
        "daily_summary": summary.model_dump(),
    }


@mcp.tool()
def update_food(
    entry_id: str,
    name: str | None = None,
    calories: int | None = None,
    protein: float | None = None,
    carbs: float | None = None,
    fat: float | None = None,
    description: str | None = None,
) -> dict:
    """Update an existing food entry. Only provided fields are updated.

    Args:
        entry_id: The ID of the entry to update
        name: New name (optional)
        calories: New calorie count (optional)
        protein: New protein value (optional)
        carbs: New carbs value (optional)
        fat: New fat value (optional)
        description: New description (optional)

    Returns:
        Updated entry and new daily summary
    """
    user_id = get_user_id()
    db = get_firestore_client()

    updates = {}
    if name is not None:
        updates["name"] = name
    if calories is not None:
        updates["calories"] = calories
    if protein is not None:
        updates["protein"] = protein
    if carbs is not None:
        updates["carbs"] = carbs
    if fat is not None:
        updates["fat"] = fat
    if description is not None:
        updates["description"] = description

    if not updates:
        return {"error": "No updates provided."}

    log = db.update_entry(user_id, entry_id, updates)
    if log is None:
        return {"error": "Entry not found or update failed."}

    settings = db.get_settings(user_id)
    if settings is None:
        return {"success": True, "warning": "No settings configured."}

    summary = calculate_daily_summary(log.entries, settings)

    # Find updated entry
    updated_entry = next((e for e in log.entries if e.id == entry_id), None)

    return {
        "entry": updated_entry.model_dump() if updated_entry else None,
        "daily_summary": summary.model_dump(),
    }


@mcp.tool()
def delete_food(entry_id: str) -> dict:
    """Delete a food entry from today's log.

    Args:
        entry_id: The ID of the entry to delete

    Returns:
        Confirmation and updated daily summary
    """
    user_id = get_user_id()
    db = get_firestore_client()

    log = db.delete_entry(user_id, entry_id)
    if log is None:
        return {"error": "Entry not found or delete failed."}

    settings = db.get_settings(user_id)
    if settings is None:
        return {"success": True, "entries_remaining": len(log.entries)}

    summary = calculate_daily_summary(log.entries, settings)

    return {
        "success": True,
        "entries_remaining": len(log.entries),
        "daily_summary": summary.model_dump(),
    }


# ==================== Query Tools ====================


@mcp.tool()
def get_today() -> dict:
    """Get today's complete food log with summary.

    Returns:
        Dictionary with date, entries list, goals, and summary
    """
    user_id = get_user_id()
    db = get_firestore_client()

    today = date.today()
    log = db.get_log(user_id, today)

    entries = []
    if log:
        entries = [
            {
                "id": e.id,
                "name": e.name,
                "description": e.description,
                "calories": e.calories,
                "protein": e.protein,
                "carbs": e.carbs,
                "fat": e.fat,
            }
            for e in log.entries
        ]

    settings = db.get_settings(user_id)
    if settings is None:
        return {
            "date": today.isoformat(),
            "entries": entries,
            "warning": "No settings configured. Use setup_user first.",
        }

    log_entries = log.entries if log else []
    summary = calculate_daily_summary(log_entries, settings)

    return {
        "date": today.isoformat(),
        "entries": entries,
        "goals": {
            "calories": settings.calorie_goal,
            "protein": settings.protein_goal,
            "carbs": settings.carb_goal,
            "fat": settings.fat_goal,
        },
        "summary": summary.model_dump(),
    }


@mcp.tool()
def get_day(date_str: str) -> dict:
    """Get a specific day's food log.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        Dictionary with date, entries list, goals, and summary
    """
    user_id = get_user_id()
    db = get_firestore_client()

    try:
        log_date = date.fromisoformat(date_str)
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD."}

    log = db.get_log(user_id, log_date)

    entries = []
    if log:
        entries = [
            {
                "id": e.id,
                "name": e.name,
                "description": e.description,
                "calories": e.calories,
                "protein": e.protein,
                "carbs": e.carbs,
                "fat": e.fat,
            }
            for e in log.entries
        ]

    settings = db.get_settings(user_id)
    if settings is None:
        return {
            "date": date_str,
            "entries": entries,
            "warning": "No settings configured.",
        }

    log_entries = log.entries if log else []
    summary = calculate_daily_summary(log_entries, settings)

    return {
        "date": date_str,
        "entries": entries,
        "goals": {
            "calories": settings.calorie_goal,
            "protein": settings.protein_goal,
            "carbs": settings.carb_goal,
            "fat": settings.fat_goal,
        },
        "summary": summary.model_dump(),
    }


@mcp.tool()
def get_weekly_report() -> dict:
    """Generate a weekly report with daily summaries and fat metric.

    The 'fat_added' metric = (total_calories_consumed - days * resting_energy).
    Negative values indicate caloric deficit.

    Returns:
        Dictionary with week dates, daily summaries, weekly totals,
        fat_added, and avg_daily_calories
    """
    user_id = get_user_id()
    db = get_firestore_client()

    settings = db.get_settings(user_id)
    if settings is None:
        return {"error": "No settings configured. Use setup_user first."}

    # Get last 7 days of logs
    end_date = date.today()
    start_date = end_date - timedelta(days=6)

    logs = db.get_logs_range(user_id, start_date, end_date)
    report = generate_weekly_report(logs, settings, start_date)

    return {
        "week_start": report.week_start.isoformat(),
        "week_end": report.week_end.isoformat(),
        "days_logged": report.days_logged,
        "daily_summaries": [
            {
                "date": s.log_date.isoformat(),
                "calories": s.total_calories,
                "protein": s.total_protein,
                "carbs": s.total_carbs,
                "fat": s.total_fat,
                "entry_count": s.entry_count,
            }
            for s in report.daily_summaries
        ],
        "weekly_totals": {
            "calories": report.total_calories,
            "protein": report.total_protein,
            "carbs": report.total_carbs,
            "fat": report.total_fat,
        },
        "avg_daily_calories": report.avg_daily_calories,
        "fat_added": report.fat_added,
        "interpretation": (
            f"Caloric {'surplus' if report.fat_added > 0 else 'deficit'} "
            f"of {abs(report.fat_added)} calories over {report.days_logged} days"
        ),
    }


# ==================== Cache Tools ====================


@mcp.tool()
def search_cache(query: str) -> list[dict]:
    """Search user's frequently used foods cache.

    Args:
        query: Search term to match against food names

    Returns:
        List of matching cached foods with their macro values
    """
    user_id = get_user_id()
    db = get_firestore_client()

    results = db.search_cache(user_id, query)

    return [
        {
            "id": f.id,
            "name": f.name,
            "description": f.description,
            "calories": f.calories,
            "protein": f.protein,
            "carbs": f.carbs,
            "fat": f.fat,
            "use_count": f.use_count,
        }
        for f in results
    ]


@mcp.tool()
def add_to_cache(
    name: str,
    calories: int,
    protein: float,
    carbs: float,
    fat: float,
    description: str | None = None,
) -> str:
    """Add a new food to the user's cache for quick future logging.

    Args:
        name: Name of the food (used for searching)
        calories: Calories per serving
        protein: Protein in grams
        carbs: Carbs in grams
        fat: Fat in grams
        description: Optional default description

    Returns:
        Confirmation message with food ID
    """
    user_id = get_user_id()
    db = get_firestore_client()

    food = CachedFood(
        name=name,
        calories=calories,
        protein=protein,
        carbs=carbs,
        fat=fat,
        description=description,
    )

    if db.add_to_cache(user_id, food):
        return f"Added '{name}' to your food cache (ID: {food.id[:8]})"
    else:
        return "Failed to add food to cache. Please try again."
