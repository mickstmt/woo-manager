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

## 2. Formato del Archivo Excel de Shalom

### 2.1 Estructura del Excel (Formato Real de Shalom)

El archivo Excel que proporciona Shalom tiene un formato específico donde **cada envío ocupa 26 filas** en la columna A:

```
┌─────┬────────────────────────────────────────────────────────┐
│ FILA│ CONTENIDO                                              │
├─────┼────────────────────────────────────────────────────────┤
│ A1  │ ENVÍO N°1                                              │
│ A2  │ 1/13/2026                        (Fecha del envío)     │
│ A3  │ (vacío)                                                │
│ A4  │ ORIGEN                           (Título sección)      │
│ A5  │ FIORI                            (Sede origen)         │
│ A6  │ Remitente                        (Etiqueta)            │
│ A7  │ JHONATAN LEON GARGATE            (Nombre remitente)    │
│ A8  │ 43305070                         (DNI REMITENTE) ⭐    │
│ A9  │ 935403614                        (TEL REMITENTE) ⭐    │
│ A10 │ DESTINO                          (Título sección)      │
│ A11 │ JR AGUILAR                       (Dirección destino)   │
│ A12 │ Destinatario                     (Etiqueta)            │
│ A13 │ YERINA ZEVALLOS MILLAN           (Nombre destinatario) │
│ A14 │ 45416776                         (DNI DESTINATARIO) ⭐ │
│ A15 │ 910453918                        (Tel destinatario)    │
│ A16 │ Detalle del envío                (Etiqueta)            │
│ A17 │ CANTIDAD: 1                                            │
│ A18 │ PAQUETERIA: XXS                                        │
│ A19 │ Servicios Adicionales            (Etiqueta)            │
│ A20 │ DETALLE                                                │
│ A21 │ Clave de seguridad               (Etiqueta)            │
│ A22 │ ACTUALIZAR                                             │
│ A23 │ N° de orden: 68529922            (ORDEN SHALOM) ⭐     │
│ A24 │ Código: JN79                     (CÓDIGO SHALOM) ⭐    │
│ A25 │ Paquetería                       (Etiqueta)            │
│ A26 │ S/. 8.00                         (Costo envío)         │
└─────┴────────────────────────────────────────────────────────┘
```

### 2.2 Datos Clave para Extraer

| Celda | Dato | Uso |
|-------|------|-----|
| **A14** | DNI Destinatario | Para identificar el pedido en WooCommerce |
| **A23** | N° de orden Shalom | Parte del tracking number |
| **A24** | Código Shalom | Parte del tracking number |
| **A8** | DNI Remitente | Últimos 2 dígitos para la CLAVE |
| **A9** | Teléfono Remitente | Últimos 2 dígitos para la CLAVE |

### 2.3 Construcción del Tracking Number

El tracking number se construye concatenando:

```
N° de orden: 68529922 Código: JN79 CLAVE: 7014
           └─ A23 ─┘        └ A24 ┘       └─┬─┘
                                            │
                    ┌───────────────────────┘
                    │
            Últimos 2 dígitos DNI remitente (A8): "70"
            +
            Últimos 2 dígitos teléfono remitente (A9): "14"
```

**Ejemplo completo:**
- A8 (DNI remitente): `43305070` → últimos 2: `70`
- A9 (Tel remitente): `935403614` → últimos 2: `14`
- A23: `N° de orden: 68529922`
- A24: `Código: JN79`

**Tracking final:** `N° de orden: 68529922 Código: JN79 CLAVE: 7014`

### 2.4 Múltiples Envíos en el Excel

Para archivos con múltiples envíos, cada bloque de 26 filas representa un envío:

| Envío | Filas | DNI Destinatario | N° Orden | Código |
|-------|-------|------------------|----------|--------|
| 1 | A1:A26 | A14 | A23 | A24 |
| 2 | A27:A52 | A40 | A49 | A50 |
| 3 | A53:A78 | A66 | A75 | A76 |
| N | A(1+26*(N-1)):A(26*N) | A(14+26*(N-1)) | A(23+26*(N-1)) | A(24+26*(N-1)) |

