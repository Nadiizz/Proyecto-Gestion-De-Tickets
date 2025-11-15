/**
ticket_form.js - Funcionalidades JavaScript para el formulario de creación de tickets

Funcionalidades implementadas:
- Contador de caracteres en tiempo real para la descripción
- Validación de descripción según prioridad del ticket
- Efectos visuales dinámicos para selección de prioridad
- Mejoras de UX (auto-focus, ayuda contextual)
- Prevención de envío con descripciones insuficientes

Estructura modular:
1. initializeForm() - Punto de entrada principal
2. setupCharacterCounter() - Controla límite de caracteres
3. setupPriorityValidation() - Valida prioridad vs descripción
4. setupPriorityVisualEffects() - Efectos visuales para prioridades
5. enhanceFormUX() - Mejoras adicionales de experiencia de usuario

Notas:
- Las validaciones se ejecutan al enviar el formulario
-Los estilos visuales se aplican automáticamente
- Compatible con todos los navegadores modernos
*/



console.log('🔧 ticket_form.js cargado correctamente');

document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ DOM completamente cargado, inicializando formulario...');
    initializeForm();
});

function initializeForm() {
    console.log('🎯 Inicializando funciones del formulario...');
    setupCharacterCounter();
    setupPriorityValidation();
    setupPriorityVisualEffects();
    enhanceFormUX();
}

function setupCharacterCounter() {
    const descripcion = document.getElementById('descripcion');
    const charCount = document.getElementById('char-count');
    
    console.log('📊 Configurando contador de caracteres...');
    console.log('Elemento descripción:', descripcion);
    console.log('Elemento contador:', charCount);
    
    if (!descripcion || !charCount) {
        console.error('❌ No se encontraron los elementos para el contador de caracteres');
        return;
    }
    
    // Función para actualizar el contador
    function updateCounter() {
        const length = descripcion.value.length;
        console.log('Caracteres escritos:', length);
        charCount.textContent = length;
        updateCounterStyle(length, charCount.parentElement);
    }
    
    // Event listeners
    descripcion.addEventListener('input', updateCounter);
    descripcion.addEventListener('change', updateCounter);
    descripcion.addEventListener('keyup', updateCounter);
    descripcion.addEventListener('paste', function() {
        setTimeout(updateCounter, 10);
    });
    
    // Actualizar contador inicial
    updateCounter();
    console.log('✅ Contador de caracteres configurado correctamente');
}

function updateCounterStyle(length, counterElement) {
    if (!counterElement) return;
    
    // Remover clases anteriores
    counterElement.classList.remove('warning', 'error');
    
    // Aplicar clases según la longitud
    if (length > 1800) {
        counterElement.classList.add('error');
        console.log('🔴 Contador en estado ERROR (>1800 caracteres)');
    } else if (length > 1500) {
        counterElement.classList.add('warning');
        console.log('🟡 Contador en estado WARNING (>1500 caracteres)');
    } else if (length > 0) {
        console.log('🟢 Contador en estado NORMAL');
    }
}

function setupPriorityValidation() {
    const prioridadSelect = document.getElementById('prioridad');
    const form = document.querySelector('.ticket-form');
    
    console.log('⚡ Configurando validación de prioridad...');
    
    if (!form || !prioridadSelect) {
        console.error('❌ No se encontró el formulario o selector de prioridad');
        return;
    }
    
    form.addEventListener('submit', function(e) {
        const descripcion = document.getElementById('descripcion');
        const prioridad = prioridadSelect.value;
        
        console.log('📨 Intentando enviar formulario...');
        console.log('Prioridad seleccionada:', prioridad);
        console.log('Longitud descripción:', descripcion.value.length);
        
        if (validatePriorityDescription(prioridad, descripcion.value)) {
            e.preventDefault();
            console.log('🚫 Envío bloqueado - descripción insuficiente');
            showPriorityAlert(prioridad);
            descripcion.focus();
        } else {
            console.log('✅ Validación pasada - enviando formulario');
        }
    });
    
    console.log('✅ Validación de prioridad configurada');
}

function validatePriorityDescription(prioridad, descripcion) {
    const descLength = descripcion.length;
    
    if (prioridad === 'critica' && descLength < 100) {
        return true;
    } else if (prioridad === 'alta' && descLength < 50) {
        return true;
    }
    
    return false;
}

function showPriorityAlert(prioridad) {
    const messages = {
        'critica': '⚠️ Para tickets de prioridad CRÍTICA, por favor proporciona una descripción detallada (mínimo 100 caracteres) incluyendo:\n\n• Qué sistema está afectado\n• Cuántos usuarios impactados\n• Desde cuándo ocurre el problema\n• Mensajes de error específicos',
        'alta': '⚠️ Para tickets de prioridad ALTA, por favor proporciona una descripción más detallada (mínimo 50 caracteres)'
    };
    
    alert(messages[prioridad] || 'Por favor completa la descripción del ticket');
}

function setupPriorityVisualEffects() {
    const prioridadSelect = document.getElementById('prioridad');
    
    console.log('🎨 Configurando efectos visuales de prioridad...');
    
    if (!prioridadSelect) {
        console.error('No se encontró el selector de prioridad');
        return;
    }
    
    prioridadSelect.addEventListener('change', function() {
        console.log('Prioridad cambiada a:', this.value);
        updatePriorityVisual(this);
    });
    
    // Aplicar estilo inicial si ya hay un valor seleccionado
    updatePriorityVisual(prioridadSelect);
    console.log('✅ Efectos visuales de prioridad configurados');
}

function updatePriorityVisual(selectElement) {
    const selectedValue = selectElement.value;
    
    // Resetear estilos
    selectElement.style.borderColor = '';
    selectElement.style.boxShadow = '';
    
    // Aplicar estilos según prioridad
    switch(selectedValue) {
        case 'critica':
            selectElement.style.borderColor = '#e74c3c';
            selectElement.style.boxShadow = '0 0 0 3px rgba(231, 76, 60, 0.1)';
            console.log('🔴 Aplicado estilo para prioridad CRÍTICA');
            break;
        case 'alta':
            selectElement.style.borderColor = '#f39c12';
            selectElement.style.boxShadow = '0 0 0 3px rgba(243, 156, 18, 0.1)';
            console.log('🟠 Aplicado estilo para prioridad ALTA');
            break;
        case 'media':
            selectElement.style.borderColor = '#f1c40f';
            selectElement.style.boxShadow = '0 0 0 3px rgba(241, 196, 15, 0.1)';
            console.log('🟡 Aplicado estilo para prioridad MEDIA');
            break;
        case 'baja':
            selectElement.style.borderColor = '#27ae60';
            selectElement.style.boxShadow = '0 0 0 3px rgba(39, 174, 96, 0.1)';
            console.log('🟢 Aplicado estilo para prioridad BAJA');
            break;
        default:
            console.log('Prioridad no seleccionada');
    }
}

function enhanceFormUX() {
    console.log('🎭 Aplicando mejoras de UX...');
    
    // Auto-focus en el primer campo
    const firstInput = document.querySelector('input[type="text"]');
    if (firstInput) {
        firstInput.focus();
        console.log('🎯 Auto-focus aplicado al primer campo');
    }
    
    console.log('✅ Mejoras de UX aplicadas');
}