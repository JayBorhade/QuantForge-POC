"""Broker connection routes."""

import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.encryption import decrypt_credentials, encrypt_credentials, mask_api_key
from app.models.broker_token import BrokerToken, BrokerType
from app.services.audit import log_audit
from brokers.factory import get_broker_adapter

router = APIRouter(prefix="/brokers", tags=["Brokers"])


class BrokerConnectRequest(BaseModel):
    broker: BrokerType
    api_key: str = Field(..., min_length=8)
    api_secret: str = Field(..., min_length=8)
    access_token: Optional[str] = None


class BrokerResponse(BaseModel):
    id: uuid.UUID
    broker: str
    is_active: bool
    last_synced_at: Optional[str]
    api_key_masked: Optional[str] = None

    model_config = {"from_attributes": True}


def _get_decrypted_token(token: BrokerToken) -> dict:
    try:
        return decrypt_credentials(token.api_secret_encrypted)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt broker credentials",
        )


@router.get("", response_model=List[BrokerResponse])
async def list_brokers(current_user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(BrokerToken).where(BrokerToken.user_id == current_user.id)
    )
    tokens = result.scalars().all()
    return [
        BrokerResponse(
            id=t.id,
            broker=t.broker.value,
            is_active=t.is_active,
            last_synced_at=t.last_synced_at.isoformat() if t.last_synced_at else None,
            api_key_masked=t.api_key,
        )
        for t in tokens
    ]


@router.post("/connect", response_model=BrokerResponse, status_code=status.HTTP_201_CREATED)
async def connect_broker(data: BrokerConnectRequest, current_user: CurrentUser, db: DbSession):
    adapter = get_broker_adapter(
        data.broker.value,
        data.api_key,
        data.api_secret,
        data.access_token,
    )
    connected = await adapter.connect()
    if not connected and data.broker != BrokerType.ZERODHA:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to connect to broker")

    encrypted = encrypt_credentials(data.api_key, data.api_secret, data.access_token)
    masked = mask_api_key(data.api_key)

    existing = await db.execute(
        select(BrokerToken).where(
            BrokerToken.user_id == current_user.id,
            BrokerToken.broker == data.broker,
        )
    )
    token = existing.scalar_one_or_none()
    if token:
        token.api_key = masked
        token.api_secret_encrypted = encrypted
        token.access_token = None
        token.is_active = True
    else:
        token = BrokerToken(
            user_id=current_user.id,
            broker=data.broker,
            api_key=masked,
            api_secret_encrypted=encrypted,
            access_token=None,
        )
        db.add(token)

    await log_audit(db, action="broker.connect", user_id=current_user.id, details={"broker": data.broker.value})
    await db.flush()
    await db.refresh(token)
    return BrokerResponse(
        id=token.id,
        broker=token.broker.value,
        is_active=token.is_active,
        last_synced_at=None,
        api_key_masked=masked,
    )


@router.delete("/{broker_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_broker(broker_id: uuid.UUID, current_user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(BrokerToken).where(BrokerToken.id == broker_id, BrokerToken.user_id == current_user.id)
    )
    token = result.scalar_one_or_none()
    if not token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Broker not found")
    token.is_active = False
    await log_audit(db, action="broker.disconnect", user_id=current_user.id)


@router.get("/quote/{symbol}")
async def get_quote(symbol: str, current_user: CurrentUser, db: DbSession, broker: str = "binance"):
    result = await db.execute(
        select(BrokerToken).where(
            BrokerToken.user_id == current_user.id,
            BrokerToken.broker == BrokerType(broker),
            BrokerToken.is_active == True,
        )
    )
    token = result.scalar_one_or_none()
    if not token:
        adapter = get_broker_adapter(broker, "demo", "demo")
    else:
        creds = _get_decrypted_token(token)
        adapter = get_broker_adapter(
            broker,
            creds["api_key"],
            creds["api_secret"],
            creds.get("access_token"),
        )
    return await adapter.get_quote(symbol)
