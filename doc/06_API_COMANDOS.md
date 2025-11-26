# API y Comandos - Sistema de Gestión de Tickets

## 🔧 Comandos de Gestión Django

### Comandos Estándar de Django

#### Gestión de Base de Datos
```bash
# Crear migraciones
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate

# Ver SQL de una migración
python manage.py sqlmigrate tickets 0001

# Verificar problemas con migraciones
python manage.py check

# Limpiar sesiones expiradas
python manage.py clearsessions
```

#### Gestión de Usuarios
```bash
# Crear superusuario
python manage.py createsuperuser

# Cambiar contraseña de usuario
python manage.py changepassword username
```

#### Servidor de Desarrollo
```bash
# Iniciar servidor (puerto 8000 por defecto)
python manage.py runserver

# Servidor en puerto específico
python manage.py runserver 8080

# Servidor accesible desde red
python manage.py runserver 0.0.0.0:8000
```

#### Shell Interactivo
```bash
# Shell de Django
python manage.py shell

# Shell de Python estándar
python manage.py shell --plain
```

Ejemplos en el shell:
```python
from tickets.models import Ticket, Comentario
from django.contrib.auth.models import User

# Obtener todos los tickets
tickets = Ticket.objects.all()

# Filtrar tickets
tickets_criticos = Ticket.objects.filter(prioridad='critica')

# Crear un ticket
user = User.objects.get(username='admin')
ticket = Ticket.objects.create(
    titulo='Test desde shell',
    descripcion='Prueba',
    creador=user,
    prioridad='media'
)

# Actualizar un ticket
ticket.estado = 'en_progreso'
ticket.save()

# Eliminar un ticket
ticket.delete()
```

#### Archivos Estáticos
```bash
# Recolectar archivos estáticos para producción
python manage.py collectstatic

# Limpiar archivos estáticos
python manage.py collectstatic --clear
```

---

## 🤖 Comandos Personalizados del Sistema

### verificar_sla
**Ruta**: `tickets/management/commands/verificar_sla.py`

**Descripción**: Verifica tickets con SLA vencido y los marca como "tiempo_excedido"

**Uso**:
```bash
python manage.py verificar_sla
```

**Salida**:
```
Verificando tickets con SLA vencido...
✓ Ticket #123 marcado como tiempo excedido
✓ Ticket #456 marcado como tiempo excedido
Total de tickets actualizados: 2
```

**Código**:
```python
from django.core.management.base import BaseCommand
from django.utils import timezone
from tickets.models import Ticket, HistorialEstado

class Command(BaseCommand):
    help = 'Verifica y actualiza tickets con SLA vencido'
    
    def handle(self, *args, **options):
        now = timezone.now()
        
        # Buscar tickets con SLA vencido
        tickets_vencidos = Ticket.objects.filter(
            tiempo_limite_resolucion__lt=now,
            estado__in=['pendiente', 'en_progreso']
        )
        
        count = 0
        for ticket in tickets_vencidos:
            estado_anterior = ticket.estado
            ticket.estado = 'tiempo_excedido'
            ticket.save()
            
            # Registrar en historial
            HistorialEstado.objects.create(
                ticket=ticket,
                estado_anterior=estado_anterior,
                estado_nuevo='tiempo_excedido',
                cambiado_por=None,  # Sistema automático
                comentario='SLA excedido - Actualización automática'
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Ticket #{ticket.id} marcado como tiempo excedido'
                )
            )
            count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'\nTotal de tickets actualizados: {count}')
        )
```

**Programación Automática**:

**Windows (Task Scheduler)**:
1. Abrir "Programador de tareas"
2. Crear tarea básica:
   - Nombre: "Verificar SLA Tickets"
   - Desencadenador: Repetir cada 1 hora
   - Acción: Iniciar programa
     * Programa: `C:\ruta\al\env\Scripts\python.exe`
     * Argumentos: `manage.py verificar_sla`
     * Directorio: `C:\ruta\al\proyecto`

**Linux (Crontab)**:
```bash
# Editar crontab
crontab -e

# Agregar línea para ejecutar cada hora
0 * * * * cd /ruta/proyecto && /ruta/env/bin/python manage.py verificar_sla >> /var/log/sla_check.log 2>&1
```

---

## 📊 Queries Útiles del ORM

