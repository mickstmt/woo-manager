# Análisis: Manejo de SKUs Compuestos en Módulo de Compras

**Fecha:** 22 de diciembre de 2025
**Estado:** Pendiente de implementación
**Prioridad:** Media

---

## 📋 Problema Identificado

### Situación Actual

**Productos con SKUs compuestos:**
- `1007479-1007210-S10` = Correa Nylon 22mm Negro (`1007479`) + Conector Gold (`1007210`)
- `1007479-1007216-S10` = Correa Nylon 22mm Negro (`1007479`) + Conector Silver (`1007216`)
- `1007479-1007212-S10` = Correa Nylon 22mm Negro (`1007479`) + Conector Black (`1007212`)
- ... (8 productos en total)

**Problema:**
1. Cuando se agota un componente (correa O conector), se actualiza stock a 0 de TODOS los productos compuestos que lo contienen
2. Al generar orden de compra, el sistema **suma costos de TODOS los componentes** del SKU:
   - Ejemplo: `1007479-1007210-S10` → Costo = $2.20 (correa) + $0.73 (conector) = **$2.93** ❌
3. En realidad solo necesitas comprar el componente que se agotó:
   - Si se agotó la correa: Solo comprar `1007479` ($2.20) ✅
   - Si se agotó el conector: Solo comprar `1007210` ($0.73) ✅

**Restricción importante del cliente:**
> "No siempre se agotan solo las correas, también se agotan los conectores"

Por lo tanto, **NO podemos asumir** que siempre es el primer componente el que se agota.

---

## 🎯 Soluciones Propuestas

### **Opción 1: Identificar el Componente Principal por Posición**

❌ **DESCARTADA** - No aplica porque ambos componentes pueden agotarse

**Estrategia:** Asumir que el primer SKU en el compuesto es siempre el que se agota.

**Por qué NO funciona:**
- Cliente confirma que conectores también se agotan
- No hay forma de distinguir cuál componente causó el stock 0

---

### **Opción 2: Tabla de Configuración de Componentes Consumibles** ⭐

✅ **VIABLE** - Máxima flexibilidad pero requiere setup inicial

**Estructura propuesta:**

```sql
CREATE TABLE woo_sku_components (
    id INT AUTO_INCREMENT PRIMARY KEY,
    composite_sku VARCHAR(100) NOT NULL,      -- 1007479-1007210-S10
    component_sku VARCHAR(50) NOT NULL,        -- 1007479 o 1007210
    component_name VARCHAR(200),               -- "Correa Nylon Negro 22mm"
    is_consumable BOOLEAN DEFAULT TRUE,        -- TRUE si se puede agotar
    component_order INT DEFAULT 1,             -- Orden en el SKU (1, 2, 3...)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_composite (composite_sku),
    INDEX idx_component (component_sku),
    UNIQUE KEY unique_composite_component (composite_sku, component_sku)
);
```

**Lógica de cálculo de costos:**

```sql
-- Al calcular costo de un producto compuesto para orden de compra:
SELECT SUM(fc.FCLastCost)
FROM woo_products_fccost fc
INNER JOIN woo_sku_components sc
    ON fc.sku = sc.component_sku
WHERE sc.composite_sku = :product_sku
  AND sc.is_consumable = TRUE  -- Solo componentes marcados como consumibles
  AND LENGTH(fc.sku) = 7;
```

**Ventajas:**
- ✅ Permite marcar qué componentes de cada SKU son consumibles
- ✅ Flexibilidad total: puedes marcar solo correa, solo conector, o ambos
- ✅ Fácil de auditar y modificar
- ✅ Escalable para nuevos productos

**Desventajas:**
- ⚠️ Requiere crear y poblar nueva tabla manualmente
- ⚠️ Necesitas definir para cada producto compuesto sus componentes
- ⚠️ Mantenimiento: al agregar nuevos productos, hay que configurarlos

**Datos de ejemplo:**

```sql
INSERT INTO woo_sku_components (composite_sku, component_sku, component_name, is_consumable, component_order) VALUES
('1007479-1007210-S10', '1007479', 'Correa Nylon Negro 22mm', TRUE, 1),
('1007479-1007210-S10', '1007210', 'Conector Gold 22mm', TRUE, 2),
('1007479-1007216-S10', '1007479', 'Correa Nylon Negro 22mm', TRUE, 1),
('1007479-1007216-S10', '1007216', 'Conector Silver 22mm', TRUE, 2);
```

