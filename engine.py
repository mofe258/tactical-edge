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

    def predict_full_suite(self, home_xg, away_xg, home_att, home_def, away_att, away_def, max_goals=6):
        # 1. GOAL DISTRIBUTION MATRIX
        matrix = np.zeros((max_goals, max_goals))
        for h in range(max_goals):
            for a in range(max_goals):
                matrix[h][a] = poisson.pmf(h, home_xg) * poisson.pmf(a, away_xg)

        # 2. HOME / AWAY / DRAW (1X2)
        prob_home = float(np.sum(np.tril(matrix, -1)))
        prob_draw = float(np.sum(np.diag(matrix)))
        prob_away = float(np.sum(np.triu(matrix, 1)))

        # 3. DOUBLE CHANCE
        dc_1x = prob_home + prob_draw
        dc_x2 = prob_away + prob_draw

        # 4. OVER / UNDER 1.5 & 2.5
        u15 = float(matrix[0][0] + matrix[1][0] + matrix[0][1])
        o15 = 1.0 - u15

        u25 = 0.0
        for h in range(max_goals):
            for a in range(max_goals):
                if h + a < 2.5:
                    u25 += matrix[h][a]
        o25 = 1.0 - u25

        # 5. CORNERS MODEL (Based on attacking intensity, baseline ~9.8 per game)
        exp_corners = 9.8 * ((home_att + away_att) / 2.0)
        over_85_corners = float(1.0 - poisson.cdf(8, exp_corners))

        # 6. BOOKINGS / CARDS MODEL (Based on defensive pressure, baseline ~4.0 per game)
        exp_cards = 4.0 * ((home_def + away_def) / 2.0)
        over_35_cards = float(1.0 - poisson.cdf(3, exp_cards))

        # Pack structured predictions
        all_markets = {
            "Home Win": prob_home,
            "Away Win": prob_away,
            "Double Chance 1X": dc_1x,
            "Double Chance X2": dc_x2,
            "Over 1.5 Goals": o15,
            "Over 2.5 Goals": o25,
            "Under 2.5 Goals": u25,
            "Over 8.5 Corners": over_85_corners,
            "Over 3.5 Bookings": over_35_cards
        }

        # Value Selector: Pick the smartest bet with balanced risk/reward
        # We don't always pick Over 1.5 if Double Chance or Home Win is strongly favored
        candidates = {k: v for k, v in all_markets.items() if v >= 0.70}
        
        # Priority to decisive markets (Winner > DC > Over 2.5 > Corners > Over 1.5)
        best_market = "Over 1.5 Goals"
        best_prob = o15

        if prob_home >= 0.75:
            best_market, best_prob = "Home Win", prob_home
        elif prob_away >= 0.75:
            best_market, best_prob = "Away Win", prob_away
        elif dc_1x >= 0.82 and prob_home > prob_away:
            best_market, best_prob = "Double Chance 1X", dc_1x
        elif dc_x2 >= 0.82 and prob_away > prob_home:
            best_market, best_prob = "Double Chance X2", dc_x2
        elif o25 >= 0.75:
            best_market, best_prob = "Over 2.5 Goals", o25
        elif u25 >= 0.75:
            best_market, best_prob = "Under 2.5 Goals", u25
        elif over_85_corners >= 0.78:
            best_market, best_prob = "Over 8.5 Corners", over_85_corners
        elif over_35_cards >= 0.78:
            best_market, best_prob = "Over 3.5 Bookings", over_35_cards
        elif candidates:
            best_market = max(candidates, key=candidates.get)
            best_prob = candidates[best_market]

        return {
            "best_market": best_market,
            "best_prob": best_prob,
            "o25_prob": o25,
            "u25_prob": u25,
            "dc_1x_prob": dc_1x,
            "dc_x2_prob": dc_x2,
            "corners_prob": over_85_corners,
            "cards_prob": over_35_cards
        }
