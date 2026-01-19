# Propuesta de Implementación: Edición de Pedidos

## Resumen Ejecutivo

Implementar funcionalidad para editar pedidos existentes en el sistema WooCommerce Manager, permitiendo modificar datos del cliente, dirección de entrega, productos, método de envío y pago.

---

## Análisis del Sistema Actual

### Flujo de Creación de Pedidos

El sistema actual utiliza un **wizard de 3 pasos** para crear pedidos:

1. **Paso 1**: Selección de productos (categorías, búsqueda, variaciones)
2. **Paso 2**: Datos del cliente y entrega (información personal, dirección, pago)
3. **Paso 3**: Resumen y confirmación

### Archivos Involucrados

| Archivo | Propósito |
|---------|-----------|
| `app/routes/orders.py` | Rutas y lógica de backend |
| `app/templates/orders_create.html` | Template del wizard (UI + JS) |
| `app/models.py` | Modelos de datos |

### Tablas de Base de Datos Afectadas

| Tabla | Descripción |
|-------|-------------|
| `wpyz_wc_orders` | Registro principal del pedido (HPOS) |
| `wpyz_posts` | Compatibilidad legacy WooCommerce |
| `wpyz_wc_order_addresses` | Direcciones billing/shipping (HPOS) |
| `wpyz_postmeta` | Metadata legacy |
| `wpyz_wc_orders_meta` | Metadata HPOS |
| `wpyz_wc_order_items` | Items del pedido (productos, envío, impuestos, descuentos) |
| `wpyz_wc_order_itemmeta` | Metadata de cada item |

---

## Opciones de Implementación

### Opción A: Wizard Completo (Recomendado)

**Descripción**: Reutilizar `orders_create.html` en "modo edición", pre-cargando los datos existentes del pedido.

**Ventajas**:
- Máxima flexibilidad (puede modificar TODO)
- Reutiliza código existente
- UX consistente con la creación
- Permite agregar/quitar/modificar productos

**Desventajas**:
- Mayor complejidad de implementación
- Necesita manejar diferencias de stock
- Requiere lógica de comparación (qué cambió)

**Campos Editables**:
- ✅ Productos (agregar, quitar, modificar cantidad)
- ✅ Datos del cliente (nombre, email, teléfono, DNI, RUC)
- ✅ Dirección de entrega (tipo, dirección, departamento, distrito)
- ✅ Método de envío y costo
- ✅ Método de pago
- ✅ Descuento
- ✅ Notas del pedido

---

### Opción B: Modal de Edición Rápida

**Descripción**: Modal simplificado para editar solo campos comunes, sin modificar productos.

**Ventajas**:
- Implementación más rápida
- Menor riesgo de errores
- No afecta inventario

**Desventajas**:
- Limitado (no puede cambiar productos)
- Si el cliente quiere cambiar producto, hay que cancelar y crear nuevo pedido

**Campos Editables**:
- ✅ Datos del cliente
- ✅ Dirección de entrega
- ✅ Método de envío y costo
- ✅ Método de pago
- ✅ Notas
- ❌ Productos (NO editable)
- ❌ Descuento (NO editable)

---

## Implementación Detallada (Opción A - Wizard Completo)

### 1. Nueva Ruta: GET `/orders/edit/<order_id>`

```python
@bp.route('/edit/<int:order_id>')
@login_required
def edit_order(order_id):
    """
    Renderiza el wizard de edición con los datos del pedido pre-cargados.
    """
    # Obtener datos del pedido desde la base de datos
    order_data = get_order_for_edit(order_id)

    if not order_data:
        flash('Pedido no encontrado', 'danger')
        return redirect(url_for('orders.list'))

    return render_template('orders_create.html',
                          edit_mode=True,
                          order_id=order_id,
                          order_data=order_data)
```

### 2. Nueva Ruta: PUT `/orders/update-order/<order_id>`

```python
@bp.route('/update-order/<int:order_id>', methods=['PUT'])
@login_required
def update_order(order_id):
    """
    Actualiza un pedido existente.

    Request JSON: Mismo formato que save-order

    Proceso:
    1. Validar datos recibidos
    2. Comparar con datos actuales
    3. Actualizar tablas afectadas
    4. Manejar diferencias de stock
    5. Registrar en historial
    """
    try:
        data = request.get_json()

        # Validaciones
        if not data.get('items'):
            return jsonify({'success': False, 'error': 'Debe haber al menos un producto'})

        # Obtener pedido actual para comparación
        current_order = get_order_details(order_id)

        # Actualizar datos del cliente
        update_order_customer(order_id, data['customer'])

        # Actualizar direcciones
        update_order_addresses(order_id, data['customer'])

        # Actualizar items (productos)
        update_order_items(order_id, data['items'], current_order['items'])

        # Actualizar envío
        update_order_shipping(order_id, data['shipping_cost'], data['shipping_method_title'])

        # Actualizar totales
        update_order_totals(order_id, data)

        # Registrar en historial
        log_order_edit(order_id, current_user.username, data)

        return jsonify({
            'success': True,
            'order_id': order_id,
            'message': 'Pedido actualizado correctamente'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
```

