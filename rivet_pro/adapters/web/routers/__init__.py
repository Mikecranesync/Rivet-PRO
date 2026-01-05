"""
API routers for Rivet Pro web adapter.
"""

from rivet_pro.adapters.web.routers import auth, equipment, work_orders, stats, upload

__all__ = ["auth", "equipment", "work_orders", "stats", "upload"]
