"""
Cognitive Skill Profiling API – Entry point
Usage:  python run.py
"""

import uvicorn
from dotenv import load_dotenv
import os

load_dotenv()

if __name__ == "__main__":
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "8000"))

    print(f"\n🚀  Starting Cognitive Profiling API on http://{host}:{port}")
    print(f"📖  Swagger UI -> http://localhost:{port}/docs\n")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,
    )
