"""Firestore Client - Persistence for food logs and user data.

This module handles all database I/O for food logging operations.
All I/O is contained here; business logic is in the core module.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from google.cloud import firestore

from ..core.models import UserSettings, FoodEntry, DailyLog, CachedFood


logger = logging.getLogger(__name__)


@dataclass
class FirestoreConfig:
    """Configuration for Firestore client.

    Attributes:
        project_id: GCP project ID (None for default)
        database: Firestore database name (None for default database)
    """

    project_id: str | None = None
    database: str | None = None


class FoodLogFirestoreClient:
    """Client for persisting food logs and settings to Firestore.

    Document structure per user:
        users/{user_id}/
            settings: { calorie_goal, protein_goal, ... }
            logs/{YYYY-MM-DD}: { date, entries: [...] }
            cache/{food_id}: { name, calories, ... }
    """

    def __init__(self, config: FirestoreConfig | None = None) -> None:
        """Initialize Firestore client.

        Args:
            config: Firestore configuration
        """
        self.config = config or FirestoreConfig()
        self._client: firestore.Client | None = None

    @property
    def client(self) -> firestore.Client:
        """Lazy initialization of Firestore client."""
        if self._client is None:
            kwargs: dict[str, Any] = {}
            if self.config.project_id:
                kwargs["project"] = self.config.project_id
            if self.config.database:
                kwargs["database"] = self.config.database
            self._client = firestore.Client(**kwargs)
        return self._client

    def _user_ref(self, user_id: str) -> firestore.DocumentReference:
        """Get reference to user document."""
        return self.client.collection("users").document(user_id)

    def _settings_ref(self, user_id: str) -> firestore.DocumentReference:
        """Get reference to user settings document."""
        return self._user_ref(user_id).collection("settings").document("config")

    def _log_ref(self, user_id: str, log_date: date) -> firestore.DocumentReference:
        """Get reference to daily log document."""
        date_str = log_date.isoformat()
        return self._user_ref(user_id).collection("logs").document(date_str)

    def _cache_ref(self, user_id: str, food_id: str) -> firestore.DocumentReference:
        """Get reference to cached food document."""
        return self._user_ref(user_id).collection("cache").document(food_id)

    # ==================== Settings Operations ====================

    def get_settings(self, user_id: str) -> UserSettings | None:
        """Fetch user settings.

        Args:
            user_id: The user's ID

        Returns:
            UserSettings if found, None otherwise
        """
        logger.debug("Fetching settings for user: %s", user_id[:8])
        try:
            doc = self._settings_ref(user_id).get()
            if not doc.exists:
                return None
            return UserSettings(**doc.to_dict())
        except Exception as e:
            logger.error("Failed to fetch settings: %s", str(e))
            return None

    def save_settings(self, user_id: str, settings: UserSettings) -> bool:
        """Save user settings.

        Args:
            user_id: The user's ID
            settings: Settings to save

        Returns:
            True if successful
        """
        logger.info("Saving settings for user: %s", user_id[:8])
        try:
            data = settings.model_dump()
            data["updated_at"] = datetime.utcnow()
            self._settings_ref(user_id).set(data)
            return True
        except Exception as e:
            logger.error("Failed to save settings: %s", str(e))
            return False

    # ==================== Daily Log Operations ====================

    def get_log(self, user_id: str, log_date: date) -> DailyLog | None:
        """Fetch a daily log.

        Args:
            user_id: The user's ID
            log_date: Date of the log

        Returns:
            DailyLog if found, None otherwise
        """
        logger.debug("Fetching log for %s on %s", user_id[:8], log_date)
        try:
            doc = self._log_ref(user_id, log_date).get()
            if not doc.exists:
                return None
            data = doc.to_dict()
            # Convert entries from dicts to FoodEntry objects
            data["entries"] = [FoodEntry(**e) for e in data.get("entries", [])]
            return DailyLog(**data)
        except Exception as e:
            logger.error("Failed to fetch log: %s", str(e))
            return None

    def save_log(self, user_id: str, log: DailyLog) -> bool:
        """Save a daily log.

        Args:
            user_id: The user's ID
            log: The log to save

        Returns:
            True if successful
        """
        logger.info("Saving log for %s on %s", user_id[:8], log.log_date)
        try:
            data = log.model_dump()
            data["updated_at"] = datetime.utcnow()
            # Convert date to ISO string for JSON serialization
            data["log_date"] = log.log_date.isoformat()
            self._log_ref(user_id, log.log_date).set(data)
            return True
        except Exception as e:
            logger.error("Failed to save log: %s", str(e))
            return False

    def get_logs_range(
        self, user_id: str, start_date: date, end_date: date
    ) -> list[DailyLog]:
        """Fetch logs for a date range.

        Args:
            user_id: The user's ID
            start_date: Start of range (inclusive)
            end_date: End of range (inclusive)

        Returns:
            List of DailyLogs found (may be empty)
        """
        logger.debug(
            "Fetching logs for %s from %s to %s", user_id[:8], start_date, end_date
        )
        logs: list[DailyLog] = []

        try:
            # Query logs collection for date range
            logs_ref = self._user_ref(user_id).collection("logs")
            query = (
                logs_ref.where("log_date", ">=", start_date.isoformat())
                .where("log_date", "<=", end_date.isoformat())
                .order_by("log_date")
            )

            for doc in query.stream():
                data = doc.to_dict()
                data["entries"] = [FoodEntry(**e) for e in data.get("entries", [])]
                # Parse date string back to date object
                if isinstance(data.get("log_date"), str):
                    data["log_date"] = date.fromisoformat(data["log_date"])
                logs.append(DailyLog(**data))

            logger.debug("Found %d logs in range", len(logs))
            return logs
        except Exception as e:
            logger.error("Failed to fetch logs range: %s", str(e))
            return []

    def add_entry(self, user_id: str, entry: FoodEntry, log_date: date | None = None) -> DailyLog | None:
        """Add a food entry to a day's log.

        Args:
            user_id: The user's ID
            entry: The food entry to add
            log_date: Date for the entry (defaults to today)

        Returns:
            Updated DailyLog if successful, None otherwise
        """
        if log_date is None:
            log_date = date.today()

        log = self.get_log(user_id, log_date)
        if log is None:
            log = DailyLog(log_date=log_date, entries=[])

        log.entries.append(entry)

        if self.save_log(user_id, log):
            return log
        return None

    def update_entry(
        self, user_id: str, entry_id: str, updates: dict, log_date: date | None = None
    ) -> DailyLog | None:
        """Update a food entry.

        Args:
            user_id: The user's ID
            entry_id: ID of the entry to update
            updates: Fields to update
            log_date: Date of the log (defaults to today)

        Returns:
            Updated DailyLog if successful, None otherwise
        """
        if log_date is None:
            log_date = date.today()

        log = self.get_log(user_id, log_date)
        if log is None:
            return None

        for i, entry in enumerate(log.entries):
            if entry.id == entry_id:
                # Create updated entry
                entry_data = entry.model_dump()
                entry_data.update(updates)
                log.entries[i] = FoodEntry(**entry_data)
                break
        else:
            logger.warning("Entry not found: %s", entry_id)
            return None

        if self.save_log(user_id, log):
            return log
        return None

    def delete_entry(
        self, user_id: str, entry_id: str, log_date: date | None = None
    ) -> DailyLog | None:
        """Delete a food entry.

        Args:
            user_id: The user's ID
            entry_id: ID of the entry to delete
            log_date: Date of the log (defaults to today)

        Returns:
            Updated DailyLog if successful, None otherwise
        """
        if log_date is None:
            log_date = date.today()

        log = self.get_log(user_id, log_date)
        if log is None:
            return None

        original_count = len(log.entries)
        log.entries = [e for e in log.entries if e.id != entry_id]

        if len(log.entries) == original_count:
            logger.warning("Entry not found: %s", entry_id)
            return None

        if self.save_log(user_id, log):
            return log
        return None

    # ==================== Cache Operations ====================

    def search_cache(self, user_id: str, query: str) -> list[CachedFood]:
        """Search user's food cache.

        Simple case-insensitive substring match on name.

        Args:
            user_id: The user's ID
            query: Search query

        Returns:
            List of matching cached foods
        """
        logger.debug("Searching cache for %s: %s", user_id[:8], query)
        results: list[CachedFood] = []

        try:
            cache_ref = self._user_ref(user_id).collection("cache")
            query_lower = query.lower()

            # Firestore doesn't support case-insensitive search,
            # so we fetch all and filter in memory (acceptable for small caches)
            for doc in cache_ref.order_by("use_count", direction=firestore.Query.DESCENDING).limit(100).stream():
                food = CachedFood(**doc.to_dict())
                if query_lower in food.name.lower():
                    results.append(food)

            return results
        except Exception as e:
            logger.error("Failed to search cache: %s", str(e))
            return []

    def add_to_cache(self, user_id: str, food: CachedFood) -> bool:
        """Add a food to the user's cache.

        Args:
            user_id: The user's ID
            food: The food to cache

        Returns:
            True if successful
        """
        logger.info("Adding to cache for %s: %s", user_id[:8], food.name)
        try:
            self._cache_ref(user_id, food.id).set(food.model_dump())
            return True
        except Exception as e:
            logger.error("Failed to add to cache: %s", str(e))
            return False

    def increment_cache_use(self, user_id: str, food_id: str) -> bool:
        """Increment use count for a cached food.

        Args:
            user_id: The user's ID
            food_id: ID of the cached food

        Returns:
            True if successful
        """
        try:
            self._cache_ref(user_id, food_id).update({
                "use_count": firestore.Increment(1),
                "last_used": datetime.utcnow(),
            })
            return True
        except Exception as e:
            logger.error("Failed to increment cache use: %s", str(e))
            return False

    def get_cached_food(self, user_id: str, food_id: str) -> CachedFood | None:
        """Get a specific cached food.

        Args:
            user_id: The user's ID
            food_id: ID of the cached food

        Returns:
            CachedFood if found, None otherwise
        """
        try:
            doc = self._cache_ref(user_id, food_id).get()
            if doc.exists:
                return CachedFood(**doc.to_dict())
            return None
        except Exception as e:
            logger.error("Failed to get cached food: %s", str(e))
            return None
