import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app._route import router
from app._helpers import app

app.include_router(router)

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "3097"))
    uvicorn.run(app, host="0.0.0.0", port=port)
    uvicorn.run(app, host="0.0.0.0")
