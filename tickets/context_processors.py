# Context processors para el sistema de tickets
# Proporciona variables globales a todos los templates

def permisos_usuario(request):
    """
    Context processor que proporciona los permisos del usuario actual
    basados en su rol personalizado o grupo tradicional.
    """
    if not request.user.is_authenticated:
        return {
            'permisos': {
                'puede_ver_metricas': False,
                'puede_ver_todos_tickets': False,
                'puede_asignar_tickets': False,
                'puede_cambiar_estado': False,
                'puede_gestionar_usuarios': False,
                'puede_crear_roles': False,
                'puede_validar_prioridad': False,
                'es_admin': False,
                'es_tecnico': False,
                'puede_acceder_admin': False,
            }
        }
    
    user = request.user
    
    # Importar las funciones de verificación de permisos
    from tickets.views import (
        es_admin, es_tecnico, puede_ver_metricas, puede_ver_todos_tickets,
        puede_asignar_tickets, puede_cambiar_estado, puede_gestionar_usuarios,
        puede_crear_roles, puede_acceder_admin_panel, puede_validar_prioridad
    )
    
    # Construimos permisos consultando las funciones centrales pero añadimos
    # una verificación directa sobre el perfil para mayor tolerancia
    permisos = {
        'puede_ver_metricas': puede_ver_metricas(user),
        'puede_ver_todos_tickets': puede_ver_todos_tickets(user),
        'puede_asignar_tickets': puede_asignar_tickets(user),
        'puede_cambiar_estado': puede_cambiar_estado(user),
        'puede_gestionar_usuarios': puede_gestionar_usuarios(user),
        'puede_crear_roles': puede_crear_roles(user),
        # Puede validar prioridad: consulta la lógica central, pero si por alguna
        # razón el perfil asociado no existe o la función falla, intentamos
        # leer el permiso directamente desde el PerfilUsuario/rol_personalizado.
        'puede_validar_prioridad': None,
        'es_admin': es_admin(user),
        'es_tecnico': es_tecnico(user),
        'puede_acceder_admin': puede_acceder_admin_panel(user),
    }

    # Determinar 'puede_validar_prioridad' de forma robusta
    try:
        # Primera opción: función existente (que cubre admins y roles personalizados)
        permisos['puede_validar_prioridad'] = puede_validar_prioridad(user)
    except Exception:
        permisos['puede_validar_prioridad'] = False

    # Si aún no se determinó correctamente, verificar el perfil/rol (fallback)
    if not permisos['puede_validar_prioridad']:
        try:
            from tickets.models import PerfilUsuario
            perfil = PerfilUsuario.objects.select_related('rol_personalizado').filter(user=user).first()
            if perfil and perfil.rol_personalizado and getattr(perfil.rol_personalizado, 'puede_validar_prioridad', False):
                permisos['puede_validar_prioridad'] = True
        except Exception:
            # no hay perfil o algo salió mal, dejamos False
            permisos['puede_validar_prioridad'] = permisos['puede_validar_prioridad'] or False
    
    return {'permisos': permisos}
