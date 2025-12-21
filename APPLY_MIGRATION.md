# Apply FPL Teams Migration to Supabase

Since local Supabase is not running, apply the migration via Supabase Dashboard:

## Option 1: Via Supabase Dashboard (Recommended)

1. Go to https://supabase.com/dashboard/project/sdezcbesdubplacfxibc
2. Navigate to **SQL Editor**
3. Copy and paste the contents of `supabase/migrations/create_fpl_teams_table.sql`
4. Click **Run** to execute the migration

## Option 2: Via Supabase CLI (if you have remote linked)

```bash
supabase db push
```

## Migration File Location

The migration file is at: `supabase/migrations/create_fpl_teams_table.sql`

## What the Migration Does

- Creates `fpl_teams` table
- Enables `pg_trgm` extension for fuzzy matching
- Creates GIN indexes for fast text search
- Creates `search_fpl_teams()` function for fuzzy search

## Verify Migration

After applying, verify the table exists:

```sql
SELECT * FROM fpl_teams LIMIT 5;
```

And verify the function exists:

```sql
SELECT proname FROM pg_proc WHERE proname = 'search_fpl_teams';
```

