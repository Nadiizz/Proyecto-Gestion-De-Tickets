# Modelos de Datos - Sistema de Gestión de Tickets

## 📊 Diagrama de Relaciones

```
┌─────────────────────┐
│     auth_user       │
│  (Django builtin)   │
└──────┬──────┬───────┘
       │      │
       │      │ FK: asignado_a
       │      │
       │ FK: creador
       │      │
       ▼      ▼
┌──────────────────────────────────┐
│      tickets_ticket              │
│  ┌────────────────────────────┐  │
│  │ id (PK)                    │  │
│  │ titulo                     │  │
│  │ descripcion                │  │
│  │ estado                     │  │
│  │ prioridad                  │  │
│  │ tipo                       │  │
│  │ area_afectada              │  │
│  │ creador (FK → User)        │  │
│  │ asignado_a (FK → User)     │  │
│  │ fecha_creacion             │  │
│  │ fecha_actualizacion        │  │
│  │ fecha_cierre               │  │
│  │ fecha_asignacion           │  │
│  │ fecha_primera_respuesta    │  │
│  │ tiempo_limite_resolucion   │  │
│  │ fue_reabierto              │  │
│  │ numero_escalamientos       │  │
│  │ calificacion_satisfaccion  │  │
│  └────────────────────────────┘  │
└──────┬───────┬───────┬──────────┘
       │       │       │
       │       │       │ 1:N
       │       │       ▼
       │       │   ┌─────────────────────────┐
       │       │   │ tickets_archivoticket   │
       │       │   │  - archivo              │
       │       │   │  - nombre_archivo       │
       │       │   │  - fecha_subida         │
       │       │   └─────────────────────────┘
       │       │
       │       │ 1:N
       │       ▼
       │   ┌──────────────────────────────┐
       │   │ tickets_historialestado      │
       │   │  - estado_anterior           │
       │   │  - estado_nuevo              │
       │   │  - cambiado_por (FK → User)  │
       │   │  - fecha                     │
       │   │  - comentario                │
       │   └──────────────────────────────┘
       │
       │ 1:N
       ▼
┌─────────────────────────────┐
│  tickets_comentario         │
│  - contenido                │
│  - autor (FK → User)        │
│  - ticket (FK → Ticket)     │
│  - fecha                    │
└───────────┬─────────────────┘
            │
            │ 1:N
            ▼
┌──────────────────────────────────┐
│ tickets_archivocomentario        │
│  - archivo                       │
│  - nombre_archivo                │
│  - comentario (FK → Comentario)  │
│  - fecha_subida                  │
└──────────────────────────────────┘
```

## 📋 Modelo Ticket (Principal)

### Campos de Identificación
```python
id: AutoField (PK)
  - Generado automáticamente
  - Clave primaria única

titulo: CharField(max_length=200)
  - Título breve del ticket
  - Requerido
  - Indexado para búsqueda

descripcion: TextField
  - Descripción detallada del problema
  - Requerido
  - Sin límite de caracteres
```

### Campos de Clasificación
```python
estado: CharField(max_length=20)
  CHOICES:
    - 'pendiente': Pendiente (default)
    - 'en_progreso': En progreso
    - 'resuelto': Resuelto
    - 'cerrado': Cerrado
    - 'tiempo_excedido': Tiempo Excedido
  
  Flujo del estado:
    pendiente → en_progreso → resuelto → cerrado
                     ↓
              tiempo_excedido

prioridad: CharField(max_length=10)
  CHOICES:
    - 'baja': Baja
    - 'media': Media (default)
    - 'alta': Alta
    - 'critica': Crítica
  
  Impacto en SLA:
    - critica: 4 horas
    - alta: 8 horas
    - media: 24 horas
    - baja: 48 horas

tipo: CharField(max_length=20)
  CHOICES:
    - 'incidencia': Incidencia (default)
    - 'solicitud': Solicitud
    - 'problema': Problema
    - 'cambio': Cambio
  
  Uso en métricas:
    - Análisis de causas raíz
    - Gráficos de distribución

area_afectada: CharField(max_length=100)
  - Departamento o área impactada
  - Ejemplos: "IT", "RRHH", "Finanzas"
  - Usado en análisis de métricas
  - Opcional (blank=True)
```

### Campos de Asignación
```python
creador: ForeignKey(User, on_delete=CASCADE)
  - Usuario que creó el ticket
  - Relación: 1 User → N Tickets
  - No puede ser nulo
  - related_name='tickets_creados'

asignado_a: ForeignKey(User, on_delete=SET_NULL)
  - Técnico asignado al ticket
  - Puede ser nulo (tickets sin asignar)
  - related_name='tickets_asignados'
  - on_delete=SET_NULL: Si se elimina el técnico,
    el ticket no se elimina
```

