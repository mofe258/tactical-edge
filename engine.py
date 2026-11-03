import numpy as np
from scipy.stats import poisson

class FootballEngine:
    def __init__(self, league_avg_home=1.45, league_avg_away=1.15):
        self.league_avg_home = league_avg_home
        self.league_avg_away = league_avg_away

    def calculate_xg(self, home_att, home_def, away_att, away_def):
        home_xg = max(0.2, home_att * away_def * self.league_avg_home)
        away_xg = max(0.2, away_att * home_def * self.league_avg_away)
        return home_xg, away_xg

    def predict_full_suite(self, home_xg, away_xg, home_att, home_def, away_att, away_def, max_goals=7):
        # 1. Goal Distribution Matrix
        matrix = np.zeros((max_goals, max_goals))
        for h in range(max_goals):
            for a in range(max_goals):
                matrix[h][a] = poisson.pmf(h, home_xg) * poisson.pmf(a, away_xg)

        # 2. 1X2 Probabilities
        prob_home = float(np.sum(np.tril(matrix, -1)))
        prob_draw = float(np.sum(np.diag(matrix)))
        prob_away = float(np.sum(np.triu(matrix, 1)))

        # 3. Double Chance
        dc_1x = prob_home + prob_draw
        dc_x2 = prob_away + prob_draw

        # 4. Over / Under Goals
        o05 = float(1.0 - matrix[0][0])
        o15 = float(1.0 - (matrix[0][0] + matrix[1][0] + matrix[0][1]))
        
        u25 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if h + a < 2.5]))
        o25 = 1.0 - u25
        
        u45 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if h + a <= 4]))

        # 5. Winning Combos (From SportyBet Slips)
        # Home & Over 1.5
        h_and_o15 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if h > a and (h + a >= 2)]))
        # Away & Over 1.5
        a_and_o15 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if a > h and (h + a >= 2)]))
        # Home & Over 2.5
        h_and_o25 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if h > a and (h + a >= 3)]))

        # 6. Handicap Cushions (Away does not lose by 3 or more goals)
        away_handicap_3 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if (h - a) < 3]))

        # 7. Corners & Cards Models
        exp_corners = 9.8 * ((home_att + away_att) / 2.0)
        over_85_corners = float(1.0 - poisson.cdf(8, exp_corners))
        exp_cards = 4.0 * ((home_def + away_def) / 2.0)
        over_35_cards = float(1.0 - poisson.cdf(3, exp_cards))

        # --- DYNAMIC MARKET ASSIGNMENT (NO OVER 1.5 REPETITION) ---
        best_market = "Over 1.5 Goals"
        best_prob = o15
        rec_odds = max(1.10, round((1.0 / o15) * 0.96, 2))

        # Hierarchy matching user's winning tickets:
        if prob_home >= 0.72 and h_and_o25 >= 0.65:
            best_market = "Home & Over 2.5"
            best_prob = h_and_o25
            rec_odds = 1.35
        elif prob_home >= 0.68 and h_and_o15 >= 0.62:
            best_market = "Home & Over 1.5"
            best_prob = h_and_o15
            rec_odds = 1.65
        elif prob_away >= 0.65 and a_and_o15 >= 0.60:
            best_market = "Away & Over 1.5"
            best_prob = a_and_o15
            rec_odds = 1.28
        elif prob_home >= 0.60 and prob_home < 0.70:
            best_market = "Home Win (1X2)"
            best_prob = prob_home
            rec_odds = 1.75
        elif prob_away > 0.52 and dc_x2 >= 0.85:
            best_market = "Draw or Away (X2)"
            best_prob = dc_x2
            rec_odds = 1.15
        elif u45 >= 0.86 and (home_xg + away_xg) < 3.0:
            best_market = "Under 4.5 Goals"
            best_prob = u45
            rec_odds = 1.24
        elif away_handicap_3 >= 0.88 and prob_home > prob_away:
            best_market = "Handicap Away (+3.0)"
            best_prob = away_handicap_3
            rec_odds = 1.18
        elif o25 >= 0.75:
            best_market = "Over 2.5 Goals"
            best_prob = o25
            rec_odds = 1.30
        elif dc_1x >= 0.88:
            best_market = "Home or Draw (1X)"
            best_prob = dc_1x
            rec_odds = 1.12
        else:
            best_market = "Over 1.5 Goals"
            best_prob = o15
            rec_odds = 1.12

        return {
            "best_market": best_market,
            "best_prob": best_prob,
            "est_odds": rec_odds,
            "h_o15": h_and_o15,
            "a_o15": a_and_o15,
            "u45": u45,
            "dc_x2": dc_x2,
            "handicap": away_handicap_3,
            "o15": o15,
            "o05": o05
        }
