"""
Dashboard API Server
FastAPI REST endpoints for visualization dashboard data.
"""
import logging
from typing import Optional, List, Dict, Tuple
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
    
    # If "*" is in the list and it's the only item, allow all
    # Otherwise, use the specific origins
    if cors_origins == ["*"] or (len(cors_origins) == 1 and cors_origins[0] == "*"):
        allow_origins = ["*"]
    else:
        # Remove "*" if present with other origins
        allow_origins = [origin for origin in cors_origins if origin != "*"]
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
    data: dict
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
                data={"gameweek": 1, "is_current": False, "is_finished": False, "is_next": False},
                meta={"event_name": ""}
            )
        
        # Priority 1: Find current gameweek (is_current = True)
        current_event = next((e for e in events if e.get('is_current', False)), None)
        
        # Priority 2: If no current, find latest finished gameweek (most recent completed)
        if not current_event:
            finished_events = [e for e in events if e.get('finished', False)]
            if finished_events:
                current_event = max(finished_events, key=lambda x: x.get('id', 0))
        
        # Priority 3: If still none, find next gameweek
        if not current_event:
            current_event = next((e for e in events if e.get('is_next', False)), None)
        
        # Priority 4: Final fallback: latest event by ID (highest gameweek number)
        if not current_event and events:
            current_event = max(events, key=lambda x: x.get('id', 0))
        
        gameweek = current_event.get('id', 1) if current_event else 1
        
        return StandardResponse(
            data={
                "gameweek": gameweek,
                "is_current": current_event.get('is_current', False) if current_event else False,
                "is_finished": current_event.get('finished', False) if current_event else False,
                "is_next": current_event.get('is_next', False) if current_event else False,
            },
            meta={
                "event_name": current_event.get('name', '') if current_event else ''
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
        
        # Load all players with projections
        # Get bootstrap data and build players DataFrame
        players_df = pd.DataFrame(bootstrap['elements'])
        teams_df = pd.DataFrame(bootstrap['teams'])
        team_map = {t['id']: t['name'] for t in teams_df.to_dict('records')}
        players_df['team_name'] = players_df['team'].map(team_map)
        
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
        
        # Apply learning system if available
        if ML_ENGINE_AVAILABLE and MLEngine:
            ml_engine_instance = MLEngine(db_manager, model_version=model_version)
            if ml_engine_instance.load_model():
                ml_engine_instance.is_trained = True
                recommendations['recommendations'] = apply_learning_system(
                    db_manager, api_client, entry_id, gameweek,
                    recommendations['recommendations'], ml_engine_instance
                )
        
        return StandardResponse(
            data={
                "entry_id": entry_id,
                "gameweek": gameweek,
                "recommendations": recommendations['recommendations'],
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
