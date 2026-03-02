-- SQL script to add unique constraint to order_id in woo_chamo_shipments
-- To prevent duplicate shipment registrations for the same order
-- 1. Identify and remove any existing duplicates first (keeping the one with the lowest ID)
DELETE s1
FROM woo_chamo_shipments s1
    INNER JOIN woo_chamo_shipments s2
WHERE s1.id > s2.id
    AND s1.order_id = s2.order_id;
-- 2. Add the unique index
ALTER TABLE woo_chamo_shipments
ADD UNIQUE KEY `idx_unique_order_id` (order_id);