**Fórmula general para el envío N:**
- DNI Destinatario: `A[14 + 26*(N-1)]`
- N° de orden: `A[23 + 26*(N-1)]`
- Código: `A[24 + 26*(N-1)]`
- DNI Remitente: `A[8 + 26*(N-1)]`
- Tel Remitente: `A[9 + 26*(N-1)]`

---

## 3. Lógica de Matching (Pedido Excel ↔ Pedido WooCommerce)

### 3.1 Proceso de Identificación

```
┌─────────────────────────────────────────────────────────────────┐
│                    PROCESO DE MATCHING                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Leer DNI destinatario del Excel (celda A14, A40, etc.)      │
│                                                                 │
│  2. Buscar en pedidos Shalom en estado "processing":            │
│     SELECT * FROM pedidos                                       │
│     WHERE metodo_envio = 'Shalom'                               │
│       AND estado = 'wc-processing'                              │
│       AND dni_cliente = :dni_excel                              │
│                                                                 │
│  3. Si hay coincidencia:                                        │
│     ✅ Construir tracking number                                │
│     ✅ Asignar al pedido                                        │
│                                                                 │
│  4. Si NO hay coincidencia:                                     │
│     ⚠️ Registrar en log de errores                              │
│     ⚠️ Mostrar en reporte final                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Validaciones

| Validación | Acción si falla |
|------------|-----------------|
| DNI no encontrado en pedidos Shalom | Omitir, registrar error |
| Pedido ya está completado | Omitir, registrar advertencia |
| Pedido no es de tipo Shalom | Omitir, registrar error |
| Formato de celda inválido | Omitir, registrar error |

---

## 4. Flujo de Implementación

### 4.1 Diagrama de Flujo

```
┌─────────────────────────────────────────────────────────────────────┐
│                    FLUJO DE TRACKING MASIVO SHALOM                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. Usuario coloca archivo Excel en ubicación predefinida           │
│     📁 app/static/uploads/shalom_tracking.xlsx                      │
│                                                                     │
│  2. Usuario accede a nueva sección en el módulo de Despacho         │
│     🖥️ /dispatch/bulk-tracking                                      │
│                                                                     │
│  3. Sistema lee el Excel:                                           │
│     📖 Detecta cantidad de envíos (filas / 26)                      │
│     📖 Extrae datos de cada bloque de 26 filas                      │
│     📖 Construye tracking number para cada envío                    │
│                                                                     │
│  4. Sistema valida cada envío:                                      │
│     🔍 Busca pedido por DNI destinatario                            │
│     ✓ Verifica que sea pedido Shalom                                │
│     ✓ Verifica que esté en estado "processing"                      │
│                                                                     │
│  5. Usuario ve preview y confirma                                   │
│     👁️ Vista previa de pedidos a procesar                           │
│     ⚠️ Alertas de DNIs no encontrados                               │
│                                                                     │
│  6. Sistema procesa cada pedido:                                    │
│     🔄 Mismo flujo que asignación individual                        │
│     📧 Emails se envían automáticamente                             │
│     📊 Progreso en tiempo real                                      │
│                                                                     │
│  7. Reporte final                                                   │
│     ✅ Pedidos procesados exitosamente                              │
│     ❌ DNIs no encontrados (y datos del Excel)                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 Ubicación del Archivo

```
📁 woocommerce-manager/
├── 📁 app/
│   └── 📁 static/
│       └── 📁 uploads/
│           └── 📄 shalom_tracking.xlsx  ← ARCHIVO AQUÍ
```

**Ruta completa:** `app/static/uploads/shalom_tracking.xlsx`

---

## 5. Interfaz de Usuario Propuesta

### 5.1 Nueva Sección en Módulo de Despacho

Se agregará un nuevo botón en el header del módulo de despacho:

```
┌──────────────────────────────────────────────────────────────┐
│  📦 Módulo de Despacho                    [Tracking Masivo]  │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 Pantalla de Tracking Masivo

```
┌──────────────────────────────────────────────────────────────────────────┐
│  📦 Asignación Masiva de Tracking - Shalom                               │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  📁 Archivo: shalom_tracking.xlsx                                        │
│  📊 Estado: ✅ Archivo encontrado (5 envíos detectados)                  │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ DNI Dest. │ Pedido     │ Cliente           │ Tracking      │ Estado│  │
│  ├───────────┼────────────┼───────────────────┼───────────────┼───────┤  │
│  │ 45416776  │ #IZI-41608 │ YERINA ZEVALLOS   │ N° orden: ... │ ✅ OK │  │
│  │ 72839164  │ #IZI-41610 │ CARLOS MENDOZA    │ N° orden: ... │ ✅ OK │  │
│  │ 10293847  │ -          │ -                 │ N° orden: ... │ ❌ DNI│  │
│  │ 48572910  │ #IZI-41615 │ MARIA TORRES      │ N° orden: ... │ ⚠️ YA │  │
│  │ 91827364  │ #IZI-41620 │ PEDRO GARCIA      │ N° orden: ... │ ✅ OK │  │
│  └───────────┴────────────┴───────────────────┴───────────────┴───────┘  │
│                                                                          │
│  Resumen:                                                                │
│  • ✅ 3 pedidos listos para procesar                                     │
│  • ⚠️ 1 pedido ya completado (se omitirá)                                │
│  • ❌ 1 DNI no encontrado en pedidos Shalom (se omitirá)                 │
│                                                                          │
│  Configuración:                                                          │
│  ☑️ Marcar como "Completado" y enviar email al cliente                   │
│  📅 Fecha de envío: [15/01/2026] (por defecto: hoy)                      │
│                                                                          │
│  [🔄 Recargar Archivo]  [▶️ Procesar 3 Pedidos]                           │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 5.3 Pantalla de Progreso

```
┌──────────────────────────────────────────────────────────────────────┐
│  📦 Procesando Tracking Masivo                                       │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Progreso: ████████████░░░░░░░░ 60% (3/5)                           │
│                                                                      │
│  Procesando: DNI 91827364 → Pedido #IZI-41620... ⏳                   │
│                                                                      │
│  Resultados:                                                         │
│  • DNI 45416776 → #IZI-41608 ✅ Tracking asignado, email enviado     │
│  • DNI 72839164 → #IZI-41610 ✅ Tracking asignado, email enviado     │
│  • DNI 10293847 → ❌ Omitido (DNI no encontrado)                     │
│  • DNI 48572910 → ⚠️ Omitido (pedido ya completado)                  │
│                                                                      │
│  ⚠️ No cierre esta ventana hasta que termine el proceso              │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 6. Consideraciones Técnicas

### 6.1 Pseudocódigo del Parser

```python
def parse_shalom_excel(filepath):
    """
    Lee el Excel de Shalom y extrae los datos de cada envío.
    """
    workbook = load_workbook(filepath)
    sheet = workbook.active

    envios = []
    fila = 1

    while sheet[f'A{fila}'].value:  # Mientras haya datos
        envio = {
            'dni_destinatario': str(sheet[f'A{fila + 13}'].value),  # A14, A40, etc.
            'orden_shalom': sheet[f'A{fila + 22}'].value,           # A23, A49, etc.
            'codigo_shalom': sheet[f'A{fila + 23}'].value,          # A24, A50, etc.
            'dni_remitente': str(sheet[f'A{fila + 7}'].value),      # A8, A34, etc.
            'tel_remitente': str(sheet[f'A{fila + 8}'].value),      # A9, A35, etc.
        }

        # Construir tracking number
        clave = envio['dni_remitente'][-2:] + envio['tel_remitente'][-2:]
        envio['tracking_number'] = f"{envio['orden_shalom']} {envio['codigo_shalom']} CLAVE: {clave}"

        envios.append(envio)
        fila += 26  # Saltar al siguiente bloque

    return envios
