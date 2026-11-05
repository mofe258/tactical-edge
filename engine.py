"""
engine.py — Anti-Cut Mathematical Engine for Queen Rins
Implements:
1. Entropy & Chaos Filtering (Blacklists coin-flip matches from accumulators)
2. Differential xG (ΔxG) Dominance Scoring
3. Strict Conviction Rating (Only allows Tier-1 Bankers into Slips)
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

        o_15 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if h + a >= 1.5]))
        o_25 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if h + a >= 2.5]))
        u_35 = float(np.sum([matrix[h][a] for h in range(max_goals) for a in range(max_goals) if h + a < 3.5]))

        # Calculate Tactical Dominance Gap (|ΔxG|)
        delta_xg = abs(home_xg - away_xg)

        # Match Entropy / Chaos Index: High entropy = TRAP match
        # If teams have similar strength, draw is high, outcome is chaotic
        is_trap_match = (delta_xg < 0.28 and prob_draw >= 0.26)

        # Allocate Market with strict Anti-Trap filters
        rec, is_slip_safe = self._allocate_anti_cut_market(
            prob_home, prob_draw, prob_away, dnb_home, dnb_away,
            dc_1x, dc_x2, o_15, o_25, u_35, home_xg, away_xg, is_trap_match
        )

        conviction = "TIER-1 BANKER" if is_slip_safe else "HIGH VOLATILITY (AVOID SLIP)"

        explanation = {
            "summary": f"xG: {home_team} {home_xg:.2f} vs {away_team} {away_xg:.2f} (ΔxG: {delta_xg:.2f}).",
            "supporting": f"Market: '{rec['pick']}'. Conviction: {conviction}.",
            "risk": f"Draw risk: {prob_draw*100:.1f}%. Slip Safety: {'Approved' if is_slip_safe else 'Blocked (Trap)'}."
        }

        return {
            "home_xg": home_xg,
            "away_xg": away_xg,
            "prob_home": prob_home,
            "prob_draw": prob_draw,
            "prob_away": prob_away,
            "evidence_quality": conviction,
            "is_accumulator_eligible": is_slip_safe,
            "reliability_score": round(rec["prob"] * 100, 1),
            "recommendation": rec,
            "explanation": explanation
        }

    def _allocate_anti_cut_market(self, p_h, p_d, p_a, dnb_h, dnb_a, dc_1x, dc_x2, o_15, o_25, u_35, h_xg, a_xg, is_trap):
        """
        Anti-Cut Selector:
        Returns: (selection_dict, is_slip_eligible_boolean)
        """
        tot_xg = h_xg + a_xg

        # If it's a Trap match (like Trabzonspor vs Freiburg), force a defensive buffer and BAN from slips
        if is_trap:
            return {"category": "Over/Under Goals", "pick": "Under 3.5 Goals", "prob": round(u_35, 3), "odds": 1.28}, False

        # 1. Clear Home Dominance (e.g. Atalanta, Monaco, Copenhagen)
        if p_h >= 0.62 and h_xg >= (a_xg + 0.60):
            return {"category": "1X2", "pick": "Home Win", "prob": round(p_h, 3), "odds": round(max(1.35, (1.0 / p_h) * 0.94), 2)}, True

        # 2. Resilient Home Banker -> 1X (Must have >= 75% probability)
        if dc_1x >= 0.76 and h_xg >= a_xg:
            return {"category": "Double Chance", "pick": "Home or Draw (1X)", "prob": round(dc_1x, 3), "odds": round(max(1.24, (1.0 / dc_1x) * 0.94), 2)}, True

        # 3. Away Powerhouse Banker -> X2
        if dc_x2 >= 0.75 and a_xg >= h_xg:
            return {"category": "Double Chance", "pick": "Draw or Away (X2)", "prob": round(dc_x2, 3), "odds": round(max(1.25, (1.0 / dc_x2) * 0.94), 2)}, True

        # 4. Open Scoring Shootout (Over 2.5)
        if o_25 >= 0.62 and tot_xg >= 2.90:
            return {"category": "Over/Under Goals", "pick": "Over 2.5 Goals", "prob": round(o_25, 3), "odds": round(max(1.55, (1.0 / o_25) * 0.94), 2)}, True

        # 5. Draw No Bet Cushions
        if dnb_h >= 0.70:
            return {"category": "Draw No Bet", "pick": "Home DNB", "prob": round(dnb_h, 3), "odds": round(max(1.32, (1.0 / dnb_h) * 0.93), 2)}, True
        if dnb_a >= 0.68:
            return {"category": "Draw No Bet", "pick": "Away DNB", "prob": round(dnb_a, 3), "odds": round(max(1.35, (1.0 / dnb_a) * 0.93), 2)}, True

        # Under 3.5 Goals for tight low-scoring games
        if u_35 >= 0.76 and tot_xg <= 2.30:
            return {"category": "Over/Under Goals", "pick": "Under 3.5 Goals", "prob": round(u_35, 3), "odds": round(max(1.26, (1.0 / u_35) * 0.94), 2)}, True

        # Everything else is flagged as NOT safe for slips
        return {"category": "Double Chance", "pick": "Home or Draw (1X)", "prob": 0.70, "odds": 1.30}, False

    @staticmethod
    def calculate_brier_score(predictions_matrix, actual_outcomes_vector):
        if not len(predictions_matrix) or not len(actual_outcomes_vector):
            return None
        n = len(predictions_matrix)
        total_error = sum(sum((p - (1.0 if actual == i else 0.0)) ** 2 for i, p in enumerate(p_dist)) for p_dist, actual in zip(predictions_matrix, actual_outcomes_vector))
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
