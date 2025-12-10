// Supabase Edge Function for ML Predictions
// Standalone - fetches pre-computed predictions from database
import 'jsr:@supabase/functions-js/edge-runtime.d.ts'
import { createClient } from 'jsr:@supabase/supabase-js@2'

Deno.serve(async (req: Request) => {
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
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_ANON_KEY') ?? ''
    )

    const url = new URL(req.url)
    const gameweek = url.searchParams.get('gameweek') || '999'
    const entryId = url.searchParams.get('entry_id')
    const modelVersion = url.searchParams.get('model_version') || 'v4.6'

    // Fetch predictions from database
    let query = supabaseClient
      .from('predictions')
      .select('*')
      .eq('gw', parseInt(gameweek))
      .eq('model_version', modelVersion)
      .order('predicted_ev', { ascending: false })
      .limit(100)

    const { data, error } = await query

    if (error) throw error

    let predictions = data || []

    // If entry_id provided, fetch user's squad and filter predictions
    if (entryId && predictions.length > 0) {
      try {
        const picksRes = await fetch(
          `https://fantasy.premierleague.com/api/entry/${entryId}/event/${gameweek}/picks/`
        )
        const picksData = await picksRes.json()
        
        if (picksData?.picks) {
          const squadIds = new Set(picksData.picks.map((p: any) => p.element))
          predictions = predictions.filter((p: any) => squadIds.has(p.player_id))
        }
      } catch (e) {
        console.warn('Could not filter by squad:', e)
      }
    }

    return new Response(
      JSON.stringify({
        data: {
          predictions: predictions,
          gameweek: parseInt(gameweek),
          model_version: modelVersion,
          count: predictions.length
        },
        meta: {
          last_update: new Date().toISOString()
        }
      }),
      {
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
      }
    )

  } catch (error) {
    console.error('Error in ml-predictions function:', error)
    return new Response(
      JSON.stringify({ 
        error: 'Failed to fetch predictions',
        message: error instanceof Error ? error.message : String(error)
      }),
      { 
        status: 500,
        headers: { 
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        }
      }
    )
  }
})

