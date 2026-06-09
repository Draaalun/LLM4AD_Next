"""add chat_tune_session and chat_tune_message tables

Revision ID: c5d6e7f8a9b0
Revises: a2b3c4d5e6f7
Create Date: 2026-05-21 10:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'c5d6e7f8a9b0'
down_revision = 'a2b3c4d5e6f7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'chat_tune_session',
        sa.Column('created_time', sa.DateTime(), nullable=False),
        sa.Column('updated_time', sa.DateTime(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('task_id', sa.Uuid(), nullable=False),
        sa.Column('active_turn_id', sa.Uuid(), nullable=True),
        sa.Column(
            'latest_config',
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['task.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id', name='uq_chat_tune_session_task_id'),
    )
    op.create_index(
        op.f('ix_chat_tune_session_user_id'),
        'chat_tune_session',
        ['user_id'],
    )

    op.create_table(
        'chat_tune_message',
        sa.Column('created_time', sa.DateTime(), nullable=False),
        sa.Column('updated_time', sa.DateTime(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('session_id', sa.Uuid(), nullable=False),
        sa.Column('turn_id', sa.Uuid(), nullable=False),
        sa.Column(
            'role',
            sa.Enum(
                'user', 'assistant', 'system',
                name='chattunemessagerole', native_enum=False, length=20,
            ),
            nullable=False,
        ),
        sa.Column('content', sa.Text(), nullable=False, server_default=''),
        sa.Column(
            'turn_status',
            sa.Enum(
                'generating', 'completed', 'failed', 'cancelled',
                name='chattuneturnstatus', native_enum=False, length=20,
            ),
            nullable=False,
            server_default='completed',
        ),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column(
            'payload_locked',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),
        sa.Column('payload_locked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('payload_submission', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ['session_id'], ['chat_tune_session.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'session_id', 'turn_id', 'role',
            name='uq_chat_tune_message_turn_role',
        ),
    )
    op.create_index(
        op.f('ix_chat_tune_message_session_id'),
        'chat_tune_message',
        ['session_id'],
    )
    op.create_index(
        op.f('ix_chat_tune_message_turn_id'),
        'chat_tune_message',
        ['turn_id'],
    )
    # 热路径：service 层都按 (session_id, turn_id) 过滤
    op.create_index(
        'ix_chat_tune_message_session_turn',
        'chat_tune_message',
        ['session_id', 'turn_id'],
    )
    # 启动钩子 reset_orphan_turns 的部分索引：只覆盖 generating 状态的行，
    # 避免随历史增长触发全表扫描
    op.create_index(
        'ix_chat_tune_message_generating',
        'chat_tune_message',
        ['updated_time'],
        postgresql_where=sa.text("turn_status = 'generating'"),
    )


def downgrade():
    op.drop_index(
        'ix_chat_tune_message_generating', table_name='chat_tune_message'
    )
    op.drop_index(
        'ix_chat_tune_message_session_turn', table_name='chat_tune_message'
    )
    op.drop_index(
        op.f('ix_chat_tune_message_turn_id'), table_name='chat_tune_message'
    )
    op.drop_index(
        op.f('ix_chat_tune_message_session_id'), table_name='chat_tune_message'
    )
    op.drop_table('chat_tune_message')
    op.drop_index(
        op.f('ix_chat_tune_session_user_id'), table_name='chat_tune_session'
    )
    op.drop_table('chat_tune_session')
