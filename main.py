import pandas as pd
from trueskill import TrueSkill, Rating
import math
import numpy as np

# Set TrueSkill parameters
MU_0 = 23.0 
SIGMA_0 = 12
BETA = 12.0
TAU = 0.35
C = 4.5

# A draw is the situation where the performance difference between two teams is so small that no winner can be declared. This implementation assumes that if you're ranked higher on the final leaderboard of a contest, then you are the winner (even if there's a $0.01 difference). The input-trueskill.csv file takes into account draws when a draw actually occurs by treating the participants that tie as a team. 
DRAW_P = 0.0

# Calculate reorientation offset. This is added to the TrueSkill score to prevent so many negative scores, though scores are relative so it doesn't really matter.
REORIENTATION_OFFSET = abs(MU_0 - C * SIGMA_0)

# TrueSkill environment
env = TrueSkill(mu=MU_0,
    sigma=SIGMA_0,
    beta=BETA,
    tau=TAU,
    draw_probability=DRAW_P
)

# Blended scoring weights
WEIGHT_TRUESKILL = 0.75
WEIGHT_EARNINGS = 0.25

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
    

def get_pot_size_range(pot_size):
    """Categorize pot size into ranges"""
    if pot_size < 50000:
        return "0-50k"
    elif pot_size < 100000:
        return "50k-100k"
    elif pot_size < 250000:
        return "100k-250k"
    else:
        return "250k+"

