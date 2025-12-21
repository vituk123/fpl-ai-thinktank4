-- Validation Tracking Table
-- Tracks ML model predictions vs actual results for real-world validation

CREATE TABLE IF NOT EXISTS validation_tracking (
  id SERIAL PRIMARY KEY,
  player_id INTEGER NOT NULL,
  player_name VARCHAR(255),
  gw INTEGER NOT NULL,
  season VARCHAR(10),
  model_version VARCHAR(50) NOT NULL,
  
  -- Prediction data
  predicted_ev DECIMAL(10, 4),
  predicted_points_per_90 DECIMAL(10, 4),
  prediction_timestamp TIMESTAMP,
  
  -- Actual results (filled in after gameweek completes)
  actual_points INTEGER,
  actual_points_per_90 DECIMAL(10, 4),
  actual_minutes INTEGER,
  validation_timestamp TIMESTAMP,
  
  -- Metrics
  prediction_error DECIMAL(10, 4),  -- predicted - actual
  absolute_error DECIMAL(10, 4),    -- |predicted - actual|
  squared_error DECIMAL(10, 4),     -- (predicted - actual)^2
  
  -- Metadata
  is_validated BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  
  UNIQUE(player_id, gw, model_version)
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_validation_gw_model 
ON validation_tracking(gw, model_version);

CREATE INDEX IF NOT EXISTS idx_validation_player 
ON validation_tracking(player_id);

CREATE INDEX IF NOT EXISTS idx_validation_validated 
ON validation_tracking(is_validated, gw);

CREATE INDEX IF NOT EXISTS idx_validation_season 
ON validation_tracking(season, gw);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_validation_tracking_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update updated_at
CREATE TRIGGER trigger_update_validation_tracking_updated_at
BEFORE UPDATE ON validation_tracking
FOR EACH ROW
EXECUTE FUNCTION update_validation_tracking_updated_at();

-- Add comments
COMMENT ON TABLE validation_tracking IS 'Tracks ML model predictions vs actual FPL results for real-world validation';
COMMENT ON COLUMN validation_tracking.predicted_ev IS 'Predicted expected value (points)';
COMMENT ON COLUMN validation_tracking.actual_points IS 'Actual points scored in the gameweek';
COMMENT ON COLUMN validation_tracking.is_validated IS 'Whether actual results have been filled in';

