# 📋 PLAN DE IMPLEMENTACIÓN: Sistema de Contraentrega (COD)

**Fecha de creación:** 2026-02-12
**Estado:** Pendiente de implementación
**Estimación:** 1.5 horas

---

## 🎯 Objetivo

Implementar control de pedidos contraentrega (Cash On Delivery - COD) con las siguientes características:

1. **Toggle en creación de pedidos WhatsApp** - Similar al toggle "Comunidad", desactivado por defecto
2. **Badge azul en tarjetas del Kanban** - Indicador visual en módulo de despacho
3. **Detección automática al enviar tracking** - Mensaje personalizado según tipo de pago
4. **Indicador en modal de detalles** - Sección visible que alerta sobre contraentrega

---

## 📊 Resumen de Componentes

| Componente | Acción | Archivo |
|------------|--------|---------|
| **1. Toggle en creación** | Agregar checkbox "Contraentrega" | `orders_create.html` |
| **2. Guardar en DB** | Campo `_is_cod` en meta | `orders.py` |
| **3. Badge en tarjetas** | Badge azul "COD" | `dispatch.js` + `dispatch.css` |
| **4. Campo en modal** | Sección "Contraentrega" | `dispatch_board.html` + `dispatch.js` |
| **5. Detección tracking** | Modificar mensaje automáticamente | `dispatch.js` (tracking masivo) |

---

## 🔧 FASE 1: Módulo de Creación de Pedidos

### 1.1 Frontend - Agregar Toggle

**Archivo:** `app/templates/orders_create.html`
**Ubicación:** Junto al checkbox "Es Comunidad" (aprox. línea 160-180)

```html
<!-- Toggle Contraentrega (junto a Es Comunidad) -->
<div class="col-md-6">
    <div class="form-check form-switch">
        <input class="form-check-input" type="checkbox" id="is-cod" role="switch">
        <label class="form-check-label" for="is-cod">
            <i class="bi bi-cash-coin text-primary"></i>
            <strong>Pago Contraentrega (COD)</strong>
            <small class="text-muted d-block">El cliente pagará al recibir el pedido</small>
        </label>
    </div>
</div>
```

---

### 1.2 Backend - Guardar en Base de Datos

**Archivo:** `app/routes/orders.py`
**Función:** `save_order()` (aprox. línea 1366)

**A) Capturar el campo del frontend:**
```python
# Línea ~1371, agregar:
is_cod = data.get('is_cod', False)
```

**B) Agregar a metadata (línea ~1824):**
```python
('_is_cod', 'yes' if is_cod else 'no'),
```

**C) En `save_order_external()` (línea ~2528):**
```python
# Agregar campo a la tabla
is_cod = data.get('is_cod', False)

# En el INSERT del OrderExternal
order_ext = OrderExternal(
    # ... campos existentes ...
    is_cod=is_cod  # Nuevo campo
)
```

**D) Agregar campo a modelo:**

**Archivo:** `app/models.py`

En la clase `OrderExternal`, agregar:
```python
is_cod = db.Column(db.Boolean, default=False, nullable=False)
```

---

### 1.3 Frontend - Enviar al Backend

**Archivo:** `app/templates/orders_create.html`
**Función:** `submitOrder()` (línea ~2724)

```javascript
const orderData = {
    customer: { ... },
    items: [ ... ],
    // ... otros campos ...
    is_community: $('#is-community').is(':checked'),
    is_cod: $('#is-cod').is(':checked')  // ← NUEVO
};
```

---

### 1.4 Backend - Actualización de Pedidos

**Archivo:** `app/routes/orders.py`
**Función:** `update_order_general_data()` (línea ~3143)

```python
# Actualizar meta de contraentrega
upsert_order_meta(order_id, '_is_cod', 'yes' if data.get('is_cod') else 'no')
```

---

## 🔧 FASE 2: Módulo de Despacho - Backend

### 2.1 Incluir Campo en Query

**Archivo:** `app/routes/dispatch.py`
**Función:** `get_orders()` (línea ~324)

**Modificación en SELECT:**
```python
SELECT
    o.id,
    # ... campos existentes ...
    om_is_cod.meta_value as is_cod  -- ← NUEVO
FROM wpyz_wc_orders o
# ... joins existentes ...
LEFT JOIN wpyz_wc_orders_meta om_is_cod ON o.id = om_is_cod.order_id
    AND om_is_cod.meta_key = '_is_cod'  -- ← NUEVO JOIN
```

**Modificación en el mapeo de resultados (línea ~530):**
```python
orders_list.append({
    'id': row[0],
    # ... campos existentes ...
    'is_cod': row[X] == 'yes'  # ← NUEVO (X = índice correcto)
})
```

---

### 2.2 Incluir en Detalles del Pedido

**Archivo:** `app/routes/dispatch.py`
**Función:** `get_order_detail()` (línea ~973)

