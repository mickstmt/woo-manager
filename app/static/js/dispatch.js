// dispatch.js - Lógica del Módulo de Despacho Kanban

// Estado global
let currentOrderId = null;
let currentOrderData = null;
let sortableInstances = [];
let currentVisibleOrderIds = []; // Lista de IDs de pedidos visibles
let orderDetailModalInstance = null; // Instancia única del modal

// ============================================
// SELECCIÓN MASIVA CHAMO/DINSIDES
// ============================================

// Variables para selección masiva
let bulkSelectedOrders = [];  // Array de {orderId, orderNumber}
let bulkSelectedColumn = null; // 'chamo' o 'dinsides'

// Plantillas de mensajes de tracking por columna (con placeholder @fecha_envio)
const BULK_TRACKING_TEMPLATES = {
    chamo: {
        normal: "Hola, somos izistore. Su pedido estará llegando el @fecha_envio entre las 11:00 am y 7:00 pm.",
        cod: "Hola, somos izistore. Su pedido estará llegando el @fecha_envio entre las 11:00 am y 7:00 pm.\n\n⚠️ IMPORTANTE: Este pedido es PAGO CONTRAENTREGA.\nMonto a cancelar: S/ @monto\n\nPor favor, tenga el monto exacto disponible para el courier."
    },
    dinsides: {
        normal: "Hola, somos izistore. Su pedido está programado para ser entregado el: @fecha_envio entre las 11:00 AM y 7:00 PM.",
        cod: "Hola, somos izistore. Su pedido está programado para ser entregado el: @fecha_envio entre las 11:00 AM y 7:00 PM.\n\n⚠️ IMPORTANTE: Este pedido es PAGO CONTRAENTREGA.\nMonto a cancelar: S/ @monto\n\nPor favor, tenga el monto exacto disponible para el courier."
    }
};

/**
 * Generar mensaje de tracking reemplazando placeholders
 * @param {string} column - Columna (chamo o dinsides)
 * @param {string} dateStr - Fecha de envío (yyyy-mm-dd)
 * @param {object} orderData - Datos del pedido (incluye is_cod, total, etc.)
 */
function generateBulkTrackingMessage(column, dateStr, orderData = {}) {
    const templates = BULK_TRACKING_TEMPLATES[column];
    if (!templates) return '';

    // Seleccionar template según si es COD o no
    const template = orderData.is_cod ? templates.cod : templates.normal;

    // Formatear fecha a formato legible (ej: "21 de enero")
    const formattedDate = formatDateForMessage(dateStr);

    // Reemplazar placeholders
    let message = template.replace('@fecha_envio', formattedDate);

    // Si es COD, reemplazar monto (Total - Costo de envío ya pagado)
    if (orderData.is_cod && orderData.total) {
        const shippingCost = orderData.shipping_cost || 0;
        const codAmount = orderData.total - shippingCost;
        message = message.replace('@monto', codAmount.toFixed(2));
    }

    return message;
}

/**
 * Formatear fecha para el mensaje (ej: "21 de enero")
 */
function formatDateForMessage(dateStr) {
    if (!dateStr) {
        console.warn('formatDateForMessage: dateStr vacío');
        return '[Fecha no seleccionada]';
    }

    const months = [
        'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
        'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
    ];

    // Limpiar la fecha (por si tiene espacios)
    const cleanDateStr = dateStr.trim();
    console.log('formatDateForMessage - Input:', cleanDateStr);

    // Validar formato de fecha
    const parts = cleanDateStr.split('-');
    if (parts.length !== 3) {
        console.error('Formato de fecha inválido:', cleanDateStr, 'parts:', parts);
        return '[Fecha inválida]';
    }

    const [year, month, day] = parts;
    console.log('formatDateForMessage - Parsed:', { year, month, day });

    const dayNum = parseInt(day, 10);
    const monthIndex = parseInt(month, 10) - 1;

    // Validar que los valores sean números válidos
    if (isNaN(dayNum) || isNaN(monthIndex) || monthIndex < 0 || monthIndex > 11) {
        console.error('Valores de fecha inválidos:', { day, month, dayNum, monthIndex });
        return '[Fecha inválida]';
    }

    const monthName = months[monthIndex];
    const result = `${dayNum} de ${monthName}`;
    console.log('formatDateForMessage - Result:', result);

    return result;
}

const BULK_TRACKING_PROVIDERS = {
    chamo: "Motorizado Izi",
    dinsides: "Dinsides Courier"
};

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function () {
    console.log('Módulo de Despacho inicializado');

    // Establecer fechas por defecto: últimos 30 días
    const today = new Date();
    const thirtyDaysAgo = new Date(today);
    thirtyDaysAgo.setDate(today.getDate() - 30);

    document.getElementById('filter-date-from').value = formatDateForInput(thirtyDaysAgo);
    document.getElementById('filter-date-to').value = formatDateForInput(today);

    // Cargar pedidos con filtro de fechas del mes actual
    loadOrders();

    // Auto-refresh cada 2 minutos (solo si no hay modal abierto)
    setInterval(autoRefreshOrders, 120000);

    // Limpiar instancia del modal cuando se cierra
    const modalElement = document.getElementById('orderDetailModal');
    if (modalElement) {
        modalElement.addEventListener('hidden.bs.modal', function () {
            // Limpiar cualquier backdrop residual
            const backdrops = document.querySelectorAll('.modal-backdrop');
            backdrops.forEach(backdrop => backdrop.remove());

            // Restaurar scroll del body
            document.body.classList.remove('modal-open');
            document.body.style.removeProperty('overflow');
            document.body.style.removeProperty('padding-right');
        });
    }
});

/**
 * Auto-refresh de pedidos solo si no hay modales de tracking abiertos
 * Evita perder selecciones de checkboxes mientras el usuario trabaja
 */
function autoRefreshOrders() {
    // Verificar si hay modales de tracking abiertos
    const bulkTrackingModal = document.getElementById('bulkTrackingConfirmModal');
    const trackingModal = document.getElementById('trackingModal');

    const isBulkModalOpen = bulkTrackingModal && bulkTrackingModal.classList.contains('show');
    const isTrackingModalOpen = trackingModal && trackingModal.classList.contains('show');

    // También verificar si hay pedidos seleccionados para tracking masivo
    const hasSelectedOrders = bulkSelectedOrders.length > 0;

    if (isBulkModalOpen || isTrackingModalOpen || hasSelectedOrders) {
        console.log('[Auto-refresh] Omitido - Modal abierto o pedidos seleccionados');
        return;
    }

    console.log('[Auto-refresh] Ejecutando recarga de pedidos...');
    loadOrders();
}

/**
 * Formatear fecha para input type="date"
 */
