"""add local auth and session tables

Revision ID: 0002_local_auth
Revises: 0001_initial
Create Date: 2026-04-03 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_local_auth"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE users SET email = lower(email)")

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("auth0_id", existing_type=sa.String(length=255), nullable=True)
        batch_op.add_column(sa.Column("password_hash", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("password_set_at", sa.DateTime(timezone=True), nullable=True))

    token_purpose = sa.Enum("email_verification", "password_reset", name="useronetimetokenpurpose")
    token_purpose.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("csrf_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_ip", sa.String(length=64), nullable=True),
        sa.Column("created_user_agent", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_token_hash", "user_sessions", ["token_hash"], unique=True)
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])

    op.create_table(
        "user_one_time_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", token_purpose, nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_ip", sa.String(length=64), nullable=True),
        sa.Column("created_user_agent", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_one_time_tokens_user_id", "user_one_time_tokens", ["user_id"])
    op.create_index("ix_user_one_time_tokens_purpose", "user_one_time_tokens", ["purpose"])
    op.create_index("ix_user_one_time_tokens_token_hash", "user_one_time_tokens", ["token_hash"], unique=True)
    op.create_index("ix_user_one_time_tokens_expires_at", "user_one_time_tokens", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_user_one_time_tokens_expires_at", table_name="user_one_time_tokens")
    op.drop_index("ix_user_one_time_tokens_token_hash", table_name="user_one_time_tokens")
    op.drop_index("ix_user_one_time_tokens_purpose", table_name="user_one_time_tokens")
    op.drop_index("ix_user_one_time_tokens_user_id", table_name="user_one_time_tokens")
    op.drop_table("user_one_time_tokens")

    op.drop_index("ix_user_sessions_expires_at", table_name="user_sessions")
    op.drop_index("ix_user_sessions_token_hash", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("password_set_at")
        batch_op.drop_column("last_login_at")
        batch_op.drop_column("email_verified_at")
        batch_op.drop_column("password_hash")
        batch_op.alter_column("auth0_id", existing_type=sa.String(length=255), nullable=False)

    sa.Enum(name="useronetimetokenpurpose").drop(op.get_bind(), checkfirst=True)
