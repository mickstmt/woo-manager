# Plan de Limpieza del Repositorio

## 📋 Análisis de Archivos

### ❌ ARCHIVOS A ELIMINAR (Temporales/Debug)

#### Archivos Python temporales en root (13 archivos):
```
temp_analyze_order.py                    # Análisis temporal de pedidos
temp_analyze_variation.py                # Análisis temporal de variaciones
temp_analyze_w00024.py                   # Análisis específico de pedido W-00024
temp_check_creator.py                    # Verificación temporal de creador
temp_check_sin_asesor.py                 # Verificación temporal de pedidos sin asesor
temp_find_order.py                       # Búsqueda temporal de pedidos
temp_query_orders_by_date.py             # Query temporal por fechas
temp_test_email.py                       # Test temporal de emails
temp_test_shipping_api.py                # Test temporal de API de envíos
temp_test_sku_logic.py                   # Test temporal de lógica SKU
test_db.py                               # Test de conexión DB
test_sku_search.py                       # Test de búsqueda SKU
debug_product_type.py                    # Debug de tipos de producto
```

#### Archivos SQL temporales en root (13 archivos):
```
debug_dispatch_dates.sql                 # Debug de fechas de despacho
debug_payment_method.sql                 # Debug de métodos de pago
debug_product_attributes.sql             # Debug de atributos de producto
debug_zero_costs.sql                     # Debug de costos en cero
temp_analyze_shipping_order_40682.sql    # Análisis específico de pedido
temp_check_lurin_config.sql              # Verificación config Lurín
temp_check_shipping_lurin.sql            # Verificación envíos Lurín
temp_check_shipping_method_types.sql     # Verificación tipos de envío
temp_compare_lurin_jesus_maria.sql       # Comparación distritos
temp_list_all_shipping_methods.sql       # Listado de métodos de envío
temp_query_orders_by_date.sql            # Query temporal por fechas
temp_understand_advanced_shipping.sql    # Análisis de shipping avanzado
verificar_y_cambiar_rol.sql              # Script de cambio de rol (ya ejecutado)
```

#### Archivos Python de debug recientes (2 archivos):
```
debug_prod_orders.py                     # Script de debug para producción (mantener temporalmente)
verify_deployment.py                     # Script de verificación (mantener temporalmente)
```

---

### ⚠️ ARCHIVOS A REUBICAR

#### Scripts de creación de tablas (3 archivos):
Estos deben ir a `migrations/` porque son migraciones/inicializaciones de DB:
```
create_expense_table.py          → migrations/create_expense_table.py
create_history_table.py          → migrations/create_history_table.py
create_purchase_tables.py        → migrations/create_purchase_tables.py
```

#### Scripts SQL de queries útiles (4 archivos):
Estos son queries de análisis que pueden ser útiles. Mover a `sql_scripts/diagnostico/`:
```
query_profit_margins_by_product.sql    → sql_scripts/diagnostico/profit_margins_by_product.sql
query_profit_margins_detailed.sql      → sql_scripts/diagnostico/profit_margins_detailed.sql
query_profit_margins_summary.sql       → sql_scripts/diagnostico/profit_margins_summary.sql
query_profit_margins_validation.sql    → sql_scripts/diagnostico/profit_margins_validation.sql
```

---

### ✅ ARCHIVOS A MANTENER EN ROOT

#### Archivos esenciales de configuración:
```
config.py                        # Configuración principal de Flask
run.py                          # Script de ejecución del servidor
requirements.txt                # Dependencias del proyecto
generate_password.py            # Utilidad para generar passwords
verificar_password_dduirem.py   # Utilidad específica de verificación
```

#### Archivos temporales útiles (eliminar después de verificar deployment):
```
debug_prod_orders.py            # Para debugging actual
verify_deployment.py            # Para verificar deployment
PROPUESTAS_UX_UI.md            # Documento de propuestas
```

---

### 📁 ESTRUCTURA FINAL PROPUESTA

```
woocommerce-manager/
├── app/                        # Código de aplicación
├── migrations/                 # Migraciones y scripts de DB
│   ├── create_expense_table.py
│   ├── create_history_table.py
│   ├── create_purchase_tables.py
│   └── [otros archivos existentes]
├── sql_scripts/                # Scripts SQL organizados
│   ├── diagnostico/
│   │   ├── profit_margins_by_product.sql
│   │   ├── profit_margins_detailed.sql
│   │   ├── profit_margins_summary.sql
│   │   └── profit_margins_validation.sql
│   ├── correcciones/
│   └── migraciones/
├── whitelist/                  # Archivos de whitelist
├── .gitignore                  # Ignorar archivos innecesarios
├── config.py
├── run.py
├── requirements.txt
├── generate_password.py
└── verificar_password_dduirem.py
```

---

## 🔧 COMANDOS DE LIMPIEZA

### 1. Eliminar archivos temporales Python:
```bash
rm temp_*.py test_*.py debug_product_type.py
```

### 2. Eliminar archivos temporales SQL:
```bash
rm debug_*.sql temp_*.sql verificar_y_cambiar_rol.sql
```

### 3. Reubicar scripts de creación:
```bash
mv create_expense_table.py migrations/
mv create_history_table.py migrations/
mv create_purchase_tables.py migrations/
```

### 4. Reubicar queries de profit margins:
```bash
mv query_profit_margins_*.sql sql_scripts/diagnostico/
```

### 5. Limpiar después de verificar deployment:
```bash
# Ejecutar SOLO después de confirmar que todo funciona en producción
rm debug_prod_orders.py verify_deployment.py
```

---

## 📊 RESUMEN

- **A eliminar:** 26 archivos temporales/debug
- **A reubicar:** 7 archivos a carpetas apropiadas
- **A mantener en root:** 7 archivos esenciales + 3 temporales (por ahora)
- **Espacio liberado estimado:** ~150 KB de archivos innecesarios

---

## ⚡ ACCIÓN RECOMENDADA

1. **Ahora:** Eliminar archivos temp_* y debug_* antiguos
2. **Ahora:** Reubicar create_* y query_* a carpetas apropiadas
3. **Después del deployment:** Eliminar debug_prod_orders.py y verify_deployment.py
4. **Opcional:** Actualizar .gitignore para evitar futuros archivos temp_*

---

## 🔍 VERIFICACIONES PREVIAS

Antes de eliminar, asegurarse de que:
- ✓ No hay código único en los archivos temp_* que necesites
- ✓ Los scripts de creación ya se ejecutaron en producción
- ✓ Los scripts SQL de queries están documentados en sql_scripts/
