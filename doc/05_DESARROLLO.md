# Guía de Desarrollo - Sistema de Gestión de Tickets

## 🚀 Configuración del Entorno de Desarrollo

### Prerequisitos
- Python 3.13+
- PostgreSQL 12+
- Git
- Editor de código (VS Code recomendado)

### Setup Inicial

#### 1. Clonar el Repositorio
```bash
git clone https://github.com/Nadiizz/Proyecto-Gestion-De-Tickets.git
cd Proyecto-Gestion-De-Tickets
```

#### 2. Crear Entorno Virtual
```bash
python -m venv env
```

#### 3. Activar Entorno Virtual
```bash
# Windows
env\Scripts\activate

# Linux/Mac
source env/bin/activate
```

#### 4. Instalar Dependencias
```bash
pip install -r requirements.txt
```

#### 5. Configurar Base de Datos
```sql
-- Conectarse a PostgreSQL
psql -U postgres

-- Crear base de datos
CREATE DATABASE tickets_db;
CREATE USER tickets_user WITH PASSWORD 'dev_password';
GRANT ALL PRIVILEGES ON DATABASE tickets_db TO tickets_user;
```

#### 6. Configurar Variables de Entorno
Crear archivo `.env` en la raíz:
```env
SECRET_KEY=tu-clave-secreta-de-desarrollo
DEBUG=True
DATABASE_NAME=tickets_db
DATABASE_USER=tickets_user
DATABASE_PASSWORD=dev_password
DATABASE_HOST=localhost
DATABASE_PORT=5432
```

#### 7. Aplicar Migraciones
```bash
python manage.py migrate
```

#### 8. Crear Superusuario
```bash
python manage.py createsuperuser
```

#### 9. Crear Grupos
```python
python manage.py shell

from django.contrib.auth.models import Group
Group.objects.create(name='Administrador')
Group.objects.create(name='Técnico')
Group.objects.create(name='Usuario')
exit()
```

#### 10. Ejecutar Servidor de Desarrollo
```bash
python manage.py runserver
```

Acceder a: `http://127.0.0.1:8000`

---

## 📁 Estructura del Código

### Convenciones de Nomenclatura

#### Archivos Python
- **Modelos**: `PascalCase` (ej: `Ticket`, `Comentario`)
- **Funciones/Métodos**: `snake_case` (ej: `crear_ticket()`, `calcular_tiempo_resolucion()`)
- **Constantes**: `UPPER_SNAKE_CASE` (ej: `TICKETS_POR_PAGINA`, `DIAS_METRICAS_DEFAULT`)
- **Variables**: `snake_case` (ej: `tickets_totales`, `usuario_mas_activo`)

#### Templates
- **Archivos**: `snake_case.html` (ej: `ticket_list.html`, `base_intranet.html`)
- **Bloques**: `{% block nombre_bloque %}{% endblock %}`
- **IDs CSS**: `kebab-case` (ej: `ticket-card`, `metric-icon`)
- **Clases CSS**: `kebab-case` (ej: `.ticket-header`, `.btn-primary`)

#### JavaScript
- **Funciones**: `camelCase` (ej: `cambiarPeriodo()`, `aplicarFiltros()`)
- **Constantes**: `UPPER_SNAKE_CASE`
- **Variables**: `camelCase`

---

## 🔧 Flujo de Trabajo con Git

### Branching Strategy

```
main
  └── develop
       ├── feature/nueva-funcionalidad
       ├── bugfix/corregir-error
       └── hotfix/emergencia
```

### Crear una Nueva Feature
```bash
# Crear branch desde develop
git checkout develop
git pull origin develop
git checkout -b feature/nombre-descriptivo

# Trabajar en la feature
git add .
git commit -m "feat: descripción clara del cambio"

# Push a repositorio
git push origin feature/nombre-descriptivo

# Crear Pull Request en GitHub
```

### Convenciones de Commits

Usar **Conventional Commits**:

```bash
# Nueva funcionalidad
git commit -m "feat: agregar sistema de notificaciones por email"

# Corrección de bug
git commit -m "fix: corregir cálculo de SLA en tickets urgentes"

# Actualización de documentación
git commit -m "docs: actualizar README con instrucciones de instalación"

# Refactoring de código
git commit -m "refactor: optimizar queries en vista de métricas"

# Estilos (CSS/formato)
git commit -m "style: mejorar diseño responsive de dashboard"

# Tests
git commit -m "test: agregar tests para modelo Ticket"

# Cambios en build/configuración
git commit -m "chore: actualizar dependencias de requirements.txt"
```

