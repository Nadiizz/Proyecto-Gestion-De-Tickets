# Vistas y Controladores - Sistema de Gestión de Tickets

## 📍 Vista General

El archivo `views.py` contiene toda la lógica de negocio del sistema, organizada en **13 vistas principales** que manejan:
- Autenticación y registro
- Gestión de tickets (CRUD)
- Sistema de métricas y analytics
- Calificaciones y feedback

## 🔐 Autenticación y Registro

### registro_usuario()
```python
@login_required
@user_passes_test(es_admin)
def registro_usuario(request):
    """
    Permite a administradores registrar nuevos usuarios.
    Valida dominio corporativo y asigna grupos automáticamente.
    """
```

**Decoradores**:
- `@login_required`: Requiere usuario autenticado
- `@user_passes_test(es_admin)`: Solo administradores

**Flujo**:
1. GET → Renderiza formulario `CustomUserCreationForm`
2. POST → Valida datos
3. Verifica dominio (@coyahue.com o @coyahue.cl)
4. Crea usuario
5. Asigna a grupo según tipo (Técnico o Usuario)
6. Redirect a login

**Validaciones**:
```python
# En CustomUserCreationForm
def clean_email(self):
    email = self.cleaned_data.get('email')
    pattern = r'@coyahue\.(com|cl)$'
    if not re.search(pattern, email):
        raise ValidationError(
            'El correo debe ser @coyahue.com o @coyahue.cl'
        )
    return email
```

**URL**: `/registro/`

---

## 📋 Gestión de Tickets

### ticket_list()
```python
@login_required
def ticket_list(request):
    """
    Lista de tickets con filtros avanzados y paginación.
    Adapta resultados según el rol del usuario.
    """
```

**Características**:
- **Búsqueda por texto**: Busca en título y descripción
- **Filtros**:
  * Estado (pendiente, en_progreso, resuelto, etc.)
  * Prioridad (baja, media, alta, crítica)
  * Área afectada
  * Técnico asignado
- **Paginación**: 10 tickets por página (configurable con `TICKETS_POR_PAGINA`)
- **Control de acceso por rol**:
  * **Usuarios**: Solo ven sus propios tickets
  * **Técnicos/Admins**: Ven todos los tickets

**Lógica de Filtrado**:
```python
if user.groups.filter(name='Usuario').exists():
    # Usuarios regulares: solo sus tickets
    tickets_base = Ticket.objects.filter(creador=user)
else:
    # Técnicos y admins: todos los tickets
    tickets_base = Ticket.objects.all()

# Aplicar filtros de búsqueda
if busqueda:
    tickets_base = tickets_base.filter(
        Q(titulo__icontains=busqueda) |
        Q(descripcion__icontains=busqueda)
    )

if estado:
    tickets_base = tickets_base.filter(estado=estado)

# ... más filtros
```

**Optimización**:
```python
tickets_lista = tickets_base.select_related(
    'creador', 'asignado_a'
).order_by('-fecha_creacion')

# select_related evita N+1 queries
# al obtener creador y asignado_a en la misma query
```

**URL**: `/` (home)

---

### crear_ticket()
```python
@login_required
def crear_ticket(request):
    """
    Permite crear un nuevo ticket con archivos adjuntos.
    """
```

**Flujo POST**:
1. Valida `TicketForm`
2. Guarda ticket con `commit=False`
3. Asigna creador automáticamente
4. Guarda ticket en BD
5. Procesa archivos adjuntos (si existen)
6. Crea registros `ArchivoTicket`
7. Mensaje de éxito
8. Redirect a lista

**Manejo de Archivos**:
```python
archivos = request.FILES.getlist('archivos')
for archivo in archivos:
    ArchivoTicket.objects.create(
        ticket=ticket,
        archivo=archivo,
        nombre_archivo=archivo.name
    )
```

**Campos del Formulario**:
- Título (requerido)
- Tipo (incidencia, solicitud, problema, cambio)
- Descripción (requerida)
- Área afectada
- Archivos (múltiples, opcional)

**URL**: `/nuevo/`

---

### ticket_detalle()
```python
@login_required
def ticket_detalle(request, ticket_id):
    """
    Vista detallada de un ticket con comentarios,
    historial y archivos.
    """
```

