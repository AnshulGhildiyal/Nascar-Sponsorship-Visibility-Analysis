# 🏁 NASCAR Sponsorship Visibility Analysis — 2024 Season

**Who pays for visibility — and who actually gets it?**

A quantitative, data-driven analysis of NASCAR Cup Series primary sponsorships across **5 sponsors**, **36 races**, and **180 race records** from the full 2024 season. Built for NY Racing (Contact: Sarah Mitchell, VP of Partnerships) to replace intuition-driven sponsorship decisions with a reproducible, multi-channel visibility model.

**Primary Finding:** Monster Energy delivers near-maximum visibility (#2, 1,343 pts) at only 7% below peak efficiency — the only sponsor defensible to both the CMO and the CFO simultaneously.

---

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Key Findings](#key-findings)
- [Results at a Glance](#results-at-a-glance)
- [Methodology](#methodology)
- [Repository Structure](#repository-structure)
- [Getting Started](#getting-started)
- [Pipeline Walkthrough](#pipeline-walkthrough)
- [Visualisations](#visualisations)
- [Limitations & Future Work](#limitations--future-work)
- [About](#about)

---

## Project Overview

NASCAR sponsorship decisions have historically been driven by relationships and gut instinct rather than quantitative visibility data. This project builds — from scratch — the **first cross-channel composite visibility scoring model** for primary NASCAR Cup Series sponsors, enabling objective comparison across vastly different cost tiers.

### Sponsors Tracked

| Sponsor | Car | Driver | Team | Tier |
|---|---|---|---|---|
| NAPA Auto Parts | #9 | Chase Elliott | Hendrick Motorsports | Elite |
| Monster Energy | #45 | Tyler Reddick | 23XI Racing | Competitive |
| Fastenal | #17 | Chris Buescher | RFK Racing | Mid |
| Love's Travel Stops | #34 | Todd Gilliland | Front Row Motorsports | Lower |
| Dollar Tree | #36 | Zane Smith | Front Row Motorsports | Lower |

### Data Collected

| Source | What | Confidence |
|---|---|---|
| Kaggle + Racing-Reference | Race results (36 races) | High |
| Reddit PRAW API (r/NASCAR) | Brand mentions in post-race threads | Med-High |
| YouTube Data API v3 | Sponsor-tagged highlight views | Med-High |
| Google News (quality-weighted) | News coverage by tier | Medium |
| Forbes / SBJ / HardHead Mktg | Sponsorship cost estimates | Low-Med ⚠ |

---

## Key Findings

### 1. Laps Led Beats Finish Position — Every Time

The biggest assumption going in was wrong. Finish position was assumed to be the primary visibility driver. Instead, **Laps Led outperformed Finish Position by 0.24–0.29 correlation points on every channel** (all 8 pairs significant at p < 0.0001):

| Relationship | r | Channel |
|---|---|---|
| Laps Led → Reddit Mentions | +0.871 | Social |
| Laps Led → News Mentions | +0.864 | Media |
| Laps Led → YouTube Views | +0.854 | Video |
| Finish Position → Reddit Mentions | −0.579 | Social |
| Finish Position → News Mentions | −0.585 | Media |
| Finish Position → YouTube Views | −0.615 | Video |

**Why?** Leading laps means sustained front-of-field camera time for hundreds of miles. A race finish is a single late-stage event. The car *at the front* for hours is worth more than the car that *wins in the final corner*.

### 2. Race Wins Generate a ~9× Visibility Multiplier

A win is not simply a very good finish. It triggers **disproportionate, simultaneous coverage across all three channels** — Reddit, news, and YouTube — at roughly 9× the average non-win race. This non-linear spike cannot be replicated by consistent top-10 finishes.

### 3. Elite Teams Sell Exposure at a Premium That Compresses ROI

NAPA Auto Parts leads raw visibility (1,363 pts) but ranks **last in efficiency** (62.0 pts/$M) due to its ~$22M estimated cost. Sponsors can achieve 82.0 pts/$M (Love's), 77.5 pts/$M (Fastenal), or 76.8 pts/$M (Monster Energy) — all dramatically more efficient per dollar.

### 4. Playoff Races Average 27.7% *Lower* Visibility Than Regular Season (Confirmed H3)

Counter to every intuitive expectation: playoff races, despite higher on-track stakes, generate significantly less sponsor visibility across social and media channels. Likely driven by fewer casual viewers and a shrinking regular-season audience. This finding directly informs playoff weighting in model v1.1.

---

## Results at a Glance

### Season Visibility Scores

| Rank | Sponsor | Season Score | Avg/Race | Wins | Avg Finish | Top-5% | Laps Led |
|---|---|---|---|---|---|---|---|
| #1 | NAPA Auto Parts | 1,363 | 37.9 | 4 | 10.0 | 33.3% | 770 |
| #2 | Monster Energy | 1,343 | 37.3 | 4 | 9.2 | 38.9% | 641 |
| #3 | Fastenal | 853 | 23.7 | 1 | 16.0 | 11.1% | 144 |
| #4 | Love's Travel Stops | 451 | 12.5 | 0 | 25.7 | 0.0% | 0 |
| #5 | Dollar Tree | 410 | 11.4 | 0 | 27.6 | 0.0% | 0 |

*Theoretical max: 3,600 pts. Season-wide min-max normalisation.*

### Efficiency Rankings (Mid-Cost Scenario)

| Rank | Sponsor | Efficiency | Cost/Point | Est. Cost | Cost Sensitivity |
|---|---|---|---|---|---|
| #1 | Love's Travel Stops | 82.0 pts/$M | $12,191 | $5.5M | ±3 rank swing |
| #2 | Fastenal | 77.5 pts/$M | $12,902 | $11M | **0 rank swing** |
| #3 | Monster Energy | 76.8 pts/$M | $13,028 | $17.5M | ±3 rank swing |
| #4 | Dollar Tree | 68.4 pts/$M | $14,622 | $6M | ±2 rank swing |
| #5 | NAPA Auto Parts | 62.0 pts/$M | $16,137 | $22M | ±1 rank swing |

### Strategic Scenario Comparison

| | Scenario A | Scenario B | Scenario C ✅ |
|---|---|---|---|
| Goal | Maximize Visibility | Maximize Efficiency | **Balanced** |
| Sponsor | NAPA Auto Parts | Love's Travel Stops | **Monster Energy** |
| Visibility | 1,363 pts (100%) | 451 pts (33%) | **1,343 pts (98.5%)** |
| Efficiency | 62.0 pts/$M (76%) | 82.0 pts/$M (100%) | **76.8 pts/$M (94%)** |
| Est. Cost | $22M/yr | $5.5M/yr | **$17.5M/yr** |
| Best For | CMO / brand growth | CFO / hard ROI | **Board consensus** |

> **Recommendation for NY Racing 2026:** Scenario C (Monster Energy). If budget falls below ~$15M, pivot to Fastenal — not NAPA.

---

## Methodology

### Model Architecture

The composite visibility model scores each sponsor across each of the 36 races on a 0–100 scale, then sums to a season total (max: 3,600 pts).

**7 variables across 4 categories:**

| Variable | Category | Eff. Weight | Direction | Transform |
|---|---|---|---|---|
| `finish_position` | Race Performance | 28% | Inverse | None |
| `laps_led` | Race Performance | 12% | Direct | None |
| `news_weighted_mentions` | Media Coverage | 30% | Direct | None |
| `reddit_mentions` | Social Engagement | 10% | Direct | None |
| `youtube_sponsor_views` | Social Engagement | 10% | Direct | log(x+1) |
| `is_win` | Special Events | 6% | Binary | ×100 |
| `is_playoff` | Special Events | 4% | Binary | ×100 |

*5 variables excluded (redundant or volatile): reddit_total_score, reddit_engagement_per_mention, youtube_total_views, youtube_view_share, news_total_mentions.*

### Normalisation

- **Finish Position:** Inverse min-max — position 1 → 100, worst → 0
- **YouTube Views:** log(x+1) pre-transform, then min-max scale
- **All others:** season-wide min-max to [0, 100]
- **Win / Playoff flags:** Binary ×100 (absolute score injection)

### Validation

6/6 model integrity checks passed, 0 anomalies:

| Check | Expected | Result |
|---|---|---|
| Finish ↔ Season Score correlation | r ≈ −0.987 | ✅ |
| Wins ↔ Season Score correlation | r ≈ +0.983 | ✅ |
| Laps Led ↔ Season Score correlation | r ≈ +0.970 | ✅ |
| Win / Non-win weekly score ratio | ≈ 2.0× | ✅ |
| Playoff impact vs regular season | −27.7% | ✅ |
| Top-5 vs Bottom-20 score ratio | ≈ 2.8× | ✅ |

### Sensitivity Testing

Rankings tested across **4 weight scenarios** (Baseline / Performance Heavy / Media Heavy / Equal Weights) — **perfectly stable in all cases.** Efficiency rankings tested across 3 cost scenarios (Low / Mid / High).

---

## Repository Structure

```
nascar-sponsorship-visibility-analysis/
│
├── config.py                        # Central config: weights, sponsors, API keys, paths
│
├── src/
│   ├── 01_data_collection.py        # Reddit PRAW + YouTube API + news loading
│   ├── 02_eda_analysis.py           # Correlation analysis + 5 EDA charts
│   ├── 03_visibility_scoring_model.py  # Core scoring model + 3 charts + 6 validation checks
│   ├── 04_efficiency_analysis.py    # ROI/efficiency analysis + 3 charts
│   └── 05_sensitivity_analysis.py   # Weight & cost sensitivity + 3 charts
│
├── data/
│   ├── raw/                         # Raw API pulls (gitignored — set up your own API keys)
│   └── processed/
│       ├── master_dataset.csv       # 180 rows × 23 cols — full season data
│       ├── scored_dataset.csv       # Master + weekly visibility scores
│       └── efficiency_rankings.csv  # Efficiency table (low/mid/high cost)
│
├── reports/
│   └── figures/                     # All 14 charts (auto-generated by scripts)
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Reddit Developer Account → [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)
- Google Cloud Project with YouTube Data API v3 enabled → [console.cloud.google.com](https://console.cloud.google.com)

### Installation

```bash
git clone https://github.com/YOUR_USERNAME/nascar-sponsorship-visibility-analysis.git
cd nascar-sponsorship-visibility-analysis

python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### API Configuration

Create a `.env` file (never commit this):

```env
YOUTUBE_API_KEY=your_youtube_api_key_here
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_SECRET=your_reddit_secret
REDDIT_USER_AGENT=nascar-analysis/1.0 by u/your_username
```

Then update `config.py` to load from environment:
```python
import os
from dotenv import load_dotenv
load_dotenv()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
```

### Race Results Data

Download the 2024 NASCAR Cup Series dataset from Kaggle:
```
https://www.kaggle.com/datasets/search?q=NASCAR+2024+cup+series
```
Place it at `data/raw/race_results_2024.csv`.

---

## Pipeline Walkthrough

Run scripts sequentially:

```bash
# Step 1: Collect all data (requires API keys + Kaggle CSV)
python src/01_data_collection.py

# Step 2: EDA + correlation analysis (generates 5 charts)
python src/02_eda_analysis.py

# Step 3: Build & validate the scoring model (generates 3 charts)
python src/03_visibility_scoring_model.py

# Step 4: Efficiency / ROI analysis (generates 3 charts)
python src/04_efficiency_analysis.py

# Step 5: Sensitivity analysis (generates 3 charts)
python src/05_sensitivity_analysis.py
```

All 14 charts will be saved to `reports/figures/`.

---

## Visualisations

| # | Chart | Script |
|---|---|---|
| 01 | Correlation heatmap — all 8 pairs | `02_eda_analysis.py` |
| 02 | Scatter: Laps Led vs Finish Position on Reddit | `02_eda_analysis.py` |
| 03 | Playoff vs regular season visibility (box plot) | `02_eda_analysis.py` |
| 04 | Win multiplier bar chart (per channel) | `02_eda_analysis.py` |
| 05 | Season-long Reddit mentions timeline | `02_eda_analysis.py` |
| 06 | Season visibility scores (horizontal bar) | `03_visibility_scoring_model.py` |
| 07 | Weekly score distribution (box plots per sponsor) | `03_visibility_scoring_model.py` |
| 08 | Sponsor performance radar chart | `03_visibility_scoring_model.py` |
| 09 | Efficiency rankings bar chart | `04_efficiency_analysis.py` |
| 10 | Visibility vs efficiency scatter (bubble = cost) | `04_efficiency_analysis.py` |
| 11 | Efficiency under low/mid/high cost scenarios | `04_efficiency_analysis.py` |
| 12 | Weight sensitivity bump chart | `05_sensitivity_analysis.py` |
| 13 | Efficiency rank heatmap across cost scenarios | `05_sensitivity_analysis.py` |
| 14 | Sensitivity summary table | `05_sensitivity_analysis.py` |

---

## Limitations & Future Work

| Limitation | Impact | Planned Fix |
|---|---|---|
| Cost estimates carry ±20–30% uncertainty | Efficiency ranks could shift ±1–3 positions | Obtain actual quotes from 23XI and RFK |
| Single-season scope (2024 only) | Cannot confirm multi-year trend stability | Extend to 2022–2023 in model v1.1 |
| Proxy metrics (not direct impressions) | Captures correlates, not direct exposure | Aligned with Zoomph industry methodology |
| H5: Lower-tier floor not yet applied | Dollar Tree / Love's may be underestimated | Add baseline offset in model v1.1 |
| 23XI charter dispute (races 20–28) | Possible data anomaly for Monster Energy | Manually review those 9 races |
| Playoff weight retained at 4% | Slight overweight given negative H3 finding | Discuss weight cut with Sarah Mitchell |

---

## About

**Analyst:** Anshul Ghildiyal
**Client:** NY Racing
**Contact:** Sarah Mitchell, VP of Partnerships | Marcus (Investment Partner)
**Data Period:** 2024 NASCAR Cup Series — all 36 races
**Model Version:** v1.0

*Based on 2024 NASCAR Cup Series data. Sponsorship cost estimates derived from Forbes, Sports Business Journal, and HardHead Marketing industry benchmarks. All efficiency findings should be validated with verified cost quotes before use in negotiation.*

---

*If this analysis was useful, feel free to ⭐ the repo.*
