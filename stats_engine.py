import numpy as np

class StatsCalculator:
    @staticmethod
    def compute_team_ratings(recent_matches, team_name, is_home=True):
        """
        Analyzes the last 5 matches of a team to calculate:
        - Attack strength (Goals scored relative to expectation)
        - Defense vulnerability (Goals conceded relative to expectation)
        - Form momentum (Weighted points from last 5 games)
        """
        if not recent_matches:
            return 1.0, 1.0, 0.5  # Defaults if no data

        goals_scored = []
        goals_conceded = []
        form_points = []
        
        # Exponential weights: match 5 (most recent) has higher weight than match 1
        weights = [0.1, 0.15, 0.2, 0.25, 0.3][-len(recent_matches):]

        for match in recent_matches:
            if match['home_team'] == team_name:
                scored = match['home_goals']
                conceded = match['away_goals']
            else:
                scored = match['away_goals']
                conceded = match['home_goals']

            goals_scored.append(scored)
            goals_conceded.append(conceded)

            # Form points: Win = 3, Draw = 1, Loss = 0
            if scored > conceded:
                form_points.append(3)
            elif scored == conceded:
                form_points.append(1)
            else:
                form_points.append(0)

        # Weighted averages
        avg_scored = np.average(goals_scored, weights=weights)
        avg_conceded = np.average(goals_conceded, weights=weights)
        norm_form = sum(form_points) / (len(form_points) * 3) # Scale 0.0 to 1.0

        # Normalization (Baseline: ~1.35 goals per game is standard)
        attack_rating = max(0.5, avg_scored / 1.35)
        defense_rating = max(0.5, avg_conceded / 1.35)

        return attack_rating, defense_rating, norm_form