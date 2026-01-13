# Plan de Implementación: Módulo de Compras (Reabastecimiento)

## 📋 Análisis del Requerimiento

**Objetivo:** Crear un módulo para gestionar compras/reabastecimiento que muestre **automáticamente** todos los productos que tienen stock cero asignado manualmente mediante el módulo de actualización de stock masivo.

**Contexto clave:**
- El usuario ya actualiza stock manualmente usando `/stock` (actualización masiva)
- Cuando un producto llega a stock 0, significa que necesita ser reabastecido
- Este módulo debe facilitar el proceso de crear órdenes de compra para reabastecer inventario

---

## 🎯 Funcionalidades Propuestas

### 1. **Vista Principal: Lista de Productos para Reabastecimiento**

**Ruta:** `/purchases` o `/restock`

**Características:**
- ✅ Mostrar automáticamente todos los productos con `_stock = 0` **que existan en `wpyz_stock_history` con `new_stock = 0`**
  - Esto asegura que solo mostramos productos que fueron actualizados manualmente a 0 mediante el módulo de stock
  - Excluye productos nuevos que nunca han tenido stock
- ✅ Filtrar solo productos con SKU válido (ya que se comparan con Fishbowl)
- ✅ Mostrar información clave:
  - SKU
  - Nombre del producto
  - Días sin stock (calculado desde última actualización a 0)
  - Último usuario que actualizó a 0 (auditoría)
  - Costo unitario en USD (desde `woo_products_fccost`)
  - Campo para ingresar cantidad a ordenar
- ✅ Permitir selección múltiple (checkboxes) para agrupar compras
- ✅ Búsqueda y filtros:
  - Por SKU
  - Por nombre
  - Por días sin stock
  - Por usuario que actualizó

### 2. **Creación de Orden de Compra**

**Características:**
- ✅ Seleccionar múltiples productos de la lista
- ✅ Especificar cantidad a ordenar por cada producto (ya ingresada en la lista)
- ✅ Calcular costo total de la orden automáticamente (USD y PEN con tipo de cambio actual)
- ✅ Campos del formulario:
  - Proveedor (campo de texto libre)
  - Fecha estimada de entrega
  - Notas/observaciones
  - Número de orden autogenerado (formato: `PO-YYYY-NNN`, ej: `PO-2024-001`)
- ✅ Guardar orden de compra en tabla `woo_purchase_orders`
- ✅ **Generar PDF automáticamente** con los detalles de la orden

### 3. **Gestión de Órdenes de Compra**

**Estados posibles:**
- `pending` - Pendiente (orden creada, esperando confirmación)
- `ordered` - Ordenado (confirmado con proveedor)
- `in_transit` - En tránsito (mercancía en camino)
- `received` - Recibido (mercancía en almacén)
- `cancelled` - Cancelado

**Acciones:**
- ✅ Cambiar estado de orden
- ✅ Ver detalles de orden (productos, cantidades, costos)
- ✅ Editar orden (solo si está en `pending` o `ordered`)
- ✅ **Al marcar como `received`:**
  - Actualizar stock automáticamente sumando la cantidad ordenada (recepción completa)
  - Registrar en `wpyz_stock_history` la recepción
  - Cambiar estado a `received` con fecha real de entrega
- ✅ Descargar PDF de la orden en cualquier momento
- ✅ Historial de cambios de estado

### 4. **Dashboard de Compras**

**Métricas:**
- Total de productos sin stock (necesitan reabastecimiento)
- Órdenes de compra activas por estado
- Valor total de órdenes pendientes (USD/PEN)
- Productos críticos (más tiempo sin stock)
- Gráfico de tendencia de órdenes por mes

---

## 🗄️ Estructura de Base de Datos

### Nueva Tabla: `woo_purchase_orders`

