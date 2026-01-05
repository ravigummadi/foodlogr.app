"""FoodLogr MCP Server - Entry point.

Runs the MCP server with HTTP transport for Cloud Run deployment.
Uses Starlette with the MCP HTTP app for maximum compatibility.
"""

import logging
import os

import uvicorn
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount

from .shell.mcp_server import mcp, current_user_id, get_auth_client
from .shell.auth import validate_api_key_format, hash_api_key


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ==================== Route Handlers ====================


async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for Cloud Run."""
    return JSONResponse({"status": "healthy", "service": "foodlogr-mcp"})


async def register_user(request: Request) -> JSONResponse:
    """Register a new user and return their API key."""
    try:
        body = await request.json()
        email = body.get("email")

        if not email or "@" not in email:
            return JSONResponse({"error": "Valid email is required"}, status_code=400)

        auth_client = get_auth_client()
        api_key, user_id = auth_client.register_user(email)

        base_url = os.environ.get(
            "BASE_URL", "https://foodlogr-mcp-504360050716.us-central1.run.app"
        )

        return JSONResponse({
            "api_key": api_key,
            "message": "Registration successful! Save your API key - it won't be shown again.",
            "claude_command": f'claude mcp add --transport http foodlogr {base_url}/mcp --header "Authorization: Bearer {api_key}"',
        })

    except Exception as e:
        logger.error("Registration failed: %s", str(e))
        return JSONResponse({"error": "Registration failed."}, status_code=500)


async def validate_key(request: Request) -> JSONResponse:
    """Validate an API key."""
    try:
        body = await request.json()
        api_key = body.get("api_key")

        if not api_key:
            return JSONResponse({"valid": False, "error": "API key required"})

        auth_client = get_auth_client()
        user_id = auth_client.validate_api_key(api_key)
        return JSONResponse({"valid": user_id is not None})

    except Exception as e:
        logger.error("Validation failed: %s", str(e))
        return JSONResponse({"valid": False, "error": "Validation failed"})


# ==================== Auth Middleware ====================


class AuthMiddleware(BaseHTTPMiddleware):
    """Authenticate MCP requests using API key in Authorization header."""

    async def dispatch(self, request: Request, call_next):
        # Skip auth for non-MCP routes
        if not request.url.path.startswith("/mcp"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")

        if auth_header.startswith("Bearer "):
            api_key = auth_header.replace("Bearer ", "")

            if validate_api_key_format(api_key):
                user_id = hash_api_key(api_key)
                auth_client = get_auth_client()

                if auth_client.user_exists(user_id):
                    # Set user context for this request
                    current_user_id.set(user_id)
                    logger.debug("Authenticated user: %s", user_id[:8])

        return await call_next(request)


# ==================== Create ASGI App ====================


def create_app() -> Starlette:
    """Create the Starlette application with MCP at root.

    The MCP streamable_http_app() handles /mcp/ internally when mounted at root.
    We use its lifespan context to ensure proper initialization.
    """
    # Get the MCP ASGI app
    mcp_app = mcp.streamable_http_app()

    # Define routes - custom routes first, then MCP app at root
    routes = [
        Route("/health", health_check, methods=["GET"]),
        Route("/auth/register", register_user, methods=["POST"]),
        Route("/auth/validate", validate_key, methods=["POST"]),
        # Mount MCP app at root - it handles /mcp/ path internally
        Mount("/", app=mcp_app),
    ]

    # Create Starlette app with CORS and auth middleware
    app = Starlette(
        routes=routes,
        middleware=[
            Middleware(
                CORSMiddleware,
                allow_origins=["https://foodlogr.app", "http://localhost:5173"],
                allow_methods=["GET", "POST", "OPTIONS"],
                allow_headers=["*"],
            ),
            Middleware(AuthMiddleware),
        ],
        lifespan=mcp_app.router.lifespan_context,
    )

    return app


# Create app at module level for Cloud Run
app = create_app()


def main() -> None:
    """Run the server."""
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "0.0.0.0")

    logger.info("Starting FoodLogr MCP server on %s:%d", host, port)

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
