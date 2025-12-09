from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.cache import cache
from django.db.models import Q, Avg, Count, Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponseForbidden, JsonResponse
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


# ============================================
# FUNCIONES DE VERIFICACIÓN DE PERMISOS
# ============================================

def obtener_permisos_rol_personalizado(user):
    """Obtiene los permisos del rol personalizado del usuario si existe"""
    try:
        perfil = user.perfilusuario
        if perfil.rol_personalizado and perfil.rol_personalizado.activo:
            return perfil.rol_personalizado
    except (PerfilUsuario.DoesNotExist, AttributeError):
        pass
    return None


def tiene_permiso_rol(user, permiso):
    """Verifica si el usuario tiene un permiso específico a través de su rol personalizado"""
    rol = obtener_permisos_rol_personalizado(user)
    if rol:
        return getattr(rol, permiso, False)
    return False


# Función auxiliar para verificar si un usuario pertenece al grupo Administrador
def es_admin(user):
    # Primero verifica grupo tradicional
    if user.groups.filter(name=GRUPO_ADMINISTRADOR).exists():
        return True
    # Luego verifica si tiene todos los permisos de admin via rol personalizado
    rol = obtener_permisos_rol_personalizado(user)
    if rol:
        # Un usuario con rol personalizado es "admin" si tiene permisos de gestión
        return rol.puede_gestionar_usuarios and rol.puede_crear_roles
    return False


# Función auxiliar para verificar si un usuario es técnico
def es_tecnico(user):
    # Primero verifica grupo tradicional
    if user.groups.filter(name=GRUPO_TECNICO).exists():
        return True
    # Luego verifica si tiene permisos de técnico via rol personalizado
    rol = obtener_permisos_rol_personalizado(user)
    if rol:
        return rol.puede_cambiar_estado or rol.puede_asignar_tickets
    return False


# Función auxiliar para verificar si un usuario es usuario regular
def es_usuario_regular(user):
    return user.groups.filter(name=GRUPO_USUARIO).exists()


# Funciones específicas para verificar permisos individuales del rol personalizado
def puede_ver_metricas(user):
    """Verifica si el usuario puede ver métricas"""
    if es_admin(user):
        return True
    return tiene_permiso_rol(user, 'puede_ver_metricas')


def puede_ver_todos_tickets(user):
    """Verifica si el usuario puede ver todos los tickets"""
    if es_admin(user) or es_tecnico(user):
        return True
    return tiene_permiso_rol(user, 'puede_ver_todos_tickets')


def puede_asignar_tickets(user):
    """Verifica si el usuario puede asignar tickets"""
    if es_admin(user):
        return True
    return tiene_permiso_rol(user, 'puede_asignar_tickets')


def puede_autoasignarse_tickets(user):
    """Verifica si el usuario (técnico) puede autoasignarse tickets"""
    # Solo los técnicos pueden autoasignarse tickets
    return es_tecnico(user)


def puede_cambiar_estado(user):
    """Verifica si el usuario puede cambiar estado de tickets"""
    if es_admin(user) or es_tecnico(user):
        return True
    return tiene_permiso_rol(user, 'puede_cambiar_estado')


def puede_gestionar_usuarios(user):
    """Verifica si el usuario puede gestionar usuarios"""
    if es_admin(user):
        return True
    return tiene_permiso_rol(user, 'puede_gestionar_usuarios')


def puede_crear_roles(user):
    """Verifica si el usuario puede crear roles"""
    if es_admin(user):
        return True
    return tiene_permiso_rol(user, 'puede_crear_roles')


def puede_validar_prioridad(user):
    """Verifica si el usuario puede validar prioridades auto-detectadas (Supervisores)"""
    if es_admin(user):
        return True
    return tiene_permiso_rol(user, 'puede_validar_prioridad')


