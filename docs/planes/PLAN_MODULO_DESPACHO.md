# Plan de Implementación: Módulo de Despacho Kanban

**Proyecto:** WooCommerce Manager - Módulo de Despacho
**Usuario Objetivo:** Jleon (Master)
**Fecha de Creación:** 2025-12-23
**Metodología:** Kanban Visual con Drag & Drop

---

## 📋 Resumen Ejecutivo

Implementar un módulo de gestión visual de despachos tipo tablero Kanban, organizado por **método de envío** (no por estados), donde cada columna representa un courier o método de entrega diferente. Los pedidos se pueden mover entre columnas mediante drag & drop para reasignar el método de envío.

---

## 🎯 Objetivos del Módulo

1. **Visualización Clara:** Tablero Kanban con pedidos organizados por método de envío
2. **Gestión Ágil:** Drag & drop para reasignar métodos de envío rápidamente
3. **Trazabilidad:** Historial completo de cambios con usuario y timestamp
4. **Alertas Proactivas:** Notificaciones para pedidos estancados y prioritarios
5. **Control de Acceso:** Exclusivo para usuario master Jleon

---

## 📊 Especificaciones Funcionales

### 1. Estructura del Tablero Kanban

**Columnas (Métodos de Envío):**
- 🚚 Olva Courier
- 🏪 Recojo en Almacén
- 🏍️ Motorizado (CHAMO)
- 📦 SHALOM
- 🚛 DINSIDES

**Tarjetas de Pedido (Información Básica):**
- Número de pedido (W-00001)
- Nombre del cliente
- Total del pedido (S/)
- Badge de prioridad (si aplica)
- Indicador de tiempo sin mover

### 2. Funcionalidades Core

#### A. Drag & Drop
- Arrastrar pedidos entre columnas para cambiar método de envío
- Actualización automática en base de datos
- Confirmación visual del cambio
- Registro en historial con timestamp

#### B. Filtros
- **Por fecha de pedido:** Selector de rango de fechas
- **Por método de envío:** Mostrar/ocultar columnas específicas
- **Por urgencia/prioridad:** Solo pedidos prioritarios

#### C. Acciones en Tarjetas
- **Ver detalle completo:** Modal con toda la información del pedido
- **Marcar como prioritario:** Badge rojo/naranja visible
- **Agregar nota de despacho:** Comentarios sobre el envío

#### D. Notificaciones
- **Pedidos estancados:** Alerta si llevan >24h sin mover
- **Pedidos prioritarios nuevos:** Notificación cuando ingresa uno nuevo

### 3. Permisos y Acceso

- **Usuario exclusivo:** Solo Jleon (role: master)
- **Ruta protegida:** `/dispatch` o `/despacho`
- **Middleware de autorización:** Verificar role antes de acceder

---

## 🗄️ Diseño de Base de Datos

### Nueva Tabla: `woo_dispatch_history`

```sql
CREATE TABLE woo_dispatch_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_id BIGINT NOT NULL,
    order_number VARCHAR(50) NOT NULL,

    -- Cambio de método de envío
    previous_shipping_method VARCHAR(100),
    new_shipping_method VARCHAR(100) NOT NULL,

    -- Trazabilidad
    changed_by VARCHAR(100) NOT NULL,
    changed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Notas
    dispatch_note TEXT,

    -- Índices
    INDEX idx_order_id (order_id),
    INDEX idx_order_number (order_number),
    INDEX idx_changed_at (changed_at),

    FOREIGN KEY (order_id) REFERENCES wpyz_wc_orders(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;
```

### Nueva Tabla: `woo_dispatch_priorities`

```sql
CREATE TABLE woo_dispatch_priorities (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_id BIGINT NOT NULL UNIQUE,
    order_number VARCHAR(50) NOT NULL,

    -- Prioridad
    is_priority BOOLEAN DEFAULT FALSE,
    priority_level ENUM('normal', 'high', 'urgent') DEFAULT 'normal',

    -- Metadata
    marked_by VARCHAR(100),
    marked_at DATETIME,
    priority_note TEXT,

    -- Índices
    INDEX idx_order_id (order_id),
    INDEX idx_is_priority (is_priority),

    FOREIGN KEY (order_id) REFERENCES wpyz_wc_orders(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;
```

---

## 🏗️ Arquitectura de Implementación

### Backend (Flask)

#### Nuevos Archivos

