# PLAN DE IMPLEMENTACIÓN: MÓDULO DE COTIZACIÓN

> **Fecha:** 23 de Enero 2026
> **Proyecto:** WooCommerce Manager
> **Módulo:** Sistema de Cotizaciones

---

## 📋 RESUMEN EJECUTIVO

Este documento detalla el plan completo de implementación del módulo de cotizaciones para el sistema WooCommerce Manager. El módulo permitirá crear, gestionar y convertir cotizaciones en pedidos reales de WooCommerce.

### Decisiones Clave

- ✅ **Conversión a pedidos:** Manual (botón)
- ✅ **Edición:** Solo borradores (no editar enviadas)
- ✅ **Email:** Solo generación de PDF (descarga manual)
- ✅ **Precios:** Personalizables por cotización

---

## 1. ARQUITECTURA Y ESTRUCTURA

### 1.1 Base de Datos (3 Tablas Principales)

#### Tabla: `woo_quotations`
```sql
CREATE TABLE woo_quotations (
    id INT PRIMARY KEY AUTO_INCREMENT,

    -- Identificación
    quote_number VARCHAR(50) UNIQUE NOT NULL,  -- Formato: COT-2025-001
    version INT DEFAULT 1,

    -- Información del Cliente
    customer_name VARCHAR(200) NOT NULL,
    customer_email VARCHAR(255) NOT NULL,
    customer_phone VARCHAR(50),
    customer_dni VARCHAR(20),
    customer_ruc VARCHAR(20),
    customer_address TEXT,
    customer_city VARCHAR(100),
    customer_state VARCHAR(100),

    -- Detalles de Cotización
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    quote_date DATETIME NOT NULL,
    valid_until DATE NOT NULL,

    -- Precios
    subtotal DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    discount_type VARCHAR(20) DEFAULT 'percentage',
    discount_value DECIMAL(10,2) DEFAULT 0.00,
    discount_amount DECIMAL(10,2) DEFAULT 0.00,
    tax_rate DECIMAL(5,2) DEFAULT 18.00,
    tax_amount DECIMAL(10,2) DEFAULT 0.00,
    shipping_cost DECIMAL(10,2) DEFAULT 0.00,
    total DECIMAL(10,2) NOT NULL DEFAULT 0.00,

    -- Términos
    payment_terms TEXT,
    delivery_time VARCHAR(100),
    notes TEXT,
    terms_conditions TEXT,

    -- Auditoría
    created_by VARCHAR(100) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    sent_at DATETIME,
    accepted_at DATETIME,
    converted_order_id BIGINT,

    INDEX idx_quote_number (quote_number),
    INDEX idx_status (status),
    INDEX idx_customer_email (customer_email),
    INDEX idx_created_at (created_at),
    INDEX idx_valid_until (valid_until)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;
```

#### Tabla: `woo_quotation_items`
```sql
CREATE TABLE woo_quotation_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    quotation_id INT NOT NULL,

    -- Referencia al Producto
    product_id BIGINT NOT NULL,
    variation_id BIGINT DEFAULT 0,
    product_name VARCHAR(255) NOT NULL,
    product_sku VARCHAR(100),

    -- Precios (personalizables)
    quantity INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(10,2) NOT NULL,
    original_price DECIMAL(10,2),
    discount_percentage DECIMAL(5,2) DEFAULT 0.00,
    subtotal DECIMAL(10,2) NOT NULL,
    tax DECIMAL(10,2) DEFAULT 0.00,
    total DECIMAL(10,2) NOT NULL,

    -- Metadata
    notes TEXT,
    display_order INT DEFAULT 0,

    FOREIGN KEY (quotation_id) REFERENCES woo_quotations(id) ON DELETE CASCADE,
    INDEX idx_quotation_id (quotation_id),
    INDEX idx_product_id (product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;
```