def detectar_prioridad_automatica(titulo, descripcion, tipo_solicitud=None):
    """
    Detecta automáticamente la prioridad de un ticket basándose en palabras clave
    y el tipo de solicitud seleccionado.
    
    Sistema híbrido inteligente que:
    - Detecta palabras individuales y frases exactas
    - Combina dispositivos + problemas para mejor precisión
    - Ajusta la prioridad según el tipo de solicitud (problema, incidencia, solicitud, cambio)
    
    Args:
        titulo: Título del ticket
        descripcion: Descripción del ticket
        tipo_solicitud: Tipo de ticket ('incidencia', 'solicitud', 'problema', 'cambio')
                       Si es None, no se aplica modificador por tipo.
    
    Returns:
        tuple: (prioridad_detectada, nivel_confianza, palabras_encontradas)
        - prioridad_detectada: 'critica', 'alta', 'media', 'baja'
        - nivel_confianza: 'alta', 'media', 'baja'
        - palabras_encontradas: lista de palabras clave detectadas
    """
    import re
    import unicodedata
    
    def normalizar_texto(texto):
        """Normaliza el texto: minúsculas, sin acentos, sin caracteres especiales"""
        texto = texto.lower()
        texto = unicodedata.normalize('NFD', texto)
        texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
        return texto
    
    def buscar_palabra(palabra, texto):
        """Busca una palabra individual con límites de palabra"""
        palabra_escaped = re.escape(palabra)
        patron = r'(?:^|[\s,.\-_;:!?¿¡()\[\]{}"\'/])' + palabra_escaped + r'(?:$|[\s,.\-_;:!?¿¡()\[\]{}"\'/]|s\b|es\b|n\b)'
        return bool(re.search(patron, texto))
    
    def buscar_frase(frase, texto):
        """Busca una frase exacta en el texto"""
        return frase in texto
    
    # Normalizar texto de entrada
    texto_normalizado = normalizar_texto(f"{titulo} {descripcion}")
    palabras_encontradas = []
    
    # ============================================
    # PALABRAS CLAVE CRÍTICAS (peso: 2 puntos)
    # ============================================
    
    palabras_criticas_individuales = [
        'urgente', 'urgentisimo', 'emergencia', 'critico', 'critica',
        'hackeo', 'hackeado', 'hackearon', 'virus', 'ransomware', 'malware',
        'incendio', 'accidente', 'inmediato', 'inmediatamente',
        'colapso', 'colapsado', 'caido', 'caida', 'paralizado', 'paralizada',
        'corrupta', 'corrupto', 'corrupcion', 'ataque', 'atacaron',
        'robo', 'robaron', 'intrusion', 'vulnerabilidad',
        'servidor'  # Un problema de servidor generalmente afecta a muchos usuarios
    ]
    
    frases_criticas = [
        'sistema caido', 'servidor caido', 'red caida', 'internet caido',
        'servidor no responde', 'servidor no funciona', 'servidores caidos',
        'no funciona nada', 'nada funciona', 'todo caido', 'todo parado',
        'perdida de datos', 'perdieron datos', 'se borraron',
        'produccion detenida', 'produccion parada', 'planta parada',
        'no podemos trabajar', 'nadie puede trabajar', 'empresa parada',
        'base de datos corrupta', 'bd corrupta', 'datos corruptos',
        'ahora mismo', 'ya mismo', 'en este momento', 'de inmediato',
        'toda la empresa', 'todo el departamento', 'todos afectados',
        'bloqueo total', 'bloqueado totalmente', 'sin acceso total',
        'seguridad comprometida', 'brecha de seguridad',
        'sistema no responde', 'sistema no funciona', 'sin sistema',
        'sin servidor', 'sin servicio', 'servicio caido'
    ]
    
    # ============================================
    # PALABRAS CLAVE ALTA - PROBLEMAS (peso: 1.5 puntos)
    # Estas palabras por sí solas indican un problema
    # ============================================
    
    palabras_problema = [
        'error', 'falla', 'fallo', 'averia', 'defecto', 'bug',
        'bloqueado', 'bloqueada', 'congelado', 'congelada', 'trabado', 'trabada',
        'colgado', 'colgada', 'lento', 'lenta', 'lentisimo',
        'danado', 'danada', 'roto', 'rota', 'quemado', 'quemada', 'malogrado',
        'descompuesto', 'descompuesta', 'estropeado', 'estropeada'
    ]
    
    frases_problema = [
        'no funciona', 'no enciende', 'no prende', 'no inicia', 'no arranca',
        'no responde', 'no carga', 'no abre', 'no imprime', 'no conecta',
        'no reconoce', 'no detecta', 'no lee', 'no guarda', 'no graba',
        'dejo de funcionar', 'dejo de andar', 'se apago', 'se apaga solo',
        'se reinicia solo', 'se reinicia', 'se traba', 'se congela', 'se cuelga',
        'pantalla negra', 'pantalla azul', 'pantalla en negro',
        'sin conexion', 'sin internet', 'sin red', 'sin wifi', 'sin senal',
        'muy lento', 'demasiado lento', 'extremadamente lento',
        'esta fallando', 'esta malo', 'no sirve', 'no anda'
    ]
    
    # ============================================
    # PALABRAS CLAVE ALTA - URGENCIA (peso: 1.5 puntos)
    # ============================================
    
    palabras_urgencia = [
        'importante', 'prioritario', 'priority', 'rapido', 'rapidamente',
        'pronto', 'deadline', 'auditoria', 'presentacion'
    ]
    
    frases_urgencia = [
        'varios usuarios', 'afecta varios', 'multiples usuarios',
        'equipo completo', 'todo el equipo', 'varios equipos',
        'cliente importante', 'cliente vip', 'cuenta importante',
        'fecha limite', 'plazo limite', 'entrega manana', 'para hoy',
        'cuanto antes', 'lo antes posible', 'asap', 'necesito ya',
        'afecta negocio', 'afecta ventas', 'afecta produccion',
        'reunion urgente', 'junta urgente', 'llamada importante'
    ]
    
    # ============================================
    # DISPOSITIVOS/HARDWARE (NO suman por sí solos)
    # Solo se usan para detectar contexto
    # Nota: 'servidor' NO está aquí porque es crítico por naturaleza
    # ============================================
    
    dispositivos = [
        'monitor', 'pantalla', 'teclado', 'mouse', 'raton',
        'impresora', 'scanner', 'escaner', 'telefono', 'celular',
        'computador', 'computadora', 'laptop', 'notebook', 'pc', 'cpu',
        'disco', 'memoria', 'ram', 'procesador', 'fuente', 'cargador',
        'cable', 'usb', 'hdmi', 'auriculares', 'audifonos', 'camara',
        'proyector', 'router', 'switch', 'modem'
    ]
    
    # ============================================
    # PALABRAS CLAVE BAJA (peso: 1 punto)
    # ============================================
    
    palabras_baja_individuales = [
        'mejora', 'sugerencia', 'recomendacion', 'idea', 'propuesta',
        'opcional', 'optativo', 'cosmetico', 'estetico', 'visual',
        'menor', 'minimo', 'pequeno', 'simple', 'basico',
        'consulta', 'duda', 'pregunta', 'informacion'
    ]
    
    frases_baja = [
        'cuando pueda', 'cuando puedan', 'cuando tengan tiempo',
        'si tienen tiempo', 'si pueden', 'si es posible',
        'no urgente', 'no es urgente', 'sin prisa', 'sin apuro',
        'para cuando sea', 'en algun momento', 'sin afan',
        'puede esperar', 'no corre prisa', 'baja prioridad',
        'nice to have', 'seria bueno', 'estaria bien',
        'solo queria saber', 'solo para saber', 'por curiosidad',
        'no es grave', 'no es importante', 'no pasa nada',
        # Solicitudes que no son problemas
        'solicitar', 'solicito', 'cambio de', 'necesito un', 'requiero',
        'quiero pedir', 'quisiera', 'podrian', 'seria posible'
    ]
    
    # ============================================
    # PALABRAS NEUTRAS (peso: 0 - solo contexto)
    # ============================================
    
    palabras_neutras = [
        'cambio', 'nuevo', 'nueva', 'reemplazo', 'actualizar',
        'instalar', 'configurar', 'agregar', 'solicitud'
    ]
    
    # ============================================
    # CALCULAR SCORES
    # ============================================
    
    score_critico = 0
    score_alto = 0
    score_bajo = 0
    
    tiene_dispositivo = False
    tiene_problema = False
    tiene_palabra_neutra = False
    
    # Detectar dispositivos (no suma puntos por sí solo)
    for dispositivo in dispositivos:
        if buscar_palabra(dispositivo, texto_normalizado):
            tiene_dispositivo = True
            break
    
    # Detectar palabras neutras (indica que puede ser solicitud, no problema)
    for neutra in palabras_neutras:
        if buscar_palabra(neutra, texto_normalizado):
            tiene_palabra_neutra = True
            break
    
    # Buscar palabras críticas
    for palabra in palabras_criticas_individuales:
        if buscar_palabra(palabra, texto_normalizado):
            score_critico += 2
            palabras_encontradas.append(f'"{palabra}" (crítica)')
    
    for frase in frases_criticas:
        if buscar_frase(frase, texto_normalizado):
            score_critico += 2
            palabras_encontradas.append(f'"{frase}" (crítica)')
    
    # Buscar palabras de PROBLEMA (estas sí suman alta)
    for palabra in palabras_problema:
        if buscar_palabra(palabra, texto_normalizado):
            score_alto += 1.5
            tiene_problema = True
            palabras_encontradas.append(f'"{palabra}" (alta)')
    
    for frase in frases_problema:
        if buscar_frase(frase, texto_normalizado):
            score_alto += 1.5
            tiene_problema = True
            palabras_encontradas.append(f'"{frase}" (alta)')
    
    # Buscar palabras de URGENCIA
    for palabra in palabras_urgencia:
        if buscar_palabra(palabra, texto_normalizado):
            score_alto += 1.5
            palabras_encontradas.append(f'"{palabra}" (alta)')
    
    for frase in frases_urgencia:
        if buscar_frase(frase, texto_normalizado):
            score_alto += 1.5
            palabras_encontradas.append(f'"{frase}" (alta)')
    
    # Buscar palabras de baja prioridad
    for palabra in palabras_baja_individuales:
        if buscar_palabra(palabra, texto_normalizado):
            score_bajo += 1
            palabras_encontradas.append(f'"{palabra}" (baja)')
    
    for frase in frases_baja:
        if buscar_frase(frase, texto_normalizado):
            score_bajo += 1.5  # Las frases de baja pesan más
            palabras_encontradas.append(f'"{frase}" (baja)')
    
    # ============================================
    # MODIFICADOR POR TIPO DE SOLICITUD
    # ============================================
    # El tipo de solicitud puede aumentar o disminuir la prioridad detectada
    
    modificador_tipo = 0  # Neutro por defecto
    tipo_info = ""
    
    if tipo_solicitud:
        tipo_normalizado = tipo_solicitud.lower().strip()
        
        if tipo_normalizado == 'problema':
            # "Problema" indica algo que ya está afectando, sube prioridad
            modificador_tipo = 1.5
            tipo_info = "tipo=problema (+1.5)"
            # Si el usuario dice que es un problema, dar más peso a palabras de problema
            if tiene_problema:
                score_alto += 1  # Bonus adicional
                
        elif tipo_normalizado == 'incidencia':
            # "Incidencia" es neutro, algo ocurrió pero puede no ser grave
            modificador_tipo = 0.5
            tipo_info = "tipo=incidencia (+0.5)"
            
        elif tipo_normalizado == 'solicitud':
            # "Solicitud" generalmente son peticiones, no urgencias
            modificador_tipo = -1
            tipo_info = "tipo=solicitud (-1)"
            # Si es solicitud y tiene palabras neutras, reforzar baja prioridad
            if tiene_palabra_neutra and not tiene_problema:
                score_bajo += 1
                
        elif tipo_normalizado == 'cambio':
            # "Cambio" son modificaciones planificadas, no urgentes
            modificador_tipo = -1.5
            tipo_info = "tipo=cambio (-1.5)"
            # Cambios sin problemas detectados = baja prioridad
            if not tiene_problema:
                score_bajo += 1.5
    
    # Agregar info del tipo a las palabras encontradas si aplica
    if tipo_info:
        palabras_encontradas.append(tipo_info)
    
    # Aplicar modificador a los scores
    score_alto += modificador_tipo
    score_bajo -= modificador_tipo  # Inverso para balance
    
    # ============================================
    # LÓGICA DE DECISIÓN INTELIGENTE
    # ============================================
    
    # Eliminar duplicados
    palabras_encontradas = list(dict.fromkeys(palabras_encontradas))
    
    # Si tiene dispositivo + palabra neutra (ej: "cambio de mouse") = BAJA/MEDIA
    if tiene_dispositivo and tiene_palabra_neutra and not tiene_problema:
        if score_bajo >= 1:
            prioridad = 'baja'
            confianza = 'alta'
        else:
            prioridad = 'media'
            confianza = 'media'
        return prioridad, confianza, palabras_encontradas
    
    # Si tiene dispositivo + problema (ej: "mouse no funciona") = ALTA
    if tiene_dispositivo and tiene_problema:
        prioridad = 'alta'
        confianza = 'alta' if score_alto >= 3 else 'media'
        return prioridad, confianza, palabras_encontradas
    
    # Lógica estándar por scores
    if score_critico >= 2:
        prioridad = 'critica'
        confianza = 'alta' if score_critico >= 4 else 'media'
    elif score_alto >= 1.5:
        # Si hay mucho score bajo, puede contrarrestar
        if score_bajo >= 3 and score_alto < 3:
            prioridad = 'media'
            confianza = 'media'
        else:
            prioridad = 'alta'
            confianza = 'alta' if score_alto >= 4.5 else 'media'
    elif score_bajo >= 1.5:
        prioridad = 'baja'
        confianza = 'alta' if score_bajo >= 3 else 'media'
    else:
        prioridad = 'media'
        confianza = 'baja'
    
    return prioridad, confianza, palabras_encontradas


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
    # Administradores, Técnicos y usuarios con permiso de ver todos los tickets ven todos
    # Usuarios regulares solo ven sus propios tickets
    if es_admin(user) or es_tecnico(user) or puede_ver_todos_tickets(user):
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
        
        # Filtro por categoría
        area = form.cleaned_data.get('categoria')
        if area:
            tickets_base = tickets_base.filter(categoria__nombre__icontains=area)
        
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
    pendientes_count = tickets_base.filter(estado='pendiente').count()
    asignados_count = tickets_base.filter(asignado_a__isnull=False).count()
    en_proceso_count = tickets_base.filter(estado='en_progreso').count()
    resueltos_count = tickets_base.filter(estado='resuelto').count()
    cerrados_count = tickets_base.filter(estado='cerrado').count()
    sla_excedido_count = tickets_base.filter(estado='tiempo_excedido').count()
    
    # Tickets urgentes: prioridad alta/crítica que no están resueltos ni cerrados
    tickets_urgentes = Ticket.objects.filter(
        prioridad__in=['alta', 'critica'],
        estado__in=['pendiente', 'en_progreso']
    ).exclude(
        estado__in=['resuelto', 'cerrado']
    ).select_related('creador', 'asignado_a', 'categoria').order_by('-prioridad', 'fecha_creacion')[:5]
    
    # Permisos del usuario actual para mostrar botones en el template
    permisos_usuario = {
        'puede_asignar': puede_asignar_tickets(user),
        'puede_autoasignarse': puede_autoasignarse_tickets(user),
        'puede_cambiar_estado': puede_cambiar_estado(user),
        'puede_ver_metricas': puede_ver_metricas(user),
        'puede_gestionar_usuarios': puede_gestionar_usuarios(user),
        'puede_acceder_admin': puede_acceder_admin_panel(user),
        'es_admin': es_admin(user),
        'es_tecnico': es_tecnico(user),
        'puede_validar_prioridad': puede_validar_prioridad(user),
    }
    
    context = {
        'tickets': tickets,
        'form': form,
        'total_tickets': total_tickets,
        'pendientes_count': pendientes_count,
        'asignados_count': asignados_count,
        'en_proceso_count': en_proceso_count,
        'resueltos_count': resueltos_count,
        'cerrados_count': cerrados_count,
        'sla_excedido_count': sla_excedido_count,
        'tickets_urgentes': tickets_urgentes,
        'permisos': permisos_usuario,
    }
    
    return render(request, 'tickets/ticket_list.html', context)

