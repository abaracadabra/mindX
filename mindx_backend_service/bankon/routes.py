"""
bankon: "I do not understand" — endpoints for confusion/help and next steps.
Suitable for UI fallback when intent is unclear or for support flows.
"""
from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/bankon", tags=["bankon"])


class ConfusionPayload(BaseModel):
    message: Optional[str] = None
    context: Optional[str] = None


@router.get("", response_class=JSONResponse)
async def bankon_get(
    q: Optional[str] = Query(None, description="User query or 'I do not understand'"),
):
    """Return a structured response when the system or user signals 'I do not understand'."""
    return JSONResponse(
        content={
            "response": "I do not understand.",
            "suggestion": "Rephrase your request or use the help links below.",
            "query": q,
            "help": {
                "docs": "/docs",
                "health": "/health",
                "bankon_page": "/bankon/page",
            },
        }
    )


@router.post("", response_class=JSONResponse)
async def bankon_post(payload: Optional[ConfusionPayload] = None):
    """Accept a confusion or unclear message and return guidance."""
    msg = (payload and payload.message) or "I do not understand."
    return JSONResponse(
        content={
            "response": "I do not understand.",
            "received": msg,
            "context": (payload and payload.context) or None,
            "suggestion": "Try being more specific or check the docs.",
            "help": {"docs": "/docs", "bankon_page": "/bankon/page"},
        }
    )


@router.get("/page", response_class=HTMLResponse)
async def bankon_page():
    """Simple HTML page for 'I do not understand' — link from UI or support."""
    html = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>mindX — I do not understand</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: system-ui, sans-serif; margin: 0; padding: 2rem; background: #0f1419; color: #e6edf3; min-height: 100vh; }
    .container { max-width: 560px; margin: 0 auto; }
    h1 { font-size: 1.5rem; margin-bottom: 0.5rem; }
    p { color: #8b949e; margin: 1rem 0; }
    a { color: #58a6ff; }
    ul { margin: 1rem 0; padding-left: 1.25rem; }
    code { background: #1a2332; padding: 0.2em 0.4em; border-radius: 4px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>I do not understand</h1>
    <p>If you're seeing this, something was unclear. Here are some next steps:</p>
    <ul>
      <li>Rephrase your request and try again.</li>
      <li>Check <a href="/docs">API docs</a> for supported endpoints.</li>
      <li>Use <a href="/health">/health</a> to verify the service is running.</li>
    </ul>
    <p>mindX backend — <code>/bankon</code></p>
  </div>
</body>
</html>
"""
    return HTMLResponse(content=html)
