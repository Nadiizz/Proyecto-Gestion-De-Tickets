"""
Comando para poblar la base de datos con las FAQs iniciales.
Migra las preguntas frecuentes estáticas a la base de datos.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from tickets.models import CategoriaFAQ, PreguntaFAQ

User = get_user_model()

class Command(BaseCommand):
    help = 'Poblar la base de datos con las FAQs iniciales del sistema'

    def handle(self, *args, **options):
        # Obtener un usuario admin para asignar como creador
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.first()
        
        self.stdout.write("Iniciando población de FAQs...")
        
        # Definición de las FAQs
        faqs_data = [
            {
                'nombre': 'Preguntas Generales',
                'icono': '❓',
                'descripcion': 'Dudas comunes sobre el sistema de tickets',
                'orden': 0,
                'preguntas': [
                    {
                        'pregunta': '¿Qué es un ticket de soporte?',
                        'respuesta': 'Un ticket de soporte es una solicitud formal que puedes crear para reportar un problema técnico, solicitar asistencia o hacer una consulta al equipo de soporte. Cada ticket tiene un número único de seguimiento y un estado que te permite conocer el progreso de tu solicitud.',
                        'orden': 0
                    },
                    {
                        'pregunta': '¿Cómo puedo crear un nuevo ticket?',
                        'respuesta': 'Para crear un nuevo ticket, haz clic en "Crear Ticket" en el menú lateral. Completa el formulario con un título descriptivo, selecciona la categoría y subcategoría correspondiente, describe detalladamente el problema y adjunta archivos si es necesario. Luego presiona "Crear Ticket".',
                        'orden': 1
                    },
                    {
                        'pregunta': '¿Cuánto tiempo tarda en resolverse un ticket?',
                        'respuesta': 'El tiempo de resolución depende de la prioridad y complejidad del problema. Los tickets críticos se atienden de forma inmediata, los de alta prioridad en menos de 4 horas, los de prioridad media en 24 horas, y los de baja prioridad en 48 horas. Estos tiempos son aproximados y pueden variar según la carga de trabajo.',
                        'orden': 2
                    },
                ]
            },
            {
                'nombre': 'Estados de los Tickets',
                'icono': '📊',
                'descripcion': 'Información sobre los diferentes estados de un ticket',
                'orden': 1,
                'preguntas': [
                    {
                        'pregunta': '¿Qué significa cada estado del ticket?',
                        'respuesta': '''<ul>
                            <li><strong>⏳ Pendiente:</strong> El ticket ha sido creado y está esperando ser revisado por un técnico.</li>
                            <li><strong>🔄 En Progreso:</strong> Un técnico está trabajando activamente en tu solicitud.</li>
                            <li><strong>✅ Resuelto:</strong> El problema ha sido solucionado. Puedes calificar la atención recibida.</li>
                            <li><strong>📁 Cerrado:</strong> El ticket ha sido cerrado definitivamente después de tu confirmación.</li>
                            <li><strong>🚨 SLA Excedido:</strong> El tiempo de respuesta establecido ha sido superado.</li>
                        </ul>''',
                        'orden': 0
                    },
                    {
                        'pregunta': '¿Puedo reabrir un ticket cerrado?',
                        'respuesta': 'No es posible reabrir un ticket cerrado directamente. Si el problema persiste o vuelve a ocurrir, te recomendamos crear un nuevo ticket haciendo referencia al ticket anterior en la descripción.',
                        'orden': 1
                    },
                    {
                        'pregunta': '¿Qué es el SLA y por qué es importante?',
                        'respuesta': 'SLA (Service Level Agreement) es el acuerdo de nivel de servicio que establece los tiempos máximos de respuesta según la prioridad del ticket. Cuando un ticket excede este tiempo, se marca como "SLA Excedido" para darle atención prioritaria.',
                        'orden': 2
                    },
                ]
            },
            {
                'nombre': 'Prioridades',
                'icono': '🎯',
                'descripcion': 'Cómo funcionan las prioridades de los tickets',
                'orden': 2,
                'preguntas': [
                    {
                        'pregunta': '¿Cómo se determina la prioridad de mi ticket?',
                        'respuesta': 'La prioridad es asignada por el equipo técnico basándose en el impacto y urgencia del problema. Factores como la cantidad de usuarios afectados, criticidad del sistema y urgencia del negocio determinan si es Crítica, Alta, Media o Baja.',
                        'orden': 0
                    },
                    {
                        'pregunta': '¿Qué significa cada nivel de prioridad?',
                        'respuesta': '''<ul>
                            <li><strong>🔴 Crítica:</strong> Sistema caído o problema que afecta a toda la organización. Atención inmediata.</li>
                            <li><strong>🟠 Alta:</strong> Problema grave que afecta a un área o proceso crítico. Respuesta en menos de 4 horas.</li>
                            <li><strong>🟡 Media:</strong> Problema que afecta el trabajo pero tiene solución temporal. Respuesta en 24 horas.</li>
                            <li><strong>🟢 Baja:</strong> Consultas, mejoras o problemas menores. Respuesta en 48 horas.</li>
                        </ul>''',
                        'orden': 1
                    },
                    {
                        'pregunta': '¿Puedo cambiar la prioridad de mi ticket?',
                        'respuesta': 'Solo los técnicos y administradores pueden modificar la prioridad de un ticket. Si consideras que tu ticket necesita mayor urgencia, puedes agregar un comentario explicando la situación o contactar directamente al equipo de soporte.',
                        'orden': 2
                    },
                ]
            },
            {
                'nombre': 'Archivos y Adjuntos',
                'icono': '📎',
                'descripcion': 'Cómo trabajar con archivos adjuntos',
                'orden': 3,
                'preguntas': [
                    {
                        'pregunta': '¿Qué tipos de archivos puedo adjuntar?',
                        'respuesta': 'Puedes adjuntar imágenes (JPG, PNG, GIF), documentos PDF, archivos de Word (.doc, .docx), Excel (.xls, .xlsx) y archivos de texto (.txt). El tamaño máximo por archivo es de 10MB.',
                        'orden': 0
                    },
                    {
                        'pregunta': '¿Puedo agregar archivos después de crear el ticket?',
                        'respuesta': 'Sí, puedes agregar archivos adicionales a través de los comentarios del ticket. Simplemente abre el detalle del ticket, escribe un comentario y adjunta el archivo.',
                        'orden': 1
                    },
                    {
                        'pregunta': '¿Cómo puedo tomar una captura de pantalla?',
                        'respuesta': '''En Windows puedes usar:
                        <ul>
                            <li><kbd>Windows</kbd> + <kbd>Shift</kbd> + <kbd>S</kbd> para capturar una región</li>
                            <li><kbd>Print Screen</kbd> para capturar toda la pantalla</li>
                            <li>La herramienta "Recortes" de Windows</li>
                        </ul>
                        Luego guarda la imagen y adjúntala al ticket.''',
                        'orden': 2
                    },
                ]
            },
            {
                'nombre': 'Mi Cuenta',
                'icono': '👤',
                'descripcion': 'Gestión de tu perfil y preferencias',
                'orden': 4,
                'preguntas': [
                    {
                        'pregunta': '¿Cómo puedo cambiar mi contraseña?',
                        'respuesta': 'Ve a "Mi Perfil" en el menú lateral y haz clic en "Cambiar Contraseña". Ingresa tu contraseña actual y luego la nueva contraseña dos veces para confirmar.',
                        'orden': 0
                    },
                    {
                        'pregunta': '¿Cómo actualizo mi foto de perfil?',
                        'respuesta': 'En la sección "Mi Perfil" encontrarás la opción para subir o cambiar tu foto de perfil. Haz clic en tu avatar actual y selecciona una nueva imagen.',
                        'orden': 1
                    },
                    {
                        'pregunta': '¿Cómo configuro las notificaciones?',
                        'respuesta': 'En "Mi Perfil" puedes configurar tus preferencias de notificaciones, incluyendo notificaciones por email y notificaciones del sistema para diferentes eventos como asignaciones, cambios de estado y comentarios.',
                        'orden': 2
                    },
                ]
            },
            {
                'nombre': 'Consejos Útiles',
                'icono': '💡',
                'descripcion': 'Tips para usar mejor el sistema',
                'orden': 5,
                'preguntas': [
                    {
                        'pregunta': '¿Cómo escribir un buen título para mi ticket?',
                        'respuesta': '''Un buen título debe ser:
                        <ul>
                            <li><strong>Específico:</strong> "Error al guardar documento en SAP" en lugar de "Algo no funciona"</li>
                            <li><strong>Breve:</strong> Máximo 10 palabras</li>
                            <li><strong>Descriptivo:</strong> Incluir qué sistema o proceso está afectado</li>
                        </ul>''',
                        'orden': 0
                    },
                    {
                        'pregunta': '¿Qué información debo incluir en la descripción?',
                        'respuesta': '''Para ayudarnos a resolver tu problema más rápido, incluye:
                        <ul>
                            <li>¿Qué estabas haciendo cuando ocurrió el problema?</li>
                            <li>¿Qué mensaje de error aparece (si hay alguno)?</li>
                            <li>¿El problema ocurre siempre o solo a veces?</li>
                            <li>¿Has intentado alguna solución?</li>
                            <li>¿Afecta solo a ti o a más personas?</li>
                        </ul>''',
                        'orden': 1
                    },
                    {
                        'pregunta': '¿Cómo puedo hacer seguimiento de mis tickets?',
                        'respuesta': 'En el menú lateral encontrarás "Mis Tickets" donde puedes ver todos los tickets que has creado, su estado actual y el historial de cada uno. También recibirás notificaciones cuando haya actualizaciones en tus tickets.',
                        'orden': 2
                    },
                ]
            },
        ]
        
        categorias_creadas = 0
        preguntas_creadas = 0
        
        for cat_data in faqs_data:
            # Verificar si la categoría ya existe
            categoria, created = CategoriaFAQ.objects.get_or_create(
                nombre=cat_data['nombre'],
                defaults={
                    'icono': cat_data['icono'],
                    'descripcion': cat_data['descripcion'],
                    'orden': cat_data['orden'],
                    'activa': True,
                    'creado_por': admin_user
                }
            )
            
            if created:
                categorias_creadas += 1
                self.stdout.write(f"  ✓ Categoría creada: {categoria.nombre}")
            else:
                self.stdout.write(f"  - Categoría existente: {categoria.nombre}")
            
            # Crear preguntas
            for preg_data in cat_data['preguntas']:
                pregunta, created = PreguntaFAQ.objects.get_or_create(
                    categoria=categoria,
                    pregunta=preg_data['pregunta'],
                    defaults={
                        'respuesta': preg_data['respuesta'],
                        'orden': preg_data['orden'],
                        'activa': True,
                        'creado_por': admin_user
                    }
                )
                
                if created:
                    preguntas_creadas += 1
        
        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Proceso completado:\n"
            f"   - Categorías creadas: {categorias_creadas}\n"
            f"   - Preguntas creadas: {preguntas_creadas}"
        ))