### 3. Nueva Ruta API: GET `/orders/api/get-order/<order_id>`

```python
@bp.route('/api/get-order/<int:order_id>')
@login_required
def api_get_order(order_id):
    """
    Retorna los datos completos del pedido para edición.

    Response JSON:
    {
        "order_id": 12345,
        "order_number": "W-00001",
        "status": "processing",
        "customer": {
            "first_name": "Juan",
            "last_name": "Pérez",
            "email": "juan@example.com",
            "phone": "987654321",
            "company": "12345678",  // DNI
            "billing_ruc": "20123456789",
            "billing_entrega": "billing_domicilio",
            "address_1": "Av. Principal 123",
            "city": "Lima",
            "state": "Lima",
            "billing_referencia": "Frente al parque"
        },
        "items": [
            {
                "item_id": 1,
                "product_id": 123,
                "variation_id": 456,
                "name": "Producto X - Talla M",
                "quantity": 2,
                "price": 50.00,
                "subtotal": 100.00
            }
        ],
        "shipping": {
            "method_title": "Envío Olva Courier",
            "cost": 15.00
        },
        "payment": {
            "method": "cod",
            "method_title": "Yape"
        },
        "totals": {
            "subtotal": 100.00,
            "shipping": 15.00,
            "tax": 18.00,
            "discount": 0.00,
            "total": 118.00
        },
        "customer_note": "Notas del pedido"
    }
    """
    order_data = get_order_for_edit(order_id)
    return jsonify(order_data)
```

### 4. Modificaciones a `orders_create.html`

#### 4.1 Detectar Modo Edición

```html
{% block content %}
<div class="container-fluid" id="order-wizard"
     data-edit-mode="{{ 'true' if edit_mode else 'false' }}"
     data-order-id="{{ order_id if edit_mode else '' }}">
```

#### 4.2 JavaScript: Cargar Datos en Modo Edición

```javascript
// Variables globales
let isEditMode = false;
let editOrderId = null;

document.addEventListener('DOMContentLoaded', function() {
    // Detectar modo edición
    const wizardContainer = document.getElementById('order-wizard');
    isEditMode = wizardContainer.dataset.editMode === 'true';
    editOrderId = wizardContainer.dataset.orderId || null;

    if (isEditMode && editOrderId) {
        loadOrderForEdit(editOrderId);
    } else {
        // Modo creación normal
        loadCategories();
    }
});

async function loadOrderForEdit(orderId) {
    try {
        showLoading('Cargando pedido...');

        const response = await fetch(`/orders/api/get-order/${orderId}`);
        const data = await response.json();

        if (!data.order_id) {
            showError('No se pudo cargar el pedido');
            return;
        }

        // Cargar productos en el carrito
        await loadOrderItems(data.items);

        // Cargar datos del cliente
        populateCustomerForm(data.customer);

        // Cargar datos de envío
        populateShippingForm(data.shipping, data.payment);

        // Cargar notas
        document.getElementById('customer-note').value = data.customer_note || '';

        // Actualizar título
        document.querySelector('.wizard-title').textContent =
            `Editar Pedido ${data.order_number}`;

        // Cambiar texto del botón
        document.getElementById('btn-submit').textContent = 'Actualizar Pedido';

        hideLoading();

    } catch (error) {
        console.error('Error cargando pedido:', error);
        showError('Error al cargar el pedido: ' + error.message);
    }
}

async function loadOrderItems(items) {
    // Limpiar carrito actual
    cart = [];

    for (const item of items) {
        // Obtener datos del producto
        const productData = await fetchProductData(item.product_id, item.variation_id);

        cart.push({
            product_id: item.product_id,
            variation_id: item.variation_id || null,
            name: item.name,
            quantity: item.quantity,
            price: item.price,
            sku: productData.sku,
            image: productData.image,
            original_item_id: item.item_id  // Para tracking de cambios
        });
    }

    updateCartDisplay();
}

function populateCustomerForm(customer) {
    document.getElementById('first-name').value = customer.first_name || '';
    document.getElementById('last-name').value = customer.last_name || '';
    document.getElementById('email').value = customer.email || '';
    document.getElementById('phone').value = customer.phone || '';
    document.getElementById('dni').value = customer.company || '';
    document.getElementById('ruc').value = customer.billing_ruc || '';

    // Tipo de entrega
    const entregaRadio = document.querySelector(
        `input[name="billing_entrega"][value="${customer.billing_entrega}"]`
    );
    if (entregaRadio) {
        entregaRadio.checked = true;
        updateAddressFields();
    }

    // Dirección
    document.getElementById('address').value = customer.address_1 || '';
    document.getElementById('reference').value = customer.billing_referencia || '';

    // Departamento y distrito (requiere cargar selects primero)
    loadDepartamentos().then(() => {
        document.getElementById('departamento').value = customer.state || '';
        if (customer.state) {
            loadDistritos(customer.state).then(() => {
                document.getElementById('distrito').value = customer.city || '';
            });
        }
    });
}

function populateShippingForm(shipping, payment) {
    // Costo de envío
    document.getElementById('shipping-cost').value = shipping.cost || 0;

    // Método de envío (se carga después de seleccionar distrito)
    // Se almacena temporalmente
    window.pendingShippingMethod = shipping.method_title;

    // Método de pago
    document.getElementById('payment-method').value = payment.method || 'cod';
}
```

