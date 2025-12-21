"""
Dashboard API Server
FastAPI REST endpoints for visualization dashboard data.
"""
import logging
from typing import Optional, List, Dict, Tuple, Union
from fastapi import FastAPI, HTTPException, Query, Path as PathParam, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
# BaseHTTPMiddleware removed - no longer needed
# StarletteRequest removed - no longer needed
from starlette.responses import Response
import json
from pydantic import BaseModel, ValidationError
import yaml
from pathlib import Path
from datetime import datetime

from .fpl_api import FPLAPIClient
from .database import DatabaseManager
from .api_football_client import APIFootballClient
from .visualization_dashboard import VisualizationDashboard
from .live_tracker import LiveGameweekTracker
from .optimizer import TransferOptimizer
from .optimizer_v2 import TransferOptimizerV2
from .projections import ProjectionEngine
from .eo import EOCalculator
import pandas as pd

# ML Engine imports
try:
    from .ml_engine import MLEngine
    ML_ENGINE_AVAILABLE = True
except ImportError:
    MLEngine = None
    ML_ENGINE_AVAILABLE = False

# ML Engine v5.0 import
try:
    from .ml_engine_v5 import MLEngineV5
    ML_ENGINE_V5_AVAILABLE = True
except ImportError:
    MLEngineV5 = None
    ML_ENGINE_V5_AVAILABLE = False

# Team search import
try:
    from .team_search import TeamSearch
    TEAM_SEARCH_AVAILABLE = True
except ImportError:
    TeamSearch = None
    TEAM_SEARCH_AVAILABLE = False

# Learning system import
try:
    from .main import apply_learning_system
except ImportError:
    def apply_learning_system(*args, **kwargs):
        return kwargs.get('recommendations', []) if 'recommendations' in kwargs else []

# Configure logging to write to both console and file
import os
log_file_path = r'C:\fpl-api\debug.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path, mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.info("Dashboard API logger initialized")

# Initialize FastAPI app
app = FastAPI(
    title="FPL Visualization Dashboard API",
    description="REST API for FPL analytics and visualization data",
    version="1.0.0"
)

def load_config():
    """Load configuration from config.yml"""
    config_path = Path('config.yml')
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Error loading config: {e}")
            return {}
    return {}

# Load config early for CORS setup
config = load_config()

def setup_cors(app: FastAPI, config: dict):
    """Setup CORS middleware from configuration"""
    dashboard_config = config.get('dashboard', {})
    cors_origins = dashboard_config.get('cors_origins', ["*"])
    
    # Support environment variable for production frontend URL
    import os
    production_frontend = os.getenv('FRONTEND_URL')
    if production_frontend and production_frontend not in cors_origins:
        cors_origins.append(production_frontend)
    
    # Allow Supabase Edge Functions to call FastAPI
    supabase_url = os.getenv('SUPABASE_URL')
    if supabase_url:
        edge_function_url = supabase_url.replace('https://', 'https://*.functions.supabase.co')
        if edge_function_url not in cors_origins:
            cors_origins.append(edge_function_url)
    
    # If "*" is in the list, allow all origins (for development)
    # Otherwise, use the specific origins
    if "*" in cors_origins:
        allow_origins = ["*"]
    else:
        allow_origins = cors_origins
        if not allow_origins:
            allow_origins = ["*"]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info(f"CORS configured with origins: {allow_origins}")

# Setup CORS early (before startup event)
setup_cors(app, config)

# NOTE: BlockedPlayerFilterMiddleware removed - V2 optimizer now handles filtering correctly
# and the middleware was causing Content-Length mismatch errors