```

### 6.2 Manejo de Errores

| Error | Acción |
|-------|--------|
| DNI no encontrado en pedidos Shalom | Registrar en log, omitir, continuar |
| Pedido ya completado | Registrar advertencia, omitir, continuar |
| Formato de celda inválido | Registrar error, omitir, continuar |
| Error de API WooCommerce | Reintentar 1 vez, si falla registrar y continuar |
| Múltiples pedidos con mismo DNI | Mostrar advertencia, procesar el más reciente |

### 6.3 Rate Limiting

Para evitar sobrecargar la API de WooCommerce:
- Procesar máximo **1 pedido por segundo**
- Implementar reintentos con backoff exponencial
- Máximo 50 pedidos por lote

### 6.4 Logs y Auditoría

Cada operación masiva generará:
1. **Log en consola** con detalle de cada pedido
2. **Registro en DispatchHistory** para cada pedido procesado
3. **Reporte final** en pantalla con resumen de éxitos y errores

---

## 7. Seguridad

### 7.1 Validaciones

- Solo usuarios con rol `master` pueden ejecutar tracking masivo
- El archivo debe estar en la ubicación predefinida (no upload dinámico inicial)
- Validación de formato antes de procesar
- Confirmación obligatoria antes de ejecutar

### 7.2 Rollback

- Si hay error crítico, las transacciones se hacen por pedido individual
- Los pedidos procesados correctamente NO se revierten
- Se genera reporte de pedidos fallidos para reprocesar manualmente

---

## 8. Ventajas de esta Propuesta

| Aspecto | Beneficio |
|---------|-----------|
| **Emails** | ✅ Se envían automáticamente (usa la API de WooCommerce) |
| **Compatibilidad** | ✅ 100% compatible con el plugin Shipment Tracking |
| **Trazabilidad** | ✅ Mismo registro en DispatchHistory |
| **Matching** | ✅ Por DNI, evita errores de número de pedido |
| **Seguridad** | ✅ Vista previa antes de procesar |
| **Recuperación** | ✅ Reporte de errores con DNIs no encontrados |

---

## 9. Ejemplo Completo

### Entrada (Excel de Shalom)

```
A1:  ENVÍO N°1
A2:  1/13/2026
...
A8:  43305070          ← DNI Remitente
A9:  935403614         ← Tel Remitente
...
A14: 45416776          ← DNI Destinatario (para buscar pedido)
...
A23: N° de orden: 68529922
A24: Código: JN79
...
A27: ENVÍO N°2
... (siguiente bloque)
```

### Proceso

1. **Extraer DNI destinatario:** `45416776`
2. **Buscar en BD:** Pedido #IZI-41608 tiene DNI `45416776` y es Shalom
3. **Construir tracking:**
   - Orden: `N° de orden: 68529922`
   - Código: `Código: JN79`
   - Clave: `70` (de 433050**70**) + `14` (de 9354036**14**) = `7014`
4. **Tracking final:** `N° de orden: 68529922 Código: JN79 CLAVE: 7014`

### Salida (Asignación)

```
Pedido: #IZI-41608
Tracking: N° de orden: 68529922 Código: JN79 CLAVE: 7014
Provider: Shalom
Fecha: 2026-01-15
Estado: wc-completed
Email: ✅ Enviado
```

---

## 10. Plan de Implementación

### Fase 1: MVP
1. Crear endpoint `/dispatch/bulk-tracking`
2. Crear página de interfaz
3. Implementar parser de Excel (formato Shalom de 26 filas)
4. Implementar matching por DNI
5. Implementar validación y preview
6. Implementar procesamiento con progreso
7. Generar reporte final

### Fase 2: Mejoras
- Upload de archivo vía web (drag & drop)
- Historial de operaciones masivas
- Exportar reporte de errores a Excel

---

## 11. Conclusión

**La propuesta es 100% viable** y mantiene todas las funcionalidades actuales:

- ✅ **Emails se envían** - Usamos la misma API de WooCommerce
- ✅ **Estado cambia a Completado** - Mismo flujo que individual
- ✅ **Plugin Shipment Tracking funciona** - Guardamos en las mismas tablas
- ✅ **Trazabilidad completa** - Registro en DispatchHistory
- ✅ **Matching preciso** - Por DNI del destinatario
- ✅ **Seguro** - Vista previa y confirmación obligatoria

---

*Documento actualizado el 2026-01-15*
*WooCommerce Manager - Módulo de Despacho*