function formatDateForInput(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

/**
 * Aplicar filtros y recargar pedidos
 */
function applyFilters() {
    loadOrders();
}

/**
 * Limpiar todos los filtros y recargar pedidos
 * Resetea las fechas a los últimos 30 días
 */
function clearFilters() {
    // Resetear fechas a los últimos 30 días (NO dejarlas vacías)
    const today = new Date();
    const thirtyDaysAgo = new Date(today);
    thirtyDaysAgo.setDate(today.getDate() - 30);

    document.getElementById('filter-date-from').value = formatDateForInput(thirtyDaysAgo);
    document.getElementById('filter-date-to').value = formatDateForInput(today);

    // Desmarcar todos los checkboxes
    document.getElementById('filter-priority').checked = false;
    document.getElementById('filter-atendido').checked = false;
    document.getElementById('filter-no-atendido').checked = false;

    // Recargar pedidos con filtro de últimos 30 días y sin checkboxes
    loadOrders();

    // Feedback visual
    showToast('info', 'Filtros Reseteados', 'Mostrando pedidos del mes actual');
}

/**
 * Cargar pedidos desde el backend
 */
async function loadOrders() {
    try {
        // Construir parámetros de filtro
        const params = new URLSearchParams();

        const dateFrom = document.getElementById('filter-date-from').value;
        const dateTo = document.getElementById('filter-date-to').value;
        const priorityOnly = document.getElementById('filter-priority').checked;
        const atendidoOnly = document.getElementById('filter-atendido').checked;
        const noAtendidoOnly = document.getElementById('filter-no-atendido').checked;

        // Debug: Log de filtros
        console.log('Filtros aplicados:', { dateFrom, dateTo, priorityOnly, atendidoOnly, noAtendidoOnly });

        // Solo aplicar filtro de fechas si AMBAS fechas están presentes
        if (dateFrom && dateTo) {
            params.append('date_from', dateFrom);
            params.append('date_to', dateTo);
            console.log('Filtro de fechas - Params:', params.toString());
        } else {
            console.log('Filtro de fechas NO aplicado - falta una o ambas fechas');
        }

        if (priorityOnly) params.append('priority_only', 'true');
        if (atendidoOnly) params.append('atendido_only', 'true');
        if (noAtendidoOnly) params.append('no_atendido_only', 'true');

        // Fetch data
        const response = await fetch(`/dispatch/api/orders?${params.toString()}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Error desconocido');
        }

        // Renderizar pedidos en el tablero
        renderOrders(data.orders);

        // Actualizar estadísticas
        updateStats(data.stats);

        // Inicializar drag & drop
        initializeDragDrop();

    } catch (error) {
        console.error('Error cargando pedidos:', error);
        showError('Error al cargar pedidos: ' + error.message);
    }
}

/**
 * Renderizar pedidos en las columnas
 */
function renderOrders(ordersByMethod) {
    // Mapeo de métodos a IDs de columnas
    const columnMap = {
        'Por Asignar': 'column-por-asignar',
        'Olva Courier': 'column-olva',
        'Recojo en Almacén': 'column-recojo',
        'Motorizado (CHAMO)': 'column-chamo',
        'SHALOM': 'column-shalom',
        'DINSIDES': 'column-dinsides'
    };

    // Limpiar todas las columnas y resetear lista de IDs visibles
    currentVisibleOrderIds = [];
    Object.values(columnMap).forEach(columnId => {
        const column = document.getElementById(columnId);
        if (column) {
            column.innerHTML = '';
        }
    });

    // Renderizar pedidos en cada columna
    for (const [method, orders] of Object.entries(ordersByMethod)) {
        // Agregar IDs a la lista de visibles
        orders.forEach(order => {
            currentVisibleOrderIds.push(order.id);
        });
        const columnId = columnMap[method];
        if (!columnId) continue;

        const column = document.getElementById(columnId);
        if (!column) continue;

        if (orders.length === 0) {
            column.innerHTML = `
                <div class="text-center text-muted py-5">
                    <i class="bi bi-inbox"></i>
                    <p>Sin pedidos</p>
                </div>
            `;
            continue;
        }

        // Crear tarjetas de pedidos (pasando el método de la columna)
        orders.forEach(order => {
            const card = createOrderCard(order, method);
            column.appendChild(card);
        });

        // Actualizar contador de columna
        const countElement = column.closest('.kanban-column')
            .querySelector('.column-count');
        if (countElement) {
            countElement.textContent = orders.length;
        }
    }
}

/**
 * Crear tarjeta de pedido
 * @param {Object} order - Datos del pedido
 * @param {string} columnMethod - Método de envío de la columna (opcional)
 */
function createOrderCard(order, columnMethod) {
    const card = document.createElement('div');
    card.className = 'order-card';
    card.dataset.orderId = order.id;
    card.dataset.orderNumber = order.number;

    // Clases adicionales según estado
    if (order.is_priority) {
        card.classList.add('priority-' + order.priority_level);
    }
    if (order.is_atendido) {
        card.classList.add('atendido');
    }
    if (order.is_stale) {
        card.classList.add('stale');
    }

    // Determinar si es columna con selección masiva (CHAMO o DINSIDES)
    const isBulkColumn = columnMethod === 'Motorizado (CHAMO)' || columnMethod === 'DINSIDES';
    const columnKey = columnMethod === 'Motorizado (CHAMO)' ? 'chamo' :
        columnMethod === 'DINSIDES' ? 'dinsides' : null;

    // Construir HTML de la tarjeta
    let html = `
        <div class="card-header">
            <div class="order-number">
                ${isBulkColumn ? `
                    <input type="checkbox" class="form-check-input bulk-order-checkbox me-1"
                           data-order-id="${order.id}"
                           data-order-number="${order.number}"
                           data-column="${columnKey}"
                           onchange="onOrderCheckboxChange(this)">
                ` : ''}
                ${order.number}
                ${order.whatsapp_number ? `<span style="color: #999; font-size: 0.85em; margin-left: 4px;">${order.whatsapp_number}</span>` : ''}
            </div>
            <div class="order-badges">
    `;

    // Badge de prioridad
    if (order.is_priority) {
        const priorityIcon = order.priority_level === 'urgent' ? 'exclamation-triangle-fill' : 'star-fill';
        const priorityColor = order.priority_level === 'urgent' ? 'danger' : 'warning';
        html += `<span class="badge bg-${priorityColor}"><i class="bi bi-${priorityIcon}"></i></span>`;
    }

    // Badge de tiempo sin actividad
    if (order.hours_since_update >= 24) {
        // Calcular días y horas
        const days = Math.floor(order.hours_since_update / 24);
        const hours = order.hours_since_update % 24;

        // Badge de días
        html += `<span class="badge bg-danger" title="${order.hours_since_update}h sin mover">
            <i class="bi bi-calendar-x"></i> ${days}d
        </span>`;

        // Badge de horas (si hay horas restantes)
        if (hours > 0) {
            html += `<span class="badge bg-warning ms-1" title="${hours}h adicionales">
                <i class="bi bi-clock-history"></i> ${hours}h
            </span>`;
        }
    } else if (order.hours_since_update > 0) {
        // Solo mostrar horas si es menos de 24 horas
        html += `<span class="badge bg-info" title="${order.hours_since_update}h sin mover">
            <i class="bi bi-clock-history"></i> ${order.hours_since_update}h
        </span>`;
    }

    // Badge de pago contraentrega (COD)
    if (order.is_cod) {
        html += `<span class="badge cod-badge ms-1" title="Pago Contraentrega">
            <i class="bi bi-cash-coin"></i> COD
        </span>`;
    }

    html += `
            </div>
        </div>
        <div class="card-body">
            <div class="customer-name">${order.customer_name}</div>
            <div class="order-total">S/ ${order.total.toFixed(2)}</div>
            <div class="order-date">${order.date_created}</div>
            <div class="shipping-method mt-2">
                <i class="bi bi-truck"></i>
                <small class="text-muted">${order.shipping_method || 'Sin método'}</small>
            </div>
    `;

    // Mostrar distrito para pedidos de "1 día hábil" y "Olva Courier"
    const mostrarDistrito = order.shipping_method && order.shipping_district && (
        order.shipping_method.toLowerCase().includes('1 día') ||
        order.shipping_method.toLowerCase().includes('olva')
    );

    if (mostrarDistrito) {
        html += `
            <div class="shipping-district mt-1">
                <i class="bi bi-geo-alt-fill"></i>
                <small class="text-primary fw-bold">${order.shipping_district}</small>
            </div>
        `;
    }

    html += `
        </div>
        <div class="card-footer">
            <button class="btn btn-outline-primary btn-icon btn-detail" data-order-id="${order.id}" onclick="showOrderDetail(${order.id})" title="Ver Detalle">
                <i class="bi bi-eye"></i>
            </button>
            <button class="btn ${order.is_atendido ? 'btn-success' : 'btn-outline-success'} btn-icon btn-atendido" 
                    onclick="toggleAtendido(${order.id}, ${order.is_atendido})" 
                    title="${order.is_atendido ? 'Marcar como Pendiente' : 'Marcar como Atendido/Empaquetado'}">
                <i class="bi bi-check-circle${order.is_atendido ? '-fill' : ''}"></i>
            </button>
            <a href="https://www.izistoreperu.com/wp-admin/post.php?post=${order.id}&action=edit" target="_blank" class="btn btn-outline-secondary btn-icon" title="Ver en WooCommerce">
                <i class="bi bi-wordpress"></i>
            </a>
            <button class="btn btn-outline-success btn-icon" onclick="showTrackingModal(${order.id}, '${order.number}')" title="Agregar Tracking">
                <i class="bi bi-truck"></i>
            </button>
        </div>
    `;

    card.innerHTML = html;

    return card;
}

/**
 * Actualizar estadísticas en el header
 */
function updateStats(stats) {
    document.getElementById('stat-total').textContent = stats.total || 0;
    document.getElementById('stat-priority').textContent = stats.priority || 0;
    document.getElementById('stat-atendido').textContent = stats.atendido || 0;
    document.getElementById('stat-stale').textContent = stats.stale || 0;
}

/**
 * Inicializar drag & drop con SortableJS
 */
function initializeDragDrop() {
    // Destruir instancias anteriores
    sortableInstances.forEach(instance => instance.destroy());
    sortableInstances = [];

    // Columnas donde se puede hacer drag & drop
    const columns = document.querySelectorAll('.column-cards');

    columns.forEach(column => {
        const sortable = new Sortable(column, {
            group: 'orders', // Permite mover entre columnas
            animation: 150,
            ghostClass: 'sortable-ghost',
            dragClass: 'sortable-drag',
            handle: '.order-card', // Toda la tarjeta es arrastrable

            onEnd: function (evt) {
                // Obtener información del movimiento
                const orderId = evt.item.dataset.orderId;
                const orderNumber = evt.item.dataset.orderNumber;
                const newColumn = evt.to;
                const newMethod = newColumn.dataset.method;
                const oldColumn = evt.from;
                const oldMethod = oldColumn.dataset.method;

                // Si cambió de columna, actualizar en backend
                if (newMethod !== oldMethod) {
                    moveOrder(orderId, orderNumber, newMethod, oldMethod, evt);
                }
            }
        });

        sortableInstances.push(sortable);
    });
}

/**
 * Mover pedido a otra columna (cambiar método de envío)
 */
async function moveOrder(orderId, orderNumber, newMethod, oldMethod, evt) {
    // Mostrar loading overlay
    showLoadingOverlay();

    try {
        const response = await fetch('/dispatch/api/move', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                order_id: parseInt(orderId),
                new_shipping_method: newMethod
            })
        });

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Error al mover pedido');
        }

        // Ocultar loading overlay
        hideLoadingOverlay();

        // Mostrar notificación de éxito con toast
        showToast('success', 'Pedido Movido', `Pedido ${orderNumber} movido a ${newMethod}`);

        // Actualizar el data-column del checkbox de la tarjeta movida
        updateCardCheckboxColumn(evt.item, newMethod);

        // Actualizar contadores
        updateColumnCounts();

    } catch (error) {
        console.error('Error moviendo pedido:', error);

        // Ocultar loading overlay
        hideLoadingOverlay();

        // Mostrar toast de error
        showToast('danger', 'Error', 'Error al mover pedido: ' + error.message);

        // Revertir movimiento visual
        if (evt.from && evt.item) {
            evt.from.insertBefore(evt.item, evt.from.children[evt.oldIndex]);
        }

        // Actualizar contadores después de revertir
        updateColumnCounts();
    }
}

/**
 * Actualizar contadores de columnas
 */
function updateColumnCounts() {
    document.querySelectorAll('.kanban-column').forEach(column => {
        const cards = column.querySelectorAll('.order-card');
        const count = column.querySelector('.column-count');
        if (count) {
            count.textContent = cards.length;
        }
    });
}

/**
 * Mostrar detalle de pedido en modal
 */
async function showOrderDetail(orderId) {
    currentOrderId = orderId;

    // Obtener botón usando data-order-id y activar estado de carga
    const btn = document.querySelector(`.btn-detail[data-order-id="${orderId}"]`);
    const originalContent = btn ? btn.innerHTML : '';

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
        btn.classList.add('loading');
    }

    try {
        // Obtener datos completos del pedido desde el backend
        const response = await fetch(`/dispatch/api/order/${orderId}`);
        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Error al obtener detalles del pedido');
        }

        const order = data.order;

        // Llenar modal con datos del pedido
        // Formato del título: mostrar siempre #ID de WooCommerce primero
        // Si es pedido WhatsApp, agregar (W-XXXXX) como indicador de origen
        const isWhatsAppOrder = order.number && order.number.startsWith('W-');
        const mainOrderNumber = `#${order.id}`;

        document.getElementById('modal-order-number').textContent = mainOrderNumber;

        const whatsappIndicator = document.getElementById('modal-whatsapp-indicator');
        if (isWhatsAppOrder) {
            // Pedido de WhatsApp: mostrar "(W-00414)" como indicador
            whatsappIndicator.textContent = `(${order.number})`;
        } else {
            // Pedido normal: no mostrar indicador
            whatsappIndicator.textContent = '';
        }
        document.getElementById('modal-customer-name').textContent = order.customer_name;
        document.getElementById('modal-customer-phone').textContent = order.customer_phone;
        document.getElementById('modal-customer-dni').textContent = order.customer_dni || '-';
        document.getElementById('modal-customer-email').textContent = order.email;
        document.getElementById('modal-total').textContent = order.total.toFixed(2);
        document.getElementById('modal-date-created').textContent = order.date_created;
        document.getElementById('modal-status').textContent = order.status;
        document.getElementById('modal-shipping-method').textContent = order.shipping_method;
        document.getElementById('modal-created-by').textContent = order.created_by;

        // Dirección de envío
        document.getElementById('modal-shipping-address').textContent = order.shipping_address || '-';
        document.getElementById('modal-shipping-district').textContent = order.shipping_district || '-';
        document.getElementById('modal-shipping-department').textContent = order.shipping_department || '-';

        // Notas del cliente - prellenar en el textarea de notas de despacho
        const dispatchNoteInput = document.getElementById('dispatch-note-input');
        if (dispatchNoteInput) {
            // Si hay notas del cliente, mostrarlas como prefijo editable
            if (order.customer_note) {
                dispatchNoteInput.value = `[Nota del cliente]: ${order.customer_note}`;
                dispatchNoteInput.placeholder = 'Notas del cliente cargadas. Puedes editar o agregar más información...';
            } else {
                dispatchNoteInput.value = '';
                dispatchNoteInput.placeholder = 'Escribir nota sobre el despacho...';
            }
        }

        // Renderizar lista de productos con imágenes y atributos
        const productsHtml = order.products.length > 0
            ? `<ul class="list-group list-group-flush">
                ${order.products.map(product => `
                    <li class="list-group-item">
                        <div class="d-flex gap-3">
                            <div>
                                <span class="badge bg-primary rounded-pill">x${product.quantity}</span>
                            </div>
                            ${product.image
                    ? `<img src="${product.image}" alt="${product.name}" class="product-thumbnail" style="width: 60px; height: 60px; object-fit: cover; border-radius: 4px;">`
                    : `<div class="product-thumbnail-placeholder" style="width: 60px; height: 60px; background: #e9ecef; border-radius: 4px; display: flex; align-items: center; justify-content: center;">
                                    <i class="bi bi-image" style="font-size: 24px; color: #adb5bd;"></i>
                                   </div>`
                }
                            <div class="flex-grow-1">
                                ${product.sku ? `<div class="text-muted small mb-1">SKU: ${product.sku}</div>` : ''}
                                <div class="fw-bold">${product.name}</div>
                                ${product.attributes ? `<div class="text-muted small">${product.attributes}</div>` : ''}
                            </div>
                        </div>
                    </li>
                `).join('')}
               </ul>`
            : '<p class="text-muted">Sin productos</p>';

        // Actualizar sección de productos
        const productsSection = document.getElementById('products-section');
        if (productsSection) {
            productsSection.innerHTML = `
                <h6 class="border-bottom pb-2">Productos</h6>
                ${productsHtml}
            `;
        }

        // Mostrar/ocultar alerta de contraentrega (COD)
        const codAlertSection = document.getElementById('cod-alert-section');
        if (codAlertSection) {
            if (order.is_cod) {
                // Calcular monto COD: Total - Costo de envío (ya pagado)
                const shippingCost = order.shipping_cost || 0;
                const codAmount = order.total - shippingCost;

                document.getElementById('modal-cod-amount').textContent = codAmount.toFixed(2);
                codAlertSection.style.display = 'block';
            } else {
                codAlertSection.style.display = 'none';
            }
        }

        // Obtener estado actual del pedido desde la tarjeta en el DOM
        const card = document.querySelector(`[data-order-id="${orderId}"]`);
        const isPriority = card && (card.classList.contains('priority-high') || card.classList.contains('priority-urgent'));
        const isAtendido = card && card.classList.contains('atendido');

        // Botón de Prioridad
        document.getElementById('priority-btn-text').textContent =
            isPriority ? 'Quitar Prioridad' : 'Marcar Prioritario';

        // Botón de Atendido
        document.getElementById('atendido-btn-text').textContent =
            isAtendido ? 'Marcar como Pendiente' : 'Marcar como Atendido/Empaquetado';

        const atendidoBtn = document.getElementById('btn-atendido-modal');
        if (atendidoBtn) {
            atendidoBtn.className = isAtendido ? 'btn btn-success btn-sm' : 'btn btn-outline-success btn-sm';
            atendidoBtn.onclick = () => toggleAtendido(orderId, isAtendido);
        }

        // Actualizar indicador de columna
        updateColumnIndicator(orderId);

        // Cargar historial
        loadOrderHistory(orderId);

        // Actualizar botones de navegación
        updateNavigationButtons();

        // Obtener o crear instancia del modal (reutilizar si ya existe)
        const modalElement = document.getElementById('orderDetailModal');
        if (!orderDetailModalInstance) {
            orderDetailModalInstance = new bootstrap.Modal(modalElement);
        }

        // Mostrar modal solo si no está visible
        if (!modalElement.classList.contains('show')) {
            orderDetailModalInstance.show();
        }

        // Restaurar botón después de mostrar el modal
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalContent;
            btn.classList.remove('loading');
        }

    } catch (error) {
        console.error('Error cargando detalle de pedido:', error);
        showError('Error al cargar detalles del pedido: ' + error.message);

        // Restaurar botón en caso de error
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalContent;
            btn.classList.remove('loading');
        }
    }
}

