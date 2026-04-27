"""
NASCAR Sponsorship Visibility Analysis
Script 03 — Composite Visibility Scoring Model

Implements the 7-variable, 4-category weighted scoring model.
Assigns each sponsor a 0-100 weekly score per race, sums to a
season total (theoretical max 3,600 pts), and validates the model
against 6 integrity checks.

Model design:
  - Min-Max normalisation (season-wide, cross-sponsor)
  - log(x+1) pre-transform for YouTube sponsor views
  - Inverse formula for Finish Position (lower finish = higher score)
  - Binary ×100 flags for Wins and Playoffs
  - Weighted sum aggregation (see config.py for weights)

Author  : Anshul Ghildiyal
Project : NY Racing Sponsorship Intelligence, 2024 Season
"""

import warnings
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(levelname)s — %(message)s")
log = logging.getLogger(__name__)

from config import (
    MASTER_DATASET, SCORED_DATASET, FIGURES_PATH, BRAND_COLORS, PLOT_DPI, PLOT_STYLE,
    VARIABLE_WEIGHTS, SPONSORS,
)

plt.style.use(PLOT_STYLE)

# ─── NORMALISATION HELPERS ───────────────────────────────────────────────────

def minmax_scale(series: pd.Series) -> pd.Series:
    """Season-wide min-max normalisation to [0, 100]."""
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (series - mn) / (mx - mn) * 100


def inverse_minmax(series: pd.Series) -> pd.Series:
    """
    Inverse min-max for finish_position: lower (better) finish → higher score.
    Position 1 maps to 100; worst position maps to 0.
    """
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series(np.full(len(series), 50.0), index=series.index)
    return (mx - series) / (mx - mn) * 100


def log_transform_scale(series: pd.Series) -> pd.Series:
    """Apply log(x+1) then min-max scale. Used for YouTube views."""
    log_series = np.log1p(series)
    return minmax_scale(log_series)


# ─── SCORING MODEL ───────────────────────────────────────────────────────────

def compute_visibility_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute weekly (per-race) visibility scores for each sponsor.

    Score components:
      1. finish_position_score   — inverse min-max (weight 0.28)
      2. laps_led_score          — min-max (weight 0.12)
      3. news_weighted_score     — min-max (weight 0.30)
      4. reddit_mentions_score   — min-max (weight 0.10)
      5. youtube_views_score     — log(x+1) + min-max (weight 0.10)
      6. win_score               — binary × 100 (weight 0.06)
      7. playoff_score           — binary × 100 (weight 0.04)

    Season total = sum of 36 weekly scores.
    Theoretical max = 100 × 36 = 3,600 pts.
    """
    df = df.copy()
    log.info("Computing visibility scores for %d records...", len(df))

    # ── Component scores (season-wide normalisation) ──────────────────────────
    df["finish_position_score"] = inverse_minmax(df["finish_position"])
    df["laps_led_score"]        = minmax_scale(df["laps_led"])
    df["news_weighted_score"]   = minmax_scale(df["news_weighted_mentions"])
    df["reddit_mentions_score"] = minmax_scale(df["reddit_mentions"])
    df["youtube_views_score"]   = log_transform_scale(df["youtube_sponsor_views"])
    df["win_score"]             = df["is_win"] * 100
    df["playoff_score"]         = df["is_playoff"] * 100

    # ── Weighted composite score ──────────────────────────────────────────────
    w = VARIABLE_WEIGHTS
    df["weekly_score"] = (
        df["finish_position_score"]  * w["finish_position"]        +
        df["laps_led_score"]         * w["laps_led"]               +
        df["news_weighted_score"]    * w["news_weighted_mentions"]  +
        df["reddit_mentions_score"]  * w["reddit_mentions"]        +
        df["youtube_views_score"]    * w["youtube_sponsor_views"]   +
        df["win_score"]              * w["is_win"]                  +
        df["playoff_score"]          * w["is_playoff"]
    )

    df["weekly_score"] = df["weekly_score"].clip(0, 100)

    log.info("Weekly score stats:\n%s", df["weekly_score"].describe().round(2).to_string())
    return df


def aggregate_season_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate 36 weekly scores per sponsor into season totals.
    Returns summary DataFrame with season score, avg/race, wins, etc.
    """
    agg = df.groupby("sponsor").agg(
        season_score    = ("weekly_score",    "sum"),
        avg_per_race    = ("weekly_score",    "mean"),
        wins            = ("is_win",          "sum"),
        avg_finish      = ("finish_position", "mean"),
        top5_count      = ("finish_position", lambda x: (x <= 5).sum()),
        laps_led_total  = ("laps_led",        "sum"),
        races           = ("race_id",         "nunique"),
    ).reset_index()

    agg["top5_pct"] = agg["top5_count"] / agg["races"] * 100
    agg = agg.sort_values("season_score", ascending=False).reset_index(drop=True)
    agg["visibility_rank"] = agg.index + 1
    agg["season_score"] = agg["season_score"].round(1)
    agg["avg_per_race"] = agg["avg_per_race"].round(1)
    agg["avg_finish"]   = agg["avg_finish"].round(1)
    agg["top5_pct"]     = agg["top5_pct"].round(1)

    log.info("\nSeason Visibility Scores:\n%s", agg[["sponsor","season_score","visibility_rank","wins","avg_finish","top5_pct","laps_led_total"]].to_string(index=False))
    return agg


