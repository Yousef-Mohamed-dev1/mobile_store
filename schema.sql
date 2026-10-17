-- =================================================================================
-- المخطط الكامل والمحدث لقاعدة البيانات (PostgreSQL) - مركز هشام كيوان لإدارة الهواتف
-- =================================================================================

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL DEFAULT 'مدير النظام',
    role VARCHAR(30) DEFAULT 'custom',
    permissions JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS suppliers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(30),
    supplier_type VARCHAR(50) DEFAULT 'تاجر',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS supplier_invoices (
    id SERIAL PRIMARY KEY,
    supplier_id INT REFERENCES suppliers(id),
    total_amount NUMERIC(12, 2) DEFAULT 0.00,
    paid_amount NUMERIC(12, 2) DEFAULT 0.00,
    remaining_amount NUMERIC(12, 2) DEFAULT 0.00,
    supplier_credit NUMERIC(12, 2) DEFAULT 0.00,
    status VARCHAR(20) DEFAULT 'UNPAID',
    invoice_date DATE DEFAULT CURRENT_DATE,
    created_by_user_id INT REFERENCES users(id),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS devices (
    id SERIAL PRIMARY KEY,
    category VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    storage VARCHAR(50),
    ram VARCHAR(50) DEFAULT 'لا يوجد',
    battery_health INT DEFAULT 0,
    accessories TEXT,
    device_condition VARCHAR(20) DEFAULT 'مستعمل',
    has_box BOOLEAN DEFAULT FALSE,
    color VARCHAR(50) DEFAULT 'أسود',
    has_tax BOOLEAN DEFAULT FALSE,
    imei_serial VARCHAR(100) NOT NULL,
    buy_price NUMERIC(12, 2) NOT NULL,
    initial_selling_price NUMERIC(12, 2) DEFAULT NULL,
    supplier_id INT REFERENCES suppliers(id),
    invoice_id INT REFERENCES supplier_invoices(id),
    notes TEXT,
    is_sold BOOLEAN DEFAULT FALSE,
    is_deleted BOOLEAN DEFAULT FALSE,
    is_archived BOOLEAN DEFAULT FALSE,
    archived_at TIMESTAMP DEFAULT NULL,
    archived_by_user_id INT REFERENCES users(id),
    buy_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by_user_id INT REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS sales (
    id SERIAL PRIMARY KEY,
    device_id INT REFERENCES devices(id),
    original_price NUMERIC(12, 2) DEFAULT 0.00,
    discount NUMERIC(12, 2) DEFAULT 0.00,
    sell_price NUMERIC(12, 2) NOT NULL,
    customer_name VARCHAR(100) NOT NULL DEFAULT 'عميل نقدي',
    customer_phone VARCHAR(30),
    cash_received NUMERIC(12, 2) DEFAULT 0.00,
    remaining_balance NUMERIC(12, 2) DEFAULT 0.00,
    net_profit NUMERIC(12, 2) DEFAULT 0.00,
    notes TEXT,
    sell_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by_user_id INT REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS customer_payments (
    id SERIAL PRIMARY KEY,
    sale_id INT REFERENCES sales(id) ON DELETE CASCADE,
    payment_amount NUMERIC(12, 2) NOT NULL,
    notes TEXT,
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by_user_id INT REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS supplier_payments (
    id SERIAL PRIMARY KEY,
    invoice_id INT REFERENCES supplier_invoices(id) ON DELETE CASCADE,
    supplier_id INT REFERENCES suppliers(id),
    payment_amount NUMERIC(12, 2) NOT NULL,
    notes TEXT,
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by_user_id INT REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS capital_transactions (
    id SERIAL PRIMARY KEY,
    amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    transaction_type VARCHAR(20) NOT NULL DEFAULT 'INJECTION',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by_user_id INT REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INT,
    user_name VARCHAR(100),
    action_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INT,
    description TEXT,
    old_values JSONB DEFAULT '{}'::jsonb,
    new_values JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_devices_imei ON devices(imei_serial);
CREATE INDEX IF NOT EXISTS idx_devices_inv_id ON devices(invoice_id);
CREATE INDEX IF NOT EXISTS idx_devices_archived ON devices(is_archived);
CREATE INDEX IF NOT EXISTS idx_sales_device_id ON sales(device_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);
