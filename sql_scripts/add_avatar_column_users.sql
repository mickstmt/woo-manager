-- Add avatar_file column to woo_users table
ALTER TABLE woo_users ADD COLUMN avatar_file VARCHAR(255) DEFAULT NULL;
