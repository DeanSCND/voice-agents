"""rename metadata to extra_data

Revision ID: 0553cfe31e31
Revises: initial_schema
Create Date: 2025-10-30 13:22:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0553cfe31e31'
down_revision = 'initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename metadata to extra_data in customers table
    op.alter_column('customers', 'metadata', new_column_name='extra_data')

    # Rename metadata to extra_data in calls table
    op.alter_column('calls', 'metadata', new_column_name='extra_data')

    # Change JSONB to JSON in call_transcript_entries
    op.alter_column('call_transcript_entries', 'tool_request',
                    type_=sa.JSON(),
                    existing_type=postgresql.JSONB(astext_type=sa.Text()))
    op.alter_column('call_transcript_entries', 'tool_response',
                    type_=sa.JSON(),
                    existing_type=postgresql.JSONB(astext_type=sa.Text()))
    op.alter_column('call_transcript_entries', 'event_data',
                    type_=sa.JSON(),
                    existing_type=postgresql.JSONB(astext_type=sa.Text()))


def downgrade() -> None:
    # Revert JSONB changes
    op.alter_column('call_transcript_entries', 'event_data',
                    type_=postgresql.JSONB(astext_type=sa.Text()),
                    existing_type=sa.JSON())
    op.alter_column('call_transcript_entries', 'tool_response',
                    type_=postgresql.JSONB(astext_type=sa.Text()),
                    existing_type=sa.JSON())
    op.alter_column('call_transcript_entries', 'tool_request',
                    type_=postgresql.JSONB(astext_type=sa.Text()),
                    existing_type=sa.JSON())

    # Revert column renames
    op.alter_column('calls', 'extra_data', new_column_name='metadata')
    op.alter_column('customers', 'extra_data', new_column_name='metadata')