#### Tabla: `woo_quotation_history`
```sql
CREATE TABLE woo_quotation_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    quotation_id INT NOT NULL,

    -- Rastreo de Cambios
    old_status VARCHAR(20),
    new_status VARCHAR(20) NOT NULL,
    changed_by VARCHAR(100) NOT NULL,
    change_reason VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (quotation_id) REFERENCES woo_quotations(id) ON DELETE CASCADE,
    INDEX idx_quotation_id (quotation_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;
```

### 1.2 Archivos a Crear/Modificar

**Nuevos Archivos:**
- `app/routes/quotations.py` (~500 líneas)
- `app/templates/quotations_list.html` (~300 líneas)
- `app/templates/quotations_create.html` (~600 líneas)
- `app/templates/quotations_detail.html` (~400 líneas)

**Modificar:**
- `app/models.py` (agregar 3 modelos)
- `app/__init__.py` (registrar blueprint)
- `app/templates/base.html` (agregar al sidebar)

---

## 2. CARACTERÍSTICAS PRINCIPALES

### 2.1 Gestión de Cotizaciones

- ✅ Crear cotización con wizard multi-paso
- ✅ Listar cotizaciones con filtros y paginación
- ✅ Ver detalle completo con historial
- ✅ Duplicar cotización (crear nueva basada en existente)
- ✅ Eliminar cotizaciones (solo borradores)

### 2.2 Productos y Precios

- ✅ Búsqueda de productos en tiempo real (AJAX)
- ✅ Sistema de carrito client-side
- ✅ **Precios personalizables** por cotización
- ✅ Muestra precio original + precio personalizado
- ✅ Descuentos por línea de producto

### 2.3 Estados de Cotización

| Estado | Descripción | Acciones Permitidas |
|--------|-------------|---------------------|
| `draft` | Borrador | Editar, Enviar, Eliminar, PDF |
| `sent` | Enviada | Aceptar, Rechazar, PDF, Duplicar |
| `accepted` | Aceptada | Convertir a Pedido, PDF, Duplicar |
| `rejected` | Rechazada | PDF, Duplicar |
| `expired` | Vencida | PDF, Duplicar |
| `converted` | Convertida a Pedido | PDF, Ver Pedido |

### 2.4 Restricciones de Edición

- ✅ **Solo se pueden editar borradores**
- ✅ Una vez enviada, no se puede editar
- ✅ Para modificar: duplicar y crear nueva
- ✅ Las convertidas son de solo lectura

### 2.5 Generación de PDF

- ✅ Descarga manual de PDF
- ✅ Layout profesional con logo
- ✅ Incluye: cliente, productos, totales, términos
- ❌ No envío automático por email

### 2.6 Conversión a Pedido

- ✅ **Botón manual** "Convertir a Pedido"
- ✅ Solo para cotizaciones aceptadas
- ✅ Requiere permisos de admin
- ✅ Crea orden real en WooCommerce
- ✅ Reduce inventario automáticamente
- ✅ Vincula orden con cotización

---

## 3. FLUJO DE TRABAJO

```
┌─────────────────┐
│ CREAR COTIZACIÓN│
└────────┬────────┘
         ↓
   ┌─────────────┐
   │  BORRADOR   │ ← Editable
   └─────┬───────┘
         ↓ Marcar como enviada
   ┌─────────────┐
   │   ENVIADA   │ ← Solo lectura
   └─────┬───────┘
         ↓ Cliente responde
   ┌─────┴──────┬──────────┐
   ↓            ↓          ↓
┌──────────┐ ┌──────────┐ ┌─────────┐
│ ACEPTADA │ │RECHAZADA │ │ VENCIDA │
└────┬─────┘ └──────────┘ └─────────┘
     ↓ Convertir a Pedido (admin)
┌────────────┐
│ CONVERTIDA │ → [PEDIDO WOOCOMMERCE]
└────────────┘
```

---

## 4. RUTAS Y ENDPOINTS

