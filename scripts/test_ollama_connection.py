#!/usr/bin/env python3
"""
Test Ollama connection using api/ollama (same layer as mindX UI and backend).
Usage: python scripts/test_ollama_connection.py [base_url]
Example: python scripts/test_ollama_connection.py
         python scripts/test_ollama_connection.py http://localhost:11434
"""
import asyncio
import sys
from pathlib import Path

# Allow importing from project root
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


async def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else None
    from api.ollama import create_ollama_api

    api = create_ollama_api(base_url=base_url) if base_url else create_ollama_api()
    print(f"Testing Ollama at {api.base_url} ...")
    result = await api.test_connection()
    print("Result:", result)
    if result.get("success"):
        models = await api.list_models()
        names = [m.get("name", m) if isinstance(m, dict) else m for m in models]
        print(f"Models ({len(names)}):", names[:15], "..." if len(names) > 15 else "")
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
