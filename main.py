import pandas as pd
from trueskill import TrueSkill, Rating

# Set TrueSkill parameters
MU_0 = 23.0 
SIGMA_0 = 12
BETA = 12.0
TAU = 0.35
C = 4.5

# A draw is the situation where the performance difference between two teams is so small that no winner can be declared. This implementation assumes that if you're ranked higher on the final leaderboard of a contest, then you are the winner (even if there's a $0.01 difference). The input-trueskill.csv file takes into account draws when a draw actually occurs by treating the participants that tie as a team. 
DRAW_P = 0.0

# Iput and output CSVs
CSV_IN = "input-trueskill.csv"
CSV_OUT = "output-trueskill.csv"
CSV_HISTORY = "output-trueskill-history.csv"

# TrueSkill environment
env = TrueSkill(mu=MU_0,
                sigma=SIGMA_0,
                beta=BETA,
                tau=TAU,
                draw_probability=DRAW_P)

# Calculate reorientation offset. This is added to the TrueSkill score to prevent so many negative scores, though scores are relative so it doesn't really matter.
REORIENTATION_OFFSET = abs(MU_0 - C * SIGMA_0)

# Read in the input CSV
df = pd.read_csv(CSV_IN, parse_dates=["start_date"])

# Unique identifier for each contest
df["contest_key"] = df["platform"].astype(str) + "-" + df["contest_id"].astype(str)

# Drop contests with ≤1 entrant. TrueSkill needs at least two participants. It's not fair to not give any ranking benefit to winners when they are the only person to find a bug. In the future, I'm planning on implementing logic that provides these winners a boost in skill scoring by creating fake competitors utilizing averages across pot size and time period. There are only a handful of these contest, so for the first iteration of this, it's easier to just exclude them.
cnts = df["contest_key"].value_counts()
df = df[df["contest_key"].isin(cnts[cnts > 1].index)]

# Process contests in order of the date they started.
df = df.sort_values("start_date")

# Dictionaries to store data for leaderboard
ratings = dict() 
place_counts = dict()  
contest_counts = dict()
total_earnings = dict()
mediums_count = dict()
highs_count = dict()  
total_hms_count = dict()  
historical_snapshots = []  

def get_rating(handle: str) -> Rating:
    if handle not in place_counts:
        place_counts[handle] = {"1st": 0, "2nd": 0, "3rd": 0, "top_5": 0, "top_10": 0}
    if handle not in contest_counts:
        contest_counts[handle] = 0
    if handle not in total_earnings:
        total_earnings[handle] = 0.0
    if handle not in mediums_count:
        mediums_count[handle] = 0
    if handle not in highs_count:
        highs_count[handle] = 0
    if handle not in total_hms_count:
        total_hms_count[handle] = 0
    return ratings.setdefault(handle, env.create_rating())

# At some point, I want to implement some sort of tiering system that is based on how many standard deviations above the mean a researcher is (prevent sybil attacks that would be possible if we took the top 1% or something). For now, using TBD as a placeholder. Any ideas here are welcome!
def get_tier(score: float, mean: float, std: float) -> str:
    if score >= mean + 2 * std:
        return "TBD"
    elif score >= mean + 1.5 * std:
        return "TBD"
    elif score >= mean + 1 * std:
        return "TBD"
    elif score >= mean + 0.5 * std:
        return "TBD"
    else:
        return "TBD"
        
def add_historical_statistics(df):
    result_dfs = []
    
    for contest_key, group in df.groupby("contest_key", sort=False):
        # Calculate mean and std for this contest's snapshot
        mean_score = group["score"].mean()
        std_score = group["score"].std()
        
        # Calculate tier cutoffs
        cutoff_1 = mean_score + 2 * std_score
        cutoff_2 = mean_score + 1.5 * std_score
        cutoff_3 = mean_score + 1 * std_score
        cutoff_4 = mean_score + 0.5 * std_score
        
        # Add columns to group
        group = group.copy()
        group["tier"] = group["score"].apply(lambda x: get_tier(x, mean_score, std_score))
        group["mean"] = mean_score
        group["std"] = std_score
        group["cutoff_1"] = cutoff_1
        group["cutoff_2"] = cutoff_2
        group["cutoff_3"] = cutoff_3
        group["cutoff_4"] = cutoff_4
        
        result_dfs.append(group)
    
    return pd.concat(result_dfs, ignore_index=True)

