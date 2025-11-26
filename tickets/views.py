from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.cache import cache
from django.db.models import Q, Avg, Count, Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponseForbidden
from django.urls import reverse_lazy
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import logging
import secrets
import hashlib

from .models import Ticket, Comentario, HistorialEstado, ArchivoTicket, ArchivoComentario, RolPersonalizado, PerfilUsuario
from .forms import CustomUserCreationForm, BusquedaTicketForm, TicketForm
from .services import crear_notificacion_completa

# Configurar logger
logger = logging.getLogger('tickets')

# Constantes de configuración (importadas de settings.py)
TICKETS_POR_PAGINA = settings.TICKETS_POR_PAGINA
DIAS_METRICAS_DEFAULT = settings.DIAS_METRICAS_DEFAULT
TOP_TECNICOS_LIMIT = settings.TOP_TECNICOS_LIMIT
TOP_AREAS_LIMIT = settings.TOP_AREAS_LIMIT
FECHA_INICIO_HISTORICO = timezone.datetime(2000, 1, 1, tzinfo=timezone.get_current_timezone())

# Constantes de grupos de usuarios (importadas de settings.py)
GRUPO_ADMINISTRADOR = settings.GRUPO_ADMINISTRADOR
GRUPO_TECNICO = settings.GRUPO_TECNICO
GRUPO_USUARIO = settings.GRUPO_USUARIO

# Constantes de archivos (importadas de settings.py)
MAX_FILE_SIZE = settings.MAX_FILE_SIZE
ALLOWED_FILE_EXTENSIONS = settings.ALLOWED_FILE_EXTENSIONS

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

# Función auxiliar para verificar si un usuario es usuario regular
def es_usuario_regular(user):
    return user.groups.filter(name=GRUPO_USUARIO).exists()

