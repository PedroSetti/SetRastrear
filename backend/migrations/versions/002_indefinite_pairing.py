from alembic import op
from sqlalchemy import text
revision='002'
down_revision='001'
def upgrade():
 op.execute(text('UPDATE device_pairings SET expires = 0'))
def downgrade():
 raise RuntimeError('Downgrade requer definir explicitamente uma nova validade para os códigos existentes')
