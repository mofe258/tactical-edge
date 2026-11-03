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
        # Goal Matrix
        matrix = np.zeros((max_goals, max_goals))
        for h in range(max_goals):
            for a in range(max_goals):
                matrix[h][a] = poisson.pmf(h, home_xg) * poisson.pmf(a, away_xg)

        # 1X2
        prob_home = float(np.sum(np.tril(matrix, -1)))
        prob_draw = float(np.sum(np.diag(matrix)))
        prob_away = float(np.sum(np.triu(matrix, 1)))

        # Double Chance
        dc_1x = prob_home + prob_draw
        dc_x2 = prob_away + prob_draw

        # Over / Under
        o15 = float(1.0 - (matrix[0][0] + matrix[1][0] + matrix[0][1]))
        
        u45 = 0.0
        for h in range(max_goals):
            for a in range(max_goals):
                if h + a <= 4:
                    u45 += matrix[h][a]
        u45 = float(u45)

        # Combo: Home & Over 1.5
        home_and_o15 = 0.0
        for h in range(max_goals):
            for a in range(max_goals):
                if h > a and (h + a >= 2):
                    home_and_o15 += matrix[h][a]
        home_and_o15 = float(home_and_o15)

        # Combo: Away & Over 1.5
        away_and_o15 = 0.0
        for h in range(max_goals):
            for a in range(max_goals):
                if a > h and (h + a >= 2):
                    away_and_o15 += matrix[h][a]
        away_and_o15 = float(away_and_o15)

        # Handicap Cushion: Away (+2.5) -> Away does not lose by 3 or more
        away_plus_25 = 0.0
        for h in range(max_goals):
            for a in range(max_goals):
                if (h - a) < 3:
                    away_plus_25 += matrix[h][a]
        away_plus_25 = float(away_plus_25)

        # Corners & Cards Models
        exp_corners = 9.8 * ((home_att + away_att) / 2.0)
        over_85_corners = float(1.0 - poisson.cdf(8, exp_corners))

        exp_cards = 4.0 * ((home_def + away_def) / 2.0)
        over_35_cards = float(1.0 - poisson.cdf(3, exp_cards))

        # --- SELECTION LOGIC (Matching your winning slips) ---
        # Prioritize Combos (Home & O1.5), Ultra Safe Under 4.5, Big Handicap cushions, and DC
        best_market = "Over 1.5 Goals"
        best_prob = o15

        if home_and_o15 >= 0.72 and prob_home >= 0.70:
            best_market, best_prob = "Home & Over 1.5", home_and_o15
        elif away_and_o15 >= 0.68 and prob_away >= 0.65:
            best_market, best_prob = "Away & Over 1.5", away_and_o15
        elif dc_x2 >= 0.86 and prob_away > prob_home:
            best_market, best_prob = "Draw or Away (X2)", dc_x2
        elif dc_1x >= 0.88:
            best_market, best_prob = "Home or Draw (1X)", dc_1x
        elif u45 >= 0.88 and (home_xg + away_xg) < 3.2:
            best_market, best_prob = "Under 4.5 Goals", u45
        elif away_plus_25 >= 0.90:
            best_market, best_prob = "Handicap (+2.5)", away_plus_25
        elif o15 >= 0.85:
            best_market, best_prob = "Over 1.5 Goals", o15

        return {
            "best_market": best_market,
            "best_prob": best_prob,
            "home_and_o15": home_and_o15,
            "away_and_o15": away_and_o15,
            "u45_prob": u45,
            "dc_1x": dc_1x,
            "dc_x2": dc_x2,
            "handicap_plus": away_plus_25,
            "corners_prob": over_85_corners,
            "cards_prob": over_35_cards
        }
