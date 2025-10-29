"""Keep-alive server for deployment platforms like Render, Railway, etc."""

from datetime import datetime
from logging import getLogger

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

logger = getLogger(__name__)

app = FastAPI(title="Discord Bot Keep-Alive Server")


@app.get("/")
async def root():
    """Root endpoint for basic health check"""
    return JSONResponse(
        content={
            "status": "ok",
            "message": "Discord bot is running",
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring services"""
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "intech-discord-bot",
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.get("/ping")
async def ping():
    """Simple ping endpoint"""
    return JSONResponse(content={"response": "pong"})


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the keep-alive server

    Args:
        host: Host address to bind to
        port: Port number to listen on
    """
    logger.info(f"Starting keep-alive server on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


async def run_server_async(host: str = "0.0.0.0", port: int = 8000):
    """Run the keep-alive server asynchronously

    Args:
        host: Host address to bind to
        port: Port number to listen on
    """
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    logger.info(f"Starting keep-alive server on {host}:{port}")
    await server.serve()


if __name__ == "__main__":
    # Standalone execution
    run_server()
