"""Reusable NBA stats endpoints backed by ``nba_api``."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

import pandas as pd
from nba_api.stats.endpoints import leaguedashteamstats, playergamelog
from requests import RequestException


class NBAClientError(RuntimeError):
    """Raised when an NBA API request fails."""


@dataclass(frozen=True)
class NBARequestConfig:
    """Centralized request parameters shared across nba_api endpoints."""

    season: str
    season_type_all_star: str = "Regular Season"
    per_mode_detailed: str = "PerGame"
    date_from_nullable: str = ""
    date_to_nullable: str = ""
    timeout: int = 30


def _request_config(season: str, **overrides: Any) -> NBARequestConfig:
    """Build a request configuration, allowing call-site overrides."""
    config = NBARequestConfig(season=season)
    if overrides:
        config = replace(config, **overrides)
    return config


def _normalize_endpoint(endpoint: Any) -> pd.DataFrame:
    """Normalize endpoint output into a pandas DataFrame."""
    try:
        return endpoint.get_data_frames()[0].copy()
    except Exception as exc:  # pragma: no cover - protective parsing guard
        raise NBAClientError("Unable to normalize NBA API endpoint response.") from exc


def _execute_endpoint(endpoint_factory: Any, **params: Any) -> pd.DataFrame:
    """Execute an endpoint call with consistent error handling."""
    try:
        endpoint = endpoint_factory(**params)
        return _normalize_endpoint(endpoint)
    except RequestException as exc:
        raise NBAClientError(f"NBA API network request failed: {exc}") from exc
    except Exception as exc:
        raise NBAClientError(f"NBA API request failed: {exc}") from exc


def get_team_basic_stats(
    season: str,
    *,
    season_type: str = "Regular Season",
    per_mode: str = "PerGame",
    date_from: str = "",
    date_to: str = "",
    timeout: int = 30,
) -> pd.DataFrame:
    """Return team-level basic stats for a given season."""
    config = _request_config(
        season,
        season_type_all_star=season_type,
        per_mode_detailed=per_mode,
        date_from_nullable=date_from,
        date_to_nullable=date_to,
        timeout=timeout,
    )
    return _execute_endpoint(
        leaguedashteamstats.LeagueDashTeamStats,
        **asdict(config),
        measure_type_detailed_defense="Base",
    )


def get_player_game_logs(
    player_id: int,
    season: str,
    *,
    season_type: str = "Regular Season",
    date_from: str = "",
    date_to: str = "",
    timeout: int = 30,
) -> pd.DataFrame:
    """Return game logs for a player in a season."""
    config = _request_config(
        season,
        season_type_all_star=season_type,
        date_from_nullable=date_from,
        date_to_nullable=date_to,
        timeout=timeout,
    )
    params = asdict(config)
    params["player_id"] = player_id
    return _execute_endpoint(playergamelog.PlayerGameLog, **params)


def get_league_advanced_stats(
    season: str,
    *,
    season_type: str = "Regular Season",
    per_mode: str = "PerGame",
    date_from: str = "",
    date_to: str = "",
    timeout: int = 30,
) -> pd.DataFrame:
    """Return league/team advanced metrics for a season."""
    config = _request_config(
        season,
        season_type_all_star=season_type,
        per_mode_detailed=per_mode,
        date_from_nullable=date_from,
        date_to_nullable=date_to,
        timeout=timeout,
    )
    return _execute_endpoint(
        leaguedashteamstats.LeagueDashTeamStats,
        **asdict(config),
        measure_type_detailed_defense="Advanced",
    )

import requests
from datetime import date


@dataclass
class NBAClient:
    """Backward-compatible helper for existing app pages."""

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
        payload = self._get("teams")
        return payload.get("data", [])

    def get_players(self, search: str = "") -> list[dict[str, Any]]:
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
