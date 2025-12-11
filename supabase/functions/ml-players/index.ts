// Supabase Edge Function for ML Players
// Proxy - forwards requests to Render FastAPI backend
import 'jsr:@supabase/functions-js/edge-runtime.d.ts'

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
    const renderApiUrl = Deno.env.get('RENDER_API_URL')
    if (!renderApiUrl) {
      throw new Error('RENDER_API_URL environment variable not set')
    }

    const url = new URL(req.url)
    const entryId = url.searchParams.get('entry_id')
    const gameweek = url.searchParams.get('gameweek')
    const modelVersion = url.searchParams.get('model_version') || 'v4.6'
    const limit = url.searchParams.get('limit') || '500'

    if (!entryId) {
      return new Response(
        JSON.stringify({ error: 'entry_id is required' }),
        { status: 400, headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
      )
    }

    // Build query params for Render API
    const params = new URLSearchParams({
      entry_id: entryId,
      model_version: modelVersion,
      limit: limit,
    })
    if (gameweek) params.append('gameweek', gameweek)

    // Forward request to Render FastAPI
    const renderUrl = `${renderApiUrl}/api/v1/ml/players?${params.toString()}`
    
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
        console.error(`Render API error ${response.status}:`, errorText.substring(0, 1000))
        
        let parsedError: any = null
        try {
          parsedError = JSON.parse(errorText)
        } catch {
          // If not JSON, use the text as-is
        }
        
        const renderErrorMessage = parsedError?.detail || parsedError?.error || parsedError?.message || errorText
        
        const errorWithDetails = new Error(`Render API error: ${response.status}`)
        ;(errorWithDetails as any).renderError = {
          status: response.status,
          fullErrorText: errorText,
          parsedError: parsedError,
          errorMessage: renderErrorMessage,
        }
        
        throw errorWithDetails
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
      console.error('Fetch error details:', {
        name: fetchError.name,
        message: fetchError.message,
        cause: fetchError.cause
      })
      
      if (fetchError.name === 'AbortError' || fetchError.message?.includes('aborted')) {
        throw new Error('Request timeout - ML players generation took too long (exceeded 2 minute limit)')
      }
      
      if (fetchError instanceof Error) {
        throw new Error(`Failed to connect to ML backend: ${fetchError.message}`)
      }
      throw fetchError
    }

  } catch (error) {
    console.error('Error in ml-players proxy:', error)
    
    let errorMessage = 'Failed to fetch ML players'
    let statusCode = 500
    let fullError: any = null
    let renderErrorDetails: any = null
    
    if (error instanceof Error) {
      if ((error as any).renderError) {
        renderErrorDetails = (error as any).renderError
        errorMessage = renderErrorDetails.errorMessage || renderErrorDetails.detail || renderErrorDetails.error || error.message
        statusCode = 502
        fullError = {
          status: renderErrorDetails.status,
          fullErrorText: renderErrorDetails.fullErrorText,
          parsedError: renderErrorDetails.parsedError
        }
      } else if (error.message.includes('RENDER_API_URL')) {
        errorMessage = 'ML service configuration error: RENDER_API_URL not set in Supabase environment variables'
        statusCode = 503
      } else if (error.message.includes('timeout')) {
        errorMessage = 'ML service timeout: The request took too long. Please try again.'
        statusCode = 504
      } else if (error.message.includes('Render API error')) {
        errorMessage = `ML backend error: ${error.message}`
        statusCode = 502
      } else {
        errorMessage = error.message
      }
    }
    
    return new Response(
      JSON.stringify({ 
        error: errorMessage,
        message: error instanceof Error ? error.message : String(error),
        fullError: fullError,
        renderError: renderErrorDetails,
        details: 'Check Supabase Edge Function logs and ensure RENDER_API_URL is configured'
      }),
      { 
        status: statusCode,
        headers: { 
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        }
      }
    )
  }
})

