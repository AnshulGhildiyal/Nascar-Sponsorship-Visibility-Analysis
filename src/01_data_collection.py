"""
NASCAR Sponsorship Visibility Analysis
Script 01 — Data Collection

Collects and merges race results, Reddit mentions, YouTube metrics,
and news mentions for all 5 tracked sponsors across the 2024 NASCAR
Cup Series season (36 races).

Author  : Anshul Ghildiyal
Project : NY Racing Sponsorship Intelligence, 2024 Season
Sources : Kaggle/Racing Reference, Reddit PRAW API, YouTube Data API v3, Google News
"""

import os
import time
import logging
import warnings
import pandas as pd
import numpy as np
import praw
from googleapiclient.discovery import build
from datetime import datetime, timedelta

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(levelname)s — %(message)s")
log = logging.getLogger(__name__)

from config import (
    YOUTUBE_API_KEY, REDDIT_CLIENT_ID, REDDIT_SECRET, REDDIT_USER_AGENT,
    SPONSORS, SEASON, TOTAL_RACES, RAW_DATA_PATH, MASTER_DATASET,
    RAW_RACE_RESULTS, RAW_REDDIT_DATA, RAW_YOUTUBE_DATA, RAW_NEWS_DATA,
)

# ─── STEP 1: RACE RESULTS ────────────────────────────────────────────────────
# Source: Kaggle "NASCAR Cup Series 2024" dataset + Racing-Reference.net
# Download manually from: https://www.kaggle.com/datasets/search?q=NASCAR+2024
# or scrape from https://www.racing-reference.info/season-stats/2024/W/