# Decorador personalizado para verificar permisos de ticket
def ticket_permission_required(permission_type='view'):
    """
    Decorador que verifica permisos para operaciones en tickets.
    permission_type: 'view', 'edit', 'admin', o 'tecnico'
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            ticket_id = kwargs.get('ticket_id')
            if not ticket_id:
                # Si no hay ticket_id, permitir que el decorador de login_required lo maneje
                return view_func(request, *args, **kwargs)
            
            try:
                ticket = Ticket.objects.get(id=ticket_id)
            except Ticket.DoesNotExist:
                messages.error(request, 'El ticket no existe.')
                return redirect('ticket_list')
            
            # Admin siempre tiene acceso
            if es_admin(request.user):
                return view_func(request, *args, **kwargs)
            
            # Permiso de visualización
            if permission_type == 'view':
                # Técnico, creador o asignado pueden ver
                if es_tecnico(request.user) or ticket.creador == request.user or ticket.asignado_a == request.user:
                    return view_func(request, *args, **kwargs)
            
            # Permiso de edición
            elif permission_type == 'edit':
                # Solo técnico, creador o asignado pueden editar
                if es_tecnico(request.user) or ticket.creador == request.user or ticket.asignado_a == request.user:
                    return view_func(request, *args, **kwargs)
            
            # Permiso de administrador
            elif permission_type == 'admin':
                if es_admin(request.user):
                    return view_func(request, *args, **kwargs)
            
            # Permiso de técnico
            elif permission_type == 'tecnico':
                if es_tecnico(request.user):
                    return view_func(request, *args, **kwargs)
            
            messages.error(request, 'No tienes permiso para acceder a este recurso.')
            return redirect('ticket_list')
        
        return wrapper
    return decorator


def verificar_y_actualizar_sla():
    """
    Verifica y actualiza automáticamente tickets que excedieron el SLA.
    Usa caching para evitar ejecutar en cada acceso (máximo 1 vez por hora).
    """
    cache_key = 'ultimo_check_sla'
    ultimo_check = cache.get(cache_key)
    
    # Si ya se verificó recientemente (dentro de 1 hora), no hacer nada
    if ultimo_check:
        return
    
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
    
    # Guardar en cache para no ejecutar nuevamente en 1 hora
    cache.set(cache_key, True, 3600)  # 3600 segundos = 1 hora
    
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
            
            # Enviar notificación a administradores cuando se crea un ticket
            from .models import Notificacion
            prioridad_notif = 'critica' if ticket.prioridad == 'urgente' else 'alta' if ticket.prioridad == 'alta' else 'media'
            administradores = User.objects.filter(groups__name=GRUPO_ADMINISTRADOR)
            for admin in administradores:
                crear_notificacion_completa(
                    usuario=admin,
                    ticket=ticket,
                    tipo='ticket_creado',
                    prioridad=prioridad_notif
                )
            
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
        ticket.tiempo_limite_resolucion = ticket.calcular_tiempo_limite_sla(horas_sla if horas_sla and horas_sla.strip() else None)
        
        # Registrar fecha de asignación si es la primera vez
        if not ticket.fecha_asignacion:
            ticket.fecha_asignacion = timezone.now()
        
        ticket.save()
        
        # Enviar notificación al técnico asignado (con manejo de error si no tiene perfil)
        try:
            prioridad_notif = 'critica' if ticket.prioridad == 'urgente' else 'alta' if ticket.prioridad == 'alta' else 'media'
            crear_notificacion_completa(
                usuario=tecnico,
                ticket=ticket,
                tipo='ticket_asignado',
                prioridad=prioridad_notif
            )
        except Exception as e:
            logger.error(f'Error al enviar notificación a {tecnico.username}: {str(e)}')
            messages.warning(
                request, 
                f'Ticket asignado pero no se pudo notificar al técnico. '
                f'Debe completar su perfil primero.'
            )
        
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
        
        messages.success(request, f'✓ Ticket asignado exitosamente a {tecnico.first_name or tecnico.username}')
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
            # Validar transición de estado
            if not ticket.puede_cambiar_estado_a(nuevo_estado):
                messages.error(
                    request, 
                    f'No se puede cambiar el ticket de "{ticket.estado}" a "{nuevo_estado}". '
                    f'Transiciones permitidas: {", ".join(ticket.obtener_transiciones_permitidas()) or "Ninguna"}'
                )
                return render(request, 'tickets/cambiar_estado.html', {
                    'ticket': ticket,
                    'estados': [
                        (estado, dict(Ticket.ESTADOS).get(estado, estado)) 
                        for estado in ticket.obtener_transiciones_permitidas()
                    ]
                })
            
            # Guarda el estado anterior
            estado_anterior = ticket.estado
            
            # Actualiza el ticket
            ticket.estado = nuevo_estado
            
            # Registrar fecha de cierre si el ticket se resuelve o cierra
            if nuevo_estado in ['resuelto', 'cerrado'] and not ticket.fecha_cierre:
                ticket.fecha_cierre = timezone.now()
            
            # Si se reabre un ticket
            if estado_anterior in ['resuelto', 'cerrado', 'tiempo_excedido'] and nuevo_estado in ['pendiente', 'en_progreso']:
                ticket.fue_reabierto = True
                ticket.fecha_cierre = None
                logger.warning(f'Ticket #{ticket.id} reabierto por {request.user.username}')
            
            ticket.save()
            
            # Enviar notificaciones según el cambio de estado
            if nuevo_estado == 'resuelto':
                # Notificar al creador que el ticket fue resuelto
                crear_notificacion_completa(
                    usuario=ticket.creador,
                    ticket=ticket,
                    tipo='ticket_resuelto',
                    prioridad='media'
                )
            elif nuevo_estado == 'cerrado':
                # Notificar al creador que el ticket fue cerrado
                crear_notificacion_completa(
                    usuario=ticket.creador,
                    ticket=ticket,
                    tipo='ticket_cerrado',
                    prioridad='baja'
                )
            elif nuevo_estado in ['pendiente', 'en_progreso']:
                # Si se reabre, notificar al técnico
                if ticket.asignado_a:
                    crear_notificacion_completa(
                        usuario=ticket.asignado_a,
                        ticket=ticket,
                        tipo='estado_cambio',
                        prioridad='alta'
                    )
            
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
            
            messages.success(request, f'Ticket actualizado a {nuevo_estado}')
        
        return redirect('ticket_detalle', ticket_id=ticket.id)
    
    # Obtener solo estados permitidos desde el estado actual
    transiciones_permitidas = ticket.obtener_transiciones_permitidas()
    estados_disponibles = [
        (estado, dict(Ticket.ESTADOS).get(estado, estado)) 
        for estado in transiciones_permitidas
    ]
    
    return render(request, 'tickets/cambiar_estado.html', {
        'ticket': ticket,
        'estados': estados_disponibles
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
            if not ticket.fecha_primera_respuesta and (es_tecnico(request.user) or es_admin(request.user)):
                ticket.fecha_primera_respuesta = timezone.now()
                ticket.save()
            
            # Enviar notificación de nuevo comentario
            usuarios_a_notificar = set()
            
            # Si el autor es técnico/admin, notificar al creador
            if es_tecnico(request.user) or es_admin(request.user):
                usuarios_a_notificar.add(ticket.creador)
            
            # Si el autor es creador/usuario, notificar al técnico asignado
            if es_creador or request.user == ticket.creador:
                if ticket.asignado_a:
                    usuarios_a_notificar.add(ticket.asignado_a)
            
            # Enviar notificaciones
            for usuario in usuarios_a_notificar:
                if usuario != request.user:  # No auto-notificar
                    crear_notificacion_completa(
                        usuario=usuario,
                        ticket=ticket,
                        tipo='ticket_comentario',
                        prioridad='media'
                    )
            
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
    # Obtener solo los tickets del usuario actual (optimizado con select_related)
    tickets_usuario = Ticket.objects.filter(creador=request.user).select_related('asignado_a').order_by('-fecha_creacion')
    
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


# ============================================
# PANEL DE ADMINISTRACIÓN DE USUARIOS
# ============================================

@login_required
@user_passes_test(es_admin)
def admin_panel(request):
    """Panel principal de administración"""
    # Estadísticas generales
    total_usuarios = User.objects.filter(is_active=True).count()
    total_roles = RolPersonalizado.objects.filter(activo=True).count()
    total_tickets = Ticket.objects.all().count()
    
    # Usuarios recientes
    usuarios_recientes = User.objects.filter(is_active=True).select_related('perfilusuario').order_by('-date_joined')[:5]
    
    context = {
        'total_usuarios': total_usuarios,
        'total_roles': total_roles,
        'total_tickets': total_tickets,
        'usuarios_recientes': usuarios_recientes,
    }
    
    return render(request, 'admin/panel.html', context)


@login_required
@user_passes_test(es_admin)
def admin_usuarios(request):
    """Lista y gestión de usuarios"""
    usuarios = User.objects.all().select_related('perfilusuario').prefetch_related('groups').order_by('-date_joined')
    
    # Filtros
    busqueda = request.GET.get('busqueda', '')
    grupo_filtro = request.GET.get('grupo', '')
    estado_filtro = request.GET.get('estado', '')
    
    if busqueda:
        usuarios = usuarios.filter(
            Q(username__icontains=busqueda) |
            Q(email__icontains=busqueda) |
            Q(first_name__icontains=busqueda) |
            Q(last_name__icontains=busqueda)
        )
    
    if grupo_filtro:
        usuarios = usuarios.filter(groups__name=grupo_filtro)
    
    if estado_filtro == 'activo':
        usuarios = usuarios.filter(is_active=True)
    elif estado_filtro == 'inactivo':
        usuarios = usuarios.filter(is_active=False)
    
    # Paginación
    paginator = Paginator(usuarios, 20)
    page_number = request.GET.get('page')
    usuarios_page = paginator.get_page(page_number)
    
    # Grupos disponibles
    grupos = Group.objects.all()
    
    context = {
        'usuarios': usuarios_page,
        'grupos': grupos,
        'busqueda': busqueda,
        'grupo_filtro': grupo_filtro,
        'estado_filtro': estado_filtro,
    }
    
    return render(request, 'admin/usuarios.html', context)


@login_required
@user_passes_test(es_admin)
def admin_crear_usuario(request):
    """Crear nuevo usuario manualmente"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        
        # Información del perfil
        telefono = request.POST.get('telefono', '')
        departamento = request.POST.get('departamento', '')
        cargo = request.POST.get('cargo', '')
        grupo_id = request.POST.get('grupo')
        rol_personalizado_id = request.POST.get('rol_personalizado')
        
        try:
            # Crear usuario
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            
            # Asignar grupo
            if grupo_id:
                grupo = Group.objects.get(id=grupo_id)
                user.groups.add(grupo)
            
            # Crear perfil
            perfil = PerfilUsuario.objects.create(
                user=user,
                telefono=telefono,
                departamento=departamento,
                cargo=cargo,
                creado_por=request.user
            )
            
            # Asignar rol personalizado
            if rol_personalizado_id:
                perfil.rol_personalizado_id = rol_personalizado_id
                perfil.save()
            
            logger.info(f'Usuario {username} creado manualmente por {request.user.username}')
            messages.success(request, f'Usuario {username} creado exitosamente.')
            return redirect('admin_usuarios')
            
        except Exception as e:
            logger.error(f'Error al crear usuario: {e}')
            messages.error(request, f'Error al crear usuario: {str(e)}')
    
    # GET - mostrar formulario
    grupos = Group.objects.all()
    roles = RolPersonalizado.objects.filter(activo=True)
    
    context = {
        'grupos': grupos,
        'roles': roles,
    }
    
    return render(request, 'admin/crear_usuario.html', context)


