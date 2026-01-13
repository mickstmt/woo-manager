# Propuestas de Mejora de UX/UI - Modernización y Diseño

> [!NOTE]  
> Este documento se enfoca exclusivamente en la experiencia visual, la estética y la interfaz de usuario, complementando las mejoras funcionales ya existentes. El objetivo es consolidar el estilo "sobrio, elegante y moderno" que se ha iniciado con la implementación del Modo Oscuro.

## 1. Identidad Visual y Sistema de Diseño (Design System)

Para asegurar consistencia en futuras implementaciones, se sugiere establecer bases sólidas de diseño:

### 🎨 Paleta de Colores "Premium"
Actualmente utilizamos un gradiente azul/violeta y colores Bootstrap estándar. Sugiero refinar la paleta:
-   **Primario:** Mantener el Azul/Indigo actual pero estandarizarlo en variables CSS globales (ya iniciado en `sidebar.css`).
-   **Acentos:** Reducir el uso de colores saturados ("rojo error", "verde éxito") en grandes superficies. Usarlos solo en textos, bordes o iconos pequeños para mantener la sobriedad.
-   **Superficies Oscuras:** Evitar el negro absoluto (`#000000`). Utilizar escalas de grises azulados profundos (`#111827`, `#1f2937`) como se aplicó en el sidebar, lo que reduce la fatiga visual y se percibe más elegante.

### 🔠 Tipografía
-   Evaluar una tipografía *sans-serif* geométrica y moderna (ej. **Inter**, **DM Sans** o **Plus Jakarta Sans**).
-   Aumentar ligeramente el espaciado (tracking) en títulos en mayúsculas para dar aire sofisticado.
-   Usar pesos de fuente (font-weights) más variados: *Light* para detalles secundarios, *SemiBold* para datos clave, evitando el *Bold* genérico.

---

## 2. Micro-interacciones y Animaciones

El "sentimiento" de modernidad viene del movimiento sutil.

### 🏎️ Transiciones Activas
-   **Hover Cards:** Al pasar el mouse sobre tarjetas (como en el Dashboard actual), aplicar un efecto de elevación suave (`translateY` negativa) y sombra suavizada.
-   **Botones:** Efecto "ripple" sutil o cambio de brillo en lugar de cambio brusco de color.
-   **Modales:** Entrada suave con *fade-in* y desplazamiento ligero hacia arriba, evitando la aparición repentina.

### ⏳ Estados de Carga (Skeletons)
-   Reemplazar los spinners de carga (`Loading...`) que bloquean la vista por **Skeletons** (esqueletos grises animados que imitan el contenido). Esto reduce la percepción del tiempo de espera y se ve mucho más profesional.

---

## 3. Optimización de Gestión de Pedidos (Dispatch Board)

El Kanban ya funciona bien, pero puede pulirse visualmente:

### 🏷️ Badges y Etiquetas
-   **Unificar Estilos:** Usar badges con fondo transparente y borde de color (estilo *outline*) o con fondo muy tenue (alpha 10%) para no sobrecargar visualmente el tablero.
-   **Prioridad:** Los bordes de color a la izquierda son buenos. Podría añadirse un sutil resplandor ("glow") a las tarjetas Urgentes en modo oscuro para que destaquen sin ser invasivas.

### 📱 Experiencia Móvil
-   Asegurar que el *Drag & Drop* se sienta natural en móviles (vibración háptica al levantar una tarjeta).
-   Ocultar columnas menos relevantes en vista móvil o permitir *scroll* horizontal suave tipo "snap".

---

## 4. Dashboard y Visualización de Datos

### 📊 Gráficos Elegantes
-   Si se añaden gráficos en el futuro, usar librerías como `ApexCharts` o `Chart.js` con temas oscuros nativos.
-   Eliminar líneas de cuadrícula (grid lines) innecesarias para "limpiar" el gráfico.
-   Usar gradientes en las áreas de los gráficos de línea para dar profundidad.

### 🍱 Widgets de Resumen
-   Mantener el estilo "Glassmorphism" (fondo semitransparente con desenfoque) aplicado en el header de bienvenida para otros elementos destacados, como alertas importantes.

---

## 5. Formularios e Inputs

### 🖱️ Inputs Modernos
-   Abandonar el estilo de input estándar ("caja con borde gris").
-   Implementar inputs con:
    -   Borde inferior solamente (estilo Material minimalista) o...
    -   Borde completo muy suave que se ilumina (glow) al recibir foco.
    -   Etiquetas flotantes (Floating Labels) que suben al escribir, ahorrando espacio vertical.

---

## 6. Consistencia en Modo Oscuro (Roadmap Inmediato)

Para cerrar la implementación actual:
-   **Tablas de Datos:** Asegurar que todas las tablas (Inventario, Productos) tengan filas alternadas (zebra-striping) con una opacidad muy baja (ej. 3%) en modo oscuro para no crear "ruido" visual.
-   **Fechas:** Estandarizar el formato de fechas. Usar fuentes monoespaciadas para números y fechas en tablas mejora la legibilidad y alineación vertical.

---

### 💡 Conclusión

La adopción del dark mode es un excelente primer paso. La siguiente fase debería centrarse en "suavizar" la interfaz: bordes más redondeados, sombras más difusas, animaciones más orgánicas y menos "cajas duras". Esto elevará la percepción de calidad del producto final.