def load_race_results(filepath: str) -> pd.DataFrame:
    """
    Load raw Kaggle/Racing-Reference race results and standardise schema.

    Expected columns (after standardisation):
        race_id, race_number, race_name, track, date,
        sponsor, car_number, driver, finish_position,
        laps_led, laps_completed, dnf, is_playoff
    """
    log.info("Loading race results from %s", filepath)
    df = pd.read_csv(filepath)

    # Normalise column names (different Kaggle datasets use different schemas)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    # Filter to the 5 tracked sponsors only
    sponsor_cars = {v["car"].strip("#"): k for k, v in SPONSORS.items()}
    df["car_number"] = df["car"].astype(str).str.strip("#")
    df = df[df["car_number"].isin(sponsor_cars.keys())].copy()
    df["sponsor"] = df["car_number"].map(sponsor_cars)

    # Create race_id and is_win / is_playoff flags
    df = df.sort_values("race_number").reset_index(drop=True)
    df["race_id"]   = df["race_number"].astype(int)
    df["is_win"]    = (df["finish_position"] == 1).astype(int)
    df["is_playoff"]= (df["race_id"] >= 27).astype(int)   # Races 27-36 are playoffs
    df["dnf"]       = (df["finish_position"] > 38).astype(int)

    # Clean numeric columns
    for col in ["finish_position", "laps_led", "laps_completed"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    keep_cols = [
        "race_id", "race_number", "race_name", "track", "date",
        "sponsor", "car_number", "driver",
        "finish_position", "laps_led", "laps_completed",
        "dnf", "is_win", "is_playoff",
    ]
    df = df[[c for c in keep_cols if c in df.columns]]
    log.info("Race results loaded: %d rows, %d sponsors", len(df), df["sponsor"].nunique())
    return df


# ─── STEP 2: REDDIT DATA ─────────────────────────────────────────────────────
# Source: r/NASCAR via PRAW (Python Reddit API Wrapper)
# Searches post-race discussion threads for sponsor brand mentions

def collect_reddit_mentions(races_df: pd.DataFrame) -> pd.DataFrame:
    """
    For each race week, query r/NASCAR for brand-specific mentions in
    the post-race discussion thread and top posts from race day + 2 days.

    Returns a DataFrame with:
        race_id, sponsor, reddit_mentions, reddit_total_score,
        reddit_engagement_per_mention
    """
    log.info("Connecting to Reddit API via PRAW...")
    reddit = praw.Reddit(
        client_id    = REDDIT_CLIENT_ID,
        client_secret= REDDIT_SECRET,
        user_agent   = REDDIT_USER_AGENT,
    )

    results = []
    sponsor_keywords = {
        "NAPA Auto Parts":    ["NAPA", "NAPA Auto Parts", "Chase Elliott"],
        "Monster Energy":     ["Monster Energy", "Monster", "Tyler Reddick", "23XI"],
        "Fastenal":           ["Fastenal", "Buescher", "RFK"],
        "Love's Travel Stops":["Love's", "Loves Travel", "Todd Gilliland"],
        "Dollar Tree":        ["Dollar Tree", "Zane Smith", "Front Row"],
    }

    unique_races = races_df[["race_id", "race_name", "date"]].drop_duplicates()

    for _, race in unique_races.iterrows():
        race_date = pd.to_datetime(race["date"])
        start_dt  = race_date - timedelta(hours=6)
        end_dt    = race_date + timedelta(days=2)

        log.info("  Fetching Reddit data for Race %d: %s", race["race_id"], race["race_name"])

        # Search for post-race discussions
        query = f'{race["race_name"]} 2024'
        try:
            submissions = list(reddit.subreddit("NASCAR").search(
                query, sort="relevance", time_filter="week", limit=50
            ))
        except Exception as e:
            log.warning("Reddit API error for race %d: %s", race["race_id"], e)
            submissions = []

        for sponsor, keywords in sponsor_keywords.items():
            mention_count  = 0
            total_score    = 0
            comment_count  = 0

            for submission in submissions:
                sub_dt = datetime.utcfromtimestamp(submission.created_utc)
                if not (start_dt <= sub_dt <= end_dt):
                    continue

                # Check title and selftext
                text = (submission.title + " " + (submission.selftext or "")).lower()
                if any(kw.lower() in text for kw in keywords):
                    mention_count += 1
                    total_score   += submission.score
                    comment_count += submission.num_comments
                    continue

                # Check top-level comments (load up to 50)
                try:
                    submission.comments.replace_more(limit=0)
                    for comment in submission.comments.list()[:50]:
                        if any(kw.lower() in comment.body.lower() for kw in keywords):
                            mention_count += 1
                            total_score   += comment.score
                except Exception:
                    pass

            results.append({
                "race_id":    race["race_id"],
                "sponsor":    sponsor,
                "reddit_mentions":               mention_count,
                "reddit_total_score":            total_score,
                "reddit_engagement_per_mention": (total_score / mention_count) if mention_count else 0,
            })
        time.sleep(1)   # Respect Reddit rate limits

    df = pd.DataFrame(results)
    df.to_csv(RAW_REDDIT_DATA, index=False)
    log.info("Reddit data saved: %d records", len(df))
    return df


# ─── STEP 3: YOUTUBE DATA ────────────────────────────────────────────────────
# Source: YouTube Data API v3
# Queries race-specific highlight videos and extracts sponsor view metrics

def collect_youtube_metrics(races_df: pd.DataFrame) -> pd.DataFrame:
    """
    Search YouTube for race highlights and broadcast clips for each race,
    then tally sponsor-tagged or sponsor-mentioned view counts.

    Returns:
        race_id, sponsor, youtube_sponsor_views, youtube_total_views,
        youtube_view_share
    """
    log.info("Connecting to YouTube Data API v3...")
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    sponsor_search_terms = {
        "NAPA Auto Parts":    ["NAPA NASCAR highlights", "Chase Elliott highlights 2024"],
        "Monster Energy":     ["Monster Energy NASCAR", "Tyler Reddick highlights 2024", "23XI Racing"],
        "Fastenal":           ["Fastenal NASCAR", "Chris Buescher highlights 2024", "RFK Racing"],
        "Love's Travel Stops":["Love's Travel Stops NASCAR", "Todd Gilliland 2024"],
        "Dollar Tree":        ["Dollar Tree NASCAR", "Zane Smith 2024", "Front Row Motorsports"],
    }

    results = []
    unique_races = races_df[["race_id", "race_name", "track", "date"]].drop_duplicates()

    for _, race in unique_races.iterrows():
        race_date   = pd.to_datetime(race["date"])
        published_after  = (race_date - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        published_before = (race_date + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")

        log.info("  Fetching YouTube data for Race %d: %s", race["race_id"], race["race_name"])

        sponsor_views = {}
        race_total_views = 0

        for sponsor, queries in sponsor_search_terms.items():
            sponsor_view_count = 0

            for query in queries:
                try:
                    search_resp = youtube.search().list(
                        part="id,snippet",
                        q=f"{query} {race['race_name']} 2024",
                        type="video",
                        publishedAfter=published_after,
                        maxResults=10,
                        order="viewCount",
                    ).execute()

                    video_ids = [item["id"]["videoId"] for item in search_resp.get("items", [])]

                    if video_ids:
                        stats_resp = youtube.videos().list(
                            part="statistics",
                            id=",".join(video_ids),
                        ).execute()

                        for item in stats_resp.get("items", []):
                            views = int(item["statistics"].get("viewCount", 0))
                            sponsor_view_count += views
                            race_total_views   += views

                except Exception as e:
                    log.warning("YouTube API error (race %d, %s): %s", race["race_id"], sponsor, e)

            sponsor_views[sponsor] = sponsor_view_count
            time.sleep(0.5)

        for sponsor, views in sponsor_views.items():
            results.append({
                "race_id":               race["race_id"],
                "sponsor":               sponsor,
                "youtube_sponsor_views": views,
                "youtube_total_views":   race_total_views,
                "youtube_view_share":    (views / race_total_views) if race_total_views else 0,
            })

    df = pd.DataFrame(results)
    df.to_csv(RAW_YOUTUBE_DATA, index=False)
    log.info("YouTube data saved: %d records", len(df))
    return df


# ─── STEP 4: NEWS MENTIONS (MANUAL + TIERED WEIGHTING) ───────────────────────
# Source: Google News (manually curated, quality-weighted)
# Tier 1 = national outlets (ESPN, AP, NBC Sports)     → weight 3
# Tier 2 = trade press (Motorsport.com, NASCAR.com)    → weight 2
# Tier 3 = blogs / regional papers                     → weight 1

def load_news_mentions(filepath: str) -> pd.DataFrame:
    """
    Load manually collected news mention data.
    Expected CSV schema:
        race_id, sponsor, outlet, tier, headline, date
    Returns aggregated:
        race_id, sponsor, news_total_mentions, news_weighted_mentions
    """
    log.info("Loading news mentions from %s", filepath)
    df = pd.read_csv(filepath)

    TIER_WEIGHTS = {1: 3, 2: 2, 3: 1}
    df["weight"] = df["tier"].map(TIER_WEIGHTS).fillna(1)

    agg = df.groupby(["race_id", "sponsor"]).agg(
        news_total_mentions    = ("headline", "count"),
        news_weighted_mentions = ("weight",   "sum"),
    ).reset_index()

    log.info("News mentions aggregated: %d records", len(agg))
    return agg


# ─── STEP 5: MERGE INTO MASTER DATASET ───────────────────────────────────────

def build_master_dataset(
    race_df:    pd.DataFrame,
    reddit_df:  pd.DataFrame,
    youtube_df: pd.DataFrame,
    news_df:    pd.DataFrame,
) -> pd.DataFrame:
    """
    Merge all four data sources on (race_id, sponsor) to produce the
    180-record master dataset (36 races × 5 sponsors).
    """
    log.info("Merging data sources into master dataset...")

    master = race_df.merge(reddit_df,  on=["race_id", "sponsor"], how="left")
    master = master.merge(youtube_df,  on=["race_id", "sponsor"], how="left")
    master = master.merge(news_df,     on=["race_id", "sponsor"], how="left")

    # Fill NaNs from missing race weeks (API gaps)
    fill_zero_cols = [
        "reddit_mentions", "reddit_total_score", "reddit_engagement_per_mention",
        "youtube_sponsor_views", "youtube_total_views", "youtube_view_share",
        "news_total_mentions", "news_weighted_mentions",
    ]
    master[fill_zero_cols] = master[fill_zero_cols].fillna(0)

    # Validate shape
    expected_rows = TOTAL_RACES * len(SPONSORS)
    if len(master) != expected_rows:
        log.warning(
            "Unexpected row count: got %d, expected %d. Check for missing races or sponsors.",
            len(master), expected_rows,
        )

    log.info("Master dataset: %d rows × %d cols", master.shape[0], master.shape[1])
    master.to_csv(MASTER_DATASET, index=False)
    log.info("Saved → %s", MASTER_DATASET)
    return master


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(RAW_DATA_PATH,       exist_ok=True)
    os.makedirs("data/processed/",   exist_ok=True)

    # Step 1: Load race results (from Kaggle CSV — must be downloaded manually)
    race_df = load_race_results(RAW_RACE_RESULTS)

    # Step 2-3: Collect live data via APIs
    reddit_df  = collect_reddit_mentions(race_df)
    youtube_df = collect_youtube_metrics(race_df)

    # Step 4: Load manually collected news data
    news_df = load_news_mentions(RAW_NEWS_DATA)

    # Step 5: Build and save master dataset
    master = build_master_dataset(race_df, reddit_df, youtube_df, news_df)
    print("\n✅ Data collection complete.")
    print(master.head())
    print(f"\nShape: {master.shape}")
    print(f"\nSponsors: {master['sponsor'].unique().tolist()}")
    print(f"Races:    {master['race_id'].nunique()}")


if __name__ == "__main__":
    main()
