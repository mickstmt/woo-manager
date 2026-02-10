-- =========================================================================
-- Script de Exportación de Pedidos (WooCommerce + WhatsApp)
-- Fecha: 2026-02-06
-- Rango: 1 de Noviembre 2025 - 31 de Enero 2026
-- Campos: Plataforma, Nombre, Correo, Teléfono, Venta Total
-- =========================================================================

SELECT 
    -- Información del Pedido
    o.id AS 'ID Pedido',
    COALESCE(om_number.meta_value, CAST(o.id AS CHAR)) AS 'Número Pedido',
    
    -- Columna Plataforma (Lógica W-XXXXX)
    CASE 
        WHEN om_number.meta_value LIKE 'W-%' THEN 'WhatsApp'
        ELSE 'Web IziStore'
    END AS 'Plataforma',

    DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) AS 'Fecha Creación',
    o.status AS 'Estado',
    
    -- Información del Cliente (Facturación)
    CONCAT(ba.first_name, ' ', ba.last_name) AS 'Nombre Completo',
    ba.email AS 'Correo Electrónico',
    RIGHT(REPLACE(ba.phone, ' ', ''), 9) AS 'Teléfono',
    
    -- Información Financiera
    o.total_amount AS 'Venta Total (PEN)'

FROM wpyz_wc_orders o

-- Unir con metadatos para obtener número personalizado (WhatsApp W-XXXXX)
LEFT JOIN wpyz_wc_orders_meta om_number 
    ON o.id = om_number.order_id 
    AND om_number.meta_key = '_order_number'

-- Unir con dirección de facturación para datos del cliente
LEFT JOIN wpyz_wc_order_addresses ba 
    ON o.id = ba.order_id 
    AND ba.address_type = 'billing'

WHERE 
    -- Filtro de Fechas (Ajustado a hora local Perú UTC-5)
    DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) BETWEEN '2025-11-01' AND '2026-01-31'
    
    -- Excluir pedidos en papelera (opcional)
    AND o.status != 'trash'

ORDER BY 
    o.date_created_gmt DESC;
