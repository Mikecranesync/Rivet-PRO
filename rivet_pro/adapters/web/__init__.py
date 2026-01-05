"""
Web adapter for Rivet Pro.
Provides FastAPI REST API for CMMS functionality.
"""

from rivet_pro.adapters.web.main import app

__all__ = ["app"]
