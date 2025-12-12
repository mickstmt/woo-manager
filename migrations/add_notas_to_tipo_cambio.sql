-- Agregar columna 'notas' a la tabla woo_tipo_cambio
-- Esta columna permite agregar observaciones o comentarios sobre el tipo de cambio del día

ALTER TABLE woo_tipo_cambio
ADD COLUMN notas TEXT NULL
COMMENT 'Observaciones o notas sobre el tipo de cambio';
