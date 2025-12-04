# Scripts SQL - WooCommerce Manager

Esta carpeta contiene scripts SQL organizados por categoría para diagnóstico, migraciones y correcciones.

## 📁 Estructura

```
sql_scripts/
├── diagnostico/      # Scripts de consulta y verificación
├── migraciones/      # Scripts de creación de tablas e índices
├── correcciones/     # Scripts de corrección de datos
└── README.md         # Este archivo
```

---

## 🔍 DIAGNÓSTICO

Scripts para consultar y verificar datos sin modificar nada.

### `consulta_producto_completo.sql`
**Propósito:** Consultar información completa de un producto con todas sus variaciones, metadatos y atributos.

**Uso:**
```sql
-- Modificar el ID del producto en la consulta
WHERE p.ID = 23233
```

**Retorna:**
- Información del producto padre
- Todas las variaciones
- Metadatos (precio, stock, SKU)
- Atributos y taxonomías

---

### `exportar_producto_completo.sql`
**Propósito:** Exportar estructura completa de un producto para replicar en otra base de datos.

**Uso:**
```sql
-- Cambiar el ID del producto
WHERE ... = 23233
```

**Genera:**
- Queries INSERT para replicar producto
- Incluye variaciones, metas y relaciones

---

### `revisar_horas_pedidos.sql`
**Propósito:** Verificar la conversión UTC de fechas de pedidos (Peru UTC-5).

**Uso:**
- Ejecutar directamente
- Verifica pedidos creados en diferentes horarios
- Confirma que la conversión UTC-5 funciona

**Contexto:** Se usó para verificar que pedidos creados después de 7 PM en Perú no aparecieran como del día siguiente.

---

### `verificar_contador_pedidos.sql`
**Propósito:** Diagnosticar por qué el contador de pedidos mostraba números incorrectos.

**Retorna:**
- Total de pedidos sin filtro
- Pedidos con `_order_number`
- Pedidos con formato W-XXXXX
- Distribución por estado

**Contexto:** Se usó para identificar que se estaban contando todos los pedidos en lugar de solo los de WhatsApp.

---

### `verificar_meta_keys_pedidos.sql`
**Propósito:** Verificar qué meta_keys se usan para los números de pedido.

**Retorna:**
- Meta keys relacionados con order_number
- Comparativa entre `_order_number` y `_order_number_formatted`
- Ejemplos de pedidos recientes

**Contexto:** Para entender qué meta_key usar para filtrar pedidos de WhatsApp.

---

### `verificar_atributos_variacion.sql`
**Propósito:** Diagnosticar atributos fantasma en variaciones de productos.

**Uso:**
```sql
-- Cambiar el SKU de la variación
WHERE meta_value = '1007346-SGW7'
```

**Retorna:**
- Metadatos `attribute_*` de la variación
- Atributos del producto padre
- Búsqueda de atributos huérfanos

**Contexto:** Para identificar el atributo `pa_conector` huérfano que aparecía en el frontend.

---

## 🔧 MIGRACIONES

Scripts para crear tablas, índices y estructuras.

### `create_orders_external_table.sql`
**Propósito:** Crear tablas para el sistema de pedidos externos.

**Crea:**
- `woo_orders_ext` - Tabla principal de pedidos externos
- `woo_orders_ext_items` - Items de pedidos externos

**Features:**
- Tracking de pedidos externos (no WooCommerce)
- Mismo esquema de campos que pedidos WhatsApp
- Foreign keys y cascade deletes

**Uso:**
```sql
-- Ejecutar una vez para crear las tablas
-- NO ejecutar si las tablas ya existen
```

---

### `create_indexes.sql`, `database_indexes.sql`, `create_indexes_wp.sql`
**Propósito:** Crear índices para optimizar queries de WooCommerce.

**Índices creados:**
- `wpyz_postmeta` (meta_key, meta_value)
- `wpyz_wc_orders_meta` (meta_key, meta_value)
- `wpyz_posts` (post_type, post_status)

**Impacto:** Mejora significativa en velocidad de búsquedas y listados.

---

### `create_price_history_table.sql`
**Propósito:** Crear tabla para historial de cambios de precios.

**Crea:**
- `price_history` - Registro de todos los cambios de precio
- Permite auditoría de precios

---

### `create_products_tables.sql` / `create_products_tables_postgres.sql`
**Propósito:** Scripts de creación de tablas de productos (MySQL y PostgreSQL).

**Uso:** Solo como referencia o para replicar estructura en otra DB.

---

## 🔨 CORRECCIONES

Scripts para corregir datos incorrectos (¡USAR CON PRECAUCIÓN!).

### `corregir_fechas_pedidos.sql`
**Propósito:** Corregir fechas de pedidos específicos con error en conversión UTC.

**Pedidos afectados:** 39844, 39843, 39841, 39840

**Incluye:**
- PASO 1: Backup de datos originales
- PASO 2: UPDATE para corregir fechas (resta 5 horas)
- PASO 3: Rollback opcional

**⚠️ ADVERTENCIA:**
- Solo ejecutar si estos pedidos específicos tienen fechas incorrectas
- Revisar backup antes de UPDATE
- Tener plan de rollback

---

### `drop_incorrect_tables.sql`
**Propósito:** Eliminar tablas creadas con prefijo incorrecto.

**Elimina:**
- `wpyz_woo_orders_ext` (prefijo incorrecto)
- `wpyz_woo_orders_ext_items`

**Contexto:** Se crearon tablas con prefijo `wpyz_woo_` cuando debían ser solo `woo_`.

**⚠️ ADVERTENCIA:**
- DROP TABLE es irreversible
- Verificar que no contienen datos importantes
- Solo ejecutar si las tablas están vacías

---

### `limpiar_atributo_conector_huerfano.sql`
**Propósito:** Eliminar metadatos `attribute_pa_conector` huérfanos de variaciones.

**Incluye:**
- PASO 1: Backup en tabla temporal
- PASO 2: DELETE comentado (descomentar para ejecutar)
- PASO 3: Verificación
- PASO 4: Rollback opcional

**Contexto:** Atributo "Conector" aparecía en frontend pero no existía en WooCommerce.

**⚠️ ADVERTENCIA:**
- DELETE viene comentado por seguridad
- Ejecutar backup primero
- Verificar que backup tiene datos correctos antes de DELETE

---

## 📋 CONVENCIONES

### Nomenclatura
- `consulta_*.sql` - Scripts de solo lectura
- `verificar_*.sql` - Scripts de diagnóstico
- `exportar_*.sql` - Scripts de exportación
- `create_*.sql` - Scripts de creación (DDL)
- `corregir_*.sql` - Scripts de corrección (DML)
- `drop_*.sql` - Scripts de eliminación (¡PELIGRO!)
- `limpiar_*.sql` - Scripts de limpieza

### Seguridad
- ✅ Scripts de diagnóstico son seguros (solo SELECT)
- ⚠️ Scripts de creación requieren verificar que no existan las tablas
- 🔴 Scripts de corrección/eliminación requieren backup y revisión

### Buenas Prácticas
1. **Siempre hacer backup antes de modificar datos**
2. **Leer el script completo antes de ejecutar**
3. **Ejecutar en ambiente de desarrollo primero**
4. **Verificar resultados con queries de diagnóstico**
5. **Documentar cambios en commits**

---

## 🔗 REFERENCIAS

- Carpeta `migrations/` - Migraciones de Flask-Migrate
- Documentación de WooCommerce HPOS
- Plan de modernización: `PLAN_MODERNIZACION_FRONTEND.md`

---

**Última actualización:** 2024-12-04
**Mantenido por:** Claude Code
