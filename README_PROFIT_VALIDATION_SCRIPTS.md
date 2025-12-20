# Scripts de Validación de Márgenes de Ganancia

## 📋 Descripción General

Este conjunto de scripts SQL te permite validar los cálculos de márgenes de ganancia directamente en la base de datos MySQL, sin necesidad de la aplicación web. Son ideales para:

- ✅ Validar que los cálculos del módulo web sean correctos
- 📊 Exportar datos a CSV para análisis externos (Excel, Google Sheets, etc.)
- 🔍 Debugging cuando los números no cuadran
- 📈 Análisis ad-hoc de rentabilidad

**✨ IMPORTANTE:** Estos scripts incluyen **TODOS los pedidos** de `wpyz_wc_orders`:
- ✅ Pedidos naturales de WooCommerce (creados en la tienda web)
- ✅ Pedidos de WhatsApp (creados vía WooCommerce Manager)
- ❌ NO incluye pedidos externos de `woo_orders_ext`

## 📁 Archivos Incluidos

### 1. `query_profit_margins_validation.sql`
**Propósito:** Vista principal de ganancias por pedido

**Columnas principales:**
- Información del pedido (ID, número, fecha, estado)
- Cliente (nombre, email, teléfono)
- Totales de venta en PEN
- Costos de productos en USD y PEN
- Costos de envío en PEN
- Ganancia neta en PEN
- Margen porcentual
- Método de pago
- Usuario que creó el pedido

**Cuándo usar:** Para validar el reporte principal de ganancias, similar a lo que ves en `/reports/profits`

---

### 2. `query_profit_margins_by_product.sql`
**Propósito:** Ganancias agrupadas por producto

**Columnas principales:**
- Nombre y SKU del producto
- Total de pedidos que contienen el producto
- Cantidad total vendida
- Costo unitario en USD
- Tipo de cambio promedio
- Ventas totales, costos totales y ganancia total en PEN
- Margen porcentual

**Cuándo usar:** Para identificar qué productos son más rentables o tienen márgenes bajos

---

### 3. `query_profit_margins_detailed.sql`
**Propósito:** Detalle línea por línea (cada producto en cada pedido)

**Columnas principales:**
- Información del pedido
- Información del producto (incluyendo ID de variación)
- Cantidad, precio unitario, subtotal
- Costos unitarios y totales (USD y PEN)
- Ganancia por línea
- Margen porcentual por línea
- Flags de validación (tiene_sku, tiene_costo)

**Cuándo usar:** Para debugging granular, cuando necesitas ver exactamente qué está pasando con cada producto en cada pedido

---

### 4. `query_profit_margins_summary.sql`
**Propósito:** Resumen ejecutivo del período completo

**Columnas principales:**
- Total de pedidos (general, completados, en proceso)
- Ventas totales y ticket promedio
- Tipo de cambio promedio del período
- Costos totales (productos y envío)
- Ganancia neta total
- Margen promedio porcentual
- Ganancia promedio por pedido

**Cuándo usar:** Para validar los totales del dashboard, retorna UNA sola fila con todas las métricas clave

---

## 🚀 Cómo Usar los Scripts

### Opción 1: MySQL Workbench (Recomendado)

1. Abre MySQL Workbench
2. Conéctate a tu base de datos
3. Abre el archivo `.sql` que quieras ejecutar
4. **IMPORTANTE:** Modifica las fechas en la cláusula `WHERE`:
   ```sql
   DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) BETWEEN '2024-12-01' AND '2024-12-31'
   ```
5. Ejecuta el query (⚡ o Ctrl+Enter)
6. Para exportar a CSV:
   - Click derecho en los resultados
   - Export → Export to CSV
   - Guarda el archivo

### Opción 2: phpMyAdmin

1. Accede a phpMyAdmin
2. Selecciona tu base de datos
3. Ve a la pestaña "SQL"
4. Pega el contenido del script
5. **Modifica las fechas** según tu necesidad
6. Click en "Ejecutar"
7. Para exportar: Click en "Exportar" → Formato CSV

### Opción 3: Línea de comandos MySQL

```bash
mysql -u tu_usuario -p tu_base_datos < query_profit_margins_validation.sql > resultados.csv
```

---

## ⚙️ Personalización de Fechas

Todos los scripts tienen esta línea que debes modificar según tus necesidades:

```sql
-- Ejemplo 1: Mes completo de diciembre 2024
DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) BETWEEN '2024-12-01' AND '2024-12-31'

-- Ejemplo 2: Último trimestre de 2024
DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) BETWEEN '2024-10-01' AND '2024-12-31'

-- Ejemplo 3: Año completo 2024
DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) BETWEEN '2024-01-01' AND '2024-12-31'

-- Ejemplo 4: Una semana específica
DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) BETWEEN '2024-12-01' AND '2024-12-07'
```

**⚠️ NOTA IMPORTANTE:** Los scripts usan `DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)` para convertir de UTC a hora de Perú (UTC-5). NO modifiques esta parte.

---

## 🔍 Escenarios de Uso Comunes

### Escenario 1: Validar totales del mes
1. Usa `query_profit_margins_summary.sql`
2. Modifica las fechas para el mes que quieres validar
3. Ejecuta y compara con el dashboard web
4. Los valores deben coincidir exactamente

