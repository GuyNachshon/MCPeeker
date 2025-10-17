"""Add Row-Level Security policies

Revision ID: 002_rls_policies
Revises: 001_initial_schema
Create Date: 2025-10-16

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '002_rls_policies'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable Row-Level Security on users table
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")

    # Create policy for developers to view only their own records
    op.execute("""
        CREATE POLICY developer_self_view ON users
            FOR SELECT
            USING (
                role = 'developer'
                AND id = current_setting('app.current_user_id')::uuid
            )
    """)

    # Create policy for analysts and admins to view all users
    op.execute("""
        CREATE POLICY analyst_admin_view ON users
            FOR SELECT
            USING (
                role IN ('analyst', 'admin')
            )
    """)

    # Enable RLS on registry_entries table
    op.execute("ALTER TABLE registry_entries ENABLE ROW LEVEL SECURITY")

    # Developers can view and update their own registry entries
    op.execute("""
        CREATE POLICY developer_own_registry ON registry_entries
            FOR ALL
            USING (
                owner_id = current_setting('app.current_user_id')::uuid
            )
    """)

    # Analysts and admins can view all registry entries
    op.execute("""
        CREATE POLICY analyst_admin_registry_view ON registry_entries
            FOR SELECT
            USING (true)
    """)

    # Only admins can approve/deny registry entries
    op.execute("""
        CREATE POLICY admin_registry_approve ON registry_entries
            FOR UPDATE
            USING (
                EXISTS (
                    SELECT 1 FROM users
                    WHERE id = current_setting('app.current_user_id')::uuid
                    AND role = 'admin'
                )
            )
    """)


def downgrade() -> None:
    # Drop policies
    op.execute("DROP POLICY IF EXISTS developer_self_view ON users")
    op.execute("DROP POLICY IF EXISTS analyst_admin_view ON users")
    op.execute("DROP POLICY IF EXISTS developer_own_registry ON registry_entries")
    op.execute("DROP POLICY IF EXISTS analyst_admin_registry_view ON registry_entries")
    op.execute("DROP POLICY IF EXISTS admin_registry_approve ON registry_entries")

    # Disable RLS
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE registry_entries DISABLE ROW LEVEL SECURITY")
