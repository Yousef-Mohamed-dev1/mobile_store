-- =================================================================================
-- مركز هشام كيوان لإدارة الهواتف الذكية
-- المخطط الكامل والمحدث لقاعدة البيانات (PostgreSQL)
-- يدعم التثبيت الجديد والترقية التلقائية الآمنة لقواعد البيانات الحالية دون فقدان أي بيانات
-- =================================================================================

-- 1. جدول المستخدمين والصلاحيات
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL DEFAULT 'مدير النظام',
    permissions JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. جدول الموردين (تاجر / زبون)
CREATE TABLE IF NOT EXISTS suppliers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(30),
    supplier_type VARCHAR(50) DEFAULT 'تاجر',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. جدول فواتير الموردين (المديونيات)
CREATE TABLE IF NOT EXISTS supplier_invoices (
    id SERIAL PRIMARY KEY,
    supplier_id INT REFERENCES suppliers(id),
    total_amount NUMERIC(12, 2) DEFAULT 0.00,
    paid_amount NUMERIC(12, 2) DEFAULT 0.00,
    remaining_amount NUMERIC(12, 2) DEFAULT 0.00,
    status VARCHAR(20) DEFAULT 'UNPAID',
    invoice_date DATE DEFAULT CURRENT_DATE,
    created_by_user_id INT REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. جدول الأجهزة والمخزون (يدعم جديد/مستعمل، بعلبة/بدون، ملاحظات الشراء، والحذف الذكي)
CREATE TABLE IF NOT EXISTS devices (
    id SERIAL PRIMARY KEY,
    category VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    storage VARCHAR(50),
    ram VARCHAR(50) DEFAULT 'لا يوجد',
    battery_health INT DEFAULT 0,
    accessories TEXT,
    device_condition VARCHAR(20) DEFAULT 'مستعمل',
    has_box BOOLEAN DEFAULT TRUE,
    imei_serial VARCHAR(100) NOT NULL,
    buy_price NUMERIC(12, 2) NOT NULL,
    supplier_id INT REFERENCES suppliers(id),
    invoice_id INT REFERENCES supplier_invoices(id),
    notes TEXT,
    is_sold BOOLEAN DEFAULT FALSE,
    is_deleted BOOLEAN DEFAULT FALSE,
    buy_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by_user_id INT REFERENCES users(id)
);

-- 5. جدول المبيعات والخرج (يدعم ملاحظات البيع)
CREATE TABLE IF NOT EXISTS sales (
    id SERIAL PRIMARY KEY,
    device_id INT REFERENCES devices(id),
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

-- 6. جدول تحصيلات ديون العملاء (الخرج)
CREATE TABLE IF NOT EXISTS customer_payments (
    id SERIAL PRIMARY KEY,
    sale_id INT REFERENCES sales(id) ON DELETE CASCADE,
    payment_amount NUMERIC(12, 2) NOT NULL,
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by_user_id INT REFERENCES users(id)
);

-- 7. جدول دفعات وأقساط الموردين
CREATE TABLE IF NOT EXISTS supplier_payments (
    id SERIAL PRIMARY KEY,
    invoice_id INT REFERENCES supplier_invoices(id) ON DELETE CASCADE,
    supplier_id INT REFERENCES suppliers(id),
    payment_amount NUMERIC(12, 2) NOT NULL,
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by_user_id INT REFERENCES users(id)
);

-- 8. جدول حركات السيولة ورأس المال
CREATE TABLE IF NOT EXISTS capital_transactions (
    id SERIAL PRIMARY KEY,
    amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    transaction_type VARCHAR(20) NOT NULL DEFAULT 'INJECTION',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by_user_id INT REFERENCES users(id)
);
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
-- =================================================================================
-- ترقيات تلقائية آمنة لقواعد البيانات الموجودة مسبقاً (ALTER TABLE IF NOT EXISTS)
-- =================================================================================
ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(100) DEFAULT 'مستخدم النظام';
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS supplier_type VARCHAR(50) DEFAULT 'تاجر';
ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

ALTER TABLE supplier_invoices ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'UNPAID';
ALTER TABLE supplier_invoices ADD COLUMN IF NOT EXISTS created_by_user_id INT REFERENCES users(id);

ALTER TABLE devices ADD COLUMN IF NOT EXISTS storage VARCHAR(50);
ALTER TABLE devices ADD COLUMN IF NOT EXISTS ram VARCHAR(50) DEFAULT 'لا يوجد';
ALTER TABLE devices ADD COLUMN IF NOT EXISTS battery_health INT DEFAULT 0;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS accessories TEXT;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS device_condition VARCHAR(20) DEFAULT 'مستعمل';
ALTER TABLE devices ADD COLUMN IF NOT EXISTS has_box BOOLEAN DEFAULT TRUE;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS invoice_id INT REFERENCES supplier_invoices(id);
ALTER TABLE devices ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS is_sold BOOLEAN DEFAULT FALSE;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS created_by_user_id INT REFERENCES users(id);

ALTER TABLE sales ADD COLUMN IF NOT EXISTS customer_name VARCHAR(100) DEFAULT 'عميل نقدي';
ALTER TABLE sales ADD COLUMN IF NOT EXISTS customer_phone VARCHAR(30);
ALTER TABLE sales ADD COLUMN IF NOT EXISTS cash_received NUMERIC(12, 2) DEFAULT 0.00;
ALTER TABLE sales ADD COLUMN IF NOT EXISTS remaining_balance NUMERIC(12, 2) DEFAULT 0.00;
ALTER TABLE sales ADD COLUMN IF NOT EXISTS net_profit NUMERIC(12, 2) DEFAULT 0.00;
ALTER TABLE sales ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE sales ADD COLUMN IF NOT EXISTS sell_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE sales ADD COLUMN IF NOT EXISTS created_by_user_id INT REFERENCES users(id);
