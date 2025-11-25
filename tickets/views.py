from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Count, Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponseForbidden
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import timedelta
import logging

from .models import Ticket, Comentario, HistorialEstado, ArchivoTicket, ArchivoComentario
from .forms import CustomUserCreationForm, BusquedaTicketForm, TicketForm

# Configurar logger
logger = logging.getLogger('tickets')

# Constantes de configuración
TICKETS_POR_PAGINA = 10
DIAS_METRICAS_DEFAULT = 30
TOP_TECNICOS_LIMIT = 10
TOP_AREAS_LIMIT = 10
FECHA_INICIO_HISTORICO = timezone.datetime(2000, 1, 1, tzinfo=timezone.get_current_timezone())

# Constantes de grupos de usuarios
GRUPO_ADMINISTRADOR = 'Administrador'
GRUPO_TECNICO = 'Técnico'
GRUPO_USUARIO = 'Usuario'

# Constantes de archivos
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_FILE_EXTENSIONS = ['.pdf', '.doc', '.docx', '.txt', '.jpg', '.jpeg', '.png', '.gif', '.xlsx', '.xls', '.zip']

# Create your views here.

# Controlador principal con todas las vistas del sistema de tickets
# Implementa control de acceso basado en roles (Admin, Técnico, Usuario)
# Gestiona creación, asignación, modificación y visualización de tickets
# Mantiene historial de cambios y comentarios para cada ticket


# Función auxiliar para verificar si un usuario pertenece al grupo Administrador
def es_admin(user):
    return user.groups.filter(name=GRUPO_ADMINISTRADOR).exists()

# Función auxiliar para verificar si un usuario es técnico
def es_tecnico(user):
    return user.groups.filter(name=GRUPO_TECNICO).exists()


def verificar_y_actualizar_sla():
    """
    Verifica y actualiza automáticamente tickets que excedieron el SLA.
    Esta función se ejecuta en cada acceso al dashboard/métricas.
    """
    tickets_excedidos = Ticket.objects.filter(
        estado__in=['pendiente', 'en_progreso'],
        tiempo_limite_resolucion__isnull=False,
        tiempo_limite_resolucion__lt=timezone.now()
    )
    
    count = 0
    for ticket in tickets_excedidos:
        estado_anterior = ticket.estado
        ticket.estado = 'tiempo_excedido'
        ticket.fecha_cierre = timezone.now()
        ticket.save()
        
        # Registrar en el historial
        HistorialEstado.objects.create(
            ticket=ticket,
            cambiado_por=ticket.asignado_a if ticket.asignado_a else ticket.creador,
            estado_anterior=estado_anterior,
            estado_nuevo='tiempo_excedido',
            comentario='Ticket cerrado automáticamente por exceder el tiempo límite SLA'
        )
        
        count += 1
        logger.warning(
            f'Ticket #{ticket.id} "{ticket.titulo}" cerrado automáticamente por SLA excedido'
        )
    
    return count


