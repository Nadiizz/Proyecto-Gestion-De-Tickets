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
    setupFilePreview();
    setupDragAndDrop();
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

/**
 * Configura la vista previa de archivos adjuntos
 * Muestra miniaturas de imágenes y nombres de otros archivos
 * Permite acumular archivos seleccionándolos de forma incremental
 */
function setupFilePreview() {
    console.log('📎 Configurando vista previa de archivos...');
    
    const fileInput = document.querySelector('input[type="file"][name="archivos"]');
    
    if (!fileInput) {
        console.log('⚠️ No se encontró el input de archivos');
        return;
    }
    
    // Array para almacenar todos los archivos acumulados
    let allFiles = [];
    
    // Crear contenedor de vista previa si no existe
    let previewContainer = document.getElementById('file-preview-container');
    if (!previewContainer) {
        previewContainer = document.createElement('div');
        previewContainer.id = 'file-preview-container';
        previewContainer.className = 'file-preview-container';
        fileInput.parentElement.appendChild(previewContainer);
    }
    
    fileInput.addEventListener('change', function(e) {
        console.log('📁 Archivos seleccionados:', e.target.files.length);
        
        if (e.target.files.length === 0) {
            return;
        }
        
        // Agregar nuevos archivos al array (evitar duplicados por nombre)
        Array.from(e.target.files).forEach((newFile) => {
            const isDuplicate = allFiles.some(existingFile => 
                existingFile.name === newFile.name && existingFile.size === newFile.size
            );
            
            if (!isDuplicate) {
                allFiles.push(newFile);
                console.log(`➕ Archivo agregado: ${newFile.name}`);
            } else {
                console.log(`⚠️ Archivo duplicado omitido: ${newFile.name}`);
            }
        });
        
        // Actualizar el input con todos los archivos acumulados
        const dt = new DataTransfer();
        allFiles.forEach(file => dt.items.add(file));
        fileInput.files = dt.files;
        
        // Renderizar todas las previsualizaciones
        renderPreviews();
    });
    
    function renderPreviews() {
        previewContainer.innerHTML = '';
        
        allFiles.forEach((file, index) => {
            const filePreview = document.createElement('div');
            filePreview.className = 'file-preview-item';
            
            // Crear elemento de vista previa
            const previewContent = document.createElement('div');
            previewContent.className = 'file-preview-content';
            
            // Verificar si es imagen
            if (file.type.startsWith('image/')) {
                const img = document.createElement('img');
                img.className = 'file-preview-image';
                
                const reader = new FileReader();
                reader.onload = function(e) {
                    img.src = e.target.result;
                };
                reader.readAsDataURL(file);
                
                previewContent.appendChild(img);
            } else {
                // Para archivos no-imagen, mostrar icono
                const fileIcon = document.createElement('div');
                fileIcon.className = 'file-preview-icon';
                
                // Determinar icono según extensión
                const extension = file.name.split('.').pop().toLowerCase();
                let icon = '📄';
                
                if (['pdf'].includes(extension)) icon = '📕';
                else if (['doc', 'docx'].includes(extension)) icon = '📘';
                else if (['xls', 'xlsx'].includes(extension)) icon = '📗';
                else if (['txt'].includes(extension)) icon = '📃';
                
                fileIcon.textContent = icon;
                previewContent.appendChild(fileIcon);
            }
            
            // Información del archivo
            const fileInfo = document.createElement('div');
            fileInfo.className = 'file-preview-info';
            
            const fileName = document.createElement('div');
            fileName.className = 'file-preview-name';
            fileName.textContent = file.name;
            fileName.title = file.name;
            
            const fileSize = document.createElement('div');
            fileSize.className = 'file-preview-size';
            fileSize.textContent = formatFileSize(file.size);
            
            fileInfo.appendChild(fileName);
            fileInfo.appendChild(fileSize);
            
            // Botón para eliminar
            const removeBtn = document.createElement('button');
            removeBtn.type = 'button';
            removeBtn.className = 'file-preview-remove';
            removeBtn.innerHTML = '×';
            removeBtn.title = 'Eliminar archivo';
            removeBtn.onclick = function() {
                // Eliminar del array
                allFiles.splice(index, 1);
                console.log(`🗑️ Archivo eliminado: ${file.name}`);
                
                // Actualizar el input de archivos
                const dt = new DataTransfer();
                allFiles.forEach(f => dt.items.add(f));
                fileInput.files = dt.files;
                
                // Volver a renderizar
                renderPreviews();
            };
            
            filePreview.appendChild(previewContent);
            filePreview.appendChild(fileInfo);
            filePreview.appendChild(removeBtn);
            
            previewContainer.appendChild(filePreview);
        });
        
        console.log(`📊 Total de archivos: ${allFiles.length}`);
    }
    
    console.log('✅ Vista previa de archivos configurada');
}

/**
 * Formatea el tamaño del archivo en formato legible
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Configura la funcionalidad de drag & drop para archivos
 */
function setupDragAndDrop() {
    console.log('🎯 Configurando drag & drop...');
    
    const uploadZone = document.getElementById('file-upload-zone');
    const fileInput = document.querySelector('input[type="file"][name="archivos"]');
    
    if (!uploadZone || !fileInput) {
        console.log('⚠️ No se encontró la zona de drag & drop');
        return;
    }
    
    // Prevenir comportamiento por defecto del navegador
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadZone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });
    
    // Destacar zona cuando se arrastra sobre ella
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadZone.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        uploadZone.addEventListener(eventName, unhighlight, false);
    });
    
    // Manejar el drop
    uploadZone.addEventListener('drop', handleDrop, false);
    
    // Click en la zona para abrir selector
    uploadZone.addEventListener('click', function(e) {
        if (e.target.tagName !== 'BUTTON' && e.target.tagName !== 'INPUT') {
            fileInput.click();
        }
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    function highlight() {
        uploadZone.classList.add('drag-over');
    }
    
    function unhighlight() {
        uploadZone.classList.remove('drag-over');
    }
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        // Crear un nuevo evento con los archivos
        const event = new Event('change', { bubbles: true });
        
        // Crear DataTransfer temporal para simular selección de archivos
        const dataTransfer = new DataTransfer();
        Array.from(files).forEach(file => dataTransfer.items.add(file));
        fileInput.files = dataTransfer.files;
        
        // Disparar el evento change
        fileInput.dispatchEvent(event);
        
        console.log(`📥 Archivos soltados: ${files.length}`);
    }
    
    console.log('✅ Drag & drop configurado');
}
