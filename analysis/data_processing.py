"""Data processing helpers for NBA analysis panels."""

from __future__ import annotations

from datetime import date

import pandas as pd


def games_to_dataframe(games: list[dict]) -> pd.DataFrame:
    """Convert raw games payload into a display-friendly DataFrame."""
    rows = []
    for game in games:
        home_team = game.get("home_team", {})
        visitor_team = game.get("visitor_team", {})
        rows.append(
            {
                "date": game.get("date", "")[:10],
                "season": game.get("season"),
                "status": game.get("status"),
                "home_team": home_team.get("full_name"),
                "home_score": game.get("home_team_score"),
                "visitor_team": visitor_team.get("full_name"),
                "visitor_score": game.get("visitor_team_score"),
            }
        )

    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values("date", ascending=False).reset_index(drop=True)
    return frame


def validate_date_range(start_date: date, end_date: date) -> tuple[bool, str]:
    """Validate date range for filtering."""
    if start_date > end_date:
        return False, "Start date must be earlier than or equal to end date."
    return True, ""
