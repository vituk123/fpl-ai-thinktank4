# Learning System Documentation

## Overview

The learning system enables the FPL Optimizer to learn from past decisions and outcomes, improving recommendations over time. It's implemented in a **non-destructive way** - all existing functionality remains unchanged, and the learning system is opt-in.

## Features

### 1. Decision History Retrieval
- Retrieves past transfer decisions from the database
- Filters by entry ID, gameweek range
- Parses recommended vs actual transfers

### 2. Outcome Comparison
- Compares actual player performance vs ML predictions
- Calculates prediction errors (MAE, RMSE)
- Identifies where the model over/under-predicts

### 3. User Preference Learning
- Analyzes transfer patterns to learn:
  - **Risk tolerance**: Low, medium, or high (based on hit-taking frequency)
  - **Transfer frequency**: How often you make transfers
  - **Follow rate**: How often you follow top recommendations
  - **Preferred transfer count**: Your typical number of transfers
  - **Forced transfer handling**: How you handle injured players

### 4. Recommendation Adjustment
- Adjusts recommendation priorities based on learned preferences:
  - Risk-averse users: Lower priority for transfer hits
  - Risk-tolerant users: Higher priority for beneficial hits
  - Matches your preferred transfer count
  - Adapts to your decision patterns

### 5. ML Model Fine-Tuning
- Fine-tunes the ML model using feedback data (actual outcomes)
- Uses weighted blending (90% original, 10% fine-tuned) for safety
- Non-destructive: Original model remains unchanged
- Improves predictions based on your specific outcomes

## Usage

### Enable Learning System

```bash
python src/main.py --entry-id YOUR_ENTRY_ID --enable-learning
```

### Record Decisions (Required for Learning)

```bash
python src/main.py --entry-id YOUR_ENTRY_ID --record-decision
```

The `--record-decision` flag saves your decisions to the database. The learning system uses this data to improve future recommendations.

## How It Works

1. **Decision Recording**: When you use `--record-decision`, the system saves:
   - Recommended transfers
   - Actual transfers you made
   - Gameweek and entry ID

2. **Learning Process** (when `--enable-learning` is used):
   - Loads past decisions from database
   - Compares actual outcomes vs predictions
   - Analyzes your preferences and patterns
   - Adjusts recommendation priorities
   - Fine-tunes ML model (if enough data available)

3. **Recommendation Enhancement**:
   - Recommendations are adjusted based on learned preferences
   - ML predictions are improved using feedback data
   - All changes are non-destructive (original recommendations still available)

## Files Modified

- `src/learning_system.py` - New learning system module
- `src/database.py` - Added methods to retrieve decisions and predictions
- `src/ml_engine.py` - Added fine-tuning capability
- `src/main.py` - Integrated learning system (optional)

## Non-Destructive Design

- Learning system is **opt-in** via `--enable-learning` flag
- Original recommendations remain available
- Fine-tuning uses weighted blending (doesn't replace original model)
- All existing functionality unchanged
- Graceful fallback if learning system fails

## Requirements

- Past decisions recorded with `--record-decision`
- At least 3-5 past decisions for meaningful learning
- Database access (Supabase)

## Future Enhancements

- Automatic learning (no flag needed)
- More sophisticated preference learning
- A/B testing of recommendations
- Performance tracking and reporting

