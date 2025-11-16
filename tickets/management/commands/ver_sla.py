"""
Script para verificar el estado de los SLAs de los tickets.
Útil para debugging y verificación manual.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from tickets.models import Ticket


class Command(BaseCommand):
    help = 'Muestra información de tickets y sus SLAs'

    def handle(self, *args, **options):
        now = timezone.now()
        
        self.stdout.write(self.style.SUCCESS(f'\n=== VERIFICACIÓN DE SLA - {now} ===\n'))
        
        # Tickets activos con SLA
        tickets_activos = Ticket.objects.filter(
            estado__in=['pendiente', 'en_progreso'],
            tiempo_limite_resolucion__isnull=False
        ).order_by('tiempo_limite_resolucion')
        
        self.stdout.write(f'Total de tickets activos con SLA: {tickets_activos.count()}\n')
        
        excedidos = 0
        por_vencer = 0
        
        for ticket in tickets_activos:
            tiempo_restante = ticket.tiempo_limite_resolucion - now
            horas_restantes = tiempo_restante.total_seconds() / 3600
            
            if horas_restantes < 0:
                excedidos += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'❌ Ticket #{ticket.id} - "{ticket.titulo}" - '
                        f'SLA EXCEDIDO hace {abs(horas_restantes):.1f} horas'
                    )
                )
            elif horas_restantes < 2:
                por_vencer += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠️  Ticket #{ticket.id} - "{ticket.titulo}" - '
                        f'SLA vence en {horas_restantes:.1f} horas'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Ticket #{ticket.id} - "{ticket.titulo}" - '
                        f'SLA en {horas_restantes:.1f} horas'
                    )
                )
        
        # Resumen
        self.stdout.write(f'\n=== RESUMEN ===')
        self.stdout.write(f'Tickets con SLA excedido: {excedidos}')
        self.stdout.write(f'Tickets por vencer (< 2hrs): {por_vencer}')
        self.stdout.write(f'Tickets en buen estado: {tickets_activos.count() - excedidos - por_vencer}\n')
        
        # Tickets ya marcados como excedidos
        ya_excedidos = Ticket.objects.filter(estado='tiempo_excedido').count()
        self.stdout.write(f'Tickets ya marcados como "tiempo_excedido": {ya_excedidos}\n')