### 4.1 Vistas HTML

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/quotations/` | GET | Lista de cotizaciones |
| `/quotations/create` | GET | Formulario de creación |
| `/quotations/<id>` | GET | Detalle de cotización |
| `/quotations/<id>/edit` | GET | Editar (solo draft) |

### 4.2 APIs JSON

| Endpoint | Método | Descripción | Permisos |
|----------|--------|-------------|----------|
| `/quotations/api/quotations` | GET | Listar con filtros y paginación | login_required |
| `/quotations/api/quotations` | POST | Crear nueva cotización | login_required |
| `/quotations/api/quotations/<id>` | GET | Obtener detalle | login_required |
| `/quotations/api/quotations/<id>` | PUT | Actualizar (solo draft) | login_required |
| `/quotations/api/quotations/<id>/status` | PUT | Cambiar estado | login_required |
| `/quotations/api/quotations/<id>/duplicate` | POST | Duplicar cotización | login_required |
| `/quotations/api/quotations/<id>/convert` | POST | Convertir a pedido | admin_required |
| `/quotations/api/quotations/<id>/pdf` | GET | Generar PDF | login_required |
| `/quotations/api/check-expired` | GET | Marcar vencidas | login_required |
| `/quotations/api/stats` | GET | Estadísticas | login_required |

---

## 5. INTERFAZ DE USUARIO

### 5.1 Lista de Cotizaciones (`quotations_list.html`)

**Elementos:**
- Tabla con columnas:
  - Nº Cotización (link a detalle)
  - Cliente
  - Email
  - Fecha
  - Válido hasta (con indicador de vencimiento)
  - Total
  - Estado (badge con color)
  - Acciones (Ver, Editar, PDF, Duplicar)

**Filtros:**
- Estado (dropdown)
- Cliente (búsqueda)
- Rango de fechas

**Cards de Estadísticas:**
- Total Cotizaciones
- Borradores
- Enviadas
- Aceptadas
- Valor Total Aceptadas

**Paginación:** 20 por página

### 5.2 Crear Cotización (`quotations_create.html`)

**Wizard de 4 Pasos:**

#### Paso 1: Información del Cliente
```
- Nombre completo *
- Email *
- Teléfono *
- DNI/RUC
- Dirección
- Ciudad/Distrito
- Departamento
```

#### Paso 2: Selección de Productos
```
- Búsqueda de productos (AJAX)
- Tabla de productos:
  ┌─────┬────────────┬──────┬────────────┬──────────────┬──────────┬──────────┐
  │ SKU │  Producto  │ Cant │ Precio Org │ Precio Perso │ Desc. %  │ Subtotal │
  ├─────┼────────────┼──────┼────────────┼──────────────┼──────────┼──────────┤
  │     │            │  +/- │  S/ XX.XX  │  [EDITABLE]  │   XX%    │ S/ XX.XX │
  └─────┴────────────┴──────┴────────────┴──────────────┴──────────┴──────────┘
- Total en tiempo real
```

#### Paso 3: Precios y Términos
```
- Descuento global (% o monto fijo)
- Costo de envío
- Tasa de IGV (18%)
- Válido hasta (date picker, +15 días)
- Condiciones de pago (textarea)
- Tiempo de entrega (text)
- Términos y condiciones (textarea)
```

#### Paso 4: Revisión
```
- Resumen completo
- Tabla de productos
- Desglose de totales:
  Subtotal:        S/ X,XXX.XX
  Descuento (X%):  S/   XXX.XX
  Base Imponible:  S/ X,XXX.XX
  IGV (18%):       S/   XXX.XX
  Envío:           S/    XX.XX
  ═══════════════════════════
  TOTAL:           S/ X,XXX.XX