### Campos de Fechas
```python
fecha_creacion: DateTimeField(auto_now_add=True)
  - Timestamp de creación automático
  - Inmutable (no se actualiza)
  - Usado para:
    * Ordenamiento
    * Filtros por período
    * Cálculo de antigüedad

fecha_actualizacion: DateTimeField(auto_now=True)
  - Timestamp de última modificación
  - Se actualiza automáticamente en cada save()
  - Usado para tracking de actividad

fecha_cierre: DateTimeField(null=True, blank=True)
  - Cuándo se cerró/resolvió el ticket
  - Se establece al cambiar estado a 'resuelto' o 'cerrado'
  - Usado para:
    * Cálculo de tiempo de resolución
    * Métricas de eficiencia

fecha_asignacion: DateTimeField(null=True, blank=True)
  - Cuándo se asignó a un técnico
  - Se establece en primera asignación
  - Usado para tracking de flujo

fecha_primera_respuesta: DateTimeField(null=True, blank=True)
  - Cuándo el técnico respondió por primera vez
  - Métrica SLA importante
  - Se establece automáticamente en primer comentario
```

### Campos SLA
```python
tiempo_limite_resolucion: DateTimeField(null=True, blank=True)
  - Deadline calculado para resolver el ticket
  - Calculado por:
    * calcular_tiempo_limite_sla() (automático)
    * Admin manualmente (personalizado)
  
  Cálculo automático:
    tiempo_limite = fecha_creacion + timedelta(horas según prioridad)
  
  Verificación:
    - Comando verificar_sla se ejecuta periódicamente
    - Si timezone.now() > tiempo_limite_resolucion:
        estado = 'tiempo_excedido'
```

### Campos de Tracking
```python
fue_reabierto: BooleanField(default=False)
  - Indica si el ticket fue reabierto después de cerrarse
  - Se marca True cuando:
    * Estado cambia de 'cerrado' a otro estado
  - Usado en métricas de calidad

numero_escalamientos: IntegerField(default=0)
  - Contador de veces que se escaló
  - Futuro: Implementar lógica de escalamiento
  - Métrica de complejidad del ticket
```

### Campos de Satisfacción
```python
calificacion_satisfaccion: IntegerField(null=True, blank=True)
  - Rating de 1 a 5 estrellas
  - Solo puede ser calificado por el creador
  - Solo en tickets resueltos/cerrados
  - Se califica al técnico asignado
  
  Validación:
    if not (1 <= calificacion <= 5):
        raise ValidationError
  
  Usado en:
    - CSAT (Customer Satisfaction Score)
    - Evaluación de técnicos
    - Métricas de calidad
```

### Métodos del Modelo

#### calcular_tiempo_primera_respuesta()
```python
def calcular_tiempo_primera_respuesta(self):
    """
    Calcula el tiempo entre creación y primera respuesta
    en horas.
    """
    if self.fecha_primera_respuesta:
        delta = self.fecha_primera_respuesta - self.fecha_creacion
        return delta.total_seconds() / 3600
    return None

# Uso en métricas:
tickets = Ticket.objects.filter(fecha_primera_respuesta__isnull=False)
tiempos = [t.calcular_tiempo_primera_respuesta() for t in tickets]
promedio = sum(tiempos) / len(tiempos) if tiempos else 0
```

#### calcular_tiempo_resolucion()
```python
def calcular_tiempo_resolucion(self):
    """
    Calcula el tiempo total de resolución en horas.
    """
    if self.fecha_cierre:
        delta = self.fecha_cierre - self.fecha_creacion
        return delta.total_seconds() / 3600
    return None

# Usado para:
# - Tiempo promedio de resolución
# - Eficiencia de técnicos
# - Cumplimiento de SLA
```

#### calcular_tiempo_limite_sla()
```python
def calcular_tiempo_limite_sla(self):
    """
    Calcula el tiempo límite según la prioridad.
    """
    from datetime import timedelta
    
    # Mapeo de prioridad a horas
    horas_sla = {
        'critica': 4,
        'alta': 8,
        'media': 24,
        'baja': 48,
    }
    
    horas = horas_sla.get(self.prioridad, 24)
    return self.fecha_creacion + timedelta(hours=horas)

# Se llama automáticamente al asignar ticket si
# no se especifica SLA personalizado
```

