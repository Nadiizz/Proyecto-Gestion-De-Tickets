/**
 * Sistema de Notificaciones en Tiempo Real
 * Realiza polling cada 30 segundos para obtener notificaciones nuevas
 * Actualiza el contador en la campana de notificaciones
 * Muestra dropdown con las 5 notificaciones más recientes
 */

// Configuración global
const NOTIFICACIONES_CONFIG = {
    POLLING_INTERVAL: 30000, // 30 segundos
    LIMITE_NUEVAS: 5,
    API_ENDPOINT: '/api/notificaciones/'
};

// Variables globales
let notificacionesPollingInterval = null;
let notificacionesActuales = [];

/**
 * Inicializa el sistema de notificaciones
 * Se ejecuta cuando el DOM está listo
 */
function inicializarNotificaciones() {
    console.log('Inicializando sistema de notificaciones...');
    
    // Obtener notificaciones al cargar la página
    actualizarNotificaciones();
    
    // Configurar polling automático cada 30 segundos
    notificacionesPollingInterval = setInterval(actualizarNotificaciones, NOTIFICACIONES_CONFIG.POLLING_INTERVAL);
    
    // Event listeners
    setupEventListeners();
}

/**
 * Configura los event listeners para el sistema de notificaciones
 */
function setupEventListeners() {
    // Click en la campana de notificaciones
    const campanaNotificaciones = document.getElementById('campana-notificaciones');
    if (campanaNotificaciones) {
        campanaNotificaciones.addEventListener('click', toggleDropdownNotificaciones);
    }
    
    // Click fuera del dropdown para cerrarlo
    document.addEventListener('click', function(event) {
        const dropdown = document.getElementById('dropdown-notificaciones');
        if (dropdown && !event.target.closest('.notification-bell-container')) {
            dropdown.classList.add('hidden');
        }
    });
}

/**
 * Actualiza las notificaciones llamando a la API
 */
function actualizarNotificaciones() {
    fetch(NOTIFICACIONES_CONFIG.API_ENDPOINT + 'nuevas/?limite=' + NOTIFICACIONES_CONFIG.LIMITE_NUEVAS)
        .then(response => response.json())
        .then(data => {
            if (data.notificaciones) {
                notificacionesActuales = data.notificaciones;
                actualizarInterfazNotificaciones();
            }
        })
        .catch(error => console.error('Error al actualizar notificaciones:', error));
}

/**
 * Actualiza la interfaz con las notificaciones nuevas
 */
function actualizarInterfazNotificaciones() {
    // Actualizar contador en la campana
    const contadorNotificaciones = document.getElementById('contador-notificaciones');
    if (contadorNotificaciones && notificacionesActuales.length > 0) {
        contadorNotificaciones.textContent = notificacionesActuales.length;
        contadorNotificaciones.classList.remove('hidden');
    } else if (contadorNotificaciones) {
        contadorNotificaciones.classList.add('hidden');
    }
    
    // Actualizar dropdown
    actualizarDropdownNotificaciones();
}

/**
 * Actualiza el contenido del dropdown con las notificaciones
 */
function actualizarDropdownNotificaciones() {
    const dropdownBody = document.getElementById('dropdown-body-notificaciones');
    
    if (!dropdownBody) return;
    
    // Limpiar contenido anterior
    dropdownBody.innerHTML = '';
    
    if (notificacionesActuales.length === 0) {
        dropdownBody.innerHTML = '<div class="text-center text-gray-500 py-4">Sin notificaciones nuevas</div>';
        return;
    }
    
    // Crear elemento para cada notificación
    notificacionesActuales.forEach(notif => {
        const element = crearElementoNotificacion(notif);
        dropdownBody.appendChild(element);
    });
    
    // Agregar enlace a ver todas
    const verTodas = document.createElement('div');
    verTodas.className = 'border-t pt-2 mt-2';
    verTodas.innerHTML = '<a href="/notificaciones/" class="text-center block text-blue-600 hover:text-blue-800 text-sm">Ver todas las notificaciones</a>';
    dropdownBody.appendChild(verTodas);
}

/**
 * Crea el elemento HTML para una notificación
 */
