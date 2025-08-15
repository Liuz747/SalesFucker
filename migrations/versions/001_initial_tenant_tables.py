"""创建租户管理相关表

Revision ID: 001
Revises: 
Create Date: 2025-01-08 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建租户表
    op.create_table('tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(length=255), nullable=False),
        sa.Column('tenant_name', sa.String(length=500), nullable=False),
        sa.Column('brand_settings', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('ai_model_preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('compliance_settings', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('feature_flags', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('allowed_origins', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('rate_limit_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('enable_audit_logging', sa.Boolean(), nullable=False),
        sa.Column('enable_rate_limiting', sa.Boolean(), nullable=False),
        sa.Column('enable_device_validation', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_access', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_requests', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建租户表索引
    op.create_index('idx_tenant_id', 'tenants', ['tenant_id'], unique=True)
    op.create_index('idx_tenant_active', 'tenants', ['is_active'], unique=False)
    op.create_index('idx_tenant_updated', 'tenants', ['updated_at'], unique=False)
    
    # 创建安全审计日志表
    op.create_table('security_audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('log_id', sa.String(length=255), nullable=False),
        sa.Column('tenant_id', sa.String(length=255), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('event_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('client_ip', sa.String(length=45), nullable=False),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('request_id', sa.String(length=255), nullable=True),
        sa.Column('jwt_subject', sa.String(length=255), nullable=True),
        sa.Column('jwt_issuer', sa.String(length=255), nullable=True),
        sa.Column('authentication_result', sa.String(length=50), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('risk_level', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建安全审计日志表索引
    op.create_index('idx_audit_log_id', 'security_audit_logs', ['log_id'], unique=True)
    op.create_index('idx_audit_tenant_event', 'security_audit_logs', ['tenant_id', 'event_type'], unique=False)
    op.create_index('idx_audit_timestamp', 'security_audit_logs', ['event_timestamp'], unique=False)
    op.create_index('idx_audit_risk', 'security_audit_logs', ['risk_level'], unique=False)
    op.create_index('idx_audit_client_ip', 'security_audit_logs', ['client_ip'], unique=False)
    op.create_index('idx_audit_request_id', 'security_audit_logs', ['request_id'], unique=False)


def downgrade() -> None:
    # 删除安全审计日志表
    op.drop_index('idx_audit_request_id', table_name='security_audit_logs')
    op.drop_index('idx_audit_client_ip', table_name='security_audit_logs')
    op.drop_index('idx_audit_risk', table_name='security_audit_logs')
    op.drop_index('idx_audit_timestamp', table_name='security_audit_logs')
    op.drop_index('idx_audit_tenant_event', table_name='security_audit_logs')
    op.drop_index('idx_audit_log_id', table_name='security_audit_logs')
    op.drop_table('security_audit_logs')
    
    # 删除租户表
    op.drop_index('idx_tenant_updated', table_name='tenants')
    op.drop_index('idx_tenant_active', table_name='tenants')
    op.drop_index('idx_tenant_id', table_name='tenants')
    op.drop_table('tenants')



