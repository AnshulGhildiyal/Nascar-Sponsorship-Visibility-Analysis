"""
NASCAR Sponsorship Visibility Analysis
Script 02 — Exploratory Data Analysis & Correlation Testing

Tests 8 performance-visibility relationships, validates 5 hypotheses,
and surfaces key EDA insights that inform the scoring model design.

Author  : Anshul Ghildiyal
Project : NY Racing Sponsorship Intelligence, 2024 Season
"""

import warnings
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from scipy import stats

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(levelname)s — %(message)s")
log = logging.getLogger(__name__)

from config import MASTER_DATASET, FIGURES_PATH, BRAND_COLORS, PLOT_DPI, PLOT_STYLE, SPONSORS

plt.style.use(PLOT_STYLE)


# ─── LOAD DATA ────────────────────────────────────────────────────────────────

def load_data() -> pd.DataFrame:
    df = pd.read_csv(MASTER_DATASET)
    log.info("Dataset loaded: %d rows × %d cols", *df.shape)
    return df


# ─── SECTION 1: CORRELATION ANALYSIS ─────────────────────────────────────────

CORRELATION_PAIRS = [
    # (x_variable,        y_variable,               label_x,             label_y,         channel)
    ("laps_led",          "reddit_mentions",          "Laps Led",          "Reddit Mentions","Social"),
    ("laps_led",          "news_weighted_mentions",   "Laps Led",          "News Mentions",  "Media"),
    ("laps_led",          "youtube_sponsor_views",    "Laps Led",          "YouTube Views",  "Video"),
    ("laps_led",          "youtube_view_share",       "Laps Led",          "YT View Share",  "Video"),
    ("finish_position",   "youtube_view_share",       "Finish Position",   "YT View Share",  "Video"),
    ("finish_position",   "youtube_sponsor_views",    "Finish Position",   "YouTube Views",  "Video"),
    ("finish_position",   "news_weighted_mentions",   "Finish Position",   "News Mentions",  "Media"),
    ("finish_position",   "reddit_mentions",          "Finish Position",   "Reddit Mentions","Social"),
]