**Características**:
- Muestra todos los detalles del ticket
- Lista de comentarios ordenados cronológicamente
- Historial de cambios de estado
- Archivos adjuntos al ticket
- Permite agregar comentarios (POST)
- Adjuntar archivos a comentarios

**Datos Renderizados**:
```python
context = {
    'ticket': ticket,
    'comentarios': comentarios,
    'historial': historial,
    'archivos_ticket': archivos_ticket,
    'now': timezone.now(),  # Para calcular SLA restante
}
```

**POST - Agregar Comentario**:
```python
if request.method == 'POST':
    contenido = request.POST.get('comentario')
    
    # Crear comentario
    comentario = Comentario.objects.create(
        ticket=ticket,
        autor=request.user,
        contenido=contenido
    )
    
    # Registrar primera respuesta (si es técnico)
    if not ticket.fecha_primera_respuesta and \
       request.user.groups.filter(name='Técnico').exists():
        ticket.fecha_primera_respuesta = timezone.now()
        ticket.save()
    
    # Procesar archivos adjuntos
    archivos = request.FILES.getlist('archivos_comentario')
    for archivo in archivos:
        ArchivoComentario.objects.create(
            comentario=comentario,
            archivo=archivo,
            nombre_archivo=archivo.name
        )
```

**URL**: `/ticket/<id>/`

---

### asignar_ticket()
```python
@user_passes_test(es_admin)
def asignar_ticket(request, ticket_id):
    """
    Solo administradores pueden asignar tickets a técnicos.
    """
```

**Funcionalidad**:
1. Seleccionar técnico del dropdown
2. Cambiar prioridad (opcional)
3. Establecer SLA personalizado (opcional)

**Lógica de SLA**:
```python
if horas_sla and horas_sla.strip():
    # SLA personalizado
    ticket.tiempo_limite_resolucion = \
        ticket.fecha_creacion + timedelta(hours=int(horas_sla))
else:
    # SLA automático según prioridad
    ticket.tiempo_limite_resolucion = \
        ticket.calcular_tiempo_limite_sla()
```

**Registro de Primera Asignación**:
```python
if not ticket.fecha_asignacion:
    ticket.fecha_asignacion = timezone.now()
```

**Historial**:
```python
HistorialEstado.objects.create(
    ticket=ticket,
    cambiado_por=request.user,
    estado_anterior=ticket.estado,
    estado_nuevo=ticket.estado,
    comentario=f'Asignado a {tecnico.username}'
)
```

**URL**: `/asignar/<id>/`

---

### cambiar_estado()
```python
@login_required
def cambiar_estado(request, ticket_id):
    """
    Permite a técnicos cambiar el estado de un ticket.
    """
```

**Estados Permitidos**:
```python
ESTADOS_VALIDOS = [
    'en_progreso',
    'resuelto',
    'cerrado'
]
```

**Validación**:
- Solo técnicos pueden cambiar estados
- Estado debe ser válido

**Lógica de Cierre**:
```python
if nuevo_estado in ['resuelto', 'cerrado']:
    # Registrar fecha de cierre
    if not ticket.fecha_cierre:
        ticket.fecha_cierre = timezone.now()
```

**Detección de Reapertura**:
```python
if ticket.estado == 'cerrado' and nuevo_estado != 'cerrado':
    ticket.fue_reabierto = True
```

**URL**: `/estado/<id>/`

---

## 📊 Sistema de Métricas

### metricas()
```python
@login_required
@user_passes_test(es_admin)
def metricas(request):
    """
    Dashboard completo de métricas y KPIs del sistema.
    Solo accesible para administradores.
    """
```

**Constantes Utilizadas**:
```python
TICKETS_POR_PAGINA = 10
DIAS_METRICAS_DEFAULT = 30
TOP_TECNICOS_LIMIT = 10
TOP_AREAS_LIMIT = 10
FECHA_INICIO_HISTORICO = timezone.datetime(2000, 1, 1, ...)
```

**Períodos Disponibles**:
```python
dias = int(request.GET.get('dias', DIAS_METRICAS_DEFAULT))

if dias == 0:
    # Todo el tiempo
    fecha_inicio = FECHA_INICIO_HISTORICO
else:
    fecha_inicio = timezone.now() - timedelta(days=dias)
```