### Filtros Básicos

```python
# Filtrar por campo exacto
Ticket.objects.filter(estado='pendiente')

# Filtrar por múltiples valores (OR)
Ticket.objects.filter(prioridad__in=['alta', 'critica'])

# Excluir
Ticket.objects.exclude(estado='cerrado')

# Combinar filtros (AND)
Ticket.objects.filter(
    estado='pendiente',
    prioridad='alta'
)
```

### Búsquedas de Texto

```python
from django.db.models import Q

# Búsqueda insensible a mayúsculas
Ticket.objects.filter(titulo__icontains='impresora')

# Búsqueda que empieza con
Ticket.objects.filter(titulo__istartswith='problema')

# Búsqueda con múltiples campos (OR)
Ticket.objects.filter(
    Q(titulo__icontains='red') | Q(descripcion__icontains='red')
)

# Búsqueda compleja
Ticket.objects.filter(
    Q(prioridad='alta') &
    (Q(titulo__icontains='servidor') | Q(descripcion__icontains='servidor'))
)
```

### Ordenamiento

```python
# Orden ascendente
Ticket.objects.order_by('fecha_creacion')

# Orden descendente
Ticket.objects.order_by('-fecha_creacion')

# Múltiples criterios
Ticket.objects.order_by('-prioridad', 'fecha_creacion')

# Orden aleatorio
Ticket.objects.order_by('?')
```

### Limitación de Resultados

```python
# Primeros 10
Ticket.objects.all()[:10]

# Del 10 al 20 (paginación)
Ticket.objects.all()[10:20]

# Primer resultado
Ticket.objects.first()

# Último resultado
Ticket.objects.last()

# Obtener uno o error 404
from django.shortcuts import get_object_or_404
ticket = get_object_or_404(Ticket, id=123)
```

### Agregaciones

```python
from django.db.models import Count, Avg, Sum, Max, Min

# Contar tickets
total = Ticket.objects.count()

# Contar por estado
Ticket.objects.filter(estado='pendiente').count()

# Promedio de calificaciones
promedio = Ticket.objects.aggregate(
    promedio_satisfaccion=Avg('calificacion_satisfaccion')
)['promedio_satisfaccion']

# Múltiples agregaciones
stats = Ticket.objects.aggregate(
    total=Count('id'),
    promedio_calificacion=Avg('calificacion_satisfaccion'),
    max_id=Max('id'),
    min_id=Min('id')
)
```

### Anotaciones (agregar campos calculados)

```python
from django.db.models import Count, Q

# Contar comentarios por ticket
tickets = Ticket.objects.annotate(
    num_comentarios=Count('comentarios')
)

# Usar el campo anotado
for ticket in tickets:
    print(f"Ticket {ticket.id} tiene {ticket.num_comentarios} comentarios")

# Contar con condición
tickets = Ticket.objects.annotate(
    tickets_resueltos=Count('id', filter=Q(estado='resuelto'))
)
```

### Agrupación (values + annotate)

```python
# Tickets por estado
Ticket.objects.values('estado').annotate(
    total=Count('id')
).order_by('-total')
# Resultado: [{'estado': 'pendiente', 'total': 15}, ...]

# Tickets por usuario
Ticket.objects.values(
    'creador__username'
).annotate(
    total_creados=Count('id')
).order_by('-total_creados')

# Tickets por mes
from django.db.models.functions import TruncMonth

Ticket.objects.annotate(
    mes=TruncMonth('fecha_creacion')
).values('mes').annotate(
    total=Count('id')
).order_by('mes')
```

### Relaciones

```python
# Forward FK (select_related)
tickets = Ticket.objects.select_related(
    'creador',
    'asignado_a'
).all()

# Reverse FK y M2M (prefetch_related)
tickets = Ticket.objects.prefetch_related(
    'comentarios',
    'archivos'
).all()

# Acceder a través de relaciones
ticket.comentarios.all()
ticket.comentarios.filter(autor=user)
ticket.comentarios.count()
```

### Fechas

