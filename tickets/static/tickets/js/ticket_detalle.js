/**
 * ticket_detalle.js - Funcionalidades JavaScript para la vista detalle del ticket
 * 
 * Funcionalidades:
 * - Vista previa de archivos adjuntos en comentarios con drag & drop
 * - Validación de formulario de comentarios
 * - Mejoras de UX
 */

console.log('🔧 ticket_detalle.js cargado correctamente');

document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ DOM completamente cargado, inicializando vista detalle...');
    initializeTicketDetail();
});

function initializeTicketDetail() {
    console.log('🎯 Inicializando funciones de detalle del ticket...');
    setupCommentFilePreview();
    setupDragAndDrop();
    setupCommentFormValidation();
}

/**
 * Configura la vista previa de archivos adjuntos en comentarios
 */
function setupCommentFilePreview() {
    console.log('📎 Configurando vista previa de archivos en comentarios...');
    
    const fileInput = document.getElementById('archivos_comentario');
    const previewContainer = document.getElementById('comment-file-preview');
    
    if (!fileInput || !previewContainer) {
        console.log('⚠️ No se encontró el input o contenedor de vista previa');
        return;
    }
    
    fileInput.addEventListener('change', function(e) {
        console.log('📁 Archivos seleccionados para comentario:', e.target.files.length);
        previewContainer.innerHTML = '';
        
        if (e.target.files.length === 0) {
            return;
        }
        
        Array.from(e.target.files).forEach((file, index) => {
            console.log(`📄 Procesando archivo ${index + 1}: ${file.name}`);
            
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
            
            filePreview.appendChild(previewContent);
            
            // Nombre del archivo
            const fileName = document.createElement('div');
            fileName.className = 'file-preview-name';
            fileName.textContent = file.name.length > 15 ? file.name.substring(0, 12) + '...' : file.name;
            fileName.title = file.name;
            
            filePreview.appendChild(fileName);
            previewContainer.appendChild(filePreview);
        });
    });
    
    console.log('✅ Vista previa de archivos configurada');
}

/**
 * Configura validación del formulario de comentarios
 */
function setupCommentFormValidation() {
    console.log('📝 Configurando validación de formulario de comentarios...');
    
    const commentForm = document.querySelector('.comment-form form');
    const messageTextarea = commentForm ? commentForm.querySelector('textarea[name="mensaje"]') : null;
    
    if (!commentForm || !messageTextarea) {
        console.log('⚠️ No se encontró el formulario de comentarios');
        return;
    }
    
    commentForm.addEventListener('submit', function(e) {
        const message = messageTextarea.value.trim();
        
        if (message.length === 0) {
            e.preventDefault();
            alert('Por favor, escribe un comentario antes de publicar.');
            messageTextarea.focus();
            return false;
        }
        
        console.log('✅ Formulario de comentario validado');
    });
    
    console.log('✅ Validación de comentarios configurada');
}

/**
 * Configura la funcionalidad de drag & drop para archivos
 */
function setupDragAndDrop() {
    console.log('🎨 Configurando drag & drop para comentarios...');
    
    const uploadZone = document.getElementById('comment-file-upload-zone');
    const fileInput = document.getElementById('archivos_comentario');
    
    if (!uploadZone || !fileInput) {
        console.log('⚠️ No se encontró la zona de drag & drop o el input');
        return;
    }
    
    // Prevenir comportamiento por defecto del navegador
    const preventDefaults = (e) => {
        e.preventDefault();
        e.stopPropagation();
    };
    
    // Highlight cuando arrastras sobre la zona
    const highlight = () => {
        uploadZone.classList.add('drag-over');
    };
    
    const unhighlight = () => {
        uploadZone.classList.remove('drag-over');
    };
    
    // Manejar el drop
    const handleDrop = (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        // Asignar archivos al input
        fileInput.files = files;
        
        // Disparar evento change para que se procese la vista previa
        const event = new Event('change', { bubbles: true });
        fileInput.dispatchEvent(event);
    };
    
    // Eventos de drag & drop
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadZone.addEventListener(eventName, preventDefaults, false);
    });
    
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadZone.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        uploadZone.addEventListener(eventName, unhighlight, false);
    });
    
    uploadZone.addEventListener('drop', handleDrop, false);
    
    console.log('✅ Drag & drop configurado');
}