# Global exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with standardized format"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": str(request.url.path)
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with user-friendly messages"""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error.get("loc", []))
        errors.append({
            "field": field,
            "message": error.get("msg"),
            "type": error.get("type")
        })
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "detail": "Invalid request parameters",
            "errors": errors,
            "path": str(request.url.path)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    import traceback
    error_traceback = traceback.format_exc()
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    # Include error details for debugging (limit traceback to 2000 chars)
    error_detail = f"An unexpected error occurred: {str(exc)}"
    error_detail += f"\nTraceback: {error_traceback[:2000]}"
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": error_detail,
            "path": str(request.url.path)
        }
    )

# Global clients (initialized on startup)
dashboard: Optional[VisualizationDashboard] = None
db_manager: Optional[DatabaseManager] = None
api_client: Optional[FPLAPIClient] = None
live_tracker: Optional[LiveGameweekTracker] = None
team_search: Optional[TeamSearch] = None

@app.on_event("startup")  # type: ignore
async def startup_event():
    """Initialize clients on startup"""
    global dashboard, db_manager, api_client, config, team_search
    try:
        config = load_config()
        
        # Initialize API client
        cache_dir = config.get('cache', {}).get('cache_dir', '.cache')
        api_client = FPLAPIClient(cache_dir=cache_dir)
        
        # Initialize database manager (optional)
        db_manager = None
        try:
            db_manager = DatabaseManager()
        except Exception as e:
            logger.warning(f"Database not available: {e}")
        
        # Initialize dashboard
        dashboard = VisualizationDashboard(
            api_client=api_client,
            db_manager=db_manager,
        )
        
        logger.info("Dashboard API initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing dashboard: {e}")
        raise


# Response models
class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


class StandardResponse(BaseModel):
    """Standard API response format"""
    data: Union[dict, list]  # Can be dict or list
    meta: Optional[dict] = None
    errors: Optional[list] = None


# ==================== AUTHENTICATION ENDPOINTS (Prepared for Future Password Auth) ====================
class AuthRequest(BaseModel):
    team_id: int
    password: Optional[str] = None

class AuthResponse(BaseModel):
    valid: bool
    message: Optional[str] = None

@app.post("/api/v1/auth/validate")
async def validate_credentials(request: AuthRequest):
    """
    Validate team ID and password credentials.
    Currently disabled - always returns success for team ID only.
    Password validation will be enabled in future update.
    """
    if not api_client:
        raise HTTPException(status_code=503, detail="FPL API client not available")
    
    try:
        # Validate team ID exists
        entry_info = api_client.get_entry_info(request.team_id)
        
        # TODO: Password validation (disabled for now)
        # When enabled, check password hash against database
        # For now, password is optional and ignored
        password_valid = True  # Always true until password feature is enabled
        
        # if request.password and db_manager:
        #     # Check password hash in database
        #     # password_valid = check_password_hash(request.team_id, request.password)
        #     pass
        
        return StandardResponse(
            data={
                "valid": True,
                "team_id": request.team_id,
                "password_required": False,  # Will be True when password feature is enabled
            },
            meta={
                "message": "Authentication successful (password validation disabled)"
            }
        )
    except Exception as e:
        logger.error(f"Error validating credentials: {e}")
        raise HTTPException(status_code=404, detail=f"Team ID {request.team_id} not found or invalid")

@app.post("/api/v1/auth/register")
async def register_credentials(request: AuthRequest):
    """
    Register password for a team ID.
    Currently disabled - placeholder for future implementation.
    """
    if not request.password:
        raise HTTPException(status_code=400, detail="Password is required for registration")
    
    # TODO: Implement password registration
    # When enabled:
    # 1. Validate team ID exists
    # 2. Hash password
    # 3. Store in database
    
    return StandardResponse(
        data={
            "registered": False,
            "message": "Password registration is not yet enabled"
        },
        meta={
            "team_id": request.team_id
        }
    )


# ==================== ENTRY INFO ENDPOINT ====================
@app.get("/api/v1/entry/{entry_id}/info")
async def get_entry_info(
    entry_id: int = PathParam(..., description="FPL entry ID"),
    password: Optional[str] = Query(None, description="Optional password for future authentication")
):
    """
    Get entry information including manager name and team name.
    Password parameter is accepted but not validated yet (prepared for future use).
    """
    if not api_client:
        raise HTTPException(status_code=503, detail="FPL API client not available")
    
    try:
        # TODO: Validate password if provided (disabled for now)
        # if password and db_manager:
        #     password_valid = check_password_hash(entry_id, password)
        #     if not password_valid:
        #         raise HTTPException(status_code=401, detail="Invalid password")
        
        entry_info = api_client.get_entry_info(entry_id)
        
        # Extract manager name
        manager_first_name = entry_info.get('player_first_name', '')
        manager_last_name = entry_info.get('player_last_name', '')
        manager_name = f"{manager_first_name} {manager_last_name}".strip() or 'Unknown'
        
        # Extract team name (from entry name)
        team_name = entry_info.get('name', 'Unknown Team')
        
        # Auto-populate fpl_teams table for search functionality
        # This ensures the database grows organically as users use the system
        if db_manager and db_manager.supabase_client:
            try:
                # Upsert team data into fpl_teams table
                db_manager.supabase_client.table('fpl_teams').upsert({
                    'team_id': entry_id,
                    'team_name': team_name,
                    'manager_name': manager_name
                }).execute()
                logger.debug(f"Auto-populated fpl_teams table for entry_id: {entry_id}")
            except Exception as e:
                # Log error but don't fail the request if upsert fails
                logger.warning(f"Failed to auto-populate fpl_teams table for entry_id {entry_id}: {e}")
        
        # Return full entry info for frontend compatibility
        return StandardResponse(
            data={
                "id": entry_id,
                "entry_id": entry_id,
                "manager_name": manager_name,
                "team_name": team_name,
                "name": team_name,  # Alias for compatibility
                "player_first_name": manager_first_name,
                "player_last_name": manager_last_name,
                "player_region_name": entry_info.get('player_region_name', ''),
                "player_region_iso_code_short": entry_info.get('player_region_iso_code_short', ''),
                "player_region_iso_code_long": entry_info.get('player_region_iso_code_long', ''),
                "summary_overall_points": entry_info.get('summary_overall_points', 0),
                "summary_overall_rank": entry_info.get('summary_overall_rank', 0),
                "summary_event_points": entry_info.get('summary_event_points', 0),
                "summary_event_rank": entry_info.get('summary_event_rank', 0),
                "current_event": entry_info.get('current_event', 1),
                "kit": entry_info.get('kit'),
            },
            meta={
                "valid": True,
                "password_required": False  # Will be True when password feature is enabled
            }
        )
    except Exception as e:
        logger.error(f"Error fetching entry info: {e}")
        raise HTTPException(status_code=404, detail=f"Entry ID {entry_id} not found or invalid")


# ==================== TEAM SEARCH ENDPOINT ====================
@app.get("/api/v1/search/teams")
async def search_teams(
    q: str = Query(..., description="Search query (team name or manager name)"),
    limit: int = Query(20, description="Maximum number of results to return")
):
    """
    Search FPL teams by team name or manager name.
    Searches the CSV file stored on the server.
    """
    if not team_search:
        raise HTTPException(
            status_code=503, 
            detail="Team search is not available. The CSV file may not be loaded on the server."
        )
    
    if not q or not q.strip():
        return StandardResponse(
            data={"matches": []},
            meta={"query": q, "count": 0}
        )
    
    try:
        results = team_search.search(q.strip(), limit=limit)
        
        return StandardResponse(
            data={"matches": results},
            meta={
                "query": q,
                "count": len(results),
                "limit": limit
            }
        )
    except Exception as e:
        logger.error(f"Error searching teams: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to search teams: {str(e)}")


# ==================== MINI-LEAGUE ENDPOINTS ====================
@app.get("/api/v1/entry/{entry_id}/leagues")
async def get_user_leagues(
    entry_id: int = PathParam(..., description="FPL entry ID")
):
    """
    Get list of mini-leagues the manager is in.
    """
    if not api_client:
        raise HTTPException(status_code=503, detail="FPL API client not available")
    
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        
        # Initialize tracker and get leagues
        tracker = LiveGameweekTracker(api_client, entry_id)
        leagues = await loop.run_in_executor(None, tracker.get_user_leagues)
        
        return StandardResponse(
            data=leagues,
            meta={
                "entry_id": entry_id,
                "total_leagues": len(leagues) if leagues else 0
            }
        )
    except Exception as e:
        logger.error(f"Error fetching user leagues: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch leagues: {str(e)}")


@app.get("/api/v1/entry/{entry_id}/league/{league_id}/standings")
async def get_league_standings(
    entry_id: int = PathParam(..., description="FPL entry ID"),
    league_id: int = PathParam(..., description="Mini-league ID")
):
    """
    Get standings table for a specific mini-league.
    """
    if not api_client:
        raise HTTPException(status_code=503, detail="FPL API client not available")
    
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        
        # Initialize tracker and get league standings
        tracker = LiveGameweekTracker(api_client, entry_id)
        table, league_name = await loop.run_in_executor(None, tracker.get_mini_league_table, league_id)
        
        return StandardResponse(
            data={
                "league_id": league_id,
                "league_name": league_name,
                "standings": table
            },
            meta={
                "entry_id": entry_id,
                "total_teams": len(table) if table else 0
            }
        )
    except Exception as e:
        logger.error(f"Error fetching league standings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch league standings: {str(e)}")


# ==================== UTILITY ENDPOINTS ====================
@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "dashboard": {
                "status": "healthy",
                "initialized": dashboard is not None
            },
            "database": {
                "status": "healthy" if db_manager else "unavailable",
                "available": db_manager is not None
            },
            "storage": {
                "status": "healthy",
                "available": True
            },
            "fpl_api": {
                "status": "healthy" if api_client else "unavailable",
                "available": api_client is not None
            }
        }
    }


@app.get("/")
async def root():
    """API information endpoint"""
    return {
        "name": "FPL Visualization Dashboard API",
        "version": "1.0.0",
        "description": "REST API for FPL analytics and visualization data",
        "endpoints": {
            "health": "/api/v1/health",
            "entry_info": "/api/v1/entry/{entry_id}/info",
            "live_gameweek": "/api/v1/live/gameweek/{gameweek}",
            "recommendations": "/api/v1/recommendations/transfers"
        }
    }


# ==================== LIVE GAMEWEEK TRACKING ENDPOINTS ====================
@app.get("/api/v1/live/gameweek/{gameweek}")
async def get_live_gameweek(
    gameweek: int = PathParam(..., description="Gameweek number"),
    entry_id: int = Query(..., description="FPL entry ID"),
    league_id: Optional[int] = Query(None, description="Optional mini-league ID for rank projections")
):
    """Get comprehensive live gameweek tracking data"""
    if not api_client:
        raise HTTPException(status_code=503, detail="FPL API client not available")
    
    try:
        # Initialize tracker for this entry
        tracker = LiveGameweekTracker(api_client, entry_id)
        
        # PERFORMANCE OPTIMIZATION: Load shared data once and pass to methods
        # This avoids redundant API calls (bootstrap, entry_info, entry_history called multiple times)
        # Use asyncio to run blocking calls in executor (prevents blocking event loop)
        import asyncio
        
        # Run blocking API calls in thread pool to avoid blocking the async event loop
        # Enable caching for all calls to speed up subsequent requests
        loop = asyncio.get_event_loop()
        bootstrap, entry_info, entry_history, picks_data, fixtures = await asyncio.gather(
            loop.run_in_executor(None, api_client.get_bootstrap_static, True),  # Enable cache
            loop.run_in_executor(None, api_client.get_entry_info, entry_id, True),  # Enable cache
            loop.run_in_executor(None, api_client.get_entry_history, entry_id, True),  # Enable cache
            loop.run_in_executor(None, api_client.get_entry_picks, entry_id, gameweek, True),  # Enable cache
            loop.run_in_executor(None, api_client.get_fixtures, True),  # Enable cache
            return_exceptions=False
        )
        
        # If picks not available for current GW, try previous GW
        # Also update gameweek if we fall back to previous GW
        original_gameweek = gameweek
        actual_gameweek = gameweek  # Track which gameweek we're actually using for data
        if not picks_data or 'picks' not in picks_data:
            try:
                picks_data = await loop.run_in_executor(None, api_client.get_entry_picks, entry_id, gameweek - 1, True)
                if picks_data and 'picks' in picks_data:
                    # Update gameweek to the one that has picks data
                    actual_gameweek = gameweek - 1
                    logger.info(f"Live tracking: No picks for GW{original_gameweek}, using GW{actual_gameweek} instead")
            except:
                picks_data = None
        
        # Get all available data - pass shared data to avoid redundant calls
        # Use actual_gameweek for live_points and player_breakdown (the GW we have picks for)
        # But try to get team_summary for the original gameweek first (for current ranks)
        # If that doesn't have rank data, fall back to actual_gameweek
        player_breakdown = tracker.get_player_breakdown(actual_gameweek, bootstrap=bootstrap, picks_data=picks_data, fixtures=fixtures)
        
        # Calculate live_points from player_breakdown (which has correct current GW points)
        # This ensures totals match the individual player points shown
        total_points = 0
        starting_xi_points = 0
        bench_points = 0
        captain_points = 0
        vice_captain_points = 0
        
        # Get chip information for multipliers
        chips_used = entry_history.get('chips', [])
        bench_boost_active = any(
            chip.get('event') == actual_gameweek and chip.get('name') == 'bboost' 
            for chip in chips_used
        )
        triple_captain_active = any(
            chip.get('event') == actual_gameweek and chip.get('name') == '3xc' 
            for chip in chips_used
        )
        
        logger.info(f"Live tracking: Calculating totals from {len(player_breakdown)} players, triple_captain_active={triple_captain_active}, bench_boost_active={bench_boost_active}")
        
        for player in player_breakdown:
            # The 'points' field in player_breakdown already has the correct current GW points
            # and has 2x multiplier applied for captains (see get_player_breakdown line 1151)
            player_points = player.get('points', 0)
            is_captain = player.get('is_captain', False)
            is_vice = player.get('is_vice_captain', False) or player.get('is_vice', False)
            is_starting = player.get('position', 0) <= 11
            
            # Calculate base_points and final points with correct multiplier
            if is_captain:
                # Points already has 2x multiplier, so get base by dividing by 2
                base_points = player_points / 2.0
                # Apply correct multiplier (3x for triple captain, 2x for normal)
                captain_multiplier = 3 if triple_captain_active else 2
                points = base_points * captain_multiplier
                captain_points = points
                logger.debug(f"Live tracking: Captain {player.get('name')} - base={base_points}, multiplier={captain_multiplier}, final={points}")
            elif is_vice:
                # Vice captain doesn't get multiplier
                base_points = player_points
                points = base_points
                vice_captain_points = points
            else:
                # Regular player, no multiplier
                base_points = player_points
                points = base_points
            
            if is_starting:
                starting_xi_points += points
                total_points += points
            else:
                bench_points += base_points
                # Include bench points in total only if Bench Boost is active
                if bench_boost_active:
                    total_points += base_points
        
        logger.info(f"Live tracking: Calculated totals - total={total_points}, starting_xi={starting_xi_points}, bench={bench_points}, captain={captain_points}")
        
        # Build live_points dict from calculated values
        live_points = {
            'total': total_points,
            'starting_xi': starting_xi_points,
            'bench': bench_points,
            'captain': captain_points,
            'vice_captain': vice_captain_points,
            'bench_boost_active': bench_boost_active,
            'triple_captain_active': triple_captain_active,
        }
        
        # Try to get team_summary for original gameweek first (for current ranks)
        team_summary = tracker.get_team_summary(original_gameweek, league_id=league_id, entry_info=entry_info, entry_history=entry_history)
        # If gameweek rank is 0 or missing, try actual_gameweek (the one we have picks for)
        if (team_summary.get('gw_rank', 0) == 0 or team_summary.get('gw_rank') is None) and actual_gameweek != original_gameweek:
            logger.info(f"Live tracking: GW{original_gameweek} has no rank data, trying GW{actual_gameweek} for team_summary")
            actual_team_summary = tracker.get_team_summary(actual_gameweek, league_id=league_id, entry_info=entry_info, entry_history=entry_history)
            # Merge ranks from actual_gameweek if they exist
            if actual_team_summary.get('gw_rank', 0) > 0:
                team_summary['gw_rank'] = actual_team_summary.get('gw_rank')
            # Keep overall_rank from original (it's the same regardless of gameweek)
            if team_summary.get('live_rank', 0) == 0 and actual_team_summary.get('live_rank', 0) > 0:
                team_summary['live_rank'] = actual_team_summary.get('live_rank')
        
        # These methods need element-summary calls - make them optional/fast
        # Skip auto_substitutions and alerts for now (they require many element-summary calls)
        # They can be enabled later with batching
        auto_substitutions = []  # tracker.calculate_auto_substitutions(gameweek, bootstrap, picks_data)
        bonus_predictions = {}  # tracker.predict_bonus_points(gameweek, bootstrap, picks_data)  # Skip for now - too many API calls
        alerts = []  # tracker.check_alerts(gameweek, bootstrap, picks_data)  # Skip for now - too many API calls
        
        # Get rank projection (use mini-league if provided)
        rank_projection = None
        league_analysis = None
        if league_id:
            # Get mini-league analysis for accurate rank projection
            user_gw_points = live_points.get('total', 0)
            league_analysis = await loop.run_in_executor(None, lambda: tracker.analyze_mini_league_competitors(league_id, gameweek, user_gw_points, entry_info))
            rank_projection = await loop.run_in_executor(None, lambda: tracker.project_rank_change(gameweek, live_points.get('total', 0), league_id, league_analysis, entry_info, entry_history))
        else:
            rank_projection = await loop.run_in_executor(None, lambda: tracker.project_rank_change(gameweek, live_points.get('total', 0), None, None, entry_info, entry_history))
        
        # Extract total points (handle different response formats)
        total_points = live_points.get('total', 0)
        if total_points == 0:
            # Try alternative keys
            total_points = live_points.get('total_points', 0)
            if total_points == 0:
                # Calculate from starting_xi and bench
                total_points = live_points.get('starting_xi', 0) + live_points.get('bench', 0)
        
        # Ensure player_breakdown is a list
        if not isinstance(player_breakdown, list):
            player_breakdown = []
        
        return StandardResponse(
            data={
                "entry_id": entry_id,
                "gameweek": gameweek,
                "live_points": {
                    "total": total_points,
                    "starting_xi": live_points.get('starting_xi', 0),
                    "bench": live_points.get('bench', 0),
                    "captain": live_points.get('captain', 0),
                    "vice_captain": live_points.get('vice_captain', 0),
                    "bench_boost_active": live_points.get('bench_boost_active', False),
                    "triple_captain_active": live_points.get('triple_captain_active', False),
                },
                "player_breakdown": player_breakdown,
                "team_summary": team_summary,
                "auto_substitutions": auto_substitutions,
                "bonus_predictions": bonus_predictions,
                "rank_projection": rank_projection,
                "alerts": alerts,
                "league_analysis": league_analysis,
            },
            meta={
                "last_update": datetime.now().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Error fetching live gameweek data: {e}", exc_info=True)
        # Return empty data instead of 500 error for better UX
        return StandardResponse(
            data={
                "entry_id": entry_id,
                "gameweek": gameweek,
                "live_points": {
                    "total": 0,
                    "starting_xi": 0,
                    "bench": 0,
                    "captain": 0,
                    "vice_captain": 0,
                    "bench_boost_active": False,
                    "triple_captain_active": False,
                },
                "player_breakdown": [],
                "team_summary": {},
                "auto_substitutions": [],
                "bonus_predictions": {},
                "rank_projection": {},
                "alerts": [],
                "league_analysis": None,
            },
            meta={
                "last_update": datetime.now().isoformat(),
                "error": str(e)
            }
        )


# ==================== GAMEWEEK UTILITY ENDPOINTS ====================
@app.get("/api/v1/gameweek/current")
async def get_current_gameweek():
    """Get current/latest gameweek number"""
    if not api_client:
        raise HTTPException(status_code=503, detail="FPL API client not available")
    
    try:
        bootstrap = api_client.get_bootstrap_static(use_cache=False)
        events = bootstrap.get('events', [])
        
        if not events:
            return StandardResponse(
                data={"gameweek": 1, "is_current": False, "is_finished": False, "is_next": False, "deadline_time": None},
                meta={"event_name": ""}
            )
        
        # For live tracking, we want the gameweek that is currently in session (being played)
        # Priority 1: Find the latest gameweek that has started (deadline passed) but not finished
        # This is the gameweek currently in session
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        current_event = None
        
        # PRIORITY 1: Find the latest gameweek that has started (deadline passed) but not finished
        # This is more reliable than is_current flag which can be stale during transitions
        # Sort events by ID descending to check latest first
        for event in sorted(events, key=lambda x: x.get('id', 0), reverse=True):
            deadline_str = event.get('deadline_time')
            if deadline_str:
                try:
                    # Parse deadline (FPL API uses ISO format with timezone)
                    deadline = datetime.fromisoformat(deadline_str.replace('Z', '+00:00'))
                    # If deadline has passed but gameweek is not finished, it's in session
                    if deadline < now and not event.get('finished', False):
                        current_event = event
                        logger.info(f"get_current_gameweek: Found gameweek in session: GW{current_event.get('id')} (deadline passed, not finished)")
                        break
                except Exception as e:
                    logger.debug(f"Error parsing deadline for event {event.get('id')}: {e}")
                    pass
        
        # PRIORITY 2: If no deadline-based match, check is_current flag (fallback)
        if not current_event:
            current_event = next((e for e in events if e.get('is_current', False)), None)
            if current_event:
                logger.info(f"get_current_gameweek: Using is_current flag: GW{current_event.get('id')}")
        
        # Priority 3: If still no current, find latest finished gameweek (most recent completed)
        # This is the fallback - use the latest finished gameweek instead of is_next
        if not current_event:
            finished_events = [e for e in events if e.get('finished', False)]
            if finished_events:
                current_event = max(finished_events, key=lambda x: x.get('id', 0))
        
        # Priority 4: Final fallback: latest event by ID (highest gameweek number)
        if not current_event and events:
            current_event = max(events, key=lambda x: x.get('id', 0))
        
        # Use current_event (gameweek in session or latest finished)
        event = current_event
        gameweek = event.get('id', 1) if event else 1
        
        return StandardResponse(
            data={
                "gameweek": gameweek,
                "is_current": event.get('is_current', False) if event else False,
                "is_finished": event.get('finished', False) if event else False,
                "is_next": event.get('is_next', False) if event else False,
                "deadline_time": event.get('deadline_time') if event else None,
            },
            meta={
                "event_name": event.get('name', '') if event else ''
            }
        )
    except Exception as e:
        logger.error(f"Error fetching current gameweek: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== DASHBOARD ENDPOINTS (Placeholders) ====================
# These endpoints return 404 until full implementation is restored
# For now, returning basic responses to prevent frontend errors

@app.get("/api/v1/dashboard/team/rank-progression")
async def get_rank_progression(
    entry_id: int = Query(..., description="FPL entry ID"),
    season: Optional[int] = Query(None, description="Season year")
):
    """Get rank progression data"""
    if not dashboard:
        raise HTTPException(status_code=503, detail="Dashboard not initialized")
    
    try:
        data = dashboard.get_rank_progression(entry_id, season)
        return StandardResponse(data=data, meta={"entry_id": entry_id, "season": season})
    except Exception as e:
        logger.error(f"Error in rank progression endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/dashboard/team/captain-performance")
async def get_captain_performance(
    entry_id: int = Query(..., description="FPL entry ID"),
    season: Optional[int] = Query(None, description="Season year")
):
    """Get captain performance data"""
    if not dashboard:
        raise HTTPException(status_code=503, detail="Dashboard not initialized")
    try:
        data = dashboard.get_captain_performance(entry_id, season)
        return StandardResponse(data=data, meta={"entry_id": entry_id, "season": season})
    except Exception as e:
        logger.error(f"Error in captain performance endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/dashboard/team/transfer-analysis")
async def get_transfer_analysis(
    entry_id: int = Query(..., description="FPL entry ID"),
    season: Optional[int] = Query(None, description="Season year")
):
    """Get transfer analysis data"""
    if not dashboard:
        raise HTTPException(status_code=503, detail="Dashboard not initialized")
    try:
        data = dashboard.get_transfer_analysis(entry_id, season)
        return StandardResponse(data=data, meta={"entry_id": entry_id, "season": season})
    except Exception as e:
        logger.error(f"Error in transfer analysis endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/dashboard/ownership-correlation")
async def get_ownership_correlation(
    season: Optional[int] = Query(None, description="Season year"),
    gameweek: Optional[int] = Query(None, description="Gameweek number (default: current)")
):
    """Get ownership vs points correlation data"""
    if not dashboard:
        raise HTTPException(status_code=503, detail="Dashboard not initialized")
    try:
        data = dashboard.get_ownership_points_correlation(season, gameweek)
        return StandardResponse(data=data, meta={"season": season, "gameweek": gameweek})
    except Exception as e:
        logger.error(f"Error in ownership correlation endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== RECOMMENDATIONS ENDPOINTS ====================
@app.get("/api/v1/recommendations/transfers")
async def get_transfer_recommendations(
    entry_id: int = Query(..., description="FPL entry ID"),
    gameweek: Optional[int] = Query(None, description="Target gameweek (default: current)"),
    max_transfers: int = Query(4, description="Maximum transfers to consider"),
    forced_out_ids: Optional[str] = Query(None, description="Comma-separated player IDs that must be removed"),
    model_version: str = Query("v4.6", description="ML model version to use")
):
    """Get ML-powered transfer recommendations for a specific user"""
    if not api_client or not db_manager:
        raise HTTPException(status_code=503, detail="API client or database not available")
    
    try:
        import asyncio
        
        # Validate entry_id exists
        loop = asyncio.get_event_loop()
        entry_info = await loop.run_in_executor(None, api_client.get_entry_info, entry_id, True)
        
        # Get current gameweek if not specified
        if gameweek is None:
            bootstrap = await loop.run_in_executor(None, api_client.get_bootstrap_static, True)
            gameweek = api_client.get_current_gameweek()
        
        # Load user's current squad
        picks_data = await loop.run_in_executor(None, api_client.get_entry_picks, entry_id, gameweek, True)
        if not picks_data or 'picks' not in picks_data:
            # Try previous gameweek
            try:
                picks_data = await loop.run_in_executor(None, api_client.get_entry_picks, entry_id, gameweek - 1, True)
            except:
                raise HTTPException(status_code=404, detail=f"Could not fetch squad for entry {entry_id}")
        
        bootstrap = await loop.run_in_executor(None, api_client.get_bootstrap_static, True)
        
        # Load all players with projections
        # Get bootstrap data and build players DataFrame (must be done before building current_squad)
        players_df = pd.DataFrame(bootstrap['elements'])
        teams_df = pd.DataFrame(bootstrap['teams'])
        team_map = {t['id']: t['name'] for t in teams_df.to_dict('records')}
        players_df['team_name'] = players_df['team'].map(team_map)
        
        # Build current squad DataFrame
        current_squad = []
        for pick in picks_data['picks']:
            player_data = players_df[players_df['id'] == pick['element']].iloc[0].to_dict()
            player_data['position'] = pick['position']
            player_data['is_captain'] = pick.get('is_captain', False)
            player_data['is_vice_captain'] = pick.get('is_vice_captain', False)
            current_squad.append(player_data)
        
        current_squad_df = pd.DataFrame(current_squad)
        current_squad_df['team_name'] = current_squad_df['team'].map(team_map)
        
        # Get bank value
        entry_history = await loop.run_in_executor(None, api_client.get_entry_history, entry_id, True)
        bank = entry_history.get('current', [{}])[-1].get('bank', 0) / 10.0  # Convert to millions
        
        # Generate projections
        projection_engine = ProjectionEngine(config)
        players_df = await loop.run_in_executor(None, projection_engine.calculate_projections, players_df)
        
        # Apply ML predictions
        if ML_ENGINE_AVAILABLE:
            players_df = train_and_predict_ml(db_manager, players_df, config, model_version)
        else:
            # Fallback to basic projections
            if 'EV' not in players_df.columns:
                players_df['EV'] = players_df.get('ep_next', 0)
        
        # Ensure 'EV' column exists in players_df
        if 'EV' not in players_df.columns:
            players_df['EV'] = players_df.get('ep_next', 0)
            if players_df['EV'].isna().any():
                players_df['EV'] = players_df['EV'].fillna(0)
        
        # Merge EV and other calculated columns from players_df into current_squad_df
        # This ensures current_squad_df has all the ML-enhanced data
        ev_columns = ['EV', 'predicted_ev', 'xP_raw', 'xP_adjusted', 'ep_next']
        merge_columns = ['id'] + [col for col in ev_columns if col in players_df.columns]
        
        if merge_columns:
            current_squad_df = current_squad_df.merge(
                players_df[merge_columns],
                on='id',
                how='left',
                suffixes=('', '_new')
            )
            # If EV column doesn't exist after merge, create it from ep_next or set to 0
            if 'EV' not in current_squad_df.columns:
                current_squad_df['EV'] = current_squad_df.get('ep_next', 0)
                if current_squad_df['EV'].isna().any():
                    current_squad_df['EV'] = current_squad_df['EV'].fillna(0)
        else:
            # Fallback if no merge columns, ensure EV exists
            if 'EV' not in current_squad_df.columns:
                current_squad_df['EV'] = current_squad_df.get('ep_next', 0)
                if current_squad_df['EV'].isna().any():
                    current_squad_df['EV'] = current_squad_df['EV'].fillna(0)
        
        # Identify forced transfers
        forced_ids = set()
        if forced_out_ids:
            forced_ids = {int(id.strip()) for id in forced_out_ids.split(',')}
        
        # Filter forced players
        forced_mask = current_squad_df['id'].isin(forced_ids) if forced_ids else pd.Series([False] * len(current_squad_df))
        forced_mask = forced_mask | (current_squad_df.get('status', '').isin(['i', 's', 'u']))
        
        # Generate recommendations
        optimizer = TransferOptimizer(config)
        current_squad_ids = set(current_squad_df['id'])
        available_players = players_df[~players_df['id'].isin(current_squad_ids)].copy()
        
        # Calculate free transfers
        free_transfers = 1  # Default
        try:
            current_event = next((e for e in entry_history.get('current', []) if e.get('event') == gameweek - 1), None)
            if current_event:
                free_transfers = current_event.get('event_transfers', 0) + 1
                free_transfers = min(free_transfers, 2)  # Cap at 2
        except:
            pass
        
        recommendations = optimizer.generate_smart_recommendations(
            current_squad_df, available_players, bank, free_transfers, max_transfers=max_transfers
        )
        
        logger.info(f"Generated {len(recommendations.get('recommendations', []))} raw recommendations")
        
        # Apply learning system if available
        # Check for v5.0
        if model_version == "v5.0" and ML_ENGINE_V5_AVAILABLE and MLEngineV5:
            ml_engine_instance = MLEngineV5(db_manager, model_version=model_version)
            if ml_engine_instance.load_model():
                ml_engine_instance.is_trained = True
                recommendations['recommendations'] = apply_learning_system(
                    db_manager, api_client, entry_id, gameweek,
                    recommendations['recommendations'], ml_engine_instance
                )
                logger.info(f"After learning system (v5.0): {len(recommendations.get('recommendations', []))} recommendations")
        elif ML_ENGINE_AVAILABLE and MLEngine:
            ml_engine_instance = MLEngine(db_manager, model_version=model_version)
            if ml_engine_instance.load_model():
                ml_engine_instance.is_trained = True
                recommendations['recommendations'] = apply_learning_system(
                    db_manager, api_client, entry_id, gameweek,
                    recommendations['recommendations'], ml_engine_instance
                )
                logger.info(f"After learning system: {len(recommendations.get('recommendations', []))} recommendations")
        
        # Transform recommendations to frontend format
        # Frontend expects: [{ element_out: Player, element_in: Player, score: number, reasoning: string }]
        # Backend returns: [{ players_out: [...], players_in: [...], net_ev_gain: number, ... }]
        transformed_recommendations = []
        raw_recs = recommendations.get('recommendations', [])
        logger.info(f"Transforming {len(raw_recs)} recommendations to frontend format")
        
        for rec in raw_recs:
            players_out = rec.get('players_out', [])
            players_in = rec.get('players_in', [])
            
            # Create individual transfer pairs (1-to-1 mapping)
            # If multiple transfers, create pairs in order
            num_transfers = min(len(players_out), len(players_in))
            
            for i in range(num_transfers):
                player_out_info = players_out[i]
                player_in_info = players_in[i]
                
                # Get full player data from DataFrames
                player_out_id = player_out_info.get('id')
                player_in_id = player_in_info.get('id')
                
                # Find full player data
                player_out_df = current_squad_df[current_squad_df['id'] == player_out_id]
                player_in_df = players_df[players_df['id'] == player_in_id]
                
                if player_out_df.empty or player_in_df.empty:
                    continue
                
                player_out = player_out_df.iloc[0].to_dict()
                player_in = player_in_df.iloc[0].to_dict()
                
                # Build frontend-compatible recommendation
                transformed_rec = {
                    'element_out': {
                        'id': player_out.get('id'),
                        'web_name': player_out.get('web_name', player_out_info.get('name', 'Unknown')),
                        'team_code': player_out.get('team', 0),
                        'element_type': player_out.get('element_type', 0),
                        'now_cost': player_out.get('now_cost', 0),
                        'selected_by_percent': str(player_out.get('selected_by_percent', 0)),
                        'form': str(player_out.get('form', 0)),
                        'total_points': player_out.get('total_points', 0),
                    },
                    'element_in': {
                        'id': player_in.get('id'),
                        'web_name': player_in.get('web_name', player_in_info.get('name', 'Unknown')),
                        'team_code': player_in.get('team', 0),
                        'element_type': player_in.get('element_type', 0),
                        'now_cost': player_in.get('now_cost', 0),
                        'selected_by_percent': str(player_in.get('selected_by_percent', 0)),
                        'form': str(player_in.get('form', 0)),
                        'total_points': player_in.get('total_points', 0),
                    },
                    'score': rec.get('net_ev_gain_adjusted', rec.get('net_ev_gain', 0)),
                    'reasoning': rec.get('description', f"{rec.get('strategy', 'Transfer')} - Expected gain: {rec.get('net_ev_gain_adjusted', 0):.2f} points")
                }
                
                # Add more context to reasoning if multiple transfers
                if num_transfers > 1:
                    transformed_rec['reasoning'] = f"Part of {num_transfers}-transfer strategy: {rec.get('description', 'Optimization')} - Net gain: {rec.get('net_ev_gain_adjusted', 0):.2f} points"
                
                transformed_recommendations.append(transformed_rec)
        
        logger.info(f"Transformed to {len(transformed_recommendations)} frontend-compatible recommendations")
        
        return StandardResponse(
            data={
                "entry_id": entry_id,
                "gameweek": gameweek,
                "recommendations": transformed_recommendations,
                "forced_transfers": recommendations.get('num_forced_transfers', 0),
                "forced_players": recommendations.get('forced_players', []),
                "free_transfers": free_transfers,
                "bank": bank,
            },
            meta={
                "model_version": model_version,
                "generated_at": datetime.now().isoformat()
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate recommendations: {str(e)}")


# ==================== ML PREDICTIONS ENDPOINTS ====================
@app.get("/api/v1/ml/predictions")
async def get_ml_predictions(
    gameweek: int = Query(999, description="Gameweek number (999 = latest)"),
    entry_id: Optional[int] = Query(None, description="Optional: Filter predictions for user's squad"),
    model_version: str = Query("v4.6", description="ML model version")
):
    """Get ML predictions from database"""
    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        predictions_df = db_manager.get_predictions_for_gw(gameweek, model_version)
        
        # If entry_id provided, filter to user's squad
        if entry_id and not predictions_df.empty:
            import asyncio
            loop = asyncio.get_event_loop()
            picks_data = await loop.run_in_executor(None, api_client.get_entry_picks, entry_id, gameweek, True)
            if picks_data and 'picks' in picks_data:
                squad_ids = {p['element'] for p in picks_data['picks']}
                predictions_df = predictions_df[predictions_df['player_id'].isin(squad_ids)]
        
        return StandardResponse(
            data={
                "predictions": predictions_df.to_dict('records') if not predictions_df.empty else [],
                "gameweek": gameweek,
                "model_version": model_version,
                "count": len(predictions_df)
            },
            meta={
                "generated_at": datetime.now().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Error fetching predictions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch predictions: {str(e)}")


@app.post("/api/v1/ml/predictions/generate")
async def generate_ml_predictions(
    gameweek: int = Query(999, description="Gameweek to generate predictions for"),
    model_version: str = Query("v4.6", description="ML model version to use")
):
    """Trigger ML model training and prediction generation"""
    if not db_manager or not ML_ENGINE_AVAILABLE:
        raise HTTPException(status_code=503, detail="ML Engine not available")
    
    try:
        from projections import ProjectionEngine
        from main import train_and_predict_ml
        import asyncio
        
        loop = asyncio.get_event_loop()
        
        # Load players and generate projections
        bootstrap = await loop.run_in_executor(None, api_client.get_bootstrap_static, True)
        players_df = pd.DataFrame(bootstrap['elements'])
        
        # Generate projections
        projection_engine = ProjectionEngine(config)
        players_df = await loop.run_in_executor(None, projection_engine.calculate_projections, players_df)
        
        # Train and predict
        players_df = train_and_predict_ml(db_manager, players_df, config, model_version)
        
        if 'predicted_ev' in players_df.columns:
            # Save predictions to database
            predictions = players_df[['id', 'predicted_ev']].copy()
            predictions.columns = ['player_id', 'predicted_ev']
            predictions['gw'] = gameweek
            predictions['model_version'] = model_version
            predictions['confidence_score'] = 0.7  # Default confidence
            
            db_manager.save_predictions(predictions.to_dict('records'))
            
            # Record predictions for validation tracking
            try:
                from validation_tracker import ValidationTracker
                tracker = ValidationTracker(db_manager, api_client)
                
                # Get player names from bootstrap
                bootstrap = await loop.run_in_executor(None, api_client.get_bootstrap_static, True)
                players_dict = {p['id']: p.get('web_name', f"Player_{p['id']}") 
                               for p in bootstrap.get('elements', [])}
                
                # Record each prediction
                for _, row in predictions.iterrows():
                    player_id = int(row['player_id'])
                    predicted_ev = float(row['predicted_ev'])
                    predicted_points_per_90 = predicted_ev * 1.5  # Rough estimate
                    
                    tracker.record_prediction(
                        player_id=player_id,
                        gw=gameweek,
                        predicted_ev=predicted_ev,
                        predicted_points_per_90=predicted_points_per_90,
                        model_version=model_version,
                        player_name=players_dict.get(player_id)
                    )
            except Exception as e:
                logger.warning(f"Could not record predictions for validation: {e}")
            
            return StandardResponse(
                data={
                    "status": "success",
                    "gameweek": gameweek,
                    "model_version": model_version,
                    "predictions_generated": len(predictions)
                },
                meta={
                    "generated_at": datetime.now().isoformat()
                }
            )
        else:
            raise HTTPException(status_code=500, detail="ML predictions failed to generate")
            
    except Exception as e:
        logger.error(f"Error generating ML predictions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate predictions: {str(e)}")

@app.get("/api/v1/ml/validation/summary")
async def get_validation_summary(
    model_version: str = Query("v5.0", description="Model version"),
    min_gw: Optional[int] = Query(None, description="Minimum gameweek"),
    max_gw: Optional[int] = Query(None, description="Maximum gameweek")
):
    """Get validation summary for ML model predictions"""
    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        from validation_tracker import ValidationTracker
        tracker = ValidationTracker(db_manager, api_client)
        
        summary = tracker.get_validation_summary(
            model_version=model_version,
            min_gw=min_gw,
            max_gw=max_gw
        )
        
        if 'error' in summary:
            raise HTTPException(status_code=404, detail=summary['error'])
        
        return StandardResponse(
            data=summary,
            meta={
                "generated_at": datetime.now().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Error getting validation summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get validation summary: {str(e)}")

@app.get("/api/v1/ml/validation/validate")
async def validate_gameweek(
    gw: int = Query(..., description="Gameweek to validate"),
    model_version: str = Query("v5.0", description="Model version")
):
    """Validate predictions for a specific gameweek"""
    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        from validation_tracker import ValidationTracker
        tracker = ValidationTracker(db_manager, api_client)
        
        result = tracker.validate_predictions_for_gw(gw, model_version)
        
        if 'error' in result:
            raise HTTPException(status_code=404, detail=result['error'])
        
        return StandardResponse(
            data=result,
            meta={
                "validated_at": datetime.now().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Error validating gameweek: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to validate gameweek: {str(e)}")

@app.get("/api/v1/ml/players")
async def get_ml_enhanced_players(
    gameweek: Optional[int] = Query(None, description="Target gameweek (default: current)"),
    entry_id: Optional[int] = Query(None, description="FPL entry ID (required for team-specific ML output)"),
    model_version: str = Query("v4.6", description="ML model version"),
    limit: int = Query(500, description="Maximum number of players to return")
):
    """Get full ML-enhanced player data (same as main.py output) for a specific team"""
    if not api_client or not db_manager:
        raise HTTPException(status_code=503, detail="API client or database not available")
    
    if not entry_id:
        raise HTTPException(status_code=400, detail="entry_id is required")
    
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        
        # Get current gameweek if not specified
        if gameweek is None:
            bootstrap = await loop.run_in_executor(None, api_client.get_bootstrap_static, True)
            gameweek = api_client.get_current_gameweek()
        
        # Load all players with bootstrap data
        bootstrap = await loop.run_in_executor(None, api_client.get_bootstrap_static, True)
        players_df = pd.DataFrame(bootstrap['elements'])
        teams_df = pd.DataFrame(bootstrap['teams'])
        team_map = {t['id']: t['name'] for t in teams_df.to_dict('records')}
        players_df['team_name'] = players_df['team'].map(team_map)
        
        # Get user's entry info and squad (like main.py does)
        entry_info = await loop.run_in_executor(None, api_client.get_entry_info, entry_id, True)
        entry_history = await loop.run_in_executor(None, api_client.get_entry_history, entry_id, True)
        
        # Get current squad IDs for optimization (like main.py)
        try:
            optimizer = TransferOptimizer(config)
            current_squad = await loop.run_in_executor(None, optimizer.get_current_squad, entry_id, gameweek, api_client, players_df)
            current_squad_ids = set(current_squad['id'].tolist()) if not current_squad.empty else set()
            current_squad_teams = set(current_squad['team'].dropna().unique()) if not current_squad.empty else set()
        except:
            current_squad_ids = set()
            current_squad_teams = set()
        
        # Get fixtures for fixture difficulty analysis
        all_fixtures = await loop.run_in_executor(None, api_client.get_fixtures, True)
        fixtures_for_gw = [f for f in all_fixtures if f.get('event') == gameweek]
        
        # Identify top transfer targets (top 200) to limit processing (like main.py)
        top_players = players_df.nlargest(200, ['now_cost', 'total_points'], keep='all')
        relevant_team_ids = current_squad_teams | set(top_players['team'].dropna().unique())
        relevant_player_ids = current_squad_ids | set(top_players['id'].head(100).tolist())
        
        # Add fixture difficulty (optimized for relevant teams, like main.py)
        try:
            from main import add_fixture_difficulty
            players_df = await loop.run_in_executor(
                None, 
                lambda: add_fixture_difficulty(players_df, api_client, gameweek, db_manager, relevant_team_ids, all_fixtures=all_fixtures, bootstrap_data=bootstrap)
            )
        except:
            logger.warning("Could not add fixture difficulty analysis")
        
        # Add statistical analysis (optimized for relevant players, like main.py)
        try:
            from main import add_statistical_analysis
            history_df = None
            if db_manager:
                history_df = db_manager.get_current_season_history()
            players_df = await loop.run_in_executor(
                None,
                lambda: add_statistical_analysis(players_df, api_client, gameweek, db_manager, relevant_player_ids, fixtures=fixtures_for_gw, bootstrap_data=bootstrap, history_df=history_df)
            )
        except Exception as e:
            logger.warning(f"Could not add statistical analysis: {e}")
        
        # Generate projections
        projection_engine = ProjectionEngine(config)
        players_df = await loop.run_in_executor(None, projection_engine.calculate_projections, players_df)
        
        # Apply ML predictions (same as main.py)
        if ML_ENGINE_AVAILABLE:
            from main import train_and_predict_ml
            players_df = train_and_predict_ml(db_manager, players_df, config, model_version)
        else:
            if 'EV' not in players_df.columns:
                players_df['EV'] = players_df.get('ep_next', 0)
        
        # Apply EO adjustment (like main.py)
        try:
            eo_calc = EOCalculator(config)
            players_df = eo_calc.apply_eo_adjustment(players_df, entry_info.get('summary_overall_rank', 100000))
        except Exception as e:
            logger.warning(f"Could not apply EO adjustment: {e}")
        
        # Sort by EV descending
        players_df = players_df.sort_values('EV', ascending=False)
        
        # Limit results
        if limit > 0:
            players_df = players_df.head(limit)
        
        # Convert to dict for JSON serialization
        # Select key columns for frontend
        display_columns = [
            'id', 'web_name', 'first_name', 'second_name', 'team', 'team_name',
            'element_type', 'now_cost', 'selected_by_percent', 'form', 'total_points',
            'EV', 'predicted_ev', 'xP_raw', 'xP_adjusted', 'ep_next',
            'status', 'chance_of_playing_next_round', 'news', 'news_added',
            'transfers_in', 'transfers_out', 'transfers_in_event', 'transfers_out_event',
            'points_per_game', 'minutes', 'goals_scored', 'assists', 'clean_sheets',
            'goals_conceded', 'yellow_cards', 'red_cards', 'saves', 'bonus',
            'bps', 'influence', 'creativity', 'threat', 'ict_index'
        ]
        
        # Only include columns that exist
        available_columns = [col for col in display_columns if col in players_df.columns]
        result_df = players_df[available_columns].copy()
        
        # Convert NaN to None for JSON serialization
        result_dict = result_df.where(pd.notnull(result_df), None).to_dict('records')
        
        return StandardResponse(
            data={
                "players": result_dict,
                "gameweek": gameweek,
                "model_version": model_version,
                "count": len(result_dict),
                "columns": available_columns
            },
            meta={
                "generated_at": datetime.now().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Error generating ML-enhanced players: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate ML-enhanced players: {str(e)}")

def determine_clean_gameweek(entry_id: int, api_client, events: List[Dict]) -> int:
    """
    Determine the correct gameweek by trying multiple gameweeks until finding one without blocked players.
    Returns the first clean gameweek found.
    """
    blocked_players = {5, 241}  # Gabriel, Caicedo
    
    logger.info(f"ML Report: [GAMEWEEK DETERMINATION] ========== STARTING GAMEWEEK DETERMINATION ==========")
    logger.info(f"ML Report: [GAMEWEEK DETERMINATION] Entry ID: {entry_id}, Blocked players: {blocked_players}")
    
    # Get current gameweek first
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    current_event = next((e for e in events if e.get('is_current', False)), None)
    
    if current_event:
        initial_gameweek = current_event.get('id')
        logger.info(f"ML Report: [GAMEWEEK DETERMINATION] Found current event: GW{initial_gameweek} (is_current=True, finished={current_event.get('finished', False)})")
    else:
        # Fallback: find latest finished gameweek
        finished_events = [e for e in events if e.get('finished', False)]
        if finished_events:
            initial_gameweek = max(finished_events, key=lambda x: x.get('id', 0)).get('id')
            logger.info(f"ML Report: [GAMEWEEK DETERMINATION] No current event, using latest finished: GW{initial_gameweek}")
        else:
            initial_gameweek = max((e.get('id', 1) for e in events), default=1)
            logger.info(f"ML Report: [GAMEWEEK DETERMINATION] No finished events, using max ID: GW{initial_gameweek}")
    
    logger.info(f"ML Report: [GAMEWEEK DETERMINATION] Initial gameweek: {initial_gameweek}")
    
    # Try multiple gameweeks in priority order
    gameweeks_to_try = []
    
    # Priority 1: Current gameweek
    gameweeks_to_try.append(initial_gameweek)
    
    # Priority 2: Next gameweek (if current is finished)
    target_event = next((e for e in events if e.get('id') == initial_gameweek), None)
    if target_event and target_event.get('finished', False):
        gameweeks_to_try.append(initial_gameweek + 1)
        logger.info(f"ML Report: [GAMEWEEK DETERMINATION] GW{initial_gameweek} is finished, will also try GW{initial_gameweek + 1}")
    
    # Priority 3: Most recent finished gameweek
    finished_events = [e for e in events if e.get('finished', False)]
    if finished_events:
        most_recent = max(finished_events, key=lambda x: x.get('id', 0))
        if most_recent['id'] not in gameweeks_to_try:
            gameweeks_to_try.append(most_recent['id'])
            logger.info(f"ML Report: [GAMEWEEK DETERMINATION] Will also try most recent finished: GW{most_recent['id']}")
    
    # Priority 4: Previous gameweek (but NOT for GW16+ to avoid GW15)
    if initial_gameweek >= 16:
        logger.info(f"ML Report: [GAMEWEEK DETERMINATION] GW{initial_gameweek} >= 16, skipping GW{initial_gameweek-1} to avoid blocked players")
    elif initial_gameweek - 1 not in gameweeks_to_try and initial_gameweek > 1:
        gameweeks_to_try.append(initial_gameweek - 1)
        logger.info(f"ML Report: [GAMEWEEK DETERMINATION] Will also try previous: GW{initial_gameweek - 1}")
    
    logger.info(f"ML Report: [GAMEWEEK DETERMINATION] Will try gameweeks in order: {gameweeks_to_try}")
    
    # Try each gameweek until we find one without blocked players
    for idx, try_gw in enumerate(gameweeks_to_try, 1):
        logger.info(f"ML Report: [GAMEWEEK DETERMINATION] ========== ATTEMPT {idx}/{len(gameweeks_to_try)}: Testing GW{try_gw} ==========")
        
        try:
            # Clear cache before each attempt
            api_client.clear_cache()
            logger.info(f"ML Report: [GAMEWEEK DETERMINATION] Cache cleared, fetching picks for GW{try_gw}...")
            
            picks_data = api_client.get_entry_picks(entry_id, try_gw, use_cache=False)
            
            if not picks_data:
                logger.warning(f"ML Report: [GAMEWEEK DETERMINATION] No picks_data returned for GW{try_gw}")
                continue
            
            if 'picks' not in picks_data:
                logger.warning(f"ML Report: [GAMEWEEK DETERMINATION] No 'picks' key in picks_data for GW{try_gw}")
                logger.warning(f"ML Report: [GAMEWEEK DETERMINATION] picks_data keys: {list(picks_data.keys())}")
                continue
            
            player_ids = [p['element'] for p in picks_data['picks']]
            logger.info(f"ML Report: [GAMEWEEK DETERMINATION] GW{try_gw} - Raw picks count: {len(player_ids)}")
            logger.info(f"ML Report: [GAMEWEEK DETERMINATION] GW{try_gw} - Raw player IDs: {sorted(player_ids)}")
            
            # Check for blocked players
            blocked_found = set(player_ids).intersection(blocked_players)
            
            if blocked_found:
                logger.error(f"ML Report: [GAMEWEEK DETERMINATION] ❌ GW{try_gw} CONTAINS BLOCKED PLAYERS: {blocked_found}")
                logger.error(f"ML Report: [GAMEWEEK DETERMINATION] Full player IDs from GW{try_gw}: {sorted(player_ids)}")
                logger.error(f"ML Report: [GAMEWEEK DETERMINATION] Blocked player details:")
                for pid in blocked_found:
                    blocked_pick = next((p for p in picks_data['picks'] if p['element'] == pid), None)
                    logger.error(f"ML Report: [GAMEWEEK DETERMINATION]   - Player ID {pid}: {blocked_pick}")
                continue
            
            # Success - found clean gameweek
            logger.info(f"ML Report: [GAMEWEEK DETERMINATION] ✅ SUCCESS - GW{try_gw} is CLEAN!")
            logger.info(f"ML Report: [GAMEWEEK DETERMINATION] Clean player IDs: {sorted(player_ids)}")
            logger.info(f"ML Report: [GAMEWEEK DETERMINATION] Verified: No blocked players in {len(player_ids)} picks")
            logger.info(f"ML Report: [GAMEWEEK DETERMINATION] ========== DETERMINED GAMEWEEK: {try_gw} ==========")
            return try_gw
            
        except Exception as e:
            logger.error(f"ML Report: [GAMEWEEK DETERMINATION] Exception testing GW{try_gw}: {e}", exc_info=True)
            continue
    
    # If we get here, all gameweeks failed - return the initial gameweek as fallback
    logger.error(f"ML Report: [GAMEWEEK DETERMINATION] ❌❌❌ CRITICAL - Could not find clean gameweek! ❌❌❌")
    logger.error(f"ML Report: [GAMEWEEK DETERMINATION] Tried gameweeks: {gameweeks_to_try}")
    logger.error(f"ML Report: [GAMEWEEK DETERMINATION] Falling back to initial gameweek: {initial_gameweek}")
    logger.error(f"ML Report: [GAMEWEEK DETERMINATION] ========== WARNING: USING FALLBACK GAMEWEEK ==========")
    return initial_gameweek

@app.get("/api/v1/ml/report")
async def get_ml_report(
    entry_id: int = Query(..., description="FPL entry ID (required)"),
    model_version: str = Query("v4.6", description="ML model version"),
    fast_mode: bool = Query(False, description="Fast mode: skip expensive operations (default: False for full ML)"),
    use_v2: bool = Query(False, description="Use simplified V2 report generator (rewritten from scratch)")
):
    """Get complete ML report data (same as main.py output) for a specific team"""
    
    # DEBUG: Log all parameters
    logger.info(f"ML Report: Received request - entry_id={entry_id}, model_version={model_version}, fast_mode={fast_mode}, use_v2={use_v2} (type: {type(use_v2)})")
    
    # #region agent log
    import json as json_log
    import platform as plat
    if plat.system() == 'Windows':
        DEBUG_LOG_PATH = r'C:\fpl-api\v2_debug.log'
    else:
        DEBUG_LOG_PATH = r'/Users/vitumbikokayuni/Documents/fpl-ai-thinktank4/.cursor/debug.log'
    try:
        with open(DEBUG_LOG_PATH, 'a') as f:
            f.write(json_log.dumps({"location":"dashboard_api.py:get_ml_report:entry","message":"ML Report endpoint called","data":{"entry_id":entry_id,"use_v2":use_v2,"fast_mode":fast_mode},"timestamp":int(datetime.now().timestamp()*1000),"sessionId":"debug-session","runId":"v2-debug","hypothesisId":"H1"}) + '\n')
    except: pass
    # #endregion
    
    # NEW: Use simplified V2 generator if requested
    # Handle both string "true"/"false" and boolean
    use_v2_bool = use_v2 if isinstance(use_v2, bool) else str(use_v2).lower() in ('true', '1', 'yes')
    
    # FORCE V2 FOR INVESTIGATION
    use_v2_bool = True
    
    # #region agent log
    try:
        with open(DEBUG_LOG_PATH, 'a') as f:
            f.write(json_log.dumps({"location":"dashboard_api.py:get_ml_report:v2_check","message":"V2 check","data":{"use_v2_bool":use_v2_bool},"timestamp":int(datetime.now().timestamp()*1000),"sessionId":"debug-session","runId":"v2-debug","hypothesisId":"H1"}) + '\n')
    except: pass
    # #endregion
    
    if use_v2_bool:
        # #region agent log
        try:
            with open(DEBUG_LOG_PATH, 'a') as f:
                f.write(json_log.dumps({"location":"dashboard_api.py:get_ml_report:v2_start","message":"Entering V2 code path","data":{},"timestamp":int(datetime.now().timestamp()*1000),"sessionId":"debug-session","runId":"v2-debug","hypothesisId":"H2"}) + '\n')
        except: pass
        # #endregion
        
        try:
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, 'a') as f:
                    f.write(json_log.dumps({"location":"dashboard_api.py:get_ml_report:v2_import","message":"Importing V2 generator","data":{},"timestamp":int(datetime.now().timestamp()*1000),"sessionId":"debug-session","runId":"v2-debug","hypothesisId":"H1"}) + '\n')
            except: pass
            # #endregion
            
            from .ml_report_v2 import generate_ml_report_v2
            
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, 'a') as f:
                    f.write(json_log.dumps({"location":"dashboard_api.py:get_ml_report:v2_import_success","message":"V2 import successful","data":{},"timestamp":int(datetime.now().timestamp()*1000),"sessionId":"debug-session","runId":"v2-debug","hypothesisId":"H1"}) + '\n')
            except: pass
            # #endregion
            
            import asyncio
            loop = asyncio.get_event_loop()
            report_data = await loop.run_in_executor(None, generate_ml_report_v2, entry_id, model_version)
            
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, 'a') as f:
                    f.write(json_log.dumps({"location":"dashboard_api.py:get_ml_report:v2_returned","message":"V2 generator returned","data":{"has_error": "error" in report_data, "has_transfer_recommendations": "transfer_recommendations" in report_data},"timestamp":int(datetime.now().timestamp()*1000),"sessionId":"debug-session","runId":"v2-debug","hypothesisId":"H2"}) + '\n')
            except: pass
            # #endregion
            
            if 'error' in report_data:
                # #region agent log
                try:
                    with open(DEBUG_LOG_PATH, 'a') as f:
                        f.write(json_log.dumps({"location":"dashboard_api.py:get_ml_report:v2_error","message":"V2 returned error","data":{"error": report_data.get('error')},"timestamp":int(datetime.now().timestamp()*1000),"sessionId":"debug-session","runId":"v2-debug","hypothesisId":"H2"}) + '\n')
                except: pass
                # #endregion
                raise HTTPException(status_code=500, detail=report_data['error'])
            
            # Check if blocked players are in the response
            players_out_ids = []
            if 'transfer_recommendations' in report_data:
                top_sug = report_data['transfer_recommendations'].get('top_suggestion', {})
                if top_sug and 'players_out' in top_sug:
                    players_out = top_sug['players_out']
                    players_out_ids = [p.get('id') for p in players_out]
                    blocked = set(players_out_ids).intersection({5, 241})
                    
                    # #region agent log
                    try:
                        with open(DEBUG_LOG_PATH, 'a') as f:
                            f.write(json_log.dumps({"location":"dashboard_api.py:get_ml_report:v2_final_check","message":"Final blocked player check","data":{"players_out_ids": players_out_ids, "blocked": list(blocked) if blocked else []},"timestamp":int(datetime.now().timestamp()*1000),"sessionId":"debug-session","runId":"v2-debug","hypothesisId":"H4"}) + '\n')
                    except: pass
                    # #endregion
            
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, 'a') as f:
                    f.write(json_log.dumps({"location":"dashboard_api.py:get_ml_report:v2_before_json","message":"About to create JSONResponse","data":{},"timestamp":int(datetime.now().timestamp()*1000),"sessionId":"debug-session","runId":"v2-debug","hypothesisId":"H5"}) + '\n')
            except: pass
            # #endregion
            
            # Convert all numpy types to native Python types for JSON serialization
            import numpy as np
            def convert_to_native(obj):
                if isinstance(obj, np.integer):
                    return int(obj)
                elif isinstance(obj, np.floating):
                    return float(obj)
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                elif isinstance(obj, dict):
                    return {k: convert_to_native(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_to_native(item) for item in obj]
                return obj
            
            report_data_native = convert_to_native(report_data)
            
            response_content = {
                "data": report_data_native,
                "meta": {
                    "model_version": model_version,
                    "generated_at": datetime.now().isoformat(),
                    "generator": "v2_simplified"
                }
            }
            
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, 'a') as f:
                    f.write(json_log.dumps({"location":"dashboard_api.py:get_ml_report:v2_creating_response","message":"Creating JSONResponse","data":{"content_keys": list(response_content.keys())},"timestamp":int(datetime.now().timestamp()*1000),"sessionId":"debug-session","runId":"v2-debug","hypothesisId":"H5"}) + '\n')
            except: pass
            # #endregion
            
            return JSONResponse(content=response_content)
        except HTTPException:
            raise
        except Exception as e:
            import traceback
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, 'a') as f:
                    f.write(json_log.dumps({"location":"dashboard_api.py:get_ml_report:v2_exception","message":"V2 generator exception","data":{"error": str(e), "traceback": traceback.format_exc()},"timestamp":int(datetime.now().timestamp()*1000),"sessionId":"debug-session","runId":"v2-debug","hypothesisId":"H1"}) + '\n')
            except: pass
            # #endregion
            raise HTTPException(status_code=500, detail=f"V2 generator failed: {str(e)}")
    
    # Original implementation - DISABLED since V2 is forced
    # The code below has been commented out to fix syntax errors
    # V2 always returns above, so this code never executes
    return JSONResponse(content={"error": "V2 forced but fell through - should never happen"}, status_code=500)
    
# ==================== OPTIMIZE TEAM ENDPOINT ====================
@app.get("/api/v1/optimize/team")
async def optimize_team(
    entry_id: int = Query(..., description="FPL entry ID"),
    gameweek: Optional[int] = Query(None, description="Target gameweek"),
    max_transfers: int = Query(4, description="Maximum transfers")
):
    """Optimize user's team with ML-powered recommendations"""
    # This endpoint calls the recommendations endpoint
    # Reuse the same logic
    return await get_transfer_recommendations(
        entry_id=entry_id,
        gameweek=gameweek,
        max_transfers=max_transfers,
        forced_out_ids=None,
        model_version="v4.6"
    )
