"""Metrics utilities for analytics-ready DataFrame transformations.

This module is intentionally UI-agnostic so it can be imported and tested from
any environment (scripts, notebooks, tests, or web apps).
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd


def _prepare_grouped_timeseries(
    df: pd.DataFrame,
    group_col: str,
    date_col: str,
) -> pd.DataFrame:
    """Return a sorted copy suitable for grouped, chronological calculations."""
    required_cols = {group_col, date_col}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    prepared = df.copy()
    prepared[date_col] = pd.to_datetime(prepared[date_col])
    return prepared.sort_values([group_col, date_col]).reset_index(drop=True)


def compute_rolling_stats(
    df: pd.DataFrame,
    stat_cols: Sequence[str],
    window: int = 10,
    group_col: str = "entity",
    date_col: str = "date",
    min_periods: int = 1,
) -> pd.DataFrame:
    """Compute grouped rolling averages for one or more statistic columns.

    Parameters
    ----------
    df:
        Input frame with at least ``group_col``, ``date_col`` and the requested
        ``stat_cols``.
    stat_cols:
        Numeric columns for rolling average calculation.
    window:
        Number of rows/games in the rolling window (e.g., 5 or 10).
    group_col:
        Entity identifier (team/player).
    date_col:
        Chronological column.
    min_periods:
        Minimum observations required to return a value.

    Returns
    -------
    pd.DataFrame
        Sorted DataFrame with additional ``{stat}_rolling_{window}`` columns.
    """
    missing = set(stat_cols) - set(df.columns)
    if missing:
        raise ValueError(f"Missing stat columns: {sorted(missing)}")

    prepared = _prepare_grouped_timeseries(df, group_col=group_col, date_col=date_col)

    for stat in stat_cols:
        prepared[f"{stat}_rolling_{window}"] = (
            prepared.groupby(group_col)[stat]
            .transform(lambda series: series.rolling(window=window, min_periods=min_periods).mean())
            .astype(float)
        )

    return prepared


def compute_pace_adjusted_scoring(
    df: pd.DataFrame,
    points_col: str = "points",
    possessions_col: str = "possessions",
    pace_col: str = "pace",
    output_col: str = "pace_adjusted_points_per_100",
    league_avg_pace: float | None = None,
) -> pd.DataFrame:
    """Create a basic pace-normalized scoring indicator.

    Formula used::

        raw_points_per_100 = points / possessions * 100
        pace_adjusted = raw_points_per_100 * (league_avg_pace / pace)

    If ``league_avg_pace`` is not provided, the mean of ``pace_col`` in ``df`` is
    used. If ``pace_col`` is unavailable, the function falls back to
    ``raw_points_per_100`` without additional pace normalization.
    """
    required = {points_col, possessions_col}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    result = df.copy()
    raw_per_100_col = f"{points_col}_per_100"
    result[raw_per_100_col] = result[points_col] / result[possessions_col].replace(0, pd.NA) * 100

    if pace_col in result.columns:
        pace_anchor = (
            float(league_avg_pace)
            if league_avg_pace is not None
            else float(result[pace_col].dropna().mean())
        )
        result[output_col] = result[raw_per_100_col] * (pace_anchor / result[pace_col].replace(0, pd.NA))
    else:
        result[output_col] = result[raw_per_100_col]

    return result


def calculate_trend(
    df: pd.DataFrame,
    stat_col: str,
    periods: int = 10,
    group_col: str = "entity",
    date_col: str = "date",
) -> pd.DataFrame:
    """Calculate trend deltas by comparing recent and prior windows per entity."""
    if stat_col not in df.columns:
        raise ValueError(f"Column not found: {stat_col}")

    prepared = _prepare_grouped_timeseries(df, group_col=group_col, date_col=date_col)

    def _group_trend(group: pd.DataFrame) -> pd.Series:
        series = group[stat_col].dropna()
        recent = series.tail(periods)
        prior = series.iloc[max(0, len(series) - (2 * periods)) : max(0, len(series) - periods)]

        recent_mean = recent.mean() if not recent.empty else pd.NA
        prior_mean = prior.mean() if not prior.empty else pd.NA

        delta = (
            recent_mean - prior_mean
            if pd.notna(recent_mean) and pd.notna(prior_mean)
            else pd.NA
        )
        delta_pct = (
            (delta / prior_mean) * 100
            if pd.notna(delta) and pd.notna(prior_mean) and prior_mean != 0
            else pd.NA
        )

        return pd.Series(
            {
                group_col: group[group_col].iloc[0],
                "recent_mean": recent_mean,
                "prior_mean": prior_mean,
                "delta": delta,
                "delta_pct": delta_pct,
                "samples_recent": len(recent),
                "samples_prior": len(prior),
            }
        )

    trend = prepared.groupby(group_col, as_index=False).apply(_group_trend, include_groups=False)
    return trend.rename(
        columns={
            "recent_mean": f"{stat_col}_recent_{periods}",
            "prior_mean": f"{stat_col}_prior_{periods}",
            "delta": f"{stat_col}_delta",
            "delta_pct": f"{stat_col}_delta_pct",
        }
    )


def compute_off_def_trend_deltas(
    df: pd.DataFrame,
    offensive_col: str = "off_rating",
    defensive_col: str = "def_rating",
    periods: int = 10,
    group_col: str = "entity",
    date_col: str = "date",
) -> pd.DataFrame:
    """Compute offensive/defensive trend deltas and a net differential delta."""
    offense = calculate_trend(
        df,
        stat_col=offensive_col,
        periods=periods,
        group_col=group_col,
        date_col=date_col,
    )
    defense = calculate_trend(
        df,
        stat_col=defensive_col,
        periods=periods,
        group_col=group_col,
        date_col=date_col,
    )

    merged = offense.merge(defense, on=group_col, how="outer")
    off_delta_col = f"{offensive_col}_delta"
    def_delta_col = f"{defensive_col}_delta"
    merged["net_trend_delta"] = merged[off_delta_col] - merged[def_delta_col]
    return merged


def rank_entities(
    df: pd.DataFrame,
    metric: str,
    ascending: bool = False,
    entity_col: str = "entity",
    min_games_col: str | None = None,
    min_games: int | None = None,
) -> pd.DataFrame:
    """Rank entities (teams/players) by a selected metric for table display."""
    required = {entity_col, metric}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    rankings = df.copy()

    if min_games_col and min_games is not None:
        if min_games_col not in rankings.columns:
            raise ValueError(f"Column not found: {min_games_col}")
        rankings = rankings[rankings[min_games_col] >= min_games]

    rankings = rankings.dropna(subset=[metric])
    rankings = rankings.sort_values(metric, ascending=ascending).reset_index(drop=True)
    rankings["rank"] = rankings[metric].rank(method="dense", ascending=ascending).astype(int)

    ordered_cols = ["rank", entity_col, metric] + [
        col for col in rankings.columns if col not in {"rank", entity_col, metric}
    ]
    return rankings[ordered_cols]
