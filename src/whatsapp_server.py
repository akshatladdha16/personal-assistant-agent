from __future__ import annotations

import uvicorn

from src.interfaces.whatsapp import create_app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("src.whatsapp_server:app", host="0.0.0.0", port=8080)
