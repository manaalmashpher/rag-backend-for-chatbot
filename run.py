"""
Startup script for the IonologyBot API
"""
import os
import uvicorn
from app.main import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))  # use Railway's injected PORT
    uvicorn.run(
        app,                 # pass the app object (avoids double import)
        host="0.0.0.0",
        port=port,
        reload=False,        # disable reloader in production
        log_level="info",
        workers=1            # keep 1 unless you know you need more
    )
