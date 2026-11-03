"""
engine.py — Advanced Statistical Modeling & Prediction Engine
Implements Dixon-Coles Bivariate Poisson distribution, multi-market derivations,
and deterministic, statistical match explainability.
"""

import numpy as np
from scipy.stats import poisson


class FootballEngine:
    """
    Bivariate Dixon-Coles inspired predictive engine for football match outcomes.
    Adjusts standard independent Poisson probabilities for low-score correlation (0-0, 1-0, 0-1, 1-1).
    """

    def __init__(self, league_avg_home=1.45, league_avg_away=1.15, rho=-0.11):
        self.league_avg_home = league_avg_home
        self.league_avg_away = league_avg_away
        self.rho = rho

    def calculate_xg(self, home_att, home_def, away_att, away_def):
        """
        Calculates expected goals (lambda, mu) based on relative team strength
        normalized against league scoring baselines.
        """
        home_att = max(0.40, float(home_att))
        home_def = max(0.40, float(home_def))
        away_att = max(0.35, float(away_att))
        away_def = max(0.35, float(away_def))

        home_xg = max(0.35, home_att * away_def * self.league_avg_home)
        away_xg = max(0.25, away_att * home_def * self.league_avg_away)
        return float(round(home_xg, 3)), float(round(away_xg, 3))

    def _tau_correction(self, h, a, lmbda, mu):
        """Dixon-Coles adjustment factor tau(x, y) for low scores."""
        if h == 0 and a == 0:
            return 1.0 - (lmbda * mu * self.rho)
        elif h == 0 and a == 1:
            return 1.0 + (lmbda * self.rho)
        elif h == 1 and a == 0:
            return 1.0 + (mu * self.rho)
        elif h == 1 and a == 1:
            return 1.0 - self.rho
        else:
            return 1.0

    def compute_score_matrix(self, home_xg, away_xg, max_goals=8):
        """
        Computes score probability matrix with Dixon-Coles correction,
        strictly renormalized so sum(P) == 1.0.
        """
        matrix = np.zeros((max_goals, max_goals))
        for h in range(max_goals):
            for a in range(max_goals):
                p_ind = poisson.pmf(h, home_xg) * poisson.pmf(a, away_xg)
                tau = self._tau_correction(h, a, home_xg, away_xg)
                matrix[h][a] = max(0.0, p_ind * tau)

        matrix_sum = np.sum(matrix)
        if matrix_sum > 0:
            matrix = matrix / matrix_sum
        return matrix

    def predict_full_match(self, home_xg, away_xg, home_team="Home", away_team="Away"):
        """
        Derives all statistical betting markets from the bivariate score matrix.
        Returns valid probability distributions and fair implied odds.
        """
        matrix = self.compute_score_matrix(home_xg, away_xg)
        max_goals = matrix.shape[0]

        # 1. 1X2 Probabilities (Guaranteed sum == 100%)
        prob_home = float(np.sum(np.tril(matrix, -1)))
        prob_draw = float(np.sum(np.diag(matrix)))
        prob_away = float(np.sum(np.triu(matrix, 1)))

        total_1x2 = prob_home + prob_draw + prob_away
        if total_1x2 > 0:
            prob_home /= total_1x2
            prob_draw /= total_1x2
            prob_away /= total_1x2

        # 2. Double Chance
        dc_1x = prob_home + prob_draw
        dc_x2 = prob_away + prob_draw
        dc_12 = prob_home + prob_away

        # 3. Over / Under Markets (1.5, 2.5, 3.5)
        ou_probs = {}
        for threshold in [1.5, 2.5, 3.5]:
            u_val = float(np.sum([
                matrix[h][a] for h in range(max_goals) for a in range(max_goals)
                if (h + a) < threshold
            ]))
            ou_probs[f"Under {threshold}"] = u_val
            ou_probs[f"Over {threshold}"] = 1.0 - u_val

        # 4. Both Teams to Score (BTTS)
        btts_yes = float(np.sum(matrix[1:, 1:]))
        btts_no = 1.0 - btts_yes

        # 5. Handicaps
        away_hcap_15 = float(np.sum([
            matrix[h][a] for h in range(max_goals) for a in range(max_goals)
            if (h - a) < 2
        ]))
        away_hcap_25 = float(np.sum([
            matrix[h][a] for h in range(max_goals) for a in range(max_goals)
            if (h - a) < 3
        ]))
        home_hcap_15 = float(np.sum([
            matrix[h][a] for h in range(max_goals) for a in range(max_goals)
            if (a - h) < 2
        ]))

        # 6. Combos: 1X2 & Over/Under 1.5
        h_and_o15 = float(np.sum([
            matrix[h][a] for h in range(max_goals) for a in range(max_goals)
            if h > a and (h + a) >= 2
        ]))
        a_and_o15 = float(np.sum([
            matrix[h][a] for h in range(max_goals) for a in range(max_goals)
            if a > h and (h + a) >= 2
        ]))

        def to_odds(p, margin=0.06):
            p = max(0.01, min(0.99, p))
            return float(round((1.0 / p) * (1.0 - margin), 2))

        markets = {
            "1X2": {
                "Home Win": {"prob": prob_home, "odds": to_odds(prob_home)},
                "Draw": {"prob": prob_draw, "odds": to_odds(prob_draw)},
                "Away Win": {"prob": prob_away, "odds": to_odds(prob_away)},
            },
            "Double Chance": {
                "Home or Draw (1X)": {"prob": dc_1x, "odds": to_odds(dc_1x)},
                "Draw or Away (X2)": {"prob": dc_x2, "odds": to_odds(dc_x2)},
                "Home or Away (12)": {"prob": dc_12, "odds": to_odds(dc_12)},
            },
            "Over/Under": {
                "Over 1.5": {"prob": ou_probs["Over 1.5"], "odds": to_odds(ou_probs["Over 1.5"])},
                "Under 1.5": {"prob": ou_probs["Under 1.5"], "odds": to_odds(ou_probs["Under 1.5"])},
                "Over 2.5": {"prob": ou_probs["Over 2.5"], "odds": to_odds(ou_probs["Over 2.5"])},
                "Under 2.5": {"prob": ou_probs["Under 2.5"], "odds": to_odds(ou_probs["Under 2.5"])},
                "Over 3.5": {"prob": ou_probs["Over 3.5"], "odds": to_odds(ou_probs["Over 3.5"])},
                "Under 3.5": {"prob": ou_probs["Under 3.5"], "odds": to_odds(ou_probs["Under 3.5"])},
            },
            "BTTS": {
                "Yes": {"prob": btts_yes, "odds": to_odds(btts_yes)},
                "No": {"prob": btts_no, "odds": to_odds(btts_no)},
            },
            "Handicaps": {
                "Away (+1.5)": {"prob": away_hcap_15, "odds": to_odds(away_hcap_15)},
                "Away (+2.5)": {"prob": away_hcap_25, "odds": to_odds(away_hcap_25)},
                "Home (+1.5)": {"prob": home_hcap_15, "odds": to_odds(home_hcap_15)},
            },
            "Combos": {
                "Home & Over 1.5": {"prob": h_and_o15, "odds": to_odds(h_and_o15)},
                "Away & Over 1.5": {"prob": a_and_o15, "odds": to_odds(a_and_o15)},
            }
        }

        best_rec = self._select_optimal_market(
            prob_home, prob_draw, prob_away, dc_1x, dc_x2,
            ou_probs, away_hcap_25, away_hcap_15, h_and_o15, a_and_o15,
            home_xg, away_xg
        )

        explanation = self._generate_explanation(
            home_team, away_team, home_xg, away_xg,
            prob_home, prob_draw, prob_away, best_rec
        )

        return {
            "home_xg": home_xg,
            "away_xg": away_xg,
            "score_matrix": matrix.tolist(),
            "markets": markets,
            "recommendation": best_rec,
            "explanation": explanation
        }

    def _select_optimal_market(self, p_h, p_d, p_a, dc_1x, dc_x2, ou, hcap_a25, hcap_a15, h_o15, a_o15, home_xg, away_xg):
        if p_h >= 0.64 and h_o15 >= 0.54:
            return {"category": "1X2 & Over/Under 1.5", "pick": "Home & Over 1.5", "prob": h_o15, "odds": round(max(1.40, min(1.85, (1.0 / h_o15) * 0.94)), 2)}
        if p_a >= 0.58 and a_o15 >= 0.50:
            return {"category": "1X2 & Over/Under 1.5", "pick": "Away & Over 1.5", "prob": a_o15, "odds": round(max(1.30, min(1.75, (1.0 / a_o15) * 0.94)), 2)}
        if p_a > p_h and dc_x2 >= 0.78:
            return {"category": "Double Chance", "pick": "Draw or Away (X2)", "prob": dc_x2, "odds": round(max(1.18, min(1.45, (1.0 / dc_x2) * 0.94)), 2)}
        if p_h >= 0.52 and dc_1x >= 0.82:
            return {"category": "Double Chance", "pick": "Home or Draw (1X)", "prob": dc_1x, "odds": round(max(1.15, min(1.40, (1.0 / dc_1x) * 0.94)), 2)}
        if p_h > 0.65 and hcap_a25 >= 0.86:
            return {"category": "Asian Handicap", "pick": "Away (+2.5)", "prob": hcap_a25, "odds": round(max(1.18, min(1.32, (1.0 / hcap_a25) * 0.95)), 2)}
        if ou["Over 2.5"] >= 0.65 and (home_xg + away_xg) >= 2.9:
            return {"category": "Over/Under Goals", "pick": "Over 2.5 Goals", "prob": ou["Over 2.5"], "odds": round(max(1.40, min(1.85, (1.0 / ou["Over 2.5"]) * 0.94)), 2)}
        if ou["Under 3.5"] >= 0.74 and (home_xg + away_xg) < 2.6:
            return {"category": "Over/Under Goals", "pick": "Under 3.5 Goals", "prob": ou["Under 3.5"], "odds": round(max(1.22, min(1.45, (1.0 / ou["Under 3.5"]) * 0.94)), 2)}
        return {"category": "Over/Under Goals", "pick": "Over 1.5 Goals", "prob": ou["Over 1.5"], "odds": round(max(1.18, min(1.38, (1.0 / ou["Over 1.5"]) * 0.94)), 2)}

    def _generate_explanation(self, home_team, away_team, home_xg, away_xg, p_h, p_d, p_a, rec):
        tot_xg = round(home_xg + away_xg, 2)
        fav_team = home_team if p_h >= p_a else away_team
        fav_prob = max(p_h, p_a) * 100.0

        rationale = (
            f"The Dixon-Coles bivariate model projects an expected goals profile of {home_xg:.2f} xG for {home_team} "
            f"and {away_xg:.2f} xG for {away_team} (Combined Match Expectancy: {tot_xg:.2f} goals). "
            f"{fav_team} holds the tactical initiative with an estimated win probability of {fav_prob:.1f}%. "
            f"The optimal mathematical selection is '{rec['pick']}' ({rec['prob']*100:.1f}% model confidence, "
            f"fair odds ~{rec['odds']:.2f}). "
            f"Primary variance factors: standard low-score variance in football draws ({p_d*100:.1f}% model weight) "
            f"and shot conversion volatility."
        )
        return rationale

    @staticmethod
    def calculate_brier_score(predictions_matrix, actual_outcomes_vector):
        if not len(predictions_matrix) or not len(actual_outcomes_vector):
            return 0.0
        n = len(predictions_matrix)
        total_error = 0.0
        for p_dist, actual in zip(predictions_matrix, actual_outcomes_vector):
            target = [0.0, 0.0, 0.0]
            if 0 <= actual <= 2:
                target[actual] = 1.0
            error = sum((p - y) ** 2 for p, y in zip(p_dist, target))
            total_error += error
        return float(round(total_error / n, 4))

    @staticmethod
    def calculate_binary_log_loss(probabilities, outcomes):
        if not len(probabilities):
            return 0.0
        eps = 1e-15
        losses = []
        for p, y in zip(probabilities, outcomes):
            p = max(eps, min(1.0 - eps, p))
            loss = -(y * np.log(p) + (1.0 - y) * np.log(1.0 - p))
            losses.append(loss)
        return float(round(float(np.mean(losses)), 4))

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
                    "range": f"{int(lower*100)}%-{int(upper*100)}%",
                    "predicted_prob": round(bin_mean_prob * 100, 1),
                    "empirical_hit_rate": round(bin_empirical_rate * 100, 1),
                    "sample_size": count
                })
        return calibration_data
