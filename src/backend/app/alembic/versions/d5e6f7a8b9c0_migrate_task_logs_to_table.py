"""migrate task logs from JSON column to dedicated task_log table

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-04-25 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'd5e6f7a8b9c0'
down_revision = 'c4d5e6f7a8b9'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create task_log table
    op.create_table(
        'task_log',
        sa.Column('created_time', sa.DateTime(), nullable=False),
        sa.Column('updated_time', sa.DateTime(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('task_id', sa.Uuid(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('level', sa.String(length=20), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['task.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # 2. Create indexes
    op.create_index('ix_task_log_task_id', 'task_log', ['task_id'])
    op.create_index(
        'ix_task_log_task_id_type', 'task_log', ['task_id', 'type']
    )
    op.create_index(
        'ix_task_log_task_id_timestamp', 'task_log', ['task_id', 'timestamp']
    )

    # 3. Migrate existing JSON data to new table (server-side SQL)
    conn = op.get_bind()
    conn.execute(sa.text("""
        INSERT INTO task_log (
            id, task_id, type, level, timestamp, message, data,
            created_time, updated_time
        )
        SELECT
            gen_random_uuid(),
            t.id,
            COALESCE(elem->>'type', 'log'),
            elem->>'level',
            CASE
                WHEN elem->>'timestamp' IS NOT NULL
                     AND elem->>'timestamp' ~ '^\\d{4}-'
                THEN (elem->>'timestamp')::timestamp
                ELSE NULL
            END,
            elem->>'message',
            CASE
                WHEN (elem::jsonb - 'type' - 'level' - 'timestamp' - 'message')
                     = '{}'::jsonb
                THEN NULL
                ELSE (elem::jsonb - 'type' - 'level' - 'timestamp' - 'message')
            END,
            NOW(),
            NOW()
        FROM task t,
             json_array_elements(t.logs) AS elem
        WHERE t.logs IS NOT NULL
          AND jsonb_typeof(t.logs::jsonb) = 'array'
    """))

    # 4. Drop the old JSON column
    op.drop_column('task', 'logs')


def downgrade():
    # 1. Re-add the logs JSON column
    op.add_column('task', sa.Column('logs', sa.JSON(), nullable=True))

    # 2. Aggregate rows back into JSON array
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE task t
        SET logs = sub.agg_logs
        FROM (
            SELECT
                tl.task_id,
                json_agg(
                    jsonb_build_object(
                        'type', tl.type,
                        'level', tl.level,
                        'timestamp', tl.timestamp,
                        'message', tl.message
                    ) || COALESCE(tl.data::jsonb, '{}'::jsonb)
                    ORDER BY tl.timestamp
                ) AS agg_logs
            FROM task_log tl
            GROUP BY tl.task_id
        ) sub
        WHERE t.id = sub.task_id
    """))

    # 3. Drop indexes and table
    op.drop_index('ix_task_log_task_id_timestamp', table_name='task_log')
    op.drop_index('ix_task_log_task_id_type', table_name='task_log')
    op.drop_index('ix_task_log_task_id', table_name='task_log')
    op.drop_table('task_log')