@login_required
@user_passes_test(es_admin)
def admin_editar_usuario(request, user_id):
    """Editar usuario existente"""
    usuario = get_object_or_404(User, id=user_id)
    
    # Crear perfil si no existe
    perfil, created = PerfilUsuario.objects.get_or_create(
        user=usuario,
        defaults={'creado_por': request.user}
    )
    
    if request.method == 'POST':
        # Actualizar datos básicos
        usuario.first_name = request.POST.get('first_name', '')
        usuario.last_name = request.POST.get('last_name', '')
        usuario.email = request.POST.get('email', '')
        
        usuario.save()
        
        # Actualizar perfil
        perfil.telefono = request.POST.get('telefono', '')
        perfil.departamento = request.POST.get('departamento', '')
        perfil.cargo = request.POST.get('cargo', '')
        
        # Actualizar grupo
        grupo_id = request.POST.get('grupo')
        if grupo_id:
            usuario.groups.clear()
            grupo = Group.objects.get(id=grupo_id)
            usuario.groups.add(grupo)
        
        # Actualizar rol personalizado
        rol_personalizado_id = request.POST.get('rol_personalizado')
        if rol_personalizado_id:
            perfil.rol_personalizado_id = rol_personalizado_id
        else:
            perfil.rol_personalizado = None
        
        perfil.save()
        
        logger.info(f'Usuario {usuario.username} actualizado por {request.user.username}')
        messages.success(request, f'Usuario {usuario.username} actualizado exitosamente.')
        return redirect('admin_usuarios')
    
    # GET - mostrar formulario
    grupos = Group.objects.all()
    roles = RolPersonalizado.objects.filter(activo=True)
    grupo_actual = usuario.groups.first()
    
    context = {
        'usuario': usuario,
        'perfil': perfil,
        'grupos': grupos,
        'roles': roles,
        'grupo_actual': grupo_actual,
    }
    
    return render(request, 'admin/editar_usuario.html', context)


