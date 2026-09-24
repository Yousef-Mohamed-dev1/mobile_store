-- 1. جدول المستخدمين (Users)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    permissions JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. جدول الموردين (Suppliers)
CREATE TABLE IF NOT EXISTS suppliers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. جدول الأجهزة / المخزون (Devices)
CREATE TABLE IF NOT EXISTS devices (
    id SERIAL PRIMARY KEY,
    category VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    storage VARCHAR(20),
    ram VARCHAR(20),
    battery_health INT DEFAULT 100,
    accessories TEXT,
    imei_serial VARCHAR(100) UNIQUE NOT NULL,
    buy_price NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    supplier_id INT REFERENCES suppliers(id) ON DELETE SET NULL,
    notes TEXT,
    is_sold BOOLEAN NOT NULL DEFAULT FALSE,
    created_by_user_id INT REFERENCES users(id),
    buy_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. جدول فواتير الموردين (Supplier Invoices)
CREATE TABLE IF NOT EXISTS supplier_invoices (
    id SERIAL PRIMARY KEY,
    supplier_id INT NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    total_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    paid_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    remaining_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    status VARCHAR(20) NOT NULL DEFAULT 'UNPAID',
    invoice_date DATE DEFAULT CURRENT_DATE,
    created_by_user_id INT REFERENCES users(id)
);

-- 5. جدول عمليات البيع (Sales)
CREATE TABLE IF NOT EXISTS sales (
    id SERIAL PRIMARY KEY,
    device_id INT UNIQUE NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    sell_price NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    customer_name VARCHAR(100) NOT NULL,
    customer_phone VARCHAR(20),
    cash_received NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    remaining_balance NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    payment_status VARCHAR(20) NOT NULL DEFAULT 'PAID',
    net_profit NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    notes TEXT,
    sold_by_user_id INT REFERENCES users(id),
    sell_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. جدول مدفوعات العملاء للديون (Customer Payments)
CREATE TABLE IF NOT EXISTS customer_payments (
    id SERIAL PRIMARY KEY,
    sale_id INT NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
    payment_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    received_by_user_id INT REFERENCES users(id)
);

-- 7. جدول مدفوعات ديون الموردين (Supplier Payments)
CREATE TABLE IF NOT EXISTS supplier_payments (
    id SERIAL PRIMARY KEY,
    supplier_id INT NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    payment_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    received_by_user_id INT REFERENCES users(id)
);

-- 8. جدول السيولة المالية المضافة ورأس المال الابتدائي (Capital Transactions)
CREATE TABLE IF NOT EXISTS capital_transactions (
    id SERIAL PRIMARY KEY,
    amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    transaction_type VARCHAR(20) NOT NULL DEFAULT 'INJECTION',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by_user_id INT REFERENCES users(id)
);

-- الفهارس لتسريع عملية البحث في النظام (Indexes)
CREATE INDEX IF NOT EXISTS idx_devices_imei ON devices(imei_serial);
CREATE INDEX IF NOT EXISTS idx_devices_is_sold ON devices(is_sold);
CREATE INDEX IF NOT EXISTS idx_sales_sell_date ON sales(sell_date);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(LOWER(username));

-- إضافة حساب المسؤول الرئيسي (Admin) افتراضياً
INSERT INTO users (username, password_hash, full_name, permissions)
VALUES (
    'admin', 
    'admin123',
    'المدير العام', 
    '{
        "can_view_buy_price": true,
        "can_manage_inventory": true,
        "can_manage_users": true,
        "can_view_reports": true,
        "can_process_returns": true,
        "can_edit_prices": true
    }'::jsonb
) ON CONFLICT (username) DO NOTHING;