from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission

class Command(BaseCommand):
    help = 'Crea los roles base para el sistema de tickets'
    def handle(self, *args, **kwargs):
        
        admin_group, _ = Group.objects.get_or_create(name='Administrador')
        tecnico_group, _ = Group.objects.get_or_create(name='Técnico')
        usuario_group, _ = Group.objects.get_or_create(name='Usuario')
        # Permisos (podemos afinar más luego)

        permisos_tickets = Permission.objects.filter(content_type__app_label='tickets')
        admin_group.permissions.set(permisos_tickets)
        tecnico_group.permissions.set(permisos_tickets)
        usuario_group.permissions.clear()  # Usuarios normales no pueden cambiar tickets directamente
        self.stdout.write(self.style.SUCCESS('Roles creados correctamente.'))