---

## 🧪 Testing

### Ejecutar Tests
```bash
python manage.py test tickets
```

### Crear Tests para un Modelo
```python
# tickets/tests.py
from django.test import TestCase
from django.contrib.auth.models import User
from .models import Ticket

class TicketModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@coyahue.com',
            password='testpass123'
        )
    
    def test_crear_ticket(self):
        """Verifica que se puede crear un ticket correctamente"""
        ticket = Ticket.objects.create(
            titulo='Test Ticket',
            descripcion='Descripción de prueba',
            creador=self.user,
            prioridad='media',
            tipo='incidencia'
        )
        self.assertEqual(ticket.estado, 'pendiente')
        self.assertEqual(str(ticket), f'Ticket #{ticket.id}: Test Ticket')
    
    def test_calcular_tiempo_limite_sla(self):
        """Verifica el cálculo correcto del SLA"""
        ticket = Ticket.objects.create(
            titulo='Test SLA',
            descripcion='Test',
            creador=self.user,
            prioridad='critica'
        )
        sla = ticket.calcular_tiempo_limite_sla()
        
        # Prioridad crítica = 4 horas
        diferencia = sla - ticket.fecha_creacion
        self.assertEqual(diferencia.total_seconds() / 3600, 4)
```

### Crear Tests para una Vista
```python
from django.test import TestCase, Client
from django.urls import reverse

class TicketViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@coyahue.com',
            password='testpass123'
        )
    
    def test_login_requerido(self):
        """Verifica que las vistas requieren autenticación"""
        response = self.client.get(reverse('ticket_list'))
        self.assertEqual(response.status_code, 302)  # Redirect a login
    
    def test_crear_ticket_post(self):
        """Verifica la creación de un ticket via POST"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(reverse('crear_ticket'), {
            'titulo': 'Nuevo Ticket',
            'descripcion': 'Descripción del problema',
            'tipo': 'incidencia',
            'area_afectada': 'IT'
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertTrue(
            Ticket.objects.filter(titulo='Nuevo Ticket').exists()
        )
```

---

## 📊 Mejores Prácticas

### Optimización de Queries

#### ❌ Malo: N+1 Problem
```python
# Genera 1 + N queries
tickets = Ticket.objects.all()
for ticket in tickets:
    print(ticket.creador.username)  # Query adicional por cada ticket
    print(ticket.asignado_a.username)  # Otra query más
```

#### ✅ Bueno: select_related
```python
# Solo 1 query con JOINs
tickets = Ticket.objects.select_related(
    'creador', 'asignado_a'
).all()

for ticket in tickets:
    print(ticket.creador.username)  # Sin query adicional
    print(ticket.asignado_a.username)  # Sin query adicional
```

#### ✅ Bueno: prefetch_related para relaciones M2N o reverse FK
```python
# Eficiente para comentarios (relación 1:N)
tickets = Ticket.objects.prefetch_related(
    'comentarios',
    'archivos'
).all()

for ticket in tickets:
    for comentario in ticket.comentarios.all():  # Sin queries adicionales
        print(comentario.contenido)
```

### Manejo de Transacciones

```python
from django.db import transaction

@transaction.atomic
def crear_ticket_con_archivos(titulo, descripcion, archivos, user):
    """
    Crea ticket y archivos en una transacción.
    Si falla cualquier operación, todo se revierte.
    """
    ticket = Ticket.objects.create(
        titulo=titulo,
        descripcion=descripcion,
        creador=user
    )
    
    for archivo in archivos:
        ArchivoTicket.objects.create(
            ticket=ticket,
            archivo=archivo
        )
    
    return ticket
```

### Seguridad

#### CSRF Protection
```html
<!-- Siempre incluir {% csrf_token %} en formularios POST -->
<form method="POST">
    {% csrf_token %}
    <!-- campos del formulario -->
</form>
```

#### Validación de Entrada
```python
# En forms.py
def clean_titulo(self):
    titulo = self.cleaned_data.get('titulo')
    
    # Validar longitud
    if len(titulo) < 5:
        raise ValidationError('El título debe tener al menos 5 caracteres')
    
    # Prevenir XSS (Django lo hace automáticamente, pero es buena práctica)
    from django.utils.html import escape
    titulo = escape(titulo)
    
    return titulo
```

