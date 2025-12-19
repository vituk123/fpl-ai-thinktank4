// Supabase Edge Function for ML Report
// Proxy - forwards requests to Render FastAPI backend
import 'jsr:@supabase/functions-js/edge-runtime.d.ts'

Deno.serve(async (req: Request) => {
  // CORS headers helper
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  }
  
  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders })
  }

  try {
    const bytehostyApiUrl = Deno.env.get('BYTEHOSTY_API_URL')
    const gcpApiUrl = Deno.env.get('GCP_API_URL')
    const renderApiUrl = Deno.env.get('RENDER_API_URL')
    console.log('ml-report: BYTEHOSTY_API_URL:', bytehostyApiUrl ? 'SET' : 'NOT SET')
    console.log('ml-report: GCP_API_URL:', gcpApiUrl ? 'SET' : 'NOT SET')
    console.log('ml-report: RENDER_API_URL:', renderApiUrl ? 'SET' : 'NOT SET')
    
    if (!bytehostyApiUrl && !gcpApiUrl && !renderApiUrl) {
      console.error('ml-report: No backend API URLs are set')
      return new Response(
        JSON.stringify({ 
          error: 'ML service configuration error: No backend API URLs are set',
          details: 'Please set BYTEHOSTY_API_URL, GCP_API_URL, or RENDER_API_URL secret in Supabase'
        }),
        { 
          status: 503, 
          headers: { 
            'Content-Type': 'application/json',
            ...corsHeaders
          } 
        }
      )
    }

    const url = new URL(req.url)
    const entryId = url.searchParams.get('entry_id')
    const gameweek = url.searchParams.get('gameweek')
    const modelVersion = url.searchParams.get('model_version') || 'v4.6'
    const fastMode = url.searchParams.get('fast_mode') === 'true' // Read fast_mode param

    console.log('ml-report: Request params:', { entryId, gameweek, modelVersion, fastMode })

    if (!entryId) {
      return new Response(
        JSON.stringify({ error: 'entry_id is required' }),
        { status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
      )
    }

    // Build query params for backend API
    const params = new URLSearchParams({
      entry_id: entryId,
      model_version: modelVersion,
      fast_mode: String(fastMode), // Pass fast_mode to backend
    })
    if (gameweek) params.append('gameweek', gameweek)

    // Priority: ByteHosty → GCP Cloud Run → Render
    let apiUrl = bytehostyApiUrl || gcpApiUrl || renderApiUrl
    let backendName = bytehostyApiUrl ? 'ByteHosty' : (gcpApiUrl ? 'GCP' : 'Render')
    const backendUrl = `${apiUrl}/api/v1/ml/report?${params.toString()}`
    console.log('ml-report: Calling backend URL:', backendUrl.replace(apiUrl, `[${backendName}_URL]`))
    
    const controller = new AbortController()
    // Supabase edge functions have a max timeout (typically 60s free, 300s paid)
    // Use shorter timeout for free tier, longer for paid
    // For fast_mode, use 60s; for full mode, use 240s (but Supabase free tier will timeout at 60s)
    // Note: Supabase free tier has 60s hard limit, so full mode will timeout
    const timeoutDuration = fastMode ? 55000 : 55000; // Use 55s for both to stay under Supabase 60s limit
    const timeoutId = setTimeout(() => controller.abort(), timeoutDuration)

    try {
      console.log(`ml-report: Starting fetch to ${backendName}...`)
      const response = await fetch(backendUrl, {
        method: req.method,
        headers: {
          'Content-Type': 'application/json',
        },
        signal: controller.signal,
      })

      console.log(`ml-report: ${backendName} response status:`, response.status)

      clearTimeout(timeoutId)

      if (!response.ok) {
        const errorText = await response.text()
        console.error(`${backendName} API error ${response.status}:`, errorText.substring(0, 1000))
        
        // Try fallback backends in priority order
        if (apiUrl === bytehostyApiUrl && (gcpApiUrl || renderApiUrl)) {
          // ByteHosty failed, try GCP or Render
          const fallbackUrl = gcpApiUrl 
            ? `${gcpApiUrl}/api/v1/ml/report?${params.toString()}`
            : `${renderApiUrl}/api/v1/ml/report?${params.toString()}`
          const fallbackName = gcpApiUrl ? 'GCP' : 'Render'
          console.log(`ml-report: ${backendName} failed, trying ${fallbackName} fallback...`)
          
          const fallbackController = new AbortController()
          const fallbackTimeoutId = setTimeout(() => fallbackController.abort(), timeoutDuration)
          
          try {
            const fallbackResponse = await fetch(fallbackUrl, {
              method: req.method,
              headers: { 'Content-Type': 'application/json' },
              signal: fallbackController.signal,
            })
            
            clearTimeout(fallbackTimeoutId)
            
            if (fallbackResponse.ok) {
              const fallbackData = await fallbackResponse.json()
              console.log(`ml-report: ${fallbackName} fallback succeeded`)
              return new Response(
                JSON.stringify(fallbackData),
                {
                  status: 200,
                  headers: {
                    'Content-Type': 'application/json',
                    ...corsHeaders,
                  },
                }
              )
            }
          } catch (fallbackError) {
            clearTimeout(fallbackTimeoutId)
            console.error(`ml-report: ${fallbackName} fallback also failed:`, fallbackError)
          }
        } else if (apiUrl === gcpApiUrl && renderApiUrl) {
          // GCP failed, try Render
          console.log('ml-report: GCP failed, trying Render fallback...')
          const fallbackUrl = `${renderApiUrl}/api/v1/ml/report?${params.toString()}`
          
          const fallbackController = new AbortController()
          const fallbackTimeoutId = setTimeout(() => fallbackController.abort(), timeoutDuration)
          
          try {
            const fallbackResponse = await fetch(fallbackUrl, {
              method: req.method,
              headers: { 'Content-Type': 'application/json' },
              signal: fallbackController.signal,
            })
            
            clearTimeout(fallbackTimeoutId)
            
            if (fallbackResponse.ok) {
              const fallbackData = await fallbackResponse.json()
              console.log('ml-report: Render fallback succeeded')
              return new Response(
                JSON.stringify(fallbackData),
                {
                  status: 200,
                  headers: {
                    'Content-Type': 'application/json',
                    ...corsHeaders,
                  },
                }
              )
            }
          } catch (fallbackError) {
            clearTimeout(fallbackTimeoutId)
            console.error('ml-report: Render fallback also failed:', fallbackError)
          }
        }
        
        let parsedError: any = null
        try {
          parsedError = JSON.parse(errorText)
        } catch {
          // If not JSON, use the text as-is
        }
        
        // Extract error message - try detail first, then error, then message, then full text
        const backendErrorMessage = parsedError?.detail || parsedError?.error || parsedError?.message || errorText.substring(0, 500)
        
        // Create error object with backendError property
        const backendErrorDetails = {
          status: response.status,
          fullErrorText: errorText.substring(0, 3000),
          parsedError: parsedError,
          errorMessage: backendErrorMessage,
          detail: parsedError?.detail,
          backend: backendName,
        }
        
        // Throw error that will be caught by outer catch
        const errorWithDetails: any = new Error(`${backendName} API error: ${response.status} - ${backendErrorMessage}`)
        errorWithDetails.backendError = backendErrorDetails
        errorWithDetails.renderError = backendErrorDetails // Keep for backward compatibility
        
        throw errorWithDetails
      }

      const data = await response.json()
      console.log(`ml-report: ${backendName} response received, data keys:`, Object.keys(data))

      return new Response(
        JSON.stringify(data),
        {
          status: 200,
          headers: {
            'Content-Type': 'application/json',
            ...corsHeaders,
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
        // Return timeout error with CORS headers
        return new Response(
          JSON.stringify({ 
            error: 'ML report generation timeout',
            message: `The ML report generation took too long (exceeded ${timeoutDuration / 1000} second limit). The analysis is computationally intensive. Please try again with fast_mode=true or contact support.`,
            timeout: true,
            timeoutDuration: timeoutDuration / 1000
          }),
          { 
            status: 504,
            headers: { 
              'Content-Type': 'application/json',
              ...corsHeaders,
            }
          }
        )
      }
      
      if (fetchError instanceof Error) {
        throw new Error(`Failed to connect to ML backend: ${fetchError.message}`)
      }
      throw fetchError
    }

  } catch (error: any) {
    console.error('Error in ml-report proxy:', error)
    console.error('Error renderError property:', error?.renderError)
    
    let errorMessage = 'Failed to fetch ML report'
    let statusCode = 500
    let fullError: any = null
    let renderErrorDetails: any = null
    
    // Check for backendError property (from GCP/Render API errors)
    if (error?.backendError || error?.renderError) {
      renderErrorDetails = error.backendError || error.renderError
      // Prefer detail field (from FastAPI HTTPException) over errorMessage
      errorMessage = renderErrorDetails.detail || renderErrorDetails.errorMessage || renderErrorDetails.error || error.message
      statusCode = 502
      fullError = {
        status: renderErrorDetails.status,
        fullErrorText: renderErrorDetails.fullErrorText?.substring(0, 2000),
        parsedError: renderErrorDetails.parsedError,
        detail: renderErrorDetails.detail,
        backend: renderErrorDetails.backend || 'Unknown'
      }
      // Include the full error text in the response for debugging (if detail doesn't have traceback)
      if (renderErrorDetails.fullErrorText && !errorMessage.includes('Traceback')) {
        errorMessage = renderErrorDetails.fullErrorText.substring(0, 2000)
      }
    } else if (error instanceof Error) {
      if (error.message.includes('BYTEHOSTY_API_URL') || error.message.includes('GCP_API_URL') || error.message.includes('RENDER_API_URL')) {
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
        fullError: fullError,
        renderError: renderErrorDetails,
        details: 'Check Supabase Edge Function logs and ensure BYTEHOSTY_API_URL, GCP_API_URL, or RENDER_API_URL is configured'
      }),
      { 
        status: statusCode,
        headers: { 
          'Content-Type': 'application/json',
          ...corsHeaders,
        }
      }
    )
  }
})

