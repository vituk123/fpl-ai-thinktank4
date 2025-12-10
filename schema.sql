-- FPL Optimizer Database Schema
-- Run this in your Supabase SQL Editor

-- Table 1: Historical player statistics (2019-2024)
CREATE TABLE IF NOT EXISTS player_history (
    id SERIAL PRIMARY KEY,
    player_id INTEGER NOT NULL,
    player_name VARCHAR(255) NOT NULL,
    season VARCHAR(10) NOT NULL,  -- e.g., '2023-24'
    gw INTEGER NOT NULL,
    minutes INTEGER DEFAULT 0,
    total_points INTEGER DEFAULT 0,
    goals_scored INTEGER DEFAULT 0,
    assists INTEGER DEFAULT 0,
    clean_sheets INTEGER DEFAULT 0,
    goals_conceded INTEGER DEFAULT 0,
    own_goals INTEGER DEFAULT 0,
    penalties_saved INTEGER DEFAULT 0,
    penalties_missed INTEGER DEFAULT 0,
    yellow_cards INTEGER DEFAULT 0,
    red_cards INTEGER DEFAULT 0,
    saves INTEGER DEFAULT 0,
    bonus INTEGER DEFAULT 0,
    bps INTEGER DEFAULT 0,
    influence DECIMAL(10,2) DEFAULT 0,
    creativity DECIMAL(10,2) DEFAULT 0,
    threat DECIMAL(10,2) DEFAULT 0,
    ict_index DECIMAL(10,2) DEFAULT 0,
    expected_goals DECIMAL(10,2) DEFAULT 0,
    expected_assists DECIMAL(10,2) DEFAULT 0,
    expected_goal_involvements DECIMAL(10,2) DEFAULT 0,
    expected_goals_conceded DECIMAL(10,2) DEFAULT 0,
    value INTEGER DEFAULT 0,
    transfers_balance INTEGER DEFAULT 0,
    selected INTEGER DEFAULT 0,
    transfers_in INTEGER DEFAULT 0,
    transfers_out INTEGER DEFAULT 0,
    opponent_team INTEGER,
    opponent_strength INTEGER DEFAULT 3,
    was_home BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(player_id, season, gw)
);

-- Index for faster queries
CREATE INDEX IF NOT EXISTS idx_player_history_player_season ON player_history(player_id, season);
CREATE INDEX IF NOT EXISTS idx_player_history_gw ON player_history(gw);

-- Table 2: Current season statistics
CREATE TABLE IF NOT EXISTS current_stats (
    id SERIAL PRIMARY KEY,
    player_id INTEGER UNIQUE NOT NULL,
    player_name VARCHAR(255) NOT NULL,
    team_id INTEGER NOT NULL,
    team_name VARCHAR(255),
    position VARCHAR(10) NOT NULL,  -- GKP, DEF, MID, FWD
    now_cost INTEGER NOT NULL,
    minutes INTEGER DEFAULT 0,
    total_points INTEGER DEFAULT 0,
    goals_scored INTEGER DEFAULT 0,
    assists INTEGER DEFAULT 0,
    clean_sheets INTEGER DEFAULT 0,
    goals_conceded INTEGER DEFAULT 0,
    own_goals INTEGER DEFAULT 0,
    penalties_saved INTEGER DEFAULT 0,
    penalties_missed INTEGER DEFAULT 0,
    yellow_cards INTEGER DEFAULT 0,
    red_cards INTEGER DEFAULT 0,
    saves INTEGER DEFAULT 0,
    bonus INTEGER DEFAULT 0,
    bps INTEGER DEFAULT 0,
    influence DECIMAL(10,2) DEFAULT 0,
    creativity DECIMAL(10,2) DEFAULT 0,
    threat DECIMAL(10,2) DEFAULT 0,
    ict_index DECIMAL(10,2) DEFAULT 0,
    expected_goals DECIMAL(10,2) DEFAULT 0,
    expected_assists DECIMAL(10,2) DEFAULT 0,
    expected_goal_involvements DECIMAL(10,2) DEFAULT 0,
    expected_goals_conceded DECIMAL(10,2) DEFAULT 0,
    form DECIMAL(10,2) DEFAULT 0,
    points_per_game DECIMAL(10,2) DEFAULT 0,
    selected_by_percent DECIMAL(10,2) DEFAULT 0,
    ep_next DECIMAL(10,2) DEFAULT 0,
    ep_this DECIMAL(10,2) DEFAULT 0,
    news TEXT,
    news_added TIMESTAMP,
    chance_of_playing_next_round INTEGER,
    chance_of_playing_this_round INTEGER,
    status VARCHAR(10) DEFAULT 'a',  -- a=available, d=doubtful, i=injured, u=unavailable
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_current_stats_player_id ON current_stats(player_id);
CREATE INDEX IF NOT EXISTS idx_current_stats_team ON current_stats(team_id);

-- Table 3: ML Predictions
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    player_id INTEGER NOT NULL,
    player_name VARCHAR(255) NOT NULL,
    gw INTEGER NOT NULL,
    predicted_points DECIMAL(10,2) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    features JSONB,  -- Store feature values used for prediction
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(player_id, gw, model_version)
);

CREATE INDEX IF NOT EXISTS idx_predictions_gw ON predictions(gw);
CREATE INDEX IF NOT EXISTS idx_predictions_player ON predictions(player_id);

-- Table 4: Decision Log
CREATE TABLE IF NOT EXISTS decisions (
    id SERIAL PRIMARY KEY,
    gw INTEGER NOT NULL,
    entry_id INTEGER,
    recommended_transfers JSONB NOT NULL,  -- Array of {player_out, player_in, cost}
    recommended_captain INTEGER,
    recommended_vice_captain INTEGER,
    recommended_chip VARCHAR(50),
    expected_points DECIMAL(10,2),
    actual_transfers_made JSONB,  -- What user actually did
    actual_captain INTEGER,
    actual_chip VARCHAR(50),
    actual_points DECIMAL(10,2),
    bank_value DECIMAL(10,2),
    squad_value DECIMAL(10,2),
    free_transfers INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_decisions_gw ON decisions(gw);
CREATE INDEX IF NOT EXISTS idx_decisions_entry ON decisions(entry_id);

-- Table 5: Model Performance Tracking
CREATE TABLE IF NOT EXISTS model_performance (
    id SERIAL PRIMARY KEY,
    model_version VARCHAR(50) NOT NULL,
    gw INTEGER NOT NULL,
    mae DECIMAL(10,4),  -- Mean Absolute Error
    rmse DECIMAL(10,4),  -- Root Mean Squared Error
    r2_score DECIMAL(10,4),
    training_samples INTEGER,
    training_date TIMESTAMP DEFAULT NOW(),
    UNIQUE(model_version, gw)
);

-- Table 6: Feature Importance (for ML interpretability)
CREATE TABLE IF NOT EXISTS feature_importance (
    id SERIAL PRIMARY KEY,
    model_version VARCHAR(50) NOT NULL,
    feature_name VARCHAR(100) NOT NULL,
    importance_score DECIMAL(10,6) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_feature_importance_model ON feature_importance(model_version);