#### 4.3 Modificar `submitOrder()` para Edición

```javascript
async function submitOrder() {
    // ... validaciones existentes ...

    // Construir payload
    const orderData = buildOrderPayload();

    // Determinar endpoint según modo
    const endpoint = isEditMode
        ? `/orders/update-order/${editOrderId}`
        : '/orders/save-order';

    const method = isEditMode ? 'PUT' : 'POST';

    try {
        const response = await fetch(endpoint, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(orderData)
        });

        const result = await response.json();

        if (result.success) {
            showSuccessModal(
                isEditMode ? 'Pedido Actualizado' : 'Pedido Creado',
                result.order_id,
                result.order_number
            );
        } else {
            showError(result.error);
        }

    } catch (error) {
        showError('Error de conexión: ' + error.message);
    }
}
```

### 5. Funciones de Actualización en Backend

#### 5.1 Actualizar Items del Pedido

```python
def update_order_items(order_id, new_items, current_items):
    """
    Compara items actuales con nuevos y aplica cambios.

    Casos:
    1. Item existe y cantidad cambió -> UPDATE
    2. Item existe y se eliminó -> DELETE
    3. Item nuevo -> INSERT
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Mapear items actuales por product_id + variation_id
        current_map = {
            (item['product_id'], item['variation_id']): item
            for item in current_items
        }

        new_map = {
            (item['product_id'], item.get('variation_id')): item
            for item in new_items
        }

        # Items a eliminar
        to_delete = set(current_map.keys()) - set(new_map.keys())
        for key in to_delete:
            item = current_map[key]
            delete_order_item(cursor, item['item_id'])
            # Restaurar stock
            restore_stock(item['product_id'], item['variation_id'], item['quantity'])

        # Items a actualizar o agregar
        for key, new_item in new_map.items():
            if key in current_map:
                current = current_map[key]
                if new_item['quantity'] != current['quantity']:
                    # Actualizar cantidad
                    update_item_quantity(cursor, current['item_id'], new_item)
                    # Ajustar stock
                    qty_diff = current['quantity'] - new_item['quantity']
                    adjust_stock(new_item['product_id'], new_item.get('variation_id'), qty_diff)
            else:
                # Nuevo item
                insert_order_item(cursor, order_id, new_item)
                # Reducir stock
                reduce_stock(new_item['product_id'], new_item.get('variation_id'), new_item['quantity'])

        conn.commit()

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()
```

#### 5.2 Actualizar Totales

```python
def update_order_totals(order_id, data):
    """
    Recalcula y actualiza los totales del pedido.
    """
    # Calcular totales
    items_total = sum(item['price'] * item['quantity'] for item in data['items'])

    discount_pct = data.get('discount_percentage', 0)
    discount_amount = items_total * (discount_pct / 100) if discount_pct > 0 else 0

    items_after_discount = items_total - discount_amount
    shipping_cost = Decimal(str(data.get('shipping_cost', 0)))

    total_with_tax = items_after_discount + shipping_cost
    tax_amount = total_with_tax - (total_with_tax / Decimal('1.18'))

    # Actualizar wpyz_wc_orders
    update_query = """
        UPDATE wpyz_wc_orders
        SET total_amount = %s,
            tax_amount = %s,
            date_updated_gmt = %s
        WHERE id = %s
    """

    # Actualizar wpyz_wc_orders_meta
    update_meta(order_id, '_order_total', str(total_with_tax))
    update_meta(order_id, '_order_tax', str(tax_amount))
    update_meta(order_id, '_order_shipping', str(shipping_cost))

    # Actualizar wpyz_postmeta (legacy)
    update_postmeta(order_id, '_order_total', str(total_with_tax))
    update_postmeta(order_id, '_order_tax', str(tax_amount))
    update_postmeta(order_id, '_order_shipping', str(shipping_cost))
```

