"""
NASCAR Sponsorship Visibility Analysis
Script 04 — Efficiency Analysis (Visibility per Dollar)

Calculates sponsor ROI across low / mid / high cost scenarios,
produces efficiency rankings, and builds the 3-scenario strategic
comparison matrix (Scenario A / B / C).

Efficiency = Season Visibility Score / Estimated Annual Cost ($M)

Author  : Anshul Ghildiyal
Project : NY Racing Sponsorship Intelligence, 2024 Season
"""

import warnings
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(levelname)s — %(message)s")
log = logging.getLogger(__name__)

from config import (
    SPONSORS, COST_SCENARIOS, SCORED_DATASET, EFFICIENCY_RANKINGS,
    FIGURES_PATH, BRAND_COLORS, PLOT_DPI, PLOT_STYLE,
)

plt.style.use(PLOT_STYLE)

# ─── LOAD DATA ────────────────────────────────────────────────────────────────

def load_season_scores(scored_path: str) -> pd.DataFrame:
    df      = pd.read_csv(scored_path)
    agg     = df.groupby("sponsor").agg(
        season_score    = ("weekly_score",    "sum"),
        wins            = ("is_win",          "sum"),
        avg_finish      = ("finish_position", "mean"),
        top5_count      = ("finish_position", lambda x: (x <= 5).sum()),
        laps_led_total  = ("laps_led",        "sum"),
    ).reset_index()
    agg["season_score"] = agg["season_score"].round(1)
    return agg


# ─── EFFICIENCY CALCULATION ───────────────────────────────────────────────────

def compute_efficiency(agg: pd.DataFrame) -> pd.DataFrame:
    """
    Compute efficiency (pts/$M) and cost-per-point for all 3 cost scenarios.
    Returns a merged efficiency table with ranks per scenario.
    """
    results = []

    for scenario, costs in COST_SCENARIOS.items():
        for _, row in agg.iterrows():
            sponsor = row["sponsor"]
            cost    = costs[sponsor]
            eff     = row["season_score"] / cost if cost > 0 else 0
            cpp     = (cost * 1_000_000) / row["season_score"] if row["season_score"] > 0 else 0
            results.append({
                "sponsor":       sponsor,
                "cost_scenario": scenario,
                "est_cost_M":    cost,
                "season_score":  row["season_score"],
                "efficiency":    round(eff, 1),
                "cost_per_point":round(cpp, 0),
            })

    eff_df = pd.DataFrame(results)

    # Rank within each scenario
    eff_df["eff_rank"] = eff_df.groupby("cost_scenario")["efficiency"].rank(ascending=False, method="min").astype(int)

    # Compute rank swing across scenarios
    pivot_rank = eff_df.pivot_table(index="sponsor", columns="cost_scenario", values="eff_rank", aggfunc="first")
    pivot_rank.columns.name = None
    pivot_rank["rank_swing"]  = pivot_rank.max(axis=1) - pivot_rank.min(axis=1)
    pivot_rank = pivot_rank.reset_index()

    # Mid-scenario as the primary reference
    mid_df = eff_df[eff_df["cost_scenario"] == "mid"].copy()
    mid_df = mid_df.merge(pivot_rank[["sponsor","rank_swing"]], on="sponsor")
    mid_df = mid_df.sort_values("eff_rank").reset_index(drop=True)

    # Attach cost range strings
    mid_df["cost_range"] = mid_df["sponsor"].map(
        lambda s: f"${SPONSORS[s]['cost_range_M'][0]}M – ${SPONSORS[s]['cost_range_M'][1]}M"
    )

    log.info("\nEfficiency Rankings (mid-cost scenario):\n%s",
             mid_df[["eff_rank","sponsor","season_score","efficiency","cost_per_point","est_cost_M","rank_swing"]].to_string(index=False))

    mid_df.to_csv(EFFICIENCY_RANKINGS, index=False)
    log.info("Efficiency rankings saved → %s", EFFICIENCY_RANKINGS)
    return eff_df, mid_df


