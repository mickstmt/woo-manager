# Análisis de Cálculo de Ganancias — Discrepancias entre métodos

**Archivo principal:** `app/routes/reports.py`

---

## Caso de prueba: Pedido #43453

| Campo | Valor |
|---|---|
| Venta Total (PEN) | S/ 38.49 |
| Costo Unitario (USD) | $ 2.00 |
| Tipo de Cambio (TC) | 3.765 |
| Costo Total (PEN) | 2 × 3.765 = **S/ 7.53** |
| Costo de Envío (PEN) | S/ 8.50 |
| Precio Item (inc. IGV) | S/ 29.99 |
| IGV del Item | S/ 4.57 |

---

## Método 1 — UI: `api_profits()`
**Líneas:** 549–550
**Ruta:** `GET /api/profits`

### Fórmula
```
ganancia = total_venta - costo_pen - costo_envio
margen   = ganancia / total_venta × 100
```

### Cálculo con #43453
```
ganancia = 38.49 - 7.53 - 8.50 = 22.46
margen   = 22.46 / 38.49 × 100 = 58.35%
```

### Resultado
| Ganancia (PEN) | Margen % |
|---|---|
| **S/ 22.46** | **58.35%** |

### Características
- **NO descuenta IGV.** Usa el total_venta con IGV incluido como base de ingreso.
- **SI resta envío.**
- **NO calcula comisión.**
- TC Fallback si no hay tipo de cambio: `1.0`

---

## Método 2 — Excel Consolidado: `export_profits_excel()`
**Líneas:** 1389–1397
**Ruta:** `GET /api/profits/export?report_type=consolidated`

### Fórmula
```
base_sin_igv = total_venta / 1.18
ganancia     = base_sin_igv - costo_pen - costo_envio - comision
margen       = ganancia / base_sin_igv × 100
```

### Cálculo con #43453
```
base_sin_igv = round(38.49 / 1.18, 2) = 32.62
comision     = 0  (no es pago con tarjeta)
ganancia     = 32.62 - 7.53 - 8.50 - 0 = 16.59
margen       = 16.59 / 32.62 × 100 = 50.86%
```

### Resultado
| Ganancia (PEN) | Margen % |
|---|---|
| **S/ 16.59** | **50.86%** |

### Características
- **SI descuenta IGV** (divide por 1.18). La base de ganancia es el ingreso sin impuesto.
- **SI resta envío.**
- **comision_pen = 0** siempre (fue una variable no definida que causaba el crash; ahora está fijada en 0).
- Margen calculado sobre `base_sin_igv`, no sobre total.

---

## Método 3 — Excel Detallado: `export_profits_excel()`
**Líneas:** 1350–1356
**Ruta:** `GET /api/profits/export?report_type=detailed`

### Fórmula (por línea de item)
```
venta_item    = _line_total + _line_tax   (total del item inc. IGV)
base_item     = round(venta_item / 1.18, 2)
costo_item    = costo_unit_usd × qty × TC
ganancia_item = base_item - costo_item
margen_item   = ganancia_item / base_item × 100
```

### Cálculo con #43453 (1 item, qty=1)
```
venta_item = 29.99       (Precio Venta Item columna L en Excel)
base_item  = round(29.99 / 1.18, 2) = 25.42
             (nota: _line_total real en DB puede ser 25.41 → pequeña diferencia por redondeo)
costo_item = 2 × 1 × 3.765 = 7.53
ganancia   = 25.42 - 7.53 = 17.89  (Excel muestra 17.88 por redondeo interno de _line_total)
margen     = 17.89 / 25.42 × 100 = 70.38%   (Excel muestra 70.37%)
```

### Resultado
| Ganancia Línea (PEN) | Margen Línea % |
|---|---|
| **S/ 17.88** | **70.37%** |

### Características
- **SI descuenta IGV** (divide venta_item por 1.18).
- **NO resta envío** — el envío es un campo de orden, no de ítem. Se muestra en columna separada "Envío Pedido (PEN)".
- **La ganancia mostrada NO es la ganancia real del pedido** si tiene envío: falta restar S/ 8.50.
- Si sumas la Ganancia Línea de todos los ítems de un pedido y restas el envío, obtienes un valor cercano al Consolidado (diferencia por redondeo de IGV).

