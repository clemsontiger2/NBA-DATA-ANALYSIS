"""Client utilities for fetching NBA data from public APIs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import requests


@dataclass
class NBAClient:
    """Simple API client for team and game lookups."""

    base_url: str = "https://www.balldontlie.io/api/v1"
    timeout_seconds: int = 10

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = requests.get(
            f"{self.base_url}/{path}",
            params=params,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def get_teams(self) -> list[dict[str, Any]]:
        """Return all NBA teams."""
        payload = self._get("teams")
        return payload.get("data", [])

    def get_players(self, search: str = "") -> list[dict[str, Any]]:
        """Search players by name."""
        params = {"per_page": 50}
        if search:
            params["search"] = search
        payload = self._get("players", params=params)
        return payload.get("data", [])

    def get_games(
        self,
        start_date: date,
        end_date: date,
        team_ids: list[int] | None = None,
        per_page: int = 100,
    ) -> list[dict[str, Any]]:
        """Get games within a date range, optionally filtered by teams."""
        params: dict[str, Any] = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "per_page": per_page,
        }
        if team_ids:
            for idx, team_id in enumerate(team_ids):
                params[f"team_ids[{idx}]"] = team_id
        payload = self._get("games", params=params)
        return payload.get("data", [])
