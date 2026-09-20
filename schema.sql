-- 1. جدول المستخدمين
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    permissions JSONB DEFAULT '{"can_view_buy_price": true}'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. جدول الموردين
CREATE TABLE IF NOT EXISTS suppliers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    phone VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. جدول الأجهزة
CREATE TABLE IF NOT EXISTS devices (
    id SERIAL PRIMARY KEY,
    category VARCHAR(100) NOT NULL,
    model VARCHAR(150) NOT NULL,
    storage VARCHAR(50),
    ram VARCHAR(50),
    battery_health INT DEFAULT 100,
    accessories TEXT,
    imei_serial VARCHAR(150) UNIQUE NOT NULL,
    buy_price DECIMAL(10, 2) NOT NULL,
    supplier_id INT REFERENCES suppliers(id) ON DELETE SET NULL,
    notes TEXT,
    is_sold BOOLEAN DEFAULT FALSE,
    buy_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by_user_id INT REFERENCES users(id)
);

-- 4. جدول المبيعات
CREATE TABLE IF NOT EXISTS sales (
    id SERIAL PRIMARY KEY,
    device_id INT REFERENCES devices(id) ON DELETE CASCADE,
    sell_price DECIMAL(10, 2) NOT NULL,
    customer_name VARCHAR(150) NOT NULL,
    customer_phone VARCHAR(50),
    cash_received DECIMAL(10, 2) NOT NULL,
    remaining_balance DECIMAL(10, 2) NOT NULL,
    payment_status VARCHAR(50) DEFAULT 'PAID',
    net_profit DECIMAL(10, 2) NOT NULL,
    notes TEXT,
    sell_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sold_by_user_id INT REFERENCES users(id)
);

-- 5. جدول مدفوعات العملاء (ديون العملاء)
CREATE TABLE IF NOT EXISTS customer_payments (
    id SERIAL PRIMARY KEY,
    sale_id INT REFERENCES sales(id) ON DELETE CASCADE,
    payment_amount DECIMAL(10, 2) NOT NULL,
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    received_by_user_id INT REFERENCES users(id)
);

-- 6. جدول فواتير الموردين
CREATE TABLE IF NOT EXISTS supplier_invoices (
    id SERIAL PRIMARY KEY,
    supplier_id INT REFERENCES suppliers(id) ON DELETE CASCADE,
    total_amount DECIMAL(10, 2) NOT NULL,
    paid_amount DECIMAL(10, 2) DEFAULT 0,
    remaining_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(50) DEFAULT 'UNPAID',
    invoice_date DATE DEFAULT CURRENT_DATE,
    created_by_user_id INT REFERENCES users(id)
);

-- 7. جدول مدفوعات الموردين
CREATE TABLE IF NOT EXISTS supplier_payments (
    id SERIAL PRIMARY KEY,
    supplier_id INT REFERENCES suppliers(id) ON DELETE CASCADE,
    payment_amount DECIMAL(10, 2) NOT NULL,
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    received_by_user_id INT REFERENCES users(id)
);

-- 8. إضافة مستخدم Admin افتراضي للتسجيل فوراً
INSERT INTO users (username, password_hash, full_name, permissions)
VALUES ('admin', 'admin123', 'مدير النظام', '{"can_view_buy_price": true}'::jsonb)
ON CONFLICT (username) DO NOTHING;
