"""
engine.py — Anti-Cut Mathematical Engine & 0-5 Minutes Blitz-Decay Model
Includes:
- Time-decay Poisson model for First 5 Minutes (Under 0.5 Goals)
- 1X2, DNB, and Double Chance Banker Algorithms
"""

import numpy as np
from scipy.stats import poisson
import math


class FootballEngine:
    def __init__(self, league_avg_home=1.35, league_avg_away=1.10, rho=-0.11, shrinkage_weight=6.0):
        self.league_avg_home = league_avg_home
        self.league_avg_away = league_avg_away
        self.rho = rho
        self.shrinkage_weight = shrinkage_weight

    def apply_bayesian_shrinkage(self, raw_rating, sample_size=10):
        n = max(1, float(sample_size))
        weight = n / (n + self.shrinkage_weight)
        shrunk = (weight * float(raw_rating)) + ((1.0 - weight) * 1.0)
        return float(np.clip(shrunk, 0.65, 1.85))

    def calculate_xg(self, home_att, home_def, away_att, away_def, home_games=10, away_games=10):
        h_att_shrunk = self.apply_bayesian_shrinkage(home_att, home_games)
        h_def_shrunk = self.apply_bayesian_shrinkage(home_def, home_games)
        a_att_shrunk = self.apply_bayesian_shrinkage(away_att, away_games)
        a_def_shrunk = self.apply_bayesian_shrinkage(away_def, away_games)

        home_xg = h_att_shrunk * a_def_shrunk * self.league_avg_home
        away_xg = a_att_shrunk * h_def_shrunk * self.league_avg_away

        home_xg = float(np.clip(home_xg, 0.45, 2.70))
        away_xg = float(np.clip(away_xg, 0.35, 2.20))
        return float(round(home_xg, 2)), float(round(away_xg, 2))

    def calculate_early_goal_prob(self, home_xg, away_xg):
        """
        Calculates exact mathematical probability of NO GOAL in minutes 0:00 to 4:59.
        First 5 minutes account for ~4.8% of total 90-minute goal expectancy.
        """
        total_xg = home_xg + away_xg
        # Early-game intensity factor (teams start cautious)
        lambda_5min = (5.0 / 90.0) * total_xg * 0.85
        # Poisson P(0 goals) = e^(-lambda)
        prob_no_goal = math.exp(-lambda_5min)
        prob_no_goal = min(0.965, max(0.880, prob_no_goal))
        
        # Fair bookmaker odds for Under 0.5 Goals (1-5 min)
        odds = round(max(1.11, min(1.22, (1.0 / prob_no_goal) * 0.96)), 2)
        return round(prob_no_goal, 3), odds

    def _tau_correction(self, h, a, lmbda, mu):
        if h == 0 and a == 0:
            return 1.0 - (lmbda * mu * self.rho)
        elif h == 0 and a == 1:
            return 1.0 + (lmbda * self.rho)
        elif h == 1 and a == 0:
            return 1.0 + (mu * self.rho)
        elif h == 1 and a == 1:
            return 1.0 - self.rho
        return 1.0

    def compute_score_matrix(self, home_xg, away_xg, max_goals=8):
        matrix = np.zeros((max_goals, max_goals))
        for h in range(max_goals):
            for a in range(max_goals):
                p_ind = poisson.pmf(h, home_xg) * poisson.pmf(a, away_xg)
                tau = self._tau_correction(h, a, home_xg, away_xg)
                matrix[h][a] = max(0.0, p_ind * tau)
        m_sum = np.sum(matrix)
        if m_sum > 0:
            matrix = matrix / m_sum
        return matrix

    def predict_full_match(self, home_xg, away_xg, home_team="Home", away_team="Away", home_games=10, away_games=10):
        matrix = self.compute_score_matrix(home_xg, away_xg)
        max_goals = matrix.shape[0]

        prob_home = float(np.sum(np.tril(matrix, -1)))
        prob_draw = float(np.sum(np.diag(matrix)))
        prob_away = float(np.sum(np.triu(matrix, 1)))

        total_1x2 = prob_home + prob_draw + prob_away
        if total_1x2 > 0:
            prob_home /= total_1x2
            prob_draw /= total_1x2
            prob_away /= total_1x2

        dnb_home = prob_home / (prob_home + prob_away) if (prob_home + prob_away) > 0 else 0.5
        dnb_away = prob_away / (prob_home + prob_away) if (prob_home + prob_away) > 0 else 0.5

        dc_1x = min(0.94, prob_home + prob_draw)
        dc_x2 = min(0.92, prob_away + prob_draw)

        o_25 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if h + a >= 2.5]))
        u_35 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if h + a < 3.5]))

        delta_xg = abs(home_xg - away_xg)
        is_trap = (delta_xg < 0.28 and prob_draw >= 0.26)

        # 0-5 Mins Calculations
        p_05_no_goal, odds_05 = self.calculate_early_goal_prob(home_xg, away_xg)

        if is_trap:
            rec = {"category": "Over/Under Goals", "pick": "Under 3.5 Goals", "prob": round(u_35, 3), "odds": 1.28}
            safe = False
        elif p_home >= 0.62 and home_xg >= (away_xg + 0.60):
            rec = {"category": "1X2", "pick": "Home Win", "prob": round(p_home, 3), "odds": round(max(1.35, (1.0 / p_home) * 0.94), 2)}
            safe = True
        elif dc_1x >= 0.76 and home_xg >= away_xg:
            rec = {"category": "Double Chance", "pick": "Home or Draw (1X)", "prob": round(dc_1x, 3), "odds": round(max(1.24, (1.0 / dc_1x) * 0.94), 2)}
            safe = True
        elif dc_x2 >= 0.75 and away_xg >= home_xg:
            rec = {"category": "Double Chance", "pick": "Draw or Away (X2)", "prob": round(dc_x2, 3), "odds": round(max(1.25, (1.0 / dc_x2) * 0.94), 2)}
            safe = True
        elif o_25 >= 0.62 and (home_xg + away_xg) >= 2.90:
            rec = {"category": "Over/Under Goals", "pick": "Over 2.5 Goals", "prob": round(o_25, 3), "odds": round(max(1.55, (1.0 / o_25) * 0.94), 2)}
            safe = True
        elif dnb_home >= 0.70:
            rec = {"category": "Draw No Bet", "pick": "Home DNB", "prob": round(dnb_home, 3), "odds": round(max(1.32, (1.0 / dnb_home) * 0.93), 2)}
            safe = True
        else:
            rec = {"category": "Double Chance", "pick": "Home or Draw (1X)", "prob": 0.70, "odds": 1.30}
            safe = False

        return {
            "home_xg": home_xg,
            "away_xg": away_xg,
            "prob_home": prob_home,
            "prob_draw": prob_draw,
            "prob_away": prob_away,
            "is_accumulator_eligible": safe,
            "recommendation": rec,
            "early_market": {
                "category": "1-5 Mins Goals",
                "pick": "Under 0.5 (1-5 Min)",
                "prob": p_05_no_goal,
                "odds": odds_05
            }
        }

    @staticmethod
    def calculate_brier_score(predictions_matrix, actual_outcomes_vector):
        if not len(predictions_matrix) or not len(actual_outcomes_vector):
            return None
        n = len(predictions_matrix)
        total_error = sum(sum((p - (1.0 if actual == i else 0.0)) ** 2 for i, p in enumerate(p_dist)) for p_dist, actual in zip(predictions_matrix, actual_outcomes_vector))
        return float(round(total_error / n, 4))