---

### **Opción 3: Regla por Longitud + Primer Componente**

❌ **DESCARTADA** - No aplica por misma razón que Opción 1

**Estrategia:** Solo considerar componentes de 7 caracteres que estén al inicio del SKU.

**Por qué NO funciona:**
- Asume que siempre el primer componente se agota
- Cliente confirmó que conectores (segundo componente) también se agotan

---

### **Opción 4: Campo "Componente Agotado" en Stock History** ⭐⭐

✅ **RECOMENDADA** - Precisión máxima y registro histórico

**Modificación de tabla existente:**

```sql
ALTER TABLE wpyz_stock_history
ADD COLUMN depleted_component VARCHAR(50) COMMENT 'SKU del componente que se agotó (para productos compuestos)',
ADD INDEX idx_depleted_component (depleted_component);
```

**Flujo de actualización de stock:**

Cuando el usuario actualiza stock a 0, debe especificar QUÉ componente se agotó:

```python
# Ejemplo: Se agotó la correa del producto 1007479-1007210-S10
StockHistory.create(
    product_id=35853,
    old_stock=10,
    new_stock=0,
    changed_by='Jleon',
    reason='Se agotó correa negra',
    depleted_component='1007479'  # ← NUEVO CAMPO
)
```

**Lógica de cálculo de costos:**

```sql
-- Al generar orden de compra, buscar qué componente se agotó
SELECT
    sh.depleted_component as sku_to_buy,
    fc.FCLastCost as unit_cost,
    fc.desc1 as description
FROM wpyz_stock_history sh
INNER JOIN woo_products_fccost fc
    ON sh.depleted_component = fc.sku
WHERE sh.product_id = :product_id
  AND sh.new_stock = 0
ORDER BY sh.created_at DESC
LIMIT 1;  -- Último cambio a stock 0
```

**Ventajas:**
- ✅ **Precisión absoluta**: Sabes exactamente qué comprar
- ✅ **Historial completo**: Auditable, sabes cuándo se agotó cada componente
- ✅ **No requiere tabla nueva**: Solo agregar columna
- ✅ **Funciona para productos simples y compuestos**: Si es simple, campo queda NULL
- ✅ **Información útil**: Puedes hacer análisis de qué componentes se agotan más

**Desventajas:**
- ⚠️ Requiere modificar UI de actualización de stock
- ⚠️ El usuario debe seleccionar qué componente se agotó (requiere un dropdown extra)
- ⚠️ Necesita capacitación del usuario

**Mockup de UI propuesta:**

```
┌─────────────────────────────────────────────────────┐
│ Actualizar Stock: 1007479-1007210-S10               │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Producto: Correa Nylon Negro 22mm + Conector Gold  │
│                                                     │
│ Stock actual: 10                                    │
│ Nuevo stock:  [0_]                                  │
│                                                     │
│ ¿Qué componente se agotó? *                        │
│ ┌─────────────────────────────────────────────┐   │
│ │ ▼ Seleccionar componente                    │   │
│ ├─────────────────────────────────────────────┤   │
│ │   1007479 - Correa Nylon Negro 22mm         │   │
│ │   1007210 - Conector Gold 22mm              │   │
│ │   Ambos componentes                         │   │
│ └─────────────────────────────────────────────┘   │
│                                                     │
│ Motivo: [Se terminó inventario de correas____]     │
│                                                     │
│         [Cancelar]  [Guardar Cambio]               │
└─────────────────────────────────────────────────────┘
```

---

### **Opción 5: Híbrido - Config + History** ⭐⭐⭐

✅ **MEJOR OPCIÓN** - Combina lo mejor de Opción 2 y 4

**Estrategia:**
1. Usar tabla `woo_sku_components` para **definir** qué componentes tiene cada producto
2. Usar campo `depleted_component` en `wpyz_stock_history` para **registrar** cuál se agotó

**Beneficios del enfoque híbrido:**

