# setup_alembic.py
import os
from dotenv import load_dotenv

# Cargar .env
load_dotenv()

# Obtener DATABASE_URL del .env
database_url = os.getenv("DATABASE_URL", "sqlite:///./sonara.db")

config_content = f"""[alembic]
script_location = migrations
prepend_sys_path = .

sqlalchemy.url = {database_url}
"""

with open("alembic.ini", "w") as f:
    f.write(config_content)

print(" alembic.ini creado desde .env")