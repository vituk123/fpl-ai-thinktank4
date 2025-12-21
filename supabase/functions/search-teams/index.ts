// Supabase Edge Function for FPL Team Search
// Provides fuzzy search by team name or manager name
import 'jsr:@supabase/functions-js/edge-runtime.d.ts'
import { createClient } from 'jsr:@supabase/supabase-js@2'

const SIMILARITY_THRESHOLD = 0.85 // 85% similarity threshold

Deno.serve(async (req: Request) => {
  // Handle CORS
  if (req.method === 'OPTIONS') {
    return new Response(null, {
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
      },
    })
  }

  try {
    const url = new URL(req.url)
    const query = url.searchParams.get('q')

    if (!query || query.trim().length === 0) {
      return new Response(
        JSON.stringify({ error: 'Query parameter "q" is required' }),
        { 
          status: 400, 
          headers: { 
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
          } 
        }
      )
    }

    // Get Supabase client from environment
    const supabaseUrl = Deno.env.get('SUPABASE_URL') || ''
    const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') || ''

    if (!supabaseUrl || !supabaseServiceKey) {
      return new Response(
        JSON.stringify({ error: 'Supabase configuration missing' }),
        { 
          status: 500, 
          headers: { 
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
          } 
        }
      )
    }

    const supabase = createClient(supabaseUrl, supabaseServiceKey)

    // Normalize query: trim and lowercase for case-insensitive matching
    const normalizedQuery = query.trim().toLowerCase()

    // Search both team_name and manager_name using pg_trgm similarity
    // Use UNION to combine results from both fields and deduplicate by team_id
    const { data, error } = await supabase.rpc('search_fpl_teams', {
      search_query: normalizedQuery,
      similarity_threshold: SIMILARITY_THRESHOLD
    })

    if (error) {
      console.error('Database error:', error)
      return new Response(
        JSON.stringify({ error: 'Database query failed', details: error.message }),
        { 
          status: 500, 
          headers: { 
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
          } 
        }
      )
    }

    // Deduplicate results by team_id and sort by highest similarity
    const matches = (data || []).reduce((acc: any[], match: any) => {
      const existing = acc.find(m => m.team_id === match.team_id)
      if (!existing) {
        acc.push(match)
      } else if (match.similarity > existing.similarity) {
        // Keep the match with higher similarity
        const index = acc.indexOf(existing)
        acc[index] = match
      }
      return acc
    }, [])

    // Sort by similarity (highest first) and limit to top 20
    matches.sort((a, b) => b.similarity - a.similarity)
    const topMatches = matches.slice(0, 20)

    return new Response(
      JSON.stringify({ 
        matches: topMatches,
        query: normalizedQuery,
        threshold: SIMILARITY_THRESHOLD
      }),
      { 
        status: 200, 
        headers: { 
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*'
        } 
      }
    )
  } catch (error) {
    console.error('Error in search-teams function:', error)
    return new Response(
      JSON.stringify({ error: 'Internal server error', details: error.message }),
      { 
        status: 500, 
        headers: { 
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*'
        } 
      }
    )
  }
})