def run_trueskill():
    df = pd.read_csv("input-trueskill.csv")

    # Unique identifier for each contest
    df["contest_key"] = df["platform"].astype(str) + "-" + df["contest_id"].astype(str)

    # Store average ratings by pot size range
    pot_size_ratings = {
        "0-50k": [],
        "50k-100k": [],
        "100k-250k": [],
        "250k+": []
    }


    # Process contests in order of the date they started.
    df = df.sort_values("start_date")

    player_contest_scores = {}  
    contests_to_skip = {} 
    
    print("First pass: Analyzing player performances...")
    
    
    # Collect all contest performances for each player
    for contest_id, cdf in df.groupby("contest_key", sort=False):
        # Skip contests with only one team
        unique_ranks = cdf["handle_rank"].unique()
        if len(unique_ranks) < 2:
            continue
            
        for _, row in cdf.iterrows():
            handle = row["handle"]
            rank = row["handle_rank"]
            
            if handle not in player_contest_scores:
                player_contest_scores[handle] = []
            
            # Store contest performance (we'll calculate score based on rank)
            # Lower rank is better (1st place = rank 1)
            player_contest_scores[handle].append((contest_id, rank))
    
    # Determine which contests to skip for each player
    for handle, performances in player_contest_scores.items():
        num_contests = len(performances)
        
        # Determine exclusion percentage based on contest count
        if num_contests <= 5:
            exclude_pct = 0.0  # Don't exclude any
        elif num_contests > 5 and num_contests <= 100:
            # Start at 10% for 6 contests, add 0.5% for each contest beyond 6
            exclude_pct = 0.10 + (num_contests - 6) * 0.005
        elif num_contests > 100 and num_contests <= 145:
            # Start at 57% for 101 contests, add 0.25% for each contest beyond 100
            exclude_pct = 0.57 + (num_contests - 100) * 0.0025
        else:
            # Stop at 68.25%
            exclude_pct = 0.6825
        
        if exclude_pct > 0:
            # Sort by rank (descending - worst performances have highest rank numbers)
            sorted_performances = sorted(performances, key=lambda x: x[1], reverse=True)
            
            # Calculate how many to exclude (round up)
            num_to_exclude = math.ceil(num_contests * exclude_pct)
            
            # Get the contest IDs to skip
            contests_to_skip[handle] = set()
            for i in range(num_to_exclude):
                contest_id = sorted_performances[i][0]
                contests_to_skip[handle].add(contest_id)
        
    
    # Second pass: Run TrueSkill algorithm
    for contest_id, cdf in df.groupby("contest_key", sort=False):
        
        # Apply time decay (tau) to all existing ratings before processing contest
        for h, r in ratings.items():
            ratings[h] = Rating(r.mu, (r.sigma ** 2 + TAU ** 2) ** 0.5)
        
        # Get contest pot size
        pot_size = cdf["total_rewards_advertised_usd"].iloc[0]
        pot_range = get_pot_size_range(pot_size)
        
        # Filter out players who should skip this contest
        filtered_cdf = cdf[~cdf['handle'].apply(lambda h: h in contests_to_skip and contest_id in contests_to_skip[h])]
        
        # Builds "teams" for TrueSkill. When there's a draw, SRs are put into the same team.
        teams = []
        team_to_handles = []  # Keep track of handles for each team
        for rank_val in sorted(filtered_cdf["handle_rank"].unique()):
            handles_in_rank = filtered_cdf.loc[filtered_cdf["handle_rank"] == rank_val, "handle"]
            teams.append([get_rating(h) for h in handles_in_rank])
            team_to_handles.append(list(handles_in_rank))
        
        # If only one team, create fake participants based on pot size averages
        if len(teams) == 1:
            # Get average rating for this pot size range
            if pot_size_ratings[pot_range]:
                # Calculate average mu and sigma from ratings in this pot range
                avg_mu = sum(r.mu for r in pot_size_ratings[pot_range]) / len(pot_size_ratings[pot_range])
                avg_sigma = sum(r.sigma for r in pot_size_ratings[pot_range]) / len(pot_size_ratings[pot_range])
            else:
                # Use default rating if no data yet for this pot range
                avg_mu = MU_0
                avg_sigma = SIGMA_0
            
            # Create 3 fake participants with slightly worse ratings
            fake_ratings = [
                Rating(avg_mu - 2, avg_sigma * 1.1), 
                Rating(avg_mu - 4, avg_sigma * 1.2), 
                Rating(avg_mu - 6, avg_sigma * 1.3) 
            ]
            
            # Add fake teams (one participant per team)
            for fake_rating in fake_ratings:
                teams.append([fake_rating])
                team_to_handles.append([f"FAKE_{pot_range}_{len(teams)}"])

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
        
        # Count top 5 finishes
        for i in range(min(5, len(unique_ranks))):
            rank_val = unique_ranks[i]
            handles_in_rank = cdf.loc[cdf["handle_rank"] == rank_val, "handle"]
            for h in handles_in_rank:
                if h in place_counts:
                    place_counts[h]["top_5"] += 1
        
        # Count top 10 finishes
        for i in range(min(10, len(unique_ranks))):
            rank_val = unique_ranks[i]
            handles_in_rank = cdf.loc[cdf["handle_rank"] == rank_val, "handle"]
            for h in handles_in_rank:
                if h in place_counts:
                    place_counts[h]["top_10"] += 1


        # Update ratings
        new_teams = env.rate(teams, ranks=None) 
        
        # Write back the new ratings (pure TrueSkill)
        for team_handles, team_ratings in zip(team_to_handles, new_teams):
            for h, new_r in zip(team_handles, team_ratings):
                # Skip if handle is NaN or not a string
                if pd.isna(h) or not isinstance(h, str):
                    continue
                if not h.startswith("FAKE_"):  # Only update real players
                    ratings[h] = new_r
                    # Collect ratings for pot size averaging (exclude first contest to avoid default ratings)
                    if contest_counts.get(h, 0) > 0:
                        pot_size_ratings[pot_range].append(new_r)
        
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
    
    # First, calculate raw scores for each component
    for handle, r in ratings.items():
        # TrueSkill score
        trueskill_score = r.mu - C * r.sigma + REORIENTATION_OFFSET
        
        # Placement score (weighted sum of top finishes)
        firsts = place_counts.get(handle, {}).get("1st", 0)
        seconds = place_counts.get(handle, {}).get("2nd", 0)
        thirds = place_counts.get(handle, {}).get("3rd", 0)
        
        # Earnings score
        total_earned = total_earnings.get(handle, 0.0)

        # Does NOT include LSW fixed pay
        earnings_score = total_earned
        
        rows.append({
            "handle": handle,
            "mu": r.mu,
            "sigma": r.sigma,
            "trueskill_score": trueskill_score,
            "earnings_score": earnings_score,
            "contests": contest_counts.get(handle, 0),
            "1st_place_finishes": firsts,
            "2nd_place_finishes": seconds,
            "3rd_place_finishes": thirds,
            "top_5": place_counts.get(handle, {}).get("top_5", 0),
            "top_10": place_counts.get(handle, {}).get("top_10", 0),
            "total_earned": total_earned,
            "mediums": mediums_count.get(handle, 0),
            "highs": highs_count.get(handle, 0),
            "total_hms": total_hms_count.get(handle, 0)
        })
    
    # Convert to DataFrame for easier manipulation
    df_scores = pd.DataFrame(rows)
    
    # Normalize each component to 0-100 scale using percentile ranks
    df_scores['trueskill_pct'] = df_scores['trueskill_score'].rank(pct=True) * 100
    df_scores['earnings_pct'] = df_scores['earnings_score'].rank(pct=True) * 100
    
    # Calculate blended score
    df_scores['score'] = (
        df_scores['trueskill_pct'] * WEIGHT_TRUESKILL +
        df_scores['earnings_pct'] * WEIGHT_EARNINGS
    )
    
    # Sort by blended score (descending order - highest score first)
    out_df = df_scores.sort_values('score', ascending=False).reset_index(drop=True)

    # Write historical leaderboard to CSV
    history_df = pd.DataFrame(historical_snapshots)

    return out_df, history_df

def main():
    out_df, history_df = run_trueskill()
    out_df.to_csv("output-trueskill.csv", index=False)
    print(f"Written output-trueskill.csv with {len(out_df)} researchers.")

    # Write historical leaderboard to CSV
    history_df = pd.DataFrame(historical_snapshots)
    history_df.to_csv("output-trueskill-history.csv", index=False)
    print(f"Written output-trueskill-history.csv with {len(history_df)} historical records.")

if __name__ == "__main__":
    main()