# ─── MODEL VALIDATION ────────────────────────────────────────────────────────

def validate_model(df: pd.DataFrame, agg: pd.DataFrame) -> dict:
    """
    Run 6 model integrity checks. All should pass.

    Checks:
      1. finish_position vs season_score correlation → expect r ≈ -0.987
      2. wins vs season_score correlation            → expect r ≈ +0.983
      3. laps_led vs season_score correlation        → expect r ≈ +0.970
      4. Win / Non-win weekly score ratio            → expect ≈ 2.0×
      5. Playoff impact (H3 confirmed)               → expect −27.7%
      6. Top-5 vs Bottom-20 score ratio             → expect ≈ 2.8×
    """
    log.info("\n=== Model Validation (6 checks) ===")
    results = {}

    # Check 1: finish_position vs season_score
    r1, _ = stats.pearsonr(agg["avg_finish"], agg["season_score"])
    results["1_finish_season_r"]    = round(r1, 3)
    log.info("Check 1 — Finish vs Season Score r: %.3f (expect ~−0.987) → %s", r1, "✅" if r1 < -0.90 else "⚠️")

    # Check 2: wins vs season_score
    r2, _ = stats.pearsonr(agg["wins"], agg["season_score"])
    results["2_wins_season_r"]      = round(r2, 3)
    log.info("Check 2 — Wins vs Season Score r:   %.3f (expect ~+0.983) → %s", r2, "✅" if r2 > 0.90 else "⚠️")

    # Check 3: laps_led vs season_score
    r3, _ = stats.pearsonr(agg["laps_led_total"], agg["season_score"])
    results["3_laps_season_r"]      = round(r3, 3)
    log.info("Check 3 — Laps vs Season Score r:   %.3f (expect ~+0.970) → %s", r3, "✅" if r3 > 0.90 else "⚠️")

    # Check 4: win/non-win weekly score ratio
    win_avg    = df[df["is_win"] == 1]["weekly_score"].mean()
    nonwin_avg = df[df["is_win"] == 0]["weekly_score"].mean()
    ratio4 = win_avg / nonwin_avg if nonwin_avg else 0
    results["4_win_nonwin_ratio"]   = round(ratio4, 2)
    log.info("Check 4 — Win/Non-Win weekly score: %.2f× (expect ~2.0×) → %s", ratio4, "✅" if 1.5 <= ratio4 <= 3.0 else "⚠️")

    # Check 5: playoff impact
    reg_avg     = df[df["is_playoff"] == 0]["weekly_score"].mean()
    playoff_avg = df[df["is_playoff"] == 1]["weekly_score"].mean()
    pct_change  = (playoff_avg - reg_avg) / reg_avg * 100
    results["5_playoff_impact_pct"] = round(pct_change, 1)
    log.info("Check 5 — Playoff vs Regular Score: %+.1f%% (expect −27.7%%) → %s", pct_change, "✅" if pct_change < 0 else "⚠️")

    # Check 6: top-5 vs bottom-20
    top5_avg   = df[df["finish_position"].between(1, 5)]["weekly_score"].mean()
    bot20_avg  = df[df["finish_position"] > 20]["weekly_score"].mean()
    ratio6 = top5_avg / bot20_avg if bot20_avg else 0
    results["6_top5_vs_bottom20"]   = round(ratio6, 2)
    log.info("Check 6 — Top-5 vs Bottom-20 score: %.2f× (expect ~2.8×) → %s", ratio6, "✅" if ratio6 >= 2.0 else "⚠️")

    passed = sum([
        r1 < -0.90,
        r2 > 0.90,
        r3 > 0.90,
        1.5 <= ratio4 <= 3.0,
        pct_change < 0,
        ratio6 >= 2.0,
    ])
    log.info("\n%d/6 validation checks passed.", passed)
    results["checks_passed"] = passed
    return results


# ─── VISUALISATIONS ──────────────────────────────────────────────────────────

