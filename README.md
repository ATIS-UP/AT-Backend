# Sistema de Alertas Tempranas - Backend

API REST desarrollada con FastAPI para el Sistema de Alertas Tempranas de la Universidad de Pamplona.

## Requisitos Previos

- Python 3.14+
- PostgreSQL (Neon Database)

## Instalación

1. Clonar el repositorio y acceder al directorio:
```bash
cd AT-Backend
```

2. Crear un entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Instalar psycopg2 (requerido para PostgreSQL):
```bash
pip install psycopg2-binary
```

## Configuración

1. Copiar el archivo de ejemplo de configuración:
```bash
cp .env.example .env
```

2. Editar `.env` con los valores correspondientes:

### Variables de entorno requeridas:

```env
# Database (Neon PostgreSQL)
DATABASE_URL=postgresql://user:password@host.neon.tech/neondb?sslmode=require

# JWT Configuration
JWT_SECRET_KEY=your_super_secret_key_min_32_characters
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Fernet Encryption (datos sensibles)
FERNET_KEY=your_fernet_key_here

# App Configuration
APP_NAME=Sistema de Alertas Tempranas
APP_VERSION=1.0.0
DEBUG=false
```

### Generar claves de seguridad:

```bash
# Generar JWT_SECRET_KEY (32+ caracteres)
openssl rand -hex 32

# Generar FERNET_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Ejecutar el Servidor

### Desarrollo:
```bash
uvicorn app.main:app --reload --port 8000
```

### Producción:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

El servidor estará disponible en:
- API: http://localhost:8000
- Documentación Swagger: http://localhost:8000/docs
- Documentación ReDoc: http://localhost:8000/redoc

## Inicializar Base de Datos

Ejecutar el script de seed para crear datos iniciales:
```bash
python seed.py
```

Esto creará:
- 29 permisos del sistema
- 3 usuarios de prueba (admin, docente, apoyo)

## Usuarios de Prueba

| Email | Contraseña | Rol |
|-------|------------|-----|
| admin@unipamplona.edu.co | Admin123! | ADMINISTRADOR |
| docente@unipamplona.edu.co | Docente123! | DOCENTE |
| apoyo@unipamplona.edu.co | Apoyo123! | APOYO |
| pruebas@unipamplona.edu.co | Pruebas123! | DOCENTE |

## Estructura del Proyecto

```
AT-Backend/
├── app/
│   ├── config.py          # Configuración del proyecto
│   ├── database.py       # Conexión a la base de datos
│   ├── main.py           # Aplicación FastAPI principal
│   ├── models/           # Modelos SQLAlchemy
│   │   ├── user.py       # Modelo de usuario
│   │   ├── estudiante.py # Modelo de estudiante
│   │   ├── alerta.py    # Modelo de alertas
│   │   └── sistema.py    # Modelos del sistema
│   ├── routers/         # Endpoints de la API
│   │   ├── auth.py      # Autenticación
│   │   ├── estudiantes.py # Gestión de estudiantes
│   │   ├── alertas.py   # Gestión de alertas
│   │   ├── admin.py     # Administración
│   │   └── dashboard.py # Dashboard
│   ├── schemas/         # Schemas Pydantic
│   │   ├── auth.py      # Schemas de autenticación
│   │   ├── estudiante.py # Schemas de estudiantes
│   │   └── alerta.py    # Schemas de alertas
│   └── utils/           # Utilidades
│       ├── auth.py      # Funciones JWT
│       ├── security.py # Encriptación
│       ├── permisos.py # Gestión de permisos
│       └── audit.py    # Auditoría
├── seed.py              # Script de inicialización
├── requirements.txt    # Dependencias Python
└── .env.example         # Ejemplo de configuración
```

## Permisos del Sistema

El sistema cuenta con 29 permisos granulares:

### Administrador y Docente
- Gestionan usuarios, estudiantes, alertas, actividades
- Acceso completo a encuestas, artefactos y parametrización

### Apoyo
- Solo `create_estudiante` - Crear estudiantes
- Solo `crear_alerta` - Crear alertas

## Endpoints Principales

### Autenticación
- `POST /api/auth/login` - Iniciar sesión
- `POST /api/auth/logout` - Cerrar sesión
- `POST /api/auth/refresh` - Renovar token

### Estudiantes
- `GET /api/estudiantes` - Listar estudiantes
- `POST /api/estudiantes` - Crear estudiante

### Alertas
- `GET /api/alertas` - Listar alertas
- `POST /api/alertas` - Crear alerta
- `GET /api/alertas/stats` - Estadísticas

### Administración
- `GET /api/admin/usuarios` - Listar usuarios
- `POST /api/admin/usuarios` - Crear usuario
- `GET /api/admin/permisos` - Listar permisos

## Tecnologías

- **Framework**: FastAPI
- **ORM**: SQLAlchemy 2.0
- **Base de Datos**: PostgreSQL (Neon)
- **Autenticación**: JWT con refresh tokens
- **Seguridad**: bcrypt, Fernet encryption
- **Validación**: Pydantic v2

## Notas

- El sistema está diseñado para Python 3.14+
- Requiere pydantic==2.13.4 por compatibilidad
- Usa CORS para permitir conexiones desde el frontend
- Incluye rate limiting para protección de login