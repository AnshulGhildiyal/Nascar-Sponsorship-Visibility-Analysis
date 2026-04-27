"""
NASCAR Sponsorship Visibility Analysis — Central Configuration
Author: Anshul Ghildiyal
Project: NY Racing Sponsorship Intelligence, 2024 Season
"""
import os
from dotenv import load_dotenv

load_dotenv() 

# ─── API CREDENTIALS (set as environment variables, never commit real keys) ───
YOUTUBE_API_KEY   = os.getenv("YOUTUBE_API_KEY")
REDDIT_CLIENT_ID  = os.getenv("REDDIT_CLIENT_ID")
REDDIT_SECRET     = os.getenv("REDDIT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")

# ─── SPONSORS & CARS ──────────────────────────────────────────────────────────
SPONSORS = {
    "NAPA Auto Parts":   {"car": "#9",  "driver": "Chase Elliott",   "team": "Hendrick Motorsports",  "tier": "elite",  "est_cost_M": 22.0,  "cost_range_M": (18.0, 26.0)},
    "Monster Energy":    {"car": "#45", "driver": "Tyler Reddick",   "team": "23XI Racing",           "tier": "comp",   "est_cost_M": 17.5,  "cost_range_M": (14.0, 21.0)},
    "Fastenal":          {"car": "#17", "driver": "Chris Buescher",  "team": "RFK Racing",            "tier": "mid",    "est_cost_M": 11.0,  "cost_range_M": (8.0,  14.0)},
    "Love's Travel Stops":{"car":"#34", "driver": "Todd Gilliland",  "team": "Front Row Motorsports", "tier": "lower",  "est_cost_M":  5.5,  "cost_range_M": (3.5,   7.5)},
    "Dollar Tree":       {"car": "#36", "driver": "Zane Smith",      "team": "Front Row Motorsports", "tier": "lower",  "est_cost_M":  6.0,  "cost_range_M": (4.0,   8.5)},
}

# ─── SEASON PARAMETERS ────────────────────────────────────────────────────────
SEASON          = 2024
TOTAL_RACES     = 36
PLAYOFF_START   = 26        # Race index where playoffs begin (0-indexed: race 27 in calendar)
PLAYOFF_RACES   = [26, 27, 28, 29, 30, 31, 32, 33, 34, 35]  # Indices of playoff races
CHARTER_DISPUTE_RACES_23XI = list(range(19, 28))             # Races 20-28 (0-indexed)

# ─── MODEL WEIGHTS (BASELINE — 40/30/20/10) ───────────────────────────────────
CATEGORY_WEIGHTS = {
    "race_performance": 0.40,
    "media_coverage":   0.30,
    "social_engagement":0.20,
    "special_events":   0.10,
}

# Effective variable weights within the 0-100 weekly score
VARIABLE_WEIGHTS = {
    "finish_position":        0.28,   # inverse: lower finish = higher score
    "laps_led":               0.12,
    "news_weighted_mentions": 0.30,
    "reddit_mentions":        0.10,
    "youtube_sponsor_views":  0.10,   # log(x+1) pre-transform
    "is_win":                 0.06,   # binary flag × 100
    "is_playoff":             0.04,   # binary flag × 100
}

# ─── SENSITIVITY SCENARIOS ───────────────────────────────────────────────────
WEIGHT_SCENARIOS = {
    "Baseline":          {"race_performance": 0.40, "media_coverage": 0.30, "social_engagement": 0.20, "special_events": 0.10},
    "Performance Heavy": {"race_performance": 0.50, "media_coverage": 0.25, "social_engagement": 0.15, "special_events": 0.10},
    "Media Heavy":       {"race_performance": 0.30, "media_coverage": 0.40, "social_engagement": 0.20, "special_events": 0.10},
    "Equal Weights":     {"race_performance": 0.25, "media_coverage": 0.25, "social_engagement": 0.25, "special_events": 0.25},
}

# ─── COST SCENARIOS ───────────────────────────────────────────────────────────
COST_SCENARIOS = {
    "low":  {s: v["cost_range_M"][0] for s, v in SPONSORS.items()},
    "mid":  {s: v["est_cost_M"]       for s, v in SPONSORS.items()},
    "high": {s: v["cost_range_M"][1] for s, v in SPONSORS.items()},
}

# ─── PATHS ────────────────────────────────────────────────────────────────────
RAW_DATA_PATH          = "data/raw/"
PROCESSED_DATA_PATH    = "data/processed/"
FIGURES_PATH           = "reports/figures/"

RAW_RACE_RESULTS       = RAW_DATA_PATH + "race_results_2024.csv"
RAW_REDDIT_DATA        = RAW_DATA_PATH + "reddit_mentions_2024.csv"
RAW_YOUTUBE_DATA       = RAW_DATA_PATH + "youtube_metrics_2024.csv"
RAW_NEWS_DATA          = RAW_DATA_PATH + "news_mentions_2024.csv"

MASTER_DATASET         = PROCESSED_DATA_PATH + "master_dataset.csv"
SCORED_DATASET         = PROCESSED_DATA_PATH + "scored_dataset.csv"
EFFICIENCY_RANKINGS    = PROCESSED_DATA_PATH + "efficiency_rankings.csv"

# ─── VISUALIZATION STYLE ──────────────────────────────────────────────────────
BRAND_COLORS = {
    "NAPA Auto Parts":    "#003087",
    "Monster Energy":     "#00D924",
    "Fastenal":           "#FF6B00",
    "Love's Travel Stops":"#CC0000",
    "Dollar Tree":        "#6B3D8F",
}
PLOT_DPI     = 150
PLOT_STYLE   = "seaborn-v0_8-whitegrid"