def plot_season_scores(agg: pd.DataFrame):
    """Chart 6: Horizontal bar chart of season visibility scores."""
    fig, ax = plt.subplots(figsize=(10, 5))
    colors  = [BRAND_COLORS[s] for s in agg["sponsor"]]

    bars = ax.barh(agg["sponsor"], agg["season_score"], color=colors, edgecolor="white", height=0.6)
    ax.invert_yaxis()

    for bar, score in zip(bars, agg["season_score"]):
        ax.text(bar.get_width() + 10, bar.get_y() + bar.get_height()/2,
                f"{score:.0f} pts", va="center", fontsize=10, weight="bold")

    ax.axvline(x=agg["season_score"].max(), color="gray", linestyle=":", alpha=0.4)
    ax.set_xlabel("Season Visibility Score (max 3,600 pts)", fontsize=11)
    ax.set_title("2024 NASCAR Sponsorship Visibility Rankings\n5 Sponsors · 36 Races · Composite Model", fontsize=13, weight="bold")
    ax.set_xlim(0, agg["season_score"].max() * 1.18)
    ax.spines[["top","right"]].set_visible(False)

    plt.tight_layout()
    plt.savefig(f"{FIGURES_PATH}06_season_visibility_scores.png", dpi=PLOT_DPI)
    plt.close()
    log.info("Saved: 06_season_visibility_scores.png")


def plot_weekly_score_distribution(df: pd.DataFrame):
    """Chart 7: Box plots of weekly scores per sponsor."""
    fig, ax = plt.subplots(figsize=(11, 5))
    sponsor_order = (
        df.groupby("sponsor")["weekly_score"].median()
        .sort_values(ascending=False).index.tolist()
    )
    data   = [df[df["sponsor"] == s]["weekly_score"].values for s in sponsor_order]
    colors = [BRAND_COLORS[s] for s in sponsor_order]

    bp = ax.boxplot(data, labels=sponsor_order, patch_artist=True,
                    medianprops={"color": "black", "linewidth": 2},
                    whiskerprops={"linewidth": 1.5},
                    flierprops={"marker": "o", "markersize": 4, "alpha": 0.5})

    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.8)

    ax.set_ylabel("Weekly Visibility Score (0–100)", fontsize=11)
    ax.set_title("Distribution of Weekly Scores — 2024 Season\n(each box = 36 races)", fontsize=12, weight="bold")
    ax.set_xticklabels(sponsor_order, rotation=15, ha="right")
    ax.spines[["top","right"]].set_visible(False)

    plt.tight_layout()
    plt.savefig(f"{FIGURES_PATH}07_weekly_score_distribution.png", dpi=PLOT_DPI)
    plt.close()
    log.info("Saved: 07_weekly_score_distribution.png")


def plot_radar_chart(agg: pd.DataFrame):
    """Chart 8: Spider/radar chart of normalised metrics per sponsor."""
    metrics = ["avg_per_race", "wins", "top5_pct", "laps_led_total", "avg_finish"]
    labels  = ["Avg Score/Race", "Wins", "Top-5 %", "Laps Led (scaled)", "Avg Finish (inv)"]

    # Normalise each metric to [0,1]
    norm = agg.copy()
    for m in metrics:
        mn, mx = norm[m].min(), norm[m].max()
        if m == "avg_finish":
            norm[m] = (mx - norm[m]) / (mx - mn) if mx != mn else 0.5
        else:
            norm[m] = (norm[m] - mn) / (mx - mn) if mx != mn else 0.5

    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={"projection": "polar"})

    for _, row in norm.iterrows():
        values = [row[m] for m in metrics]
        values += values[:1]
        ax.plot(angles, values, "o-", linewidth=2, color=BRAND_COLORS[row["sponsor"]], label=row["sponsor"])
        ax.fill(angles, values, alpha=0.08, color=BRAND_COLORS[row["sponsor"]])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, size=9)
    ax.set_yticks([0.25, 0.50, 0.75, 1.0])
    ax.set_yticklabels(["25%","50%","75%","100%"], size=8)
    ax.set_title("Sponsor Performance Radar — 2024 Season", size=13, weight="bold", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=9)

    plt.tight_layout()
    plt.savefig(f"{FIGURES_PATH}08_sponsor_radar.png", dpi=PLOT_DPI)
    plt.close()
    log.info("Saved: 08_sponsor_radar.png")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    import os
    os.makedirs(FIGURES_PATH, exist_ok=True)

    # Load master dataset
    df = pd.read_csv(MASTER_DATASET)
    log.info("Master dataset loaded: %d rows", len(df))

    # Compute weekly scores
    df_scored = compute_visibility_scores(df)

    # Aggregate to season level
    agg = aggregate_season_scores(df_scored)

    # Validate model
    validation = validate_model(df_scored, agg)

    # Save scored dataset
    df_scored.to_csv(SCORED_DATASET, index=False)
    log.info("Scored dataset saved → %s", SCORED_DATASET)

    # Visualisations
    plot_season_scores(agg)
    plot_weekly_score_distribution(df_scored)
    plot_radar_chart(agg)

    print("\n" + "="*60)
    print("  VISIBILITY SCORE RESULTS")
    print("="*60)
    print(agg[[
        "visibility_rank","sponsor","season_score","avg_per_race",
        "wins","avg_finish","top5_pct","laps_led_total"
    ]].to_string(index=False))

    print(f"\n  Validation: {validation['checks_passed']}/6 checks passed")
    print("✅ Scoring model complete.")
    return df_scored, agg


if __name__ == "__main__":
    main()
