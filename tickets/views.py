from django.shortcuts import render
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Ticket, Comentario, HistorialEstado
from django.contrib.auth.models import User
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden
from .forms import CustomUserCreationForm
from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.auth import login

# Create your views here.

# Controlador principal con todas las vistas del sistema de tickets
# Implementa control de acceso basado en roles (Admin, Técnico, Usuario)
# Gestiona creación, asignación, modificación y visualización de tickets
# Mantiene historial de cambios y comentarios para cada ticket


# Función auxiliar para verificar si un usuario pertenece al grupo Administrador
def es_admin(user):
    return user.groups.filter(name='Administrador').exists()


# Vista principal que muestra la lista de tickets según el rol del usuario
@login_required
def ticket_list(request):
    user = request.user
    
    # Obtener filtro de estado 
    estado_filtro = request.GET.get('estado')
    
    if user.groups.filter(name='Administrador').exists():
        tickets_base = Ticket.objects.all()
    elif user.groups.filter(name='Técnico').exists():
        tickets_base = Ticket.objects.filter(asignado_a=user)
    else:
        tickets_base = Ticket.objects.filter(creador=user)
    
    # Aplicar filtro de estado 
    if estado_filtro:
        tickets = tickets_base.filter(estado=estado_filtro).order_by('-fecha_creacion')[:10]
        filtro_aplicado = True
    else:
        tickets = tickets_base.order_by('-fecha_creacion')[:10]
        filtro_aplicado = False
    
    # Estadísticas para el dashboard
    total_tickets = tickets_base.count()
    asignados_count = tickets_base.filter(asignado_a__isnull=False).count()
    en_proceso_count = tickets_base.filter(estado='en_progreso').count()
    resueltos_count = tickets_base.filter(estado='resuelto').count()  
    
    context = {
        'tickets': tickets,
        'total_tickets': total_tickets,
        'asignados_count': asignados_count,
        'en_proceso_count': en_proceso_count,
        'resueltos_count': resueltos_count,  
        'filtro_aplicado': filtro_aplicado,
        'estado_filtro': estado_filtro,
    }
    
    return render(request, 'tickets/ticket_list.html', context)

# Vista para crear nuevos tickets en el sistema
@login_required
def ticket_create(request):
    if request.method == 'POST':
        # Obtiene los datos del formulario de creación
        titulo = request.POST.get('titulo')
        descripcion = request.POST.get('descripcion')
        prioridad = request.POST.get('prioridad')
        area = request.POST.get('area')
        
        # Crea un nuevo ticket en la base de datos
        Ticket.objects.create(
            titulo=titulo,
            descripcion=descripcion,
            prioridad=prioridad,
            area_afectada=area,
            creador=request.user
        )
        return redirect('ticket_list')
    return render(request, 'tickets/ticket_form.html')

# Vista para asignar tickets a técnicos (solo administradores)
@user_passes_test(es_admin)
def asignar_ticket(request, ticket_id):
    ticket = Ticket.objects.get(id=ticket_id)
    if request.method == 'POST':
        # Asigna el ticket al técnico seleccionado
        tecnico_id = request.POST.get('tecnico')
        tecnico = User.objects.get(id=tecnico_id)
        ticket.asignado_a = tecnico
        ticket.save()
        return redirect('ticket_list')
    # Obtiene la lista de todos los técnicos disponibles
    tecnicos = User.objects.filter(groups__name='Técnico')
    return render(request, 'tickets/asignar_ticket.html', {
        'ticket': ticket,
        'tecnicos': tecnicos
    })

# Vista para que los técnicos cambien el estado de los tickets asignados
@login_required
def cambiar_estado(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    # Verifica permisos
    if ticket.asignado_a != request.user and not request.user.groups.filter(name='Administrador').exists():
        return HttpResponseForbidden("No tienes permiso para cambiar este ticket.")
    
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        comentario = request.POST.get('comentario', '').strip()
        
        if nuevo_estado and nuevo_estado != ticket.estado:
            # Guarda el estado anterior
            estado_anterior = ticket.estado
            
            # Actualiza el ticket
            ticket.estado = nuevo_estado
            ticket.save()
            
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
    
    # Estados disponibles
    ESTADOS_DISPONIBLES = [
        ('abierto', 'Abierto'),
        ('en_progreso', 'En Progreso'),
        ('resuelto', 'Resuelto'),

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

def ticket_detalle(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)

    # Verifica los permisos para ver el ticket
    es_admin = request.user.groups.filter(name='Administrador').exists()
    es_tecnico_asignado = ticket.asignado_a == request.user
    es_creador = ticket.creador == request.user

    # Solo permitir acceso a usuarios autorizados
    if not (es_admin or es_tecnico_asignado or es_creador):
        return HttpResponseForbidden("No tienes permiso para ver este ticket.")

    # Maneja la creación de nuevos comentarios
    if request.method == 'POST':
        mensaje = request.POST.get('mensaje')
        if mensaje:
            Comentario.objects.create(
                ticket=ticket,
                autor=request.user,
                mensaje=mensaje
            )
            return redirect('ticket_detalle', ticket_id=ticket.id)

    # Obtiene comentarios e historial ordenados por fecha
    comentarios = ticket.comentarios.all().order_by('fecha')
    historial = ticket.historial_estados.all().order_by('fecha')
    return render(request, 'tickets/ticket_detalle.html', {
        'ticket': ticket,
        'comentarios': comentarios,
        'historial': historial
    })

