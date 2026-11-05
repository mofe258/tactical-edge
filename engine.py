"""
engine.py — Chaos-Proof Football Intelligence Engine for Queen Rins
Implements Dixon-Coles Bivariate Poisson, Bayesian Rating Shrinkage,
Asian Handicap + DNB Cushions, and Empirical Calibration Scoring.
"""

import numpy as np
from scipy.stats import poisson


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
        return float(np.clip(shrunk, 0.60, 1.85))

    def calculate_xg(self, home_att, home_def, away_att, away_def, home_games=10, away_games=10):
        h_att_shrunk = self.apply_bayesian_shrinkage(home_att, home_games)
        h_def_shrunk = self.apply_bayesian_shrinkage(home_def, home_games)
        a_att_shrunk = self.apply_bayesian_shrinkage(away_att, away_games)
        a_def_shrunk = self.apply_bayesian_shrinkage(away_def, away_games)

        home_xg = h_att_shrunk * a_def_shrunk * self.league_avg_home
        away_xg = a_att_shrunk * h_def_shrunk * self.league_avg_away

        # Apply tactical reality: European cup matches average 2.4 goals, not 3.5
        home_xg = float(np.clip(home_xg, 0.45, 2.50))
        away_xg = float(np.clip(away_xg, 0.40, 2.10))

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

        # Draw No Bet (DNB)
        dnb_home = prob_home / (prob_home + prob_away) if (prob_home + prob_away) > 0 else 0.5
        dnb_away = prob_away / (prob_home + prob_away) if (prob_home + prob_away) > 0 else 0.5

        # Double Chance
        dc_1x = min(0.92, prob_home + prob_draw)
        dc_x2 = min(0.92, prob_away + prob_draw)

        # Asian Handicap +1.5 (Wins if team wins, draws, OR loses by only 1 goal!)
        away_plus_15 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if (a + 1.5) > h]))
        home_plus_15 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if (h + 1.5) > a]))

        # Over / Under
        u_25 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if h + a < 2.5]))
        u_35 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if h + a < 3.5]))

        # Allocator: Enforce Chaos-Proof Selection
        rec = self._select_chaos_proof_market(
            prob_home, prob_draw, prob_away, dnb_home, dnb_away,
            dc_1x, dc_x2, away_plus_15, home_plus_15, u_25, u_35, home_xg, away_xg
        )

        explanation = {
            "summary": f"Model xG: {home_team} {home_xg:.2f} vs {away_team} {away_xg:.2f}.",
            "supporting": f"Selected '{rec['pick']}' to guard against tactical clean-sheet upsets.",
            "risk": f"Draw factor: {prob_draw*100:.1f}%. Handicap & DNB cushions applied."
        }

        return {
            "home_xg": home_xg,
            "away_xg": away_xg,
            "prob_home": prob_home,
            "prob_draw": prob_draw,
            "prob_away": prob_away,
            "evidence_quality": "Chaos-Proof",
            "reliability_score": round(rec["prob"] * 100, 1),
            "recommendation": rec,
            "explanation": explanation
        }

    def _select_chaos_proof_market(self, p_h, p_d, p_a, dnb_h, dnb_a, dc_1x, dc_x2, a_p15, h_p15, u_25, u_35, h_xg, a_xg):
        candidates = []

        # 1. Asian Handicap (+1.5) — Survives 0-1, 1-1, 0-0, 0-2
        if a_p15 >= 0.78 and p_a >= 0.35:
            candidates.append({"category": "Asian Handicap", "pick": "Away (+1.5)", "prob": a_p15, "odds": round(max(1.30, (1.0 / a_p15) * 0.94), 2), "safety": a_p15 * 1.30})
        if h_p15 >= 0.80 and p_h >= 0.40:
            candidates.append({"category": "Asian Handicap", "pick": "Home (+1.5)", "prob": h_p15, "odds": round(max(1.25, (1.0 / h_p15) * 0.94), 2), "safety": h_p15 * 1.28})

        # 2. Draw No Bet (DNB) — Stake refunded if game ends in a draw
        if dnb_h >= 0.65 and p_h > p_a:
            candidates.append({"category": "Draw No Bet", "pick": "Home DNB", "prob": dnb_h, "odds": round(max(1.38, (1.0 / dnb_h) * 0.93), 2), "safety": dnb_h * 1.22})
        if dnb_a >= 0.60 and p_a > p_h:
            candidates.append({"category": "Draw No Bet", "pick": "Away DNB", "prob": dnb_a, "odds": round(max(1.45, (1.0 / dnb_a) * 0.93), 2), "safety": dnb_a * 1.20})

        # 3. Double Chance (1X / X2)
        if dc_x2 >= 0.70 and p_a >= p_h:
            candidates.append({"category": "Double Chance", "pick": "Draw or Away (X2)", "prob": dc_x2, "odds": round(max(1.32, (1.0 / dc_x2) * 0.93), 2), "safety": dc_x2 * 1.15})
        if dc_1x >= 0.72 and p_h >= p_a:
            candidates.append({"category": "Double Chance", "pick": "Home or Draw (1X)", "prob": dc_1x, "odds": round(max(1.30, (1.0 / dc_1x) * 0.93), 2), "safety": dc_1x * 1.15})

        # 4. Under 3.5 Goals
        if u_35 >= 0.75:
            candidates.append({"category": "Over/Under Goals", "pick": "Under 3.5 Goals", "prob": u_35, "odds": round(max(1.28, (1.0 / u_35) * 0.93), 2), "safety": u_35 * 1.10})

        # Fallback
        if not candidates:
            return {"category": "Double Chance", "pick": "Home or Draw (1X)", "prob": 0.76, "odds": 1.32}

        candidates.sort(key=lambda x: x["safety"], reverse=True)
        winner = candidates[0]
        return {
            "category": winner["category"],
            "pick": winner["pick"],
            "prob": round(min(0.92, winner["prob"]), 3),
            "odds": winner["odds"]
        }

    @staticmethod
    def calculate_brier_score(predictions_matrix, actual_outcomes_vector):
        if not len(predictions_matrix) or not len(actual_outcomes_vector):
            return None
        n = len(predictions_matrix)
        total_error = 0.0
        for p_dist, actual in zip(predictions_matrix, actual_outcomes_vector):
            target = [0.0, 0.0, 0.0]
            if 0 <= actual <= 2:
                target[actual] = 1.0
            total_error += sum((p - y) ** 2 for p, y in zip(p_dist, target))
        return float(round(total_error / n, 4))

    @staticmethod
    def compute_calibration_curve(probabilities, outcomes, n_bins=5):
        if not len(probabilities):
            return []
        probs = np.array(probabilities)
        outs = np.array(outcomes)
        bins = np.linspace(0.5, 1.0, n_bins + 1)
        calibration_data = []

        for i in range(len(bins) - 1):
            lower, upper = bins[i], bins[i + 1]
            mask = (probs >= lower) & (probs < upper)
            if np.sum(mask) > 0:
                bin_mean_prob = float(np.mean(probs[mask]))
                bin_empirical_rate = float(np.mean(outs[mask]))
                count = int(np.sum(mask))
                calibration_data.append({
                    "Probability Bin": f"{int(lower*100)}% - {int(upper*100)}%",
                    "Mean Model Probability": f"{bin_mean_prob * 100:.1f}%",
                    "Observed Win Rate": f"{bin_empirical_rate * 100:.1f}%",
                    "Settled Matches": count
                })
        return calibration_data