# Vista principal que muestra la lista de tickets según el rol del usuario
@login_required
def ticket_list(request):
    # Verificar y actualizar SLA automáticamente
    verificar_y_actualizar_sla()
    
    user = request.user
    
    # Determinar tickets base según el rol
    # Administradores y Técnicos ven todos los tickets
    # Usuarios solo ven sus propios tickets
    if es_admin(user) or es_tecnico(user):
        tickets_base = Ticket.objects.all().select_related('creador', 'asignado_a')
    else:
        tickets_base = Ticket.objects.filter(creador=user).select_related('creador', 'asignado_a')
    
    # Inicializar formulario de búsqueda
    form = BusquedaTicketForm(request.GET or None)
    
    # Aplicar filtros de búsqueda avanzada
    if form.is_valid():
        # Búsqueda por texto en título o descripción
        busqueda = form.cleaned_data.get('busqueda')
        if busqueda:
            tickets_base = tickets_base.filter(
                Q(titulo__icontains=busqueda) | Q(descripcion__icontains=busqueda)
            )
        
        # Filtro por estado
        estado = form.cleaned_data.get('estado')
        if estado:
            tickets_base = tickets_base.filter(estado=estado)
        
        # Filtro por prioridad
        prioridad = form.cleaned_data.get('prioridad')
        if prioridad:
            tickets_base = tickets_base.filter(prioridad=prioridad)
        
        # Filtro por área
        area = form.cleaned_data.get('area_afectada')
        if area:
            tickets_base = tickets_base.filter(area_afectada__icontains=area)
        
        # Filtro por técnico asignado
        asignado = form.cleaned_data.get('asignado_a')
        if asignado:
            tickets_base = tickets_base.filter(asignado_a=asignado)
    
    # Filtro por días atrás (desde el parámetro GET)
    dias_atras = request.GET.get('dias_atras')
    if dias_atras:
        try:
            dias = int(dias_atras)
            fecha_limite = timezone.now() - timedelta(days=dias)
            tickets_base = tickets_base.filter(fecha_creacion__gte=fecha_limite)
        except ValueError:
            pass  # Si no es un número válido, ignorar el filtro
    
    # Ordenar tickets
    tickets_lista = tickets_base.order_by('-fecha_creacion')
    
    # Paginación: configurable mediante constante
    paginator = Paginator(tickets_lista, TICKETS_POR_PAGINA)
    page_number = request.GET.get('page')
    tickets = paginator.get_page(page_number)
    
    # Estadísticas para el dashboard (sobre todos los tickets del usuario, no solo la página actual)
    total_tickets = tickets_base.count()
    asignados_count = tickets_base.filter(asignado_a__isnull=False).count()
    en_proceso_count = tickets_base.filter(estado='en_progreso').count()
    resueltos_count = tickets_base.filter(estado='resuelto').count()
    cerrados_count = tickets_base.filter(estado='cerrado').count()
    sla_excedido_count = tickets_base.filter(estado='tiempo_excedido').count()
    
    context = {
        'tickets': tickets,
        'form': form,
        'total_tickets': total_tickets,
        'asignados_count': asignados_count,
        'en_proceso_count': en_proceso_count,
        'resueltos_count': resueltos_count,
        'cerrados_count': cerrados_count,
        'sla_excedido_count': sla_excedido_count,
    }
    
    return render(request, 'tickets/ticket_list.html', context)

# Vista para crear nuevos tickets en el sistema
@login_required
def ticket_create(request):
    if request.method == 'POST':
        form = TicketForm(request.POST, request.FILES)
        if form.is_valid():
            # Crear el ticket
            ticket = form.save(commit=False)
            ticket.creador = request.user
            # Asignar prioridad por defecto 'media' si el usuario no es admin
            ticket.prioridad = 'media'
            
            # Guardar primero para que tenga fecha_creacion
            ticket.save()
            
            # Ahora calcular tiempo límite SLA basado en la prioridad
            ticket.tiempo_limite_resolucion = ticket.calcular_tiempo_limite_sla()
            ticket.save()
            
            # Logging
            logger.info(f'Ticket #{ticket.id} creado por {request.user.username}: "{ticket.titulo}"')
            
            # Registrar en el historial
            HistorialEstado.objects.create(
                ticket=ticket,
                cambiado_por=request.user,
                estado_nuevo='pendiente'
            )
            
            # Procesar archivos adjuntos
            archivos = request.FILES.getlist('archivos')
            for archivo in archivos:
                ArchivoTicket.objects.create(
                    ticket=ticket,
                    subido_por=request.user,
                    archivo=archivo,
                    nombre_archivo=archivo.name
                )
            
            messages.success(request, 'Ticket creado exitosamente.')
            return redirect('ticket_list')
    else:
        form = TicketForm()
    
    return render(request, 'tickets/ticket_form.html', {'form': form})