/**
 * Cargar historial de cambios del pedido
 */
async function loadOrderHistory(orderId) {
    const historyContainer = document.getElementById('order-history');
    historyContainer.innerHTML = '<div class="text-center"><i class="bi bi-hourglass-split"></i> Cargando...</div>';

    try {
        const response = await fetch(`/dispatch/api/history/${orderId}`);
        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Error al cargar historial');
        }

        if (data.history.length === 0) {
            historyContainer.innerHTML = '<p class="text-muted">Sin cambios registrados</p>';
            return;
        }

        // Renderizar timeline
        let html = '<div class="timeline">';
        data.history.forEach(entry => {
            const icon = entry.dispatch_note ? 'chat-left-text' : 'arrow-left-right';
            html += `
                <div class="timeline-item">
                    <div class="timeline-marker">
                        <i class="bi bi-${icon}"></i>
                    </div>
                    <div class="timeline-content">
                        <div class="timeline-date">${entry.changed_at}</div>
                        <div class="timeline-user">por ${entry.changed_by}</div>
            `;

            if (entry.previous_shipping_method) {
                html += `
                    <div class="timeline-change">
                        ${entry.previous_shipping_method}
                        <i class="bi bi-arrow-right"></i>
                        ${entry.new_shipping_method}
                    </div>
                `;
            }

            if (entry.dispatch_note) {
                html += `<div class="timeline-note">${entry.dispatch_note}</div>`;
            }

            html += '</div></div>';
        });
        html += '</div>';

        historyContainer.innerHTML = html;

    } catch (error) {
        console.error('Error cargando historial:', error);
        historyContainer.innerHTML = '<p class="text-danger">Error al cargar historial</p>';
    }
}