---

## Cuadro resumen de diferencias

| Criterio | UI | Excel Consolidado | Excel Detallado |
|---|---|---|---|
| **Método/función** | `api_profits()` L.549 | `export_profits_excel()` L.1391 | `export_profits_excel()` L.1351 |
| **Base de ingreso** | total_venta (con IGV) | total_venta / 1.18 (sin IGV) | venta_item / 1.18 (sin IGV) |
| **Descuenta IGV** | NO | SI | SI |
| **Descuenta envío** | SI | SI | NO (se muestra aparte) |
| **Descuenta comisión** | NO | NO (comision=0) | NO |
| **Granularidad** | Por pedido | Por pedido | Por línea de ítem |
| **Margen base** | total_venta | base_sin_igv | base_item_sin_igv |
| **TC Fallback** | 1.0 | (igual que API) | (igual que API) |
| **Ganancia #43453** | **S/ 22.46** | **S/ 16.59** | **S/ 17.88** (sin envío) |
| **Margen #43453** | **58.35%** | **50.86%** | **70.37%** (sin envío) |

---

## Cuál es la fórmula correcta

Desde el punto de vista contable peruano:

- El IGV (18%) es un impuesto que el negocio recauda para SUNAT. **No es ingreso del negocio.**
- La ganancia real debe calcularse sobre la **base imponible** (precio sin IGV).
- La fórmula del **Excel Consolidado es la más correcta** para medir la rentabilidad real.

### Fórmula recomendada (unificada)
```
base_sin_igv = total_venta / 1.18
ganancia     = base_sin_igv - costo_pen - costo_envio
margen       = ganancia / base_sin_igv × 100
```

### Impacto del cambio en UI
Actualmente la UI sobreestima la ganancia en ~18%:
- UI muestra S/ 22.46 vs. real S/ 16.59 (diferencia = S/ 5.87 = exactamente el IGV del pedido)

---

## Problema adicional: Detallado sin envío

El detallado muestra ganancia por ítem sin restar el envío del pedido.
Esto puede confundir porque:
- Si el pedido tiene 3 ítems, cada uno muestra ganancia "buena" pero el envío no está repartido.
- La suma de "Ganancia Línea" de todos los ítems NO equivale a la ganancia real del pedido.

**Opciones:**
1. Agregar una fila al final de cada pedido con el envío como fila negativa.
2. Repartir el envío proporcional a cada ítem según su venta.
3. Dejar como está pero agregar nota aclaratoria en el Excel.

---

## Método adicional: `api_profits_externos()` (UI Externos)
**Líneas:** 744–745
**Ruta:** `GET /api/profits/externos`

```python
ganancia = total_venta_pen - costo_total_pen - costo_envio_pen
margen   = ganancia / total_venta_pen × 100
```

Mismo problema que la UI principal: **no descuenta IGV**. Consistente con `api_profits()` pero incorrecto desde el punto de vista contable.

---

## Método adicional: `export_profits_externos_excel()` (Excel Externos)
**Líneas:** 946–953
**Ruta:** `GET /api/profits/externos/export`

```python
base_imponible = round(total_venta / 1.18, 2)
comision       = total_venta * 0.05  si método contiene "TARJETA", sino 0
ganancia       = base_imponible - costo_pen - envio - comision
margen         = ganancia / base_imponible × 100
```

Único método que calcula comisión por tarjeta (5%). Correcto en términos de IGV.

---

## Resumen de acciones recomendadas

| # | Acción | Archivo | Línea |
|---|---|---|---|
| 1 | Unificar UI (`api_profits`) para usar `total/1.18` como base | `reports.py` | L.549–550 |
| 2 | Unificar UI externos (`api_profits_externos`) igual | `reports.py` | L.744–745 |
| 3 | Decidir qué hacer con envío en detallado (repartir o nota) | `reports.py` | L.1350–1384 |
| 4 | Implementar comisión tarjeta en Excel Consolidado woo si aplica | `reports.py` | L.1394 |