# Vista para crear nuevos tickets en el sistema
@login_required
def ticket_create(request):
    from .services import notificar_validadores_ticket_critico
    
    usuario_es_admin = es_admin(request.user)
    
    if request.method == 'POST':
        form = TicketForm(request.POST, request.FILES)
        if form.is_valid():
            # Crear el ticket
            ticket = form.save(commit=False)
            ticket.creador = request.user
            
            # Detectar prioridad automática basada en palabras clave y tipo de solicitud
            prioridad_detectada, confianza, palabras = detectar_prioridad_automatica(
                form.cleaned_data.get('titulo', ''),
                form.cleaned_data.get('descripcion', ''),
                form.cleaned_data.get('tipo', None)  # Pasar el tipo de solicitud
            )
            
            # Si es admin, puede establecer prioridad y técnico manualmente
            if usuario_es_admin:
                prioridad = request.POST.get('prioridad')
                tecnico_id = request.POST.get('asignar_a')
                
                if prioridad:
                    ticket.prioridad = prioridad
                    # Si admin establece manualmente, se considera validada
                    ticket.prioridad_validada = True
                    ticket.validado_por = request.user
                    ticket.fecha_validacion = timezone.now()
                else:
                    ticket.prioridad = 'media'
                    
                # Asignar técnico si se seleccionó
                if tecnico_id:
                    tecnico = User.objects.filter(id=tecnico_id, groups__name=GRUPO_TECNICO).first()
                    if tecnico:
                        ticket.asignado_a = tecnico
                        ticket.fecha_asignacion = timezone.now()
            else:
                # Usuario normal: usar detección automática
                ticket.prioridad_auto_detectada = prioridad_detectada
                
                # Si se detectó prioridad alta o crítica, requiere validación
                if prioridad_detectada in ['critica', 'alta']:
                    ticket.prioridad = prioridad_detectada  # Asignar temporalmente
                    ticket.prioridad_validada = False  # Marcar como pendiente de validación
                    logger.info(f"Ticket detectado con prioridad {prioridad_detectada} (confianza: {confianza}). Palabras: {palabras}")
                else:
                    # Prioridad media o baja no requiere validación
                    ticket.prioridad = prioridad_detectada
                    ticket.prioridad_validada = True
            
            # Guardar primero para que tenga fecha_creacion
            ticket.save()
            
            # Ahora calcular tiempo límite SLA basado en la prioridad
            ticket.tiempo_limite_resolucion = ticket.calcular_tiempo_limite_sla()
            ticket.save()
            
            # Enviar notificación a administradores cuando se crea un ticket
            from .models import Notificacion
            # Usar la prioridad real del ticket para la notificación
            prioridad_notif = ticket.prioridad  # Puede ser: critica, alta, media, baja
            administradores = User.objects.filter(groups__name=GRUPO_ADMINISTRADOR)
            for admin in administradores:
                crear_notificacion_completa(
                    usuario=admin,
                    ticket=ticket,
                    tipo='ticket_creado',
                    prioridad=prioridad_notif
                )
            
            # Si se detectó prioridad crítica/alta y no está validada, notificar a validadores
            if not ticket.prioridad_validada and ticket.prioridad_auto_detectada in ['critica', 'alta']:
                try:
                    notificar_validadores_ticket_critico(ticket, palabras)
                except Exception as e:
                    logger.error(f'Error al notificar validadores: {str(e)}')
            
            # Si se asignó un técnico, notificarlo
            if ticket.asignado_a:
                try:
                    nombre_tecnico = ticket.asignado_a.get_full_name() or ticket.asignado_a.username
                    
                    # Notificar al TÉCNICO: "Te asignaron un ticket"
                    crear_notificacion_completa(
                        usuario=ticket.asignado_a,
                        ticket=ticket,
                        tipo='ticket_asignado',
                        prioridad=prioridad_notif
                    )
                    
                    # Notificar al CREADOR: "Tu ticket fue asignado a [técnico]"
                    # Solo si el creador no es el mismo técnico
                    if ticket.creador != ticket.asignado_a:
                        crear_notificacion_completa(
                            usuario=ticket.creador,
                            ticket=ticket,
                            tipo='tu_ticket_asignado',
                            prioridad=prioridad_notif,
                            datos_extra={'nombre_tecnico': nombre_tecnico}
                        )
                except Exception as e:
                    logger.error(f'Error al notificar técnico asignado: {str(e)}')
            
            # Logging
            asignacion_info = f', asignado a {ticket.asignado_a.username}' if ticket.asignado_a else ''
            logger.info(f'Ticket #{ticket.id} creado por {request.user.username}: "{ticket.titulo}"{asignacion_info}')
            
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
    
    # Si es admin, obtener lista de técnicos para asignación
    tecnicos = None
    if usuario_es_admin:
        tecnicos = User.objects.filter(groups__name=GRUPO_TECNICO, is_active=True).order_by('first_name', 'username')
    
    return render(request, 'tickets/ticket_form.html', {
        'form': form,
        'es_admin': usuario_es_admin,
        'tecnicos': tecnicos,
        'prioridades': Ticket.PRIORIDADES,
    })

