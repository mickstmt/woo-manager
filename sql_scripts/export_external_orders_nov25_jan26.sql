-- =========================================================================
-- Script de Exportación de Pedidos EXTERNOS (woo_orders_ext)
-- Fecha: 2026-02-06
-- Rango: 1 de Noviembre 2025 - 31 de Enero 2026
-- Campos: Plataforma, Nombre, Correo, Teléfono, Venta Total
-- =========================================================================

SELECT 
    -- Información del Pedido
    o.id AS 'ID Pedido',
    o.order_number AS 'Número Pedido',
    
    -- Columna Plataforma
    COALESCE(NULLIF(o.external_source, ''), 'Externo') AS 'Plataforma',

    DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) AS 'Fecha Creación',
    o.status AS 'Estado',
    
    -- Información del Cliente
    CONCAT(o.customer_first_name, ' ', o.customer_last_name) AS 'Nombre Completo',
    o.customer_email AS 'Correo Electrónico',
    RIGHT(REPLACE(o.customer_phone, ' ', ''), 9) AS 'Teléfono', -- Eliminar espacios y tomar últimos 9
    
    -- Información Financiera
    o.total_amount AS 'Venta Total (PEN)'

FROM woo_orders_ext o

WHERE 
    -- Filtro de Fechas (Ajustado a hora local Perú UTC-5)
    DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) BETWEEN '2025-11-01' AND '2026-01-31'
    
    -- Excluir pedidos en papelera (si aplica, o estados no deseados)
    AND o.status != 'trash'

ORDER BY 
    o.date_created_gmt DESC;