/**
 * Toggle prioridad del pedido
 */
async function togglePriority() {
    if (!currentOrderId) return;

    const card = document.querySelector(`[data-order-id="${currentOrderId}"]`);
    const isPriority = card.classList.contains('priority-high') || card.classList.contains('priority-urgent');

    try {
        const response = await fetch('/dispatch/api/priority', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                order_id: parseInt(currentOrderId),
                is_priority: !isPriority,
                priority_level: isPriority ? 'normal' : 'high',
                note: ''
            })
        });

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Error al cambiar prioridad');
        }

        // Recargar pedidos para reflejar cambio
        loadOrders();

        // Cerrar modal
        bootstrap.Modal.getInstance(document.getElementById('orderDetailModal')).hide();

        showSuccess(data.message);

    } catch (error) {
        console.error('Error cambiando prioridad:', error);
        showError('Error al cambiar prioridad: ' + error.message);
    }
}

/**
 * Toggle estado Atendido/Empaquetado del pedido
 */
async function toggleAtendido(orderId, currentStatus) {
    // Encontrar el botón que activó la acción (puede estar en tarjeta o modal)
    const cardBtn = document.querySelector(`.order-card[data-order-id="${orderId}"] .btn-atendido`);
    const modalBtn = document.getElementById('btn-atendido-modal');
    const modalBtnText = document.getElementById('atendido-btn-text');

    // Guardar contenido original y aplicar estado de carga
    let cardBtnOriginalHtml, modalBtnOriginalHtml;

    if (cardBtn) {
        cardBtnOriginalHtml = cardBtn.innerHTML;
        cardBtn.disabled = true;
        cardBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
    }

    if (modalBtn) {
        modalBtnOriginalHtml = modalBtnText ? modalBtnText.textContent : '';
        modalBtn.disabled = true;
        if (modalBtnText) {
            modalBtnText.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Procesando...';
        }
    }

    try {
        const response = await fetch('/dispatch/api/atendido', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                order_id: parseInt(orderId),
                is_atendido: !currentStatus
            })
        });

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Error al cambiar estado');
        }

        // Recargar pedidos para reflejar cambio
        loadOrders();

        // Si el modal está abierto, actualizarlo
        const modalElement = document.getElementById('orderDetailModal');
        if (modalElement && modalElement.classList.contains('show')) {
            const atendidoBtn = document.getElementById('btn-atendido-modal');
            const btnText = document.getElementById('atendido-btn-text');
            const isNowAtendido = !currentStatus;

            if (atendidoBtn) {
                atendidoBtn.className = isNowAtendido ? 'btn btn-success btn-sm' : 'btn btn-outline-success btn-sm';
                atendidoBtn.disabled = false;
                atendidoBtn.onclick = () => toggleAtendido(orderId, isNowAtendido);
            }
            if (btnText) {
                btnText.textContent = isNowAtendido ? 'Marcar como Pendiente' : 'Marcar como Atendido/Empaquetado';
            }
        }

        showToast('success', 'Pedido Actualizado', data.message);

    } catch (error) {
        console.error('Error cambiando estado atendido:', error);
        showToast('danger', 'Error', 'Error al cambiar estado: ' + error.message);

        // Restaurar estado original en caso de error
        if (cardBtn && cardBtnOriginalHtml) {
            cardBtn.disabled = false;
            cardBtn.innerHTML = cardBtnOriginalHtml;
        }

        if (modalBtn && modalBtnOriginalHtml) {
            modalBtn.disabled = false;
            if (modalBtnText) {
                modalBtnText.textContent = modalBtnOriginalHtml;
            }
        }
    }
}