@login_required
@user_passes_test(es_admin)
def admin_toggle_usuario(request, user_id):
    """Activar/Desactivar usuario"""
    if request.method == 'POST':
        usuario = get_object_or_404(User, id=user_id)
        
        # No permitir desactivar al propio usuario
        if usuario == request.user:
            messages.error(request, 'No puedes desactivarte a ti mismo.')
            return redirect('admin_usuarios')
        
        usuario.is_active = not usuario.is_active
        usuario.save()
        
        # Actualizar perfil
        if hasattr(usuario, 'perfil'):
            usuario.perfil.activo = usuario.is_active
            usuario.perfil.save()
        
        estado = 'activado' if usuario.is_active else 'desactivado'
        logger.info(f'Usuario {usuario.username} {estado} por {request.user.username}')
        messages.success(request, f'Usuario {usuario.username} {estado} exitosamente.')
    
    return redirect('admin_usuarios')


@login_required
@user_passes_test(es_admin)
def admin_eliminar_usuario(request, user_id):
    """Eliminar usuario (con confirmación)"""
    if request.method == 'POST':
        usuario = get_object_or_404(User, id=user_id)
        
        # No permitir eliminar al propio usuario
        if usuario == request.user:
            messages.error(request, 'No puedes eliminarte a ti mismo.')
            return redirect('admin_usuarios')
        
        # No permitir eliminar superusuarios
        if usuario.is_superuser:
            messages.error(request, 'No puedes eliminar un superusuario.')
            return redirect('admin_usuarios')
        
        username = usuario.username
        usuario.delete()
        
        logger.warning(f'Usuario {username} eliminado por {request.user.username}')
        messages.success(request, f'Usuario {username} eliminado exitosamente.')
    
    return redirect('admin_usuarios')



# ============================================
# GESTIÓN DE ROLES PERSONALIZADOS
# ============================================

@login_required
@user_passes_test(es_admin)
def admin_roles(request):
    """Lista de roles personalizados"""
    roles = RolPersonalizado.objects.annotate(
        num_usuarios=Count('usuarios')
    ).order_by('nombre')
    
    context = {
        'roles': roles,
    }
    
    return render(request, 'admin/roles.html', context)


@login_required
@user_passes_test(es_admin)
def admin_crear_rol(request):
    """Crear nuevo rol personalizado"""
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion', '')
        color = request.POST.get('color', '#3498db')
        
        # Permisos
        puede_ver_metricas = request.POST.get('puede_ver_metricas') == 'on'
        puede_ver_todos_tickets = request.POST.get('puede_ver_todos_tickets') == 'on'
        puede_asignar_tickets = request.POST.get('puede_asignar_tickets') == 'on'
        puede_cambiar_estado = request.POST.get('puede_cambiar_estado') == 'on'
        puede_gestionar_usuarios = request.POST.get('puede_gestionar_usuarios') == 'on'
        puede_crear_roles = request.POST.get('puede_crear_roles') == 'on'
        
        try:
            rol = RolPersonalizado.objects.create(
                nombre=nombre,
                descripcion=descripcion,
                color=color,
                puede_ver_metricas=puede_ver_metricas,
                puede_ver_todos_tickets=puede_ver_todos_tickets,
                puede_asignar_tickets=puede_asignar_tickets,
                puede_cambiar_estado=puede_cambiar_estado,
                puede_gestionar_usuarios=puede_gestionar_usuarios,
                puede_crear_roles=puede_crear_roles,
                creado_por=request.user
            )
            
            logger.info(f'Rol {nombre} creado por {request.user.username}')
            messages.success(request, f'Rol {nombre} creado exitosamente.')
            return redirect('admin_roles')
            
        except Exception as e:
            logger.error(f'Error al crear rol: {e}')
            messages.error(request, f'Error al crear rol: {str(e)}')
    
    return render(request, 'admin/crear_rol.html')


@login_required
@user_passes_test(es_admin)
def admin_editar_rol(request, rol_id):
    """Editar rol personalizado"""
    rol = get_object_or_404(RolPersonalizado, id=rol_id)
    
    if request.method == 'POST':
        rol.nombre = request.POST.get('nombre')
        rol.descripcion = request.POST.get('descripcion', '')
        rol.color = request.POST.get('color', '#3498db')
        
        # Permisos
        rol.puede_ver_metricas = request.POST.get('puede_ver_metricas') == 'on'
        rol.puede_ver_todos_tickets = request.POST.get('puede_ver_todos_tickets') == 'on'
        rol.puede_asignar_tickets = request.POST.get('puede_asignar_tickets') == 'on'
        rol.puede_cambiar_estado = request.POST.get('puede_cambiar_estado') == 'on'
        rol.puede_gestionar_usuarios = request.POST.get('puede_gestionar_usuarios') == 'on'
        rol.puede_crear_roles = request.POST.get('puede_crear_roles') == 'on'
        rol.activo = request.POST.get('activo') == 'on'
        
        rol.save()
        
        logger.info(f'Rol {rol.nombre} actualizado por {request.user.username}')
        messages.success(request, f'Rol {rol.nombre} actualizado exitosamente.')
        return redirect('admin_roles')
    
    context = {
        'rol': rol,
    }
    
    return render(request, 'admin/editar_rol.html', context)