```python
from django.utils import timezone
from datetime import timedelta

# Filtrar por rango de fechas
hoy = timezone.now()
hace_7_dias = hoy - timedelta(days=7)

tickets_recientes = Ticket.objects.filter(
    fecha_creacion__gte=hace_7_dias
)

# Por año
tickets_2025 = Ticket.objects.filter(
    fecha_creacion__year=2025
)

# Por mes
tickets_enero = Ticket.objects.filter(
    fecha_creacion__month=1
)

# Comparar fechas
tickets_sla_vencido = Ticket.objects.filter(
    tiempo_limite_resolucion__lt=timezone.now()
)
```

### Actualización en Masa

```python
# Actualizar múltiples registros
Ticket.objects.filter(
    estado='pendiente',
    prioridad='baja'
).update(prioridad='media')

# Incrementar valor
from django.db.models import F

Ticket.objects.filter(
    id__in=[1, 2, 3]
).update(numero_escalamientos=F('numero_escalamientos') + 1)
```

### Eliminación

```python
# Eliminar tickets antiguos
antiguos = Ticket.objects.filter(
    fecha_creacion__lt=timezone.now() - timedelta(days=365),
    estado='cerrado'
)
count = antiguos.count()
antiguos.delete()

# Eliminar uno específico
ticket = Ticket.objects.get(id=123)
ticket.delete()
```

---

## 📡 URLs del Sistema

### Mapeo Completo de URLs

```python
# ticket_coyahue/urls.py
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('tickets.urls')),
]

# tickets/urls.py
urlpatterns = [
    # Autenticación
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('registro/', views.registro_usuario, name='registro'),
    
    # Gestión de Tickets
    path('', views.ticket_list, name='ticket_list'),
    path('nuevo/', views.crear_ticket, name='crear_ticket'),
    path('ticket/<int:ticket_id>/', views.ticket_detalle, name='ticket_detalle'),
    path('asignar/<int:ticket_id>/', views.asignar_ticket, name='asignar_ticket'),
    path('estado/<int:ticket_id>/', views.cambiar_estado, name='cambiar_estado'),
    
    # Métricas
    path('metricas/', views.metricas, name='metricas'),
    
    # Calificaciones
    path('calificar/<int:ticket_id>/', views.calificar_ticket, name='calificar_ticket'),
    
    # Vista Personal
    path('mis-tickets/', views.mis_tickets, name='mis_tickets'),
]
```

### Generación de URLs en Templates

```html
<!-- URL simple -->
<a href="{% url 'ticket_list' %}">Lista de Tickets</a>

<!-- URL con parámetros -->
<a href="{% url 'ticket_detalle' ticket.id %}">Ver Ticket</a>

<!-- URL con query string -->
<a href="{% url 'metricas' %}?dias=30">Métricas 30 días</a>
```

### Generación de URLs en Python

```python
from django.urls import reverse

# URL simple
url = reverse('ticket_list')
# Resultado: '/'

# URL con parámetros
url = reverse('ticket_detalle', args=[123])
# Resultado: '/ticket/123/'

# URL con kwargs
url = reverse('ticket_detalle', kwargs={'ticket_id': 123})
# Resultado: '/ticket/123/'

# Redirect
from django.shortcuts import redirect
return redirect('ticket_list')
return redirect('ticket_detalle', ticket_id=ticket.id)
```

---

## 🔒 Permisos y Decoradores

### Decoradores Disponibles

```python
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.decorators import permission_required

# Requiere autenticación
@login_required
def mi_vista(request):
    pass

# Requiere condición específica
@user_passes_test(es_admin)
def vista_admin(request):
    pass

# Requiere permiso específico
@permission_required('tickets.add_ticket')
def crear_ticket(request):
    pass

# Combinar múltiples decoradores
@login_required
@user_passes_test(es_tecnico)
def vista_tecnico(request):
    pass
```

### Funciones de Verificación

```python
def es_admin(user):
    """Verifica si el usuario es administrador"""
    return user.groups.filter(name='Administrador').exists()

def es_tecnico(user):
    """Verifica si el usuario es técnico"""
    return user.groups.filter(name='Técnico').exists()

def es_usuario(user):
    """Verifica si el usuario es usuario regular"""
    return user.groups.filter(name='Usuario').exists()

def puede_editar_ticket(user, ticket):
    """Verifica si el usuario puede editar el ticket"""
    return (
        user == ticket.creador or
        user == ticket.asignado_a or
        es_admin(user)
    )
```

---

## 📢 API REST de Notificaciones (✨ NEW)

### Endpoints Disponibles

