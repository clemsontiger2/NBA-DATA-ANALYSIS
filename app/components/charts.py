"""Chart and table helpers for Streamlit NBA dashboards."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st


@st.cache_data(show_spinner=False)
def build_team_game_log(games: list[dict]) -> pd.DataFrame:
    """Expand game records into one row per team per game with derived proxies."""
    rows: list[dict] = []
    for game in games:
        game_date = pd.to_datetime(game.get("date"), errors="coerce")
        home_team = game.get("home_team", {})
        away_team = game.get("visitor_team", {})

        home_score = game.get("home_team_score")
        away_score = game.get("visitor_team_score")

        if home_score is None or away_score is None:
            continue

        rows.append(
            {
                "date": game_date,
                "team": home_team.get("full_name"),
                "team_id": home_team.get("id"),
                "opponent": away_team.get("full_name"),
                "points": home_score,
                "opponent_points": away_score,
            }
        )
        rows.append(
            {
                "date": game_date,
                "team": away_team.get("full_name"),
                "team_id": away_team.get("id"),
                "opponent": home_team.get("full_name"),
                "points": away_score,
                "opponent_points": home_score,
            }
        )

    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame

    frame["point_diff"] = frame["points"] - frame["opponent_points"]
    possessions_proxy = ((frame["points"] + frame["opponent_points"]) / 2).replace(0, pd.NA)
    frame["net_rating_proxy"] = (frame["point_diff"] / possessions_proxy) * 100

    # Balldontlie game endpoint does not expose AST/REB at game level; expose proxies.
    frame["ast_proxy"] = frame["points"] * 0.60
    frame["reb_proxy"] = (frame["points"] + frame["opponent_points"]) * 0.22

    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    return frame.sort_values(["date", "team"]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def summarize_kpis(team_game_log: pd.DataFrame) -> dict[str, float]:
    """Return top-level KPI values from filtered game logs."""
    if team_game_log.empty:
        return {"ppg": 0.0, "ast_proxy": 0.0, "reb_proxy": 0.0, "net_rating_proxy": 0.0}

    return {
        "ppg": float(team_game_log["points"].mean()),
        "ast_proxy": float(team_game_log["ast_proxy"].mean()),
        "reb_proxy": float(team_game_log["reb_proxy"].mean()),
        "net_rating_proxy": float(team_game_log["net_rating_proxy"].mean()),
    }


@st.cache_data(show_spinner=False)
def trend_frame(team_game_log: pd.DataFrame) -> pd.DataFrame:
    """Aggregate trend values by date for charting."""
    if team_game_log.empty:
        return pd.DataFrame()

    trend = (
        team_game_log.groupby("date", as_index=False)
        .agg(
            ppg=("points", "mean"),
            ast_proxy=("ast_proxy", "mean"),
            reb_proxy=("reb_proxy", "mean"),
            net_rating_proxy=("net_rating_proxy", "mean"),
        )
        .sort_values("date")
    )
    return trend


@st.cache_data(show_spinner=False)
def ranking_frame(team_game_log: pd.DataFrame) -> pd.DataFrame:
    """Compute per-team ranking metrics."""
    if team_game_log.empty:
        return pd.DataFrame()

    rankings = (
        team_game_log.groupby("team", as_index=False)
        .agg(
            games=("team", "count"),
            ppg=("points", "mean"),
            ast_proxy=("ast_proxy", "mean"),
            reb_proxy=("reb_proxy", "mean"),
            net_rating_proxy=("net_rating_proxy", "mean"),
        )
        .sort_values("ppg", ascending=False)
        .reset_index(drop=True)
    )
    rankings["rank"] = rankings.index + 1
    return rankings[["rank", "team", "games", "ppg", "ast_proxy", "reb_proxy", "net_rating_proxy"]]


def make_trend_chart(trend_data: pd.DataFrame, metric: str):
    """Build line chart for selected trend metric."""
    labels = {
        "ppg": "Points Per Game",
        "ast_proxy": "Assist Proxy",
        "reb_proxy": "Rebound Proxy",
        "net_rating_proxy": "Net Rating Proxy",
    }
    fig = px.line(
        trend_data,
        x="date",
        y=metric,
        markers=True,
        title=f"{labels[metric]} Trend by Date",
        labels={"date": "Date", metric: labels[metric]},
        hover_data={"date": True, metric: ':.2f'},
    )
    fig.update_layout(hovermode="x unified")
    return fig


def make_rankings_chart(rankings: pd.DataFrame, metric: str):
    """Build bar chart for team rankings by metric."""
    labels = {
        "ppg": "Points Per Game",
        "ast_proxy": "Assist Proxy",
        "reb_proxy": "Rebound Proxy",
        "net_rating_proxy": "Net Rating Proxy",
    }
    metric_sorted = rankings.sort_values(metric, ascending=False)
    fig = px.bar(
        metric_sorted,
        x="team",
        y=metric,
        color=metric,
        title=f"Team Rankings by {labels[metric]}",
        labels={"team": "Team", metric: labels[metric]},
        hover_data={"team": True, metric: ':.2f', "games": True},
    )
    fig.update_layout(xaxis_tickangle=-35, coloraxis_showscale=False)
    return fig


@st.cache_data(show_spinner=False)
def dataframe_to_csv(df: pd.DataFrame) -> bytes:
    """Serialize frame to CSV bytes for download button."""
    return df.to_csv(index=False).encode("utf-8")