**Queryset Base Optimizado**:
```python
# Evita repetir fecha_creacion__gte en cada query
tickets_periodo = Ticket.objects.filter(
    fecha_creacion__gte=fecha_inicio
)
```

### Métricas Calculadas

#### 1. Métricas de Rendimiento
```python
# Volumen de tickets
tickets_totales = tickets_periodo.count()
tickets_resueltos = tickets_periodo.filter(
    estado__in=['resuelto', 'cerrado']
).count()
tickets_pendientes = Ticket.objects.filter(
    estado__in=['pendiente', 'en_progreso']
).count()
tickets_tiempo_excedido = Ticket.objects.filter(
    estado='tiempo_excedido'
).count()
```

#### 2. Tiempo de Primera Respuesta
```python
tickets_con_respuesta = tickets_periodo.filter(
    fecha_primera_respuesta__isnull=False
)

tiempos_primera_respuesta = []
for ticket in tickets_con_respuesta:
    tiempo = ticket.calcular_tiempo_primera_respuesta()
    if tiempo:
        tiempos_primera_respuesta.append(tiempo)

tiempo_promedio_primera_respuesta = (
    sum(tiempos_primera_respuesta) / len(tiempos_primera_respuesta)
    if tiempos_primera_respuesta else 0
)
```

#### 3. Tiempo de Resolución
```python
tickets_resueltos_con_tiempo = tickets_periodo.filter(
    estado__in=['resuelto', 'cerrado'],
    fecha_cierre__isnull=False
)

tiempos_resolucion = []
for ticket in tickets_resueltos_con_tiempo:
    tiempo = ticket.calcular_tiempo_resolucion()
    if tiempo:
        tiempos_resolucion.append(tiempo)

tiempo_promedio_resolucion = (
    sum(tiempos_resolucion) / len(tiempos_resolucion)
    if tiempos_resolucion else 0
)
```

#### 4. Satisfacción del Cliente (CSAT)
```python
tickets_con_calificacion = tickets_periodo.filter(
    calificacion_satisfaccion__isnull=False
)

satisfaccion_promedio = tickets_con_calificacion.aggregate(
    promedio=Avg('calificacion_satisfaccion')
)['promedio'] or 0
```

#### 5. Usuario Más Activo
```python
usuarios_activos = tickets_periodo.values(
    'creador__username',
    'creador__first_name',
    'creador__last_name'
).annotate(
    total_tickets=Count('id')
).order_by('-total_tickets')

usuario_mas_activo = usuarios_activos.first()
```

#### 6. Eficiencia por Técnico
```python
tickets_por_tecnico = tickets_periodo.filter(
    asignado_a__isnull=False
).values('asignado_a__username').annotate(
    total=Count('id'),
    resueltos=Count('id', filter=Q(estado__in=['resuelto', 'cerrado'])),
    calificacion_promedio=Avg('calificacion_satisfaccion')
).order_by('-total')[:TOP_TECNICOS_LIMIT]
```

#### 7. Análisis de Causas Raíz
```python
# Tickets por tipo con porcentaje
tickets_por_tipo = list(tickets_periodo.values('tipo').annotate(
    total=Count('id')
).order_by('-total'))

for tipo in tickets_por_tipo:
    tipo['porcentaje'] = round(
        (tipo['total'] / tickets_totales * 100)
        if tickets_totales > 0 else 0, 1
    )

# Tickets por área
tickets_por_area = list(tickets_periodo.values('area_afectada').annotate(
    total=Count('id')
).order_by('-total')[:TOP_AREAS_LIMIT])

for area in tickets_por_area:
    area['porcentaje'] = round(
        (area['total'] / tickets_totales * 100)
        if tickets_totales > 0 else 0, 1
    )

# Tickets por prioridad
tickets_por_prioridad = tickets_periodo.values('prioridad').annotate(
    total=Count('id')
).order_by('-total')
```

#### 8. Cumplimiento de SLA
```python
tickets_con_sla = tickets_periodo.filter(
    tiempo_limite_resolucion__isnull=False
).count()

tickets_sla_cumplido = tickets_periodo.filter(
    tiempo_limite_resolucion__isnull=False,
    fecha_cierre__isnull=False,
    fecha_cierre__lte=timezone.now()
).exclude(estado='tiempo_excedido').count()

tasa_cumplimiento_sla = (
    (tickets_sla_cumplido / tickets_con_sla * 100)
    if tickets_con_sla > 0 else 0
)
```