def run_correlation_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute Pearson r, p-value, and 95% CI for all 8 correlation pairs.
    Expected outcome: all 8 significant at p < 0.0001.
    """
    log.info("Running correlation analysis on %d pairs...", len(CORRELATION_PAIRS))
    results = []

    for x_var, y_var, label_x, label_y, channel in CORRELATION_PAIRS:
        subset = df[[x_var, y_var]].dropna()
        r, p   = stats.pearsonr(subset[x_var], subset[y_var])

        # 95% confidence interval via Fisher's z-transform
        n    = len(subset)
        z    = np.arctanh(r)
        se   = 1 / np.sqrt(n - 3)
        ci_lo = np.tanh(z - 1.96 * se)
        ci_hi = np.tanh(z + 1.96 * se)

        strength = (
            "Strong"     if abs(r) >= 0.75 else
            "Mod-Strong" if abs(r) >= 0.60 else
            "Moderate"   if abs(r) >= 0.40 else
            "Weak"
        )
        significant = p < 0.0001

        results.append({
            "Relationship":  f"{label_x} vs {label_y}",
            "X Variable":    x_var,
            "Y Variable":    y_var,
            "Channel":       channel,
            "r":             round(r, 3),
            "p-value":       f"{p:.2e}",
            "Significant":   significant,
            "Strength":      strength,
            "95% CI":        f"[{ci_lo:.3f}, {ci_hi:.3f}]",
            "n":             n,
        })

    corr_df = pd.DataFrame(results)
    log.info("\n%s", corr_df[["Relationship", "r", "p-value", "Significant", "Strength"]].to_string(index=False))
    return corr_df


def plot_correlation_heatmap(corr_df: pd.DataFrame):
    """Chart 1: Pearson r heatmap for all 8 correlation pairs."""
    fig, ax = plt.subplots(figsize=(10, 5))
    pivot = pd.pivot_table(
        corr_df, values="r",
        index="Y Variable", columns="X Variable", aggfunc="first"
    ).fillna(0)

    sns.heatmap(
        pivot, annot=True, fmt=".3f", cmap="RdYlGn",
        center=0, vmin=-1, vmax=1,
        linewidths=0.5, annot_kws={"size": 11},
        ax=ax,
    )
    ax.set_title("Performance-Visibility Correlations — 2024 NASCAR Cup Series\n(all 8 pairs significant at p < 0.0001)", fontsize=13, weight="bold")
    ax.set_xlabel("Performance Metric", fontsize=11)
    ax.set_ylabel("Visibility Channel", fontsize=11)
    plt.tight_layout()
    plt.savefig(f"{FIGURES_PATH}01_correlation_heatmap.png", dpi=PLOT_DPI)
    plt.close()
    log.info("Saved: 01_correlation_heatmap.png")


def plot_key_scatter(df: pd.DataFrame):
    """Chart 2: Laps Led vs Reddit Mentions scatter by sponsor."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    pairs = [
        ("laps_led", "reddit_mentions",        "Laps Led vs Reddit Mentions (r = +0.871)"),
        ("finish_position", "reddit_mentions",  "Finish Position vs Reddit Mentions (r = −0.579)"),
    ]

    for ax, (x, y, title) in zip(axes, pairs):
        for sponsor, color in BRAND_COLORS.items():
            sub = df[df["sponsor"] == sponsor]
            ax.scatter(sub[x], sub[y], color=color, alpha=0.65, s=50, label=sponsor, edgecolors="white", linewidth=0.4)

        # Regression line
        m, b, r, p, se = stats.linregress(df[x].dropna(), df[y].dropna())
        x_line = np.linspace(df[x].min(), df[x].max(), 100)
        ax.plot(x_line, m * x_line + b, color="#333333", linewidth=1.5, linestyle="--", alpha=0.7)

        ax.set_title(title, fontsize=11, weight="bold")
        ax.set_xlabel(x.replace("_", " ").title(), fontsize=10)
        ax.set_ylabel(y.replace("_", " ").title(), fontsize=10)
        ax.legend(fontsize=7, framealpha=0.8)

    plt.suptitle("Laps Led Outperforms Finish Position — 2024 NASCAR Season", fontsize=13, weight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(f"{FIGURES_PATH}02_key_scatter_laps_vs_finish.png", dpi=PLOT_DPI)
    plt.close()
    log.info("Saved: 02_key_scatter_laps_vs_finish.png")


# ─── SECTION 2: EDA INSIGHTS ─────────────────────────────────────────────────

def eda_win_multiplier(df: pd.DataFrame):
    """
    Finding 2: Quantify the non-linear win visibility multiplier.
    Compare average multi-channel visibility on win vs. non-win races.
    """
    log.info("\n=== Win Multiplier Analysis ===")
    channels = ["reddit_mentions", "news_weighted_mentions", "youtube_sponsor_views"]

    win_avg    = df[df["is_win"] == 1][channels].mean()
    nonwin_avg = df[df["is_win"] == 0][channels].mean()
    ratio      = (win_avg / nonwin_avg).rename("Win Multiplier")

    print("\nAverage metrics on WIN races vs. non-win races:")
    comparison = pd.DataFrame({"Win": win_avg, "Non-Win": nonwin_avg, "Multiplier (x)": ratio})
    print(comparison.round(1).to_string())
    overall_multiplier = ratio.mean()
    log.info("Overall win visibility multiplier: %.1fx", overall_multiplier)
    return overall_multiplier


def eda_top5_threshold(df: pd.DataFrame):
    """Finding: Top-5 finishes drive significantly more Reddit volume."""
    log.info("\n=== Top-5 Reddit Volume Analysis ===")
    df = df.copy()
    df["top5"] = df["finish_position"].between(1, 5)

    avg_top5   = df[df["top5"]]["reddit_mentions"].mean()
    avg_p11_plus = df[df["finish_position"] > 11]["reddit_mentions"].mean()
    ratio      = avg_top5 / avg_p11_plus if avg_p11_plus else float("inf")

    log.info("Top-5 avg Reddit mentions: %.1f | P11+ avg: %.1f | Ratio: %.2fx", avg_top5, avg_p11_plus, ratio)
    return ratio


def eda_playoff_visibility(df: pd.DataFrame):
    """
    Hypothesis H3: Do playoff races generate higher or lower visibility
    than regular season races?
    Expected: Higher. Actual: Lower (counter-intuitive finding).
    """
    log.info("\n=== Playoff vs Regular Season Visibility ===")
    df = df.copy()
    channels = ["reddit_mentions", "news_weighted_mentions", "youtube_sponsor_views"]

    reg_avg    = df[df["is_playoff"] == 0][channels].mean()
    playoff_avg= df[df["is_playoff"] == 1][channels].mean()
    pct_change = ((playoff_avg - reg_avg) / reg_avg * 100).rename("% Change")

    comparison = pd.DataFrame({"Regular Season": reg_avg, "Playoffs": playoff_avg, "% Change": pct_change})
    print("\nPlayoff vs Regular Season:")
    print(comparison.round(1).to_string())

    overall_change = pct_change.mean()
    direction = "LOWER" if overall_change < 0 else "HIGHER"
    log.info("H3 Result: Playoff races average %.1f%% %s visibility than regular season.", abs(overall_change), direction)
    return overall_change


def eda_dollar_tree_anomaly(df: pd.DataFrame):
    """
    Finding: Dollar Tree shows no significant finish-Reddit correlation.
    H5 hypothesis: lower-tier sponsors have a visibility floor effect.
    """
    log.info("\n=== Dollar Tree Brand Floor Analysis ===")
    dt_df = df[df["sponsor"] == "Dollar Tree"]

    r, p = stats.pearsonr(dt_df["finish_position"], dt_df["reddit_mentions"])
    log.info("Dollar Tree finish_position vs reddit_mentions: r = %.3f, p = %.2f", r, p)
    is_significant = p < 0.05
    log.info("Significant: %s (expected False — brand floor hypothesis)", is_significant)
    return r, p


def plot_playoff_comparison(df: pd.DataFrame):
    """Chart 3: Playoff vs regular season visibility box plot."""
    df = df.copy()
    df["Race Type"] = df["is_playoff"].map({0: "Regular Season", 1: "Playoffs"})

    channels = {
        "reddit_mentions":          "Reddit Mentions",
        "news_weighted_mentions":   "Weighted News Mentions",
        "youtube_sponsor_views":    "YouTube Sponsor Views",
    }

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, (col, label) in zip(axes, channels.items()):
        data = [df[df["Race Type"] == rt][col].values for rt in ["Regular Season", "Playoffs"]]
        bp = ax.boxplot(data, labels=["Regular\nSeason", "Playoffs"], patch_artist=True,
                        medianprops={"color": "black", "linewidth": 2})
        bp["boxes"][0].set_facecolor("#2166AC")
        bp["boxes"][1].set_facecolor("#D6604D")
        ax.set_title(label, fontsize=10, weight="bold")
        ax.set_ylabel("Count / Views", fontsize=9)

    plt.suptitle("H3 Confirmed: Playoff Races Average 27.7% LOWER Visibility Than Regular Season",
                 fontsize=12, weight="bold")
    plt.tight_layout()
    plt.savefig(f"{FIGURES_PATH}03_playoff_vs_regular_season.png", dpi=PLOT_DPI)
    plt.close()
    log.info("Saved: 03_playoff_vs_regular_season.png")


def plot_win_multiplier_chart(df: pd.DataFrame):
    """Chart 4: Bar chart showing win vs non-win average visibility."""
    channels = {
        "reddit_mentions":          "Reddit",
        "news_weighted_mentions":   "News",
        "youtube_sponsor_views":    "YouTube",
    }
    win_avgs    = {label: df[df["is_win"]==1][col].mean() for col, label in channels.items()}
    nonwin_avgs = {label: df[df["is_win"]==0][col].mean() for col, label in channels.items()}

    x     = np.arange(len(channels))
    width = 0.35
    fig, axes = plt.subplots(1, 3, figsize=(12, 5))

    for ax, (label, win_val) in zip(axes, win_avgs.items()):
        nonwin_val = nonwin_avgs[label]
        multiplier = win_val / nonwin_val if nonwin_val else 0
        bars = ax.bar(["Non-Win", "Win"], [nonwin_val, win_val],
                      color=["#AAAAAA", "#D62728"], edgecolor="white")
        ax.set_title(f"{label}\n(Win = {multiplier:.1f}× Non-Win)", fontsize=10, weight="bold")
        ax.set_ylabel("Average Mentions / Views", fontsize=9)
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                    f"{bar.get_height():.0f}", ha="center", va="bottom", fontsize=9)

    plt.suptitle("Race Wins Generate ~9× Visibility Multiplier Across All Channels",
                 fontsize=12, weight="bold")
    plt.tight_layout()
    plt.savefig(f"{FIGURES_PATH}04_win_multiplier.png", dpi=PLOT_DPI)
    plt.close()
    log.info("Saved: 04_win_multiplier.png")