### Escenario 2: Identificar productos poco rentables
1. Usa `query_profit_margins_by_product.sql`
2. Ordena por `margen_porcentaje ASC` (de menor a mayor)
3. Los primeros resultados son los menos rentables
4. Considera ajustar precios o costos

### Escenario 3: Debugging de un pedido específico
1. Usa `query_profit_margins_detailed.sql`
2. Agrega en el WHERE: `AND o.id = 12345` (el ID del pedido)
3. Verás línea por línea qué está pasando
4. Revisa las columnas `tiene_sku` y `tiene_costo`

### Escenario 4: Exportar para análisis en Excel
1. Elige el script según lo que necesites
2. Ejecuta en MySQL Workbench
3. Exporta a CSV
4. Abre en Excel/Google Sheets
5. Crea tablas dinámicas y gráficos

### Escenario 5: Comparar períodos
1. Ejecuta el mismo script dos veces
2. Primera vez: fechas del período 1 (ej: Noviembre)
3. Segunda vez: fechas del período 2 (ej: Diciembre)
4. Exporta ambos a CSV
5. Compara en Excel

---

## 📊 Interpretación de Resultados

### Valores de Margen Porcentual

- **> 30%:** Excelente margen, producto muy rentable 🟢
- **20-30%:** Buen margen, rentabilidad saludable 🟢
- **10-20%:** Margen aceptable, monitorear 🟡
- **5-10%:** Margen bajo, revisar precios/costos 🟠
- **< 5%:** Margen muy bajo o pérdida, acción urgente 🔴
- **Negativo:** Pérdida, revisar inmediatamente ❌

### Productos sin Costo o SKU

Si ves productos con valores NULL en ganancia, revisa:
- **tiene_sku = 'SIN SKU'**: El producto no tiene SKU asignado
- **tiene_costo = 'SIN COSTO'**: No hay costo en la tabla `woo_products_fccost`

**Solución:**
1. Asigna SKU al producto en WooCommerce
2. Importa costos desde Fishbowl a `woo_products_fccost`

---

## 🎯 Índices Recomendados para Mejor Rendimiento

Si los queries son lentos, ejecuta estos comandos para crear índices (solo una vez):

```sql
CREATE INDEX idx_orders_date_type_status ON wpyz_wc_orders(date_created_gmt, type, status);
CREATE INDEX idx_orders_meta_key_value ON wpyz_wc_orders_meta(order_id, meta_key, meta_value(100));
CREATE INDEX idx_order_items_order_type ON wpyz_woocommerce_order_items(order_id, order_item_type);
CREATE INDEX idx_order_itemmeta_item_key ON wpyz_woocommerce_order_itemmeta(order_item_id, meta_key);
CREATE INDEX idx_postmeta_post_key ON wpyz_postmeta(post_id, meta_key);
CREATE INDEX idx_fccost_sku ON woo_products_fccost(sku);
CREATE INDEX idx_tipo_cambio_fecha_activo ON woo_tipo_cambio(fecha, activo);
```

---

## ⚡ Tips y Trucos

### Filtrar solo pedidos completados
Agrega al WHERE:
```sql
AND o.status = 'wc-completed'
```

### Ver solo productos con margen bajo (< 15%)
En los scripts por producto, agrega al final:
```sql
HAVING margen_porcentaje < 15 AND margen_porcentaje > 0
```

### Excluir productos sin costo
Agrega al final del script detallado:
```sql
AND (
    SELECT SUM(fc.FCLastCost)
    FROM woo_products_fccost fc
    WHERE pm_sku.meta_value LIKE CONCAT('%', fc.sku, '%')
) IS NOT NULL
```

### Filtrar por asesor específico
Agrega al WHERE:
```sql
AND om_created.meta_value = 'nombre_usuario'
```

---

## 🆘 Solución de Problemas

### Error: "Unknown column"
- Verifica que estés conectado a la base de datos correcta
- Confirma que las tablas tengan el prefijo correcto (`wpyz_`)

### Query muy lento (> 30 segundos)
- Crea los índices recomendados (ver arriba)
- Reduce el rango de fechas
- Usa el script de resumen en lugar del detallado

### Resultados diferentes al dashboard
- Verifica que las fechas sean exactamente las mismas
- Confirma que estás usando la misma conversión UTC-5
- Revisa que los estados de pedido filtrados sean los mismos

### Productos con ganancia NULL
- Verifica que tengan SKU asignado
- Confirma que existan en `woo_products_fccost`
- Revisa que el SKU coincida exactamente

---

## 📞 Soporte

Si encuentras discrepancias entre los scripts y el módulo web:

1. Compara primero con `query_profit_margins_summary.sql`
2. Si los totales no coinciden, usa `query_profit_margins_validation.sql`
3. Para debugging profundo, usa `query_profit_margins_detailed.sql`
4. Documenta las diferencias específicas encontradas

---

## 📝 Changelog

**Versión 1.0** (2024-12-19)
- Scripts iniciales de validación
- 4 niveles de granularidad (summary, validation, by_product, detailed)
- Soporte para costos de productos y envío
- Conversión UTC-5 automática
- Exportación a CSV compatible

---

**¡Listo para validar tus márgenes de ganancia! 🚀**