@login_required
@user_passes_test(es_admin)
def admin_eliminar_rol(request, rol_id):
    """Eliminar rol personalizado"""
    if request.method == 'POST':
        rol = get_object_or_404(RolPersonalizado, id=rol_id)
        
        # Verificar que no haya usuarios con este rol
        if rol.usuarios.exists():
            messages.error(request, f'No se puede eliminar el rol {rol.nombre} porque tiene usuarios asignados.')
            return redirect('admin_roles')
        
        nombre = rol.nombre
        rol.delete()
        
        logger.warning(f'Rol {nombre} eliminado por {request.user.username}')
        messages.success(request, f'Rol {nombre} eliminado exitosamente.')
    
    return redirect('admin_roles')


# ============================================
# SISTEMA DE INVITACIONES - ELIMINADO
# ============================================


# ============================================
# CONFIGURACIÓN Y PERFIL DE USUARIO
# ============================================

@login_required
def mi_perfil(request):
    """Vista de perfil y configuración del usuario autenticado"""
    usuario = request.user
    perfil, created = PerfilUsuario.objects.get_or_create(
        user=usuario,
        defaults={'creado_por': usuario}
    )
    
    if request.method == 'POST':
        accion = request.POST.get('accion')
        
        # Actualizar información del perfil
        if accion == 'actualizar_perfil':
            usuario.first_name = request.POST.get('first_name', '')
            usuario.last_name = request.POST.get('last_name', '')
            usuario.email = request.POST.get('email', '')
            usuario.save()
            
            perfil.telefono = request.POST.get('telefono', '')
            perfil.departamento = request.POST.get('departamento', '')
            perfil.cargo = request.POST.get('cargo', '')
            
            # Actualizar foto de perfil si se proporciona
            if 'foto_perfil' in request.FILES:
                archivo = request.FILES['foto_perfil']
                # Validar tipo de archivo
                if archivo.content_type.startswith('image/'):
                    perfil.foto_perfil = archivo
                else:
                    messages.error(request, 'Por favor sube un archivo de imagen válido.')
                    return redirect('mi_perfil')
            
            perfil.save()
            logger.info(f'Usuario {usuario.username} actualizó su perfil')
            messages.success(request, 'Perfil actualizado exitosamente.')
            return redirect('mi_perfil')
        
        # Cambiar contraseña
        elif accion == 'cambiar_password':
            password_actual = request.POST.get('password_actual')
            password_nueva = request.POST.get('password_nueva')
            password_confirmacion = request.POST.get('password_confirmacion')
            
            # Validar contraseña actual
            if not usuario.check_password(password_actual):
                messages.error(request, 'La contraseña actual es incorrecta.')
                return redirect('mi_perfil')
            
            # Validar que las nuevas contraseñas coincidan
            if password_nueva != password_confirmacion:
                messages.error(request, 'Las nuevas contraseñas no coinciden.')
                return redirect('mi_perfil')
            
            # Validar mínimo de caracteres
            if len(password_nueva) < 8:
                messages.error(request, 'La nueva contraseña debe tener al menos 8 caracteres.')
                return redirect('mi_perfil')
            
            # Cambiar contraseña
            usuario.set_password(password_nueva)
            usuario.save()
            
            logger.info(f'Usuario {usuario.username} cambió su contraseña')
            messages.success(request, 'Contraseña cambio exitosamente. Por favor inicia sesión nuevamente.')
            return redirect('login')
    
    # GET - mostrar formulario
    grupo_actual = usuario.groups.first()
    
    context = {
        'usuario': usuario,
        'perfil': perfil,
        'grupo_actual': grupo_actual,
    }
    
    return render(request, 'tickets/mi_perfil.html', context)


# ==================== API ENDPOINTS DE NOTIFICACIONES ====================

@login_required
def api_notificaciones(request):
    """
    API para obtener todas las notificaciones del usuario autenticado.
    
    GET /api/notificaciones/?limite=20
    
    Retorna: JSON con lista de notificaciones (máximo 20 por defecto)
    """
    from django.http import JsonResponse
    from .models import Notificacion
    from .services import obtener_todas_notificaciones
    
    try:
        limite = int(request.GET.get('limite', 20))
        notificaciones = obtener_todas_notificaciones(request.user, limite=limite)
        
        data = []
        for notif in notificaciones:
            data.append({
                'id': notif.id,
                'titulo': notif.titulo,
                'tipo': notif.tipo,
                'prioridad': notif.prioridad,
                'leida': notif.leida,
                'fecha_creacion': notif.fecha_creacion.isoformat(),
                'ticket_id': notif.ticket_id,
                'enlace': notif.enlace
            })
        
        return JsonResponse({'notificaciones': data, 'total': len(data)})
    
    except Exception as e:
        logger.error(f'Error al obtener notificaciones: {str(e)}')
        return JsonResponse({'error': 'Error al obtener notificaciones'}, status=400)