#### dias_desde_creacion()
```python
def dias_desde_creacion(self):
    """
    Retorna el número de días desde la creación.
    """
    from django.utils import timezone
    delta = timezone.now() - self.fecha_creacion
    return delta.days

# Usado en UI para mostrar antigüedad del ticket
```

#### __str__()
```python
def __str__(self):
    return f"Ticket #{self.id}: {self.titulo}"

# Representación legible en admin y shell
```

### Meta Class
```python
class Meta:
    ordering = ['-fecha_creacion']  # Más recientes primero
    verbose_name = 'Ticket'
    verbose_name_plural = 'Tickets'
    
    indexes = [
        models.Index(fields=['estado']),
        models.Index(fields=['prioridad']),
        models.Index(fields=['creador']),
        models.Index(fields=['asignado_a']),
    ]
```

## 💬 Modelo Comentario

### Estructura
```python
class Comentario(models.Model):
    ticket = ForeignKey(Ticket, on_delete=CASCADE,
                       related_name='comentarios')
    autor = ForeignKey(User, on_delete=CASCADE)
    contenido = TextField()
    fecha = DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['fecha']  # Ordenado cronológicamente
```

### Características
- **Sistema de comunicación** interno del ticket
- **Trazabilidad** de quién dijo qué y cuándo
- **Relación 1:N** con Ticket (un ticket tiene muchos comentarios)
- **Soporte de archivos** adjuntos via ArchivoComentario

### Uso
```python
# Obtener comentarios de un ticket
comentarios = ticket.comentarios.all().order_by('fecha')

# Crear comentario
Comentario.objects.create(
    ticket=ticket,
    autor=request.user,
    contenido="Problema resuelto"
)
```

## 📂 Modelo ArchivoTicket

### Estructura
```python
class ArchivoTicket(models.Model):
    ticket = ForeignKey(Ticket, on_delete=CASCADE,
                       related_name='archivos')
    archivo = FileField(upload_to='tickets/archivos/%Y/%m/')
    nombre_archivo = CharField(max_length=255)
    fecha_subida = DateTimeField(auto_now_add=True)
```

### Características
- **Organización por fecha**: Carpetas YYYY/MM/
- **Validación de tipo**: Solo ciertos formatos permitidos
- **Almacenamiento**: Sistema de archivos del servidor
- **Relación 1:N**: Un ticket puede tener múltiples archivos

### Validación
```python
# En forms.py
def clean_archivo(self):
    archivo = self.cleaned_data.get('archivo')
    
    # Validar tamaño (ej: max 10MB)
    if archivo.size > 10 * 1024 * 1024:
        raise ValidationError("Archivo muy grande")
    
    # Validar extensión
    extensiones_validas = ['.pdf', '.jpg', '.png', '.docx']
    ext = os.path.splitext(archivo.name)[1].lower()
    if ext not in extensiones_validas:
        raise ValidationError("Tipo de archivo no permitido")
    
    return archivo
```

## 📜 Modelo HistorialEstado

### Estructura
```python
class HistorialEstado(models.Model):
    ticket = ForeignKey(Ticket, on_delete=CASCADE,
                       related_name='historial_estados')
    estado_anterior = CharField(max_length=20)
    estado_nuevo = CharField(max_length=20)
    cambiado_por = ForeignKey(User, on_delete=CASCADE)
    fecha = DateTimeField(auto_now_add=True)
    comentario = TextField(blank=True)
```

### Características
- **Auditoría completa** de cambios de estado
- **Trazabilidad** de responsables
- **Timeline** del ticket
- **Inmutable**: Una vez creado, no se modifica

### Uso
```python
# Al cambiar estado en la vista
HistorialEstado.objects.create(
    ticket=ticket,
    estado_anterior=ticket.estado,
    estado_nuevo='en_progreso',
    cambiado_por=request.user,
    comentario='Iniciando trabajo en el ticket'
)
```

## 🔍 Consultas Comunes

### Tickets Pendientes de un Usuario
```python
tickets = Ticket.objects.filter(
    creador=user,
    estado='pendiente'
).order_by('-fecha_creacion')
```

### Tickets con SLA Próximo a Vencer
```python
from django.utils import timezone
from datetime import timedelta

proximo_vencimiento = timezone.now() + timedelta(hours=2)

tickets = Ticket.objects.filter(
    tiempo_limite_resolucion__lte=proximo_vencimiento,
    estado__in=['pendiente', 'en_progreso']
)
```

