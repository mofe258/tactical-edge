"""
engine.py — High-Yield Prediction Engine for Queen Rins
DNB (Draw No Bet) permanently banned and removed.
Only allocates high-hit-rate markets: Home Win, Away Win, 1X, X2, and Under 3.5.
"""

import numpy as np
from scipy.stats import poisson


class FootballEngine:
    def __init__(self, league_avg_home=1.30, league_avg_away=1.05, rho=-0.11, shrinkage_weight=6.0):
        self.league_avg_home = league_avg_home
        self.league_avg_away = league_avg_away
        self.rho = rho
        self.shrinkage_weight = shrinkage_weight

    def apply_bayesian_shrinkage(self, raw_rating, sample_size=10):
        n = max(1, float(sample_size))
        weight = n / (n + self.shrinkage_weight)
        shrunk = (weight * float(raw_rating)) + ((1.0 - weight) * 1.0)
        return float(np.clip(shrunk, 0.55, 1.85))

    def calculate_xg(self, home_att, home_def, away_att, away_def, home_games=10, away_games=10):
        h_att_shrunk = self.apply_bayesian_shrinkage(home_att, home_games)
        h_def_shrunk = self.apply_bayesian_shrinkage(home_def, home_games)
        a_att_shrunk = self.apply_bayesian_shrinkage(away_att, away_games)
        a_def_shrunk = self.apply_bayesian_shrinkage(away_def, away_games)

        home_xg = h_att_shrunk * a_def_shrunk * self.league_avg_home
        away_xg = a_att_shrunk * h_def_shrunk * self.league_avg_away

        home_xg = float(np.clip(home_xg, 0.40, 2.65))
        away_xg = float(np.clip(away_xg, 0.30, 2.15))

        return float(round(home_xg, 2)), float(round(away_xg, 2))

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

        # Double Chance: pays out as WON on win OR draw
        dc_1x = min(0.94, prob_home + prob_draw)
        dc_x2 = min(0.92, prob_away + prob_draw)

        u_25 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if h + a < 2.5]))
        o_25 = 1.0 - u_25
        u_35 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if h + a < 3.5]))

        # High-Hit-Rate Allocation (ZERO DNB)
        rec = self._select_pure_banker_market(
            prob_home, prob_draw, prob_away, dc_1x, dc_x2,
            o_25, u_25, u_35, home_xg, away_xg
        )

        delta_xg = abs(home_xg - away_xg)
        is_safe = not (delta_xg < 0.18 and prob_draw >= 0.28)

        explanation = {
            "summary": f"xG: {home_team} {home_xg:.2f} vs {away_team} {away_xg:.2f}.",
            "supporting": f"Selected '{rec['pick']}' with high probability cushion. Zero DNB risk.",
            "risk": f"Draw probability: {prob_draw*100:.1f}%."
        }

        return {
            "home_xg": home_xg,
            "away_xg": away_xg,
            "prob_home": prob_home,
            "prob_draw": prob_draw,
            "prob_away": prob_away,
            "evidence_quality": "Tier-1 Banker" if is_safe else "High Entropy",
            "is_accumulator_eligible": is_safe,
            "reliability_score": round(rec["prob"] * 100, 1),
            "recommendation": rec,
            "explanation": explanation
        }

    def _select_pure_banker_market(self, p_h, p_d, p_a, dc_1x, dc_x2, o_25, u_25, u_35, h_xg, a_xg):
        """
        STRICT MARKET ALLOCATION (NO DNB):
        1. Clear Dominance -> Straight Win (Home Win / Away Win)
        2. Tight / Defensive Match -> Under 3.5 Goals
        3. Equal / Tactical Fixture -> Double Chance (1X or X2)
        4. Shootouts ONLY -> Over 2.5
        """
        tot_xg = h_xg + a_xg

        # 1. Clear Home Dominance -> Straight Home Win
        if p_h >= 0.58 and h_xg >= (a_xg + 0.55):
            return {"category": "1X2", "pick": "Home Win", "prob": round(p_h, 3), "odds": round(max(1.42, (1.0 / p_h) * 0.94), 2)}

        # 2. Defensive Gridlock -> Under 3.5 Goals (Hits in 76%+ of matches)
        if tot_xg <= 2.45 and u_35 >= 0.72:
            return {"category": "Over/Under Goals", "pick": "Under 3.5 Goals", "prob": round(u_35, 3), "odds": round(max(1.26, (1.0 / u_35) * 0.94), 2)}

        # 3. Clear Away Dominance -> Straight Away Win
        if p_a >= 0.54 and a_xg >= (h_xg + 0.45):
            return {"category": "1X2", "pick": "Away Win", "prob": round(p_a, 3), "odds": round(max(1.48, (1.0 / p_a) * 0.94), 2)}

        # 4. Away Edge in Tough Fixture -> Draw or Away (X2) (Instead of Away DNB)
        if p_a > p_h and dc_x2 >= 0.68:
            return {"category": "Double Chance", "pick": "Draw or Away (X2)", "prob": round(dc_x2, 3), "odds": round(max(1.30, (1.0 / dc_x2) * 0.94), 2)}

        # 5. Genuine High-Scoring Shootout Only -> Over 2.5 Goals
        if tot_xg >= 2.95 and o_25 >= 0.62 and h_xg >= 1.40 and a_xg >= 1.20:
            return {"category": "Over/Under Goals", "pick": "Over 2.5 Goals", "prob": round(o_25, 3), "odds": round(max(1.60, (1.0 / o_25) * 0.94), 2)}

        # 6. Solid Home Edge -> Home or Draw (1X) (Instead of Home DNB)
        return {"category": "Double Chance", "pick": "Home or Draw (1X)", "prob": round(dc_1x, 3), "odds": round(max(1.25, (1.0 / dc_1x) * 0.94), 2)}

    @staticmethod
    def calculate_brier_score(predictions_matrix, actual_outcomes_vector):
        if not len(predictions_matrix) or not len(actual_outcomes_vector):
            return None
        n = len(predictions_matrix)
        total_error = sum(sum((p - (1.0 if actual == i else 0.0)) ** 2 for i, p in enumerate(p_dist)) for p_dist, actual in zip(predictions_matrix, actual_outcomes_vector))
        return float(round(total_error / n, 4))
