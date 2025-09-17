#!/usr/bin/env python3
"""
Simple test API server to verify basic functionality
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="MindX Test API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "MindX Test API is running"}

@app.get("/system/status")
async def get_status():
    return {
        "status": "running",
        "message": "MindX system is operational",
        "version": "test-1.0"
    }

@app.post("/system/evolve")
async def evolve_system(payload: dict):
    return {
        "message": f"Evolution directive received: {payload.get('directive', 'No directive provided')}",
        "status": "processing"
    }

@app.post("/coordinator/query")
async def query_coordinator(payload: dict):
    return {
        "response": f"Query received: {payload.get('query', 'No query provided')}",
        "status": "processed"
    }

@app.get("/agents/")
async def list_agents():
    return {
        "agents": ["test_agent_1", "test_agent_2"],
        "count": 2
    }

@app.get("/coordinator/backlog")
async def get_backlog():
    return {
        "backlog": ["Task 1", "Task 2", "Task 3"],
        "count": 3
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)




