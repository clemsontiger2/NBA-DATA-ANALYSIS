"""Streamlit entrypoint for NBA data exploration."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from nba.analysis.data_processing import games_to_dataframe, validate_date_range
from nba.app.components.charts import (
    build_team_game_log,
    dataframe_to_csv,
    make_rankings_chart,
    make_trend_chart,
    ranking_frame,
    summarize_kpis,
    trend_frame,
)
from nba.services.nba_client import NBAClient


st.set_page_config(page_title="NBA Data Analysis", page_icon="🏀", layout="wide")


@st.cache_resource
def get_client() -> NBAClient:
    """Create/reuse API client across reruns."""
    return NBAClient()


@st.cache_data(show_spinner=False)
def fetch_teams() -> list[dict]:
    """Load team catalog with caching."""
    return get_client().get_teams()


@st.cache_data(show_spinner=False)
def fetch_players(search: str) -> list[dict]:
    """Load players for a given search term with caching."""
    return get_client().get_players(search)


@st.cache_data(show_spinner=True)
def fetch_games(start: date, end: date, team_ids: tuple[int, ...]) -> list[dict]:
    """Load games with cached API responses."""
    return get_client().get_games(start, end, team_ids=list(team_ids))


st.title("🏀 NBA Data Analysis")
st.caption("Explore recent NBA games with team/player filters and date controls.")

with st.sidebar:
    st.header("Filters")

    default_end = date.today()
    default_start = default_end - timedelta(days=30)
    start_date = st.date_input("Start date", value=default_start)
    end_date = st.date_input("End date", value=default_end)

    valid_range, validation_message = validate_date_range(start_date, end_date)
    if not valid_range:
        st.error(validation_message)

    try:
        teams = fetch_teams()
    except Exception as exc:
        st.warning(f"Unable to load teams from API: {exc}")
        teams = []

    team_lookup = {team["full_name"]: team["id"] for team in teams}
    selected_team_names = st.multiselect(
        "Teams",
        options=sorted(team_lookup.keys()),
        placeholder="Select one or more teams",
    )

    player_search = st.text_input("Player search", placeholder="e.g. LeBron")
    if player_search:
        try:
            players = fetch_players(player_search)
        except Exception as exc:
            st.warning(f"Unable to load players from API: {exc}")
            players = []
    else:
        players = []
    selected_player = st.selectbox(
        "Player",
        options=["Any"] + [f"{p['first_name']} {p['last_name']}" for p in players],
    )

if valid_range:
    team_ids = tuple(team_lookup[name] for name in selected_team_names)
    try:
        games = fetch_games(start_date, end_date, team_ids)
    except Exception as exc:
        st.error(f"Unable to load games from API: {exc}")
        games = []
else:
    games = []

results_df = games_to_dataframe(games) if valid_range else pd.DataFrame()
team_game_log = build_team_game_log(games) if valid_range else pd.DataFrame()

if selected_team_names and not team_game_log.empty:
    team_game_log = team_game_log[team_game_log["team"].isin(selected_team_names)].copy()

kpis = summarize_kpis(team_game_log)

kpi_cols = st.columns(4)
kpi_cols[0].metric("PPG", f"{kpis['ppg']:.1f}")
kpi_cols[1].metric("AST Proxy", f"{kpis['ast_proxy']:.1f}")
kpi_cols[2].metric("REB Proxy", f"{kpis['reb_proxy']:.1f}")
kpi_cols[3].metric("Net Rating Proxy", f"{kpis['net_rating_proxy']:.2f}")

left_col, right_col = st.columns([2.2, 1])

with left_col:
    st.subheader("Results")
    if results_df.empty:
        st.info("No games found for the current filters.")
    else:
        st.dataframe(results_df, use_container_width=True)

with right_col:
    st.subheader("Selection Summary")
    st.write(f"**Date range:** {start_date} → {end_date}")
    st.write(
        f"**Teams:** {', '.join(selected_team_names) if selected_team_names else 'All teams'}"
    )
    st.write(f"**Player:** {selected_player}")
    st.metric("Games returned", value=len(results_df) if valid_range else 0)

st.divider()
st.subheader("Trend Analysis")
trend_data = trend_frame(team_game_log)
metric_options = {
    "PPG": "ppg",
    "AST Proxy": "ast_proxy",
    "REB Proxy": "reb_proxy",
    "Net Rating Proxy": "net_rating_proxy",
}
trend_metric_label = st.selectbox("Trend metric", options=list(metric_options.keys()))
if trend_data.empty:
    st.info("Not enough data to render trend charts.")
else:
    trend_fig = make_trend_chart(trend_data, metric_options[trend_metric_label])
    st.plotly_chart(trend_fig, use_container_width=True)

st.subheader("Team Rankings")
rankings = ranking_frame(team_game_log)
ranking_metric_label = st.selectbox("Ranking metric", options=list(metric_options.keys()))
if rankings.empty:
    st.info("Not enough data to render rankings.")
else:
    ranking_fig = make_rankings_chart(rankings, metric_options[ranking_metric_label])
    st.plotly_chart(ranking_fig, use_container_width=True)

st.subheader("Filterable Rankings Table")
if rankings.empty:
    st.info("No ranking data available for table view.")
else:
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        table_teams = st.multiselect(
            "Filter teams",
            options=sorted(rankings["team"].unique()),
            default=sorted(rankings["team"].unique()),
        )
    with filter_col2:
        min_ppg = st.slider(
            "Minimum PPG",
            min_value=float(rankings["ppg"].min()),
            max_value=float(rankings["ppg"].max()),
            value=float(rankings["ppg"].min()),
        )

    filtered_rankings = rankings[
        rankings["team"].isin(table_teams) & (rankings["ppg"] >= min_ppg)
    ].reset_index(drop=True)

    st.dataframe(filtered_rankings, use_container_width=True)
    st.download_button(
        label="Download CSV",
        data=dataframe_to_csv(filtered_rankings),
        file_name="nba_rankings_filtered.csv",
        mime="text/csv",
    )
