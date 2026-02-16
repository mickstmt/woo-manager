# Mejoras para Kanban de Despacho en Móvil

## 📱 Problema Identificado

Al usar el Kanban de despacho en dispositivos móviles, existe un **conflicto entre gestos táctiles**:

- **Scroll touch**: El usuario quiere desplazarse por el módulo
- **Drag and drop**: El usuario quiere arrastrar las tarjetas del kanban

Este conflicto genera que:
- Al intentar hacer scroll, se activa accidentalmente el drag
- Al intentar arrastrar una tarjeta, se hace scroll en lugar de drag
- La experiencia móvil es frustrante e imprecisa

---

## 🎯 Soluciones Propuestas

### **Opción A: Long Press (Presión Larga)** ⭐ RECOMENDADA

#### Descripción
El usuario debe **mantener presionado ~500ms** para activar el modo drag.

#### Comportamiento
- **Toque simple/deslizamiento**: Scroll normal
- **Mantener presionado 500ms**: Activa el drag con feedback visual
  - Vibración háptica (si está disponible)
  - Sombra elevada en la tarjeta
  - Posible cambio de opacidad/escala

#### Ventajas ✅
- Intuitivo y familiar (patrón usado en iOS/Android)
- Diferencia claramente entre scroll y drag
- No requiere cambios visuales importantes
- Mantiene la experiencia de drag-and-drop
- Fácil de implementar técnicamente

#### Desventajas ⚠️
- Requiere que el usuario aprenda el gesto
- Puede parecer menos responsive al principio
- Necesita un tutorial/tooltip la primera vez

#### Implementación Técnica
```javascript
// Ejemplo con SortableJS
new Sortable(element, {
    delay: 500, // 500ms de presión antes de activar drag
    delayOnTouchOnly: true, // Solo en dispositivos táctiles
    animation: 150,
    // Feedback visual al activar
    onChoose: function(evt) {
        evt.item.classList.add('dragging');
        // Vibración opcional
        if (navigator.vibrate) {
            navigator.vibrate(50);
        }
    }
});
```

---

### **Opción B: Drag Handle (Icono de Agarre)**

#### Descripción
Agregar un **ícono específico** (⋮⋮ o ☰) visible solo en móvil que debe tocarse para arrastrar.

#### Comportamiento
- Tocar el handle → permite arrastrar
- Tocar cualquier otra parte de la tarjeta → scroll normal

#### Ventajas ✅
- Muy claro y sin ambigüedad
- Usado en apps populares (Trello, Asana, Notion)
- Sin conflictos entre gestos
- No requiere aprendizaje (es obvio)

#### Desventajas ⚠️
- Requiere precisión en el toque (el handle puede ser pequeño)
- Cambio visual en las tarjetas
- Ocupa espacio en el diseño
- Puede ser difícil de tocar si es muy pequeño

#### Implementación Técnica
```javascript
// HTML: Agregar handle a cada tarjeta
<div class="kanban-card">
    <div class="drag-handle d-md-none">⋮⋮</div>
    <!-- Resto del contenido -->
</div>

// JavaScript
new Sortable(element, {
    handle: '.drag-handle', // Solo se puede arrastrar desde aquí
    animation: 150
});
```

```css
.drag-handle {
    cursor: grab;
    padding: 8px;
    color: #999;
    font-size: 20px;
}

/* Ocultar en desktop */
@media (min-width: 768px) {
    .drag-handle {
        display: none !important;
    }
}
```

---

### **Opción C: Modo Toggle (Cambio de Modo)**

#### Descripción
Agregar un botón que alterne entre **"Modo Scroll"** 📜 y **"Modo Editar"** ✏️.

#### Comportamiento
- **Por defecto**: Modo scroll (drag desactivado)
- **Al activar "Modo Editar"**: Se pueden arrastrar tarjetas libremente
- Indicador visual del modo activo

#### Ventajas ✅
- Sin conflictos entre gestos
- Control total sobre cuándo se puede arrastrar
- Muy claro para el usuario

#### Desventajas ⚠️
- Requiere un paso extra cada vez (activar/desactivar modo)
- Menos fluido que drag-and-drop directo
- Puede resultar tedioso si se usa frecuentemente

#### Implementación Técnica
```javascript
let dragEnabled = false;
let sortableInstance = null;

// Botón para toggle
$('#toggleDragMode').on('click', function() {
    dragEnabled = !dragEnabled;

    if (dragEnabled) {
        // Activar drag
        sortableInstance = new Sortable(element, { /* config */ });
        $(this).html('<i class="bi bi-check-circle"></i> Modo Editar');
        $('.kanban-column').addClass('edit-mode');
    } else {
        // Desactivar drag
        if (sortableInstance) {
            sortableInstance.destroy();
        }
        $(this).html('<i class="bi bi-cursor"></i> Modo Scroll');
        $('.kanban-column').removeClass('edit-mode');
    }
});
```

---

