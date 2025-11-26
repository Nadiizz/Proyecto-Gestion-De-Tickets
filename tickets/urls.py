from django.urls import path
from . import views

urlpatterns = [
    # path('registro/', views.registro, name='registro'),  # Desactivado: solo registro mediante invitaciones
    path('logout/', views.cerrar_sesion, name='logout'),
    path('', views.ticket_list, name='ticket_list'),
    path('nuevo/', views.ticket_create, name='ticket_create'),
    path('asignar/<int:ticket_id>/', views.asignar_ticket, name='asignar_ticket'),
    path('estado/<int:ticket_id>/', views.cambiar_estado, name='cambiar_estado'),
    path('ticket/<int:ticket_id>/', views.ticket_detalle, name='ticket_detalle'),
    path('metricas/', views.metricas, name='metricas'),
    path('calificar/<int:ticket_id>/', views.calificar_ticket, name='calificar_ticket'),
    path('mis-tickets/', views.mis_tickets, name='mis_tickets'),
    path('mis-asignaciones/', views.mis_asignaciones, name='mis_asignaciones'),
    path('perfil/', views.mi_perfil, name='mi_perfil'),
    path('notificaciones/', views.lista_notificaciones, name='lista_notificaciones'),
    
    # API para obtener subcategorías por categoría
    path('api/subcategorias/<int:categoria_id>/', views.obtener_subcategorias, name='obtener_subcategorias'),
    
    # API de Notificaciones
    path('api/notificaciones/', views.api_notificaciones, name='api_notificaciones'),
    path('api/notificaciones/nuevas/', views.api_notificaciones_nuevas, name='api_notificaciones_nuevas'),
    path('api/notificaciones/<int:notificacion_id>/marcar-leida/', views.api_marcar_notificacion_leida, name='api_marcar_notificacion_leida'),
    path('api/notificaciones/marcar-todas-leidas/', views.api_marcar_todas_leidas, name='api_marcar_todas_leidas'),
    
    # URLs del Admin Panel
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    
    # Gestión de Usuarios
    path('admin-panel/usuarios/', views.admin_usuarios, name='admin_usuarios'),
    path('admin-panel/usuarios/crear/', views.admin_crear_usuario, name='admin_crear_usuario'),
    path('admin-panel/usuarios/editar/<int:user_id>/', views.admin_editar_usuario, name='admin_editar_usuario'),
    path('admin-panel/usuarios/toggle/<int:user_id>/', views.admin_toggle_usuario, name='admin_toggle_usuario'),
    path('admin-panel/usuarios/eliminar/<int:user_id>/', views.admin_eliminar_usuario, name='admin_eliminar_usuario'),
    
    # Gestión de Roles
    path('admin-panel/roles/', views.admin_roles, name='admin_roles'),
    path('admin-panel/roles/crear/', views.admin_crear_rol, name='admin_crear_rol'),
    path('admin-panel/roles/editar/<int:rol_id>/', views.admin_editar_rol, name='admin_editar_rol'),
    path('admin-panel/roles/eliminar/<int:rol_id>/', views.admin_eliminar_rol, name='admin_eliminar_rol'),
    
    # Gestión de Categorías y Subcategorías
    path('admin-panel/categorias/', views.admin_categorias, name='admin_categorias'),
    path('admin-panel/categorias/crear/', views.admin_crear_categoria, name='admin_crear_categoria'),
    path('admin-panel/categorias/editar/<int:categoria_id>/', views.admin_editar_categoria, name='admin_editar_categoria'),
    path('admin-panel/categorias/eliminar/<int:categoria_id>/', views.admin_eliminar_categoria, name='admin_eliminar_categoria'),
    
    path('admin-panel/subcategorias/', views.admin_subcategorias, name='admin_subcategorias'),
    path('admin-panel/subcategorias/crear/', views.admin_crear_subcategoria, name='admin_crear_subcategoria'),
    path('admin-panel/subcategorias/editar/<int:subcategoria_id>/', views.admin_editar_subcategoria, name='admin_editar_subcategoria'),
    path('admin-panel/subcategorias/eliminar/<int:subcategoria_id>/', views.admin_eliminar_subcategoria, name='admin_eliminar_subcategoria'),
]
