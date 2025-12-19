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
    const bytehostyApiUrl = Deno.env.get('BYTEHOSTY_API_URL')
    const gcpApiUrl = Deno.env.get('GCP_API_URL')
    const renderApiUrl = Deno.env.get('RENDER_API_URL')
    console.log('optimize-team: BYTEHOSTY_API_URL:', bytehostyApiUrl ? 'SET' : 'NOT SET')
    console.log('optimize-team: GCP_API_URL:', gcpApiUrl ? 'SET' : 'NOT SET')
    console.log('optimize-team: RENDER_API_URL:', renderApiUrl ? 'SET' : 'NOT SET')
    
    if (!bytehostyApiUrl && !gcpApiUrl && !renderApiUrl) {
      throw new Error('No backend API URLs are set')
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

    // Build query params for backend API
    const params = new URLSearchParams({
      entry_id: entryId,
      max_transfers: maxTransfers,
    })
    if (gameweek) params.append('gameweek', gameweek)

    // Priority: ByteHosty → GCP Cloud Run → Render
    let apiUrl = bytehostyApiUrl || gcpApiUrl || renderApiUrl
    let backendName = bytehostyApiUrl ? 'ByteHosty' : (gcpApiUrl ? 'GCP' : 'Render')
    const backendUrl = `${apiUrl}/api/v1/optimize/team?${params.toString()}`
    console.log('optimize-team: Calling backend URL:', backendUrl.replace(apiUrl, `[${backendName}_URL]`))
    
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 120000) // 2 minute timeout for ML

    try {
      const response = await fetch(backendUrl, {
        method: req.method,
        headers: {
          'Content-Type': 'application/json',
        },
        signal: controller.signal,
      })

      clearTimeout(timeoutId)

      if (!response.ok) {
        const errorText = await response.text()
        
        // Try fallback backends in priority order
        if (apiUrl === bytehostyApiUrl && (gcpApiUrl || renderApiUrl)) {
          const fallbackUrl = gcpApiUrl 
            ? `${gcpApiUrl}/api/v1/optimize/team?${params.toString()}`
            : `${renderApiUrl}/api/v1/optimize/team?${params.toString()}`
          const fallbackName = gcpApiUrl ? 'GCP' : 'Render'
          console.log(`optimize-team: ${backendName} failed, trying ${fallbackName} fallback...`)
          
          const fallbackController = new AbortController()
          const fallbackTimeoutId = setTimeout(() => fallbackController.abort(), 120000)
          
          try {
            const fallbackResponse = await fetch(fallbackUrl, {
              method: req.method,
              headers: { 'Content-Type': 'application/json' },
              signal: fallbackController.signal,
            })
            
            clearTimeout(fallbackTimeoutId)
            
            if (fallbackResponse.ok) {
              const fallbackData = await fallbackResponse.json()
              console.log(`optimize-team: ${fallbackName} fallback succeeded`)
              return new Response(
                JSON.stringify(fallbackData),
                {
                  status: 200,
                  headers: {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                  },
                }
              )
            }
          } catch (fallbackError) {
            clearTimeout(fallbackTimeoutId)
            console.error(`optimize-team: ${fallbackName} fallback also failed:`, fallbackError)
          }
        } else if (apiUrl === gcpApiUrl && renderApiUrl) {
          console.log('optimize-team: GCP failed, trying Render fallback...')
          const fallbackUrl = `${renderApiUrl}/api/v1/optimize/team?${params.toString()}`
          
          const fallbackController = new AbortController()
          const fallbackTimeoutId = setTimeout(() => fallbackController.abort(), 120000)
          
          try {
            const fallbackResponse = await fetch(fallbackUrl, {
              method: req.method,
              headers: { 'Content-Type': 'application/json' },
              signal: fallbackController.signal,
            })
            
            clearTimeout(fallbackTimeoutId)
            
            if (fallbackResponse.ok) {
              const fallbackData = await fallbackResponse.json()
              console.log('optimize-team: Render fallback succeeded')
              return new Response(
                JSON.stringify(fallbackData),
                {
                  status: 200,
                  headers: {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                  },
                }
              )
            }
          } catch (fallbackError) {
            clearTimeout(fallbackTimeoutId)
            console.error('optimize-team: Render fallback also failed:', fallbackError)
          }
        }
        
        throw new Error(`${backendName} API error: ${response.status} - ${errorText}`)
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

