"""
engine.py — Advanced Statistical Modeling & Prediction Engine
Implements Dixon-Coles Bivariate Poisson with Bayesian Shrinkage on team ratings,
preventing extreme (>90%) probability spikes and calculating exact joint distributions.
"""

import numpy as np
from scipy.stats import poisson


class FootballEngine:
    def __init__(self, league_avg_home=1.45, league_avg_away=1.15, rho=-0.11, shrinkage_weight=6.0):
        self.league_avg_home = league_avg_home
        self.league_avg_away = league_avg_away
        self.rho = rho
        # Bayesian prior weight: regresses extreme early-season form toward league mean (1.0)
        self.shrinkage_weight = shrinkage_weight

    def apply_bayesian_shrinkage(self, raw_rating, sample_size):
        """
        Applies empirical Bayes shrinkage:
        Shrunk = (n / (n + alpha)) * raw + (alpha / (n + alpha)) * 1.0
        Prevents small-sample rating explosions that cause artificial >90% probabilities.
        """
        n = max(1, float(sample_size))
        weight = n / (n + self.shrinkage_weight)
        shrunk = (weight * float(raw_rating)) + ((1.0 - weight) * 1.0)
        # Bounded between realistic professional football attack/defense parameters
        return float(np.clip(shrunk, 0.55, 1.85))

    def calculate_xg(self, home_att, home_def, away_att, away_def, home_games=10, away_games=10):
        """
        Calculates realistic Expected Goals (xG) using Bayesian shrunk ratings.
        """
        h_att_shrunk = self.apply_bayesian_shrinkage(home_att, home_games)
        h_def_shrunk = self.apply_bayesian_shrinkage(home_def, home_games)
        a_att_shrunk = self.apply_bayesian_shrinkage(away_att, away_games)
        a_def_shrunk = self.apply_bayesian_shrinkage(away_def, away_games)

        # Baseline projection
        home_xg = h_att_shrunk * a_def_shrunk * self.league_avg_home
        away_xg = a_att_shrunk * h_def_shrunk * self.league_avg_away

        # Natural football expectancy clamp (rarely exceeds 2.75 xG in top professional tiers)
        home_xg = float(np.clip(home_xg, 0.40, 2.75))
        away_xg = float(np.clip(away_xg, 0.30, 2.25))

        return float(round(home_xg, 3)), float(round(away_xg, 3))

    def _tau_correction(self, h, a, lmbda, mu):
        """Dixon-Coles adjustment for low scores (0-0, 1-0, 0-1, 1-1)."""
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
        """Computes bivariate probability matrix strictly normalized to sum = 1.0."""
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

    def predict_full_match(self, home_xg, away_xg, home_team="Home", away_team="Away"):
        """Calculates derived markets from the exact bivariate distribution."""
        matrix = self.compute_score_matrix(home_xg, away_xg)
        max_goals = matrix.shape[0]

        # 1. 1X2 Probabilities (Guaranteed sum = 100%)
        prob_home = float(np.sum(np.tril(matrix, -1)))
        prob_draw = float(np.sum(np.diag(matrix)))
        prob_away = float(np.sum(np.triu(matrix, 1)))

        total_1x2 = prob_home + prob_draw + prob_away
        if total_1x2 > 0:
            prob_home /= total_1x2
            prob_draw /= total_1x2
            prob_away /= total_1x2

        # 2. Double Chance
        dc_1x = min(0.92, prob_home + prob_draw)
        dc_x2 = min(0.90, prob_away + prob_draw)
        dc_12 = prob_home + prob_away

        # 3. Over / Under Goals
        ou = {}
        for line in [1.5, 2.5, 3.5]:
            u_prob = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if h + a < line]))
            ou[f"Under {line}"] = u_prob
            ou[f"Over {line}"] = 1.0 - u_prob

        # 4. BTTS
        btts_yes = float(np.sum(matrix[1:, 1:]))
        btts_no = 1.0 - btts_yes

        # 5. Exact Joint Probability Combos
        h_and_o15 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if h > a and (h + a) >= 2]))
        a_and_o15 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if a > h and (h + a) >= 2]))

        # 6. Handicap Cushions
        away_hcap_25 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if (h - a) < 3]))
        away_hcap_15 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if (h - a) < 2]))

        def to_odds(p, margin=0.06):
            p = np.clip(p, 0.02, 0.96)
            return float(round((1.0 / p) * (1.0 - margin), 2))

        # Top 5 most probable exact scores
        score_candidates = []
        for h in range(5):
            for a in range(5):
                score_candidates.append({"score": f"{h} - {a}", "prob": float(matrix[h][a])})
        score_candidates.sort(key=lambda x: x["prob"], reverse=True)
        top_scores = score_candidates[:5]

        # Select primary market
        rec = self._select_balanced_market(
            prob_home, prob_draw, prob_away, dc_1x, dc_x2,
            ou, away_hcap_25, h_and_o15, a_and_o15, home_xg, away_xg
        )

        explanation = (
            f"Bivariate Dixon-Coles projection assigns {home_xg:.2f} xG to {home_team} and {away_xg:.2f} xG to {away_team} "
            f"(Total Expectancy: {home_xg + away_xg:.2f} goals). "
            f"Win probability distribution: {prob_home*100:.1f}% Home, {prob_draw*100:.1f}% Draw, {prob_away*100:.1f}% Away. "
            f"Recommended market: '{rec['pick']}' ({rec['prob']*100:.1f}% calibrated model confidence, fair odds ~{rec['odds']:.2f}). "
            f"Key risk: Draw probability density is modeled at {prob_draw*100:.1f}%."
        )

        return {
            "home_xg": home_xg,
            "away_xg": away_xg,
            "prob_home": prob_home,
            "prob_draw": prob_draw,
            "prob_away": prob_away,
            "top_scores": top_scores,
            "markets": {
                "1X2": {
                    "Home Win": {"prob": prob_home, "odds": to_odds(prob_home)},
                    "Draw": {"prob": prob_draw, "odds": to_odds(prob_draw)},
                    "Away Win": {"prob": prob_away, "odds": to_odds(prob_away)},
                },
                "Double Chance": {
                    "Home or Draw (1X)": {"prob": dc_1x, "odds": to_odds(dc_1x)},
                    "Draw or Away (X2)": {"prob": dc_x2, "odds": to_odds(dc_x2)},
                },
                "Over/Under": {
                    "Over 1.5": {"prob": ou["Over 1.5"], "odds": to_odds(ou["Over 1.5"])},
                    "Under 2.5": {"prob": ou["Under 2.5"], "odds": to_odds(ou["Under 2.5"])},
                    "Over 2.5": {"prob": ou["Over 2.5"], "odds": to_odds(ou["Over 2.5"])},
                    "Under 3.5": {"prob": ou["Under 3.5"], "odds": to_odds(ou["Under 3.5"])},
                },
                "BTTS": {
                    "Yes": {"prob": btts_yes, "odds": to_odds(btts_yes)},
                    "No": {"prob": btts_no, "odds": to_odds(btts_no)},
                }
            },
            "recommendation": rec,
            "explanation": explanation
        }

    def _select_balanced_market(self, p_h, p_d, p_a, dc_1x, dc_x2, ou, hcap_a25, h_o15, a_o15, h_xg, a_xg):
        # Combos
        if p_h >= 0.62 and h_o15 >= 0.52:
            return {"category": "1X2 & Over/Under 1.5", "pick": "Home & Over 1.5", "prob": min(0.85, h_o15), "odds": round(max(1.42, (1.0 / h_o15) * 0.94), 2)}
        if p_a >= 0.56 and a_o15 >= 0.48:
            return {"category": "1X2 & Over/Under 1.5", "pick": "Away & Over 1.5", "prob": min(0.84, a_o15), "odds": round(max(1.36, (1.0 / a_o15) * 0.94), 2)}
        # Double Chance
        if p_a > p_h and dc_x2 >= 0.72:
            return {"category": "Double Chance", "pick": "Draw or Away (X2)", "prob": min(0.88, dc_x2), "odds": round(max(1.18, (1.0 / dc_x2) * 0.94), 2)}
        if p_h >= 0.52 and dc_1x >= 0.75:
            return {"category": "Double Chance", "pick": "Home or Draw (1X)", "prob": min(0.89, dc_1x), "odds": round(max(1.18, (1.0 / dc_1x) * 0.94), 2)}
        # Handicap
        if p_h > 0.62 and hcap_a25 >= 0.82:
            return {"category": "Asian Handicap", "pick": "Away (+2.5)", "prob": min(0.88, hcap_a25), "odds": round(max(1.18, (1.0 / hcap_a25) * 0.95), 2)}
        # Goals
        if ou["Over 2.5"] >= 0.60 and (h_xg + a_xg) >= 2.8:
            return {"category": "Over/Under Goals", "pick": "Over 2.5 Goals", "prob": min(0.82, ou["Over 2.5"]), "odds": round(max(1.45, (1.0 / ou["Over 2.5"]) * 0.94), 2)}
        if ou["Under 3.5"] >= 0.70 and (h_xg + a_xg) < 2.6:
            return {"category": "Over/Under Goals", "pick": "Under 3.5 Goals", "prob": min(0.86, ou["Under 3.5"]), "odds": round(max(1.22, (1.0 / ou["Under 3.5"]) * 0.94), 2)}
        return {"category": "Over/Under Goals", "pick": "Over 1.5 Goals", "prob": min(0.88, ou["Over 1.5"]), "odds": round(max(1.18, (1.0 / ou["Over 1.5"]) * 0.94), 2)}

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