- Notas internas
- Botones: Guardar como Borrador, Cancelar
```

### 5.3 Detalle de Cotización (`quotations_detail.html`)

**Layout de 2 Columnas:**

**Columna Izquierda:**
1. Card "Información del Cliente"
2. Card "Productos" (tabla)
3. Card "Totales" (desglose)
4. Card "Términos y Condiciones"

**Columna Derecha:**
1. Card "Acciones" (botones según estado)
2. Card "Resumen" (estado, fechas, validez)
3. Card "Historial" (timeline de cambios)

**Botones según Estado:**

| Estado | Botones Disponibles |
|--------|---------------------|
| Draft | Editar, Marcar como Enviada, Eliminar, Descargar PDF |
| Sent | Aceptar, Rechazar, PDF, Duplicar |
| Accepted | **Convertir a Pedido** (admin), PDF, Duplicar |
| Rejected | PDF, Duplicar |
| Expired | PDF, Duplicar |
| Converted | Ver Pedido, PDF |

---

## 6. LÓGICA DE CONVERSIÓN A PEDIDO

### 6.1 Requisitos

- ✅ Cotización en estado "accepted"
- ✅ Usuario con rol admin
- ✅ Productos con stock suficiente

### 6.2 Proceso (Transacción Atómica)

```python
def convert_quotation_to_order(quotation_id):
    """
    1. Validar estado y permisos
    2. Crear orden en wpyz_wc_orders
       - Generar W-XXXXX
       - Status: wc-processing
       - Copiar datos de cliente
    3. Crear items en wpyz_woocommerce_order_items
       - Usar precios de cotización
    4. Crear direcciones en wpyz_wc_order_addresses
    5. Reducir stock de productos
    6. Actualizar cotización:
       - status = 'converted'
       - converted_order_id = nuevo_order_id
    7. Crear entrada en historial
    8. Commit transacción
    9. Return order_id
    """
