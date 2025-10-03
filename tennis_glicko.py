import csv
import glicko2
from datetime import date, timedelta
import math
import random
from collections import defaultdict

PERIOD_LENGTH = 7

players_overall = dict()
players_hard = dict()
players_clay = dict()
players_grass = dict()


matches = []



def period(s):
    m,d,y = s.split("/")

    d = date(int(y),int(m),int(d))
    start = date(2002,12,30)
    return ((d-start).days)//PERIOD_LENGTH


tournaments = []
with open("atp_tennis_weekly.csv") as f:
    reader = csv.reader(f)
    header = next(reader)
    for line in reader:
        if (line[0].strip() + (line[1].strip())[:4]) not in tournaments:
            tournaments.append(line[0].strip() + (line[1].strip())[:4])
        #if line[1].strip()[-4:] == "2025":
        m = {
            "surface": line[4].strip(),
            "p1": line[7].strip(),
            "p2": line[8].strip(),
            "winner": line[9].strip(),
            "date": line[1].strip(),
            "period": period(line[1]),
            "tourney": line[0].strip() + (line[1].strip())[:4]
        }
        matches.append(m)

NUM_PERIODS = (((date(2025,9,30)-date(2002,12,30)).days)//PERIOD_LENGTH)+1
for pd in range(NUM_PERIODS):
    if pd % 50 == 0:
        print("Period", pd) 

    period_matches = [x for x in matches if x["period"] == pd]
    period_matches_hard = [x for x in matches if x["period"] == pd and x["surface"] == "Hard"]
    period_matches_clay = [x for x in matches if x["period"] == pd and x["surface"] == "Clay"]
    period_matches_grass = [x for x in matches if x["period"] == pd and x["surface"] == "Grass"]

    played = set()
    played_hard = set()
    played_clay = set()
    played_grass = set()

    for match in period_matches:
        surface = match["surface"]
        p1 = match["p1"]
        p2 = match["p2"]
        winner = match["winner"]

        played.add(p1)
        played.add(p2)

        if p1 not in players_overall:
            players_overall[p1] = glicko2.Player()
        if p2 not in players_overall:
            players_overall[p2] = glicko2.Player()
        

        if match["surface"] == "Hard":
            played_hard.add(p1)
            played_hard.add(p2)

            if p1 not in players_hard:
                players_hard[p1] = glicko2.Player()
            if p2 not in players_hard:
                players_hard[p2] = glicko2.Player()

        if match["surface"] == "Clay":
            played_clay.add(p1)
            played_clay.add(p2)

            if p1 not in players_clay:
                players_clay[p1] = glicko2.Player()
            if p2 not in players_clay:
                players_clay[p2] = glicko2.Player()

        if match["surface"] == "Grass":
            played_grass.add(p1)
            played_grass.add(p2)

            if p1 not in players_grass:
                players_grass[p1] = glicko2.Player()
            if p2 not in players_grass:
                players_grass[p2] = glicko2.Player()
                
    
    # Collect all match data for each player before updating any ratings
    player_match_data = {}
    for player_str in players_overall:
        if player_str in played:
            players_matches = [m for m in period_matches if m["p1"] == player_str or m["p2"] == player_str]
            players_opponent_ratings = []
            players_opponent_RDs = []
            players_results = []
            match_weights = []
            for m in players_matches:
                if player_str == m["p1"]:
                    # Use current ratings (before any updates in this period)
                    players_opponent_ratings.append(players_overall[m["p2"]].rating)
                    players_opponent_RDs.append(players_overall[m["p2"]].rd)
                else:
                    players_opponent_ratings.append(players_overall[m["p1"]].rating)
                    players_opponent_RDs.append(players_overall[m["p1"]].rd)
                players_results.append(int(m["winner"]==player_str))
                
                    
            player_match_data[player_str] = (players_opponent_ratings, players_opponent_RDs, players_results)
    
    # Now update all players simultaneously using the collected data
    for player_str, player in players_overall.items():
        if player_str in played:
            opponent_ratings, opponent_RDs, results = player_match_data[player_str]
            player.update_player(opponent_ratings, opponent_RDs, results)
        else:
            player.did_not_compete()
    
    # Handle surface-specific ratings with the same simultaneous update approach
    for s_players_overall, s_period_matches, s_played, surface_name in (
        (players_hard, period_matches_hard, played_hard, "Hard"), 
        (players_clay, period_matches_clay, played_clay, "Clay"), 
        (players_grass, period_matches_grass, played_grass, "Grass")
    ):
        # Collect all match data for each player before updating any ratings
        s_player_match_data = {}
        for player_str in s_players_overall:
            if player_str in s_played:
                players_matches = [m for m in s_period_matches if m["p1"] == player_str or m["p2"] == player_str]
                players_opponent_ratings = []
                players_opponent_RDs = []
                players_results = []
                for m in players_matches:
                    if player_str == m["p1"]:
                        # Use current ratings (before any updates in this period)
                        players_opponent_ratings.append(s_players_overall[m["p2"]].rating)
                        players_opponent_RDs.append(s_players_overall[m["p2"]].rd)
                    else:
                        players_opponent_ratings.append(s_players_overall[m["p1"]].rating)
                        players_opponent_RDs.append(s_players_overall[m["p1"]].rd)
                    players_results.append(int(m["winner"]==player_str))
                        
                s_player_match_data[player_str] = (players_opponent_ratings, players_opponent_RDs, players_results)
        
        # Now update all players simultaneously using the collected data
        for player_str, player in s_players_overall.items():
            if player_str in s_played:
                opponent_ratings, opponent_RDs, results = s_player_match_data[player_str]
                player.update_player(opponent_ratings, opponent_RDs, results)
            else:
                player.did_not_compete()
        
        # Apply bounded blend with RD-aware weights to surface ratings
        for player_str, surface_player in s_players_overall.items():
            if player_str in players_overall:
                global_player = players_overall[player_str]
                
                # Convert to Glicko scale (μ, φ)
                mu_s = (surface_player.rating - 1500) / 173.7178
                phi_s = surface_player.rd / 173.7178
                mu_o = (global_player.rating - 1500) / 173.7178
                phi_o = global_player.rd / 173.7178
                
                rho = .98
                
                mu_blend = rho * mu_s + (1 - rho) * mu_o
                
                kappa = rho

                phi_blend = kappa * phi_s + (1 - kappa) * phi_o
                
                # Convert back to rating/RD scale
                surface_player.rating = 1500 + 173.7178 * mu_blend
                surface_player.rd = 173.7178 * phi_blend
    
def get_active_players():
    """Get players who have played in the last year (365 days)."""
    
    # Calculate cutoff date (1 year ago)
    cutoff_date = date.today() - timedelta(days=365)
    
    # Track last activity for each player
    player_last_activity = {}
    
    for match in matches:
        # Parse date from MM/DD/YYYY format
        date_parts = match["date"].split("/")
        match_date = date(int(date_parts[2]), int(date_parts[0]), int(date_parts[1]))
        
        for player in [match["p1"], match["p2"]]:
            if player not in player_last_activity:
                player_last_activity[player] = match_date
            else:
                player_last_activity[player] = max(player_last_activity[player], match_date)
    
    # Return only players who have played in the last year
    active_players = set()
    for player, last_activity in player_last_activity.items():
        if last_activity >= cutoff_date:
            active_players.add(player)
    
    return active_players

def get_players_with_min_matches_2025(min_matches=15):
    """Get players who have played at least min_matches in 2025"""
    # Count matches per player in 2025
    player_match_counts = defaultdict(int)
    
    for match in matches:
        # Check if match is in 2025
        if "2025" in match["date"]:
            player_match_counts[match["p1"]] += 1
            player_match_counts[match["p2"]] += 1
    
    # Return players with at least min_matches
    return {player for player, count in player_match_counts.items() if count >= min_matches}

def glicko2_win_prob(p1_rating, p1_rd, p2_rating, p2_rd):
    """
    Calculate expected outcome using the Glicko formula:
    E = 1 / (1 + 10^(-g(sqrt(RD_i^2 + RD_j^2)) * (r_i - r_j) / 400))
    """
    # Convert to internal scale
    mu1 = (p1_rating - 1500.0) / 173.7178
    mu2 = (p2_rating - 1500.0) / 173.7178
    phi1 = p1_rd / 173.7178
    phi2 = p2_rd / 173.7178
    
    # Calculate combined RD: sqrt(RD_i^2 + RD_j^2)
    combined_rd = math.sqrt(phi1**2 + phi2**2)
    
    # Glicko g function applied to combined RD
    g = 1.0 / math.sqrt(1.0 + 3.0 * (combined_rd ** 2) / (math.pi ** 2))
    
    # Expected outcome formula: E = 1 / (1 + 10^(-g * (r_i - r_j) / 400))
    # Note: Using natural log base for consistency with Glicko-2 internal calculations
    rating_diff = p1_rating - p2_rating
    exponent = -g * rating_diff / 400.0
    
    return 1.0 / (1.0 + 10.0 ** exponent)

p1_rating = players_overall["Tien L."].rating
p1_rd = players_overall["Tien L."].rd
p2_rating = players_overall["Cobolli F."].rating
p2_rd = players_overall["Cobolli F."].rd

# Get active players (played in last year)
active_players = get_active_players()

# Get players with at least 15 matches in 2025
players_2025_15plus = get_players_with_min_matches_2025(15)

print("\n=== TOP PLAYERS (Overall) - Active Only (15+ matches in 2025) ===")
# Filter to only active players with 15+ matches in 2025
active_overall_players = {name: player for name, player in players_overall.items() 
                          if name in active_players and name in players_2025_15plus}
top_players = sorted(active_overall_players.items(), key=lambda x: x[1].rating, reverse=True)
for i, (name, player) in enumerate(top_players[:100]):  # Top 50
    print(f"{i+1:2d}. {name:<20} Rating: {player.rating:.1f} RD: {player.rd:.1f}")

print(f"\nTotal active players: {len(active_players)}")
print(f"Players with 15+ matches in 2025: {len(players_2025_15plus)}")
print(f"Total players in system: {len(players_overall)}")
print(f"Filtered out: {len(players_overall) - len(active_overall_players)} inactive players or insufficient 2025 matches")




# Print top players by surface (active only) - Regularized Surface Ratings
for surface_name, surface_dict in [("Hard", players_hard), ("Clay", players_clay), ("Grass", players_grass)]:
    if surface_dict:  # Only if surface has players
        # Filter to only active players with 15+ matches in 2025
        active_surface_players = {name: player for name, player in surface_dict.items() 
                                 if name in active_players and name in players_2025_15plus}
        if active_surface_players:  # Only show if there are active players
            print(f"\n=== TOP PLAYERS ({surface_name}) - Bounded Blend Surface Ratings ===")
            
            # Show regularized surface ratings with comparison to global
            surface_ratings = []
            for name, surface_player in active_surface_players.items():
                if name in players_overall:
                    global_player = players_overall[name]
                    rating_diff = surface_player.rating - global_player.rating
                    rd_diff = surface_player.rd - global_player.rd
                    surface_ratings.append((
                        name, surface_player.rating, surface_player.rd,
                        global_player.rating, global_player.rd, rating_diff, rd_diff
                    ))
            
            # Sort by surface rating
            surface_ratings.sort(key=lambda x: x[1], reverse=True)
            
            for i, (name, surface_rating, surface_rd, global_rating, global_rd, rating_diff, rd_diff) in enumerate(surface_ratings[:20]):  # Top 10 per surface
                # Show surface rating with difference from global
                diff_str = f"({rating_diff:+.1f})" if abs(rating_diff) > 5 else "(~)"
                print(f"{i+1:2d}. {name:<20} Surface: {surface_rating:.1f}±{surface_rd:.1f} {diff_str} | Global: {global_rating:.1f}±{global_rd:.1f}")
            print(f"Active {surface_name} players: {len(active_surface_players)} (Bounded Blend)")


