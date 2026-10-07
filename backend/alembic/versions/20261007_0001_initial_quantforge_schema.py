"""Initial QuantForge schema baseline.

Revision ID: 20261007_0001
Revises:
Create Date: 2026-10-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20261007_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL enum types used by the SQLAlchemy models.
    userrole = postgresql.ENUM("USER", "ADMIN", "SUPERADMIN", name="userrole")
    portfoliostatus = postgresql.ENUM("ACTIVE", "PAUSED", "CLOSED", name="portfoliostatus")
    tradeside = postgresql.ENUM("BUY", "SELL", name="tradeside")
    tradestatus = postgresql.ENUM("PENDING", "OPEN", "CLOSED", "CANCELLED", "FAILED", name="tradestatus")
    trademode = postgresql.ENUM("LIVE", "PAPER", "BACKTEST", name="trademode")
    strategytype = postgresql.ENUM(
        "EMA_CROSSOVER", "RSI_MEAN_REVERSION", "VWAP_INTRADAY", "BREAKOUT", "AI_SENTIMENT", "CUSTOM",
        name="strategytype",
    )
    strategystatus = postgresql.ENUM("DRAFT", "ACTIVE", "PAUSED", "STOPPED", "ERROR", name="strategystatus")
    runstatus = postgresql.ENUM("PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED", name="runstatus")
    runmode = postgresql.ENUM("LIVE", "PAPER", "BACKTEST", name="runmode")
    brokertype = postgresql.ENUM("ZERODHA", "BINANCE", "ANGEL_ONE", name="brokertype")
    notificationtype = postgresql.ENUM("TRADE", "STRATEGY", "ALERT", "SYSTEM", "AI", "SECURITY", name="notificationtype")
    deploymentstatus = postgresql.ENUM("PENDING", "DEPLOYING", "RUNNING", "STOPPED", "FAILED", name="deploymentstatus")
    plantier = postgresql.ENUM("FREE", "STARTER", "PRO", "ENTERPRISE", name="plantier")
    subscriptionstatus = postgresql.ENUM("ACTIVE", "CANCELLED", "EXPIRED", "TRIAL", name="subscriptionstatus")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", userrole, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("is_banned", sa.Boolean(), nullable=False),
        sa.Column("two_factor_enabled", sa.Boolean(), nullable=False),
        sa.Column("two_factor_secret", sa.String(length=64), nullable=True),
        sa.Column("avatar_url", sa.String(length=512), nullable=True),
        sa.Column("email_verification_token", sa.String(length=128), nullable=True),
        sa.Column("password_reset_token", sa.String(length=128), nullable=True),
        sa.Column("password_reset_expires", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
            )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("refresh_token_jti", sa.String(length=64), nullable=False),
        sa.Column("device_name", sa.String(length=255), nullable=True),
        sa.Column("device_type", sa.String(length=64), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("location", sa.String(length=128), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("remember_me", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
            )
    op.create_index("ix_user_sessions_refresh_token_jti", "user_sessions", ["refresh_token_jti"], unique=True)
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"], unique=False)

    op.create_table(
        "strategies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("strategy_type", strategytype, nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("status", strategystatus, nullable=False),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("schedule_cron", sa.String(length=64), nullable=True),
        sa.Column("is_paper", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_strategies_user_id", "strategies", ["user_id"], unique=False)

    op.create_table(
        "portfolios",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("total_value", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("cash_balance", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("daily_pnl", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("total_pnl", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("risk_exposure", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("win_rate", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("status", portfoliostatus, nullable=False),
        sa.Column("broker", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_portfolios_user_id", "portfolios", ["user_id"], unique=False)

    op.create_table(
        "broker_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("broker", brokertype, nullable=False),
        sa.Column("api_key", sa.String(length=512), nullable=False),
        sa.Column("api_secret_encrypted", sa.Text(), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_broker_tokens_user_id", "broker_tokens", ["user_id"], unique=False)

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", notificationtype, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=True),
        sa.Column("email_sent", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"], unique=False)

    op.create_table(
        "deployments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("status", deploymentstatus, nullable=False),
        sa.Column("region", sa.String(length=64), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("logs", sa.Text(), nullable=True),
        sa.Column("deployed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_deployments_strategy_id", "deployments", ["strategy_id"], unique=False)
    op.create_index("ix_deployments_user_id", "deployments", ["user_id"], unique=False)

    op.create_table(
        "strategy_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mode", runmode, nullable=False),
        sa.Column("status", runstatus, nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sharpe_ratio", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("max_drawdown", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("total_return", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("win_rate", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("total_trades", sa.Integer(), nullable=False),
        sa.Column("results", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_strategy_runs_strategy_id", "strategy_runs", ["strategy_id"], unique=False)

    op.create_table(
        "trades",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("side", tradeside, nullable=False),
        sa.Column("status", tradestatus, nullable=False),
        sa.Column("mode", trademode, nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column("entry_price", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("exit_price", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("stop_loss", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("take_profit", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("pnl", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("fees", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("broker_order_id", sa.String(length=128), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trades_portfolio_id", "trades", ["portfolio_id"], unique=False)
    op.create_index("ix_trades_symbol", "trades", ["symbol"], unique=False)

    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan", plantier, nullable=False),
        sa.Column("status", subscriptionstatus, nullable=False),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=128), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=128), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("resource", sa.String(length=128), nullable=True),
        sa.Column("resource_id", sa.String(length=64), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"], unique=False)
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"], unique=False)
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_table("subscriptions")
    op.drop_index("ix_trades_symbol", table_name="trades")
    op.drop_index("ix_trades_portfolio_id", table_name="trades")
    op.drop_table("trades")
    op.drop_index("ix_strategy_runs_strategy_id", table_name="strategy_runs")
    op.drop_table("strategy_runs")
    op.drop_index("ix_deployments_user_id", table_name="deployments")
    op.drop_index("ix_deployments_strategy_id", table_name="deployments")
    op.drop_table("deployments")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_broker_tokens_user_id", table_name="broker_tokens")
    op.drop_table("broker_tokens")
    op.drop_index("ix_portfolios_user_id", table_name="portfolios")
    op.drop_table("portfolios")
    op.drop_index("ix_strategies_user_id", table_name="strategies")
    op.drop_table("strategies")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_index("ix_user_sessions_refresh_token_jti", table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    for enum_name in (
        "subscriptionstatus", "plantier", "deploymentstatus", "notificationtype",
        "brokertype", "runmode", "runstatus", "strategystatus", "strategytype",
        "trademode", "tradestatus", "tradeside", "portfoliostatus", "userrole",
    ):
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