#### 9. Series Temporales
```python
from django.db.models.functions import TruncDate

tickets_por_dia = tickets_periodo.annotate(
    dia=TruncDate('fecha_creacion')
).values('dia').annotate(
    total=Count('id')
).order_by('dia')
```

**Context Enviado al Template**:
```python
context = {
    'dias': dias,  # Período seleccionado
    # Rendimiento
    'tickets_totales': tickets_totales,
    'tickets_resueltos': tickets_resueltos,
    'tickets_pendientes': tickets_pendientes,
    'tickets_tiempo_excedido': tickets_tiempo_excedido,
    'tiempo_promedio_primera_respuesta': round(..., 2),
    'tiempo_promedio_resolucion': round(..., 2),
    # Calidad
    'satisfaccion_promedio': round(..., 2),
    'usuario_mas_activo': usuario_mas_activo,
    'total_calificaciones': total_calificaciones,
    # Eficiencia
    'tickets_por_tecnico': tickets_por_tecnico,
    # Causas raíz
    'tickets_por_tipo': tickets_por_tipo,
    'tickets_por_area': tickets_por_area,
    'tickets_por_prioridad': tickets_por_prioridad,
    # SLA
    'tasa_cumplimiento_sla': round(..., 2),
    'tickets_con_sla': tickets_con_sla,
    'tickets_sla_cumplido': tickets_sla_cumplido,
    # Gráficos
    'tickets_por_dia': list(tickets_por_dia),
}
```

**URL**: `/metricas/` con parámetro `?dias=30`

---

## ⭐ Sistema de Calificaciones

### calificar_ticket()
```python
@login_required
def calificar_ticket(request, ticket_id):
    """
    Permite al creador del ticket calificar el servicio.
    """
```

**Validaciones**:
1. Solo el creador puede calificar
2. Solo tickets resueltos/cerrados
3. Solo una calificación por ticket
4. Calificación debe ser 1-5

**Lógica**:
```python
if request.user != ticket.creador:
    messages.error(request, 'No tienes permiso')
    return redirect('ticket_detalle', ticket_id=ticket_id)

if ticket.estado not in ['resuelto', 'cerrado']:
    messages.error(request, 'Solo tickets resueltos')
    return redirect('ticket_detalle', ticket_id=ticket_id)

if ticket.calificacion_satisfaccion:
    messages.warning(request, 'Ya calificaste este ticket')
    return redirect('ticket_detalle', ticket_id=ticket_id)

# Guardar calificación
calificacion = int(request.POST.get('calificacion'))
if 1 <= calificacion <= 5:
    ticket.calificacion_satisfaccion = calificacion
    ticket.save()
    messages.success(request, 'Gracias por tu calificación')
```

**URL**: `/calificar/<id>/`

---

## 📱 Mis Tickets (Vista Personal)

### mis_tickets()
```python
@login_required
def mis_tickets(request):
    """
    Vista personal para que los usuarios vean sus propios tickets.
    """
```

**Características**:
- Muestra solo los tickets del usuario actual
- Ordenados por fecha de creación (más recientes primero)
- Incluye información del técnico asignado
- Estados visualizados con colores

**Query**:
```python
tickets_usuario = Ticket.objects.filter(
    creador=request.user
).select_related('asignado_a').order_by('-fecha_creacion')
```

**URL**: `/mis-tickets/`

---

## 📢 Vistas API de Notificaciones (✨ NEW)

### notificaciones_api()
```python
@login_required
def notificaciones_api(request):
    """
    Retorna todas las notificaciones del usuario en formato JSON.
    Soporta filtros por estado de lectura.
    """
```

**Método**: GET  
**URL**: `/api/notificaciones/`  
**Respuesta**: JSON

**Parámetros**:
- `leidas` (boolean, opcional): Filtrar por estado
- `limite` (integer, opcional, default=20): Límite de resultados