```sql
-- Query inteligente para cálculo de costos:
SELECT
    COALESCE(sh.depleted_component, sc.component_sku) as sku_to_buy,
    fc.FCLastCost as unit_cost
FROM woo_sku_components sc
LEFT JOIN wpyz_stock_history sh
    ON sh.product_id = :product_id
    AND sh.new_stock = 0
    AND sh.created_at = (
        SELECT MAX(created_at)
        FROM wpyz_stock_history
        WHERE product_id = :product_id AND new_stock = 0
    )
INNER JOIN woo_products_fccost fc
    ON fc.sku = COALESCE(sh.depleted_component, sc.component_sku)
WHERE sc.composite_sku = :product_sku
  AND sc.is_consumable = TRUE;
```

**Lógica:**
1. Si hay registro en `stock_history` con `depleted_component` → Usar ese ✅
2. Si NO hay registro → Usar TODOS los componentes marcados como consumibles en `woo_sku_components`
3. Permite que el usuario sea específico, pero también funciona sin modificar UI

**Ventajas combinadas:**
- ✅ Funciona CON o SIN especificar componente agotado
- ✅ Migración gradual: implementar tabla primero, luego UI opcional
- ✅ Fallback inteligente
- ✅ Máxima precisión cuando se especifica

---

## 📊 Comparación de Opciones

| Criterio | Opción 2: Tabla Config | Opción 4: History Field | Opción 5: Híbrido |
|----------|------------------------|-------------------------|-------------------|
| Precisión | ⭐⭐⭐ Media | ⭐⭐⭐⭐⭐ Máxima | ⭐⭐⭐⭐⭐ Máxima |
| Facilidad implementación | ⭐⭐ Media | ⭐⭐⭐ Media-Alta | ⭐⭐ Media |
| Cambios en UI | ❌ No requiere | ✅ Requiere | ⭐ Opcional |
| Mantenimiento | ⭐⭐ Manual | ⭐⭐⭐⭐ Automático | ⭐⭐⭐ Semi-auto |
| Historial | ❌ No | ✅ Sí | ✅ Sí |
| Flexibilidad | ⭐⭐⭐ Alta | ⭐⭐⭐⭐ Muy Alta | ⭐⭐⭐⭐⭐ Máxima |

---

## 🏆 Recomendación Final

### **Implementar Opción 5 (Híbrido) en 2 fases:**

### **Fase 1 (Corto plazo - 2 horas):**
1. Crear tabla `woo_sku_components`
2. Poblar con productos actuales (script de migración)
3. Modificar query de costos para usar la tabla
4. **Resultado:** Funcionalidad básica operativa, suma TODOS los componentes consumibles

### **Fase 2 (Mediano plazo - 4 horas):**
1. Agregar columna `depleted_component` a `wpyz_stock_history`
2. Modificar UI de actualización de stock para incluir selector de componente
3. Actualizar query para priorizar `depleted_component` si existe
4. **Resultado:** Precisión máxima, usuario especifica qué se agotó

### **Fase 3 (Opcional - Futuro):**
1. Dashboard de análisis: ¿Qué componentes se agotan más?
2. Predicción de compras basada en historial
3. Alertas automáticas de reabastecimiento

---

## 💡 Script de Migración Propuesto (Fase 1)

```sql
-- 1. Crear tabla
CREATE TABLE woo_sku_components (
    id INT AUTO_INCREMENT PRIMARY KEY,
    composite_sku VARCHAR(100) NOT NULL,
    component_sku VARCHAR(50) NOT NULL,
    component_name VARCHAR(200),
    is_consumable BOOLEAN DEFAULT TRUE,
    component_order INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_composite (composite_sku),
    INDEX idx_component (component_sku),
    UNIQUE KEY unique_composite_component (composite_sku, component_sku)
);

-- 2. Poblar automáticamente con productos existentes que tengan SKU compuesto
INSERT INTO woo_sku_components (composite_sku, component_sku, component_order, is_consumable)
SELECT DISTINCT
    pm.meta_value as composite_sku,
    fc.sku as component_sku,
    CASE
        WHEN pm.meta_value LIKE CONCAT(fc.sku, '%') THEN 1  -- Primer componente
        ELSE 2  -- Segundo componente
    END as component_order,
    TRUE as is_consumable
FROM wpyz_postmeta pm
INNER JOIN woo_products_fccost fc
    ON pm.meta_value COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
WHERE pm.meta_key = '_sku'
  AND pm.meta_value LIKE '%-%'  -- Solo SKUs compuestos
  AND LENGTH(fc.sku) = 7
ORDER BY pm.meta_value, component_order;
```