### 6. Agregar Botón "Editar" en Vista de Detalle

En `orders_list.html` o donde se muestre el detalle del pedido:

```html
{% if order.status not in ['completed', 'cancelled', 'refunded'] %}
<a href="{{ url_for('orders.edit_order', order_id=order.id) }}"
   class="btn btn-warning">
    <i class="bi bi-pencil"></i> Editar Pedido
</a>
{% endif %}
```

---

## Consideraciones de Stock

### Al Editar Productos

| Acción | Stock |
|--------|-------|
| Aumentar cantidad | Reducir stock adicional |
| Reducir cantidad | Restaurar stock |
| Eliminar producto | Restaurar stock completo |
| Agregar producto | Reducir stock |

### Validaciones

- Verificar stock disponible antes de aumentar cantidad
- No permitir agregar productos sin stock
- Mostrar advertencia si stock es bajo

---

## Permisos y Restricciones

### Quién Puede Editar

- Usuarios con rol `admin` o `master`
- Solo pedidos en estado: `pending`, `processing`, `on-hold`

### Estados No Editables

- `completed` - Pedido ya entregado
- `cancelled` - Pedido cancelado
- `refunded` - Pedido reembolsado
- `failed` - Pedido fallido

---

## Historial de Cambios

Registrar cada edición en tabla de historial:

```sql
CREATE TABLE order_edit_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    user_id INT NOT NULL,
    changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    changes_json TEXT,  -- JSON con antes/después
    FOREIGN KEY (order_id) REFERENCES wpyz_wc_orders(id)
);
```

---

## Plan de Implementación

### Fase 1: Backend (Estimado: 1-2 días)
1. [ ] Crear ruta `GET /orders/api/get-order/<id>`
2. [ ] Crear ruta `PUT /orders/update-order/<id>`
3. [ ] Implementar funciones de actualización de items
4. [ ] Implementar actualización de direcciones
5. [ ] Implementar actualización de totales
6. [ ] Agregar manejo de stock

### Fase 2: Frontend (Estimado: 1-2 días)
1. [ ] Modificar `orders_create.html` para detectar modo edición
2. [ ] Implementar `loadOrderForEdit()`
3. [ ] Implementar funciones de pre-llenado de formularios
4. [ ] Modificar `submitOrder()` para edición
5. [ ] Agregar botón "Editar" en vista de detalle

### Fase 3: Testing (Estimado: 1 día)
1. [ ] Probar edición de datos de cliente
2. [ ] Probar cambio de productos (agregar, quitar, modificar cantidad)
3. [ ] Verificar actualización de stock
4. [ ] Verificar recálculo de totales
5. [ ] Probar edge cases (sin productos, stock insuficiente)

### Fase 4: Refinamiento
1. [ ] Agregar registro de historial de cambios
2. [ ] Mejorar mensajes de error
3. [ ] Optimizar queries

---

## Archivos a Crear/Modificar

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `app/routes/orders.py` | Modificar | Agregar rutas de edición |
| `app/templates/orders_create.html` | Modificar | Soporte modo edición |
| `app/templates/orders_detail.html` | Modificar | Agregar botón editar |
| `app/services/order_service.py` | Crear (opcional) | Lógica de negocio separada |

---

## Riesgos y Mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| Inconsistencia de stock | Usar transacciones DB |
| Edición concurrente | Bloqueo optimista con timestamp |
| Pérdida de datos | Backup antes de actualizar |
| Errores de cálculo | Reutilizar lógica existente de creación |

---

## Notas Adicionales

1. **Sincronización WooCommerce**: Los cambios se guardan tanto en tablas HPOS como legacy para compatibilidad.

2. **Emails**: Considerar si se debe enviar email al cliente cuando se edita su pedido.

3. **Webhook**: Si hay integraciones externas, considerar disparar webhook de "order.updated".

4. **Cache**: Limpiar cache de WooCommerce después de actualizar (`wc_order_*` transients).

---

*Documento generado el 19 de enero de 2026*
