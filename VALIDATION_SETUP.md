# Real-World Validation Tracking - Setup Instructions

## ✅ What Has Been Created

1. **Database Migration**: `supabase/migrations/create_validation_tracking.sql`
   - Creates `validation_tracking` table
   - Stores predictions and actual results
   - Tracks validation metrics

2. **Validation Tracker Module**: `src/validation_tracker.py`
   - Records predictions automatically
   - Validates predictions against actual results
   - Generates validation summaries

3. **Validation Script**: `src/validate_predictions.py`
   - Command-line tool for validation
   - Can validate specific gameweeks or all unvalidated ones
   - Shows validation summaries

4. **API Endpoints** (in `src/dashboard_api.py`):
   - `GET /api/v1/ml/validation/summary` - Get validation summary
   - `GET /api/v1/ml/validation/validate?gw=X` - Validate a gameweek

5. **Automatic Integration**:
   - Predictions are automatically recorded when generated via API or CLI
   - No manual intervention needed for recording

## 🔧 Setup Steps

### Step 1: Apply Database Migration

**Option A: Via Supabase Dashboard (Recommended)**
1. Go to your Supabase Dashboard
2. Navigate to **SQL Editor**
3. Open the file: `supabase/migrations/create_validation_tracking.sql`
4. Copy and paste the entire SQL into the editor
5. Click **Run**

**Option B: Via Supabase CLI**
```bash
supabase db push
```

### Step 2: Verify Setup

```bash
# Test the validation script
python3 src/validate_predictions.py --summary --model-version v5.0
```

If you see "No validated predictions found", that's normal - it means the table exists but no validations have been run yet.

## 📊 How It Works

### Automatic Prediction Recording

When ML predictions are generated (via API or CLI), they are automatically recorded in the `validation_tracking` table with:
- Player ID and name
- Gameweek
- Predicted EV and points per 90
- Model version
- Timestamp

### Manual Validation

After each gameweek completes, run:

```bash
# Validate latest finished gameweek
python3 src/validate_predictions.py --model-version v5.0

# Or validate a specific gameweek
python3 src/validate_predictions.py --gw 17 --model-version v5.0
```

This will:
1. Fetch all predictions for that gameweek
2. Get actual results from FPL API
3. Calculate errors (MAE, RMSE, R²)
4. Update the database with validation results

### View Results

```bash
# Overall summary
python3 src/validate_predictions.py --summary --model-version v5.0

# Summary for specific range
python3 src/validate_predictions.py --summary --model-version v5.0 --min-gw 1 --max-gw 20
```

## 🎯 Next Steps

1. **Apply the migration** (Step 1 above)
2. **Generate some predictions** (they'll be automatically recorded)
3. **After GW17 completes**, run validation:
   ```bash
   python3 src/validate_predictions.py --gw 17 --model-version v5.0
   ```
4. **Monitor performance** over time using summaries

## 📈 Expected Output

After validating a gameweek, you'll see:

```
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
```

This will help you track whether the model's high test scores (R² > 0.99) translate to real-world performance.