```sql
CREATE TABLE woo_purchase_orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_number VARCHAR(50) UNIQUE NOT NULL,           -- Ej: PO-2024-001
    supplier_name VARCHAR(200),                          -- Proveedor
    status VARCHAR(20) NOT NULL DEFAULT 'pending',      -- pending, ordered, in_transit, received, cancelled
    order_date DATETIME NOT NULL,                        -- Fecha de creación
    expected_delivery_date DATE,                         -- Fecha estimada de entrega
    actual_delivery_date DATE,                           -- Fecha real de entrega (cuando se recibe)
    total_cost_usd DECIMAL(10,2),                        -- Costo total en USD
    exchange_rate DECIMAL(6,4),                          -- Tipo de cambio al momento de crear
    total_cost_pen DECIMAL(10,2),                        -- Costo total en PEN
    notes TEXT,                                          -- Observaciones
    created_by VARCHAR(100),                             -- Usuario que creó
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_order_number (order_number),
    INDEX idx_status (status),
    INDEX idx_order_date (order_date)
);
```

### Nueva Tabla: `woo_purchase_order_items`

```sql
CREATE TABLE woo_purchase_order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    purchase_order_id INT NOT NULL,                      -- FK a woo_purchase_orders
    product_id INT NOT NULL,                              -- ID del producto en wpyz_posts
    product_title VARCHAR(200),                           -- Nombre del producto (snapshot)
    sku VARCHAR(100),                                     -- SKU del producto
    quantity INT NOT NULL,                                -- Cantidad ordenada
    unit_cost_usd DECIMAL(10,2),                         -- Costo unitario en USD
    total_cost_usd DECIMAL(10,2),                        -- Costo total línea (quantity * unit_cost)
    notes TEXT,                                           -- Notas específicas del producto
    FOREIGN KEY (purchase_order_id) REFERENCES woo_purchase_orders(id) ON DELETE CASCADE,
    INDEX idx_purchase_order (purchase_order_id),
    INDEX idx_product (product_id),
    INDEX idx_sku (sku)
);
```

**Nota:** Se removió `quantity_received` ya que no se necesita recepción parcial.

### Nueva Tabla: `woo_purchase_order_history`

```sql
CREATE TABLE woo_purchase_order_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    purchase_order_id INT NOT NULL,
    old_status VARCHAR(20),
    new_status VARCHAR(20),
    changed_by VARCHAR(100),
    change_reason VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (purchase_order_id) REFERENCES woo_purchase_orders(id) ON DELETE CASCADE,
    INDEX idx_purchase_order (purchase_order_id),
    INDEX idx_created_at (created_at)
);
```

---

## 📁 Estructura de Archivos Nuevos

### Backend (Flask)

```
app/routes/purchases.py          # Blueprint principal de compras
app/models.py                     # Agregar clases PurchaseOrder, PurchaseOrderItem, PurchaseOrderHistory
```

### Frontend (Templates)

```
app/templates/purchases_list.html           # Lista de productos sin stock
app/templates/purchases_orders.html         # Gestión de órdenes de compra
app/templates/purchases_create.html         # Crear nueva orden
app/templates/purchases_detail.html         # Detalle de una orden
app/templates/purchases_dashboard.html      # Dashboard de compras
```

---

## 🔄 Flujo de Trabajo Completo

### Escenario: Reabastecer productos sin stock

1. **Usuario accede a `/purchases`**
   - Sistema muestra automáticamente todos los productos con `stock = 0`
   - Ordenados por fecha de última actualización (los más antiguos primero)

2. **Usuario selecciona productos a reabastecer**
   - Checkbox para selección múltiple
   - Input para especificar cantidad a ordenar

3. **Usuario crea orden de compra**
   - Click en "Crear Orden de Compra"
   - Formulario con:
     - Proveedor
     - Fecha estimada de entrega
     - Notas
   - Sistema calcula costo total automáticamente
   - Sistema genera número de orden (Ej: PO-2024-001)

4. **Orden creada con estado `pending`**
   - Se guarda en `woo_purchase_orders`
   - Items se guardan en `woo_purchase_order_items`
   - Historial registra creación

