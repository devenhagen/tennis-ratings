import csv
import glicko2
from datetime import date
import math


players_overall = dict()
players_hard = dict()
players_clay = dict()
players_grass = dict()


matches = []

def period(s):
    m,d,y = s.split("/")

    d = date(int(y),int(m),int(d))
    start = date(2002,12,30)
    return ((d-start).days)//14


tournaments = []
with open("atp_tennis_weekly.csv") as f:
    reader = csv.reader(f)
    header = next(reader)
    for line in reader:
        if (line[0].strip() + (line[1].strip())[:4]) not in tournaments:
            tournaments.append(line[0].strip() + (line[1].strip())[:4])
        m = {
            "surface": line[4].strip(),
            "p1": line[7].strip(),
            "p2": line[8].strip(),
            "winner": line[9].strip(),
            "period": period(line[1]),
            "tourney": line[0].strip() + (line[1].strip())[:4]
        }
        matches.append(m)

NUM_PERIODS = (((date(2025,9,30)-date(2002,12,30)).days)//14)+1
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
    
    temp_players_overall = players_overall.copy()
    temp_players_hard = players_hard.copy()
    temp_players_clay = players_clay.copy()
    temp_players_grass = players_grass.copy()

    for player_str,player in temp_players_overall.items():
        if player_str in played:
            players_matches = [m for m in period_matches if m["p1"] == player_str or m["p2"] == player_str]
            players_opponent_ratings = []
            players_opponent_RDs = []
            players_results = []
            for m in players_matches:
                if player_str == m["p1"]:
                    players_opponent_ratings.append(players_overall[m["p2"]].rating)
                    players_opponent_RDs.append(players_overall[m["p2"]].rd)
                else:
                    players_opponent_ratings.append(players_overall[m["p1"]].rating)
                    players_opponent_RDs.append(players_overall[m["p1"]].rd)
                players_results.append(int(m["winner"]==player_str))
            player.update_player(players_opponent_ratings, players_opponent_RDs, players_results)
        else:
            player.did_not_compete()
    players_overall = temp_players_overall
    
    for s_players_overall,s_temp_players_overall,s_period_matches,s_played in (
        (players_hard, temp_players_hard, period_matches_hard, played_hard), 
        (players_clay, temp_players_clay, period_matches_clay, played_clay), 
        (players_grass, temp_players_grass, period_matches_grass, played_grass)
    ):
        for player_str,player in s_temp_players_overall.items():
            if player_str in s_played:
                players_matches = [m for m in s_period_matches if m["p1"] == player_str or m["p2"] == player_str]
                players_opponent_ratings = []
                players_opponent_RDs = []
                players_results = []
                for m in players_matches:
                    if player_str == m["p1"]:
                        players_opponent_ratings.append(s_players_overall[m["p2"]].rating)
                        players_opponent_RDs.append(s_players_overall[m["p2"]].rd)
                    else:
                        players_opponent_ratings.append(s_players_overall[m["p1"]].rating)
                        players_opponent_RDs.append(s_players_overall[m["p1"]].rd)
                    players_results.append(int(m["winner"]==player_str))
                player.update_player(players_opponent_ratings, players_opponent_RDs, players_results)
            else:
                player.did_not_compete()
        s_players_overall = s_temp_players_overall
    
import math

def glicko2_win_prob(p1_rating, p1_rd, p2_rating, p2_rd):
    # Convert to internal scale
    mu1 = (p1_rating - 1500.0) / 173.7178
    mu2 = (p2_rating - 1500.0) / 173.7178
    phi1 = p1_rd / 173.7178
    phi2 = p2_rd / 173.7178
    
    # Combined uncertainty
    combined_rd = math.sqrt(phi1**2 + phi2**2)
    
    # Glicko-2 g function
    g = 1.0 / math.sqrt(1.0 + 3.0 * (combined_rd ** 2) / (math.pi ** 2))
    
    # Expected outcome formula from the document
    return 1.0 / (1.0 + math.exp(-g * (mu1 - mu2)))



print("\n=== TOP PLAYERS (Overall) ===")
top_players = sorted(players_overall.items(), key=lambda x: x[1].rating, reverse=True)
for i, (name, player) in enumerate(top_players[:50]):  # Top 20
    print(f"{i+1:2d}. {name:<20} Rating: {player.rating:.1f} RD: {player.rd:.1f}")

alc_rating = top_players[0][1].rating
alc_rd = top_players[0][1].rd
sin_rating = top_players[2][1].rating
sin_rd = top_players[2][1].rd

p1_rating = players_overall["Alcaraz C."].rating
p1_rd = players_overall["Alcaraz C."].rd
p2_rating = players_overall["Sinner J."].rating
p2_rd = players_overall["Sinner J."].rd

print(glicko2_win_prob(p1_rating,p1_rd,p2_rating,p2_rd))


'''
# Print top players by surface
for surface_name, surface_dict in [("Hard", players_hard), ("Clay", players_clay), ("Grass", players_grass)]:
    if surface_dict:  # Only if surface has players
        print(f"\n=== TOP PLAYERS ({surface_name}) ===")
        top_surface = sorted(surface_dict.items(), key=lambda x: x[1].rating, reverse=True)
        for i, (name, player) in enumerate(top_surface[:10]):  # Top 10 per surface
            print(f"{i+1:2d}. {name:<20} Rating: {player.rating:.1f} RD: {player.rd:.1f}")
'''
