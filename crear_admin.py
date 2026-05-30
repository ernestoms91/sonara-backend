# crear_admin.py
from datetime import datetime, timezone
from app.core.database import get_engine
from app.core.security import hash_password
from sqlmodel import Session, select
from app.models.user import User

def crear_admin():
    engine = get_engine()
    
    try:
        with Session(engine) as session:
            # Verificar si ya existe algún admin
            statement = select(User).where(User.is_admin == True)
            admin_exists = session.exec(statement).first()
            
            if admin_exists:
                print(f"\n[AVISO] Ya existe un administrador en el sistema")
                print(f"   Usuario: {admin_exists.username}")
                print(f"   Email: {admin_exists.email}\n")
                return
            
            print("\n" + "="*50)
            print("   CREAR ADMINISTRADOR DEL SISTEMA")
            print("="*50 + "\n")
            
            username = input("Usuario: ").strip()
            email = input("Email: ").strip()
            password = input("Contrasena: ").strip()
            full_name = input("Nombre completo (opcional): ").strip()
            
            if not username or not email or not password:
                print("\n[ERROR] Usuario, email y contrasena son obligatorios\n")
                return
            
            if len(password) < 4:
                print("\n[ERROR] La contrasena debe tener al menos 4 caracteres\n")
                return
            
            # Verificar si ya existe el username o email
            existing = session.exec(
                select(User).where((User.username == username) | (User.email == email))
            ).first()
            
            if existing:
                print(f"\n[ERROR] Ya existe un usuario con username '{username}' o email '{email}'\n")
                return
            
            hashed = hash_password(password)
            
            nuevo_admin = User(
                username=username,
                email=email,
                hashed_password=hashed,
                full_name=full_name if full_name else None,
                is_active=True,
                is_admin=True,
                password_version=1,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            session.add(nuevo_admin)
            session.commit()
            
            print("\n" + "="*50)
            print("   [OK] ADMIN CREADO EXITOSAMENTE")
            print("="*50)
            print(f"   ID: {nuevo_admin.id}")
            print(f"   Usuario: {nuevo_admin.username}")
            print(f"   Email: {nuevo_admin.email}")
            print(f"   Nombre: {nuevo_admin.full_name or 'No especificado'}")
            print(f"   Rol: Administrador")
            print("="*50 + "\n")
            
    except Exception as e:
        print(f"\n[ERROR] {e}\n")
    finally:
        engine.dispose()
        print("[INFO] Conexiones cerradas correctamente")

if __name__ == "__main__":
    crear_admin()