"""Streamlit entrypoint for NBA data exploration."""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from analysis.data_processing import games_to_dataframe, validate_date_range
from services.nba_client import NBAClient


st.set_page_config(page_title="NBA Data Analysis", page_icon="🏀", layout="wide")

st.title("🏀 NBA Data Analysis")
st.caption("Explore recent NBA games with team/player filters and date controls.")

client = NBAClient()

with st.sidebar:
    st.header("Filters")

    # Date filter section
    default_end = date.today()
    default_start = default_end - timedelta(days=30)
    start_date = st.date_input("Start date", value=default_start)
    end_date = st.date_input("End date", value=default_end)

    valid_range, validation_message = validate_date_range(start_date, end_date)
    if not valid_range:
        st.error(validation_message)

    # Team selection section
    try:
        teams = client.get_teams()
    except Exception as exc:
        st.warning(f"Unable to load teams from API: {exc}")
        teams = []

    team_lookup = {team["full_name"]: team["id"] for team in teams}
    selected_team_names = st.multiselect(
        "Teams",
        options=sorted(team_lookup.keys()),
        placeholder="Select one or more teams",
    )

    # Player selection section
    player_search = st.text_input("Player search", placeholder="e.g. LeBron")
    if player_search:
        try:
            players = client.get_players(player_search)
        except Exception as exc:
            st.warning(f"Unable to load players from API: {exc}")
            players = []
    else:
        players = []
    selected_player = st.selectbox(
        "Player",
        options=["Any"] + [f"{p['first_name']} {p['last_name']}" for p in players],
    )

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Results")
    if valid_range:
        team_ids = [team_lookup[name] for name in selected_team_names]
        try:
            games = client.get_games(start_date, end_date, team_ids=team_ids)
        except Exception as exc:
            st.error(f"Unable to load games from API: {exc}")
            games = []
        games_df = games_to_dataframe(games)

        if games_df.empty:
            st.info("No games found for the current filters.")
        else:
            st.dataframe(games_df, use_container_width=True)

with col2:
    st.subheader("Selection Summary")
    st.write(f"**Date range:** {start_date} → {end_date}")
    st.write(
        f"**Teams:** {', '.join(selected_team_names) if selected_team_names else 'All teams'}"
    )
    st.write(f"**Player:** {selected_player}")
    st.metric("Games returned", value=len(games_df) if valid_range else 0)
