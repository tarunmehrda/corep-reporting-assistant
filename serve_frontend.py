#!/usr/bin/env python3
"""
Modern HTTP server to serve the PRA COREP Reporting Assistant frontend.
Run this script to serve the frontend on http://localhost:3000
"""

import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers to allow API calls
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        # Serve index.html for root path
        if self.path == '/':
            self.path = '/frontend/index.html'
        # Serve favicon.ico
        elif self.path == '/favicon.ico':
            self.path = '/frontend/favicon.ico'
        # Serve frontend files
        elif self.path.startswith('/'):
            if not self.path.startswith('/frontend'):
                self.path = '/frontend' + self.path
        
        return super().do_GET()

def main():
    PORT = 3001
    frontend_dir = Path(__file__).parent
    
    # Change to frontend directory
    os.chdir(frontend_dir)
    
    # Create server
    with socketserver.TCPServer(("", PORT), CustomHTTPRequestHandler) as httpd:
        print(f"🚀 Modern Frontend server started at http://localhost:{PORT}")
        print(f"📁 Serving from: {frontend_dir}/frontend/")
        print("🔄 Make sure the API server is running at http://localhost:8000")
        print("🌐 Opening modern browser interface...")
        
        # Open browser to the modern frontend
        webbrowser.open(f'http://localhost:{PORT}/frontend/index.html')
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 Server stopped")

if __name__ == "__main__":
    main()