#### 1. Obtener Todas las Notificaciones
**Endpoint**: `GET /api/notificaciones/`

**Autenticación**: Requerida (Login)

**Parámetros Query** (Opcionales):
```
?leidas=true      - Mostrar solo leídas
?leidas=false     - Mostrar solo no leídas
?limite=10        - Limitar resultados (default: 20)
?offset=0         - Paginación
```

**cURL**:
```bash
curl -X GET "http://localhost:8000/api/notificaciones/" \
  -H "Cookie: sessionid=abc123..."
```

**Respuesta Exitosa (200)**:
```json
{
  "total": 15,
  "notificaciones": [
    {
      "id": 42,
      "titulo": "Ticket Asignado",
      "mensaje": "Se te ha asignado el ticket #1005",
      "tipo": "ticket_asignado",
      "prioridad": "media",
      "leida": false,
      "fecha_creacion": "2025-01-15T10:30:00Z",
      "ticket": {
        "id": 1005,
        "titulo": "Problema con impresora",
        "enlace": "/tickets/1005/"
      }
    }
  ]
}
```

---

#### 2. Obtener Notificaciones No Leídas
**Endpoint**: `GET /api/notificaciones/nuevas/`

**Autenticación**: Requerida (Login)

**Descripción**: Retorna solo las notificaciones no leídas del usuario actual

**cURL**:
```bash
curl -X GET "http://localhost:8000/api/notificaciones/nuevas/" \
  -H "Cookie: sessionid=abc123..."
```

**Respuesta Exitosa (200)**:
```json
{
  "total": 3,
  "sin_leer": 3,
  "notificaciones": [
    {
      "id": 42,
      "titulo": "Ticket Asignado",
      "tipo": "ticket_asignado",
      "prioridad": "alta",
      "leida": false,
      "fecha_creacion": "2025-01-15T10:30:00Z"
    }
  ]
}
```

---

#### 3. Marcar Notificación como Leída
**Endpoint**: `POST /api/notificaciones/<id>/marcar-leida/`

**Autenticación**: Requerida (Login)

**Método**: POST

**Body**: Vacío

**cURL**:
```bash
curl -X POST "http://localhost:8000/api/notificaciones/42/marcar-leida/" \
  -H "Cookie: sessionid=abc123..."
```

**Respuesta Exitosa (200)**:
```json
{
  "success": true,
  "mensaje": "Notificación marcada como leída",
  "notificacion": {
    "id": 42,
    "leida": true,
    "fecha_leida": "2025-01-15T10:35:00Z"
  }
}
```

**Errores Posibles**:
- **404 Not Found**: Notificación no existe
- **403 Forbidden**: No tienes permisos para esta notificación

---

#### 4. Marcar Todas las Notificaciones como Leídas
**Endpoint**: `POST /api/notificaciones/marcar-todas-leidas/`

**Autenticación**: Requerida (Login)

**Descripción**: Marca todas las notificaciones del usuario actual como leídas

**Body**: Vacío

**cURL**:
```bash
curl -X POST "http://localhost:8000/api/notificaciones/marcar-todas-leidas/" \
  -H "Cookie: sessionid=abc123..."
```

**Respuesta Exitosa (200)**:
```json
{
  "success": true,
  "mensaje": "Todas las notificaciones han sido marcadas como leídas",
  "actualizadas": 15,
  "timestamp": "2025-01-15T10:35:00Z"
}
```

---

### Códigos de Estado HTTP

| Código | Significado | Descripción |
|--------|------------|-------------|
| 200 | OK | Solicitud exitosa |
| 201 | Created | Recurso creado |
| 400 | Bad Request | Datos inválidos |
| 401 | Unauthorized | No autenticado |
| 403 | Forbidden | No autorizado |
| 404 | Not Found | Recurso no encontrado |
| 500 | Server Error | Error interno |

---

### Ejemplo: JavaScript Fetch

