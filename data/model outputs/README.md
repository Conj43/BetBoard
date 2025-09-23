# LGBM Metrics by Season

This file contains performance metrics for LightGBM models that predict college basketball game outcomes. Each row shows the season, the metric name, and the value.

⸻

## Metrics Explained

### MAE (Mean Absolute Error)
	•	MAE_pts_A / MAE_pts_B
Average difference between the predicted points for Team A (or B) and the actual points scored.
Example: MAE = 8 means the model’s score predictions are off by about 8 points on average.
	•	MAE_total
Average difference between the predicted total points (A + B) and the actual total.
Example: MAE = 13 means the predicted total score is usually 13 points away from the real total.
	•	MAE_margin
Average difference between the predicted margin (Team A’s score − Team B’s score) and the actual margin.
Example: MAE = 9 means the predicted winning margin is off by about 9 points on average.

⸻

## Win Probability Metrics
	•	Brier(A_win)
Measures how close the predicted win probabilities are to reality.
Range: 0 to 1. Lower is better. 0.25 = random guessing; 0.0 = perfect predictions.
	•	LogLoss(A_win)
Punishes confident wrong predictions.
Range: 0 to ∞. Lower is better. Values near 0 mean probabilities were very accurate.
	•	Accuracy(A_win)
Percentage of games where the predicted winner (Team A if probability > 50%, otherwise Team B) matched the actual winner.
Example: Accuracy = 0.65 means the model picked the right winner 65% of the time.

⸻

## Probability Averages
	•	Avg P(over)
The average probability (across all games) that the model assigned to the game going Over the betting total.
Example: 0.55 means on average the model thought there was a 55% chance of going Over.
	•	Avg P(A covers)
The average probability (across all games) that the model assigned to Team A covering the spread.
Example: 0.48 means on average the model thought A had a 48% chance to cover.

⸻