/**
 * Agregar nota de despacho
 */
async function addDispatchNote() {
    if (!currentOrderId) return;

    const noteInput = document.getElementById('dispatch-note-input');
    const note = noteInput.value.trim();

    if (!note) {
        showError('Por favor escribe una nota');
        return;
    }

    try {
        const response = await fetch('/dispatch/api/note', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                order_id: parseInt(currentOrderId),
                note: note
            })
        });

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Error al guardar nota');
        }

        // Limpiar input
        noteInput.value = '';

        // Recargar historial
        loadOrderHistory(currentOrderId);

        showSuccess('Nota guardada exitosamente');

    } catch (error) {
        console.error('Error guardando nota:', error);
        showError('Error al guardar nota: ' + error.message);
    }
}

/**
 * Mostrar notificación global
 * @param {string} type - 'success', 'danger', 'warning', 'info'
 * @param {string} title - Título del toast
 * @param {string} message - Mensaje del toast
 */
function showToast(type, title, message) {
    // Usar la función global centralizada en base.html
    if (typeof showNotification === 'function') {
        showNotification(type, `${title}: ${message}`);
    } else {
        console.log(`Notification (${type}): ${title} - ${message}`);
    }
}

/**
 * Mostrar loading overlay durante drag & drop
 */
function showLoadingOverlay() {
    const overlay = document.getElementById('drag-loading-overlay');
    if (overlay) {
        overlay.style.display = 'flex';
    }
}

/**
 * Ocultar loading overlay
 */
