from django.core.management.base import BaseCommand
from tickets.models import Categoria, Subcategoria


class Command(BaseCommand):
    help = 'Crea las categorías y subcategorías iniciales'

    def handle(self, *args, **options):
        # Definir categorías y sus subcategorías
        categorias_data = {
            'Finanzas': [
                'Nómina',
                'Facturas',
                'Reportes financieros',
                'Contabilidad',
                'Reembolsos',
            ],
            'RRHH': [
                'Vacaciones',
                'Permisos',
                'Beneficios',
                'Capacitación',
                'Actualización de datos',
            ],
            'IT': [
                'Acceso a sistemas',
                'Soporte técnico',
                'Hardware',
                'Software',
                'Conectividad de red',
                'Impresoras',
            ],
            'Operaciones': [
                'Procesos',
                'Proveedores',
                'Logística',
                'Compras',
                'Inventario',
            ],
            'Legales': [
                'Documentos legales',
                'Contratos',
                'Compliance',
                'Consultas legales',
            ],
            'Marketing': [
                'Campañas',
                'Contenido',
                'Social media',
                'Diseño',
                'Publicidad',
            ],
        }

        for categoria_nombre, subcategorias in categorias_data.items():
            # Crear o obtener la categoría
            categoria, created = Categoria.objects.get_or_create(
                nombre=categoria_nombre,
                defaults={'descripcion': f'Categoría de {categoria_nombre}'}
            )
            
            if created:
                self.stdout.write(f'✓ Categoría creada: {categoria_nombre}')
            else:
                self.stdout.write(f'→ Categoría existente: {categoria_nombre}')
            
            # Crear subcategorías
            for subcategoria_nombre in subcategorias:
                subcategoria, created = Subcategoria.objects.get_or_create(
                    categoria=categoria,
                    nombre=subcategoria_nombre
                )
                
                if created:
                    self.stdout.write(f'  ✓ Subcategoría creada: {subcategoria_nombre}')
                else:
                    self.stdout.write(f'  → Subcategoría existente: {subcategoria_nombre}')

        self.stdout.write(self.style.SUCCESS('✓ Categorías y subcategorías configuradas correctamente'))