**Query Optimizada**:
```python
notificaciones = Notificacion.objects.filter(
    usuario=request.user
).select_related('ticket').order_by('-fecha_creacion')

if 'leidas' in request.GET:
    leidas = request.GET.get('leidas').lower() == 'true'
    notificaciones = notificaciones.filter(leida=leidas)

# Paginación
limite = int(request.GET.get('limite', 20))
return JsonResponse({
    'total': notificaciones.count(),
    'notificaciones': list(notificaciones[:limite].values())
})
```

**Ejemplo de Respuesta**:
```json
{
  "total": 5,
  "notificaciones": [
    {
      "id": 42,
      "titulo": "Ticket Asignado",
      "mensaje": "Se te asignó ticket #1005",
      "tipo": "ticket_asignado",
      "prioridad": "media",
      "leida": false,
      "fecha_creacion": "2025-01-15T10:30:00Z"
    }
  ]
}
```

---

### notificaciones_nuevas_api()
```python
@login_required
def notificaciones_nuevas_api(request):
    """
    Retorna solo las notificaciones no leídas del usuario.
    Ideal para actualizar badge de contador.
    """
```

**Método**: GET  
**URL**: `/api/notificaciones/nuevas/`  
**Respuesta**: JSON

**Lógica**:
```python
no_leidas = Notificacion.objects.filter(
    usuario=request.user,
    leida=False
).order_by('-fecha_creacion')

return JsonResponse({
    'total': Notificacion.objects.filter(usuario=request.user).count(),
    'sin_leer': no_leidas.count(),
    'notificaciones': list(no_leidas.values())
})
```

---

### marcar_notificacion_leida_api()
```python
@login_required
def marcar_notificacion_leida_api(request, notificacion_id):
    """
    Marca una notificación específica como leída.
    """
```

**Método**: POST  
**URL**: `/api/notificaciones/<id>/marcar-leida/`  
**Respuesta**: JSON

**Validación y Lógica**:
```python
try:
    notificacion = Notificacion.objects.get(
        id=notificacion_id,
        usuario=request.user
    )
    notificacion.leida = True
    notificacion.fecha_leida = timezone.now()
    notificacion.save()
    
    return JsonResponse({
        'success': True,
        'mensaje': 'Notificación marcada como leída',
        'notificacion': {
            'id': notificacion.id,
            'leida': True
        }
    })
except Notificacion.DoesNotExist:
    return JsonResponse(
        {'error': 'Notificación no encontrada'},
        status=404
    )
```

---

### marcar_todas_notificaciones_leidas_api()
```python
@login_required
def marcar_todas_notificaciones_leidas_api(request):
    """
    Marca todas las notificaciones del usuario como leídas.
    """
```

**Método**: POST  
**URL**: `/api/notificaciones/marcar-todas-leidas/`  
**Respuesta**: JSON

**Lógica**:
```python
no_leidas = Notificacion.objects.filter(
    usuario=request.user,
    leida=False
)

actualizadas = 0
for notif in no_leidas:
    notif.leida = True
    notif.fecha_leida = timezone.now()
    notif.save()
    actualizadas += 1

return JsonResponse({
    'success': True,
    'mensaje': 'Todas las notificaciones han sido marcadas como leídas',
    'actualizadas': actualizadas,
    'timestamp': timezone.now().isoformat()
})
```

---

### lista_notificaciones()
```python
@login_required
def lista_notificaciones(request):
    """
    Vista HTML que renderiza la página de notificaciones.
    """
```

**Método**: GET  
**URL**: `/notificaciones/`  
**Template**: `tickets/lista_notificaciones.html`

**Contexto**:
```python
notificaciones = Notificacion.objects.filter(
    usuario=request.user
).select_related('ticket')

context = {
    'notificaciones': notificaciones,
    'sin_leer': notificaciones.filter(leida=False).count(),
}
return render(request, 'tickets/lista_notificaciones.html', context)
```

---

## 🔧 Funciones Auxiliares

### es_admin()
```python
def es_admin(user):
    """
    Verifica si el usuario es administrador.
    Usado en decorador @user_passes_test
    """
    return user.groups.filter(name='Administrador').exists()
```

### es_tecnico()
```python
def es_tecnico(user):
    """
    Verifica si el usuario es técnico.
    """
    return user.groups.filter(name='Técnico').exists()
```

---

**Siguiente**: [Templates y Frontend →](04_TEMPLATES.md)
