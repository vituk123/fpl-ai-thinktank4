#!/usr/bin/env python3
"""
Start the Dashboard API server
"""
import sys
from pathlib import Path
import yaml
import uvicorn

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def main():
    """Start the dashboard API server"""
    # Load config
    config_path = Path('config.yml')
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    else:
        config = {}
    
    dashboard_config = config.get('dashboard', {})
    port = dashboard_config.get('api_port', 8000)
    
    print("=" * 70)
    print("FPL VISUALIZATION DASHBOARD API")
    print("=" * 70)
    print(f"Starting server on http://localhost:{port}")
    print(f"API documentation: http://localhost:{port}/docs")
    print("=" * 70)
    
    # Run the server
    uvicorn.run(
        "dashboard_api:app",
        host="0.0.0.0",
        port=port,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )

if __name__ == '__main__':
    main()