@login_required
def api_notificaciones_nuevas(request):
    """
    API para obtener solo las notificaciones no leídas del usuario.
    
    GET /api/notificaciones/nuevas/?limite=5
    
    Retorna: JSON con lista de notificaciones no leídas (máximo 5 por defecto)
    """
    from django.http import JsonResponse
    from .services import obtener_notificaciones_no_leidas
    
    try:
        limite = int(request.GET.get('limite', 5))
        notificaciones = obtener_notificaciones_no_leidas(request.user, limite=limite)
        
        data = []
        for notif in notificaciones:
            data.append({
                'id': notif.id,
                'titulo': notif.titulo,
                'mensaje': notif.mensaje[:100],  # Solo primeros 100 caracteres
                'tipo': notif.tipo,
                'prioridad': notif.prioridad,
                'fecha_creacion': notif.fecha_creacion.isoformat(),
                'ticket_id': notif.ticket_id,
                'enlace': notif.enlace
            })
        
        return JsonResponse({'notificaciones': data, 'total': len(data)})
    
    except Exception as e:
        logger.error(f'Error al obtener notificaciones nuevas: {str(e)}')
        return JsonResponse({'error': 'Error al obtener notificaciones'}, status=400)


@login_required
def api_marcar_notificacion_leida(request, notificacion_id):
    """
    API para marcar una notificación específica como leída.
    
    POST /api/notificaciones/<id>/marcar-leida/
    
    Retorna: JSON con estado de la operación
    """
    from django.http import JsonResponse
    from .models import Notificacion
    from .services import marcar_notificacion_leida
    
    try:
        notificacion = get_object_or_404(Notificacion, id=notificacion_id, usuario=request.user)
        marcar_notificacion_leida(notificacion)
        
        return JsonResponse({'success': True, 'mensaje': 'Notificación marcada como leída'})
    
    except Notificacion.DoesNotExist:
        return JsonResponse({'error': 'Notificación no encontrada'}, status=404)
    except Exception as e:
        logger.error(f'Error al marcar notificación como leída: {str(e)}')
        return JsonResponse({'error': 'Error al procesar la solicitud'}, status=400)


@login_required
def api_marcar_todas_leidas(request):
    """
    API para marcar todas las notificaciones del usuario como leídas.
    
    POST /api/notificaciones/marcar-todas-leidas/
    
    Retorna: JSON con estado de la operación
    """
    from django.http import JsonResponse
    from .services import marcar_todas_leidas
    
    try:
        marcar_todas_leidas(request.user)
        return JsonResponse({'success': True, 'mensaje': 'Todas las notificaciones marcadas como leídas'})
    
    except Exception as e:
        logger.error(f'Error al marcar todas las notificaciones como leídas: {str(e)}')
        return JsonResponse({'error': 'Error al procesar la solicitud'}, status=400)


@login_required
def lista_notificaciones(request):
    """
    Vista para ver todas las notificaciones del usuario actual.
    
    GET /notificaciones/
    
    Parámetros:
    - tipo: Filtrar por tipo de notificación
    - prioridad: Filtrar por prioridad
    - leida: Filtrar por estado de lectura (true/false)
    """
    from .models import Notificacion
    from django.db.models import Q
    
    try:
        # Obtener todas las notificaciones del usuario
        notificaciones = Notificacion.objects.filter(usuario=request.user).order_by('-fecha_creacion')
        
        # Filtros
        tipo_filtro = request.GET.get('tipo')
        if tipo_filtro:
            notificaciones = notificaciones.filter(tipo=tipo_filtro)
        
        prioridad_filtro = request.GET.get('prioridad')
        if prioridad_filtro:
            notificaciones = notificaciones.filter(prioridad=prioridad_filtro)
        
        leida_filtro = request.GET.get('leida')
        if leida_filtro:
            leida_bool = leida_filtro.lower() == 'true'
            notificaciones = notificaciones.filter(leida=leida_bool)
        
        # Paginación
        paginator = Paginator(notificaciones, 20)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        
        context = {
            'notificaciones': page_obj,
            'paginator': paginator,
            'page_number': page_number,
            'total_notificaciones': notificaciones.count(),
            'tipos_notificacion': Notificacion.TIPOS_NOTIFICACION,
            'prioridades': Notificacion.PRIORIDADES,
            'tipo_filtro': tipo_filtro,
            'prioridad_filtro': prioridad_filtro,
            'leida_filtro': leida_filtro,
        }
        
        return render(request, 'tickets/lista_notificaciones.html', context)
    
    except Exception as e:
        logger.error(f'Error al obtener lista de notificaciones: {str(e)}')
        messages.error(request, 'Error al cargar las notificaciones')
        return redirect('ticket_list')


# API endpoint para obtener subcategorías filtradas por categoría (para selects dependientes)
@login_required
def obtener_subcategorias(request, categoria_id):
    """
    Vista API que retorna las subcategorías de una categoría específica en formato JSON.
    Utilizada por JavaScript para actualizar dinámicamente el select de subcategorías.
    
    GET /api/subcategorias/<categoria_id>/
    
    Retorna: JSON con lista de subcategorías activas
    Ejemplo: [{"id": 1, "nombre": "Nómina"}, {"id": 2, "nombre": "Facturas"}]
    """
    from django.http import JsonResponse
    from .models import Subcategoria
    
    try:
        # Obtener todas las subcategorías activas de la categoría especificada
        subcategorias = Subcategoria.objects.filter(
            categoria_id=categoria_id,
            activa=True
        ).values('id', 'nombre').order_by('nombre')
        
        return JsonResponse(list(subcategorias), safe=False)
    
    except Exception as e:
        logger.error(f'Error al obtener subcategorías: {str(e)}')
        return JsonResponse({'error': 'Error al obtener subcategorías'}, status=400)