---

## 📝 Notas Adicionales

### Consideraciones de UX (Fase 2):

1. **Selector inteligente**: Al actualizar stock a 0, mostrar dropdown con componentes del producto
2. **Opcional pero recomendado**: Si el usuario NO selecciona, usar todos los componentes marcados como consumibles
3. **Validación**: Si selecciona "Ambos", registrar entrada separada en history para cada componente

### Casos edge:

1. **¿Qué pasa si un SKU simple se marca como 0?**
   - `depleted_component` queda NULL
   - Query de costos usa el SKU completo directamente
   - No afecta funcionalidad actual

2. **¿Qué pasa si se agrega un nuevo tipo de componente (3 partes)?**
   - Agregar filas a `woo_sku_components` con `component_order = 3`
   - Sistema automáticamente lo incluye en cálculos

3. **¿Qué pasa con productos antiguos sin configuración?**
   - Script de migración los detecta y configura automáticamente
   - Fallback: si no existe en `woo_sku_components`, usar lógica actual (LIKE con %)

---

## ⏰ Estimación de Esfuerzo

| Fase | Tarea | Tiempo | Prioridad |
|------|-------|--------|-----------|
| 1 | Crear tabla `woo_sku_components` | 30 min | Alta |
| 1 | Script de migración/población | 45 min | Alta |
| 1 | Modificar query de costos | 45 min | Alta |
| 2 | Agregar campo `depleted_component` | 15 min | Media |
| 2 | Modificar UI de stock update | 2 horas | Media |
| 2 | Actualizar query híbrido | 30 min | Media |
| 2 | Testing e2e | 1 hora | Media |
| 3 | Dashboard de análisis | 3 horas | Baja |

**Total Fase 1:** ~2 horas
**Total Fase 1+2:** ~6 horas
**Total completo:** ~9 horas

---

## 🔍 Ejemplos de Funcionamiento

### Escenario 1: Se agota correa (Fase 1)
```
Producto: 1007479-1007210-S10
Stock: 10 → 0
Usuario: Jleon

Sin selector (Fase 1):
└─ Sistema busca en woo_sku_components
   └─ Encuentra: 1007479 (consumible) + 1007210 (consumible)
   └─ Costo orden: $2.20 + $0.73 = $2.93 ⚠️
```

### Escenario 2: Se agota correa (Fase 2)
```
Producto: 1007479-1007210-S10
Stock: 10 → 0
Usuario: Jleon selecciona "1007479 - Correa"

Con selector (Fase 2):
└─ Registra: depleted_component = '1007479'
└─ Sistema busca en stock_history
   └─ Encuentra: 1007479
   └─ Costo orden: $2.20 ✅
```

### Escenario 3: Se agotan ambos
```
Producto: 1007479-1007210-S10
Stock: 10 → 0
Usuario: Jleon selecciona "Ambos componentes"

└─ Registra: depleted_component = '1007479,1007210' (CSV)
└─ O dos registros separados en history
└─ Costo orden: $2.20 + $0.73 = $2.93 ✅
```

---

## ✅ Checklist de Implementación

### Fase 1:
- [ ] Crear tabla `woo_sku_components`
- [ ] Ejecutar script de población inicial
- [ ] Verificar datos poblados correctamente
- [ ] Modificar función de cálculo de costos en `purchases.py`
- [ ] Probar con productos existentes
- [ ] Validar que órdenes muestren costos correctos
- [ ] Commit con mensaje descriptivo

### Fase 2:
- [ ] Agregar columna `depleted_component` a `wpyz_stock_history`
- [ ] Actualizar modelo `StockHistory` en `models.py`
- [ ] Modificar template de actualización de stock
- [ ] Agregar lógica JS para cargar componentes por AJAX
- [ ] Actualizar endpoint de actualización de stock
- [ ] Modificar query híbrido en `purchases.py`
- [ ] Testing end-to-end completo
- [ ] Documentación de usuario
- [ ] Commit con mensaje descriptivo

---

**Documento creado:** 2025-12-22
**Última actualización:** 2025-12-22
**Autor:** Claude (Asistente IA)
**Revisado por:** Pendiente
**Estado:** Análisis completado, pendiente de decisión e implementación
