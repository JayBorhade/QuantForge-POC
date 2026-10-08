"""API router aggregation."""

from fastapi import APIRouter

from app.api.routes import (
    admin,
    ai,
    auth,
    billing,
    brokers,
    dashboard,
    deployments,
    logs,
    notifications,
    portfolios,
    risk,
    sessions,
    strategies,
    websocket,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(billing.router)
api_router.include_router(strategies.router)
api_router.include_router(dashboard.router)
api_router.include_router(portfolios.router)
api_router.include_router(risk.router)
api_router.include_router(brokers.router)
api_router.include_router(notifications.router)
api_router.include_router(ai.router)
api_router.include_router(deployments.router)
api_router.include_router(logs.router)
api_router.include_router(sessions.router)
api_router.include_router(admin.router)
api_router.include_router(websocket.router)