5. **Usuario descarga PDF de la orden**
   - Click en "Descargar PDF"
   - PDF generado con:
     - Logo y datos de la empresa
     - Número de orden y fecha
     - Proveedor
     - Tabla de productos (SKU, nombre, cantidad, costo unitario, total)
     - Total general en USD y PEN
     - Notas
   - PDF listo para enviar por email al proveedor

6. **Usuario gestiona estado de orden**
   - Cambiar a `ordered` cuando se confirma con proveedor
   - Cambiar a `in_transit` cuando está en camino
   - Cambiar a `received` cuando llega al almacén
     - **IMPORTANTE:** Al marcar como `received`, sistema actualiza stock automáticamente
     - Suma `quantity` completa al `_stock` de cada producto (recepción 100%)
     - Registra cambio en `wpyz_stock_history` con razón: "Recepción de orden PO-2024-XXX"
     - Guarda fecha real de entrega

7. **Stock actualizado automáticamente**
   - Productos desaparecen de lista de "productos sin stock"
   - Stock history registra: "Recepción de orden PO-2024-001"

---

## 🎨 Diseño de Interfaz (Wireframe Conceptual)

### Vista: `/purchases` (Lista de productos sin stock)

```
┌──────────────────────────────────────────────────────────────────────┐
│  [🛒 Módulo de Compras]                      [📊 Ver Dashboard]      │
├──────────────────────────────────────────────────────────────────────┤
│  Productos Sin Stock - Necesitan Reabastecimiento                   │
│                                                                       │
│  [🔍 Buscar SKU/Nombre]  [Filtro: Todos ▼]  [Ordenar: Fecha ▼]     │
│                                                                       │
│  Seleccionados: 0 productos   [✓ Crear Orden de Compra]            │
├──────────────────────────────────────────────────────────────────────┤
│  [☑] SKU       │ Producto              │ Sin stock │ Costo  │ Cant. │
│  [ ] AB12345   │ Producto XYZ          │ 5 días    │ $15.00 │ [50]  │
│  [ ] CD67890   │ Producto ABC          │ 3 días    │ $22.50 │ [30]  │
│  [ ] EF11223   │ Producto 123          │ 10 días   │ $8.75  │ [100] │
└──────────────────────────────────────────────────────────────────────┘
```

### Vista: `/purchases/orders` (Órdenes de compra)

