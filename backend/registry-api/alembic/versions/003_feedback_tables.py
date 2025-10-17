"""Add feedback and investigation tables

Revision ID: 003
Revises: 002
Create Date: 2025-01-17

Reference: FR-023 (Analyst feedback), US2
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create feedback_records table
    op.create_table(
        'feedback_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('detection_id', sa.String(255), nullable=False, index=True),
        sa.Column('composite_id', sa.String(64), nullable=True, index=True),
        sa.Column('analyst_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('analyst_email', sa.String(255), nullable=False),
        sa.Column('feedback_type', sa.String(50), nullable=False, index=True),
        sa.Column('severity', sa.String(20), nullable=True),
        sa.Column('notes', sa.Text, nullable=False),
        sa.Column('recommended_action', sa.Text, nullable=True),
        sa.Column('investigation_status', sa.String(50), nullable=False, server_default='open', index=True),
        sa.Column('resolution_notes', sa.Text, nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tags', postgresql.JSONB, nullable=True),
        sa.Column('additional_context', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['analyst_id'], ['users.id'], ondelete='SET NULL'),
        sa.CheckConstraint("feedback_type IN ('false_positive', 'true_positive', 'investigation_needed', 'escalation_required', 'resolved')", name='check_feedback_type'),
        sa.CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')", name='check_severity'),
        sa.CheckConstraint("investigation_status IN ('open', 'in_progress', 'resolved', 'closed')", name='check_investigation_status'),
    )

    # Create investigation_notes table
    op.create_table(
        'investigation_notes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('feedback_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('detection_id', sa.String(255), nullable=False, index=True),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('author_email', sa.String(255), nullable=False),
        sa.Column('note_text', sa.Text, nullable=False),
        sa.Column('note_type', sa.String(50), nullable=False, server_default='observation'),
        sa.Column('is_internal', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['feedback_id'], ['feedback_records.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='SET NULL'),
        sa.CheckConstraint("note_type IN ('observation', 'action_taken', 'question', 'conclusion')", name='check_note_type'),
    )

    # Create indexes for better query performance
    op.create_index('ix_feedback_detection_type', 'feedback_records', ['detection_id', 'feedback_type'])
    op.create_index('ix_feedback_analyst_status', 'feedback_records', ['analyst_email', 'investigation_status'])
    op.create_index('ix_notes_feedback_created', 'investigation_notes', ['feedback_id', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_notes_feedback_created', 'investigation_notes')
    op.drop_index('ix_feedback_analyst_status', 'feedback_records')
    op.drop_index('ix_feedback_detection_type', 'feedback_records')
    op.drop_table('investigation_notes')
    op.drop_table('feedback_records')
