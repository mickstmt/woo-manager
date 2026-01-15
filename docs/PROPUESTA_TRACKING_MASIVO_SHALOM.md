# Propuesta: Asignación Masiva de Tracking para Envíos Shalom

## Resumen Ejecutivo

Este documento describe la propuesta para implementar la asignación masiva de números de tracking a pedidos con método de envío **Shalom**, manteniendo 100% de compatibilidad con el flujo actual (envío de correos, cambio de estado, registro en WooCommerce).

---

## 1. Análisis del Sistema Actual

### 1.1 Flujo Actual de Asignación de Tracking (Individual)

Cuando se asigna un tracking manualmente desde el módulo de despacho, el sistema ejecuta:

1. **Validación del pedido** - Verifica que exista en la BD
2. **Llamada a la API de WooCommerce** (si `mark_as_shipped=true`):
   - Cambia el estado del pedido a `wc-completed`
   - Guarda los metadatos de tracking
   - **Dispara automáticamente el email al cliente** con la información del envío
3. **Guardado en BD Legacy** (`wpyz_postmeta`):
   - `_tracking_number`
   - `_tracking_provider`
   - `_wc_shipment_tracking_items` (serializado PHP)
   - Se insertan duplicados para compatibilidad con el plugin "Shipment Tracking"
4. **Guardado en HPOS** (`wpyz_wc_orders_meta`):
   - `_wc_shipment_tracking_items`

### 1.2 Respuesta a la Pregunta Clave

> **¿Se perdería alguna funcionalidad?**

**NO**, siempre y cuando la implementación masiva utilice **exactamente el mismo flujo** que el proceso individual, específicamente:

- Llamar a la API de WooCommerce para cada pedido (esto es lo que dispara los emails)
- Guardar los metadatos en ambas tablas (Legacy y HPOS)

---

## 2. Propuesta de Implementación

### 2.1 Flujo Propuesto

```
┌─────────────────────────────────────────────────────────────────────┐
│                    FLUJO DE TRACKING MASIVO                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. Usuario coloca archivo Excel en ubicación predefinida           │
│     📁 app/static/uploads/shalom_tracking.xlsx                      │
│                                                                     │
│  2. Usuario accede a nueva sección en el módulo de Despacho         │
│     🖥️ /dispatch/bulk-tracking                                      │
│                                                                     │
│  3. Sistema lee y valida el Excel:                                  │
│     ✓ Formato correcto                                              │
│     ✓ Pedidos existen en BD                                         │
│     ✓ Pedidos están en estado "processing"                          │
│     ✓ Pedidos son de tipo Shalom                                    │
│                                                                     │
│  4. Usuario ve preview y confirma                                   │
│     👁️ Vista previa de pedidos a procesar                           │
│     ⚠️ Alertas de pedidos con problemas                             │
│                                                                     │
│  5. Sistema procesa cada pedido:                                    │
│     🔄 Mismo flujo que asignación individual                        │
│     📧 Emails se envían automáticamente                             │
│     📊 Progreso en tiempo real                                      │
│                                                                     │
│  6. Reporte final                                                   │
│     ✅ Pedidos procesados exitosamente                              │
│     ❌ Pedidos con errores (y razón)                                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Formato del Archivo Excel

El archivo debe contener las siguientes columnas:

| Columna | Nombre | Descripción | Ejemplo | Requerido |
|---------|--------|-------------|---------|-----------|
| A | `numero_pedido` | Número de pedido (sin #) | 41608 | ✅ Sí |
| B | `tracking_number` | Código de seguimiento Shalom | SHL123456789 | ✅ Sí |
| C | `fecha_envio` | Fecha de envío (YYYY-MM-DD) | 2026-01-15 | ❌ No (default: hoy) |

**Ejemplo de contenido:**

```
numero_pedido | tracking_number | fecha_envio
------------- | --------------- | -----------
41608         | SHL123456789    | 2026-01-15
41610         | SHL123456790    | 2026-01-15
41615         | SHL123456791    |
```

### 2.3 Ubicación del Archivo

```
📁 woocommerce-manager/
├── 📁 app/
│   └── 📁 static/
│       └── 📁 uploads/
│           └── 📄 shalom_tracking.xlsx  ← ARCHIVO AQUÍ
```

**Ruta completa:** `app/static/uploads/shalom_tracking.xlsx`

---

## 3. Interfaz de Usuario Propuesta

### 3.1 Nueva Sección en Módulo de Despacho

Se agregará un nuevo botón en el header del módulo de despacho:

```
┌──────────────────────────────────────────────────────────────┐
│  📦 Módulo de Despacho                    [Tracking Masivo]  │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 Pantalla de Tracking Masivo