```

### 6.3 Manejo de Errores

- Stock insuficiente → Rollback + mensaje de error
- Fallo en creación de orden → Rollback + log
- Producto eliminado → Rollback + mensaje

---

## 7. GENERACIÓN DE PDF

### 7.1 Biblioteca

**ReportLab** (ya usado en módulo de compras)

### 7.2 Estructura del PDF

```
┌─────────────────────────────────────────────┐
│ [LOGO]              COTIZACIÓN              │
│                                              │
│ Nº: COT-2025-001                             │
│ Fecha: 23/01/2025                            │
│ ⚠ Válido hasta: 07/02/2025                   │
├─────────────────────────────────────────────┤
│ CLIENTE:                                     │
│ Nombre: Juan Pérez                           │
│ Email: juan@example.com                      │
│ Teléfono: 987654321                          │
│ DNI: 12345678                                │
│ Dirección: Av. Principal 123, Lima           │
├─────────────────────────────────────────────┤
│ PRODUCTOS:                                   │
│ ┌───┬──────────┬────┬────────┬────┬────────┐│
│ │SKU│ Producto │Cant│ Precio │Desc│Subtotal││
│ ├───┼──────────┼────┼────────┼────┼────────┤│
│ │...│   ...    │... │  ...   │... │  ...   ││
│ └───┴──────────┴────┴────────┴────┴────────┘│
├─────────────────────────────────────────────┤
│ TOTALES:                                     │
│                                              │
│ Subtotal:           S/ 1,000.00              │
│ Descuento (10%):    S/   100.00              │
│                     ───────────              │
│ Base Imponible:     S/   900.00              │
│ IGV (18%):          S/   162.00              │
│ Envío:              S/    20.00              │
│                     ═══════════              │
│ TOTAL:              S/ 1,082.00              │
├─────────────────────────────────────────────┤
│ TÉRMINOS:                                    │
│                                              │
│ Condiciones de Pago:                         │
│ 50% adelanto, 50% contra entrega             │
│                                              │
│ Tiempo de Entrega:                           │
│ 5-7 días hábiles                             │
│                                              │
│ Términos y Condiciones:                      │
│ [Texto personalizado...]                     │
├─────────────────────────────────────────────┤
│ Generado por: mickstmt                       │
│ Fecha: 23/01/2025 14:30      Página 1 de 1  │
└─────────────────────────────────────────────┘
```

### 7.3 Configuración

```python
# Config para PDF
PDF_CONFIG = {
    'company_logo': 'app/static/images/logo.png',
    'company_name': 'Tu Empresa S.A.C.',
    'company_address': 'Av. Principal 123, Lima',
    'company_ruc': '20XXXXXXXXX',
    'company_phone': '+51 987 654 321',
    'company_email': 'ventas@empresa.com'
}
```

---

## 8. FASES DE IMPLEMENTACIÓN

### FASE 1: Base de Datos y Modelos
**Duración:** 2-3 horas

**Tareas:**
- [ ] Crear script SQL para tablas
- [ ] Agregar modelos a `app/models.py`:
  - [ ] Clase `Quotation`
  - [ ] Clase `QuotationItem`
  - [ ] Clase `QuotationHistory`
- [ ] Agregar métodos:
  - [ ] `to_dict()`
  - [ ] `is_expired()`
  - [ ] `calculate_totals()`
- [ ] Ejecutar migración en base de datos
- [ ] Probar relaciones con script de prueba

### FASE 2: Backend - Rutas Básicas
**Duración:** 3-4 horas

**Tareas:**
- [ ] Crear `app/routes/quotations.py`
- [ ] Implementar vistas HTML:
  - [ ] `index()` - Lista
  - [ ] `create()` - Crear
  - [ ] `detail()` - Detalle
  - [ ] `edit()` - Editar
- [ ] Implementar APIs básicas:
  - [ ] `api_get_quotations()` - GET /api/quotations
  - [ ] `api_create_quotation()` - POST /api/quotations
  - [ ] `api_get_quotation()` - GET /api/quotations/<id>
  - [ ] `api_update_quotation()` - PUT /api/quotations/<id>
- [ ] Registrar blueprint en `app/__init__.py`
- [ ] Probar endpoints con Postman

### FASE 3: Frontend - Lista y Detalle
**Duración:** 4-5 horas

**Tareas:**
- [ ] Crear `quotations_list.html`:
  - [ ] Estructura de página con cards de stats
  - [ ] Tabla de cotizaciones
  - [ ] Filtros (estado, cliente, fecha)
  - [ ] Paginación
  - [ ] AJAX para cargar datos
- [ ] Crear `quotations_detail.html`:
  - [ ] Layout de 2 columnas
  - [ ] Cards de información
  - [ ] Botones de acción (según estado)
  - [ ] Timeline de historial
- [ ] Agregar al sidebar en `base.html`:
  ```html
  <li class="nav-item">
      <a href="/quotations/" class="nav-link">
          <i class="bi bi-file-earmark-text"></i>
          <span>Cotizaciones</span>
      </a>
  </li>
  ```
- [ ] Probar navegación

### FASE 4: Frontend - Wizard de Creación
**Duración:** 5-6 horas

**Tareas:**
- [ ] Crear `quotations_create.html`:
  - [ ] Estructura de wizard (4 pasos)
  - [ ] Paso 1: Formulario de cliente
  - [ ] Paso 2: Búsqueda de productos (AJAX)
    - [ ] Integrar con `/orders/search-products`
    - [ ] Sistema de carrito client-side
    - [ ] Input de precio personalizable
    - [ ] Cálculo de descuento por línea
  - [ ] Paso 3: Términos y precios globales
  - [ ] Paso 4: Resumen y revisión
  - [ ] Navegación entre pasos
  - [ ] Validaciones de formulario
  - [ ] Cálculos en tiempo real
- [ ] JavaScript:
  - [ ] `calculateTotals()` - Calcular totales
  - [ ] `addProduct()` - Agregar al carrito
  - [ ] `removeProduct()` - Quitar del carrito
  - [ ] `updateQuantity()` - Actualizar cantidad
  - [ ] `submitQuotation()` - Enviar al backend
- [ ] Probar flujo completo de creación

### FASE 5: Generación de PDF
**Duración:** 3-4 horas

**Tareas:**
- [ ] Implementar `api_generate_pdf()` en backend:
  - [ ] Importar ReportLab
  - [ ] Crear layout del PDF
  - [ ] Agregar logo y header
  - [ ] Tabla de productos
  - [ ] Sección de totales
  - [ ] Términos y condiciones
  - [ ] Footer con metadata
- [ ] Configuración de empresa:
  - [ ] Logo path
  - [ ] Datos de empresa
- [ ] Probar descarga de PDF
- [ ] Validar formato y contenido

### FASE 6: Conversión a Pedido
**Duración:** 4-5 horas

**Tareas:**
- [ ] Implementar `api_convert_to_order()`:
  - [ ] Validar estado (accepted)
  - [ ] Validar permisos (admin)
  - [ ] Crear orden en `wpyz_wc_orders`
  - [ ] Generar order_number (W-XXXXX)
  - [ ] Crear items en `wpyz_woocommerce_order_items`
  - [ ] Crear direcciones en `wpyz_wc_order_addresses`
  - [ ] Reducir stock de productos
  - [ ] Actualizar cotización (status, order_id)
  - [ ] Crear registro en historial
  - [ ] Manejo de errores (rollback)
- [ ] Probar conversión end-to-end:
  - [ ] Crear cotización
  - [ ] Aceptar
  - [ ] Convertir
  - [ ] Verificar orden en WooCommerce
  - [ ] Verificar reducción de stock

### FASE 7: Funcionalidades Avanzadas
**Duración:** 3-4 horas

**Tareas:**
- [ ] Cambios de estado:
  - [ ] `api_update_status()` endpoint
  - [ ] Validaciones de transiciones
  - [ ] Botones en frontend
- [ ] Duplicar cotización:
  - [ ] `api_duplicate_quotation()` endpoint
  - [ ] Copiar datos + items
  - [ ] Nuevo quote_number
  - [ ] Nueva fecha de validez
- [ ] Expiración automática:
  - [ ] `api_check_expired()` endpoint
  - [ ] UPDATE query para marcar vencidas
  - [ ] Llamar al cargar lista
- [ ] Historial de cambios:
  - [ ] Crear registro en cada cambio de estado
  - [ ] Timeline en frontend
- [ ] Estadísticas:
  - [ ] `api_stats()` endpoint
  - [ ] Contadores por estado
  - [ ] Valor total aceptadas

### FASE 8: Testing y Refinamiento
**Duración:** 3-4 horas

**Tareas:**
- [ ] Pruebas end-to-end:
  - [ ] Crear → Enviar → Aceptar → Convertir
  - [ ] Crear → Rechazar
  - [ ] Crear → Expirar
  - [ ] Editar borrador
  - [ ] Duplicar cotización
- [ ] Pruebas de seguridad:
  - [ ] CSRF tokens
  - [ ] SQL injection
  - [ ] XSS prevention
  - [ ] Permisos de admin
- [ ] Optimización:
  - [ ] Queries N+1
  - [ ] Índices en BD
  - [ ] Caching de productos
- [ ] Corrección de bugs
- [ ] Documentación:
  - [ ] Comentarios en código
  - [ ] README del módulo

---

## 9. TIEMPO TOTAL ESTIMADO

| Fase | Duración |
|------|----------|
| Fase 1: DB y Modelos | 2-3 horas |
| Fase 2: Backend Básico | 3-4 horas |
| Fase 3: Frontend Lista/Detalle | 4-5 horas |
| Fase 4: Wizard Creación | 5-6 horas |
| Fase 5: PDF | 3-4 horas |
| Fase 6: Conversión | 4-5 horas |
| Fase 7: Avanzadas | 3-4 horas |
| Fase 8: Testing | 3-4 horas |
| **TOTAL** | **27-35 horas** |

**Equivalente:** 3-4 días de trabajo completo (8 horas/día)

---

## 10. SEGURIDAD Y VALIDACIONES

### 10.1 Backend (Flask)

```python
# Decoradores de seguridad
@bp.route('/...')
@login_required  # Todas las rutas
@admin_required  # Solo conversión a pedido