function hideLoadingOverlay() {
    const overlay = document.getElementById('drag-loading-overlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

/**
 * Mostrar notificación de éxito (compatibilidad con código existente)
 */
function showSuccess(message) {
    showToast('success', 'Éxito', message);
}

/**
 * Mostrar notificación de error (compatibilidad con código existente)
 */
function showError(message) {
    showToast('danger', 'Error', message);
}

/**
 * Mostrar modal de agregar tracking
 */
async function showTrackingModal(orderId, orderNumber) {
    currentOrderId = orderId;

    // Actualizar título del modal
    document.getElementById('trackingModalLabel').textContent = `Agregar Tracking - ${orderNumber}`;

    // Resetear formulario
    document.getElementById('tracking-form').reset();

    // Establecer fecha actual por defecto
    const today = new Date();
    const dateString = today.toISOString().split('T')[0];
    document.getElementById('tracking-date-shipped').value = dateString;

    // Ocultar campo de mensaje por defecto
    document.getElementById('tracking-message-container').style.display = 'none';

    // Obtener datos del pedido para detectar COD
    try {
        const response = await fetch(`/dispatch/api/order/${orderId}`);
        const data = await response.json();

        if (data.success) {
            // Guardar datos del pedido para usarlos en handleProviderChange
            currentOrderData = data.order;
        }
    } catch (error) {
        console.error('Error obteniendo datos del pedido:', error);
        currentOrderData = null;
    }

    // Mostrar modal
    const modal = new bootstrap.Modal(document.getElementById('trackingModal'));
    modal.show();
}

/**
 * Generar mensaje de tracking para pedido individual
 * @param {string} provider - Proveedor de envío
 * @param {string} dateStr - Fecha de envío (yyyy-mm-dd)
 * @param {object} orderData - Datos del pedido
 */
function generateIndividualTrackingMessage(provider, dateStr, orderData) {
    if (!orderData) return '';

    // Solo generar mensaje para CHAMO y DINSIDES
    let column = null;
    if (provider === 'Motorizado Izi') {
        column = 'chamo';
    } else if (provider === 'Dinsides Courier') {
        column = 'dinsides';
    }

    if (!column) return '';

    // Usar la misma lógica que el tracking masivo
    return generateBulkTrackingMessage(column, dateStr, orderData);
}

/**
 * Manejar cambio en el selector de proveedor de envío
 * Si se selecciona "Recojo en Almacén", deshabilitar tracking number
 * Si se selecciona CHAMO o DINSIDES, mostrar mensaje personalizado
 */
function handleProviderChange() {
    const providerSelect = document.getElementById('tracking-provider');
    const trackingNumberInput = document.getElementById('tracking-number');
    const messageContainer = document.getElementById('tracking-message-container');
    const messageTextarea = document.getElementById('tracking-message');
    const codBadge = document.getElementById('tracking-cod-badge');
    const codInfo = document.getElementById('tracking-cod-info');
    const trackingNumberRequired = document.getElementById('tracking-number-required');
    const trackingNumberHelp = document.getElementById('tracking-number-help');

    const provider = providerSelect.value;

    // Manejar "Recojo en Almacén"
    if (provider === 'Recojo en Almacén') {
        trackingNumberInput.value = 'RECOJO';
        trackingNumberInput.disabled = true;
        trackingNumberInput.required = false;
        trackingNumberRequired.textContent = '';
        trackingNumberHelp.textContent = 'Se generará automáticamente';
        messageContainer.style.display = 'none';
        return;
    }

    // Habilitar tracking number por defecto
    trackingNumberInput.value = '';
    trackingNumberInput.disabled = false;
    trackingNumberInput.required = true;
    trackingNumberRequired.textContent = '*';
    trackingNumberHelp.textContent = 'Ingrese el código de seguimiento del envío';

    // Mostrar mensaje solo para CHAMO y DINSIDES
    if (provider === 'Motorizado Izi' || provider === 'Dinsides Courier') {
        messageContainer.style.display = 'block';

        // Obtener fecha de envío
        const dateShipped = document.getElementById('tracking-date-shipped').value;

        // Generar mensaje
        const message = generateIndividualTrackingMessage(provider, dateShipped, currentOrderData);
        messageTextarea.value = message;

        // Si es COD, hacer tracking_number OPCIONAL (porque se usará el mensaje)
        const isCOD = currentOrderData && currentOrderData.is_cod;
        if (isCOD) {
            trackingNumberInput.required = false;
            trackingNumberInput.placeholder = 'Opcional - Se usará el mensaje personalizado COD';
            trackingNumberRequired.textContent = '';
            trackingNumberHelp.innerHTML = '<span class="text-info">✓ Opcional para pedidos COD - Se usará el mensaje personalizado</span>';
            codBadge.style.display = 'inline-block';
            codInfo.style.display = 'inline';
        } else {
            trackingNumberInput.required = true;
            trackingNumberInput.placeholder = 'Ej: IZI26010841608660';
            trackingNumberRequired.textContent = '*';
            trackingNumberHelp.textContent = 'Ingrese el código de seguimiento del envío';
            codBadge.style.display = 'none';
            codInfo.style.display = 'none';
        }
    } else {
        messageContainer.style.display = 'none';
        trackingNumberInput.placeholder = 'Ej: IZI26010841608660';
    }
}

/**
 * Guardar información de tracking
 */
async function saveTracking() {
    const trackingNumber = document.getElementById('tracking-number').value.trim();
    const shippingProvider = document.getElementById('tracking-provider').value;
    const dateShipped = document.getElementById('tracking-date-shipped').value;
    const markAsShipped = document.getElementById('tracking-mark-shipped').checked;

    // Obtener mensaje personalizado si aplica (CHAMO o DINSIDES)
    let trackingMessage = null;
    if (shippingProvider === 'Motorizado Izi' || shippingProvider === 'Dinsides Courier') {
        trackingMessage = document.getElementById('tracking-message').value.trim();
    }

    // Validar campos
    // Tracking number es opcional si:
    // 1. Es "Recojo en Almacén", O
    // 2. Es CHAMO/DINSIDES con mensaje personalizado (COD)
    const hasTrackingMessage = trackingMessage && trackingMessage.length > 0;
    if (!trackingNumber && shippingProvider !== 'Recojo en Almacén' && !hasTrackingMessage) {
        showError('Por favor ingrese el número de tracking');
        return;
    }

    if (!shippingProvider) {
        showError('Por favor seleccione el proveedor de envío');
        return;
    }

    // Mostrar loading en el botón
    const saveBtn = document.getElementById('btn-save-tracking');
    const originalText = saveBtn.innerHTML;
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Guardando...';

    try {
        const requestBody = {
            order_id: currentOrderId,
            tracking_number: trackingNumber,
            shipping_provider: shippingProvider,
            date_shipped: dateShipped,
            mark_as_shipped: markAsShipped
        };

        // Agregar mensaje solo si existe (CHAMO o DINSIDES)
        if (trackingMessage) {
            requestBody.tracking_message = trackingMessage;
        }

        const response = await fetch('/dispatch/api/add-tracking', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Error al guardar tracking');
        }

        // Cerrar modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('trackingModal'));
        modal.hide();

        // Mostrar mensaje de éxito
        let successMsg = `Tracking agregado exitosamente al pedido ${data.order_number}`;
        if (data.status_changed) {
            successMsg += ' y estado cambiado a "Enviado"';
        }
        showSuccess(successMsg);

        // Recargar pedidos para reflejar cambios
        await loadOrders();

    } catch (error) {
        console.error('Error guardando tracking:', error);
        showError('Error al guardar tracking: ' + error.message);
    } finally {
        // Restaurar botón
        saveBtn.disabled = false;
        saveBtn.innerHTML = originalText;
    }
}

/**
 * Navegar entre pedidos (siguiente/anterior)
 */
function navigateOrder(direction) {
    if (!currentOrderId || currentVisibleOrderIds.length === 0) {
        return;
    }

    const currentIndex = currentVisibleOrderIds.indexOf(currentOrderId);
    if (currentIndex === -1) {
        return;
    }

    // Obtener ambos botones
    const btnPrev = document.getElementById('btn-prev-order');
    const btnNext = document.getElementById('btn-next-order');
    const btn = direction === 'next' ? btnNext : btnPrev;

    if (!btn || btn.disabled) {
        return;
    }

    // Guardar contenido original y mostrar loading en ambos botones
    const originalContentPrev = btnPrev.innerHTML;
    const originalContentNext = btnNext.innerHTML;

    btnPrev.disabled = true;
    btnNext.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';

    let newIndex;
    if (direction === 'next') {
        newIndex = currentIndex + 1;
        if (newIndex >= currentVisibleOrderIds.length) {
            newIndex = 0; // Volver al inicio
        }
    } else { // 'prev'
        newIndex = currentIndex - 1;
        if (newIndex < 0) {
            newIndex = currentVisibleOrderIds.length - 1; // Ir al último
        }
    }

    const newOrderId = currentVisibleOrderIds[newIndex];

    // Llamar a showOrderDetail y restaurar botones después
    showOrderDetail(newOrderId).then(() => {
        // Restaurar ambos botones
        btnPrev.innerHTML = originalContentPrev;
        btnNext.innerHTML = originalContentNext;
        btnPrev.disabled = false;
        btnNext.disabled = false;
    }).catch((error) => {
        // En caso de error, también restaurar botones
        btnPrev.innerHTML = originalContentPrev;
        btnNext.innerHTML = originalContentNext;
        btnPrev.disabled = false;
        btnNext.disabled = false;
        console.error('Error navegando a orden:', error);
    });
}

/**
 * Actualizar indicador de columna en el modal
 */
function updateColumnIndicator(orderId) {
    const columnNameElement = document.getElementById('modal-column-name');
    const columnIndicator = document.getElementById('modal-column-indicator');

    if (!columnNameElement || !columnIndicator) return;

    // Buscar la tarjeta del pedido en el DOM para obtener su columna
    const card = document.querySelector(`.order-card[data-order-id="${orderId}"]`);

    if (card) {
        // Encontrar la columna padre
        const column = card.closest('.column-cards');
        if (column) {
            // Obtener el título de la columna desde el header
            const columnHeader = column.closest('.kanban-column').querySelector('.column-title');
            if (columnHeader) {
                const columnName = columnHeader.textContent.trim();
                columnNameElement.textContent = columnName;

                // Cambiar color del badge según la columna (tamaño grande y prominente)
                columnIndicator.className = 'badge';
                columnIndicator.style.fontSize = '1.1rem';
                columnIndicator.style.fontWeight = '600';
                columnIndicator.style.padding = '0.6rem 1.2rem';
                columnIndicator.style.borderRadius = '8px';

                // Asignar color según columna
                if (columnName.includes('Por Asignar')) {
                    columnIndicator.classList.add('bg-secondary');
                } else if (columnName.includes('Olva')) {
                    columnIndicator.classList.add('bg-info');
                } else if (columnName.includes('Recojo')) {
                    columnIndicator.classList.add('bg-success');
                } else if (columnName.includes('CHAMO')) {
                    columnIndicator.classList.add('bg-warning', 'text-dark');
                } else if (columnName.includes('SHALOM')) {
                    columnIndicator.classList.add('bg-danger');
                } else if (columnName.includes('DINSIDES')) {
                    columnIndicator.classList.add('bg-primary');
                } else {
                    columnIndicator.classList.add('bg-secondary');
                }
            }
        }
    } else {
        // Si no se encuentra la tarjeta, mostrar "Desconocido"
        columnNameElement.textContent = 'Desconocido';
        columnIndicator.className = 'badge bg-secondary';
    }
}

/**
 * Actualizar estado de botones de navegación
 */
function updateNavigationButtons() {
    const btnPrev = document.getElementById('btn-prev-order');
    const btnNext = document.getElementById('btn-next-order');

    if (!btnPrev || !btnNext) return;

    const currentIndex = currentVisibleOrderIds.indexOf(currentOrderId);
    const totalOrders = currentVisibleOrderIds.length;

    // Siempre habilitados (circular)
    btnPrev.disabled = totalOrders <= 1;
    btnNext.disabled = totalOrders <= 1;

    // Actualizar tooltips con información
    if (totalOrders > 1) {
        btnPrev.title = `Pedido anterior (${currentIndex + 1}/${totalOrders})`;
        btnNext.title = `Pedido siguiente (${currentIndex + 1}/${totalOrders})`;
    } else {
        btnPrev.title = 'No hay más pedidos';
        btnNext.title = 'No hay más pedidos';
    }
}

// ============================================
// FUNCIONES DE SELECCIÓN MASIVA CHAMO/DINSIDES
// ============================================

/**
 * Actualizar el checkbox de una tarjeta después de moverla a otra columna.
 * Agrega/elimina checkbox según si la nueva columna es CHAMO/DINSIDES o no.
 * @param {HTMLElement} cardElement - El elemento de la tarjeta movida
 * @param {string} newMethod - El nuevo método de envío de la columna destino
 */
function updateCardCheckboxColumn(cardElement, newMethod) {
    const isBulkColumn = newMethod === 'Motorizado (CHAMO)' || newMethod === 'DINSIDES';
    const newColumnKey = newMethod === 'Motorizado (CHAMO)' ? 'chamo' :
        newMethod === 'DINSIDES' ? 'dinsides' : null;

    const existingCheckbox = cardElement.querySelector('.bulk-order-checkbox');
    const orderNumberDiv = cardElement.querySelector('.order-number');

    if (isBulkColumn) {
        // La tarjeta va a una columna con selección masiva
        if (existingCheckbox) {
            // Ya tiene checkbox, solo actualizar data-column
            existingCheckbox.dataset.column = newColumnKey;
            existingCheckbox.checked = false;
            existingCheckbox.disabled = false;
        } else {
            // No tiene checkbox, crear uno nuevo
            const orderId = cardElement.dataset.orderId;
            const orderNumber = cardElement.dataset.orderNumber;
            const newCheckbox = document.createElement('input');
            newCheckbox.type = 'checkbox';
            newCheckbox.className = 'form-check-input bulk-order-checkbox me-1';
            newCheckbox.dataset.orderId = orderId;
            newCheckbox.dataset.orderNumber = orderNumber;
            newCheckbox.dataset.column = newColumnKey;
            newCheckbox.onchange = function () { onOrderCheckboxChange(this); };
            orderNumberDiv.insertBefore(newCheckbox, orderNumberDiv.firstChild);
        }
    } else {
        // La tarjeta va a una columna sin selección masiva
        if (existingCheckbox) {
            // Remover el checkbox
            existingCheckbox.remove();
        }
    }

    // Limpiar selección si había algo seleccionado (para evitar estados inconsistentes)
    clearBulkSelection();
}

/**
 * Toggle seleccionar todos de una columna
 */
function toggleSelectAllColumn(column) {
    const selectAllCheckbox = document.getElementById(`select-all-${column}`);
    const isChecked = selectAllCheckbox.checked;

    // Si se está seleccionando y hay otra columna activa, deshabilitarla
    if (isChecked && bulkSelectedColumn && bulkSelectedColumn !== column) {
        clearBulkSelection();
    }

    // Seleccionar/deseleccionar todos los checkboxes de la columna
    const checkboxes = document.querySelectorAll(`.bulk-order-checkbox[data-column="${column}"]`);
    checkboxes.forEach(cb => {
        cb.checked = isChecked;
    });

    // Actualizar estado
    updateBulkSelection();
}

/**
 * Cuando cambia un checkbox individual
 */
function onOrderCheckboxChange(checkbox) {
    const column = checkbox.dataset.column;

    // Si se está seleccionando y hay otra columna activa, deshabilitarla
    if (checkbox.checked && bulkSelectedColumn && bulkSelectedColumn !== column) {
        clearBulkSelection();
        checkbox.checked = true; // Re-marcar este
    }

    updateBulkSelection();
}

/**
 * Actualizar estado de selección masiva
 */
function updateBulkSelection() {
    // Recolectar pedidos seleccionados
    bulkSelectedOrders = [];
    bulkSelectedColumn = null;

    const checkedBoxes = document.querySelectorAll('.bulk-order-checkbox:checked');

    checkedBoxes.forEach(cb => {
        bulkSelectedOrders.push({
            orderId: parseInt(cb.dataset.orderId),
            orderNumber: cb.dataset.orderNumber
        });
        bulkSelectedColumn = cb.dataset.column;
    });

    // Actualizar UI
    const actionBar = document.getElementById('bulk-action-bar');
    const countSpan = document.getElementById('bulk-selected-count');
    const columnSpan = document.getElementById('bulk-selected-column');

    if (bulkSelectedOrders.length > 0) {
        actionBar.style.display = 'block';
        countSpan.textContent = bulkSelectedOrders.length;
        columnSpan.textContent = bulkSelectedColumn === 'chamo' ? 'CHAMO' : 'DINSIDES';

        // Deshabilitar checkboxes de la otra columna
        const otherColumn = bulkSelectedColumn === 'chamo' ? 'dinsides' : 'chamo';
        document.querySelectorAll(`.bulk-order-checkbox[data-column="${otherColumn}"]`).forEach(cb => {
            cb.disabled = true;
        });
        const otherSelectAll = document.getElementById(`select-all-${otherColumn}`);
        if (otherSelectAll) {
            otherSelectAll.disabled = true;
        }
    } else {
        actionBar.style.display = 'none';

        // Habilitar todos los checkboxes
        document.querySelectorAll('.bulk-order-checkbox').forEach(cb => {
            cb.disabled = false;
        });
        document.querySelectorAll('.bulk-select-all').forEach(cb => {
            cb.disabled = false;
        });
    }

    // Actualizar estado del checkbox "seleccionar todos"
    ['chamo', 'dinsides'].forEach(col => {
        const allCheckbox = document.getElementById(`select-all-${col}`);
        if (!allCheckbox) return;

        const columnCheckboxes = document.querySelectorAll(`.bulk-order-checkbox[data-column="${col}"]`);
        const checkedCount = document.querySelectorAll(`.bulk-order-checkbox[data-column="${col}"]:checked`).length;

        if (columnCheckboxes.length > 0) {
            allCheckbox.checked = checkedCount === columnCheckboxes.length;
            allCheckbox.indeterminate = checkedCount > 0 && checkedCount < columnCheckboxes.length;
        } else {
            allCheckbox.checked = false;
            allCheckbox.indeterminate = false;
        }
    });
}

/**
 * Limpiar selección masiva
 */
function clearBulkSelection() {
    // Desmarcar todos los checkboxes
    document.querySelectorAll('.bulk-order-checkbox').forEach(cb => {
        cb.checked = false;
        cb.disabled = false;
    });
    document.querySelectorAll('.bulk-select-all').forEach(cb => {
        cb.checked = false;
        cb.indeterminate = false;
        cb.disabled = false;
    });

    bulkSelectedOrders = [];
    bulkSelectedColumn = null;

    document.getElementById('bulk-action-bar').style.display = 'none';
}

/**
 * Mostrar modal de confirmación para tracking masivo
 */
function processBulkTracking() {
    if (bulkSelectedOrders.length === 0) return;

    // Llenar datos del modal
    document.getElementById('confirm-count').textContent = bulkSelectedOrders.length;
    document.getElementById('confirm-column').textContent =
        bulkSelectedColumn === 'chamo' ? 'CHAMO' : 'DINSIDES';

    // Establecer fecha por defecto (hoy)
    const today = new Date();
    const dateInput = document.getElementById('bulk-tracking-date');
    dateInput.value = formatDateForInput(today);

    // Actualizar vista previa del mensaje con la fecha actual
    updateBulkTrackingPreview();

    // Agregar listener para actualizar preview cuando cambie la fecha
    dateInput.removeEventListener('change', updateBulkTrackingPreview);
    dateInput.addEventListener('change', updateBulkTrackingPreview);

    // Mostrar modal
    const modal = new bootstrap.Modal(document.getElementById('bulkTrackingConfirmModal'));
    modal.show();
}

/**
 * Actualizar vista previa del mensaje de tracking masivo
 */
function updateBulkTrackingPreview() {
    const dateInput = document.getElementById('bulk-tracking-date');
    let dateValue = dateInput.value;

    console.log('updateBulkTrackingPreview - dateInput.value (raw):', dateValue);

    // Si el navegador devuelve fecha en formato local (DD/MM/YYYY), convertir a ISO (YYYY-MM-DD)
    if (dateValue && dateValue.includes('/')) {
        const parts = dateValue.split('/');
        if (parts.length === 3) {
            // Formato DD/MM/YYYY -> YYYY-MM-DD
            dateValue = `${parts[2]}-${parts[1]}-${parts[0]}`;
            console.log('updateBulkTrackingPreview - dateValue convertido:', dateValue);
        }
    }

    console.log('updateBulkTrackingPreview - bulkSelectedColumn:', bulkSelectedColumn);
    // Mostrar mensaje normal (los pedidos COD recibirán mensaje personalizado automáticamente)
    const message = generateBulkTrackingMessage(bulkSelectedColumn, dateValue);
    console.log('updateBulkTrackingPreview - message:', message);

    // Verificar si hay pedidos COD en la selección
    const hasCodOrders = bulkSelectedOrders.some(o => {
        const card = document.querySelector(`[data-order-id="${o.orderId}"]`);
        return card && card.querySelector('.cod-badge');
    });

    let displayMessage = message;
    if (hasCodOrders) {
        displayMessage += '\n\n📌 Nota: Los pedidos con pago contraentrega (COD) recibirán un mensaje personalizado con el monto a pagar.';
    }

    document.getElementById('confirm-message').textContent = displayMessage;
}

/**
 * Confirmar y procesar tracking masivo
 */
async function confirmBulkTracking() {
    // Validar que se haya seleccionado una fecha
    const dateInput = document.getElementById('bulk-tracking-date');
    if (!dateInput.value) {
        showError('Por favor seleccione una fecha de envío');
        return;
    }

    // Convertir fecha si está en formato local (DD/MM/YYYY) a ISO (YYYY-MM-DD)
    let dateValue = dateInput.value;
    if (dateValue.includes('/')) {
        const parts = dateValue.split('/');
        if (parts.length === 3) {
            dateValue = `${parts[2]}-${parts[1]}-${parts[0]}`;
        }
    }

    const btn = document.getElementById('btn-confirm-bulk');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Procesando...';

    try {
        const response = await fetch('/dispatch/api/bulk-tracking-simple', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                orders: bulkSelectedOrders.map(o => o.orderId),
                column: bulkSelectedColumn,
                shipping_date: dateValue
            })
        });

        const data = await response.json();

        // Cerrar modal
        bootstrap.Modal.getInstance(document.getElementById('bulkTrackingConfirmModal')).hide();

        if (data.success) {
            let msg = `Tracking asignado a ${data.exitosos} pedido(s).`;
            if (data.fallidos > 0) {
                msg += ` ${data.fallidos} fallido(s).`;
            }
            showSuccess(msg);
            clearBulkSelection();
            await loadOrders();
        } else {
            showError(data.error || 'Error al procesar tracking masivo');
        }

    } catch (error) {
        console.error('Error:', error);
        showError('Error de conexión: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}