# Vista para asignar tickets a técnicos (administradores o usuarios con permiso)
@login_required
def asignar_ticket(request, ticket_id):
    # Verificar permiso para asignar tickets
    if not puede_asignar_tickets(request.user):
        messages.error(request, 'No tienes permiso para asignar tickets.')
        return redirect('ticket_list')
    
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
            # Usar la prioridad real del ticket para la notificación
            prioridad_notif = ticket.prioridad  # Puede ser: critica, alta, media, baja
            
            # Obtener nombre del técnico para las notificaciones
            nombre_tecnico = tecnico.get_full_name() or tecnico.username
            
            # Notificar al TÉCNICO: "Te asignaron un ticket"
            crear_notificacion_completa(
                usuario=tecnico,
                ticket=ticket,
                tipo='ticket_asignado',
                prioridad=prioridad_notif
            )
            
            # Notificar al CREADOR: "Tu ticket fue asignado a [técnico]"
            if ticket.creador != tecnico:  # No notificar si el técnico es el creador
                crear_notificacion_completa(
                    usuario=ticket.creador,
                    ticket=ticket,
                    tipo='tu_ticket_asignado',
                    prioridad=prioridad_notif,
                    datos_extra={'nombre_tecnico': nombre_tecnico}
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


# Vista para que los técnicos se autoasignen tickets sin asignar
@login_required
def autoasignar_ticket(request, ticket_id):
    """Permite a un técnico autoasignarse un ticket (incluso si está asignado a otro técnico)"""
    # Verificar que el usuario es técnico
    if not puede_autoasignarse_tickets(request.user):
        messages.error(request, 'Solo los técnicos pueden autoasignarse tickets.')
        return redirect('ticket_list')
    
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    # Verificar que el ticket no esté ya asignado a este mismo técnico
    if ticket.asignado_a == request.user:
        messages.info(request, 'Este ticket ya está asignado a ti.')
        return redirect('ticket_detalle', ticket_id=ticket.id)
    
    # Verificar que el técnico no sea el creador del ticket
    if ticket.creador == request.user:
        messages.error(request, 'No puedes autoasignarte un ticket que tú mismo creaste.')
        return redirect('ticket_detalle', ticket_id=ticket.id)
    
    # Guardar información del técnico anterior (si existe) para el historial
    tecnico_anterior = ticket.asignado_a
    
    if request.method == 'POST':
        # Autoasignar el ticket al técnico actual
        ticket.asignado_a = request.user
        
        # Registrar fecha de asignación (solo si es primera asignación)
        if not ticket.fecha_asignacion:
            ticket.fecha_asignacion = timezone.now()
        
        # Calcular tiempo límite SLA por defecto según prioridad
        ticket.tiempo_limite_resolucion = ticket.calcular_tiempo_limite_sla()
        
        ticket.save()
        
        # Registrar en historial con información de reasignación si aplica
        if tecnico_anterior:
            nombre_anterior = tecnico_anterior.first_name or tecnico_anterior.username
            comentario_historial = f'Ticket reasignado de {nombre_anterior} a {request.user.first_name or request.user.username} (autoasignación)'
        else:
            comentario_historial = f'Ticket autoasignado por {request.user.first_name or request.user.username}'
        
        HistorialEstado.objects.create(
            ticket=ticket,
            cambiado_por=request.user,
            estado_anterior=ticket.estado,
            estado_nuevo=ticket.estado,
            comentario=comentario_historial
        )
        
        # Obtener nombre del técnico actual para las notificaciones
        nombre_tecnico_actual = request.user.get_full_name() or request.user.username
        nombre_tecnico_anterior = (tecnico_anterior.get_full_name() or tecnico_anterior.username) if tecnico_anterior else None
        
        # Notificar al CREADOR del ticket: "Tu ticket fue asignado a [técnico]"
        try:
            crear_notificacion_completa(
                usuario=ticket.creador,
                ticket=ticket,
                tipo='tu_ticket_asignado',
                prioridad=ticket.prioridad,
                datos_extra={
                    'nombre_tecnico': nombre_tecnico_actual,
                    'nombre_anterior': nombre_tecnico_anterior
                }
            )
        except Exception as e:
            logger.error(f'Error al notificar autoasignación al creador: {str(e)}')
        
        # Si había un técnico anterior, notificarle que el ticket fue reasignado
        if tecnico_anterior:
            try:
                crear_notificacion_completa(
                    usuario=tecnico_anterior,
                    ticket=ticket,
                    tipo='ticket_reasignado',
                    prioridad=ticket.prioridad,
                    datos_extra={
                        'nombre_tecnico': nombre_tecnico_actual,
                        'nombre_anterior': nombre_tecnico_anterior
                    }
                )
            except Exception as e:
                logger.error(f'Error al notificar al técnico anterior: {str(e)}')
        
        # Logging
        reasignacion_info = f' (reasignado desde {tecnico_anterior.username})' if tecnico_anterior else ''
        logger.info(
            f'Ticket #{ticket.id} autoasignado por {request.user.username}{reasignacion_info}. '
            f'SLA: {ticket.tiempo_limite_resolucion}'
        )
        
        messages.success(request, f'✓ Te has autoasignado el ticket #{ticket.id} exitosamente.')
        return redirect('ticket_detalle', ticket_id=ticket.id)
    
    # Si es GET, mostrar confirmación
    # Pasar información del técnico anterior para mostrar advertencia
    nombre_tecnico_anterior = None
    if tecnico_anterior:
        nombre_tecnico_anterior = tecnico_anterior.first_name or tecnico_anterior.username
        if tecnico_anterior.last_name:
            nombre_tecnico_anterior += f" {tecnico_anterior.last_name}"
    
    return render(request, 'tickets/autoasignar_ticket.html', {
        'ticket': ticket,
        'tecnico_anterior': tecnico_anterior,
        'nombre_tecnico_anterior': nombre_tecnico_anterior,
    })


def _obtener_mensaje_contexto_cambio(ticket, es_admin, es_tecnico, es_asignado, es_creador):
    """Genera un mensaje contextual sobre qué puede hacer el usuario con el ticket."""
    estado = ticket.estado
    
    if es_admin:
        return "Como administrador, tienes control total sobre el estado de este ticket."
    
    if es_tecnico and es_asignado:
        if estado == 'pendiente':
            return "Puedes comenzar a trabajar en este ticket marcándolo como 'En Progreso'."
        elif estado == 'en_progreso':
            return "Cuando termines de resolver el problema, marca el ticket como 'Resuelto'."
        elif estado == 'tiempo_excedido':
            return "Este ticket excedió su tiempo de respuesta. Puedes retomarlo y comenzar a trabajar."
        else:
            return "Actualiza el estado según el progreso del ticket."
    
    if es_tecnico and not es_asignado:
        if estado == 'pendiente':
            return "Este ticket está pendiente y sin técnico asignado. Puedes tomarlo."
        else:
            return "Este ticket está asignado a otro técnico."
    
    if es_creador:
        if estado == 'resuelto':
            return "El técnico marcó tu ticket como resuelto. Por favor confirma si el problema fue solucionado."
        else:
            return "Puedes ver el progreso de tu ticket."
    
    return "Actualiza el estado de progreso de este ticket."


# Vista para cambiar el estado de los tickets
# Flujo: Pendiente → En Progreso → Resuelto → Cerrado
@login_required
def cambiar_estado(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    usuario_es_admin = es_admin(request.user)
    usuario_es_tecnico = es_tecnico(request.user)
    usuario_es_creador = ticket.creador == request.user
    usuario_es_asignado = ticket.asignado_a == request.user
    
    # Determinar qué transiciones puede hacer este usuario
    # - Admin: todas las transiciones
    # - Técnico asignado: pendiente→en_progreso, en_progreso→resuelto/pendiente
    # - Creador: resuelto→cerrado (confirmar solución), resuelto→en_progreso (no solucionado)
    
    transiciones_base = ticket.obtener_transiciones_permitidas()
    
    if usuario_es_admin:
        # Admin puede hacer todas las transiciones + reabrir desde cerrado
        transiciones_permitidas = transiciones_base.copy()
        if ticket.estado == 'cerrado':
            transiciones_permitidas = ['pendiente']  # Permitir reabrir
    elif usuario_es_tecnico and (usuario_es_asignado or not ticket.asignado_a):
        # Técnico: puede tomar tickets (pendiente→en_progreso) y resolver (en_progreso→resuelto)
        if ticket.estado == 'pendiente':
            transiciones_permitidas = ['en_progreso']
        elif ticket.estado == 'en_progreso':
            transiciones_permitidas = ['resuelto', 'pendiente']
        elif ticket.estado == 'tiempo_excedido':
            transiciones_permitidas = ['pendiente', 'en_progreso']
        else:
            transiciones_permitidas = []
    elif usuario_es_creador:
        # Creador: puede confirmar solución (resuelto→cerrado) o reabrir (resuelto→en_progreso)
        if ticket.estado == 'resuelto':
            transiciones_permitidas = ['cerrado', 'en_progreso']
        else:
            transiciones_permitidas = []
    elif puede_cambiar_estado(request.user):
        # Usuario con permiso especial
        transiciones_permitidas = transiciones_base
    else:
        transiciones_permitidas = []
    
    # Si no tiene permisos para ninguna transición
    if not transiciones_permitidas:
        messages.warning(request, 'No puedes cambiar el estado de este ticket en su estado actual.')
        return redirect('ticket_detalle', ticket_id=ticket.id)
    
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        comentario = request.POST.get('comentario', '').strip()
        
        if nuevo_estado and nuevo_estado != ticket.estado:
            # Validar que el usuario puede hacer esta transición específica
            if nuevo_estado not in transiciones_permitidas:
                messages.error(
                    request, 
                    f'No tienes permiso para cambiar el ticket a "{dict(Ticket.ESTADOS).get(nuevo_estado, nuevo_estado)}".'
                )
                return redirect('ticket_detalle', ticket_id=ticket.id)
            
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
            
            # Datos extra para las notificaciones
            nombre_quien_cambio = request.user.get_full_name() or request.user.username
            datos_notificacion = {
                'estado_anterior': dict(Ticket.ESTADOS).get(estado_anterior, estado_anterior),
                'estado_nuevo': dict(Ticket.ESTADOS).get(nuevo_estado, nuevo_estado),
                'cambiado_por': nombre_quien_cambio
            }
            
            # Enviar notificaciones según el cambio de estado
            # SIEMPRE usar la prioridad real del ticket
            prioridad_real = ticket.prioridad
            
            if nuevo_estado == 'resuelto':
                # Notificar al creador que el ticket fue resuelto
                crear_notificacion_completa(
                    usuario=ticket.creador,
                    ticket=ticket,
                    tipo='ticket_resuelto',
                    prioridad=prioridad_real,
                    datos_extra=datos_notificacion
                )
            elif nuevo_estado == 'cerrado':
                # Si el creador cierra el ticket (confirma solución), notificar al técnico
                if usuario_es_creador and ticket.asignado_a:
                    crear_notificacion_completa(
                        usuario=ticket.asignado_a,
                        ticket=ticket,
                        tipo='ticket_cerrado_exito',
                        prioridad=prioridad_real,
                        datos_extra=datos_notificacion
                    )
                else:
                    # Notificar al creador que el ticket fue cerrado (por admin/técnico)
                    crear_notificacion_completa(
                        usuario=ticket.creador,
                        ticket=ticket,
                        tipo='ticket_cerrado',
                        prioridad=prioridad_real,
                        datos_extra=datos_notificacion
                    )
            elif nuevo_estado == 'en_progreso':
                # Si el creador rechaza la solución (resuelto → en_progreso), notificar al técnico
                if estado_anterior == 'resuelto' and usuario_es_creador and ticket.asignado_a:
                    crear_notificacion_completa(
                        usuario=ticket.asignado_a,
                        ticket=ticket,
                        tipo='solucion_rechazada',
                        prioridad=prioridad_real,
                        datos_extra=datos_notificacion
                    )
                else:
                    # Notificar al creador que su ticket está siendo atendido
                    crear_notificacion_completa(
                        usuario=ticket.creador,
                        ticket=ticket,
                        tipo='ticket_en_progreso',
                        prioridad=prioridad_real,
                        datos_extra=datos_notificacion
                    )
            elif nuevo_estado == 'pendiente' and estado_anterior in ['resuelto', 'cerrado', 'tiempo_excedido']:
                # Si se reabre un ticket, notificar al creador y al técnico
                crear_notificacion_completa(
                    usuario=ticket.creador,
                    ticket=ticket,
                    tipo='ticket_reabierto',
                    prioridad=prioridad_real,
                    datos_extra=datos_notificacion
                )
                if ticket.asignado_a and ticket.asignado_a != ticket.creador:
                    crear_notificacion_completa(
                        usuario=ticket.asignado_a,
                        ticket=ticket,
                        tipo='ticket_reabierto',
                        prioridad=prioridad_real,
                        datos_extra=datos_notificacion
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
            mensaje_comentario = f"📋 **Cambio de estado:** {dict(Ticket.ESTADOS).get(estado_anterior, estado_anterior)} → {dict(Ticket.ESTADOS).get(nuevo_estado, nuevo_estado)}"
            if comentario:
                mensaje_comentario += f"\n💬 **Comentario:** {comentario}"
            
            Comentario.objects.create(
                ticket=ticket,
                autor=request.user,
                mensaje=mensaje_comentario
            )
            
            messages.success(request, f'Ticket actualizado a "{dict(Ticket.ESTADOS).get(nuevo_estado, nuevo_estado)}"')
        
        return redirect('ticket_detalle', ticket_id=ticket.id)
    
    # Preparar estados disponibles para el template según las transiciones permitidas del usuario
    estados_disponibles = [
        (estado, dict(Ticket.ESTADOS).get(estado, estado)) 
        for estado in transiciones_permitidas
    ]
    
    # Información adicional para el template
    contexto_cambio = {
        'puede_resolver': 'resuelto' in transiciones_permitidas,
        'puede_cerrar': 'cerrado' in transiciones_permitidas,
        'puede_reabrir': 'pendiente' in transiciones_permitidas and ticket.estado in ['resuelto', 'cerrado', 'tiempo_excedido'],
        'es_creador': usuario_es_creador,
        'es_tecnico_asignado': usuario_es_asignado,
        'es_admin': usuario_es_admin,
        'mensaje': _obtener_mensaje_contexto_cambio(ticket, usuario_es_admin, usuario_es_tecnico, usuario_es_asignado, usuario_es_creador)
    }
    
    return render(request, 'tickets/cambiar_estado.html', {
        'ticket': ticket,
        'estados_disponibles': estados_disponibles,
        'contexto_cambio': contexto_cambio,
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
    usuario_es_tecnico = es_tecnico(request.user)
    es_tecnico_asignado = ticket.asignado_a == request.user
    es_creador = ticket.creador == request.user

    # Solo permitir acceso a usuarios autorizados
    # Los técnicos pueden ver TODOS los tickets (para poder tomarlos si es necesario)
    if not (usuario_es_admin or es_tecnico_asignado or es_creador or usuario_es_tecnico):
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
                        prioridad=ticket.prioridad  # Usar prioridad real del ticket
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
    # Excluir comentarios automáticos de cambio de estado (contienen "📋 **Cambio de estado:**")
    comentarios = ticket.comentarios.select_related('autor').prefetch_related('archivos').exclude(
        mensaje__startswith='📋 **Cambio de estado:**'
    ).order_by('fecha')
    # Historial ordenado del más reciente al más antiguo
    historial = ticket.historial_estados.select_related('cambiado_por').order_by('-fecha')
    archivos_ticket = ticket.archivos.select_related('subido_por').order_by('-fecha_subida')
    
    # Verificar si el técnico puede autoasignarse este ticket
    # Puede autoasignarse si: es técnico, no es el creador, y no está asignado a él mismo
    puede_autoasignarse = (
        puede_autoasignarse_tickets(request.user) and 
        ticket.creador != request.user and
        ticket.asignado_a != request.user
    )
    
    # Indicar si el ticket ya está asignado a otro técnico (para mostrar advertencia)
    ticket_asignado_a_otro = ticket.asignado_a and ticket.asignado_a != request.user
    
    # Nombre del técnico asignado para el popup de advertencia
    nombre_tecnico_asignado = None
    if ticket_asignado_a_otro:
        nombre_tecnico_asignado = ticket.asignado_a.first_name or ticket.asignado_a.username
        if ticket.asignado_a.last_name:
            nombre_tecnico_asignado += f" {ticket.asignado_a.last_name}"
    
    return render(request, 'tickets/ticket_detalle.html', {
        'ticket': ticket,
        'comentarios': comentarios,
        'historial': historial,
        'archivos_ticket': archivos_ticket,
        'now': timezone.now(),
        'puede_autoasignarse': puede_autoasignarse,
        'ticket_asignado_a_otro': ticket_asignado_a_otro,
        'nombre_tecnico_asignado': nombre_tecnico_asignado,
        'es_tecnico': es_tecnico(request.user),
    })


# Vista de métricas y estadísticas del sistema
@login_required
def metricas(request):
    """Vista completa de métricas y KPIs del sistema de tickets"""
    
    # Verificar permiso para ver métricas
    if not puede_ver_metricas(request.user):
        messages.error(request, 'No tienes permiso para ver las métricas.')
        return redirect('ticket_list')
    
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
    
    # Tickets por categoría con porcentaje calculado
    tickets_por_area = list(tickets_periodo.filter(
        categoria__isnull=False
    ).values('categoria__nombre').annotate(
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
    tickets_abiertos = tickets_usuario.filter(estado__in=['pendiente', 'en_progreso']).count()
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

def puede_acceder_admin_panel(user):
    """Verifica si el usuario puede acceder al panel de administración"""
    if es_admin(user):
        return True
    # También permitir si tiene algún permiso de administración
    return puede_gestionar_usuarios(user) or puede_crear_roles(user)


@login_required
def admin_panel(request):
    """Panel principal de administración"""
    # Verificar acceso al panel
    if not puede_acceder_admin_panel(request.user):
        messages.error(request, 'No tienes permiso para acceder al panel de administración.')
        return redirect('ticket_list')
    
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
def admin_usuarios(request):
    """Lista y gestión de usuarios"""
    # Verificar permiso
    if not puede_gestionar_usuarios(request.user):
        messages.error(request, 'No tienes permiso para gestionar usuarios.')
        return redirect('ticket_list')
    
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
def admin_crear_usuario(request):
    """Crear nuevo usuario manualmente"""
    # Verificar permiso
    if not puede_gestionar_usuarios(request.user):
        messages.error(request, 'No tienes permiso para crear usuarios.')
        return redirect('ticket_list')
    
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
        grupo_id = request.POST.get('grupo') or None
        rol_personalizado_id = request.POST.get('rol_personalizado') or None
        
        # Validar que tenga al menos un grupo o rol personalizado
        if not grupo_id and not rol_personalizado_id:
            messages.error(request, 'Debe seleccionar al menos un Grupo tradicional o un Rol personalizado.')
            grupos = Group.objects.all()
            roles = RolPersonalizado.objects.filter(activo=True)
            return render(request, 'admin/crear_usuario.html', {'grupos': grupos, 'roles': roles})
        
        try:
            # Crear usuario
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            
            # Crear perfil
            perfil = PerfilUsuario.objects.create(
                user=user,
                telefono=telefono,
                departamento=departamento,
                cargo=cargo,
                creado_por=request.user
            )
            
            # Si hay rol personalizado, usarlo para determinar el grupo
            if rol_personalizado_id:
                rol = RolPersonalizado.objects.get(id=rol_personalizado_id)
                perfil.rol_personalizado = rol
                perfil.save()
                
                # Crear o obtener grupo con el nombre del rol y asignarlo
                grupo_rol, created = Group.objects.get_or_create(name=rol.nombre)
                user.groups.clear()
                user.groups.add(grupo_rol)
                
                logger.info(f'Usuario {username} asignado al grupo del rol: {rol.nombre}')
            elif grupo_id:
                # Si no hay rol personalizado pero sí grupo tradicional
                grupo = Group.objects.get(id=grupo_id)
                user.groups.add(grupo)
            
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
def admin_editar_usuario(request, user_id):
    """Editar usuario existente"""
    # Verificar permiso
    if not puede_gestionar_usuarios(request.user):
        messages.error(request, 'No tienes permiso para editar usuarios.')
        return redirect('ticket_list')
    
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
        
        # Actualizar rol personalizado y grupo
        rol_personalizado_id = request.POST.get('rol_personalizado') or None
        grupo_id = request.POST.get('grupo') or None
        
        # Validar que tenga al menos un grupo o rol personalizado
        if not grupo_id and not rol_personalizado_id:
            messages.error(request, 'Debe seleccionar al menos un Grupo tradicional o un Rol personalizado.')
            grupos = Group.objects.all()
            roles = RolPersonalizado.objects.filter(activo=True)
            grupo_actual = usuario.groups.first()
            return render(request, 'admin/editar_usuario.html', {
                'usuario': usuario,
                'perfil': perfil,
                'grupos': grupos,
                'roles': roles,
                'grupo_actual': grupo_actual,
            })
        
        if rol_personalizado_id:
            # Si hay rol personalizado, usarlo para el grupo
            rol = RolPersonalizado.objects.get(id=rol_personalizado_id)
            perfil.rol_personalizado = rol
            
            # Crear o obtener grupo con el nombre del rol y asignarlo
            grupo_rol, created = Group.objects.get_or_create(name=rol.nombre)
            usuario.groups.clear()
            usuario.groups.add(grupo_rol)
            
            logger.info(f'Usuario {usuario.username} asignado al grupo del rol: {rol.nombre}')
        else:
            # Si no hay rol personalizado
            perfil.rol_personalizado = None
            
            # Usar grupo tradicional si se especificó
            if grupo_id:
                usuario.groups.clear()
                grupo = Group.objects.get(id=grupo_id)
                usuario.groups.add(grupo)
        
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
def admin_toggle_usuario(request, user_id):
    """Activar/Desactivar usuario"""
    # Verificar permiso
    if not puede_gestionar_usuarios(request.user):
        messages.error(request, 'No tienes permiso para gestionar usuarios.')
        return redirect('ticket_list')
    
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
def admin_eliminar_usuario(request, user_id):
    """Eliminar usuario (con confirmación)"""
    # Verificar permiso
    if not puede_gestionar_usuarios(request.user):
        messages.error(request, 'No tienes permiso para eliminar usuarios.')
        return redirect('ticket_list')
    
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
def admin_roles(request):
    """Lista de roles personalizados"""
    # Verificar permiso
    if not puede_crear_roles(request.user):
        messages.error(request, 'No tienes permiso para gestionar roles.')
        return redirect('ticket_list')
    
    roles = RolPersonalizado.objects.annotate(
        num_usuarios=Count('usuarios')
    ).order_by('nombre')
    
    context = {
        'roles': roles,
    }
    
    return render(request, 'admin/roles.html', context)


@login_required
def admin_crear_rol(request):
    """Crear nuevo rol personalizado"""
    # Verificar permiso
    if not puede_crear_roles(request.user):
        messages.error(request, 'No tienes permiso para crear roles.')
        return redirect('ticket_list')
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion', '')
        color = request.POST.get('color', '#3498db')
        
        # Permisos
        puede_ver_metricas_val = request.POST.get('puede_ver_metricas') == 'on'
        puede_ver_todos_tickets_val = request.POST.get('puede_ver_todos_tickets') == 'on'
        puede_asignar_tickets_val = request.POST.get('puede_asignar_tickets') == 'on'
        puede_cambiar_estado_val = request.POST.get('puede_cambiar_estado') == 'on'
        puede_gestionar_usuarios_val = request.POST.get('puede_gestionar_usuarios') == 'on'
        puede_crear_roles_val = request.POST.get('puede_crear_roles') == 'on'
        puede_validar_prioridad_val = request.POST.get('puede_validar_prioridad') == 'on'
        
        try:
            rol = RolPersonalizado.objects.create(
                nombre=nombre,
                descripcion=descripcion,
                color=color,
                puede_ver_metricas=puede_ver_metricas_val,
                puede_ver_todos_tickets=puede_ver_todos_tickets_val,
                puede_asignar_tickets=puede_asignar_tickets_val,
                puede_cambiar_estado=puede_cambiar_estado_val,
                puede_gestionar_usuarios=puede_gestionar_usuarios_val,
                puede_crear_roles=puede_crear_roles_val,
                puede_validar_prioridad=puede_validar_prioridad_val,
                creado_por=request.user
            )
            
            # Crear el grupo de Django correspondiente al rol
            Group.objects.get_or_create(name=nombre)
            
            logger.info(f'Rol {nombre} creado por {request.user.username}')
            messages.success(request, f'Rol {nombre} creado exitosamente.')
            return redirect('admin_roles')
            
        except Exception as e:
            logger.error(f'Error al crear rol: {e}')
            messages.error(request, f'Error al crear rol: {str(e)}')
    
    return render(request, 'admin/crear_rol.html')


@login_required
def admin_editar_rol(request, rol_id):
    """Editar rol personalizado"""
    # Verificar permiso
    if not puede_crear_roles(request.user):
        messages.error(request, 'No tienes permiso para editar roles.')
        return redirect('ticket_list')
    
    rol = get_object_or_404(RolPersonalizado, id=rol_id)
    nombre_anterior = rol.nombre
    
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
        rol.puede_validar_prioridad = request.POST.get('puede_validar_prioridad') == 'on'
        rol.activo = request.POST.get('activo') == 'on'
        
        rol.save()
        
        # Si cambió el nombre, actualizar el grupo de Django
        if nombre_anterior != rol.nombre:
            try:
                grupo_anterior = Group.objects.get(name=nombre_anterior)
                grupo_anterior.name = rol.nombre
                grupo_anterior.save()
            except Group.DoesNotExist:
                Group.objects.get_or_create(name=rol.nombre)
        
        logger.info(f'Rol {rol.nombre} actualizado por {request.user.username}')
        messages.success(request, f'Rol {rol.nombre} actualizado exitosamente.')
        return redirect('admin_roles')
    
    context = {
        'rol': rol,
    }
    
    return render(request, 'admin/editar_rol.html', context)


@login_required
def admin_toggle_rol(request, rol_id):
    """Activar/Desactivar rol personalizado"""
    # Verificar permiso
    if not puede_crear_roles(request.user):
        messages.error(request, 'No tienes permiso para gestionar roles.')
        return redirect('ticket_list')
    
    if request.method == 'POST':
        rol = get_object_or_404(RolPersonalizado, id=rol_id)
        rol.activo = not rol.activo
        rol.save()
        
        estado = 'activado' if rol.activo else 'desactivado'
        logger.info(f'Rol {rol.nombre} {estado} por {request.user.username}')
        messages.success(request, f'Rol {rol.nombre} {estado} exitosamente.')
    
    return redirect('admin_roles')


@login_required
def admin_eliminar_rol(request, rol_id):
    """Eliminar rol personalizado"""
    # Verificar permiso
    if not puede_crear_roles(request.user):
        messages.error(request, 'No tienes permiso para eliminar roles.')
        return redirect('ticket_list')
    
    if request.method == 'POST':
        rol = get_object_or_404(RolPersonalizado, id=rol_id)
        
        # Verificar que no haya usuarios con este rol
        if rol.usuarios.exists():
            messages.error(request, f'No se puede eliminar el rol {rol.nombre} porque tiene usuarios asignados.')
            return redirect('admin_roles')
        
        nombre = rol.nombre
        
        # Eliminar también el grupo de Django correspondiente
        try:
            grupo = Group.objects.get(name=nombre)
            grupo.delete()
        except Group.DoesNotExist:
            pass
        
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
            'page_obj': page_obj,  # Para paginación en template
            'paginator': paginator,
            'page_number': page_number,
            'total_notificaciones': notificaciones.count(),
            'tipos_notificacion': Notificacion.TIPOS_NOTIFICACION,
            'prioridades': Ticket.PRIORIDADES,  # Usar PRIORIDADES de Ticket
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


# ============================================
# PÁGINA DE PREGUNTAS FRECUENTES (FAQs) - DINÁMICO
# ============================================

@login_required
def faqs(request):
    """
    Vista para mostrar las preguntas frecuentes del sistema.
    Lee las FAQs desde la base de datos.
    """
    from .models import CategoriaFAQ, PreguntaFAQ, BusquedaFAQ
    from django.db.models import Prefetch
    
    busqueda = request.GET.get('q', '').strip()
    
    # Obtener categorías activas con sus preguntas activas
    categorias = CategoriaFAQ.objects.filter(activa=True).prefetch_related(
        Prefetch(
            'preguntas',
            queryset=PreguntaFAQ.objects.filter(activa=True).order_by('orden')
        )
    ).order_by('orden')
    
    # Si hay búsqueda, filtrar
    if busqueda:
        from django.db.models import Q
        
        # Buscar en preguntas y respuestas
        preguntas_encontradas = PreguntaFAQ.objects.filter(
            activa=True,
            categoria__activa=True
        ).filter(
            Q(pregunta__icontains=busqueda) | Q(respuesta__icontains=busqueda)
        ).select_related('categoria').order_by('categoria__orden', 'orden')
        
        # Agrupar por categoría
        categorias_dict = {}
        for pregunta in preguntas_encontradas:
            cat_id = pregunta.categoria.id
            if cat_id not in categorias_dict:
                categorias_dict[cat_id] = {
                    'categoria': pregunta.categoria,
                    'preguntas': []
                }
            categorias_dict[cat_id]['preguntas'].append(pregunta)
        
        cantidad_resultados = preguntas_encontradas.count()
        
        # Registrar búsqueda
        BusquedaFAQ.objects.create(
            termino=busqueda[:200],
            usuario=request.user if request.user.is_authenticated else None,
            encontro_resultados=cantidad_resultados > 0,
            cantidad_resultados=cantidad_resultados
        )
        
        context = {
            'categorias_busqueda': categorias_dict.values(),
            'busqueda': busqueda,
            'es_busqueda': True,
        }
    else:
        context = {
            'categorias': categorias,
            'busqueda': '',
            'es_busqueda': False,
        }
    
    return render(request, 'tickets/faqs.html', context)


# ============================================
# ADMINISTRACIÓN DE FAQs
# ============================================

@login_required
@user_passes_test(puede_acceder_admin_panel)
def admin_faqs(request):
    """Vista principal de administración de FAQs"""
    from .models import CategoriaFAQ, PreguntaFAQ, BusquedaFAQ
    from django.db.models import Count, Q
    from django.db.models.functions import TruncDate
    
    # Obtener todas las categorías con conteo de preguntas
    categorias = CategoriaFAQ.objects.annotate(
        total_preguntas=Count('preguntas'),
        preguntas_activas=Count('preguntas', filter=Q(preguntas__activa=True))
    ).order_by('orden')
    
    # Estadísticas generales
    total_categorias = CategoriaFAQ.objects.count()
    total_preguntas = PreguntaFAQ.objects.count()
    total_preguntas_activas = PreguntaFAQ.objects.filter(activa=True).count()
    
    # Búsquedas recientes (últimas 50)
    busquedas_recientes = BusquedaFAQ.objects.select_related('usuario')[:50]
    
    # Términos más buscados (últimos 30 días)
    from datetime import timedelta
    hace_30_dias = timezone.now() - timedelta(days=30)
    terminos_populares = BusquedaFAQ.objects.filter(
        fecha__gte=hace_30_dias
    ).values('termino').annotate(
        total=Count('id'),
        sin_resultados=Count('id', filter=Q(encontro_resultados=False))
    ).order_by('-total')[:15]
    
    # Búsquedas sin resultados (más importantes para crear FAQs)
    busquedas_sin_resultados = BusquedaFAQ.objects.filter(
        encontro_resultados=False,
        fecha__gte=hace_30_dias
    ).values('termino').annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    context = {
        'categorias': categorias,
        'total_categorias': total_categorias,
        'total_preguntas': total_preguntas,
        'total_preguntas_activas': total_preguntas_activas,
        'busquedas_recientes': busquedas_recientes,
        'terminos_populares': terminos_populares,
        'busquedas_sin_resultados': busquedas_sin_resultados,
    }
    return render(request, 'admin/faqs/admin_faqs.html', context)


@login_required
@user_passes_test(puede_acceder_admin_panel)
def admin_crear_categoria_faq(request):
    """Crear una nueva categoría de FAQ"""
    from .models import CategoriaFAQ
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        icono = request.POST.get('icono', '❓').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        orden = request.POST.get('orden', 0)
        activa = request.POST.get('activa') == 'on'
        
        if not nombre:
            messages.error(request, 'El nombre de la categoría es obligatorio.')
            return redirect('admin_crear_categoria_faq')
        
        try:
            CategoriaFAQ.objects.create(
                nombre=nombre,
                icono=icono,
                descripcion=descripcion,
                orden=int(orden) if orden else 0,
                activa=activa,
                creado_por=request.user
            )
            messages.success(request, f'Categoría "{nombre}" creada exitosamente.')
            return redirect('admin_faqs')
        except Exception as e:
            messages.error(request, f'Error al crear la categoría: {str(e)}')
    
    # Obtener el siguiente orden disponible
    from .models import CategoriaFAQ
    ultimo_orden = CategoriaFAQ.objects.order_by('-orden').first()
    siguiente_orden = (ultimo_orden.orden + 1) if ultimo_orden else 0
    
    context = {
        'siguiente_orden': siguiente_orden,
    }
    return render(request, 'admin/faqs/crear_categoria_faq.html', context)


@login_required
@user_passes_test(puede_acceder_admin_panel)
def admin_editar_categoria_faq(request, categoria_id):
    """Editar una categoría de FAQ existente"""
    from .models import CategoriaFAQ
    
    categoria = get_object_or_404(CategoriaFAQ, id=categoria_id)
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        icono = request.POST.get('icono', '❓').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        orden = request.POST.get('orden', 0)
        activa = request.POST.get('activa') == 'on'
        
        if not nombre:
            messages.error(request, 'El nombre de la categoría es obligatorio.')
            return redirect('admin_editar_categoria_faq', categoria_id=categoria_id)
        
        try:
            categoria.nombre = nombre
            categoria.icono = icono
            categoria.descripcion = descripcion
            categoria.orden = int(orden) if orden else 0
            categoria.activa = activa
            categoria.save()
            messages.success(request, f'Categoría "{nombre}" actualizada exitosamente.')
            return redirect('admin_faqs')
        except Exception as e:
            messages.error(request, f'Error al actualizar la categoría: {str(e)}')
    
    context = {
        'categoria': categoria,
    }
    return render(request, 'admin/faqs/editar_categoria_faq.html', context)


@login_required
@user_passes_test(puede_acceder_admin_panel)
def admin_eliminar_categoria_faq(request, categoria_id):
    """Eliminar una categoría de FAQ"""
    from .models import CategoriaFAQ
    
    categoria = get_object_or_404(CategoriaFAQ, id=categoria_id)
    
    # Verificar si tiene preguntas
    if categoria.preguntas.exists():
        messages.error(request, f'No se puede eliminar la categoría "{categoria.nombre}" porque tiene preguntas asociadas. Elimina las preguntas primero.')
        return redirect('admin_faqs')
    
    try:
        nombre = categoria.nombre
        categoria.delete()
        messages.success(request, f'Categoría "{nombre}" eliminada exitosamente.')
    except Exception as e:
        messages.error(request, f'Error al eliminar la categoría: {str(e)}')
    
    return redirect('admin_faqs')


@login_required
@user_passes_test(puede_acceder_admin_panel)
def admin_preguntas_faq(request, categoria_id):
    """Ver y gestionar preguntas de una categoría"""
    from .models import CategoriaFAQ, PreguntaFAQ
    
    categoria = get_object_or_404(CategoriaFAQ, id=categoria_id)
    preguntas = categoria.preguntas.all().order_by('orden')
    
    context = {
        'categoria': categoria,
        'preguntas': preguntas,
    }
    return render(request, 'admin/faqs/preguntas_faq.html', context)


@login_required
@user_passes_test(puede_acceder_admin_panel)
def admin_crear_pregunta_faq(request, categoria_id=None):
    """Crear una nueva pregunta FAQ"""
    from .models import CategoriaFAQ, PreguntaFAQ
    
    categorias = CategoriaFAQ.objects.filter(activa=True).order_by('orden')
    categoria_seleccionada = None
    
    if categoria_id:
        categoria_seleccionada = get_object_or_404(CategoriaFAQ, id=categoria_id)
    
    if request.method == 'POST':
        categoria_id_post = request.POST.get('categoria')
        pregunta = request.POST.get('pregunta', '').strip()
        respuesta = request.POST.get('respuesta', '').strip()
        orden = request.POST.get('orden', 0)
        activa = request.POST.get('activa') == 'on'
        imagen = request.FILES.get('imagen')
        
        if not categoria_id_post or not pregunta or not respuesta:
            messages.error(request, 'Todos los campos son obligatorios.')
            return redirect('admin_crear_pregunta_faq')
        
        try:
            categoria = CategoriaFAQ.objects.get(id=categoria_id_post)
            nueva_pregunta = PreguntaFAQ.objects.create(
                categoria=categoria,
                pregunta=pregunta,
                respuesta=respuesta,
                orden=int(orden) if orden else 0,
                activa=activa,
                creado_por=request.user
            )
            
            # Guardar imagen si se subió
            if imagen:
                nueva_pregunta.imagen = imagen
                nueva_pregunta.save()
            
            messages.success(request, 'Pregunta creada exitosamente.')
            return redirect('admin_preguntas_faq', categoria_id=categoria.id)
        except Exception as e:
            messages.error(request, f'Error al crear la pregunta: {str(e)}')
    
    # Obtener el siguiente orden disponible
    siguiente_orden = 0
    if categoria_seleccionada:
        ultima_pregunta = categoria_seleccionada.preguntas.order_by('-orden').first()
        siguiente_orden = (ultima_pregunta.orden + 1) if ultima_pregunta else 0
    
    context = {
        'categorias': categorias,
        'categoria_seleccionada': categoria_seleccionada,
        'siguiente_orden': siguiente_orden,
    }
    return render(request, 'admin/faqs/crear_pregunta_faq.html', context)


@login_required
@user_passes_test(puede_acceder_admin_panel)
def admin_editar_pregunta_faq(request, pregunta_id):
    """Editar una pregunta FAQ existente"""
    from .models import CategoriaFAQ, PreguntaFAQ
    
    pregunta = get_object_or_404(PreguntaFAQ, id=pregunta_id)
    categorias = CategoriaFAQ.objects.filter(activa=True).order_by('orden')
    
    if request.method == 'POST':
        categoria_id = request.POST.get('categoria')
        pregunta_texto = request.POST.get('pregunta', '').strip()
        respuesta = request.POST.get('respuesta', '').strip()
        orden = request.POST.get('orden', 0)
        activa = request.POST.get('activa') == 'on'
        imagen = request.FILES.get('imagen')
        eliminar_imagen = request.POST.get('eliminar_imagen') == 'on'
        
        if not categoria_id or not pregunta_texto or not respuesta:
            messages.error(request, 'Todos los campos son obligatorios.')
            return redirect('admin_editar_pregunta_faq', pregunta_id=pregunta_id)
        
        try:
            categoria = CategoriaFAQ.objects.get(id=categoria_id)
            pregunta.categoria = categoria
            pregunta.pregunta = pregunta_texto
            pregunta.respuesta = respuesta
            pregunta.orden = int(orden) if orden else 0
            pregunta.activa = activa
            
            # Manejar imagen
            if eliminar_imagen and pregunta.imagen:
                pregunta.imagen.delete(save=False)
                pregunta.imagen = None
            elif imagen:
                # Si ya tenía imagen, eliminarla primero
                if pregunta.imagen:
                    pregunta.imagen.delete(save=False)
                pregunta.imagen = imagen
            
            pregunta.save()
            messages.success(request, 'Pregunta actualizada exitosamente.')
            return redirect('admin_preguntas_faq', categoria_id=categoria.id)
        except Exception as e:
            messages.error(request, f'Error al actualizar la pregunta: {str(e)}')
    
    context = {
        'pregunta': pregunta,
        'categorias': categorias,
    }
    return render(request, 'admin/faqs/editar_pregunta_faq.html', context)


@login_required
@user_passes_test(puede_acceder_admin_panel)
def admin_eliminar_pregunta_faq(request, pregunta_id):
    """Eliminar una pregunta FAQ"""
    from .models import PreguntaFAQ
    
    pregunta = get_object_or_404(PreguntaFAQ, id=pregunta_id)
    categoria_id = pregunta.categoria.id
    
    try:
        pregunta.delete()
        messages.success(request, 'Pregunta eliminada exitosamente.')
    except Exception as e:
        messages.error(request, f'Error al eliminar la pregunta: {str(e)}')
    
    return redirect('admin_preguntas_faq', categoria_id=categoria_id)


@login_required
@user_passes_test(puede_acceder_admin_panel)
def admin_toggle_pregunta_faq(request, pregunta_id):
    """Activar/desactivar una pregunta FAQ"""
    from .models import PreguntaFAQ
    
    pregunta = get_object_or_404(PreguntaFAQ, id=pregunta_id)
    pregunta.activa = not pregunta.activa
    pregunta.save()
    
    estado = "activada" if pregunta.activa else "desactivada"
    messages.success(request, f'Pregunta {estado} exitosamente.')
    
    return redirect('admin_preguntas_faq', categoria_id=pregunta.categoria.id)


@login_required
@user_passes_test(puede_acceder_admin_panel)
def admin_busquedas_faq(request):
    """Ver historial de búsquedas de FAQs"""
    from .models import BusquedaFAQ
    from django.db.models import Count, Q
    from datetime import timedelta
    
    # Filtros
    filtro = request.GET.get('filtro', 'todas')
    dias = int(request.GET.get('dias', 30))
    
    fecha_limite = timezone.now() - timedelta(days=dias)
    
    # Base query
    busquedas = BusquedaFAQ.objects.filter(fecha__gte=fecha_limite)
    
    if filtro == 'sin_resultados':
        busquedas = busquedas.filter(encontro_resultados=False)
    elif filtro == 'con_resultados':
        busquedas = busquedas.filter(encontro_resultados=True)
    
    busquedas = busquedas.select_related('usuario').order_by('-fecha')[:200]
    
    # Estadísticas
    stats = BusquedaFAQ.objects.filter(fecha__gte=fecha_limite).aggregate(
        total=Count('id'),
        sin_resultados=Count('id', filter=Q(encontro_resultados=False)),
        con_resultados=Count('id', filter=Q(encontro_resultados=True))
    )
    
    # Términos más buscados sin resultados
    terminos_sin_resultados = BusquedaFAQ.objects.filter(
        fecha__gte=fecha_limite,
        encontro_resultados=False
    ).values('termino').annotate(
        total=Count('id')
    ).order_by('-total')[:20]
    
    context = {
        'busquedas': busquedas,
        'stats': stats,
        'terminos_sin_resultados': terminos_sin_resultados,
        'filtro': filtro,
        'dias': dias,
    }
    return render(request, 'admin/faqs/busquedas_faq.html', context)


def admin_subir_imagen_faq(request):
    """Subir imagen para usar en FAQs vía AJAX"""
    from .models import ImagenFAQ
    import os
    
    # Verificar autenticación manualmente para devolver JSON
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'No autenticado. Por favor inicia sesión.'}, status=401)
    
    # Verificar permisos
    if not puede_acceder_admin_panel(request.user):
        return JsonResponse({'success': False, 'error': 'No tienes permisos para esta acción.'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)
    
    if 'imagen' not in request.FILES:
        return JsonResponse({'success': False, 'error': 'No se envió ninguna imagen'}, status=400)
    
    archivo = request.FILES['imagen']
    
    # Validar tipo de archivo
    extensiones_permitidas = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    ext = os.path.splitext(archivo.name)[1].lower()
    if ext not in extensiones_permitidas:
        return JsonResponse({
            'success': False, 
            'error': f'Tipo de archivo no permitido. Use: {", ".join(extensiones_permitidas)}'
        }, status=400)
    
    # Validar tamaño (máximo 5MB)
    max_size = 5 * 1024 * 1024  # 5MB
    if archivo.size > max_size:
        return JsonResponse({
            'success': False, 
            'error': 'La imagen es demasiado grande. Máximo 5MB.'
        }, status=400)
    
    try:
        # Crear la imagen
        imagen = ImagenFAQ.objects.create(
            imagen=archivo,
            nombre_original=archivo.name,
            alt_text=request.POST.get('alt_text', ''),
            subida_por=request.user
        )
        
        return JsonResponse({
            'success': True,
            'url': imagen.url,
            'id': imagen.id,
            'nombre': imagen.nombre_original
        })
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'error': f'Error al guardar la imagen: {str(e)}'
        }, status=500)


# ============================================
# VISTAS DE VALIDACIÓN DE PRIORIDAD
# ============================================

@login_required
def lista_tickets_pendientes_validacion(request):
    """Lista de tickets que requieren validación de prioridad"""
    if not puede_validar_prioridad(request.user):
        messages.error(request, 'No tienes permiso para validar prioridades.')
        return redirect('ticket_list')
    
    # Obtener tickets con prioridad auto-detectada alta/crítica sin validar
    tickets = Ticket.objects.filter(
        prioridad_auto_detectada__in=['critica', 'alta'],
        prioridad_validada=False
    ).select_related('creador', 'asignado_a', 'categoria').order_by('-fecha_creacion')
    
    # Paginación
    paginator = Paginator(tickets, TICKETS_POR_PAGINA)
    page = request.GET.get('page', 1)
    tickets_page = paginator.get_page(page)
    
    context = {
        'tickets': tickets_page,
        'total_pendientes': tickets.count(),
    }
    return render(request, 'tickets/validar_prioridad_lista.html', context)


@login_required
def validar_prioridad_ticket(request, ticket_id):
    """Vista para validar o modificar la prioridad de un ticket"""
    if not puede_validar_prioridad(request.user):
        messages.error(request, 'No tienes permiso para validar prioridades.')
        return redirect('ticket_list')
    
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    if request.method == 'POST':
        accion = request.POST.get('accion')
        
        if accion == 'aprobar':
            # Aprobar la prioridad auto-detectada
            ticket.prioridad = ticket.prioridad_auto_detectada
            ticket.prioridad_validada = True
            ticket.validado_por = request.user
            ticket.fecha_validacion = timezone.now()
            ticket.save()
            
            # Registrar en historial: representamos el cambio de prioridad como un evento
            # Usamos los campos válidos del modelo: cambiado_por, estado_anterior, estado_nuevo, comentario
            HistorialEstado.objects.create(
                ticket=ticket,
                cambiado_por=request.user,
                estado_anterior=f'prioridad:pendiente_validacion',
                estado_nuevo=f'prioridad:{ticket.prioridad}',
                comentario=f'Prioridad {ticket.prioridad} validada por supervisor'
            )
            
            messages.success(request, f'Prioridad "{ticket.get_prioridad_display()}" aprobada para el ticket #{ticket.id}.')
            logger.info(f"Usuario {request.user.username} aprobó prioridad {ticket.prioridad} para ticket #{ticket.id}")
            
        elif accion == 'modificar':
            nueva_prioridad = request.POST.get('nueva_prioridad')
            if nueva_prioridad in dict(Ticket.PRIORIDADES):
                prioridad_anterior = ticket.prioridad_auto_detectada
                ticket.prioridad = nueva_prioridad
                ticket.prioridad_validada = True
                ticket.validado_por = request.user
                ticket.fecha_validacion = timezone.now()
                ticket.save()
                
                # Registrar en historial: se registra la modificación de prioridad
                HistorialEstado.objects.create(
                    ticket=ticket,
                    cambiado_por=request.user,
                    estado_anterior=f'prioridad:{prioridad_anterior}',
                    estado_nuevo=f'prioridad:{nueva_prioridad}',
                    comentario=f'Prioridad modificada de {prioridad_anterior} a {nueva_prioridad} por supervisor'
                )
                
                messages.success(request, f'Prioridad modificada a "{ticket.get_prioridad_display()}" para el ticket #{ticket.id}.')
                logger.info(f"Usuario {request.user.username} modificó prioridad de {prioridad_anterior} a {nueva_prioridad} para ticket #{ticket.id}")
            else:
                messages.error(request, 'Prioridad inválida.')
                return redirect('validar_prioridad_ticket', ticket_id=ticket.id)
        
        return redirect('lista_tickets_pendientes_validacion')
    
    # Preferir la prioridad auto-detectada almacenada (si existe) para evitar
    # discrepancias entre lo que ve el validador y lo que realmente se aprobará.
    # Aún así, calculamos confianza y palabras para mostrar información útil.
    if ticket.prioridad_auto_detectada:
        prioridad_detectada = ticket.prioridad_auto_detectada
        # Recalcular confianza / palabras (informativo) con la misma función
        _, confianza, palabras = detectar_prioridad_automatica(
            ticket.titulo,
            ticket.descripcion,
            ticket.tipo
        )
    else:
        prioridad_detectada, confianza, palabras = detectar_prioridad_automatica(
            ticket.titulo,
            ticket.descripcion,
            ticket.tipo  # Incluir el tipo de solicitud
        )
    
    context = {
        'ticket': ticket,
        'prioridad_detectada': prioridad_detectada,
        'nivel_confianza': confianza,
        'palabras_encontradas': palabras,
        'prioridades': Ticket.PRIORIDADES,
    }
    return render(request, 'tickets/validar_prioridad.html', context)