# Vista para asignar tickets a técnicos (solo administradores)
@user_passes_test(es_admin)
def asignar_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    if request.method == 'POST':
        # Asigna el ticket al técnico seleccionado
        tecnico_id = request.POST.get('tecnico')
        prioridad = request.POST.get('prioridad')
        horas_sla = request.POST.get('horas_sla')
        
        tecnico = get_object_or_404(User, id=tecnico_id)
        ticket.asignado_a = tecnico
        
        # Actualizar prioridad si se especifica
        if prioridad:
            ticket.prioridad = prioridad
        
        # Calcular tiempo límite SLA: personalizado o por defecto
        if horas_sla and horas_sla.strip():
            # SLA personalizado: usar las horas especificadas
            from datetime import timedelta
            ticket.tiempo_limite_resolucion = ticket.fecha_creacion + timedelta(hours=int(horas_sla))
        else:
            # SLA por defecto: basado en la prioridad
            ticket.tiempo_limite_resolucion = ticket.calcular_tiempo_limite_sla()
        
        # Registrar fecha de asignación si es la primera vez
        if not ticket.fecha_asignacion:
            ticket.fecha_asignacion = timezone.now()
        
        ticket.save()
        
        # Logging
        logger.info(
            f'Ticket #{ticket.id} asignado a {tecnico.username} por {request.user.username}. '
            f'Prioridad: {ticket.prioridad}, SLA: {ticket.tiempo_limite_resolucion}'
        )
        
        # Registrar en historial
        HistorialEstado.objects.create(
            ticket=ticket,
            cambiado_por=request.user,
            estado_anterior=ticket.estado,
            estado_nuevo=ticket.estado,
            comentario=f'Ticket asignado a {tecnico.username}'
        )
        
        return redirect('ticket_list')
    
    # Obtiene la lista de todos los técnicos disponibles
    # Excluye al creador del ticket para evitar conflicto de interés
    tecnicos = User.objects.filter(groups__name=GRUPO_TECNICO).exclude(id=ticket.creador.id)
    
    # Verificar si hay técnicos disponibles
    if not tecnicos.exists():
        messages.warning(
            request,
            'No hay técnicos disponibles para asignar este ticket. '
            'El creador del ticket no puede ser asignado al mismo.'
        )
    
    return render(request, 'tickets/asignar_ticket.html', {
        'ticket': ticket,
        'tecnicos': tecnicos
    })

