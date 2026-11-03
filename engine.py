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

    def predict_match(self, home_xg, away_xg, max_goals=6):
        matrix = np.zeros((max_goals, max_goals))
        for h in range(max_goals):
            for a in range(max_goals):
                matrix[h][a] = poisson.pmf(h, home_xg) * poisson.pmf(a, away_xg)

        prob_home = float(np.sum(np.tril(matrix, -1)))
        prob_draw = float(np.sum(np.diag(matrix)))
        prob_away = float(np.sum(np.triu(matrix, 1)))

        # Markets
        dc_1x = prob_home + prob_draw
        dc_x2 = prob_away + prob_draw
        
        # Over/Under
        u15 = float(matrix[0][0] + matrix[1][0] + matrix[0][1])
        o15 = 1.0 - u15
        
        u25 = 0.0
        for h in range(max_goals):
            for a in range(max_goals):
                if h + a < 2.5:
                    u25 += matrix[h][a]
        o25 = 1.0 - u25

        # Both Teams To Score (BTTS)
        btts_no = float(matrix[0].sum() + matrix[:, 0].sum() - matrix[0][0])
        btts_yes = 1.0 - btts_no

        return {
            "Double Chance 1X": dc_1x,
            "Double Chance X2": dc_x2,
            "Over 1.5 Goals": o15,
            "Under 2.5 Goals": u25,
            "Over 2.5 Goals": o25,
            "BTTS - Yes": btts_yes
        }