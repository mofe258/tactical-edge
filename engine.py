"""
engine.py — High-Precision Mathematical Football Prediction Engine
Implements Dixon-Coles Bivariate Poisson, Bayesian Rating Shrinkage,
Draw-Trap Detection, and Risk-Adjusted Market Allocation.
"""

import numpy as np
from scipy.stats import poisson


class FootballEngine:
    def __init__(self, league_avg_home=1.45, league_avg_away=1.15, rho=-0.11, shrinkage_weight=6.0):
        self.league_avg_home = league_avg_home
        self.league_avg_away = league_avg_away
        self.rho = rho
        self.shrinkage_weight = shrinkage_weight

    def apply_bayesian_shrinkage(self, raw_rating, sample_size=10):
        n = max(1, float(sample_size))
        weight = n / (n + self.shrinkage_weight)
        shrunk = (weight * float(raw_rating)) + ((1.0 - weight) * 1.0)
        return float(np.clip(shrunk, 0.50, 1.95))

    def calculate_xg(self, home_att, home_def, away_att, away_def, home_games=10, away_games=10):
        h_att_shrunk = self.apply_bayesian_shrinkage(home_att, home_games)
        h_def_shrunk = self.apply_bayesian_shrinkage(home_def, home_games)
        a_att_shrunk = self.apply_bayesian_shrinkage(away_att, away_games)
        a_def_shrunk = self.apply_bayesian_shrinkage(away_def, away_games)

        home_xg = h_att_shrunk * a_def_shrunk * self.league_avg_home
        away_xg = a_att_shrunk * h_def_shrunk * self.league_avg_away

        home_xg = float(np.clip(home_xg, 0.35, 2.95))
        away_xg = float(np.clip(away_xg, 0.25, 2.45))

        return float(round(home_xg, 3)), float(round(away_xg, 3))

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

        # 1X2 Probabilities
        prob_home = float(np.sum(np.tril(matrix, -1)))
        prob_draw = float(np.sum(np.diag(matrix)))
        prob_away = float(np.sum(np.triu(matrix, 1)))

        total_1x2 = prob_home + prob_draw + prob_away
        if total_1x2 > 0:
            prob_home /= total_1x2
            prob_draw /= total_1x2
            prob_away /= total_1x2

        # Double Chance
        dc_1x = min(0.94, prob_home + prob_draw)
        dc_x2 = min(0.92, prob_away + prob_draw)

        # Over / Under
        ou = {}
        for line in [1.5, 2.5, 3.5]:
            u_prob = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if h + a < line]))
            ou[f"Under {line}"] = u_prob
            ou[f"Over {line}"] = 1.0 - u_prob

        # Combos
        h_and_o15 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if h > a and (h + a) >= 2]))
        a_and_o15 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if a > h and (h + a) >= 2]))

        def to_odds(p, margin=0.06):
            p = np.clip(p, 0.02, 0.96)
            return float(round((1.0 / p) * (1.0 - margin), 2))

        # Dynamically evaluate all eligible candidate bets and rank by mathematical safety
        rec = self._allocate_optimal_market(
            prob_home, prob_draw, prob_away, dc_1x, dc_x2,
            ou, h_and_o15, a_and_o15, home_xg, away_xg
        )

        # Calculate Leg Reliability Rating (0.0 to 100.0) for Accumulator Sorting
        # High confidence, low draw risk, balanced odds = Top Banker
        reliability_score = round((rec["prob"] * 100.0) * (1.0 - (prob_draw * 0.35)), 1)

        explanation = {
            "summary": f"Model projects {home_xg:.2f} xG for {home_team} vs {away_xg:.2f} xG for {away_team}.",
            "supporting": f"Selected '{rec['pick']}' with a {rec['prob']*100:.1f}% safety profile and optimal risk buffer.",
            "risk": f"Draw density is {prob_draw*100:.1f}%. Reliability index: {reliability_score}/100."
        }

        return {
            "home_xg": home_xg,
            "away_xg": away_xg,
            "prob_home": prob_home,
            "prob_draw": prob_draw,
            "prob_away": prob_away,
            "evidence_quality": "Strong Evidence" if min(home_games, away_games) >= 6 else "Moderate Evidence",
            "reliability_score": reliability_score,
            "recommendation": rec,
            "explanation": explanation
        }

    def _allocate_optimal_market(self, p_h, p_d, p_a, dc_1x, dc_x2, ou, h_o15, a_o15, h_xg, a_xg):
        """
        Risk-Adjusted Decision Allocator.
        Evaluates risk-to-reward ratio and prevents draw/deadlock traps.
        """
        tot_xg = h_xg + a_xg
        candidates = []

        # 1. Double Chance (Highest stability against variance)
        if dc_1x >= 0.74 and p_h > p_a:
            candidates.append({"category": "Double Chance", "pick": "Home or Draw (1X)", "prob": dc_1x, "odds": round(max(1.16, (1.0 / dc_1x) * 0.94), 2), "safety": dc_1x * 1.15})
        if dc_x2 >= 0.72 and p_a > p_h:
            candidates.append({"category": "Double Chance", "pick": "Draw or Away (X2)", "prob": dc_x2, "odds": round(max(1.18, (1.0 / dc_x2) * 0.94), 2), "safety": dc_x2 * 1.12})

        # 2. Over 1.5 Goals (Banker market for open matches)
        if ou["Over 1.5"] >= 0.75 and tot_xg >= 2.30:
            candidates.append({"category": "Over/Under Goals", "pick": "Over 1.5 Goals", "prob": ou["Over 1.5"], "odds": round(max(1.18, (1.0 / ou["Over 1.5"]) * 0.94), 2), "safety": ou["Over 1.5"] * 1.10})

        # 3. Straight Wins (Only when dominance is clear and draw risk is minimal)
        if p_h >= 0.65 and p_d <= 0.22:
            candidates.append({"category": "1X2", "pick": "Home Win", "prob": p_h, "odds": round(max(1.30, (1.0 / p_h) * 0.94), 2), "safety": p_h * 1.05})
        if p_a >= 0.58 and p_d <= 0.22:
            candidates.append({"category": "1X2", "pick": "Away Win", "prob": p_a, "odds": round(max(1.40, (1.0 / p_a) * 0.94), 2), "safety": p_a * 1.02})

        # 4. Combo Market: Home & Over 1.5 (High scoring home favorites)
        if p_h >= 0.60 and h_o15 >= 0.52 and tot_xg >= 2.6:
            candidates.append({"category": "1X2 & Over/Under 1.5", "pick": "Home & Over 1.5", "prob": h_o15, "odds": round(max(1.45, (1.0 / h_o15) * 0.94), 2), "safety": h_o15 * 0.95})

        # 5. Under 3.5 Goals (For tactical defensive battles)
        if ou["Under 3.5"] >= 0.74 and tot_xg < 2.45:
            candidates.append({"category": "Over/Under Goals", "pick": "Under 3.5 Goals", "prob": ou["Under 3.5"], "odds": round(max(1.20, (1.0 / ou["Under 3.5"]) * 0.94), 2), "safety": ou["Under 3.5"] * 1.02})

        # Fallback to Over 1.5 Goals
        if not candidates:
            return {"category": "Over/Under Goals", "pick": "Over 1.5 Goals", "prob": min(0.85, ou["Over 1.5"]), "odds": round(max(1.20, (1.0 / ou["Over 1.5"]) * 0.94), 2)}

        # Pick the candidate with the highest safety index
        candidates.sort(key=lambda x: x["safety"], reverse=True)
        best = candidates[0]
        return {
            "category": best["category"],
            "pick": best["pick"],
            "prob": round(min(0.92, best["prob"]), 3),
            "odds": best["odds"]
        }

    @staticmethod
    def calculate_brier_score(predictions_matrix, actual_outcomes_vector):
        if not len(predictions_matrix) or not len(actual_outcomes_vector):
            return None
        n = len(predictions_matrix)
        total_error = sum(sum((p - (1.0 if actual == i else 0.0)) ** 2 for i, p in enumerate(p_dist)) for p_dist, actual in zip(predictions_matrix, actual_outcomes_vector))
        return float(round(total_error / n, 4))