#### Control de Acceso
```python
# Siempre verificar permisos
@login_required
@user_passes_test(es_admin)
def vista_sensible(request):
    # Solo admins pueden acceder
    pass

# Verificar ownership
def editar_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    # Verificar que el usuario es el creador o admin
    if request.user != ticket.creador and not es_admin(request.user):
        return HttpResponseForbidden()
    
    # ... resto de la lógica
```

---

## 🎨 Desarrollo de Frontend

### Agregar un Nuevo Componente CSS

1. Crear archivo CSS en `tickets/static/tickets/css/`:
```css
/* nuevo_componente.css */
.mi-componente {
    background: #fff;
    border-radius: 8px;
    padding: 1rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.mi-componente:hover {
    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    transform: translateY(-2px);
    transition: all 0.3s ease;
}
```

2. Incluir en el template:
```html
{% block extra_css %}
    <link rel="stylesheet"
          href="{% static 'tickets/css/nuevo_componente.css' %}">
{% endblock %}
```

### Agregar JavaScript Personalizado

```javascript
// tickets/static/tickets/js/mi_script.js
document.addEventListener('DOMContentLoaded', function() {
    // Código que se ejecuta cuando el DOM está listo
    
    const buttons = document.querySelectorAll('.mi-boton');
    buttons.forEach(button => {
        button.addEventListener('click', function() {
            // Lógica del evento
        });
    });
});
```

Incluir en template:
```html
{% block extra_js %}
    <script src="{% static 'tickets/js/mi_script.js' %}"></script>
{% endblock %}
```

---

## 🔄 Migraciones de Base de Datos

### Crear una Migración
```bash
# Después de modificar models.py
python manage.py makemigrations tickets
```

### Aplicar Migraciones
```bash
python manage.py migrate
```

### Ver SQL de una Migración
```bash
python manage.py sqlmigrate tickets 0001
```

### Revertir una Migración
```bash
python manage.py migrate tickets 0002  # Vuelve a la migración 0002
```

### Ejemplo: Agregar un Nuevo Campo
```python
# En models.py
class Ticket(models.Model):
    # ... campos existentes ...
    
    # Nuevo campo
    requiere_aprobacion = models.BooleanField(default=False)
```

```bash
python manage.py makemigrations tickets
python manage.py migrate
```

---

## 📝 Comandos de Gestión Personalizados

### Crear un Nuevo Comando

1. Crear estructura de directorios:
```
tickets/
└── management/
    ├── __init__.py
    └── commands/
        ├── __init__.py
        └── mi_comando.py
```

2. Implementar el comando:
```python
# tickets/management/commands/mi_comando.py
from django.core.management.base import BaseCommand
from tickets.models import Ticket

class Command(BaseCommand):
    help = 'Descripción de lo que hace el comando'
    
    def add_arguments(self, parser):
        # Argumentos opcionales
        parser.add_argument(
            '--dias',
            type=int,
            default=30,
            help='Número de días'
        )
    
    def handle(self, *args, **options):
        dias = options['dias']
        
        # Lógica del comando
        tickets = Ticket.objects.filter(...)
        
        self.stdout.write(
            self.style.SUCCESS(f'Procesados {tickets.count()} tickets')
        )
```

3. Ejecutar:
```bash
python manage.py mi_comando --dias=60
```

---

## 🐛 Debugging

### Usar Django Debug Toolbar

1. Instalar:
```bash
pip install django-debug-toolbar
```

2. Configurar en `settings.py`:
```python
INSTALLED_APPS = [
    # ...
    'debug_toolbar',
]

MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    # ...
]

INTERNAL_IPS = [
    '127.0.0.1',
]
```

3. URLs:
```python
# urls.py
from django.conf import settings

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
```

### Logging

```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
        },
    },
    'loggers': {
        'tickets': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
```

Usar en código:
```python
import logging

logger = logging.getLogger('tickets')

def mi_vista(request):
    logger.debug('Debug message')
    logger.info('Info message')
    logger.warning('Warning message')
    logger.error('Error message')
```

---

**Siguiente**: [API y Comandos →](06_API_COMANDOS.md)
