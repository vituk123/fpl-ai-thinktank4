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

# Learning system import
try:
    from .main import apply_learning_system
except ImportError:
    def apply_learning_system(*args, **kwargs):
        return kwargs.get('recommendations', []) if 'recommendations' in kwargs else []

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred. Please try again later.",
            "path": str(request.url.path)
        }
    )

# Global clients (initialized on startup)
dashboard: Optional[VisualizationDashboard] = None
db_manager: Optional[DatabaseManager] = None
api_client: Optional[FPLAPIClient] = None
live_tracker: Optional[LiveGameweekTracker] = None

@app.on_event("startup")  # type: ignore
async def startup_event():
    """Initialize clients on startup"""
    global dashboard, db_manager, api_client, config
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
        if not picks_data or 'picks' not in picks_data:
            try:
                picks_data = await loop.run_in_executor(None, api_client.get_entry_picks, entry_id, gameweek - 1, True)
            except:
                picks_data = None
        
        # Get all available data - pass shared data to avoid redundant calls
        live_points = tracker.get_live_points(gameweek, bootstrap=bootstrap, entry_history=entry_history, picks_data=picks_data)
        player_breakdown = tracker.get_player_breakdown(gameweek, bootstrap=bootstrap, picks_data=picks_data, fixtures=fixtures)
        team_summary = tracker.get_team_summary(gameweek, league_id=league_id, entry_info=entry_info, entry_history=entry_history)
        
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
        
        # Priority 1: Find next gameweek (is_next = True)
        next_event = next((e for e in events if e.get('is_next', False)), None)
        
        # Priority 2: Find current gameweek (is_current = True)
        current_event = next((e for e in events if e.get('is_current', False)), None)
        
        # Priority 3: If no current, find latest finished gameweek (most recent completed)
        if not current_event:
            finished_events = [e for e in events if e.get('finished', False)]
            if finished_events:
                current_event = max(finished_events, key=lambda x: x.get('id', 0))
        
        # Priority 4: Final fallback: latest event by ID (highest gameweek number)
        if not current_event and events:
            current_event = max(events, key=lambda x: x.get('id', 0))
        
        # Use next_event if available, otherwise current_event
        event = next_event or current_event
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
        if ML_ENGINE_AVAILABLE and MLEngine:
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

@app.get("/api/v1/ml/report")
async def get_ml_report(
    entry_id: int = Query(..., description="FPL entry ID (required)"),
    gameweek: Optional[int] = Query(None, description="Target gameweek (default: current)"),
    model_version: str = Query("v4.6", description="ML model version")
):
    """Get complete ML report data (same as main.py output) for a specific team"""
    if not api_client or not db_manager:
        raise HTTPException(status_code=503, detail="API client or database not available")
    
    try:
        import asyncio
        from .chips import ChipEvaluator
        from .report import ReportGenerator
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
        players_df['position'] = players_df['element_type']
        
        # Get user's entry info and history
        entry_info = await loop.run_in_executor(None, api_client.get_entry_info, entry_id, True)
        entry_history = await loop.run_in_executor(None, api_client.get_entry_history, entry_id, True)
        
        # Get current squad (like main.py)
        optimizer = TransferOptimizer(config)
        current_squad = await loop.run_in_executor(None, optimizer.get_current_squad, entry_id, gameweek, api_client, players_df)
        current_squad_ids = set(current_squad['id'].tolist()) if not current_squad.empty else set()
        current_squad_teams = set(current_squad['team'].dropna().unique()) if not current_squad.empty else set()
        
        # Get fixtures
        all_fixtures = await loop.run_in_executor(None, api_client.get_fixtures, True)
        fixtures_for_gw = [f for f in all_fixtures if f.get('event') == gameweek]
        
        # Identify top transfer targets (top 200) to limit processing (like main.py)
        top_players = players_df.nlargest(200, ['now_cost', 'total_points'], keep='all')
        relevant_team_ids = current_squad_teams | set(top_players['team'].dropna().unique())
        relevant_player_ids = current_squad_ids | set(top_players['id'].head(100).tolist())
        
        # Add fixture difficulty (optimized for relevant teams, like main.py)
        try:
            from .main import add_fixture_difficulty
            players_df = await loop.run_in_executor(
                None, 
                lambda: add_fixture_difficulty(players_df, api_client, gameweek, db_manager, relevant_team_ids, all_fixtures=all_fixtures, bootstrap_data=bootstrap)
            )
        except Exception as e:
            logger.warning(f"Could not add fixture difficulty: {e}")
        
        # Add statistical analysis (optimized for relevant players, like main.py)
        try:
            from .main import add_statistical_analysis
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
            from .main import train_and_predict_ml
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
        
        # Get bank value
        bank = entry_history.get('current', [{}])[-1].get('bank', 0) / 10.0
        
        # Generate transfer recommendations (like main.py)
        current_squad_ids_set = set(current_squad['id'])
        available_players = players_df[~players_df['id'].isin(current_squad_ids_set)].copy()
        
        # Calculate free transfers
        free_transfers = 1
        try:
            current_event = next((e for e in entry_history.get('current', []) if e.get('event') == gameweek - 1), None)
            if current_event:
                free_transfers = current_event.get('event_transfers', 0) + 1
                free_transfers = min(free_transfers, 2)
        except:
            pass
        
        smart_recs = optimizer.generate_smart_recommendations(
            current_squad, available_players, bank, free_transfers, max_transfers=4
        )
        
        # Apply learning system if available
        if ML_ENGINE_AVAILABLE and MLEngine:
            ml_engine_instance = MLEngine(db_manager, model_version=model_version)
            if ml_engine_instance.load_model():
                ml_engine_instance.is_trained = True
                smart_recs['recommendations'] = apply_learning_system(
                    db_manager, api_client, entry_id, gameweek,
                    smart_recs['recommendations'], ml_engine_instance
                )
        
        # Evaluate chips (like main.py)
        chip_eval = ChipEvaluator(config)
        chips_used = [c['name'] for c in entry_history.get('chips', [])]
        avail_chips = [c for c in ['bboost', '3xc', 'freehit', 'wildcard'] if c not in chips_used]
        chip_evals = chip_eval.evaluate_all_chips(
            current_squad, players_df, gameweek, avail_chips, bank, smart_recs['recommendations']
        )
        
        # Generate report data (JSON format)
        report_generator = ReportGenerator(config)
        report_data = report_generator.generate_report_data(
            entry_info, gameweek, current_squad, smart_recs['recommendations'],
            chip_evals, players_df, fixtures_for_gw, team_map
        )
        
        return StandardResponse(
            data=report_data,
            meta={
                "model_version": model_version,
                "generated_at": datetime.now().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Error generating ML report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate ML report: {str(e)}")


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