# ─── STRATEGIC SCENARIO MATRIX ───────────────────────────────────────────────

def build_scenario_matrix(mid_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build the 3-scenario comparison:
      Scenario A — Maximize Visibility   → NAPA Auto Parts
      Scenario B — Maximize Efficiency   → Love's Travel Stops
      Scenario C — Balanced (Primary)    → Monster Energy
    """
    max_vis = mid_df["season_score"].max()
    max_eff = mid_df["efficiency"].max()

    scenario_sponsors = {
        "A — Maximize Visibility": "NAPA Auto Parts",
        "B — Maximize Efficiency": "Love's Travel Stops",
        "C — Balanced (Primary)":  "Monster Energy",
    }

    rows = []
    for label, sponsor in scenario_sponsors.items():
        row = mid_df[mid_df["sponsor"] == sponsor].iloc[0]
        rows.append({
            "Scenario":      label,
            "Best For":      {"A — Maximize Visibility": "CMO / brand growth mandate",
                              "B — Maximize Efficiency": "CFO / ROI mandate",
                              "C — Balanced (Primary)":  "Board consensus / mixed priorities"}[label],
            "Sponsor":       sponsor,
            "Visibility Score": f"{row['season_score']:.0f} pts",
            "Vis % of Max":  f"{row['season_score']/max_vis*100:.1f}%",
            "Efficiency":    f"{row['efficiency']:.1f} pts/$M",
            "Eff % of Max":  f"{row['efficiency']/max_eff*100:.1f}%",
            "Est. Cost":     f"${row['est_cost_M']:.1f}M/yr",
        })

    matrix = pd.DataFrame(rows)
    print("\n" + "="*60)
    print("  STRATEGIC SCENARIO COMPARISON")
    print("="*60)
    print(matrix.to_string(index=False))
    return matrix


# ─── VISUALISATIONS ──────────────────────────────────────────────────────────

def plot_efficiency_bars(mid_df: pd.DataFrame):
    """Chart 9: Efficiency ranking bar chart (mid-cost scenario)."""
    df = mid_df.sort_values("efficiency", ascending=True)
    colors = [BRAND_COLORS[s] for s in df["sponsor"]]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(df["sponsor"], df["efficiency"], color=colors, edgecolor="white", height=0.6)

    for bar, val in zip(bars, df["efficiency"]):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                f"{val:.1f} pts/$M", va="center", fontsize=10, weight="bold")

    ax.set_xlabel("Efficiency (Visibility Points per $M of Sponsorship Cost)", fontsize=11)
    ax.set_title("Sponsorship Efficiency Rankings — 2024 NASCAR Season\n(Mid-Cost Scenario | Efficiency = Season Score / Est. Cost)", fontsize=12, weight="bold")
    ax.set_xlim(0, df["efficiency"].max() * 1.2)
    ax.spines[["top","right"]].set_visible(False)

    plt.tight_layout()
    plt.savefig(f"{FIGURES_PATH}09_efficiency_rankings.png", dpi=PLOT_DPI)
    plt.close()
    log.info("Saved: 09_efficiency_rankings.png")


def plot_visibility_vs_efficiency(mid_df: pd.DataFrame):
    """Chart 10: 2×2 scatter — Visibility Score vs Efficiency, bubble = Cost."""
    fig, ax = plt.subplots(figsize=(10, 7))

    for _, row in mid_df.iterrows():
        sponsor  = row["sponsor"]
        color    = BRAND_COLORS[sponsor]
        bubble_s = row["est_cost_M"] * 18      # scale bubble to cost

        ax.scatter(row["season_score"], row["efficiency"],
                   s=bubble_s, color=color, alpha=0.75, edgecolors="white", linewidth=1.5, zorder=3)
        ax.annotate(sponsor.replace("Love's Travel Stops", "Love's\nTravel Stops"),
                    xy=(row["season_score"], row["efficiency"]),
                    xytext=(8, 5), textcoords="offset points", fontsize=9, weight="bold", color=color)

    # Quadrant lines
    mid_vis = mid_df["season_score"].median()
    mid_eff = mid_df["efficiency"].median()
    ax.axvline(mid_vis, color="gray", linestyle="--", alpha=0.4, linewidth=1)
    ax.axhline(mid_eff, color="gray", linestyle="--", alpha=0.4, linewidth=1)

    # Quadrant labels
    ax.text(mid_df["season_score"].max() * 0.95, mid_df["efficiency"].max() * 0.98,
            "Sweet Spot", ha="right", va="top", fontsize=9, color="#2ca02c", style="italic", alpha=0.7)
    ax.text(mid_df["season_score"].min() * 1.02, mid_df["efficiency"].min() * 1.01,
            "Avoid", ha="left", va="bottom", fontsize=9, color="#d62728", style="italic", alpha=0.7)

    ax.set_xlabel("Season Visibility Score (pts)", fontsize=11)
    ax.set_ylabel("Efficiency (pts/$M)", fontsize=11)
    ax.set_title("Visibility vs Efficiency — 2024 NASCAR Sponsors\n(Bubble size ∝ Estimated Annual Cost)", fontsize=12, weight="bold")
    ax.spines[["top","right"]].set_visible(False)

    plt.tight_layout()
    plt.savefig(f"{FIGURES_PATH}10_visibility_vs_efficiency.png", dpi=PLOT_DPI)
    plt.close()
    log.info("Saved: 10_visibility_vs_efficiency.png")


def plot_cost_sensitivity(eff_df: pd.DataFrame):
    """Chart 11: Efficiency under low / mid / high cost scenarios per sponsor."""
    pivot = eff_df.pivot_table(index="sponsor", columns="cost_scenario", values="efficiency", aggfunc="first")
    pivot = pivot[["low","mid","high"]]
    pivot = pivot.reindex(pivot["mid"].sort_values(ascending=False).index)

    fig, ax = plt.subplots(figsize=(11, 6))
    x      = np.arange(len(pivot))
    width  = 0.25
    colors = {"low": "#66C2A5", "mid": "#FC8D62", "high": "#8DA0CB"}

    for i, (scenario, color) in enumerate(colors.items()):
        bars = ax.bar(x + (i - 1) * width, pivot[scenario], width,
                      label=scenario.capitalize() + " Cost Estimate", color=color, edgecolor="white")

    ax.set_xticks(x)
    ax.set_xticklabels([s.replace("Love's Travel Stops", "Love's") for s in pivot.index], rotation=15, ha="right")
    ax.set_ylabel("Efficiency (pts/$M)", fontsize=11)
    ax.set_title("Efficiency Across Cost Scenarios — Low / Mid / High\n(Fastenal shows zero rank swing; Monster Energy most sensitive)", fontsize=12, weight="bold")
    ax.legend(fontsize=9)
    ax.spines[["top","right"]].set_visible(False)

    plt.tight_layout()
    plt.savefig(f"{FIGURES_PATH}11_cost_sensitivity.png", dpi=PLOT_DPI)
    plt.close()
    log.info("Saved: 11_cost_sensitivity.png")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    import os
    os.makedirs(FIGURES_PATH, exist_ok=True)

    # Load season scores
    agg = load_season_scores(SCORED_DATASET)

    # Compute efficiency across all cost scenarios
    eff_df, mid_df = compute_efficiency(agg)

    # Build strategic scenario matrix
    matrix = build_scenario_matrix(mid_df)

    # Visualisations
    plot_efficiency_bars(mid_df)
    plot_visibility_vs_efficiency(mid_df)
    plot_cost_sensitivity(eff_df)

    print("\n✅ Efficiency analysis complete.")
    print(f"Charts saved to {FIGURES_PATH}")
    return eff_df, mid_df, matrix


if __name__ == "__main__":
    main()
