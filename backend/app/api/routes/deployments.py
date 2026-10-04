"""Deployment center routes."""

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.deployment import Deployment, DeploymentStatus
from app.models.strategy import Strategy
from app.services.audit import log_audit

router = APIRouter(prefix="/deployments", tags=["Deployments"])


class DeploymentCreate(BaseModel):
    strategy_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=128)
    region: str = "us-east-1"
    config: Dict[str, Any] = Field(default_factory=dict)


class DeploymentResponse(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    region: str
    strategy_id: uuid.UUID
    deployed_at: Optional[str]
    created_at: str

    model_config = {"from_attributes": True}


@router.get("", response_model=List[DeploymentResponse])
async def list_deployments(current_user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Deployment).where(Deployment.user_id == current_user.id).order_by(Deployment.created_at.desc())
    )
    deployments = result.scalars().all()
    return [
        DeploymentResponse(
            id=d.id,
            name=d.name,
            status=d.status.value,
            region=d.region,
            strategy_id=d.strategy_id,
            deployed_at=d.deployed_at.isoformat() if d.deployed_at else None,
            created_at=d.created_at.isoformat(),
        )
        for d in deployments
    ]


@router.post("", response_model=DeploymentResponse, status_code=status.HTTP_201_CREATED)
async def create_deployment(data: DeploymentCreate, current_user: CurrentUser, db: DbSession):
    strat_result = await db.execute(
        select(Strategy).where(Strategy.id == data.strategy_id, Strategy.user_id == current_user.id)
    )
    if not strat_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")

    deployment = Deployment(
        user_id=current_user.id,
        strategy_id=data.strategy_id,
        name=data.name,
        region=data.region,
        config=data.config,
        status=DeploymentStatus.PENDING,
    )
    db.add(deployment)
    await log_audit(db, action="deployment.create", user_id=current_user.id)
    await db.flush()
    await db.refresh(deployment)
    return DeploymentResponse(
        id=deployment.id,
        name=deployment.name,
        status=deployment.status.value,
        region=deployment.region,
        strategy_id=deployment.strategy_id,
        deployed_at=None,
        created_at=deployment.created_at.isoformat(),
    )


@router.post("/{deployment_id}/start")
async def start_deployment(deployment_id: uuid.UUID, current_user: CurrentUser, db: DbSession):
    deployment = await _get_deployment(db, deployment_id, current_user.id)
    deployment.status = DeploymentStatus.RUNNING
    from datetime import datetime, timezone
    deployment.deployed_at = datetime.now(timezone.utc)
    return {"message": "Deployment started", "id": str(deployment.id)}


@router.post("/{deployment_id}/stop")
async def stop_deployment(deployment_id: uuid.UUID, current_user: CurrentUser, db: DbSession):
    deployment = await _get_deployment(db, deployment_id, current_user.id)
    deployment.status = DeploymentStatus.STOPPED
    from datetime import datetime, timezone
    deployment.stopped_at = datetime.now(timezone.utc)
    return {"message": "Deployment stopped", "id": str(deployment.id)}


async def _get_deployment(db, deployment_id: uuid.UUID, user_id: uuid.UUID) -> Deployment:
    result = await db.execute(
        select(Deployment).where(Deployment.id == deployment_id, Deployment.user_id == user_id)
    )
    deployment = result.scalar_one_or_none()
    if not deployment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deployment not found")
    return deployment