1. **`app/routes/dispatch.py`** - Blueprint principal del módulo
   - `GET /dispatch` - Render del tablero
   - `GET /api/dispatch/orders` - Obtener pedidos agrupados por método
   - `POST /api/dispatch/move` - Mover pedido a otra columna
   - `POST /api/dispatch/priority` - Marcar/desmarcar prioridad
   - `POST /api/dispatch/note` - Agregar nota de despacho
   - `GET /api/dispatch/history/<order_id>` - Historial de cambios

2. **`app/models.py`** - Nuevos modelos
   - `class DispatchHistory(db.Model)`
   - `class DispatchPriority(db.Model)`

#### Middleware de Autorización

```python
from functools import wraps
from flask import abort
from flask_login import current_user

def master_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'master':
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function
```

### Frontend (HTML/JS)

#### Nuevos Archivos

1. **`app/templates/dispatch_board.html`** - Vista principal del tablero
2. **`app/static/js/dispatch.js`** - Lógica del Kanban
3. **`app/static/css/dispatch.css`** - Estilos del tablero

#### Librerías Necesarias

- **SortableJS** o **dragula.js** - Para drag & drop
- **Bootstrap Modals** - Para detalles y notas
- **Toastr** o **SweetAlert2** - Para notificaciones

---

## 📅 Plan de Desarrollo (Fases)

### **FASE 1: Infraestructura Base** ⏱️ 2-3 días

**Objetivo:** Preparar base de datos, modelos y estructura básica

- [ ] 1.1 Crear tablas `woo_dispatch_history` y `woo_dispatch_priorities`
- [ ] 1.2 Crear modelos SQLAlchemy en `app/models.py`
- [ ] 1.3 Crear blueprint `app/routes/dispatch.py`
- [ ] 1.4 Implementar middleware `@master_required`
- [ ] 1.5 Registrar blueprint en `app/__init__.py`
- [ ] 1.6 Crear ruta protegida `/dispatch`

**Entregable:** Estructura base funcional con acceso restringido

---

### **FASE 2: API Backend** ⏱️ 3-4 días

**Objetivo:** Endpoints para gestión de pedidos en el tablero

- [ ] 2.1 **GET `/api/dispatch/orders`**
  - Consultar pedidos con status `wc-processing`
  - Agrupar por método de envío (`shipping_method_title`)
  - Incluir info básica: número, cliente, total
  - Marcar pedidos estancados (>24h sin cambios)
  - Incluir flag de prioridad

- [ ] 2.2 **POST `/api/dispatch/move`**
  - Recibir: `order_id`, `new_shipping_method`
  - Actualizar método de envío en `wpyz_wc_orders`
  - Registrar en historial `woo_dispatch_history`
  - Retornar confirmación

- [ ] 2.3 **POST `/api/dispatch/priority`**
  - Recibir: `order_id`, `is_priority`, `priority_level`, `note`
  - Insertar/actualizar en `woo_dispatch_priorities`
  - Retornar confirmación

- [ ] 2.4 **POST `/api/dispatch/note`**
  - Recibir: `order_id`, `note`
  - Registrar en `woo_dispatch_history`
  - Retornar confirmación

- [ ] 2.5 **GET `/api/dispatch/history/<order_id>`**
  - Obtener historial completo de cambios
  - Ordenar por fecha descendente
  - Incluir usuario y timestamp

**Entregable:** API completa documentada y testeada

---

### **FASE 3: Frontend - Vista Básica** ⏱️ 3-4 días

**Objetivo:** Tablero Kanban visual sin drag & drop (versión estática)

- [ ] 3.1 Crear template `dispatch_board.html`
  - Layout de 5 columnas (métodos de envío)
  - Header con filtros (fecha, prioridad)
  - Contador de pedidos por columna

- [ ] 3.2 Renderizar tarjetas de pedidos
  - Número de pedido
  - Nombre de cliente
  - Total (S/)
  - Badge de prioridad (si aplica)
  - Tiempo sin mover (color rojo si >24h)

- [ ] 3.3 Modal de detalle de pedido
  - Información completa del pedido
  - Productos y cantidades
  - Datos de cliente y envío
  - Botón para marcar prioritario
  - Formulario para agregar nota

- [ ] 3.4 Implementar filtros
  - Selector de fecha (date range)
  - Toggle para ver solo prioritarios
  - Toggle para mostrar/ocultar columnas

**Entregable:** Vista funcional con información estática

---

### **FASE 4: Drag & Drop** ⏱️ 2-3 días

**Objetivo:** Implementar arrastre de tarjetas entre columnas