# ==================== GESTIÓN DE CATEGORÍAS Y SUBCATEGORÍAS ====================

@login_required
@user_passes_test(es_admin)
def admin_categorias(request):
    """
    Vista para gestionar categorías en el panel de admin.
    Permite ver, crear, editar y eliminar categorías.
    """
    from .models import Categoria
    
    categorias = Categoria.objects.all().order_by('nombre')
    
    context = {
        'categorias': categorias,
        'total_categorias': categorias.count(),
    }
    
    return render(request, 'admin/categorias.html', context)


@login_required
@user_passes_test(es_admin)
def admin_crear_categoria(request):
    """
    Vista para crear una nueva categoría.
    Valida que el nombre no esté duplicado.
    """
    from .models import Categoria
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        
        # Validaciones
        if not nombre:
            messages.error(request, 'El nombre de la categoría es requerido.')
            return redirect('admin_categorias')
        
        # Verificar duplicado
        if Categoria.objects.filter(nombre__iexact=nombre).exists():
            messages.error(request, f'Ya existe una categoría con el nombre "{nombre}".')
            return redirect('admin_categorias')
        
        # Crear categoría
        try:
            Categoria.objects.create(
                nombre=nombre,
                descripcion=descripcion,
                activa=True
            )
            logger.info(f'Admin {request.user.username} creó categoría: {nombre}')
            messages.success(request, f'Categoría "{nombre}" creada exitosamente.')
        except Exception as e:
            logger.error(f'Error al crear categoría: {str(e)}')
            messages.error(request, 'Error al crear la categoría.')
        
        return redirect('admin_categorias')
    
    return render(request, 'admin/crear_categoria.html')


@login_required
@user_passes_test(es_admin)
def admin_editar_categoria(request, categoria_id):
    """
    Vista para editar una categoría existente.
    """
    from .models import Categoria
    
    categoria = get_object_or_404(Categoria, id=categoria_id)
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        activa = request.POST.get('activa') == 'on'
        
        # Validaciones
        if not nombre:
            messages.error(request, 'El nombre de la categoría es requerido.')
            return redirect('admin_editar_categoria', categoria_id=categoria_id)
        
        # Verificar duplicado (excluyendo la categoría actual)
        if Categoria.objects.filter(nombre__iexact=nombre).exclude(id=categoria_id).exists():
            messages.error(request, f'Ya existe otra categoría con el nombre "{nombre}".')
            return redirect('admin_editar_categoria', categoria_id=categoria_id)
        
        # Actualizar categoría
        try:
            categoria.nombre = nombre
            categoria.descripcion = descripcion
            categoria.activa = activa
            categoria.save()
            logger.info(f'Admin {request.user.username} editó categoría: {nombre}')
            messages.success(request, f'Categoría "{nombre}" actualizada exitosamente.')
        except Exception as e:
            logger.error(f'Error al editar categoría: {str(e)}')
            messages.error(request, 'Error al actualizar la categoría.')
        
        return redirect('admin_categorias')
    
    context = {'categoria': categoria}
    return render(request, 'admin/editar_categoria.html', context)


@login_required
@user_passes_test(es_admin)
def admin_eliminar_categoria(request, categoria_id):
    """
    Vista para eliminar una categoría.
    Verifica que no tenga tickets asociados.
    """
    from .models import Categoria
    
    categoria = get_object_or_404(Categoria, id=categoria_id)
    
    # Contar tickets asociados
    tickets_count = categoria.tickets.count()
    
    if tickets_count > 0:
        messages.error(request, f'No se puede eliminar la categoría "{categoria.nombre}" porque tiene {tickets_count} ticket(s) asociado(s).')
        return redirect('admin_categorias')
    
    try:
        nombre = categoria.nombre
        categoria.delete()
        logger.info(f'Admin {request.user.username} eliminó categoría: {nombre}')
        messages.success(request, f'Categoría "{nombre}" eliminada exitosamente.')
    except Exception as e:
        logger.error(f'Error al eliminar categoría: {str(e)}')
        messages.error(request, 'Error al eliminar la categoría.')
    
    return redirect('admin_categorias')


@login_required
@user_passes_test(es_admin)
def admin_subcategorias(request):
    """
    Vista para gestionar subcategorías en el panel de admin.
    Permite ver, crear, editar y eliminar subcategorías.
    """
    from .models import Subcategoria, Categoria
    
    categoria_id = request.GET.get('categoria')
    
    if categoria_id:
        try:
            categoria = Categoria.objects.get(id=categoria_id)
            subcategorias = categoria.subcategorias.all().order_by('nombre')
        except Categoria.DoesNotExist:
            messages.error(request, 'Categoría no encontrada.')
            return redirect('admin_subcategorias')
    else:
        categoria = None
        subcategorias = Subcategoria.objects.all().order_by('categoria__nombre', 'nombre')
    
    categorias = Categoria.objects.all().order_by('nombre')
    
    context = {
        'categorias': categorias,
        'subcategorias': subcategorias,
        'categoria_seleccionada': categoria,
        'total_subcategorias': subcategorias.count(),
    }
    
    return render(request, 'admin/subcategorias.html', context)


