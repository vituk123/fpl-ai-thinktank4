-- Create fpl_teams table for team name/manager name search
-- This table stores FPL team information to enable fuzzy search functionality

-- Enable pg_trgm extension for fuzzy text matching
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create fpl_teams table
CREATE TABLE IF NOT EXISTS fpl_teams (
  team_id INTEGER PRIMARY KEY,
  team_name TEXT NOT NULL,
  manager_name TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Create GIN indexes for fast fuzzy text search on team_name and manager_name
CREATE INDEX IF NOT EXISTS idx_fpl_teams_team_name_trgm 
ON fpl_teams USING gin(team_name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_fpl_teams_manager_name_trgm 
ON fpl_teams USING gin(manager_name gin_trgm_ops);

-- Create standard indexes for exact lookups
CREATE INDEX IF NOT EXISTS idx_fpl_teams_team_id 
ON fpl_teams(team_id);

CREATE INDEX IF NOT EXISTS idx_fpl_teams_team_name 
ON fpl_teams(team_name);

CREATE INDEX IF NOT EXISTS idx_fpl_teams_manager_name 
ON fpl_teams(manager_name);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_fpl_teams_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update updated_at
CREATE TRIGGER trigger_update_fpl_teams_updated_at
BEFORE UPDATE ON fpl_teams
FOR EACH ROW
EXECUTE FUNCTION update_fpl_teams_updated_at();

-- Add comment for documentation
COMMENT ON TABLE fpl_teams IS 'FPL team information for fuzzy search by team name or manager name';
COMMENT ON COLUMN fpl_teams.team_id IS 'FPL entry ID (primary key)';
COMMENT ON COLUMN fpl_teams.team_name IS 'Team name from FPL API';
COMMENT ON COLUMN fpl_teams.manager_name IS 'Full manager name (first + last)';

-- Create function for fuzzy search using pg_trgm
CREATE OR REPLACE FUNCTION search_fpl_teams(
  search_query TEXT,
  similarity_threshold FLOAT DEFAULT 0.85
)
RETURNS TABLE (
  team_id INTEGER,
  team_name TEXT,
  manager_name TEXT,
  similarity FLOAT
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    t.team_id,
    t.team_name,
    t.manager_name,
    GREATEST(
      similarity(LOWER(t.team_name), search_query),
      similarity(LOWER(t.manager_name), search_query)
    ) AS similarity
  FROM fpl_teams t
  WHERE 
    similarity(LOWER(t.team_name), search_query) >= similarity_threshold
    OR similarity(LOWER(t.manager_name), search_query) >= similarity_threshold
  ORDER BY similarity DESC;
END;
$$ LANGUAGE plpgsql STABLE;

