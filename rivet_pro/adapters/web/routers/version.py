"""
Version endpoint for API monitoring and debugging.

Returns API version, environment, and build information.
"""

import sys
from fastapi import APIRouter
from rivet_pro.config.settings import settings

router = APIRouter()


@router.get("/version")
async def get_version() -> dict:
    """
    Get API version and environment information.

    Returns:
        dict: Version info including version, environment, API name, and Python version.

    Example response:
        {
            "version": "1.0.0",
            "environment": "development",
            "api_name": "rivet-pro-api",
            "python_version": "3.11.9"
        }
    """
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    return {
        "version": "1.0.0",
        "environment": settings.environment,
        "api_name": "rivet-pro-api",
        "python_version": python_version
    }