```python
# En la query, agregar:
LEFT JOIN wpyz_wc_orders_meta om_is_cod ON o.id = om_is_cod.order_id
    AND om_is_cod.meta_key = '_is_cod'

# En el resultado (línea ~1162):
order_data = {
    # ... campos existentes ...
    'is_cod': order_result[X] == 'yes'  # ← NUEVO
}
```

---

## 🔧 FASE 3: Módulo de Despacho - Frontend

### 3.1 Badge en Tarjetas del Kanban

**Archivo:** `app/static/js/dispatch.js`
**Función:** `createOrderCard()` (línea ~177)

```javascript
function createOrderCard(order, columnMethod) {
    // ... código existente ...

    // Badges adicionales
    let badges = '';

    // Badge Comunidad
    if (order.is_community) {
        badges += '<span class="badge bg-success-subtle text-success border border-success ms-1" title="Comunidad">👥</span>';
    }

    // Badge Contraentrega ← NUEVO
    if (order.is_cod) {
        badges += '<span class="badge bg-primary cod-badge ms-1" title="Pago Contraentrega">💵 COD</span>';
    }

    let html = `
        <div class="card-header">
            <div class="order-number">
                ${order.number}
                ${badges}  // ← Insertar aquí
            </div>
            <!-- ... resto del header ... -->
        </div>
    `;
}
```

---

### 3.2 CSS para Badge COD

**Archivo:** `app/static/css/dispatch.css`
**Agregar al final:**

```css
/* ============================================
   BADGE CONTRAENTREGA (COD)
   ============================================ */

.cod-badge {
    background-color: #0d6efd !important;
    color: white !important;
    font-weight: 600;
    font-size: 0.75rem;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
}

/* Dark mode */
[data-theme="dark"] .cod-badge {
    background-color: #0a58ca !important;
    box-shadow: 0 0 8px rgba(13, 110, 253, 0.5);
}
```

---

### 3.3 Sección en Modal de Detalles

**Archivo:** `app/templates/dispatch_board.html`
**Ubicación:** Dentro de "Información del Pedido" (después de línea ~350)

```html
<!-- Información del pedido -->
<div class="mb-4">
    <h6 class="border-bottom pb-2">Información del Pedido</h6>
    <div class="row">
        <div class="col-md-6">
            <p class="mb-2">
                <i class="bi bi-cash"></i>
                <strong>Total:</strong>
                S/ <span id="modal-total"></span>
            </p>
            <p class="mb-2">
                <i class="bi bi-info-circle"></i>
                <strong>Estado:</strong>
                <span id="modal-status"></span>
            </p>
        </div>
        <div class="col-md-6">
            <p class="mb-2">
                <i class="bi bi-truck"></i>
                <strong>Método de Envío:</strong>
                <span id="modal-shipping-method"></span>
            </p>
            <p class="mb-2">
                <i class="bi bi-person-badge"></i>
                <strong>Creado por:</strong>
                <span id="modal-created-by"></span>
            </p>
        </div>
    </div>

    <!-- Alerta de Contraentrega ← NUEVO -->
    <div id="cod-alert-section" class="mt-3" style="display: none;">
        <div class="alert alert-primary d-flex align-items-center mb-0" role="alert">
            <i class="bi bi-cash-coin fs-4 me-3"></i>
            <div>
                <strong>Pago Contraentrega (COD)</strong>
                <p class="mb-0 small">El cliente pagará <strong>S/ <span id="modal-cod-amount">0</span></strong> al recibir el pedido</p>
            </div>
        </div>
    </div>
</div>
```

---

### 3.4 JavaScript - Mostrar en Modal

**Archivo:** `app/static/js/dispatch.js`
**Función:** `showOrderDetail()` (línea ~569)

```javascript
// Llenar modal con datos del pedido
document.getElementById('modal-order-number').textContent = order.number;
// ... otros campos ...

// Mostrar alerta de contraentrega si aplica ← NUEVO
const codAlertSection = document.getElementById('cod-alert-section');
if (order.is_cod) {
    document.getElementById('modal-cod-amount').textContent = order.total.toFixed(2);
    codAlertSection.style.display = 'block';
} else {
    codAlertSection.style.display = 'none';
}
```

---

## 🔧 FASE 4: Tracking Masivo con Mensaje Personalizado

### 4.1 Mensajes Personalizados por Tipo

**Archivo:** `app/static/js/dispatch.js`
**Ubicación:** Junto a `BULK_TRACKING_TEMPLATES` (línea ~19)

```javascript
// Plantillas de mensajes de tracking
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
```

---

### 4.2 Función para Generar Mensaje

**Archivo:** `app/static/js/dispatch.js`
**Modificar función:** `generateBulkTrackingMessage()` (línea ~27)