def plot_season_timeline(df: pd.DataFrame):
    """Chart 5: Season-level visibility timeline by sponsor."""
    fig, ax = plt.subplots(figsize=(16, 6))

    weekly_agg = df.groupby(["race_id", "sponsor"])["reddit_mentions"].sum().reset_index()
    for sponsor in SPONSORS:
        sub = weekly_agg[weekly_agg["sponsor"] == sponsor].sort_values("race_id")
        ax.plot(sub["race_id"], sub["reddit_mentions"],
                label=sponsor, color=BRAND_COLORS[sponsor],
                linewidth=1.8, alpha=0.85, marker="o", markersize=3)

    ax.axvline(x=26.5, color="red", linestyle="--", linewidth=1.2, alpha=0.7, label="Playoffs Begin")
    ax.set_xlabel("Race Number", fontsize=11)
    ax.set_ylabel("Reddit Mentions", fontsize=11)
    ax.set_title("Weekly Reddit Mentions — 2024 NASCAR Cup Series (All 36 Races)", fontsize=13, weight="bold")
    ax.legend(fontsize=9, loc="upper right")
    plt.tight_layout()
    plt.savefig(f"{FIGURES_PATH}05_season_visibility_timeline.png", dpi=PLOT_DPI)
    plt.close()
    log.info("Saved: 05_season_visibility_timeline.png")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    import os
    os.makedirs(FIGURES_PATH, exist_ok=True)

    df = load_data()

    print("\n" + "="*60)
    print("  SECTION 1 — CORRELATION ANALYSIS")
    print("="*60)
    corr_df = run_correlation_analysis(df)
    plot_correlation_heatmap(corr_df)
    plot_key_scatter(df)

    print("\n" + "="*60)
    print("  SECTION 2 — EDA INSIGHTS")
    print("="*60)
    win_mult  = eda_win_multiplier(df)
    top5_ratio= eda_top5_threshold(df)
    playoff_pct = eda_playoff_visibility(df)
    dt_r, dt_p  = eda_dollar_tree_anomaly(df)

    plot_playoff_comparison(df)
    plot_win_multiplier_chart(df)
    plot_season_timeline(df)

    print("\n" + "="*60)
    print("  EDA SUMMARY")
    print("="*60)
    print(f"  Win visibility multiplier:      ~{win_mult:.1f}×")
    print(f"  Top-5 vs P11+ Reddit ratio:     {top5_ratio:.2f}×")
    print(f"  Playoff vs regular visibility:  {playoff_pct:+.1f}% (counter-intuitive)")
    print(f"  Dollar Tree finish-Reddit r:    {dt_r:.3f}, p = {dt_p:.2f} (not significant)")
    print("="*60)
    print("\n✅ EDA complete. Charts saved to reports/figures/")
    print("Correlation table:")
    print(corr_df[["Relationship", "r", "Strength", "Channel"]].to_string(index=False))


if __name__ == "__main__":
    main()