- [ ] 4.1 Integrar librería SortableJS
- [ ] 4.2 Configurar drag & drop entre columnas
- [ ] 4.3 Implementar callback de drop
  - Llamar a `/api/dispatch/move`
  - Actualizar UI optimísticamente
  - Mostrar confirmación/error

- [ ] 4.4 Restricciones y validaciones
  - Confirmar antes de mover (opcional)
  - Manejar errores de red
  - Rollback visual si falla

**Entregable:** Drag & drop funcional con actualización en BD

---

### **FASE 5: Notificaciones y Alertas** ⏱️ 2 días

**Objetivo:** Sistema de alertas proactivas

- [ ] 5.1 Indicador visual de pedidos estancados
  - Badge rojo si >24h sin mover
  - Tooltip con tiempo exacto

- [ ] 5.2 Notificación de pedidos prioritarios nuevos
  - Polling cada 30 segundos
  - Toast notification
  - Sonido opcional

- [ ] 5.3 Resumen en header
  - Total de pedidos
  - Pedidos prioritarios
  - Pedidos estancados

**Entregable:** Sistema de alertas funcionando

---

### **FASE 6: Historial y Trazabilidad** ⏱️ 1-2 días

**Objetivo:** Visualización de historial de cambios

- [ ] 6.1 Timeline de cambios en modal de detalle
  - Lista cronológica de movimientos
  - Usuario que hizo el cambio
  - Fecha y hora
  - Método anterior → nuevo

- [ ] 6.2 Notas de despacho en timeline
  - Mostrar notas junto con cambios
  - Diferenciar visualmente

**Entregable:** Historial completo visible

---

### **FASE 7: Testing y Refinamiento** ⏱️ 2-3 días

**Objetivo:** Pruebas completas y ajustes finales

- [ ] 7.1 Testing funcional
  - Drag & drop en diferentes navegadores
  - Filtros y búsquedas
  - Modales y formularios

- [ ] 7.2 Testing de permisos
  - Verificar acceso solo para Jleon
  - 403 para otros usuarios

- [ ] 7.3 Testing de performance
  - Optimizar queries con muchos pedidos
  - Lazy loading si es necesario

- [ ] 7.4 UX/UI refinamiento
  - Responsive design
  - Animaciones suaves
  - Feedback visual claro

**Entregable:** Módulo completo, testeado y optimizado

---

### **FASE 8: Documentación y Deployment** ⏱️ 1 día

**Objetivo:** Documentar y desplegar a producción

- [ ] 8.1 Documentación técnica
  - README del módulo
  - Comentarios en código
  - Diagramas de flujo

- [ ] 8.2 Manual de usuario
  - Cómo usar el tablero
  - Shortcuts y tips

- [ ] 8.3 Deploy a producción
  - Migración de base de datos
  - Deploy de código
  - Verificación en producción

**Entregable:** Módulo en producción documentado

---

## 📐 Wireframes y Diseño

### Layout del Tablero

