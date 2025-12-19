# Fix .env file encoding issue
$envFile = "C:\fpl-api\.env"

# Create .env file with proper encoding
$lines = @(
    "SUPABASE_URL=https://sdezcbesdubplacfxibc.supabase.co",
    "SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNkZXpjYmVzZHVicGxhY2Z4aWJjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQwODAyNTYsImV4cCI6MjA3OTY1NjI1Nn0.hT-2UDR0HbIwAWQHmw6T-QO5jFwWBuyMI2qgPwJRZAE",
    "DB_CONNECTION_STRING=postgresql://postgres.sdezcbesdubplacfxibc:Nwcdmvaam1`$@aws-0-eu-central-1.pooler.supabase.com:6543/postgres",
    "API_FOOTBALL_KEY=08b18b2d60e1cfea7769c7276226d2d1",
    "NEWS_API_KEY=pub_a13e0ce062804c5891decaa7ac8a27b9",
    "PYTHON_VERSION=3.11",
    "PORT=8080"
)

# Write file with UTF8 encoding without BOM
[System.IO.File]::WriteAllLines($envFile, $lines, [System.Text.UTF8Encoding]::new($false))
Write-Host "Fixed .env file with UTF8 encoding (no BOM)"

