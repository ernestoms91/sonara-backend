"""add_created_by

Revision ID: 0e3d64da1e38
Revises: 26ac0fc764fb
Create Date: 2026-06-02 00:24:44.432324

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0e3d64da1e38'
down_revision: Union[str, None] = '26ac0fc764fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Verificar si las columnas ya existen antes de añadirlas
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Para tabla generated_audio
    columns = [col['name'] for col in inspector.get_columns('generated_audio')]
    if 'created_by' not in columns:
        op.add_column('generated_audio', sa.Column('created_by', sa.String(length=255), nullable=True))
    
    # Para tabla boletin
    columns = [col['name'] for col in inspector.get_columns('boletin')]
    if 'created_by' not in columns:
        with op.batch_alter_table('boletin') as batch_op:
            batch_op.add_column(sa.Column('created_by', sa.String(length=255), nullable=True))

def downgrade() -> None:
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Solo eliminar si existen
    columns = [col['name'] for col in inspector.get_columns('generated_audio')]
    if 'created_by' in columns:
        op.drop_column('generated_audio', 'created_by')
    
    columns = [col['name'] for col in inspector.get_columns('boletin')]
    if 'created_by' in columns:
        with op.batch_alter_table('boletin') as batch_op:
            batch_op.drop_column('created_by')