#!/usr/bin/env python3
"""
Simple mock API server for SimpleCoder update requests
This serves the update requests data without the complex backend dependencies
"""

import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import time

class MockAPIHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.update_requests_file = '/home/hacker/mindX/simple_coder_sandbox/update_requests.json'
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/simple-coder/update-requests':
            self.serve_update_requests()
        elif parsed_path.path == '/':
            self.serve_frontend()
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path.startswith('/simple-coder/approve-update/'):
            request_id = parsed_path.path.split('/')[-1]
            self.approve_update(request_id)
        elif parsed_path.path.startswith('/simple-coder/reject-update/'):
            request_id = parsed_path.path.split('/')[-1]
            self.reject_update(request_id)
        else:
            self.send_error(404, "Not Found")
    
    def serve_update_requests(self):
        try:
            if os.path.exists(self.update_requests_file):
                with open(self.update_requests_file, 'r') as f:
                    data = json.load(f)
            else:
                data = []
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
            
        except Exception as e:
            self.send_error(500, f"Error loading update requests: {str(e)}")
    
    def serve_frontend(self):
        # Serve the main frontend file
        frontend_path = '/home/hacker/mindX/mindx_frontend_ui/index.html'
        try:
            with open(frontend_path, 'r') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(content.encode())
            
        except Exception as e:
            self.send_error(404, f"Frontend not found: {str(e)}")
    
    def approve_update(self, request_id):
        try:
            # Load current requests
            if os.path.exists(self.update_requests_file):
                with open(self.update_requests_file, 'r') as f:
                    requests = json.load(f)
            else:
                requests = []
            
            # Find and update the request
            for request in requests:
                if request['request_id'] == request_id:
                    request['status'] = 'approved'
                    break
            
            # Save back to file
            with open(self.update_requests_file, 'w') as f:
                json.dump(requests, f, indent=2)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True, 'request_id': request_id}).encode())
            
        except Exception as e:
            self.send_error(500, f"Error approving update: {str(e)}")
    
    def reject_update(self, request_id):
        try:
            # Load current requests
            if os.path.exists(self.update_requests_file):
                with open(self.update_requests_file, 'r') as f:
                    requests = json.load(f)
            else:
                requests = []
            
            # Find and update the request
            for request in requests:
                if request['request_id'] == request_id:
                    request['status'] = 'rejected'
                    break
            
            # Save back to file
            with open(self.update_requests_file, 'w') as f:
                json.dump(requests, f, indent=2)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True, 'request_id': request_id}).encode())
            
        except Exception as e:
            self.send_error(500, f"Error rejecting update: {str(e)}")
    
    def do_OPTIONS(self):
        # Handle CORS preflight requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass

def start_mock_server():
    port = 8000
    server = HTTPServer(('0.0.0.0', port), MockAPIHandler)
    print(f"Mock API server running on http://localhost:{port}")
    print("Available endpoints:")
    print("  GET  /simple-coder/update-requests")
    print("  POST /simple-coder/approve-update/{request_id}")
    print("  POST /simple-coder/reject-update/{request_id}")
    print("  GET  / (serves frontend)")
    print("\nPress Ctrl+C to stop")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()

if __name__ == '__main__':
    start_mock_server()