```
┌──────────────────────────────────────────────────────────────────────┐
│  [← Volver]  Órdenes de Compra                [+ Nueva Orden]        │
├──────────────────────────────────────────────────────────────────────┤
│  [Todas ▼]  [Pendientes]  [Ordenadas]  [En Tránsito]  [Recibidas]  │
├──────────────────────────────────────────────────────────────────────┤
│  Orden       │ Proveedor    │ Items │ Total    │ Estado      │ ...  │
│  PO-2024-003 │ Proveedor A  │ 5     │ $450.00  │ [En Tránsito]│ Ver │
│  PO-2024-002 │ Proveedor B  │ 3     │ $320.00  │ [Ordenado]   │ Ver │
│  PO-2024-001 │ Proveedor A  │ 8     │ $890.00  │ [Recibido]   │ Ver │
└──────────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Consideraciones Técnicas

### 1. **Integración con Stock History**

- Al marcar orden como `received`, usar la función existente de actualización de stock
- Registrar en `wpyz_stock_history`:
  - `change_reason`: "Recepción de orden PO-2024-XXX"
  - `changed_by`: Usuario que marcó como recibido
  - `old_stock`: 0 (o el valor que tenga)
  - `new_stock`: quantity_received

### 2. **Permisos y Roles**

- **Asesores:** Pueden ver productos sin stock, ver órdenes, pero NO crear/editar
- **Admins:** Pueden crear, editar, cambiar estados de órdenes

### 3. **Validaciones**

- No permitir crear orden con 0 productos seleccionados
- Validar que cantidad > 0
- Validar que producto tenga SKU válido
- Al marcar como `received`, validar que `quantity_received <= quantity`

### 4. **Tipo de Cambio**

- Al crear orden, capturar tipo de cambio actual desde `woo_tipo_cambio`
- Guardar en orden para mantener histórico correcto
- Calcular `total_cost_pen = total_cost_usd * exchange_rate`

### 5. **Reportes y Exportación**

- Exportar lista de productos sin stock a Excel (similar a reportes de ganancias)
- Exportar orden de compra a PDF para enviar a proveedor
- Reporte de órdenes por período

---

## 📊 Métricas de Dashboard

### KPIs Principales:

1. **Productos sin stock:** Total de productos con `stock = 0`
2. **Días promedio sin stock:** Promedio de días que productos llevan en 0
3. **Órdenes activas:** Count de órdenes en `pending`, `ordered`, `in_transit`
4. **Valor en tránsito:** Sum de `total_cost_usd` de órdenes `in_transit`
5. **Próximas entregas:** Órdenes con `expected_delivery_date` en próximos 7 días

### Gráficos:

- Tendencia de órdenes creadas por mes (últimos 12 meses)
- Top 10 productos más reabastecidos
- Tiempo promedio desde orden hasta recepción

---

## 🚀 Plan de Implementación Actualizado

### **Fase 1: Base de Datos y Modelos** (2 horas)
1. Crear 3 tablas SQL:
   - `woo_purchase_orders`
   - `woo_purchase_order_items`
   - `woo_purchase_order_history`
2. Agregar modelos en `app/models.py`: `PurchaseOrder`, `PurchaseOrderItem`, `PurchaseOrderHistory`
3. Crear índices necesarios
4. Script de migración SQL

### **Fase 2: Backend - API Endpoints** (4 horas)
1. Crear `app/routes/purchases.py`
2. Endpoints esenciales:
   - `GET /purchases/api/products-out-of-stock` - Lista de productos con stock = 0 (verificados en history)
   - `POST /purchases/api/orders` - Crear orden de compra
   - `GET /purchases/api/orders` - Lista de órdenes
   - `GET /purchases/api/orders/<id>` - Detalle de orden específica
   - `PUT /purchases/api/orders/<id>/status` - Cambiar estado (con lógica especial para `received`)
   - `GET /purchases/api/orders/<id>/pdf` - Generar y descargar PDF
   - `GET /purchases/api/stats` - Estadísticas para dashboard (opcional)
3. Instalar librería PDF: `reportlab` o `weasyprint`

### **Fase 3: Frontend - Vistas Principales** (5 horas)
1. **`purchases_list.html`** - Vista principal
   - Tabla de productos sin stock con checkbox, cantidad input
   - Botón "Crear Orden de Compra" con modal/formulario
   - Cálculo automático de totales
2. **`purchases_orders.html`** - Lista de órdenes
   - Tabla con filtros por estado
   - Acciones: Ver, Descargar PDF, Cambiar Estado
3. **`purchases_detail.html`** - Detalle de orden
   - Información completa de la orden
   - Items en tabla
   - Botones de acción según estado
   - Historial de cambios

### **Fase 4: Generación de PDF** (2-3 horas)
1. Template de PDF profesional para orden de compra
2. Función para generar PDF con datos de la orden
3. Incluir logo, datos empresa, tabla productos, totales
4. Endpoint para descargar PDF

### **Fase 5: Lógica de Actualización de Stock** (2 horas)
1. Función para actualizar stock al marcar como `received`
2. Validación de stock actual antes de actualizar
3. Registro automático en `wpyz_stock_history`
4. Actualización de metadatos `_stock` y `_stock_status`
5. Testing de flujo completo

### **Fase 6: Testing y Refinamiento** (2 horas)
1. Testing de flujo completo end-to-end
2. Validaciones de edge cases
3. Permisos por rol (solo admins pueden crear/editar)
4. Optimización de queries
5. UX improvements

**Tiempo total estimado:** 17-19 horas de desarrollo

### Simplificaciones aplicadas:
- ✅ Sin recepción parcial (siempre 100%)
- ✅ Proveedor como texto libre (sin catálogo)
- ✅ Enfoque en funcionalidad core
- ✅ Dashboard opcional (puede implementarse después si se necesita)

---

## 🔐 Seguridad y Permisos

| Acción | Asesor | Admin |
|--------|--------|-------|
| Ver productos sin stock | ✅ | ✅ |
| Ver órdenes de compra | ✅ | ✅ |
| Crear orden de compra | ❌ | ✅ |
| Editar orden | ❌ | ✅ |
| Cambiar estado orden | ❌ | ✅ |
| Marcar como recibido | ❌ | ✅ |
| Cancelar orden | ❌ | ✅ |
| Ver dashboard | ✅ | ✅ |

---

## 📌 Notas Adicionales

### Posibles Mejoras Futuras (v2.0):

1. **Proveedores como catálogo**
   - Tabla `woo_suppliers` con info de contacto
   - Relación con productos (qué proveedor surte qué SKUs)

2. **Integración con correo**
   - Enviar orden de compra por email a proveedor
   - Notificación cuando orden está en tránsito

3. **Recepción parcial**
   - Permitir marcar cantidades recibidas distintas a las ordenadas
   - Campo `quantity_received` por item

4. **Predicción de reabastecimiento**
   - ML para predecir cuándo un producto llegará a stock 0
   - Sugerencias automáticas de cantidad a ordenar basado en ventas

5. **Códigos de barras**
   - Escanear productos al recibir orden
   - Validación contra orden de compra

6. **Multi-moneda**
   - Proveedores en diferentes monedas (USD, EUR, PEN)

---

## ✅ Respuestas del Cliente - Alcance Confirmado

1. **Stock:** ✅ Solo productos con stock **exactamente = 0** que hayan sido asignados mediante el módulo de actualización de stock
   - Verificar que existan en `wpyz_stock_history` con `new_stock = 0`

2. **Proveedores:** ✅ Un solo proveedor, campo de texto libre es suficiente

3. **Recepción parcial:** ❌ NO necesaria - Siempre se recibe la cantidad completa ordenada

4. **Exportación a PDF:** ✅ SÍ, necesaria para enviar al proveedor

5. **Prioridad:** 🟡 Media (1-2 compras al mes)

---

## ✅ Resumen del Alcance Final

### Funcionalidad Core (Implementación Completa):

1. **📦 Vista de Productos Sin Stock** (`/purchases`)
   - Solo productos con stock = 0 verificados en historial
   - Tabla con selección múltiple
   - Campos: SKU, nombre, días sin stock, costo USD, cantidad a ordenar

2. **📝 Crear Orden de Compra**
   - Modal/formulario simple
   - Proveedor (texto libre)
   - Fecha estimada
   - Cálculo automático de totales (USD y PEN)
   - Número autogenerado (PO-YYYY-NNN)

3. **📋 Gestión de Órdenes** (`/purchases/orders`)
   - Lista de todas las órdenes
   - Filtros por estado
   - Vista detalle de cada orden
   - Cambio de estados con validaciones

4. **📄 Generación de PDF**
   - PDF profesional de orden de compra
   - Descargable en cualquier momento
   - Listo para enviar a proveedor

5. **📊 Recepción Automática**
   - Al marcar como "Recibido":
     - Stock actualizado automáticamente (suma cantidad completa)
     - Historial registrado
     - Productos desaparecen de lista sin stock

### Opcionales (Prioridad Baja):
- Dashboard con métricas
- Exportación a Excel
- Gráficos de tendencias

---

## ⏱️ Timeline Propuesto

Dado que el módulo tiene **prioridad media** y se usa **1-2 veces al mes**, propongo implementar en **2 sesiones**:

### **Sesión 1 (8-10 horas):**
- Fase 1: Base de datos y modelos
- Fase 2: Backend completo
- Fase 3: Frontend vista principal y creación

### **Sesión 2 (8-10 horas):**
- Fase 4: Generación de PDF
- Fase 5: Lógica de recepción y actualización stock
- Fase 6: Testing y refinamiento

**Total: 17-19 horas** repartidas en 2 días de trabajo.

---

**¿Procedo con la implementación? Puedo empezar con la Fase 1 (Base de Datos) ahora mismo si confirmas.**
