// Supabase Edge Function for ML Recommendations
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
    console.log('ml-recommendations: BYTEHOSTY_API_URL:', bytehostyApiUrl ? 'SET' : 'NOT SET')
    console.log('ml-recommendations: GCP_API_URL:', gcpApiUrl ? 'SET' : 'NOT SET')
    console.log('ml-recommendations: RENDER_API_URL:', renderApiUrl ? 'SET' : 'NOT SET')
    
    if (!bytehostyApiUrl && !gcpApiUrl && !renderApiUrl) {
      throw new Error('No backend API URLs are set')
    }

    const url = new URL(req.url)
    const entryId = url.searchParams.get('entry_id')
    const gameweek = url.searchParams.get('gameweek')
    const maxTransfers = url.searchParams.get('max_transfers') || '4'
    const forcedOutIds = url.searchParams.get('forced_out_ids')
    const modelVersion = url.searchParams.get('model_version') || 'v4.6'

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
      model_version: modelVersion,
    })
    if (gameweek) params.append('gameweek', gameweek)
    if (forcedOutIds) params.append('forced_out_ids', forcedOutIds)

    // Priority: ByteHosty → GCP Cloud Run → Render
    let apiUrl = bytehostyApiUrl || gcpApiUrl || renderApiUrl
    let backendName = bytehostyApiUrl ? 'ByteHosty' : (gcpApiUrl ? 'GCP' : 'Render')
    const backendUrl = `${apiUrl}/api/v1/recommendations/transfers?${params.toString()}`
    console.log('ml-recommendations: Calling backend URL:', backendUrl.replace(apiUrl, `[${backendName}_URL]`))
    
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
        console.error(`${backendName} API error ${response.status}:`, errorText.substring(0, 1000))
        
        // Try fallback backends in priority order
        if (apiUrl === bytehostyApiUrl && (gcpApiUrl || renderApiUrl)) {
          const fallbackUrl = gcpApiUrl 
            ? `${gcpApiUrl}/api/v1/recommendations/transfers?${params.toString()}`
            : `${renderApiUrl}/api/v1/recommendations/transfers?${params.toString()}`
          const fallbackName = gcpApiUrl ? 'GCP' : 'Render'
          console.log(`ml-recommendations: ${backendName} failed, trying ${fallbackName} fallback...`)
          
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
              console.log(`ml-recommendations: ${fallbackName} fallback succeeded`)
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
            console.error(`ml-recommendations: ${fallbackName} fallback also failed:`, fallbackError)
          }
        } else if (apiUrl === gcpApiUrl && renderApiUrl) {
          console.log('ml-recommendations: GCP failed, trying Render fallback...')
          const fallbackUrl = `${renderApiUrl}/api/v1/recommendations/transfers?${params.toString()}`
          
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
              console.log('ml-recommendations: Render fallback succeeded')
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
            console.error('ml-recommendations: Render fallback also failed:', fallbackError)
          }
        }
        
        let parsedError: any = null
        try {
          parsedError = JSON.parse(errorText)
        } catch {
          // If not JSON, use the text as-is
        }
        
        const backendErrorMessage = parsedError?.detail || parsedError?.error || parsedError?.message || errorText
        
        const errorWithDetails = new Error(`${backendName} API error: ${response.status}`)
        ;(errorWithDetails as any).backendError = {
          status: response.status,
          fullErrorText: errorText,
          parsedError: parsedError,
          errorMessage: backendErrorMessage,
          detail: parsedError?.detail,
          error: parsedError?.error,
          message: parsedError?.message,
          backend: backendName,
        }
        ;(errorWithDetails as any).renderError = (errorWithDetails as any).backendError // Backward compatibility
        
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
        throw new Error('Request timeout - ML recommendations took too long (exceeded 2 minute limit)')
      }
      
      // Re-throw with more context
      if (fetchError instanceof Error) {
        throw new Error(`Failed to connect to ML backend: ${fetchError.message}`)
      }
      throw fetchError
    }

  } catch (error) {
    console.error('Error in ml-recommendations proxy:', error)
    
    // Provide more detailed error information
    let errorMessage = 'Failed to fetch ML recommendations'
    let statusCode = 500
    let fullError: any = null
    let renderErrorDetails: any = null
    
    if (error instanceof Error) {
      // Check if this error contains backend API error details
      if ((error as any).backendError || (error as any).renderError) {
        renderErrorDetails = (error as any).backendError || (error as any).renderError
        errorMessage = renderErrorDetails.errorMessage || renderErrorDetails.detail || renderErrorDetails.error || error.message
        statusCode = 502 // Bad Gateway - backend error
        fullError = {
          status: renderErrorDetails.status,
          fullErrorText: renderErrorDetails.fullErrorText,
          parsedError: renderErrorDetails.parsedError,
          backend: renderErrorDetails.backend || 'Unknown'
        }
      } else if (error.message.includes('BYTEHOSTY_API_URL') || error.message.includes('GCP_API_URL') || error.message.includes('RENDER_API_URL')) {
        errorMessage = 'ML service configuration error: No backend API URLs are set in Supabase environment variables'
        statusCode = 503
      } else if (error.message.includes('timeout')) {
        errorMessage = 'ML service timeout: The request took too long. Please try again.'
        statusCode = 504
      } else if (error.message.includes('API error')) {
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
        fullError: fullError, // Include full error details for debugging
        renderError: renderErrorDetails, // Include Render API error details if available
        details: 'Check Supabase Edge Function logs and ensure BYTEHOSTY_API_URL, GCP_API_URL, or RENDER_API_URL is configured'
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