def main():
    # Iterate over each contest and build the historical snapshot
    for contest_id, cdf in df.groupby("contest_key", sort=False):
        
        # Adds the time decay, so SRs are slightly penalized for inactivity.
        for h, r in ratings.items():
            ratings[h] = Rating(r.mu, (r.sigma ** 2 + TAU ** 2) ** 0.5)
        
        # Builds "teams" for TrueSkill. When there's a draw, SRs are put into the same team.
        teams = []
        for rank_val in sorted(cdf["handle_rank"].unique()):
            handles_in_rank = cdf.loc[cdf["handle_rank"] == rank_val, "handle"]
            teams.append([get_rating(h) for h in handles_in_rank])

        # Skip contests with only one "team"
        if len(teams) < 2:
            print(f"Skipping contest {contest_id} with only {len(teams)} team(s)")
            continue

        # Get contest participation, accumulate earnings, and findings
        for _, row in cdf.iterrows():
            h = row["handle"]
            if h in contest_counts:
                contest_counts[h] += 1
            if h in total_earnings:
                total_earnings[h] += row["reward_amount"]
            if h in mediums_count:
                mediums_count[h] += row["mediums"]
            if h in highs_count:
                highs_count[h] += row["highs"]
            if h in total_hms_count:
                total_hms_count[h] += row["total_hms"]

        
        unique_ranks = sorted(cdf["handle_rank"].unique())
        
        # Count 1st, 2nd, 3rd place finishes
        for i, rank_val in enumerate(unique_ranks[:3]):
            handles_in_rank = cdf.loc[cdf["handle_rank"] == rank_val, "handle"]
            place = ["1st", "2nd", "3rd"][i]
            for h in handles_in_rank:
                if h in place_counts:
                    place_counts[h][place] += 1
        
        # Count 4th-5th place finishes (top_5)
        for i in range(3, min(5, len(unique_ranks))):
            rank_val = unique_ranks[i]
            handles_in_rank = cdf.loc[cdf["handle_rank"] == rank_val, "handle"]
            for h in handles_in_rank:
                if h in place_counts:
                    place_counts[h]["top_5"] += 1
        
        # Count 6th-10th place finishes (top_10)
        for i in range(5, min(10, len(unique_ranks))):
            rank_val = unique_ranks[i]
            handles_in_rank = cdf.loc[cdf["handle_rank"] == rank_val, "handle"]
            for h in handles_in_rank:
                if h in place_counts:
                    place_counts[h]["top_10"] += 1

        # Update ratings
        new_teams = env.rate(teams, ranks=None) 
        
        # Write back the new ratings
        for rank_val, team_ratings in zip(sorted(cdf["handle_rank"].unique()), new_teams):
            handles_in_rank = cdf.loc[cdf["handle_rank"] == rank_val, "handle"]
            for h, new_r in zip(handles_in_rank, team_ratings):
                ratings[h] = new_r
        
        # Capture snapshot after this contest
        contest_date = cdf["start_date"].iloc[0]
        for handle, r in ratings.items():
            score = r.mu - C * r.sigma + REORIENTATION_OFFSET
            snapshot = {
                "contest_key": contest_id,
                "contest_date": contest_date,
                "handle": handle,
                "mu": r.mu,
                "sigma": r.sigma,
                "score": score,
                "contests": contest_counts.get(handle, 0),
                "1st_place_finishes": place_counts.get(handle, {}).get("1st", 0),
                "2nd_place_finishes": place_counts.get(handle, {}).get("2nd", 0),
                "3rd_place_finishes": place_counts.get(handle, {}).get("3rd", 0),
                "top_5": place_counts.get(handle, {}).get("top_5", 0),
                "top_10": place_counts.get(handle, {}).get("top_10", 0),
                "total_earned": total_earnings.get(handle, 0.0),
                "mediums": mediums_count.get(handle, 0),
                "highs": highs_count.get(handle, 0),
                "total_hms": total_hms_count.get(handle, 0)
            }
            historical_snapshots.append(snapshot)

    # Now that we've iterated over all contests, we can build the final leaderboard.
    rows = []
    for handle, r in ratings.items():
        score = r.mu - C * r.sigma + REORIENTATION_OFFSET
        rows.append({"handle": handle,
                    "mu": r.mu,
                    "sigma": r.sigma,
                    "score": score,
                    "contests": contest_counts.get(handle, 0),
                    "1st_place_finishes": place_counts.get(handle, {}).get("1st", 0),
                    "2nd_place_finishes": place_counts.get(handle, {}).get("2nd", 0),
                    "3rd_place_finishes": place_counts.get(handle, {}).get("3rd", 0),
                    "top_5": place_counts.get(handle, {}).get("top_5", 0),
                    "top_10": place_counts.get(handle, {}).get("top_10", 0),
                    "total_earned": total_earnings.get(handle, 0.0),
                    "mediums": mediums_count.get(handle, 0),
                    "highs": highs_count.get(handle, 0),
                    "total_hms": total_hms_count.get(handle, 0)})

    out_df = (pd.DataFrame(rows).sort_values("score", ascending=False).reset_index(drop=True))

    # Calculate statistics for final leaderboard
    mean_score = out_df["score"].mean()
    std_score = out_df["score"].std()

    # Calculate tier cutoffs
    cutoff_1 = mean_score + 2 * std_score
    cutoff_2 = mean_score + 1.5 * std_score
    cutoff_3 = mean_score + 1 * std_score
    cutoff_4 = mean_score + 0.5 * std_score

    # Add tier and statistics columns
    out_df["tier"] = out_df["score"].apply(lambda x: get_tier(x, mean_score, std_score))
    out_df["mean"] = mean_score
    out_df["std"] = std_score
    out_df["cutoff_1"] = cutoff_1
    out_df["cutoff_2"] = cutoff_2
    out_df["cutoff_3"] = cutoff_3
    out_df["cutoff_4"] = cutoff_4

    # Write final leaderboard to CSV
    out_df.to_csv(CSV_OUT, index=False)
    print(f"Written {CSV_OUT} with {len(out_df)} researchers.")

    # Write historical leaderboard to CSV
    history_df = pd.DataFrame(historical_snapshots)
    history_df = add_historical_statistics(history_df)
    history_df.to_csv(CSV_HISTORY, index=False)
    print(f"Written {CSV_HISTORY} with {len(history_df)} historical records.")

if __name__ == "__main__":
    main()
