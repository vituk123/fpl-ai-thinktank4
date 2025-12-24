#!/usr/bin/env python3
"""
Simple HTTP server to serve the frontend static files
"""
import http.server
import socketserver
import os
from pathlib import Path

# Frontend directory
FRONTEND_DIR = Path(__file__).parent / "frontend" / "dist"
PORT = 3000

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler to serve SPA routes"""
    
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        # Add cache control for index.html
        if self.path == '/' or self.path.endswith('.html'):
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()
    
    def do_GET(self):
        # Remove query string and fragment
        path = self.path.split('?')[0].split('#')[0]
        
        # Don't serve index.html for API routes
        if path.startswith('/api/'):
            self.send_error(404, "Not Found")
            return
        
        # Build file path
        if path == '/':
            file_path = FRONTEND_DIR / 'index.html'
        else:
            # Remove leading slash
            file_path = FRONTEND_DIR / path.lstrip('/')
        
        # If file doesn't exist or is a directory, serve index.html for SPA routing
        if not file_path.exists() or file_path.is_dir():
            file_path = FRONTEND_DIR / 'index.html'
        
        # Serve the file
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # Determine content type
            if file_path.suffix == '.html':
                content_type = 'text/html'
            elif file_path.suffix == '.css':
                content_type = 'text/css'
            elif file_path.suffix == '.js':
                content_type = 'application/javascript'
            elif file_path.suffix == '.json':
                content_type = 'application/json'
            elif file_path.suffix in ['.png', '.jpg', '.jpeg', '.gif', '.svg']:
                content_type = f'image/{file_path.suffix[1:]}'
            else:
                content_type = 'application/octet-stream'
            
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Internal Server Error: {str(e)}")

if __name__ == "__main__":
    import json
    import time
    
    # #region agent log
    log_path = Path(__file__).parent.parent / ".cursor" / "debug.log"
    log_data = {
        "location": "serve_frontend.py:77",
        "message": "Frontend server startup beginning",
        "data": {
            "frontend_dir": str(FRONTEND_DIR),
            "frontend_dir_exists": FRONTEND_DIR.exists(),
            "port": PORT
        },
        "timestamp": int(time.time() * 1000),
        "sessionId": "debug-session",
        "runId": "run1",
        "hypothesisId": "A"
    }
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_data) + '\n')
    except:
        pass
    # #endregion
    
    if not FRONTEND_DIR.exists():
        # #region agent log
        log_data = {
            "location": "serve_frontend.py:95",
            "message": "Frontend directory not found",
            "data": {"frontend_dir": str(FRONTEND_DIR)},
            "timestamp": int(time.time() * 1000),
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": "A"
        }
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_data) + '\n')
        except:
            pass
        # #endregion
        print(f"ERROR: Frontend directory not found: {FRONTEND_DIR}")
        print("Please build the frontend first: cd frontend && npm run build")
        exit(1)
    
    if not (FRONTEND_DIR / 'index.html').exists():
        # #region agent log
        log_data = {
            "location": "serve_frontend.py:110",
            "message": "index.html not found",
            "data": {"frontend_dir": str(FRONTEND_DIR)},
            "timestamp": int(time.time() * 1000),
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": "A"
        }
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_data) + '\n')
        except:
            pass
        # #endregion
        print(f"ERROR: index.html not found in {FRONTEND_DIR}")
        print("Please build the frontend first: cd frontend && npm run build")
        exit(1)
    
    print(f"Frontend server starting on port {PORT}")
    print(f"Serving from: {FRONTEND_DIR}")
    print(f"Open http://localhost:{PORT} in your browser")
    
    # #region agent log
    log_data = {
        "location": "serve_frontend.py:125",
        "message": "Creating TCPServer",
        "data": {
            "bind_address": "0.0.0.0",
            "port": PORT
        },
        "timestamp": int(time.time() * 1000),
        "sessionId": "debug-session",
        "runId": "run1",
        "hypothesisId": "B"
    }
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_data) + '\n')
    except:
        pass
    # #endregion
    
    try:
        with socketserver.TCPServer(("0.0.0.0", PORT), CustomHTTPRequestHandler) as httpd:
            # #region agent log
            log_data = {
                "location": "serve_frontend.py:140",
                "message": "TCPServer created successfully",
                "data": {
                    "server_address": str(httpd.server_address),
                    "port": httpd.server_address[1]
                },
                "timestamp": int(time.time() * 1000),
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "B"
            }
            try:
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_data) + '\n')
            except:
                pass
            # #endregion
            
            print(f"Server bound to {httpd.server_address}")
            
            # #region agent log
            log_data = {
                "location": "serve_frontend.py:155",
                "message": "Starting serve_forever",
                "data": {},
                "timestamp": int(time.time() * 1000),
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "B"
            }
            try:
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_data) + '\n')
            except:
                pass
            # #endregion
            
            httpd.serve_forever()
    except OSError as e:
        # #region agent log
        log_data = {
            "location": "serve_frontend.py:165",
            "message": "TCPServer creation failed",
            "data": {
                "error": str(e),
                "error_type": type(e).__name__
            },
            "timestamp": int(time.time() * 1000),
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": "B"
        }
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_data) + '\n')
        except:
            pass
        # #endregion
        print(f"ERROR: Failed to start server: {e}")
        exit(1)
    except KeyboardInterrupt:
        # #region agent log
        log_data = {
            "location": "serve_frontend.py:180",
            "message": "Server stopped by user",
            "data": {},
            "timestamp": int(time.time() * 1000),
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": "B"
        }
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_data) + '\n')
        except:
            pass
        # #endregion
        print("\nServer stopped")