```
┌──────────────────────────────────────────────────────────────────────┐
│  📦 Asignación Masiva de Tracking - Shalom                           │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  📁 Archivo: shalom_tracking.xlsx                                    │
│  📊 Estado: ✅ Archivo encontrado (15 registros)                     │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ # Pedido │ Tracking      │ Fecha     │ Estado    │ Validación │  │
│  ├──────────┼───────────────┼───────────┼───────────┼────────────┤  │
│  │ 41608    │ SHL123456789  │ 2026-01-15│ processing│ ✅ OK      │  │
│  │ 41610    │ SHL123456790  │ 2026-01-15│ processing│ ✅ OK      │  │
│  │ 41615    │ SHL123456791  │ 2026-01-15│ completed │ ⚠️ Ya env. │  │
│  │ 41620    │ SHL123456792  │ 2026-01-15│ -         │ ❌ No exist│  │
│  └──────────┴───────────────┴───────────┴───────────┴────────────┘  │
│                                                                      │
│  Resumen:                                                            │
│  • ✅ 2 pedidos listos para procesar                                 │
│  • ⚠️ 1 pedido ya tiene tracking (se omitirá)                        │
│  • ❌ 1 pedido no encontrado (se omitirá)                            │
│                                                                      │
│  ☑️ Marcar como "Completado" y enviar email al cliente               │
│                                                                      │
│  [🔄 Recargar Archivo]  [▶️ Procesar 2 Pedidos]                       │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.3 Pantalla de Progreso

```
┌──────────────────────────────────────────────────────────────────────┐
│  📦 Procesando Tracking Masivo                                       │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Progreso: ████████████░░░░░░░░ 60% (12/20)                         │
│                                                                      │
│  Procesando pedido #41625... ⏳                                       │
│                                                                      │
│  Últimos procesados:                                                 │
│  • #41608 - ✅ Tracking asignado, email enviado                      │
│  • #41610 - ✅ Tracking asignado, email enviado                      │
│  • #41612 - ❌ Error: API timeout (se reintentará)                   │
│                                                                      │
│  ⚠️ No cierre esta ventana hasta que termine el proceso              │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 4. Consideraciones Técnicas

### 4.1 Manejo de Errores

| Error | Acción |
|-------|--------|
| Pedido no existe | Registrar en log, omitir, continuar |
| Pedido ya completado | Registrar en log, omitir, continuar |
| Error de API WooCommerce | Reintentar 1 vez, si falla registrar y continuar |
| Tracking duplicado | Registrar advertencia, continuar |

### 4.2 Rate Limiting

Para evitar sobrecargar la API de WooCommerce:
- Procesar máximo **1 pedido por segundo**
- Implementar reintentos con backoff exponencial
- Máximo 100 pedidos por lote

### 4.3 Logs y Auditoría

Cada operación masiva generará:
1. **Log en consola** con detalle de cada pedido
2. **Registro en DispatchHistory** para cada pedido procesado
3. **Archivo de reporte** descargable (CSV) al finalizar

---

## 5. Seguridad

### 5.1 Validaciones

- Solo usuarios con rol `master` pueden ejecutar tracking masivo
- El archivo debe estar en la ubicación predefinida (no upload dinámico inicial)
- Validación de formato antes de procesar
- Confirmación obligatoria antes de ejecutar

### 5.2 Rollback

- Si hay error crítico, las transacciones se hacen por pedido individual
- Los pedidos procesados correctamente NO se revierten
- Se genera reporte de pedidos fallidos para reprocesar manualmente

---

## 6. Ventajas de esta Propuesta

| Aspecto | Beneficio |
|---------|-----------|
| **Emails** | ✅ Se envían automáticamente (usa la API de WooCommerce) |
| **Compatibilidad** | ✅ 100% compatible con el plugin Shipment Tracking |
| **Trazabilidad** | ✅ Mismo registro en DispatchHistory |
| **Flexibilidad** | ✅ Puede usarse solo para Shalom o extenderse a otros |
| **Seguridad** | ✅ Vista previa antes de procesar |
| **Recuperación** | ✅ Reporte de errores para reprocesar |

---

## 7. Alternativas Consideradas

### 7.1 Alternativa A: Subir Excel vía formulario web
- **Pro:** Más flexible para el usuario
- **Contra:** Requiere más desarrollo (upload, validación de archivos maliciosos)
- **Decisión:** Fase 2 (después de validar el flujo básico)

### 7.2 Alternativa B: Copiar/pegar datos en textarea
- **Pro:** No requiere archivos
- **Contra:** Propenso a errores de formato, límite de datos
- **Decisión:** Descartado

### 7.3 Alternativa C: Integración directa con API de Shalom
- **Pro:** Automatización total
- **Contra:** Requiere API de Shalom (verificar disponibilidad)
- **Decisión:** Fase 3 (investigar API de Shalom)

---

## 8. Plan de Implementación

### Fase 1: MVP (Propuesta actual)
1. Crear endpoint `/dispatch/bulk-tracking`
2. Crear página de interfaz
3. Implementar lectura de Excel
4. Implementar validación y preview
5. Implementar procesamiento con progreso
6. Generar reporte final

### Fase 2: Mejoras
- Upload de archivo vía web
- Soporte para otros proveedores (Olva, Dinsides)
- Historial de operaciones masivas

### Fase 3: Automatización
- Integración con API de Shalom (si disponible)
- Programación de tareas automáticas

---

## 9. Preguntas para el Usuario

Antes de proceder con la implementación, necesito confirmar:

1. **¿El formato del Excel propuesto es correcto?**
   - ¿El número de pedido es el ID interno o el número visible (#41608)?

2. **¿El tracking de Shalom tiene un formato específico?**
   - Ejemplo: ¿Siempre empieza con "SHL" o tiene otro patrón?

3. **¿Hay un límite de pedidos que procesan por día con Shalom?**
   - Para definir el tamaño máximo del lote

4. **¿Necesitan que el archivo Excel se elimine automáticamente después de procesar?**
   - Por seguridad de datos

5. **¿Quieren recibir una notificación (email/Slack) cuando termine el proceso masivo?**

---

## 10. Conclusión

**La propuesta es 100% viable** y mantiene todas las funcionalidades actuales:

- ✅ **Emails se envían** - Usamos la misma API de WooCommerce
- ✅ **Estado cambia a Completado** - Mismo flujo que individual
- ✅ **Plugin Shipment Tracking funciona** - Guardamos en las mismas tablas
- ✅ **Trazabilidad completa** - Registro en DispatchHistory
- ✅ **Seguro** - Vista previa y confirmación obligatoria

**Tiempo estimado de desarrollo:** 1-2 sesiones de trabajo

---

*Documento generado el 2026-01-15*
*WooCommerce Manager - Módulo de Despacho*
