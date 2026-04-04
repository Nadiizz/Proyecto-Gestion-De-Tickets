# 🚀 Guía de Instalación y Despliegue

## Requisitos Previos

- Python 3.10+
- PostgreSQL 14+
- pip (gestor de paquetes Python)
- Git

---

## 1. Clonar el Repositorio

```bash
git clone https://github.com/Nadiizz/Proyecto-Gestion-De-Tickets.git
cd Proyecto-Gestion-De-Tickets
```

---

## 2. Crear Entorno Virtual

```bash
# Windows
python -m venv env
.\env\Scripts\activate

# Linux/Mac
python3 -m venv env
source env/bin/activate
```

---

## 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

---

## 4. Configurar Base de Datos PostgreSQL

```sql
-- Conectar a PostgreSQL como superusuario
psql -U postgres

-- Crear base de datos
CREATE DATABASE ticket_coyahue;

-- Verificar
\l
```

---

## 5. Configurar Variables de Entorno

Crear archivo `.env` en la raíz del proyecto:

```env
# Django
SECRET_KEY=django-insecure-genera-tu-propia-clave-secreta-aqui
DEBUG=True
DB_PASSWORD=tu_password_de_postgres

# Email (Gmail SMTP)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu_correo@gmail.com
EMAIL_HOST_PASSWORD=xxxx xxxx xxxx xxxx
DEFAULT_FROM_EMAIL=Sistema Tickets <noreply@coyahue.com>

# WhatsApp (Twilio) - Opcional
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

### Obtener App Password de Gmail

1. Ve a [myaccount.google.com](https://myaccount.google.com)
2. Seguridad → Verificación en 2 pasos (activar)
3. Seguridad → Contraseñas de aplicaciones
4. Seleccionar "Correo" y "Ordenador Windows"
5. Copiar la contraseña de 16 caracteres

---

## 6. Ejecutar Migraciones

```bash
python manage.py migrate
```

---

## 7. Crear Grupos de Usuarios

```bash
python manage.py shell
```

```python
from django.contrib.auth.models import Group

# Crear grupos
Group.objects.get_or_create(name='Administrador')
Group.objects.get_or_create(name='Técnico')
Group.objects.get_or_create(name='Usuario')

exit()
```

---

## 8. Crear Superusuario

```bash
python manage.py createsuperuser
```

Seguir las instrucciones en pantalla.

---

## 9. Poblar Datos de Ejemplo (Opcional)

```bash
# FAQs de ejemplo
python manage.py poblar_faqs
```

---

## 10. Ejecutar Servidor de Desarrollo

```bash
python manage.py runserver
```

Acceder a: http://127.0.0.1:8000

---

## 11. Configuración de Producción

### Cambios en `.env`

```env
DEBUG=False
SECRET_KEY=genera-una-clave-segura-de-50-caracteres
```

### Cambios en `settings.py`

```python
ALLOWED_HOSTS = ['tu-dominio.com', 'www.tu-dominio.com']

# Seguridad
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
```

### Archivos Estáticos

```bash
python manage.py collectstatic
```

---

## Solución de Problemas Comunes

### Error: "No module named 'psycopg2'"

```bash
pip install psycopg2-binary
```

### Error: "FATAL: password authentication failed"

Verificar que `DB_PASSWORD` en `.env` coincida con la contraseña de PostgreSQL.

### Error: "Connection refused" (Email)

1. Verificar que Gmail tenga verificación en 2 pasos
2. Usar App Password, no la contraseña normal
3. Verificar configuración de puerto (587 para TLS)

### Error: "Twilio authentication error"

1. Verificar TWILIO_ACCOUNT_SID y TWILIO_AUTH_TOKEN
2. Asegurarse de que la cuenta Twilio esté activa
3. Para sandbox: el destinatario debe enviar "join <codigo>" primero

---

## Estructura de Directorios Necesarios

El proyecto necesita estas carpetas (se crean automáticamente):

```
Proyecto-Gestion-De-Tickets/
├── logs/               # Archivos de log
├── media/              # Archivos subidos
│   ├── tickets/
│   ├── comentarios/
│   ├── fotos_perfil/
│   └── faqs/
└── static/             # Archivos estáticos
```

---

## Comandos Útiles

```bash
# Verificar proyecto
python manage.py check

# Ver migraciones pendientes
python manage.py showmigrations

# Crear nueva migración
python manage.py makemigrations

# Resetear base de datos (¡CUIDADO!)
python manage.py flush

# Shell interactivo
python manage.py shell

# Crear backup de BD
pg_dump -U postgres ticket_coyahue > backup.sql
```
