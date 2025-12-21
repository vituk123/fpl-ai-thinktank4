# Real-World Validation Tracking System

This system tracks ML model predictions and compares them to actual FPL results for real-world validation.

## Setup

1. **Run the database migration:**
   ```bash
   # Apply the migration via Supabase dashboard or CLI
   # The migration file is at: supabase/migrations/create_validation_tracking.sql
   ```

2. **The system automatically records predictions** when:
   - ML predictions are generated via the API (`/api/v1/ml/predictions/generate`)
   - ML predictions are generated via `main.py` with ML enabled

## Usage

### Validate a Specific Gameweek

After a gameweek completes, validate the predictions:

```bash
# Validate latest finished gameweek
python3 src/validate_predictions.py --model-version v5.0

# Validate specific gameweek
python3 src/validate_predictions.py --gw 17 --model-version v5.0
```

### Validate All Unvalidated Gameweeks

```bash
python3 src/validate_predictions.py --all --model-version v5.0
```

### View Validation Summary

```bash
# Overall summary
python3 src/validate_predictions.py --summary --model-version v5.0

# Summary for specific gameweek range
python3 src/validate_predictions.py --summary --model-version v5.0 --min-gw 1 --max-gw 20
```

## API Endpoints

### Get Validation Summary
```
GET /api/v1/ml/validation/summary?model_version=v5.0&min_gw=1&max_gw=20
```

Returns:
- Overall metrics (MAE, RMSE, R²)
- Per-gameweek breakdown
- Total validated predictions

### Validate a Gameweek
```
GET /api/v1/ml/validation/validate?gw=17&model_version=v5.0
```

Validates predictions for a specific gameweek and returns:
- Validation metrics (MAE, RMSE, R², MAPE)
- Number of validated predictions
- Comparison statistics

## Metrics Explained

- **MAE (Mean Absolute Error)**: Average absolute difference between predicted and actual points
- **RMSE (Root Mean Squared Error)**: Penalizes larger errors more heavily
- **R² Score**: Proportion of variance explained (1.0 = perfect, 0.0 = no better than mean)
- **MAPE (Mean Absolute Percentage Error)**: Error as percentage of actual points

## Workflow

1. **Predictions are automatically recorded** when generated
2. **After each gameweek completes**, run validation:
   ```bash
   python3 src/validate_predictions.py --gw <completed_gw>
   ```
3. **Monitor performance** over time using the summary:
   ```bash
   python3 src/validate_predictions.py --summary
   ```

## Example Output

```
======================================================================
VALIDATING PREDICTIONS FOR GW17
======================================================================

Validation Results:
  Gameweek: 17
  Model Version: v5.0
  Total Predictions: 500
  Validated Predictions: 487
  Matched Players: 487

Metrics:
  MAE (Mean Absolute Error): 1.23 points
  RMSE (Root Mean Squared Error): 2.45 points
  MAPE (Mean Absolute Percentage Error): 15.67%
  R² Score: 0.8234

  Mean Actual Points: 7.85
  Mean Predicted EV: 7.92

✓ Validation complete!
```