```
┌─────────────────────────────────────────────────────────────────┐
│  🚚 Módulo de Despacho                   [Filtros: 📅 🎯 🔍]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐      │
│  │Olva (5)  │Recojo(3) │CHAMO (2) │SHALOM(4) │DINSID(1) │      │
│  ├──────────┼──────────┼──────────┼──────────┼──────────┤      │
│  │┌────────┐│┌────────┐│┌────────┐│┌────────┐│┌────────┐│      │
│  ││W-00050 ││││W-00048 ││││W-00051 ││││W-00045 ││││W-00052 ││      │
│  ││Juan P. ││││María G.││││Carlos L││││Ana M. ││││Luis R. ││      │
│  ││S/125.00││││S/89.50 ││││S/210.00││││S/145.00││││S/95.00 ││      │
│  ││⭐ URGENTE││        ││││        ││││🔴 24h+││││        ││      │
│  │└────────┘││└────────┘││└────────┘││└────────┘││└────────┘│      │
│  │          ││          ││          ││          ││          │      │
│  │┌────────┐││┌────────┐││┌────────┐││┌────────┐││          │      │
│  ││W-00049 ││││W-00047 ││││W-00046 ││││W-00044 ││││          │      │
│  ││...     ││││...     ││││...     ││││...     ││││          │      │
│  │└────────┘││└────────┘││└────────┘││└────────┘││          │      │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Modal de Detalle

```
┌─────────────────────────────────────────┐
│  Pedido W-00050              [X]        │
├─────────────────────────────────────────┤
│                                         │
│  👤 Cliente: Juan Pérez                 │
│  📞 Teléfono: 987654321                 │
│  📧 Email: juan@example.com             │
│  📍 Dirección: Av. Principal 123, Lima  │
│                                         │
│  🛒 Productos:                          │
│  • Apple Watch Series 10 (x1) - S/899   │
│  • Correa Metal (x1) - S/89            │
│                                         │
│  💰 Total: S/988.00                     │
│  🚚 Envío: Olva Courier - S/15.00      │
│                                         │
│  [⭐ Marcar Prioritario]                │
│                                         │
│  📝 Notas de Despacho:                  │
│  ┌─────────────────────────────────┐   │
│  │ Agregar nota...                 │   │
│  └─────────────────────────────────┘   │
│  [Guardar Nota]                         │
│                                         │
│  📜 Historial de Cambios:               │
│  • 23/12/2025 15:30 - Movido a Olva    │
│    por: Jleon                           │
│  • 23/12/2025 14:00 - Pedido creado    │
│    por: Maria                           │
│                                         │
└─────────────────────────────────────────┘
```

---

## 🔧 Stack Tecnológico

### Backend
- **Framework:** Flask (Python)
- **ORM:** SQLAlchemy
- **Base de datos:** MySQL
- **Autenticación:** Flask-Login

### Frontend
- **HTML/CSS:** Bootstrap 5
- **JavaScript:** Vanilla JS + jQuery
- **Drag & Drop:** SortableJS (https://sortablejs.github.io/Sortable/)
- **Notificaciones:** Toastr (https://codeseven.github.io/toastr/)
- **Iconos:** Bootstrap Icons

---

## ⚠️ Consideraciones Importantes

### Performance
- Limitar pedidos mostrados a últimos 30 días por defecto
- Implementar paginación o lazy loading si >100 pedidos
- Cachear contadores de columnas

### UX/UI
- Animaciones suaves en drag & drop (200-300ms)
- Feedback visual inmediato al soltar tarjeta
- Loading spinners durante operaciones de red
- Mensajes de error claros y amigables

### Seguridad
- Validar en backend que usuario es master
- CSRF tokens en todos los POST
- Sanitizar inputs de notas
- Rate limiting en endpoints de cambio

### Escalabilidad
- Diseñar pensando en múltiples usuarios (futuro)
- Estructura de permisos extensible
- Logs de auditoría completos

---

## 📊 Métricas de Éxito

- ✅ Usuario Jleon puede ver todos los pedidos organizados por método de envío
- ✅ Puede mover pedidos entre columnas con drag & drop
- ✅ Los cambios se registran correctamente en base de datos
- ✅ Recibe alertas de pedidos estancados y prioritarios
- ✅ Puede ver historial completo de cada pedido
- ✅ Módulo carga en <2 segundos con 50 pedidos
- ✅ Compatible con Chrome, Firefox, Safari, Edge

---

## 🚀 Estimación Total

**Tiempo total estimado:** 16-21 días laborables (3-4 semanas)

**Distribución:**
- Backend (Fases 1-2): 5-7 días
- Frontend (Fases 3-4): 5-7 días
- Features avanzados (Fases 5-6): 3-4 días
- Testing y deployment (Fases 7-8): 3-4 días

---

## 📝 Notas Adicionales

### Extensiones Futuras (Fuera de Scope Inicial)

1. **Impresión de guías:** PDF con código de barras para couriers
2. **Integración con APIs de couriers:** Tracking automático
3. **Estadísticas de despacho:** Dashboard con métricas
4. **Múltiples usuarios:** Expandir acceso a otros roles
5. **App móvil:** Para escaneo de productos en despacho
6. **WhatsApp notifications:** Avisar a clientes automáticamente

### Dependencias

- No hay dependencias bloqueantes con otros módulos
- Reutiliza infraestructura existente (auth, modelos, templates)
- Compatible con estructura actual del proyecto

---

## ✅ Checklist Pre-Inicio

Antes de comenzar la implementación, verificar:

- [ ] Acceso a base de datos de producción para crear tablas
- [ ] Usuario Jleon confirmado como 'master' en tabla `woo_users`
- [ ] Ambiente de desarrollo configurado y funcionando
- [ ] Backup de base de datos realizado
- [ ] Plan revisado y aprobado por usuario

---

**Última actualización:** 2025-12-23
**Estado:** Planificación completa - Listo para implementar
**Próximo paso:** Iniciar Fase 1 - Infraestructura Base