### Tickets Resueltos por Técnico
```python
from django.db.models import Count, Avg

stats = Ticket.objects.filter(
    asignado_a=tecnico,
    estado__in=['resuelto', 'cerrado']
).aggregate(
    total=Count('id'),
    promedio_calificacion=Avg('calificacion_satisfaccion')
)
```

### Tickets con Comentarios y Archivos
```python
ticket = Ticket.objects.select_related(
    'creador', 'asignado_a'
).prefetch_related(
    'comentarios__autor',
    'archivos',
    'historial_estados'
).get(id=ticket_id)

# Evita N+1 queries
```

---

## 📢 Modelo Notificacion (✨ NEW - Migración 0008)

### Descripción
Modelo para almacenar todas las notificaciones del sistema. Soporta múltiples canales de envío (Email, WhatsApp, Web).

### Campos
```python
class Notificacion(models.Model):
    # Relaciones
    usuario = ForeignKey(User, on_delete=CASCADE, related_name='notificaciones')
    ticket = ForeignKey(Ticket, on_delete=CASCADE, null=True, blank=True, related_name='notificaciones')
    
    # Tipos y Prioridades
    TIPOS = [
        ('ticket_creado', 'Ticket Creado'),
        ('ticket_asignado', 'Ticket Asignado'),
        ('ticket_comentario', 'Nuevo Comentario'),
        ('estado_cambio', 'Cambio de Estado'),
        ('ticket_resuelto', 'Ticket Resuelto'),
        ('ticket_cerrado', 'Ticket Cerrado'),
    ]
    
    PRIORIDADES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('critica', 'Crítica'),
    ]
    
    tipo = CharField(max_length=50, choices=TIPOS)
    prioridad = CharField(max_length=20, choices=PRIORIDADES, default='media')
    
    # Contenido
    titulo = CharField(max_length=200)
    mensaje = TextField()
    enlace = CharField(max_length=500, blank=True)
    
    # Estados de Envío - Email
    email_enviado = BooleanField(default=False)
    email_fecha = DateTimeField(null=True, blank=True)
    
    # Estados de Envío - WhatsApp
    whatsapp_enviado = BooleanField(default=False)
    whatsapp_fecha = DateTimeField(null=True, blank=True)
    
    # Estado Web
    leida = BooleanField(default=False)
    fecha_leida = DateTimeField(null=True, blank=True)
    
    # Auditoría
    fecha_creacion = DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha_creacion']
        indexes = [
            Index(fields=['usuario', '-fecha_creacion']),
            Index(fields=['usuario', 'leida']),
        ]
```

### Métodos Útiles
```python
# Obtener notificaciones no leídas
notificaciones = Notificacion.objects.filter(
    usuario=request.user,
    leida=False
).order_by('-fecha_creacion')

# Marcar como leída
notificacion.leida = True
notificacion.fecha_leida = timezone.now()
notificacion.save()

# Estadísticas
stats = {
    'total': Notificacion.objects.filter(usuario=user).count(),
    'no_leidas': Notificacion.objects.filter(usuario=user, leida=False).count(),
    'emails_enviados': Notificacion.objects.filter(usuario=user, email_enviado=True).count(),
}
```

### Consultas Comunes
```python
# Todas las notificaciones de un usuario ordenadas
notificaciones = Notificacion.objects.filter(
    usuario=request.user
).select_related('ticket__creador', 'usuario').order_by('-fecha_creacion')

# Notificaciones sin leer
no_leidas = Notificacion.objects.filter(
    usuario=request.user,
    leida=False
)[:5]  # Top 5

# Por tipo de notificación
creadas = Notificacion.objects.filter(
    usuario=request.user,
    tipo='ticket_creado'
)

# Notificaciones críticas
criticas = Notificacion.objects.filter(
    usuario=request.user,
    prioridad='critica'
)
```

### Integración con PerfilUsuario
```python
class PerfilUsuario(models.Model):
    user = OneToOneField(User, on_delete=CASCADE, related_name='perfilusuario')
    
    # Nuevos campos para notificaciones (Migración 0008)
    notificaciones_email = BooleanField(default=True)
    notificaciones_whatsapp = BooleanField(default=False)
    numero_whatsapp = CharField(max_length=20, blank=True, help_text="Formato: +57301234567")
    
    # ... otros campos
```

---

**Siguiente**: [Vistas y Controladores →](03_VISTAS.md)  
**Referencia**: [Sistema de Notificaciones →](SISTEMA_NOTIFICACIONES.md)