### **Opción D: Menú Contextual**

#### Descripción
En móvil, **eliminar drag-and-drop** y usar un menú de opciones al tocar la tarjeta.

#### Comportamiento
- Tocar tarjeta → Abre menú contextual
- Menú muestra: "Mover a..." con lista de columnas
- Seleccionar columna destino → Mueve la tarjeta

#### Ventajas ✅
- Sin conflictos técnicos
- Simple de implementar
- Funciona en cualquier dispositivo

#### Desventajas ⚠️
- Pierde la interactividad visual del kanban
- Menos intuitivo que drag-and-drop
- Requiere más toques para completar la acción
- No se siente como un kanban real

#### Implementación Técnica
```javascript
// Detectar toque largo en tarjeta
$('.kanban-card').on('touchstart', function(e) {
    const card = $(this);
    const touchTimer = setTimeout(function() {
        showMoveMenu(card);
    }, 500);

    card.on('touchend touchmove', function() {
        clearTimeout(touchTimer);
    });
});

function showMoveMenu(card) {
    const columns = ['Pendiente', 'En Preparación', 'En Ruta', 'Entregado'];
    // Mostrar modal/dropdown con opciones
    // Al seleccionar, mover la tarjeta
}
```

---

### **Opción E: Combinación Inteligente** 🌟 MÁS COMPLETA

#### Descripción
Implementar **Long Press como principal** + **Drag Handle opcional** para mayor flexibilidad.

#### Comportamiento
1. **Presión larga (500ms)**: Activa drag en toda la tarjeta
2. **Handle visible**: Para drag inmediato sin esperar
3. **Feedback visual**: Vibración + sombra al activar
4. **Detección automática**: Solo en dispositivos móviles

#### Ventajas ✅
- Lo mejor de ambos mundos
- Flexible para diferentes preferencias de usuario
- Mantiene la experiencia de kanban
- Feedback claro y responsivo

#### Desventajas ⚠️
- Más complejo de implementar
- Requiere más testing

#### Implementación Técnica
```javascript
// Detectar si es móvil
const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);

const sortableConfig = {
    animation: 150,
    ghostClass: 'ghost-card',
    chosenClass: 'chosen-card',
    dragClass: 'dragging-card',

    // Configuración específica para móvil
    ...(isMobile && {
        delay: 500,
        delayOnTouchOnly: true,
        handle: '.drag-handle, .kanban-card', // Handle O toda la tarjeta con delay
        touchStartThreshold: 5 // Píxeles de tolerancia
    }),

    // Eventos
    onChoose: function(evt) {
        evt.item.classList.add('dragging');
        if (navigator.vibrate) {
            navigator.vibrate(50);
        }
    },

    onUnchoose: function(evt) {
        evt.item.classList.remove('dragging');
    }
};

// Inicializar Sortable
new Sortable(element, sortableConfig);
```

```css
/* Estilos para feedback visual */
.dragging-card {
    opacity: 0.8;
    transform: scale(1.05);
    box-shadow: 0 8px 16px rgba(0,0,0,0.3);
    transition: all 0.2s ease;
}

.ghost-card {
    opacity: 0.4;
    background: #f0f0f0;
}

.drag-handle {
    display: none; /* Oculto por defecto */
}

/* Mostrar handle solo en móvil */
@media (max-width: 767px) {
    .drag-handle {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 30px;
        color: #999;
        cursor: grab;
    }

    .drag-handle:active {
        cursor: grabbing;
    }
}
```

---

## 📊 Comparación Rápida

| Característica | Long Press | Drag Handle | Modo Toggle | Menú Contextual | Combinación |
|---------------|------------|-------------|-------------|-----------------|-------------|
| **Intuitivo** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Sin conflictos** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Rapidez de uso** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Fácil implementación** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Mantiene UX kanban** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Accesibilidad** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

---

## 🚀 Recomendación Final

### Para implementación rápida y efectiva:
**Opción A: Long Press**
- Menos cambios de código
- Buena experiencia de usuario
- Soluciona el problema principal

### Para la mejor experiencia posible:
**Opción E: Combinación**
- Más flexible
- Cubre diferentes preferencias
- Experiencia premium

---

## 📝 Siguiente Paso

1. **Revisar opciones** con el equipo/usuarios
2. **Decidir cuál implementar**
3. **Hacer pruebas** en diferentes dispositivos
4. **Iterar** basándose en feedback

---

## 🔗 Referencias Técnicas

- [SortableJS Documentation](https://github.com/SortableJS/Sortable)
- [Touch Events API](https://developer.mozilla.org/en-US/docs/Web/API/Touch_events)
- [Mobile UX Best Practices](https://www.nngroup.com/articles/mobile-ux/)

---

**Documento creado**: 2026-02-16
**Módulo afectado**: Kanban de Despacho (`dispatch_board.html`, `dispatch.js`)
**Prioridad**: Media-Alta (afecta usabilidad móvil)