# Validaciones
- Email format (regex)
- Precios > 0
- Cantidades > 0
- valid_until > today
- Estado válido antes de editar/convertir
- Stock disponible antes de convertir

# Prevención
- SQL injection: usar ORM/parámetros
- CSRF: Flask-WTF tokens
- XSS: escape en templates
```

### 10.2 Frontend (JavaScript)

```javascript
// Validaciones en tiempo real
- Email válido (pattern)
- Números positivos
- Fechas futuras
- Campos requeridos

// UX
- Deshabilitar botón al enviar
- Mostrar spinner mientras procesa
- Mensajes de error claros
```

---

## 11. TEXTO EN ESPAÑOL

### 11.1 Estados

```python
STATUS_LABELS = {
    'draft': 'Borrador',
    'sent': 'Enviada',
    'accepted': 'Aceptada',
    'rejected': 'Rechazada',
    'expired': 'Vencida',
    'converted': 'Convertida'
}

STATUS_COLORS = {
    'draft': 'secondary',
    'sent': 'info',
    'accepted': 'success',
    'rejected': 'danger',
    'expired': 'warning',
    'converted': 'primary'
}
```

### 11.2 Etiquetas de Formulario

```
Cliente = Customer
Correo electrónico = Email
Teléfono = Phone
DNI/RUC = ID Number
Dirección = Address
Ciudad = City
Departamento = State/Province
Productos = Products
Cantidad = Quantity
Precio unitario = Unit Price
Precio original = Original Price
Precio personalizado = Custom Price
Descuento = Discount
Subtotal = Subtotal
IGV (18%) = Tax
Total = Total
Válido hasta = Valid Until
Condiciones de pago = Payment Terms
Tiempo de entrega = Delivery Time
Notas internas = Internal Notes
Términos y condiciones = Terms & Conditions
```

### 11.3 Botones y Acciones

```
Nueva Cotización = New Quotation
Guardar Borrador = Save Draft
Marcar como Enviada = Mark as Sent
Marcar como Aceptada = Mark as Accepted
Marcar como Rechazada = Mark as Rejected
Convertir a Pedido = Convert to Order
Descargar PDF = Download PDF
Duplicar Cotización = Duplicate Quotation
Editar = Edit
Eliminar = Delete
Ver Pedido = View Order
```

---

## 12. ARCHIVOS DE REFERENCIA

### Para Seguir Patrones Existentes

1. **app/routes/purchases.py**
   - Patrón de rutas y APIs
   - Status workflow
   - Generación de PDF
   - Paginación

2. **app/routes/orders.py**
   - API de búsqueda de productos
   - Sistema de carrito
   - Creación de órdenes WooCommerce

3. **app/templates/purchases_orders.html**
   - Layout de lista
   - Filtros y paginación
   - Cards de estadísticas

4. **app/templates/orders_create.html**
   - Wizard multi-paso
   - Búsqueda de productos
   - Cálculos en tiempo real

---

## 13. NOTAS FINALES

### ✅ Ventajas de este Diseño

- Sigue patrones existentes del codebase
- Reutiliza código (búsqueda de productos, etc.)
- Base de datos normalizada y eficiente
- Audit trail completo
- Seguro (validaciones + permisos)
- Escalable (fácil agregar funcionalidades)

### ⚠️ Consideraciones

- Requiere permisos de admin para conversión
- PDF básico (sin plantillas avanzadas)
- No envío automático de emails (futura mejora)
- Precios en soles (futura mejora: multi-moneda)

### 🔮 Mejoras Futuras (Post-MVP)

1. Email integration con plantillas
2. WhatsApp integration
3. Portal de cliente (aceptar/rechazar online)
4. Analytics dashboard
5. Templates de cotización
6. Multi-moneda
7. Workflow de aprobación

---

## 📞 SOPORTE

Para preguntas sobre la implementación:
- Revisar este documento
- Consultar archivos de referencia
- Probar en entorno local primero

---

**Última actualización:** 23 de Enero 2026
**Versión del documento:** 1.0
