# Update .env file with correct database password
$envFile = "C:\fpl-api\.env"
$newPassword = "Nwcdmvaam1`$"
$newConnectionString = "postgresql://postgres.sdezcbesdubplacfxibc:$newPassword@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"

$content = Get-Content $envFile
$updatedContent = $content | ForEach-Object {
    if ($_ -match '^DB_CONNECTION_STRING=') {
        "DB_CONNECTION_STRING=$newConnectionString"
    } else {
        $_
    }
}

$updatedContent | Set-Content $envFile -Encoding UTF8
Write-Host "Updated DB_CONNECTION_STRING in .env file"

