// Supabase Edge Function for Team Optimization
// Proxy - forwards requests to Render FastAPI backend
import 'jsr:@supabase/functions-js/edge-runtime.d.ts'

Deno.serve(async (req: Request) => {
  // Handle CORS
  if (req.method === 'OPTIONS') {
    return new Response(null, {
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
      },
    })
  }

  try {
    const renderApiUrl = Deno.env.get('RENDER_API_URL')
    if (!renderApiUrl) {
      throw new Error('RENDER_API_URL environment variable not set')
    }

    const url = new URL(req.url)
    const entryId = url.searchParams.get('entry_id')
    const gameweek = url.searchParams.get('gameweek')
    const maxTransfers = url.searchParams.get('max_transfers') || '4'

    if (!entryId) {
      return new Response(
        JSON.stringify({ error: 'entry_id is required' }),
        { status: 400, headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
      )
    }

    // Build query params for Render API
    const params = new URLSearchParams({
      entry_id: entryId,
      max_transfers: maxTransfers,
    })
    if (gameweek) params.append('gameweek', gameweek)

    // Forward request to Render FastAPI
    const renderUrl = `${renderApiUrl}/api/v1/optimize/team?${params.toString()}`
    
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 120000) // 2 minute timeout for ML

    try {
      const response = await fetch(renderUrl, {
        method: req.method,
        headers: {
          'Content-Type': 'application/json',
        },
        signal: controller.signal,
      })

      clearTimeout(timeoutId)

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`Render API error: ${response.status} - ${errorText}`)
      }

      const data = await response.json()

      return new Response(
        JSON.stringify(data),
        {
          status: 200,
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
          },
        }
      )
    } catch (fetchError) {
      clearTimeout(timeoutId)
      if (fetchError.name === 'AbortError') {
        throw new Error('Request timeout - optimization took too long')
      }
      throw fetchError
    }

  } catch (error) {
    console.error('Error in optimize-team proxy:', error)
    return new Response(
      JSON.stringify({ 
        error: 'Failed to optimize team',
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