function crearElementoNotificacion(notif) {
    const div = document.createElement('div');
    div.className = 'border-b pb-3 mb-3 hover:bg-gray-50 p-2 rounded cursor-pointer notification-item';
    div.id = 'notif-' + notif.id;
    
    // Color de prioridad
    let colorPrioridad = 'bg-green-100';
    let textoPrioridad = '🟢';
    if (notif.prioridad === 'critica') {
        colorPrioridad = 'bg-red-100';
        textoPrioridad = '🔴';
    } else if (notif.prioridad === 'alta') {
        colorPrioridad = 'bg-orange-100';
        textoPrioridad = '🟠';
    } else if (notif.prioridad === 'media') {
        colorPrioridad = 'bg-blue-100';
        textoPrioridad = '🔵';
    }
    
    // Emoji según tipo
    let emoji = '📌';
    if (notif.tipo === 'ticket_asignado') emoji = '📋';
    if (notif.tipo === 'ticket_comentario') emoji = '💬';
    if (notif.tipo === 'ticket_resuelto') emoji = '✅';
    if (notif.tipo === 'estado_cambio') emoji = '🔄';
    
    // Fecha formateada
    const fecha = new Date(notif.fecha_creacion);
    const fechaFormato = fecha.toLocaleString('es-CO', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
    
    div.innerHTML = `
        <div class="flex items-start gap-2">
            <span class="text-lg">${emoji}</span>
            <div class="flex-1">
                <p class="font-semibold text-gray-800">${escapeHtml(notif.titulo)}</p>
                <p class="text-sm text-gray-600">${notif.mensaje}</p>
                <div class="flex justify-between items-center mt-1">
                    <span class="inline-block ${colorPrioridad} px-2 py-1 rounded text-xs font-semibold">
                        ${textoPrioridad} ${notif.prioridad.toUpperCase()}
                    </span>
                    <span class="text-xs text-gray-400">${fechaFormato}</span>
                </div>
            </div>
            <button class="ml-2 text-gray-400 hover:text-red-600" onclick="marcarNotificacionLeida(${notif.id}, event)">
                ✕
            </button>
        </div>
    `;
    
    // Click en la notificación
    div.querySelector('.flex-1').addEventListener('click', function() {
        if (notif.enlace) {
            marcarNotificacionLeida(notif.id).then(() => {
                window.location.href = notif.enlace;
            });
        }
    });
    
    return div;
}

/**
 * Marca una notificación como leída
 */
function marcarNotificacionLeida(notifId, event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    
    return fetch(`/api/notificaciones/${notifId}/marcar-leida/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Remover del estado local
            notificacionesActuales = notificacionesActuales.filter(n => n.id !== notifId);
            
            // Remover del DOM
            const element = document.getElementById('notif-' + notifId);
            if (element) {
                element.style.opacity = '0';
                element.style.transition = 'opacity 0.3s';
                setTimeout(() => {
                    element.remove();
                    actualizarInterfazNotificaciones();
                }, 300);
            }
        }
    })
    .catch(error => console.error('Error al marcar notificación como leída:', error));
}

/**
 * Marca todas las notificaciones como leídas
 */
function marcarTodasLeidasNotificaciones() {
    fetch('/api/notificaciones/marcar-todas-leidas/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            notificacionesActuales = [];
            actualizarInterfazNotificaciones();
            console.log('Todas las notificaciones marcadas como leídas');
        }
    })
    .catch(error => console.error('Error al marcar todas como leídas:', error));
}

/**
 * Alterna la visibilidad del dropdown
 */
function toggleDropdownNotificaciones() {
    const dropdown = document.getElementById('dropdown-notificaciones');
    if (dropdown) {
        dropdown.classList.toggle('hidden');
    }
}

/**
 * Obtiene el valor de una cookie
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 * Escapa caracteres HTML para prevenir XSS
 */
function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

/**
 * Detiene el polling de notificaciones
 */
function detenerPollingNotificaciones() {
    if (notificacionesPollingInterval) {
        clearInterval(notificacionesPollingInterval);
        console.log('Polling de notificaciones detenido');
    }
}

/**
 * Inicia el polling de notificaciones
 */
function iniciarPollingNotificaciones() {
    if (!notificacionesPollingInterval) {
        notificacionesPollingInterval = setInterval(actualizarNotificaciones, NOTIFICACIONES_CONFIG.POLLING_INTERVAL);
        console.log('Polling de notificaciones iniciado');
    }
}

// Inicializar cuando el DOM esté listo
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inicializarNotificaciones);
} else {
    inicializarNotificaciones();
}

// Limpiar polling cuando se cierra la página
window.addEventListener('beforeunload', detenerPollingNotificaciones);
