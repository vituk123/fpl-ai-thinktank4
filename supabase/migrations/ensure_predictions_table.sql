-- Ensure predictions table exists with proper schema
-- This migration ensures the predictions table is available for ML predictions

CREATE TABLE IF NOT EXISTS predictions (
  id SERIAL PRIMARY KEY,
  player_id INTEGER NOT NULL,
  gw INTEGER NOT NULL,
  predicted_ev DECIMAL(10, 4),
  confidence_score DECIMAL(5, 4),
  model_version VARCHAR(50),
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(player_id, gw, model_version)
);

-- Create indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_predictions_gw_model 
ON predictions(gw, model_version);

CREATE INDEX IF NOT EXISTS idx_predictions_player_id 
ON predictions(player_id);

-- Add comment for documentation
COMMENT ON TABLE predictions IS 'ML model predictions for player expected values by gameweek';

