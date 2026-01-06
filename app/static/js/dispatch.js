// dispatch.js - Lógica del Módulo de Despacho Kanban

// Estado global
let currentOrderId = null;
let currentOrderData = null;
let sortableInstances = [];

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    console.log('Módulo de Despacho inicializado');

    // NO establecer fechas por defecto
    // Por defecto, se muestran TODOS los pedidos en estado wc-processing
    // El usuario puede filtrar manualmente si lo desea

    // Cargar pedidos (sin filtro de fechas)
    loadOrders();

    // Auto-refresh cada 2 minutos
    setInterval(loadOrders, 120000);
});

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
 * Cargar pedidos desde el backend
 */
async function loadOrders() {
    try {
        // Construir parámetros de filtro
        const params = new URLSearchParams();

        const dateFrom = document.getElementById('filter-date-from').value;
        const dateTo = document.getElementById('filter-date-to').value;
        const priorityOnly = document.getElementById('filter-priority').checked;

        // Solo aplicar filtro de fechas si AMBAS fechas están presentes
        if (dateFrom && dateTo) {
            params.append('date_from', dateFrom);
            params.append('date_to', dateTo);
        }

        if (priorityOnly) params.append('priority_only', 'true');

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

    // Limpiar todas las columnas
    Object.values(columnMap).forEach(columnId => {
        const column = document.getElementById(columnId);
        if (column) {
            column.innerHTML = '';
        }
    });

    // Renderizar pedidos en cada columna
    for (const [method, orders] of Object.entries(ordersByMethod)) {
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

        // Crear tarjetas de pedidos
        orders.forEach(order => {
            const card = createOrderCard(order);
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
 */
function createOrderCard(order) {
    const card = document.createElement('div');
    card.className = 'order-card';
    card.dataset.orderId = order.id;
    card.dataset.orderNumber = order.number;

    // Clases adicionales según estado
    if (order.is_priority) {
        card.classList.add('priority-' + order.priority_level);
    }
    if (order.is_stale) {
        card.classList.add('stale');
    }

    // Construir HTML de la tarjeta
    let html = `
        <div class="card-header">
            <div class="order-number">${order.number}</div>
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

    html += `
            </div>
        </div>
        <div class="card-body">
            <div class="customer-name">${order.customer_name}</div>
            <div class="order-total">S/ ${order.total.toFixed(2)}</div>
            <div class="order-date">${order.date_created}</div>
        </div>
        <div class="card-footer">
            <button class="btn btn-sm btn-outline-primary w-100" id="detail-btn-${order.id}" onclick="showOrderDetail(${order.id})">
                <i class="bi bi-eye"></i> Ver Detalle
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

            onEnd: function(evt) {
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

        // Mostrar notificación de éxito
        showSuccess(`Pedido ${orderNumber} movido a ${newMethod}`);

        // Actualizar contadores
        updateColumnCounts();

    } catch (error) {
        console.error('Error moviendo pedido:', error);
        showError('Error al mover pedido: ' + error.message);

        // Revertir movimiento visual
        if (evt.from && evt.item) {
            evt.from.insertBefore(evt.item, evt.from.children[evt.oldIndex]);
        }
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

    // Obtener botón y activar estado de carga
    const btn = document.getElementById(`detail-btn-${orderId}`);
    const originalContent = btn ? btn.innerHTML : '';

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Cargando...';
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
        document.getElementById('modal-order-number').textContent = order.number;
        document.getElementById('modal-customer-name').textContent = order.customer_name;
        document.getElementById('modal-customer-phone').textContent = order.customer_phone;
        document.getElementById('modal-customer-email').textContent = order.email;
        document.getElementById('modal-total').textContent = order.total.toFixed(2);
        document.getElementById('modal-date-created').textContent = order.date_created;
        document.getElementById('modal-status').textContent = order.status;
        document.getElementById('modal-shipping-method').textContent = order.shipping_method;
        document.getElementById('modal-created-by').textContent = order.created_by;

        // Renderizar lista de productos con imágenes y atributos
        const productsHtml = order.products.length > 0
            ? `<ul class="list-group list-group-flush">
                ${order.products.map(product => `
                    <li class="list-group-item">
                        <div class="d-flex gap-3">
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
                            <div class="text-end">
                                <span class="badge bg-primary rounded-pill">x${product.quantity}</span>
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

        // Botón de prioridad
        const card = document.querySelector(`[data-order-id="${orderId}"]`);
        const isPriority = card && (card.classList.contains('priority-high') || card.classList.contains('priority-urgent'));
        document.getElementById('priority-btn-text').textContent =
            isPriority ? 'Quitar Prioridad' : 'Marcar Prioritario';

        // Cargar historial
        loadOrderHistory(orderId);

        // Mostrar modal
        const modal = new bootstrap.Modal(document.getElementById('orderDetailModal'));
        modal.show();

        // Restaurar botón después de mostrar el modal
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalContent;
        }

    } catch (error) {
        console.error('Error cargando detalle de pedido:', error);
        showError('Error al cargar detalles del pedido: ' + error.message);

        // Restaurar botón en caso de error
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalContent;
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
 * Mostrar notificación de éxito
 */
function showSuccess(message) {
    // Usar toastr si está disponible, sino alert simple
    if (typeof toastr !== 'undefined') {
        toastr.success(message);
    } else {
        alert(message);
    }
}

/**
 * Mostrar notificación de error
 */
function showError(message) {
    if (typeof toastr !== 'undefined') {
        toastr.error(message);
    } else {
        alert('ERROR: ' + message);
    }
}