# Vista para que los técnicos cambien el estado de los tickets asignados
@login_required
def cambiar_estado(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    # Verifica permisos
    if ticket.asignado_a != request.user and not es_admin(request.user):
        return HttpResponseForbidden("No tienes permiso para cambiar este ticket.")
    
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        comentario = request.POST.get('comentario', '').strip()
        
        if nuevo_estado and nuevo_estado != ticket.estado:
            # Guarda el estado anterior
            estado_anterior = ticket.estado
            
            # Actualiza el ticket
            ticket.estado = nuevo_estado
            
            # Registrar fecha de cierre si el ticket se resuelve o cierra
            if nuevo_estado in ['resuelto', 'cerrado'] and not ticket.fecha_cierre:
                ticket.fecha_cierre = timezone.now()
            
            # Si se reabre un ticket
            if estado_anterior in ['resuelto', 'cerrado'] and nuevo_estado in ['pendiente', 'en_progreso']:
                ticket.fue_reabierto = True
                ticket.fecha_cierre = None
                logger.warning(f'Ticket #{ticket.id} reabierto por {request.user.username}')
            
            ticket.save()
            
            # Logging
            logger.info(
                f'Ticket #{ticket.id} cambió de estado: {estado_anterior} → {nuevo_estado} '
                f'por {request.user.username}'
            )
            
            # Crea el historial 
            HistorialEstado.objects.create(
                ticket=ticket,
                cambiado_por=request.user,
                estado_anterior=estado_anterior,  
                estado_nuevo=nuevo_estado,
                comentario=comentario or None
            )
            
            # También crea un comentario para mayor visibilidad
            mensaje_comentario = f"📋 **Cambio de estado:** {estado_anterior} → {nuevo_estado}"
            if comentario:
                mensaje_comentario += f"\n💬 **Comentario:** {comentario}"
            
            Comentario.objects.create(
                ticket=ticket,
                autor=request.user,
                mensaje=mensaje_comentario
            )
        
        return redirect('ticket_detalle', ticket_id=ticket.id)
    
    # Estados disponibles (usa los estados del modelo Ticket)
    ESTADOS_DISPONIBLES = [
        ('pendiente', 'Pendiente'),
        ('en_progreso', 'En Progreso'),
        ('resuelto', 'Resuelto'),
        ('cerrado', 'Cerrado'),
    ]
    
    return render(request, 'tickets/cambiar_estado.html', {
        'ticket': ticket,
        'estados': ESTADOS_DISPONIBLES
    })

# Vista detallada de un ticket específico con comentarios e historial
@login_required
def registro(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registro exitoso. ¡Bienvenido!')
            return redirect('ticket_list')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/registro.html', {'form': form})


def cerrar_sesion(request):
    """Vista personalizada para cerrar sesión que permite GET y POST"""
    logout(request)
    # Redirigir al login con parámetro GET para mostrar mensaje
    return redirect('/login/?logout=success')


def ticket_detalle(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)

    # Verifica los permisos para ver el ticket
    usuario_es_admin = es_admin(request.user)
    es_tecnico_asignado = ticket.asignado_a == request.user
    es_creador = ticket.creador == request.user

    # Solo permitir acceso a usuarios autorizados
    if not (usuario_es_admin or es_tecnico_asignado or es_creador):
        return HttpResponseForbidden("No tienes permiso para ver este ticket.")

    # Maneja la creación de nuevos comentarios
    if request.method == 'POST':
        mensaje = request.POST.get('mensaje')
        if mensaje:
            comentario = Comentario.objects.create(
                ticket=ticket,
                autor=request.user,
                mensaje=mensaje
            )
            
            # Registrar primera respuesta si es la primera vez que un técnico/admin responde
            if not ticket.fecha_primera_respuesta and request.user != ticket.creador:
                ticket.fecha_primera_respuesta = timezone.now()
                ticket.save()
            
            # Procesar archivos adjuntos del comentario
            archivos = request.FILES.getlist('archivos_comentario')
            for archivo in archivos:
                ArchivoComentario.objects.create(
                    comentario=comentario,
                    subido_por=request.user,
                    archivo=archivo,
                    nombre_archivo=archivo.name
                )
            
            return redirect('ticket_detalle', ticket_id=ticket.id)

    # Obtiene comentarios e historial ordenados por fecha (optimizado con select_related)
    comentarios = ticket.comentarios.select_related('autor').prefetch_related('archivos').order_by('fecha')
    historial = ticket.historial_estados.select_related('cambiado_por').order_by('fecha')
    archivos_ticket = ticket.archivos.select_related('subido_por').order_by('-fecha_subida')
    
    return render(request, 'tickets/ticket_detalle.html', {
        'ticket': ticket,
        'comentarios': comentarios,
        'historial': historial,
        'archivos_ticket': archivos_ticket,
        'now': timezone.now(),
    })


# Vista de métricas y estadísticas del sistema
@login_required
@user_passes_test(es_admin)
def metricas(request):
    """Vista completa de métricas y KPIs del sistema de tickets"""
    
    # Verificar y actualizar SLA automáticamente
    verificar_y_actualizar_sla()
    
    # Obtener rango de fechas (0 = todo el tiempo)
    dias = int(request.GET.get('dias', DIAS_METRICAS_DEFAULT))
    
    if dias == 0:
        # Todo el tiempo - usar fecha de inicio histórico
        fecha_inicio = FECHA_INICIO_HISTORICO
    else:
        fecha_inicio = timezone.now() - timedelta(days=dias)
    
    # Queryset base para evitar repetición
    tickets_periodo = Ticket.objects.filter(fecha_creacion__gte=fecha_inicio)
    
    # MÉTRICAS DE RENDIMIENTO
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
    
    # Tiempo de primera respuesta (en horas)
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
    
    # Tiempo de resolución (en horas)
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
    
    # MÉTRICAS DE CALIDAD
    # Satisfacción del cliente (CSAT)
    tickets_con_calificacion = tickets_periodo.filter(
        calificacion_satisfaccion__isnull=False
    )
    
    satisfaccion_promedio = tickets_con_calificacion.aggregate(
        promedio=Avg('calificacion_satisfaccion')
    )['promedio'] or 0
    
    # Usuario más activo - reemplaza al NPS
    usuarios_activos = tickets_periodo.values(
        'creador__username', 'creador__first_name', 'creador__last_name'
    ).annotate(
        total_tickets=Count('id')
    ).order_by('-total_tickets')
    
    usuario_mas_activo = usuarios_activos.first() if usuarios_activos else None
    total_calificaciones = tickets_con_calificacion.count()
    
    # MÉTRICAS DE EFICIENCIA
    # Tickets por técnico con calificación promedio
    tickets_por_tecnico = tickets_periodo.filter(
        asignado_a__isnull=False
    ).values('asignado_a__username').annotate(
        total=Count('id'),
        resueltos=Count('id', filter=Q(estado__in=['resuelto', 'cerrado'])),
        calificacion_promedio=Avg('calificacion_satisfaccion')
    ).order_by('-total')[:TOP_TECNICOS_LIMIT]
    
    # CAUSAS RAÍZ Y RESOLUCIÓN
    # Tickets por tipo con porcentaje calculado
    tickets_por_tipo = list(tickets_periodo.values('tipo').annotate(
        total=Count('id')
    ).order_by('-total'))
    
    for tipo in tickets_por_tipo:
        tipo['porcentaje'] = round((tipo['total'] / tickets_totales * 100) if tickets_totales > 0 else 0, 1)
    
    # Tickets por área afectada con porcentaje calculado
    tickets_por_area = list(tickets_periodo.values('area_afectada').annotate(
        total=Count('id')
    ).order_by('-total')[:TOP_AREAS_LIMIT])
    
    for area in tickets_por_area:
        area['porcentaje'] = round((area['total'] / tickets_totales * 100) if tickets_totales > 0 else 0, 1)
    
    # Tickets por prioridad
    tickets_por_prioridad = tickets_periodo.values('prioridad').annotate(
        total=Count('id')
    ).order_by('-total')
    
    # Cumplimiento de SLA
    tickets_con_sla = tickets_periodo.filter(
        tiempo_limite_resolucion__isnull=False
    ).count()
    
    tickets_sla_cumplido = tickets_periodo.filter(
        tiempo_limite_resolucion__isnull=False,
        fecha_cierre__isnull=False,
        fecha_cierre__lte=timezone.now()
    ).exclude(estado='tiempo_excedido').count()
    
    tasa_cumplimiento_sla = (
        (tickets_sla_cumplido / tickets_con_sla * 100) if tickets_con_sla > 0 else 0
    )
    
    # Tickets por día (para gráfico)
    tickets_por_dia = tickets_periodo.annotate(
        dia=TruncDate('fecha_creacion')
    ).values('dia').annotate(
        total=Count('id')
    ).order_by('dia')
    
    context = {
        'dias': dias,
        # Rendimiento
        'tickets_totales': tickets_totales,
        'tickets_resueltos': tickets_resueltos,
        'tickets_pendientes': tickets_pendientes,
        'tickets_tiempo_excedido': tickets_tiempo_excedido,
        'tiempo_promedio_primera_respuesta': round(tiempo_promedio_primera_respuesta, 2),
        'tiempo_promedio_resolucion': round(tiempo_promedio_resolucion, 2),
        # Calidad
        'satisfaccion_promedio': round(satisfaccion_promedio, 2),
        'usuario_mas_activo': usuario_mas_activo,
        'total_calificaciones': total_calificaciones,
        # Eficiencia
        'tickets_por_tecnico': tickets_por_tecnico,
        # Causas raíz
        'tickets_por_tipo': tickets_por_tipo,
        'tickets_por_area': tickets_por_area,
        'tickets_por_prioridad': tickets_por_prioridad,
        # SLA
        'tasa_cumplimiento_sla': round(tasa_cumplimiento_sla, 2),
        'tickets_con_sla': tickets_con_sla,
        'tickets_sla_cumplido': tickets_sla_cumplido,
        # Gráficos
        'tickets_por_dia': list(tickets_por_dia),
    }
    
    return render(request, 'tickets/metricas.html', context)

# Vista para calificar el servicio de un ticket
@login_required
def calificar_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    # Solo el creador puede calificar y solo si el ticket está resuelto/cerrado
    if request.user != ticket.creador:
        messages.error(request, 'No tienes permiso para calificar este ticket.')
        return redirect('ticket_detalle', ticket_id=ticket_id)
    
    if ticket.estado not in ['resuelto', 'cerrado']:
        messages.error(request, 'Solo puedes calificar tickets resueltos o cerrados.')
        return redirect('ticket_detalle', ticket_id=ticket_id)
    
    if ticket.calificacion_satisfaccion:
        messages.warning(request, 'Ya has calificado este ticket.')
        return redirect('ticket_detalle', ticket_id=ticket_id)
    
    if request.method == 'POST':
        calificacion = request.POST.get('calificacion')
        if calificacion and calificacion.isdigit():
            calificacion_int = int(calificacion)
            if 1 <= calificacion_int <= 5:
                ticket.calificacion_satisfaccion = calificacion_int
                ticket.save()
                messages.success(request, f'¡Gracias por tu calificación de {calificacion_int} estrellas!')
            else:
                messages.error(request, 'La calificación debe estar entre 1 y 5.')
        else:
            messages.error(request, 'Calificación inválida.')
    
    return redirect('ticket_detalle', ticket_id=ticket_id)

# Vista para que los usuarios vean sus propios tickets
@login_required
def mis_tickets(request):
    # Obtener solo los tickets del usuario actual
    tickets_usuario = Ticket.objects.filter(creador=request.user).order_by('-fecha_creacion')
    
    # Filtros opcionales
    estado_filtro = request.GET.get('estado', '')
    if estado_filtro:
        tickets_usuario = tickets_usuario.filter(estado=estado_filtro)
    
    # Estadísticas del usuario
    total_tickets = tickets_usuario.count()
    tickets_abiertos = tickets_usuario.filter(estado__in=['abierto', 'en_progreso']).count()
    tickets_cerrados = tickets_usuario.filter(estado__in=['resuelto', 'cerrado']).count()
    tickets_sin_calificar = tickets_usuario.filter(
        estado__in=['resuelto', 'cerrado'],
        calificacion_satisfaccion__isnull=True
    ).count()
    
    context = {
        'tickets': tickets_usuario,
        'total_tickets': total_tickets,
        'tickets_abiertos': tickets_abiertos,
        'tickets_cerrados': tickets_cerrados,
        'tickets_sin_calificar': tickets_sin_calificar,
        'estado_filtro': estado_filtro,
    }
    
    return render(request, 'tickets/mis_tickets.html', context)


# Vista para que los técnicos vean sus tickets asignados
@login_required
def mis_asignaciones(request):
    # Verificar que el usuario sea técnico
    if not es_tecnico(request.user) and not es_admin(request.user):
        messages.error(request, 'No tienes permiso para acceder a esta página.')
        return redirect('ticket_list')
    
    # Obtener tickets asignados al técnico actual
    tickets_asignados = Ticket.objects.filter(
        asignado_a=request.user
    ).select_related('creador', 'asignado_a').order_by('-fecha_creacion')
    
    # Filtros opcionales
    estado_filtro = request.GET.get('estado', '')
    prioridad_filtro = request.GET.get('prioridad', '')
    
    if estado_filtro:
        tickets_asignados = tickets_asignados.filter(estado=estado_filtro)
    
    if prioridad_filtro:
        tickets_asignados = tickets_asignados.filter(prioridad=prioridad_filtro)
    
    # Estadísticas del técnico
    total_asignados = tickets_asignados.count()
    tickets_pendientes = tickets_asignados.filter(estado='pendiente').count()
    tickets_en_progreso = tickets_asignados.filter(estado='en_progreso').count()
    tickets_resueltos = tickets_asignados.filter(estado__in=['resuelto', 'cerrado']).count()
    tickets_sla_excedido = tickets_asignados.filter(estado='tiempo_excedido').count()
    
    # Tickets críticos sin resolver
    tickets_criticos = tickets_asignados.filter(
        prioridad='critica',
        estado__in=['pendiente', 'en_progreso']
    ).count()
    
    # Tickets próximos a vencer (SLA en menos de 2 horas)
    from datetime import timedelta
    tiempo_limite = timezone.now() + timedelta(hours=2)
    tickets_por_vencer = tickets_asignados.filter(
        estado__in=['pendiente', 'en_progreso'],
        tiempo_limite_resolucion__isnull=False,
        tiempo_limite_resolucion__lte=tiempo_limite,
        tiempo_limite_resolucion__gt=timezone.now()
    ).count()
    
    # Paginación
    paginator = Paginator(tickets_asignados, TICKETS_POR_PAGINA)
    page_number = request.GET.get('page')
    tickets = paginator.get_page(page_number)
    
    context = {
        'tickets': tickets,
        'total_asignados': total_asignados,
        'tickets_pendientes': tickets_pendientes,
        'tickets_en_progreso': tickets_en_progreso,
        'tickets_resueltos': tickets_resueltos,
        'tickets_sla_excedido': tickets_sla_excedido,
        'tickets_criticos': tickets_criticos,
        'tickets_por_vencer': tickets_por_vencer,
        'estado_filtro': estado_filtro,
        'prioridad_filtro': prioridad_filtro,
        'now': timezone.now(),
    }
    
    return render(request, 'tickets/mis_asignaciones.html', context)