```javascript
// Obtener notificaciones nuevas
async function obtenerNotificacionesNuevas() {
  try {
    const response = await fetch('/api/notificaciones/nuevas/');
    const data = await response.json();
    
    if (response.ok) {
      console.log(`Tienes ${data.sin_leer} notificaciones sin leer`);
      data.notificaciones.forEach(notif => {
        console.log(`- ${notif.titulo}`);
      });
    }
  } catch (error) {
    console.error('Error:', error);
  }
}

// Marcar como leída
async function marcarComoLeida(notificacionId) {
  try {
    const response = await fetch(
      `/api/notificaciones/${notificacionId}/marcar-leida/`,
      { method: 'POST' }
    );
    const data = await response.json();
    
    if (response.ok) {
      console.log('Notificación marcada como leída');
    }
  } catch (error) {
    console.error('Error:', error);
  }
}

// Marcar todas como leídas
async function marcarTodasLeidas() {
  try {
    const response = await fetch(
      '/api/notificaciones/marcar-todas-leidas/',
      { method: 'POST' }
    );
    const data = await response.json();
    
    if (response.ok) {
      console.log(`${data.actualizadas} notificaciones marcadas como leídas`);
    }
  } catch (error) {
    console.error('Error:', error);
  }
}
```

---

### Notas Importantes

- ✅ Todos los endpoints requieren autenticación
- ✅ Solo puedes ver/editar tus propias notificaciones
- ✅ Las notificaciones se crean automáticamente en eventos del sistema
- ✅ Los datos se sincronizan en tiempo real
- ✅ Ver [Sistema de Notificaciones](SISTEMA_NOTIFICACIONES.md) para más detalles

---

## 📤 Exportación de Datos

### Exportar a CSV

```python
import csv
from django.http import HttpResponse

def exportar_tickets_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="tickets.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['ID', 'Título', 'Estado', 'Prioridad', 'Creado'])
    
    tickets = Ticket.objects.all()
    for ticket in tickets:
        writer.writerow([
            ticket.id,
            ticket.titulo,
            ticket.estado,
            ticket.prioridad,
            ticket.fecha_creacion.strftime('%Y-%m-%d')
        ])
    
    return response
```

### Exportar a Excel (openpyxl)

```python
from openpyxl import Workbook
from django.http import HttpResponse

def exportar_tickets_excel(request):
    wb = Workbook()
    ws = wb.active
    ws.title = "Tickets"
    
    # Encabezados
    ws.append(['ID', 'Título', 'Estado', 'Prioridad', 'Creado'])
    
    # Datos
    tickets = Ticket.objects.all()
    for ticket in tickets:
        ws.append([
            ticket.id,
            ticket.titulo,
            ticket.estado,
            ticket.prioridad,
            ticket.fecha_creacion
        ])
    
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=tickets.xlsx'
    wb.save(response)
    
    return response
```

### Exportar a PDF (reportlab)

```python
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.http import HttpResponse

def exportar_ticket_pdf(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ticket_{ticket.id}.pdf"'
    
    p = canvas.Canvas(response, pagesize=letter)
    
    # Título
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 750, f"Ticket #{ticket.id}")
    
    # Contenido
    p.setFont("Helvetica", 12)
    p.drawString(100, 720, f"Título: {ticket.titulo}")
    p.drawString(100, 700, f"Estado: {ticket.get_estado_display()}")
    p.drawString(100, 680, f"Prioridad: {ticket.get_prioridad_display()}")
    
    p.showPage()
    p.save()
    
    return response
```

---

## 🔍 Debugging y Profiling

### Django Debug Queries

```python
from django.db import connection

# Ver todas las queries ejecutadas
print(len(connection.queries))
print(connection.queries)

# Resetear contador
from django.db import reset_queries
reset_queries()
```

### Medir Tiempo de Ejecución

```python
import time
from django.db import connection, reset_queries

reset_queries()
start = time.time()

# Tu código aquí
tickets = Ticket.objects.select_related('creador').all()
list(tickets)  # Forzar evaluación

end = time.time()
print(f"Tiempo: {end - start:.4f}s")
print(f"Queries: {len(connection.queries)}")
```

---

## 📚 Recursos Útiles

### Documentación Oficial
- Django: https://docs.djangoproject.com/
- PostgreSQL: https://www.postgresql.org/docs/
- Bootstrap 4: https://getbootstrap.com/docs/4.6/

### Paquetes Útiles
- Django Debug Toolbar: https://django-debug-toolbar.readthedocs.io/
- Django Extensions: https://django-extensions.readthedocs.io/
- Django REST Framework: https://www.django-rest-framework.org/

---

**Documentación completa. Ver [README principal](../README.md) para más información.**