```javascript
/**
 * Generar mensaje de tracking reemplazando placeholders
 */
function generateBulkTrackingMessage(column, dateStr, orderData) {
    const templates = BULK_TRACKING_TEMPLATES[column];
    if (!templates) return '';

    // Seleccionar template según si es COD o no
    const template = orderData.is_cod ? templates.cod : templates.normal;

    // Formatear fecha
    const formattedDate = formatDateForMessage(dateStr);

    // Reemplazar placeholders
    let message = template.replace('@fecha_envio', formattedDate);

    // Si es COD, reemplazar monto
    if (orderData.is_cod) {
        message = message.replace('@monto', orderData.total.toFixed(2));
    }

    return message;
}
```

---

### 4.3 Backend - Procesar Tracking con COD

**Archivo:** `app/routes/dispatch.py`
**Función:** `bulk_tracking_simple()` (línea ~1390)

**Nota:** La implementación actual ya debería funcionar correctamente, solo verificar que recibe el mensaje correcto del frontend.

---

## 📝 FASE 5: Migración de Base de Datos

### 5.1 Script de Migración para Pedidos Externos

**Crear archivo:** `migrations/add_is_cod_to_external_orders.sql`

```sql
-- Agregar columna is_cod a woo_orders_ext
ALTER TABLE woo_orders_ext
ADD COLUMN is_cod BOOLEAN DEFAULT FALSE NOT NULL;

-- Crear índice para consultas rápidas
CREATE INDEX idx_woo_orders_ext_is_cod ON woo_orders_ext(is_cod);
```

**Ejecutar migración:**
```bash
# Conectar a la base de datos y ejecutar el script
mysql -u usuario -p nombre_db < migrations/add_is_cod_to_external_orders.sql
```

---

## ✅ FASE 6: Testing

### 6.1 Test Cases

| # | Caso de Prueba | Resultado Esperado |
|---|----------------|-------------------|
| 1 | Crear pedido WhatsApp con COD activado | Se guarda `_is_cod = 'yes'` en meta |
| 2 | Crear pedido WhatsApp sin COD | Se guarda `_is_cod = 'no'` en meta |
| 3 | Editar pedido y activar COD | Meta se actualiza correctamente |
| 4 | Ver pedido COD en despacho | Badge azul "💵 COD" visible |
| 5 | Ver pedido normal en despacho | Sin badge COD |
| 6 | Abrir modal de pedido COD | Alerta azul con monto visible |
| 7 | Enviar tracking a pedido COD | Mensaje personalizado con monto |
| 8 | Enviar tracking a pedido normal | Mensaje normal sin mención de COD |

---

## 📂 Resumen de Archivos a Modificar

| Archivo | Líneas Aprox. | Cambios |
|---------|---------------|---------|
| `orders_create.html` | +15 | Toggle COD |
| `orders.py` | +10 | Guardar meta `_is_cod` |
| `models.py` | +1 | Campo `is_cod` en OrderExternal |
| `dispatch.py` | +3 | JOIN y campo en queries |
| `dispatch_board.html` | +12 | Alerta COD en modal |
| `dispatch.js` | +40 | Badge, detección, mensajes |
| `dispatch.css` | +15 | Estilos badge COD |
| **SQL Migration** | +3 | ALTER TABLE |

**Total:** ~100 líneas de código

---

## 🚀 Orden de Implementación Recomendado

1. ✅ **Migración DB** (5 min)
2. ✅ **Modelo** (2 min)
3. ✅ **Toggle en creación** (10 min)
4. ✅ **Guardar en backend** (15 min)
5. ✅ **Queries despacho** (10 min)
6. ✅ **Badge en tarjetas** (10 min)
7. ✅ **Modal de detalles** (10 min)
8. ✅ **Mensajes personalizados** (15 min)
9. ✅ **Testing** (20 min)

**Tiempo total estimado:** ~1.5 horas

---

## 📌 Notas Importantes

- El campo `is_cod` se guarda como meta `_is_cod` con valores 'yes'/'no' para pedidos WooCommerce
- Para pedidos externos se usa un campo booleano en la tabla `woo_orders_ext`
- El badge usa color azul (`bg-primary`) para diferenciarse del verde de comunidad
- Los mensajes de tracking se modifican automáticamente sin intervención del usuario
- El monto exacto se incluye en el mensaje para que el cliente prepare el dinero

---

## 🔄 Próximos Pasos (Opcional - Futuras Mejoras)

1. **Filtro de COD en Kanban** - Checkbox para filtrar solo pedidos contraentrega
2. **Estadísticas** - Dashboard con métricas de pedidos COD vs otros métodos
3. **Notificación al courier** - Email/SMS especial para couriers con pedidos COD
4. **Confirmación de pago** - Sistema para marcar cuando se recibió el pago
5. **Reportes** - Exportar lista de pedidos COD para conciliación

---

**Documento creado por:** Claude Sonnet 4.5
**Última actualización:** 2026-02-12
