"""Initial schema for MCPeeker registry

Revision ID: 001_initial_schema
Revises:
Create Date: 2025-10-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ========================================
    # Table: users
    # ========================================
    # Authenticated users with RBAC roles (FR-031)

    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('associated_endpoints', postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('last_login_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.CheckConstraint("role IN ('developer', 'analyst', 'admin')", name='users_role_check')
    )

    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_role', 'users', ['role'])

    # ========================================
    # Table: registry_entries
    # ========================================
    # Authorized MCP server registry (FR-006, FR-024)

    op.create_table(
        'registry_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('composite_id', sa.String(64), nullable=False),
        sa.Column('host', sa.String(255), nullable=False),
        sa.Column('port', sa.Integer, nullable=False),
        sa.Column('manifest_hash', sa.String(64), nullable=True),
        sa.Column('process_signature', sa.String(64), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('team', sa.String(100), nullable=True),
        sa.Column('purpose', sa.Text, nullable=False),
        sa.Column('approval_status', sa.String(50), nullable=False, server_default=sa.text("'pending'")),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approved_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('renewed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('expiration_notified_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ondelete='SET NULL'),
        sa.CheckConstraint("port > 0 AND port <= 65535", name='registry_entries_port_check'),
        sa.CheckConstraint("approval_status IN ('pending', 'approved', 'denied', 'expired')", name='registry_entries_approval_status_check')
    )

    op.create_unique_index('idx_registry_composite_id', 'registry_entries', ['composite_id'])
    op.create_index('idx_registry_owner', 'registry_entries', ['owner_id'])
    # Partial index for expiration checks
    op.execute("""
        CREATE INDEX idx_registry_expiration ON registry_entries(expires_at)
        WHERE approval_status = 'approved'
    """)

    # ========================================
    # Table: notification_preferences
    # ========================================
    # Per-user notification delivery configuration (FR-025a, FR-025b)

    op.create_table(
        'notification_preferences',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email_enabled', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('webhook_enabled', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('in_app_enabled', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('webhook_url', sa.String(512), nullable=True),
        sa.Column('webhook_secret', sa.String(255), nullable=True),
        sa.Column('notify_on_detection', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('notify_on_expiration', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('notify_on_system_alert', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('detection_score_threshold', sa.Integer, nullable=True, server_default=sa.text('9')),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )

    op.create_unique_index('idx_notif_prefs_user', 'notification_preferences', ['user_id'])

    # ========================================
    # Table: audit_logs
    # ========================================
    # Signed audit trail for compliance (FR-021, FR-022)

    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('actor_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('target_entity_type', sa.String(50), nullable=True),
        sa.Column('target_entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('changes', postgresql.JSONB, nullable=True),
        sa.Column('ip_address', postgresql.INET, nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('log_hash', sa.String(64), nullable=False),
        sa.Column('signature', sa.String(512), nullable=True),
        sa.Column('timestamp', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], ondelete='SET NULL')
    )

    op.create_index('idx_audit_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('idx_audit_actor', 'audit_logs', ['actor_user_id'])
    op.create_index('idx_audit_event_type', 'audit_logs', ['event_type'])


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('notification_preferences')
    op.drop_table('registry_entries')
    op.drop_table('users')
