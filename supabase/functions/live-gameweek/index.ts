// Supabase Edge Function for Live Gameweek Tracking
// Standalone - directly fetches from FPL API
import 'jsr:@supabase/functions-js/edge-runtime.d.ts'
import { createClient } from 'jsr:@supabase/supabase-js@2'

const FPL_API_BASE = 'https://fantasy.premierleague.com/api'

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
    const gameweek = url.searchParams.get('gameweek')
    const entryId = url.searchParams.get('entry_id')
    const leagueId = url.searchParams.get('league_id')

    if (!gameweek || !entryId) {
      return new Response(
        JSON.stringify({ error: 'gameweek and entry_id are required' }),
        { status: 400, headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } }
      )
    }

    // Fetch data from FPL API in parallel
    const [bootstrapRes, entryInfoRes, entryHistoryRes, picksRes, fixturesRes] = await Promise.all([
      fetch(`${FPL_API_BASE}/bootstrap-static/`),
      fetch(`${FPL_API_BASE}/entry/${entryId}/`),
      fetch(`${FPL_API_BASE}/entry/${entryId}/history/`),
      fetch(`${FPL_API_BASE}/entry/${entryId}/event/${gameweek}/picks/`).catch(() => null),
      fetch(`${FPL_API_BASE}/fixtures/`),
    ])

    const [bootstrap, entryInfo, entryHistory, picksData, fixtures] = await Promise.all([
      bootstrapRes.json(),
      entryInfoRes.json(),
      entryHistoryRes.json(),
      picksRes?.json().catch(() => null),
      fixturesRes.json(),
    ])

    // If picks not available for current GW, try previous GW
    let picks = picksData
    if (!picks || !picks.picks) {
      try {
        const prevPicksRes = await fetch(`${FPL_API_BASE}/entry/${entryId}/event/${parseInt(gameweek) - 1}/picks/`)
        picks = await prevPicksRes.json()
      } catch {
        picks = null
      }
    }

    // Calculate live points
    const livePoints = calculateLivePoints(picks, bootstrap, parseInt(gameweek))
    const playerBreakdown = getPlayerBreakdown(picks, bootstrap, fixtures, parseInt(gameweek))
    const teamSummary = getTeamSummary(entryInfo, entryHistory, parseInt(gameweek))
    const autoSubstitutions = calculateAutoSubstitutions(picks, bootstrap, parseInt(gameweek))

    return new Response(
      JSON.stringify({
        data: {
          entry_id: parseInt(entryId),
          gameweek: parseInt(gameweek),
          live_points: livePoints,
          player_breakdown: playerBreakdown,
          team_summary: teamSummary,
          auto_substitutions: autoSubstitutions,
          bonus_predictions: {},
          rank_projection: null,
          alerts: [],
          league_analysis: null,
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
    console.error('Error in live-gameweek function:', error)
    return new Response(
      JSON.stringify({ 
        error: 'Failed to fetch live gameweek data',
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

function calculateLivePoints(picksData: any, bootstrap: any, gameweek: number) {
  if (!picksData?.picks) {
    return { total: 0, starting_xi: 0, bench: 0, captain: 0, vice_captain: 0, bench_boost_active: false }
  }

  const elements = Object.fromEntries(bootstrap.elements.map((e: any) => [e.id, e]))
  let total = 0
  let startingXi = 0
  let bench = 0
  let captainId = null
  let viceCaptainId = null

  // Check if bench boost is active
  const chips = bootstrap.events?.find((e: any) => e.id === gameweek)?.chip_plays || []
  const benchBoostActive = chips.some((c: any) => c.chip_name === 'bboost')

  for (const pick of picksData.picks) {
    const element = elements[pick.element]
    if (!element) continue

    const points = element.event_points || 0
    const isCaptain = pick.is_captain
    const isViceCaptain = pick.is_vice_captain
    
    if (isCaptain) captainId = pick.element
    if (isViceCaptain) viceCaptainId = pick.element

    // Captain gets double points
    const multiplier = isCaptain ? 2 : 1
    const playerPoints = points * multiplier
    
    total += playerPoints
    
    if (pick.position <= 11 || benchBoostActive) {
      startingXi += playerPoints
    } else {
      bench += points  // Bench players don't get captain multiplier
    }
  }

  return {
    total,
    starting_xi: startingXi,
    bench,
    captain: captainId,
    vice_captain: viceCaptainId,
    bench_boost_active: benchBoostActive,
  }
}

function getPlayerBreakdown(picksData: any, bootstrap: any, fixtures: any, gameweek: number) {
  if (!picksData?.picks) return []

  const elements = Object.fromEntries(bootstrap.elements.map((e: any) => [e.id, e]))
  const breakdown = []

  for (const pick of picksData.picks) {
    const element = elements[pick.element]
    if (!element) continue

    breakdown.push({
      player_id: pick.element,
      player_name: `${element.first_name} ${element.second_name}`,
      position: pick.position,
      points: element.event_points || 0,
      is_captain: pick.is_captain,
      is_vice_captain: pick.is_vice_captain,
      is_starting: pick.position <= 11,
    })
  }

  return breakdown
}

function getTeamSummary(entryInfo: any, entryHistory: any, gameweek: number) {
  const current = entryHistory?.current || []
  const gwData = current.find((e: any) => e.event === gameweek)

  return {
    team_name: entryInfo.name || 'Unknown',
    manager_name: `${entryInfo.player_first_name || ''} ${entryInfo.player_last_name || ''}`.trim() || 'Unknown',
    total_points: entryInfo.summary_overall_points || 0,
    overall_rank: entryInfo.summary_overall_rank || 0,
    gameweek_points: gwData?.points || 0,
    gameweek_rank: gwData?.rank || 0,
  }
}

function calculateAutoSubstitutions(picksData: any, bootstrap: any, gameweek: number) {
  if (!picksData?.picks) return []

  const elements = Object.fromEntries(bootstrap.elements.map((e: any) => [e.id, e]))
  const autoSubs = []

  // Separate starting XI and bench
  const startingXi = picksData.picks.filter((p: any) => p.position <= 11)
  const bench = picksData.picks.filter((p: any) => p.position > 11)

  // Check each starting XI player
  for (const starter of startingXi) {
    const element = elements[starter.element]
    if (!element) continue

    const points = element.event_points || 0
    
    // Heuristic: If player has 0 points, they likely didn't play
    // Note: This is not perfect - a player could play and get 0 points
    // For more accuracy, we'd need to fetch element-summary/{id}/ which has minutes
    // but that requires many API calls. This heuristic works for most cases.
    if (points === 0) {
      const positionType = element.element_type // 1=GK, 2=DEF, 3=MID, 4=FWD
      
      // Find bench player of same position who played (has points > 0)
      for (const benchPlayer of bench) {
        const benchElement = elements[benchPlayer.element]
        if (!benchElement) continue

        const benchPoints = benchElement.event_points || 0
        const benchPositionType = benchElement.element_type

        // Match same position and bench player has points (played)
        if (benchPoints > 0 && benchPositionType === positionType) {
          autoSubs.push({
            out: {
              id: starter.element,
              name: `${element.first_name} ${element.second_name}`,
              position: starter.position
            },
            in: {
              id: benchPlayer.element,
              name: `${benchElement.first_name} ${benchElement.second_name}`,
              position: benchPlayer.position
            },
            points_gain: benchPoints
          })
          break // Only one substitution per position
        }
      }
    }
  }

  return autoSubs
}

