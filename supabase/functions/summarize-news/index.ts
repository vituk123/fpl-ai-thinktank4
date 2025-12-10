// Supabase Edge Function for FPL News Summarization
// Uses built-in Supabase AI API with Ollama/Llamafile
import 'jsr:@supabase/functions-js/edge-runtime.d.ts'

// Use Llamafile server (Docker container)
// The model name should match what's configured in your Llamafile server
const model = new Supabase.ai.Session('mistral') // Model name in Llamafile server

Deno.serve(async (req: Request) => {
  // Handle CORS
  if (req.method === 'OPTIONS') {
    return new Response(null, {
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
      },
    })
  }

  try {
    const { title, content, url } = await req.json()

    if (!title) {
      return new Response(
        JSON.stringify({ error: 'Title is required' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      )
    }

    // Create prompt for FPL news summarization
    const prompt = `You are an expert Fantasy Premier League (FPL) analyst. Analyze the following news article and extract ONLY information relevant to FPL managers.

Article Title: ${title}
Article Content: ${content || 'No content provided'}
Article URL: ${url || 'N/A'}

Extract and summarize ONLY FPL-relevant information such as:
- Player injuries, fitness updates, or availability
- Transfer news affecting FPL players
- Captaincy recommendations or insights
- Price changes or value analysis
- Fixture difficulty or schedule changes
- Team news affecting lineups or formations
- Player form or performance insights
- Chip usage recommendations (Wildcard, Free Hit, etc.)

IGNORE general football news that doesn't impact FPL decisions (e.g., manager quotes, general match reports, non-FPL related transfers).

CRITICAL: You MUST respond with ONLY valid JSON. No markdown, no code blocks, no explanations. Just the JSON object.

Required JSON format (respond with ONLY this structure):
{
    "summary": "A concise 2-3 sentence summary of FPL-relevant information",
    "relevance_score": 0.5,
    "key_points": ["point 1", "point 2"],
    "player_names": ["Player1"],
    "teams": ["Team1"],
    "article_type": "injury"
}

If the article contains NO FPL-relevant information, set relevance_score to 0.0 and explain why in the summary. Remember: respond with ONLY the JSON object, nothing else.`

    // Run inference with the model
    const response = await model.run(prompt, {
      stream: false,
      timeout: 60, // 60 second timeout
      mode: 'ollama', // Use Ollama mode
    })

    // Parse the response
    let summaryText = ''
    if (typeof response === 'string') {
      summaryText = response
    } else if (response && typeof response === 'object' && 'response' in response) {
      summaryText = String(response.response)
    } else {
      // Handle streaming response if needed
      summaryText = JSON.stringify(response)
    }

    // Try to extract JSON from response
    let jsonText = summaryText.trim()
    
    // Remove markdown code blocks if present
    if (jsonText.includes('```')) {
      const codeBlockMatch = jsonText.match(/```(?:json)?\s*\n?(.*?)\n?```/s)
      if (codeBlockMatch) {
        jsonText = codeBlockMatch[1].trim()
      } else {
        // Fallback: remove lines with ```
        jsonText = jsonText.split('\n').filter(line => !line.includes('```')).join('\n')
      }
    }

    // Extract JSON object
    if (jsonText.includes('{') && jsonText.includes('}')) {
      const startIdx = jsonText.indexOf('{')
      let braceCount = 0
      let endIdx = startIdx
      
      for (let i = startIdx; i < jsonText.length; i++) {
        if (jsonText[i] === '{') braceCount++
        if (jsonText[i] === '}') {
          braceCount--
          if (braceCount === 0) {
            endIdx = i + 1
            break
          }
        }
      }
      
      if (endIdx > startIdx) {
        jsonText = jsonText.substring(startIdx, endIdx)
      }
    }

    // Clean up JSON
    jsonText = jsonText.replace(/,\s*}/g, '}').replace(/,\s*]/g, ']')
    
    // Normalize relevance_score to 0-1 range
    jsonText = jsonText.replace(/"relevance_score":\s*(\d+)(?:\.\d+)?/g, (match, score) => {
      const numScore = parseFloat(score)
      const normalized = numScore > 1 ? Math.min(numScore, 10) / 10.0 : numScore
      return `"relevance_score": ${normalized}`
    })

    let summaryData
    try {
      summaryData = JSON.parse(jsonText)
    } catch (e) {
      // If JSON parsing fails, create a fallback response
      summaryData = {
        summary: summaryText.substring(0, 500),
        relevance_score: 0.5,
        key_points: [],
        article_type: 'general',
        player_names: [],
        teams: []
      }
    }

    // Validate and fill in required fields
    if (!summaryData.summary) summaryData.summary = summaryText.substring(0, 500)
    if (typeof summaryData.relevance_score !== 'number') {
      summaryData.relevance_score = parseFloat(summaryData.relevance_score) || 0.5
    }
    if (!summaryData.key_points) summaryData.key_points = []
    if (!summaryData.article_type) summaryData.article_type = 'general'
    if (!summaryData.player_names) summaryData.player_names = []
    if (!summaryData.teams) summaryData.teams = []

    return new Response(
      JSON.stringify(summaryData),
      {
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
      }
    )

  } catch (error) {
    console.error('Error in summarize-news function:', error)
    return new Response(
      JSON.stringify({ 
        error: 'Failed to summarize article',
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