@login_required
@user_passes_test(es_admin)
def admin_crear_subcategoria(request):
    """
    Vista para crear una nueva subcategoría.
    """
    from .models import Categoria, Subcategoria
    
    if request.method == 'POST':
        categoria_id = request.POST.get('categoria')
        nombre = request.POST.get('nombre', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        
        # Validaciones
        if not categoria_id:
            messages.error(request, 'Debes seleccionar una categoría.')
            return redirect('admin_subcategorias')
        
        if not nombre:
            messages.error(request, 'El nombre de la subcategoría es requerido.')
            return redirect('admin_subcategorias')
        
        try:
            categoria = Categoria.objects.get(id=categoria_id)
        except Categoria.DoesNotExist:
            messages.error(request, 'Categoría no encontrada.')
            return redirect('admin_subcategorias')
        
        # Verificar duplicado en la misma categoría
        if Subcategoria.objects.filter(categoria=categoria, nombre__iexact=nombre).exists():
            messages.error(request, f'Ya existe una subcategoría "{nombre}" en la categoría "{categoria.nombre}".')
            return redirect('admin_subcategorias')
        
        # Crear subcategoría
        try:
            Subcategoria.objects.create(
                categoria=categoria,
                nombre=nombre,
                descripcion=descripcion,
                activa=True
            )
            logger.info(f'Admin {request.user.username} creó subcategoría: {nombre} en {categoria.nombre}')
            messages.success(request, f'Subcategoría "{nombre}" creada en "{categoria.nombre}".')
        except Exception as e:
            logger.error(f'Error al crear subcategoría: {str(e)}')
            messages.error(request, 'Error al crear la subcategoría.')
        
        return redirect('admin_subcategorias')
    
    categorias = Categoria.objects.all().order_by('nombre')
    context = {'categorias': categorias}
    return render(request, 'admin/crear_subcategoria.html', context)


@login_required
@user_passes_test(es_admin)
def admin_editar_subcategoria(request, subcategoria_id):
    """
    Vista para editar una subcategoría existente.
    """
    from .models import Subcategoria, Categoria
    
    subcategoria = get_object_or_404(Subcategoria, id=subcategoria_id)
    
    if request.method == 'POST':
        categoria_id = request.POST.get('categoria')
        nombre = request.POST.get('nombre', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        activa = request.POST.get('activa') == 'on'
        
        # Validaciones
        if not categoria_id:
            messages.error(request, 'Debes seleccionar una categoría.')
            return redirect('admin_editar_subcategoria', subcategoria_id=subcategoria_id)
        
        if not nombre:
            messages.error(request, 'El nombre de la subcategoría es requerido.')
            return redirect('admin_editar_subcategoria', subcategoria_id=subcategoria_id)
        
        try:
            categoria = Categoria.objects.get(id=categoria_id)
        except Categoria.DoesNotExist:
            messages.error(request, 'Categoría no encontrada.')
            return redirect('admin_editar_subcategoria', subcategoria_id=subcategoria_id)
        
        # Verificar duplicado (excluyendo la subcategoría actual)
        if Subcategoria.objects.filter(
            categoria=categoria,
            nombre__iexact=nombre
        ).exclude(id=subcategoria_id).exists():
            messages.error(request, f'Ya existe otra subcategoría "{nombre}" en la categoría "{categoria.nombre}".')
            return redirect('admin_editar_subcategoria', subcategoria_id=subcategoria_id)
        
        # Actualizar subcategoría
        try:
            subcategoria.categoria = categoria
            subcategoria.nombre = nombre
            subcategoria.descripcion = descripcion
            subcategoria.activa = activa
            subcategoria.save()
            logger.info(f'Admin {request.user.username} editó subcategoría: {nombre}')
            messages.success(request, f'Subcategoría "{nombre}" actualizada exitosamente.')
        except Exception as e:
            logger.error(f'Error al editar subcategoría: {str(e)}')
            messages.error(request, 'Error al actualizar la subcategoría.')
        
        return redirect('admin_subcategorias')
    
    categorias = Categoria.objects.all().order_by('nombre')
    context = {
        'subcategoria': subcategoria,
        'categorias': categorias,
    }
    return render(request, 'admin/editar_subcategoria.html', context)


@login_required
@user_passes_test(es_admin)
def admin_eliminar_subcategoria(request, subcategoria_id):
    """
    Vista para eliminar una subcategoría.
    Verifica que no tenga tickets asociados.
    """
    from .models import Subcategoria
    
    subcategoria = get_object_or_404(Subcategoria, id=subcategoria_id)
    
    # Contar tickets asociados
    tickets_count = subcategoria.tickets.count()
    
    if tickets_count > 0:
        messages.error(request, f'No se puede eliminar la subcategoría "{subcategoria.nombre}" porque tiene {tickets_count} ticket(s) asociado(s).')
        return redirect('admin_subcategorias')
    
    try:
        nombre = subcategoria.nombre
        categoria_nombre = subcategoria.categoria.nombre
        subcategoria.delete()
        logger.info(f'Admin {request.user.username} eliminó subcategoría: {nombre}')
        messages.success(request, f'Subcategoría "{nombre}" eliminada exitosamente.')
    except Exception as e:
        logger.error(f'Error al eliminar subcategoría: {str(e)}')
        messages.error(request, 'Error al eliminar la subcategoría.')
    
    return redirect('admin_subcategorias')
