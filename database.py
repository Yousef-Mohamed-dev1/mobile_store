# =================================================================================
# مدير قاعدة البيانات المحدث (PostgreSQL) - مركز هشام كيوان لإدارة الهواتف
# الإصدار الثاني: عزل مالي تام للأرشفة، معالجة Decimal في السجل، وتصحيح get_supplier_by_id
# =================================================================================

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
from contextlib import contextmanager
import bcrypt
import json
import os
import re
from decimal import Decimal
from datetime import datetime, date

CONFIG_FILE = "config.json"


def load_db_config():
    default_config = {
        "host": "localhost",
        "database": "DB_NAME",
        "user": "postgres",
        "password": "password",
        "port": 5432
    }
    if not os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error creating config.json: {e}")
        return default_config
    else:
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config
        except Exception as e:
            print(f"Error reading config.json: {e}")
            return default_config


def _clean_int_id(val):
    """استخراج الرقم الصحيح بأمان من أي قيمة ID حتى مع وجود رموز اتجاه النص أو # أو كائنات القواميس."""
    if val is None:
        return None
    if isinstance(val, dict):
        return _clean_int_id(val.get('id') or val.get('user_id'))
    if isinstance(val, int):
        return val
    s = str(val).replace('\u200f', '').replace('\u200e', '').replace('#', '').strip()
    if s.isdigit():
        return int(s)
    m = re.search(r'\d+', s)
    return int(m.group(0)) if m else None


def _json_serial_default(obj):
    """معالج تسلسل مخصص لحل خطأ Decimal و datetime في تسجيل العمليات JSON."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return str(obj)


class DatabaseManager:
    def __init__(self):
        self.conn_params = load_db_config()
        self.pool = None
        self._init_pool()
        self.ensure_tables_exist()

    def _init_pool(self):
        try:
            self.pool = pool.ThreadedConnectionPool(minconn=1, maxconn=20, cursor_factory=RealDictCursor, **self.conn_params)
        except Exception as e:
            print(f"Notice: Connection pool initialization fallback: {e}")
            self.pool = None

    @contextmanager
    def get_connection(self):
        conn = None
        is_from_pool = False
        try:
            if self.pool and not self.pool.closed:
                try:
                    conn = self.pool.getconn()
                    is_from_pool = True
                except Exception:
                    conn = psycopg2.connect(**self.conn_params, cursor_factory=RealDictCursor)
            else:
                conn = psycopg2.connect(**self.conn_params, cursor_factory=RealDictCursor)

            conn.cursor_factory = RealDictCursor
            yield conn
            if conn and not conn.closed:
                conn.commit()
        except Exception as e:
            if conn and not conn.closed:
                try:
                    conn.rollback()
                except Exception:
                    pass
            raise e
        finally:
            if conn:
                if is_from_pool and self.pool and not self.pool.closed:
                    try:
                        self.pool.putconn(conn)
                    except Exception:
                        pass
                else:
                    try:
                        conn.close()
                    except Exception:
                        pass

    def ensure_tables_exist(self):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # 1. جدول المستخدمين
                    cur.execute("""
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
                    """)
                    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(100) DEFAULT 'مستخدم النظام';")
                    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(30) DEFAULT 'custom';")
                    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS permissions JSONB DEFAULT '{}'::jsonb;")
                    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;")

                    # 2. جدول الموردين
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS suppliers (
                            id SERIAL PRIMARY KEY,
                            name VARCHAR(100) NOT NULL,
                            phone VARCHAR(30),
                            supplier_type VARCHAR(50) DEFAULT 'تاجر',
                            is_active BOOLEAN DEFAULT TRUE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    cur.execute("ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS supplier_type VARCHAR(50) DEFAULT 'تاجر';")
                    cur.execute("ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;")

                    # 3. جدول فواتير الموردين
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS supplier_invoices (
                            id SERIAL PRIMARY KEY,
                            supplier_id INT REFERENCES suppliers(id),
                            total_amount NUMERIC(12, 2) DEFAULT 0.00,
                            paid_amount NUMERIC(12, 2) DEFAULT 0.00,
                            remaining_amount NUMERIC(12, 2) DEFAULT 0.00,
                            supplier_credit NUMERIC(12, 2) DEFAULT 0.00,
                            status VARCHAR(30) DEFAULT 'UNPAID',
                            invoice_date DATE DEFAULT CURRENT_DATE,
                            created_by_user_id INT REFERENCES users(id),
                            notes TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    cur.execute("ALTER TABLE supplier_invoices ADD COLUMN IF NOT EXISTS status VARCHAR(30) DEFAULT 'UNPAID';")
                    cur.execute("ALTER TABLE supplier_invoices ADD COLUMN IF NOT EXISTS created_by_user_id INT REFERENCES users(id);")
                    cur.execute("ALTER TABLE supplier_invoices ADD COLUMN IF NOT EXISTS supplier_credit NUMERIC(12, 2) DEFAULT 0.00;")
                    cur.execute("ALTER TABLE supplier_invoices ADD COLUMN IF NOT EXISTS notes TEXT;")

                    # 4. جدول الأجهزة (مع دعم الأرشفة is_archived)
                    cur.execute("""
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
                    """)
                    cur.execute("ALTER TABLE devices ADD COLUMN IF NOT EXISTS storage VARCHAR(50);")
                    cur.execute("ALTER TABLE devices ADD COLUMN IF NOT EXISTS ram VARCHAR(50) DEFAULT 'لا يوجد';")
                    cur.execute("ALTER TABLE devices ADD COLUMN IF NOT EXISTS battery_health INT DEFAULT 0;")
                    cur.execute("ALTER TABLE devices ADD COLUMN IF NOT EXISTS accessories TEXT;")
                    cur.execute("ALTER TABLE devices ADD COLUMN IF NOT EXISTS device_condition VARCHAR(20) DEFAULT 'مستعمل';")
                    cur.execute("ALTER TABLE devices ADD COLUMN IF NOT EXISTS has_box BOOLEAN DEFAULT FALSE;")
                    cur.execute("ALTER TABLE devices ADD COLUMN IF NOT EXISTS invoice_id INT REFERENCES supplier_invoices(id);")
                    cur.execute("ALTER TABLE devices ADD COLUMN IF NOT EXISTS notes TEXT;")
                    cur.execute("ALTER TABLE devices ADD COLUMN IF NOT EXISTS is_sold BOOLEAN DEFAULT FALSE;")
                    cur.execute("ALTER TABLE devices ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;")
                    cur.execute("ALTER TABLE devices ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE;")
                    cur.execute("ALTER TABLE devices ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP DEFAULT NULL;")
                    cur.execute("ALTER TABLE devices ADD COLUMN IF NOT EXISTS archived_by_user_id INT REFERENCES users(id);")
                    cur.execute("ALTER TABLE devices ADD COLUMN IF NOT EXISTS created_by_user_id INT REFERENCES users(id);")
                    cur.execute("ALTER TABLE devices ADD COLUMN IF NOT EXISTS color VARCHAR(50) DEFAULT 'أسود';")
                    cur.execute("ALTER TABLE devices ADD COLUMN IF NOT EXISTS has_tax BOOLEAN DEFAULT FALSE;")
                    cur.execute("ALTER TABLE devices ADD COLUMN IF NOT EXISTS initial_selling_price NUMERIC(12, 2) DEFAULT NULL;")

                    # 5. جدول المبيعات
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS sales (
                            id SERIAL PRIMARY KEY,
                            device_id INT REFERENCES devices(id),
                            original_price NUMERIC(12, 2) DEFAULT 0.00,
                            discount NUMERIC(12, 2) DEFAULT 0.00,
                            sell_price NUMERIC(12, 2) NOT NULL,
                            customer_name VARCHAR(100) NOT NULL DEFAULT 'عميل نقدي',
                            customer_phone VARCHAR(30),
                            customer_address VARCHAR(255) DEFAULT '',
                            cash_received NUMERIC(12, 2) DEFAULT 0.00,
                            remaining_balance NUMERIC(12, 2) DEFAULT 0.00,
                            net_profit NUMERIC(12, 2) DEFAULT 0.00,
                            notes TEXT,
                            sell_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            created_by_user_id INT REFERENCES users(id)
                        );
                    """)
                    cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS original_price NUMERIC(12, 2) DEFAULT 0.00;")
                    cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS discount NUMERIC(12, 2) DEFAULT 0.00;")
                    cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS customer_name VARCHAR(100) DEFAULT 'عميل نقدي';")
                    cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS customer_phone VARCHAR(30);")
                    cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS customer_address VARCHAR(255) DEFAULT '';")
                    cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS cash_received NUMERIC(12, 2) DEFAULT 0.00;")
                    cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS remaining_balance NUMERIC(12, 2) DEFAULT 0.00;")
                    cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS net_profit NUMERIC(12, 2) DEFAULT 0.00;")
                    cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS notes TEXT;")
                    cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS sell_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
                    cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS created_by_user_id INT REFERENCES users(id);")

                    # 6. جدول تحصيلات ديون العملاء
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS customer_payments (
                            id SERIAL PRIMARY KEY,
                            sale_id INT REFERENCES sales(id) ON DELETE CASCADE,
                            payment_amount NUMERIC(12, 2) NOT NULL,
                            notes TEXT,
                            payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            created_by_user_id INT REFERENCES users(id)
                        );
                    """)
                    cur.execute("ALTER TABLE customer_payments ADD COLUMN IF NOT EXISTS notes TEXT;")
                    cur.execute("ALTER TABLE customer_payments ADD COLUMN IF NOT EXISTS created_by_user_id INT REFERENCES users(id);")

                    # 7. جدول دفعات الموردين
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS supplier_payments (
                            id SERIAL PRIMARY KEY,
                            invoice_id INT REFERENCES supplier_invoices(id) ON DELETE CASCADE,
                            supplier_id INT REFERENCES suppliers(id),
                            payment_amount NUMERIC(12, 2) NOT NULL,
                            notes TEXT,
                            payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            created_by_user_id INT REFERENCES users(id)
                        );
                    """)
                    cur.execute("ALTER TABLE supplier_payments ADD COLUMN IF NOT EXISTS supplier_id INT REFERENCES suppliers(id);")
                    cur.execute("ALTER TABLE supplier_payments ADD COLUMN IF NOT EXISTS notes TEXT;")
                    cur.execute("ALTER TABLE supplier_payments ADD COLUMN IF NOT EXISTS created_by_user_id INT REFERENCES users(id);")

                    # 8. جدول حركة السيولة ورأس المال
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS capital_transactions (
                            id SERIAL PRIMARY KEY,
                            amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
                            transaction_type VARCHAR(50) NOT NULL DEFAULT 'INJECTION',
                            notes TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            created_by_user_id INT REFERENCES users(id)
                        );
                    """)
                    cur.execute("ALTER TABLE capital_transactions ADD COLUMN IF NOT EXISTS transaction_type VARCHAR(50) DEFAULT 'INJECTION';")
                    cur.execute("ALTER TABLE capital_transactions ALTER COLUMN transaction_type TYPE VARCHAR(50);")
                    cur.execute("ALTER TABLE capital_transactions DROP CONSTRAINT IF EXISTS capital_transactions_transaction_type_check;")

                    # 9. جدول سجل التدقيق الدقيق للعمليات والرقابة المالية (Audit Log)
                    cur.execute("""
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
                    """)
                    cur.execute("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS user_name VARCHAR(100);")
                    cur.execute("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS old_values JSONB DEFAULT '{}'::jsonb;")
                    cur.execute("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS new_values JSONB DEFAULT '{}'::jsonb;")

                    
                    # 10. جدول المعاملات المالية العامة وتكامل الأصول
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS general_financial_transactions (
                            id SERIAL PRIMARY KEY,
                            trans_type VARCHAR(50) NOT NULL,
                            is_asset BOOLEAN NOT NULL DEFAULT FALSE,
                            recipient VARCHAR(255) NOT NULL,
                            category VARCHAR(255) NOT NULL,
                            amount NUMERIC(14, 2) NOT NULL,
                            paid_back_amount NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
                            remaining_amount NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
                            status VARCHAR(50) NOT NULL DEFAULT 'OPEN',
                            payment_method VARCHAR(100) DEFAULT 'كاش',
                            notes TEXT,
                            user_id INT REFERENCES users(id),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    cur.execute("ALTER TABLE general_financial_transactions ADD COLUMN IF NOT EXISTS trans_type VARCHAR(50) NOT NULL DEFAULT 'OPERATIONAL_EXP';")
                    cur.execute("ALTER TABLE general_financial_transactions ADD COLUMN IF NOT EXISTS is_asset BOOLEAN NOT NULL DEFAULT FALSE;")
                    cur.execute("ALTER TABLE general_financial_transactions ADD COLUMN IF NOT EXISTS paid_back_amount NUMERIC(14, 2) NOT NULL DEFAULT 0.00;")
                    cur.execute("ALTER TABLE general_financial_transactions ADD COLUMN IF NOT EXISTS remaining_amount NUMERIC(14, 2) NOT NULL DEFAULT 0.00;")
                    cur.execute("ALTER TABLE general_financial_transactions ADD COLUMN IF NOT EXISTS status VARCHAR(50) NOT NULL DEFAULT 'OPEN';")
                    cur.execute("ALTER TABLE general_financial_transactions ADD COLUMN IF NOT EXISTS payment_method VARCHAR(100) DEFAULT 'كاش';")
                    cur.execute("ALTER TABLE general_financial_transactions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

                    # 11. جدول الاقتراحات والقوالب المالية الجاهزة
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS financial_presets (
                            id SERIAL PRIMARY KEY,
                            preset_type VARCHAR(50) NOT NULL,
                            preset_value VARCHAR(255) UNIQUE NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)

                    # 12. جدول استرداد العهد والسلف والأمانات
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS general_transaction_refunds (
                            id SERIAL PRIMARY KEY,
                            transaction_id INT REFERENCES general_financial_transactions(id) ON DELETE CASCADE,
                            refund_amount NUMERIC(14, 2) NOT NULL,
                            payment_method VARCHAR(100) DEFAULT 'كاش',
                            notes TEXT,
                            user_id INT REFERENCES users(id),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)

                    cur.execute("CREATE INDEX IF NOT EXISTS idx_gen_trans_type ON general_financial_transactions(trans_type);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_gen_trans_status ON general_financial_transactions(status);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_gen_trans_recipient ON general_financial_transactions(recipient);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_gen_trans_date ON general_financial_transactions(created_at);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_gen_refunds_trans ON general_transaction_refunds(transaction_id);")

                    cur.execute("SELECT COUNT(*) as cnt FROM financial_presets;")
                    if cur.fetchone()['cnt'] == 0:
                        initial_presets = [
                            ('RECIPIENT', 'المالك / هشام كيوان'),
                            ('RECIPIENT', 'المحل / الخزينة الرئيسية'),
                            ('RECIPIENT', 'مسؤول الصيانة'),
                            ('RECIPIENT', 'أمين المخزن'),
                            ('RECIPIENT', 'موظف مبيعات'),
                            ('CATEGORY', 'إنترنت وهاتف المحل'),
                            ('CATEGORY', 'أدوات نظافة ومطبوعات'),
                            ('CATEGORY', 'سلفة راتب موظف'),
                            ('CATEGORY', 'عهدة صيانة وقطع غيار'),
                            ('CATEGORY', 'عهدة مشتريات بضاعة'),
                            ('CATEGORY', 'تحويل بين الخزائن'),
                            ('CATEGORY', 'أمانة نقدية طرف الغير')
                        ]
                        for p_t, p_v in initial_presets:
                            cur.execute("INSERT INTO financial_presets (preset_type, preset_value) VALUES (%s, %s) ON CONFLICT (preset_value) DO NOTHING;", (p_t, p_v))

                    # فهارس للأداء العالي وسرعة البحث
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_devices_imei ON devices(imei_serial);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_devices_inv_id ON devices(invoice_id);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_devices_archived ON devices(is_archived);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_devices_supp_id ON devices(supplier_id);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_supplier_inv_supp ON supplier_invoices(supplier_id);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_supplier_inv_date ON supplier_invoices(invoice_date);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_sales_device_id ON sales(device_id);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(sell_date);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_sales_rem ON sales(remaining_balance);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_customer_payments_sale ON customer_payments(sale_id);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_supplier_payments_inv ON supplier_payments(invoice_id);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action_type);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);")

                    # مستخدم المدير الافتراضي
                    cur.execute("SELECT COUNT(*) as cnt FROM users;")
                    if cur.fetchone()['cnt'] == 0:
                        default_hash = self.hash_password("admin123")
                        cur.execute("""
                            INSERT INTO users (username, password_hash, full_name, role, permissions, is_active)
                            VALUES ('admin', %s, 'مدير النظام العام', 'admin', '{}'::jsonb, TRUE);
                        """, (default_hash,))

                    conn.commit()
        except Exception as e:
            print(f"Table verification notice: {e}")

    # =========================================================================
    # دالة جلب المورد بالمعرف (إصلاح خطأ AttributeError المذكور في البلاغ)
    # =========================================================================
    def get_supplier_by_id(self, supplier_id):
        s_id = _clean_int_id(supplier_id)
        if not s_id:
            return None
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM suppliers WHERE id = %s;", (s_id,))
                    return cur.fetchone()
        except Exception as ex:
            print(f"get_supplier_by_id error: {ex}")
            return None

    # =========================================================================
    # تسجيل سجل العمليات (تم إصلاح خطأ Decimal is not JSON serializable جذرياً)
    # =========================================================================
    def add_audit_log(self, user_id, user_name, action_type, entity_type, entity_id, description, old_values=None, new_values=None):
        try:
            uid_clean = _clean_int_id(user_id)
            final_user_name = user_name
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    if uid_clean and (not final_user_name or final_user_name in ("مستخدم", "مستخدم النظام")):
                        try:
                            cur.execute("SELECT COALESCE(full_name, username) as uname FROM users WHERE id = %s;", (uid_clean,))
                            u_row = cur.fetchone()
                            if u_row and u_row.get('uname'):
                                final_user_name = u_row['uname']
                        except Exception:
                            pass

                    # استخدام _json_serial_default لحل مشكلة Decimal و DateTime بشكل كامل
                    old_json = json.dumps(old_values or {}, default=_json_serial_default, ensure_ascii=False)
                    new_json = json.dumps(new_values or {}, default=_json_serial_default, ensure_ascii=False)

                    cur.execute("""
                        INSERT INTO audit_logs (user_id, user_name, action_type, entity_type, entity_id, description, old_values, new_values)
                        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
                        RETURNING id;
                    """, (
                        uid_clean,
                        final_user_name or "مدير النظام",
                        action_type,
                        entity_type,
                        _clean_int_id(entity_id),
                        description,
                        old_json,
                        new_json
                    ))
                    conn.commit()
        except Exception as e:
            print(f"Audit log error: {e}")

    def get_audit_logs(self, limit=500, action_type=None, search_query=None, log_id=None, date_from=None, date_to=None):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    q = """
                        SELECT a.*,
                               to_char(a.created_at, 'YYYY-MM-DD HH24:MI:SS') as created_at_formatted
                        FROM audit_logs a
                        WHERE 1=1
                    """
                    params = []
                    if log_id:
                        clean_lid = _clean_int_id(log_id)
                        if clean_lid:
                            q += " AND a.id = %s"
                            params.append(clean_lid)
                    if action_type and action_type != 'ALL':
                        if action_type == 'ANOMALY':
                            q += " AND (a.action_type IN ('SALE_PRICE_BELOW_INITIAL', 'SALE_PRICE_ABOVE_INITIAL', 'UPDATE_PRICE_BELOW', 'UPDATE_PRICE_ABOVE', 'SALE_BELOW_COST') OR a.description LIKE '%⚠️%')"
                        elif action_type == 'SALE':
                            q += " AND (a.action_type LIKE '%SALE%')"
                        elif action_type == 'RETURN_DEVICE':
                            q += " AND a.action_type = 'RETURN_DEVICE'"
                        elif action_type == 'COLLECT_DEBT':
                            q += " AND a.action_type = 'COLLECT_DEBT'"
                        elif action_type == 'PAY_SUPPLIER':
                            q += " AND a.action_type IN ('PAY_SUPPLIER', 'PAY_SUPPLIER_BULK')"
                        elif action_type == 'CLAIM_SUPPLIER_CREDIT':
                            q += " AND a.action_type = 'CLAIM_SUPPLIER_CREDIT'"
                        elif action_type == 'ADD_DEVICE':
                            q += " AND a.action_type = 'ADD_DEVICE'"
                        elif action_type == 'EDIT_DEVICE':
                            q += " AND a.action_type IN ('EDIT_DEVICE', 'UPDATE_PRICE_BELOW', 'UPDATE_PRICE_ABOVE')"
                        elif action_type == 'DELETE_DEVICE':
                            q += " AND a.action_type = 'DELETE_DEVICE'"
                        elif action_type == 'ARCHIVE_DEVICE':
                            q += " AND a.action_type IN ('ARCHIVE_DEVICE', 'UNARCHIVE_DEVICE')"
                        elif action_type == 'CAPITAL':
                            q += " AND a.action_type IN ('CAPITAL_INJECTION', 'CAPITAL_WITHDRAWAL', 'DELETE_CAPITAL_TX', 'SUPPLIER_REFUND')"
                        elif action_type == 'SUPPLIER':
                            q += " AND a.action_type IN ('ADD_SUPPLIER', 'UPDATE_SUPPLIER', 'DELETE_SUPPLIER')"
                        elif action_type == 'USER':
                            q += " AND a.action_type IN ('ADD_USER', 'UPDATE_USER_PERMISSIONS')"
                        elif action_type == 'UPDATE_DATE':
                            q += " AND a.action_type = 'UPDATE_DATE'"
                        elif action_type in ('GENERAL_TRANSACTION', 'GENERAL_TRANSACTIONS'):
                            q += " AND a.action_type IN ('GENERAL_TRANSACTION_CREATE', 'GENERAL_TRANSACTION_REFUND')"
                        elif action_type == 'GENERAL_TRANSACTION_CREATE':
                            q += " AND a.action_type = 'GENERAL_TRANSACTION_CREATE'"
                        elif action_type == 'GENERAL_TRANSACTION_REFUND':
                            q += " AND a.action_type = 'GENERAL_TRANSACTION_REFUND'"
                        elif action_type == 'SUPPLIER_DEBIT_OFFSET':
                            q += " AND a.action_type = 'SUPPLIER_DEBIT_OFFSET'"
                        elif action_type == 'DEVICE_RETURN_TO_SUPPLIER':
                            q += " AND a.action_type IN ('DEVICE_RETURN_TO_SUPPLIER', 'DELETE_DEVICE')"
                        else:
                            q += " AND a.action_type = %s"
                            params.append(action_type)
                    if date_from and str(date_from).strip():
                        q += " AND DATE(a.created_at) >= %s::date"
                        params.append(str(date_from).strip())
                    if date_to and str(date_to).strip():
                        q += " AND DATE(a.created_at) <= %s::date"
                        params.append(str(date_to).strip())
                    if search_query:
                        sq = f"%{search_query.strip()}%"
                        q += " AND (a.description ILIKE %s OR a.user_name ILIKE %s OR a.entity_type ILIKE %s OR CAST(a.entity_id AS TEXT) ILIKE %s OR CAST(a.id AS TEXT) ILIKE %s)"
                        params.extend([sq, sq, sq, sq, sq])
                    q += " ORDER BY a.created_at DESC, a.id DESC LIMIT %s;"
                    params.append(limit)
                    cur.execute(q, tuple(params))
                    return [dict(r) for r in cur.fetchall()]
        except Exception as ex:
            print(f"Error fetching audit logs: {ex}")
            return []

    def hash_password(self, password):
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password, hashed_password):
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception:
            return False

    def authenticate_user(self, username, password):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM users WHERE LOWER(TRIM(username)) = LOWER(%s) AND COALESCE(is_active, TRUE) = TRUE",
                        (username.strip(),)
                    )
                    user = cur.fetchone()
                    if user:
                        stored_pass = str(user['password_hash'] or '').strip()
                        input_pass = str(password or '').strip()

                        authenticated = False
                        if self.check_password(input_pass, stored_pass):
                            authenticated = True
                        elif stored_pass == input_pass:
                            new_hash = self.hash_password(input_pass)
                            cur.execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_hash, user['id']))
                            conn.commit()
                            user['password_hash'] = new_hash
                            authenticated = True

                        if authenticated:
                            perms = user.get('permissions')
                            if isinstance(perms, str):
                                try:
                                    perms = json.loads(perms)
                                except Exception:
                                    perms = {}
                            if not isinstance(perms, dict):
                                perms = {}
                            user['permissions'] = perms
                            return user
            return None
        except Exception as e:
            print(f"Error Authenticating: {e}")
            return None

    def get_all_users(self):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, username,
                               COALESCE(full_name, username) as full_name,
                               COALESCE(role, 'custom') as role,
                               COALESCE(permissions, '{}'::jsonb) as permissions,
                               COALESCE(is_active, TRUE) as is_active
                        FROM users
                        ORDER BY id ASC;
                    """)
                    return cur.fetchall()
        except Exception:
            return []

    def add_user(self, username, password, full_name, permissions, role='custom', admin_user_id=None):
        hashed = self.hash_password(password)
        perm_json = json.dumps(permissions, ensure_ascii=False)
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (username, password_hash, full_name, role, permissions, is_active)
                    VALUES (%s, %s, %s, %s, %s::jsonb, TRUE) RETURNING id;
                """, (username.strip(), hashed, full_name.strip(), role or 'custom', perm_json))
                uid = cur.fetchone()['id']
                conn.commit()
        self.add_audit_log(
            user_id=admin_user_id,
            user_name=None,
            action_type="ADD_USER",
            entity_type="USER",
            entity_id=uid,
            description=f"إضافة مستخدم جديد للنظام: {username.strip()} ({full_name.strip()}) بصلاحية {role or 'custom'}",
            new_values={"username": username.strip(), "full_name": full_name.strip(), "role": role}
        )
        return uid

    def create_user(self, username, password, full_name, permissions, role='custom', admin_user_id=None):
        return self.add_user(username, password, full_name, permissions, role=role, admin_user_id=admin_user_id)

    def update_user(self, user_id, full_name, permissions, new_password=None, role=None, username=None, is_active=None, admin_user_id=None):
        perm_json = json.dumps(permissions, ensure_ascii=False)
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT username, role, is_active, full_name FROM users WHERE id = %s;", (user_id,))
                cur_u = cur.fetchone() or {}
                final_uname = (username.strip() if username else cur_u.get('username')) or 'user'
                final_role = (role if role is not None else cur_u.get('role')) or 'custom'
                final_active = bool(is_active) if is_active is not None else bool(cur_u.get('is_active', True))
                if str(cur_u.get('username', '')).lower() == 'admin':
                    final_uname = cur_u.get('username')
                    final_active = True

                if new_password and new_password.strip():
                    hashed = self.hash_password(new_password.strip())
                    cur.execute("""
                        UPDATE users 
                        SET username = %s, full_name = %s, role = %s, is_active = %s, permissions = %s::jsonb, password_hash = %s 
                        WHERE id = %s;
                    """, (final_uname, full_name.strip(), final_role, final_active, perm_json, hashed, user_id))
                else:
                    cur.execute("""
                        UPDATE users 
                        SET username = %s, full_name = %s, role = %s, is_active = %s, permissions = %s::jsonb 
                        WHERE id = %s;
                    """, (final_uname, full_name.strip(), final_role, final_active, perm_json, user_id))
                conn.commit()
        self.add_audit_log(
            user_id=admin_user_id,
            user_name=None,
            action_type="UPDATE_USER_PERMISSIONS",
            entity_type="USER",
            entity_id=user_id,
            description=f"تحديث بيانات وصلاحيات المستخدم #{user_id}: {final_uname} ({full_name.strip()}) [الدور: {final_role}]",
            old_values=dict(cur_u),
            new_values={"username": final_uname, "full_name": full_name.strip(), "role": final_role, "is_active": final_active}
        )

    def toggle_user_active(self, user_id, new_status=None):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                if new_status is None:
                    cur.execute("UPDATE users SET is_active = NOT COALESCE(is_active, TRUE) WHERE id = %s;", (user_id,))
                else:
                    cur.execute("UPDATE users SET is_active = %s WHERE id = %s;", (bool(new_status), user_id))
                conn.commit()

    def get_suppliers(self, active_only=True, search_query=None):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT id, name, COALESCE(phone, '') as phone,
                               COALESCE(supplier_type, 'تاجر') as supplier_type,
                               COALESCE(is_active, TRUE) as is_active
                        FROM suppliers
                        WHERE 1=1
                    """
                    params = []
                    if active_only:
                        query += " AND COALESCE(is_active, TRUE) = TRUE"
                    if search_query:
                        q = str(search_query).strip()
                        query += " AND (name ILIKE %s OR COALESCE(phone, '') ILIKE %s OR COALESCE(supplier_type, '') ILIKE %s OR CAST(id AS TEXT) = %s)"
                        params.extend([f"%{q}%", f"%{q}%", f"%{q}%", q.lstrip('#')])
                    query += " ORDER BY name ASC;"
                    cur.execute(query, params)
                    return cur.fetchall()
        except Exception:
            return []

    def get_all_suppliers(self, search_query=None):
        return self.get_suppliers(active_only=True, search_query=search_query)

    def archive_supplier(self, supp_id, user_id=None):
        s_id = _clean_int_id(supp_id)
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM suppliers WHERE id = %s;", (s_id,))
                supp = cur.fetchone()
                cur.execute("UPDATE suppliers SET is_active = FALSE WHERE id = %s;", (s_id,))
                conn.commit()
        self.add_audit_log(
            user_id=user_id,
            user_name=None,
            action_type="DELETE_SUPPLIER",
            entity_type="SUPPLIER",
            entity_id=s_id,
            description=f"أرشفة وتعطيل المورد #{s_id}: {supp.get('name') if supp else '-'}",
            old_values=dict(supp) if supp else {},
            new_values={"is_active": False}
        )

    def restore_supplier(self, supp_id, user_id=None):
        s_id = _clean_int_id(supp_id)
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM suppliers WHERE id = %s;", (s_id,))
                supp = cur.fetchone()
                cur.execute("UPDATE suppliers SET is_active = TRUE WHERE id = %s;", (s_id,))
                conn.commit()
        self.add_audit_log(
            user_id=user_id,
            user_name=None,
            action_type="UPDATE_SUPPLIER",
            entity_type="SUPPLIER",
            entity_id=s_id,
            description=f"إعادة تفعيل المورد المؤرشف #{s_id}: {supp.get('name') if supp else '-'}",
            old_values=dict(supp) if supp else {},
            new_values={"is_active": True}
        )

    def add_supplier(self, name, phone, supplier_type='تاجر', user_id=None):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO suppliers (name, phone, supplier_type) VALUES (%s, %s, %s) RETURNING id;",
                    (name.strip(), phone.strip() if phone else '', supplier_type or 'تاجر')
                )
                supp_id = cur.fetchone()['id']
                conn.commit()
        self.add_audit_log(
            user_id=user_id,
            user_name=None,
            action_type="ADD_SUPPLIER",
            entity_type="SUPPLIER",
            entity_id=supp_id,
            description=f"إضافة مورد جديد: {name.strip()} ({supplier_type or 'تاجر'}) - هاتف: {phone or '-'}",
            new_values={"name": name.strip(), "phone": phone, "type": supplier_type}
        )
        return supp_id

    def update_supplier(self, supp_id, name, phone, supplier_type='تاجر', user_id=None):
        s_id = _clean_int_id(supp_id)
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM suppliers WHERE id = %s;", (s_id,))
                old_supp = cur.fetchone()
                cur.execute(
                    "UPDATE suppliers SET name = %s, phone = %s, supplier_type = %s WHERE id = %s;",
                    (name.strip(), phone.strip() if phone else '', supplier_type or 'تاجر', s_id)
                )
                conn.commit()
        self.add_audit_log(
            user_id=user_id,
            user_name=None,
            action_type="UPDATE_SUPPLIER",
            entity_type="SUPPLIER",
            entity_id=s_id,
            description=f"تعديل بيانات المورد #{s_id}: {name.strip()} ({supplier_type})",
            old_values=dict(old_supp) if old_supp else {},
            new_values={"name": name.strip(), "phone": phone, "type": supplier_type}
        )

    def delete_supplier(self, supp_id, user_id=None):
        s_id = _clean_int_id(supp_id)
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM suppliers WHERE id = %s;", (s_id,))
                supp = cur.fetchone()
                if not supp:
                    raise Exception("المورد غير موجود أو تم حذفه مسبقاً!")
                cur.execute("SELECT COALESCE(SUM(remaining_amount), 0) as rem, COALESCE(SUM(supplier_credit), 0) as cred FROM supplier_invoices WHERE supplier_id = %s;", (s_id,))
                row = cur.fetchone()
                rem = float(row['rem'] or 0)
                cred = float(row['cred'] or 0)
                if rem > 0:
                    raise Exception(f"لا يمكن حذف المورد لوجود مديونية متبقية له بقيمة ({rem:,.2f} ج.م)!")
                if cred > 0:
                    raise Exception(f"لا يمكن حذف المورد لوجود رصيد دائن أمانة مستحق لنا لديه بقيمة ({cred:,.2f} ج.م)! يرجى استرداد الرصيد للخزينة أولاً.")
                cur.execute("UPDATE suppliers SET is_active = FALSE WHERE id = %s;", (s_id,))
                conn.commit()
        self.add_audit_log(
            user_id=user_id,
            user_name=None,
            action_type="DELETE_SUPPLIER",
            entity_type="SUPPLIER",
            entity_id=s_id,
            description=f"أرشفة وحذف المورد #{s_id}: {supp.get('name')} ({supp.get('phone') or '-'})",
            old_values=dict(supp) if supp else {}
        )

    def get_distinct_models_by_category(self, category=None):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    if category and category.strip():
                        cur.execute("""
                            SELECT DISTINCT model FROM devices
                            WHERE category ILIKE %s AND COALESCE(is_deleted, FALSE) = FALSE AND COALESCE(is_archived, FALSE) = FALSE
                            ORDER BY model ASC LIMIT 40;
                        """, (f"%{category.strip()}%",))
                    else:
                        cur.execute("""
                            SELECT DISTINCT model FROM devices
                            WHERE COALESCE(is_deleted, FALSE) = FALSE AND COALESCE(is_archived, FALSE) = FALSE
                            ORDER BY model ASC LIMIT 40;
                        """)
                    return [r['model'] for r in cur.fetchall() if r.get('model')]
        except Exception:
            return []

    # =========================================================================
    # إضافة الأجهزة مع إنشاء فاتورة مورد مستقلة لكل جهاز (Per-Device Invoice)
    # =========================================================================
    def add_device(self, category, model, storage="", ram="", battery=None, accessories="", imei="", buy_price=0.0, supplier_id=None, notes="", user_id=None, device_condition="مستعمل", has_box=False, paid_amount=None, color="أسود", has_tax=False, initial_selling_price=None, custom_date=None):
        if not supplier_id:
            raise Exception("يجب اختيار المورد أولاً لإتمام عملية الشراء!")

        ram_val = ram.strip() if ram else ""
        bat_val = int(battery) if (battery is not None and str(battery).replace('.', '', 1).isdigit()) else 0
        if bat_val < 0 or bat_val > 100:
            raise Exception("نسبة صحة البطارية غير منطقية! يجب أن تكون بين 1% و 100%.")

        cond_val = device_condition if device_condition in ("جديد", "مستعمل", "كسر زيرو") else "مستعمل"
        box_val = bool(has_box)
        color_val = (color or "").strip()
        if not color_val or color_val == "بدون":
            color_val = "أسود"
        tax_val = bool(has_tax)
        b_price = float(buy_price or 0)
        paid_now = max(0.0, min(b_price, float(paid_amount if paid_amount is not None else b_price)))
        rem_now = max(0.0, b_price - paid_now)

        init_sp_val = float(initial_selling_price) if (initial_selling_price is not None and str(initial_selling_price).strip() != "") else b_price
        if init_sp_val < b_price:
            raise Exception(f"لا يمكن أن يكون سعر البيع المبدئي ({init_sp_val:,.2f} ج.م) أقل من سعر الشراء ({b_price:,.2f} ج.م)!")

        clean_imei = (imei or "").strip()

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                if clean_imei:
                    cur.execute("SELECT id, model FROM devices WHERE imei_serial = %s AND COALESCE(is_sold, FALSE) = FALSE AND COALESCE(is_deleted, FALSE) = FALSE;", (clean_imei,))
                    dup = cur.fetchone()
                    if dup:
                        raise Exception(f"السيريال ({clean_imei}) مسجل بالفعل بالمخزون للجهاز #{dup['id']} ({dup['model']})!")

                # فحص رصيد المورد الدائن واستهلاكه تلقائياً
                cur.execute("""
                    SELECT id, supplier_credit 
                    FROM supplier_invoices 
                    WHERE supplier_id = %s AND supplier_credit > 0 
                    ORDER BY invoice_date ASC, id ASC 
                    FOR UPDATE;
                """, (supplier_id,))
                credit_invoices = cur.fetchall()

                total_avail_credit = sum(float(ci['supplier_credit'] or 0) for ci in credit_invoices)
                offset_amount = min(b_price, total_avail_credit)

                # خصم الرصيد المستهلك من فواتير المورد السابقة
                remaining_offset_to_deduct = offset_amount
                for ci in credit_invoices:
                    if remaining_offset_to_deduct <= 0:
                        break
                    ci_id = ci['id']
                    ci_cred = float(ci['supplier_credit'] or 0)
                    deduct = min(ci_cred, remaining_offset_to_deduct)
                    new_ci_cred = max(0.0, ci_cred - deduct)
                    cur.execute("UPDATE supplier_invoices SET supplier_credit = %s WHERE id = %s;", (new_ci_cred, ci_id))
                    remaining_offset_to_deduct -= deduct

                # القيمة المتبقية المطلوب سدادها بعد خصم رصيد المورد الدائن
                net_cost_after_offset = max(0.0, b_price - offset_amount)

                # المبلغ النقدي المدفوع من المستخدم يطبق على الصافي بعد الخصم
                if paid_amount is not None:
                    user_cash_paid = max(0.0, min(net_cost_after_offset, float(paid_amount)))
                else:
                    user_cash_paid = net_cost_after_offset

                total_paid_for_invoice = offset_amount + user_cash_paid
                rem_now = max(0.0, b_price - total_paid_for_invoice)

                c_date = custom_date.strip() if (custom_date and str(custom_date).strip()) else None
                inv_date_target = c_date.split()[0] if c_date else datetime.now().strftime("%Y-%m-%d")

                inv_status = 'PAID' if rem_now <= 0 else 'UNPAID'
                inv_notes = f"فاتورة شراء مستقلة للجهاز: {category} {model} (سيريال: {clean_imei})"
                if offset_amount > 0:
                    inv_notes += f" [تم الخصم تلقائياً من رصيد ديننا القديم لدى المورد بمبلغ {offset_amount:,.2f} ج.م]"
                if notes and str(notes).strip():
                    inv_notes += f" - ملاحظات: {notes.strip()}"

                cur.execute("""
                    INSERT INTO supplier_invoices (supplier_id, total_amount, paid_amount, remaining_amount, supplier_credit, status, invoice_date, created_by_user_id, notes)
                    VALUES (%s, %s, %s, %s, 0.00, %s, %s::date, %s, %s)
                    RETURNING id;
                """, (supplier_id, b_price, total_paid_for_invoice, rem_now, inv_status, inv_date_target, _clean_int_id(user_id), inv_notes))
                inv_id = cur.fetchone()['id']

                # تسجيل دفعة الخصم الدائن
                if offset_amount > 0:
                    offset_pay_note = f"خصم تلقائي من رصيد ديننا القديم لدى المورد بمبلغ {offset_amount:,.2f} ج.م لسداد تكلفة جهاز #{category} {model}"
                    if c_date:
                        cur.execute("""
                            INSERT INTO supplier_payments (invoice_id, supplier_id, payment_amount, notes, created_by_user_id, payment_date)
                            VALUES (%s, %s, %s, %s, %s, %s::timestamp);
                        """, (inv_id, supplier_id, offset_amount, offset_pay_note, _clean_int_id(user_id), c_date))
                    else:
                        cur.execute("""
                            INSERT INTO supplier_payments (invoice_id, supplier_id, payment_amount, notes, created_by_user_id)
                            VALUES (%s, %s, %s, %s, %s);
                        """, (inv_id, supplier_id, offset_amount, offset_pay_note, _clean_int_id(user_id)))

                # تسجيل الدفعة النقدية المسددة إن وجدت
                if user_cash_paid > 0:
                    pay_notes = f"دفعة نقدية عند شراء {category} {model} (فاتورة مستقلة #{inv_id})"
                    if c_date:
                        cur.execute("""
                            INSERT INTO supplier_payments (invoice_id, supplier_id, payment_amount, notes, created_by_user_id, payment_date)
                            VALUES (%s, %s, %s, %s, %s, %s::timestamp);
                        """, (inv_id, supplier_id, user_cash_paid, pay_notes, _clean_int_id(user_id), c_date))
                    else:
                        cur.execute("""
                            INSERT INTO supplier_payments (invoice_id, supplier_id, payment_amount, notes, created_by_user_id)
                            VALUES (%s, %s, %s, %s, %s);
                        """, (inv_id, supplier_id, user_cash_paid, pay_notes, _clean_int_id(user_id)))

                if c_date:
                    cur.execute("""
                        INSERT INTO devices (
                            category, model, storage, ram, battery_health, accessories,
                            device_condition, has_box, imei_serial, buy_price,
                            supplier_id, invoice_id, notes, created_by_user_id, color, has_tax,
                            initial_selling_price, buy_date, is_archived
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::timestamp, FALSE) RETURNING id;
                    """, (category, model, storage, ram_val, bat_val, accessories, cond_val, box_val, clean_imei, b_price, supplier_id, inv_id, notes, _clean_int_id(user_id), color_val, tax_val, init_sp_val, c_date))
                else:
                    cur.execute("""
                        INSERT INTO devices (
                            category, model, storage, ram, battery_health, accessories,
                            device_condition, has_box, imei_serial, buy_price,
                            supplier_id, invoice_id, notes, created_by_user_id, color, has_tax,
                            initial_selling_price, is_archived
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE) RETURNING id;
                    """, (category, model, storage, ram_val, bat_val, accessories, cond_val, box_val, clean_imei, b_price, supplier_id, inv_id, notes, _clean_int_id(user_id), color_val, tax_val, init_sp_val))
                device_id = cur.fetchone()['id']

                conn.commit()

        if offset_amount > 0:
            self.add_audit_log(
                user_id=user_id,
                user_name=None,
                action_type="SUPPLIER_DEBIT_OFFSET",
                entity_type="SUPPLIER",
                entity_id=supplier_id,
                description=f"خصم تلقائي لرصيد مورد دائن بقيمة {offset_amount:,.2f} ج.م لسداد تكلفة شراء الجهاز #{device_id} ({category} {model}) من المورد #{supplier_id}",
                old_values={"available_credit": total_avail_credit},
                new_values={"offset_amount": offset_amount, "new_credit": total_avail_credit - offset_amount, "device_id": device_id, "invoice_id": inv_id}
            )

        self.add_audit_log(
            user_id=user_id,
            user_name=None,
            action_type="ADD_DEVICE",
            entity_type="DEVICE",
            entity_id=device_id,
            description=f"إضافة وشراء جهاز للمخزون #{device_id} ({category} {model}) بسعر شراء {b_price:,.2f} ج.م وسعر بيع مبدئي {init_sp_val:,.2f} ج.م (لون: {color_val}) - فاتورة مورد مستقلة #{inv_id}" + (f" [تم خصم {offset_amount:,.2f} ج.م من رصيد المورد الدائن]" if offset_amount > 0 else ""),
            old_values=None,
            new_values={"category": category, "model": model, "storage": storage, "ram": ram_val, "battery": bat_val, "imei": clean_imei, "buy_price": b_price, "initial_selling_price": init_sp_val, "supplier_id": supplier_id, "invoice_id": inv_id, "offset_amount": offset_amount, "paid_now": total_paid_for_invoice, "remaining_debt": rem_now, "color": color_val, "has_tax": tax_val, "notes": notes}
        )
        return {
            'device_id': device_id,
            'invoice_id': inv_id,
            'buy_price': b_price,
            'offset_amount': offset_amount,
            'cash_paid': user_cash_paid,
            'total_paid': total_paid_for_invoice,
            'remaining_debt': rem_now
        }

    # =========================================================================
    # تعديل الجهاز مع تحديث فاتورته المستقلة تلقائياً والحفاظ التام على المورد والتواريخ
    # =========================================================================
    def update_device(self, device_id, category, model, storage="", ram="", battery=None, imei="", buy_price=0.0, device_condition="مستعمل", has_box=False, notes="", supplier_id=None, color="أسود", has_tax=False, initial_selling_price=None, accessories="", buy_date=None, sell_date=None, user_id=None, customer_name=None, customer_phone=None, sell_price=None, cash_received=None):
        dev_id = _clean_int_id(device_id)
        if dev_id is None:
            raise Exception("كود الجهاز غير صالح!")

        cond_val = device_condition if device_condition in ("جديد", "مستعمل", "كسر زيرو") else "مستعمل"
        box_val = bool(has_box)
        color_val = (color or "").strip()
        if not color_val or color_val == "بدون":
            color_val = "أسود"
        tax_val = bool(has_tax)
        bat_val = int(battery) if (battery is not None and str(battery).replace('.', '', 1).isdigit()) else 0
        if bat_val < 0 or bat_val > 100:
            raise Exception("نسبة صحة البطارية غير منطقية! يجب أن تكون بين 1% و 100%.")

        ram_val = ram.strip() if ram else ""
        clean_imei = (imei or "").strip()
        new_buy_price = float(buy_price or 0)
        new_init_sp = float(initial_selling_price) if (initial_selling_price is not None and str(initial_selling_price).strip() != "") else None
        if new_init_sp is not None and new_init_sp < new_buy_price:
            raise Exception(f"لا يمكن أن يكون سعر البيع المبدئي ({new_init_sp:,.2f} ج.م) أقل من سعر الشراء ({new_buy_price:,.2f} ج.م)!")

        parsed_buy_date = None
        if buy_date and str(buy_date).strip():
            for b_fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    parsed_buy_date = datetime.strptime(str(buy_date).strip(), b_fmt)
                    break
                except ValueError:
                    continue
            if parsed_buy_date and parsed_buy_date.date() > datetime.now().date():
                raise Exception("لا يمكن تعيين تاريخ شراء مستقبلي للجهاز!")

        parsed_sell_date = None
        if sell_date and str(sell_date).strip():
            for s_fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    parsed_sell_date = datetime.strptime(str(sell_date).strip(), s_fmt)
                    break
                except ValueError:
                    continue
            if parsed_sell_date and parsed_sell_date.date() > datetime.now().date():
                raise Exception("لا يمكن تعيين تاريخ بيع مستقبلي للجهاز!")

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                if clean_imei:
                    cur.execute("SELECT id, model FROM devices WHERE imei_serial = %s AND id != %s AND COALESCE(is_sold, FALSE) = FALSE AND COALESCE(is_deleted, FALSE) = FALSE;", (clean_imei, dev_id))
                    dup = cur.fetchone()
                    if dup:
                        raise Exception(f"السيريال ({clean_imei}) مستخدم بالفعل في جهاز آخر بالمخزون #{dup['id']} ({dup['model']})!")

                cur.execute("SELECT * FROM devices WHERE id = %s FOR UPDATE;", (dev_id,))
                old_dev = cur.fetchone()
                if not old_dev:
                    raise Exception("الجهاز غير موجود!")

                cur.execute("SELECT * FROM sales WHERE device_id = %s FOR UPDATE;", (dev_id,))
                existing_sale = cur.fetchone()

                effective_buy_dt = parsed_buy_date or (datetime.strptime(str(old_dev['buy_date']).split('.')[0], "%Y-%m-%d %H:%M:%S") if old_dev.get('buy_date') else None)
                effective_sell_dt = parsed_sell_date or (datetime.strptime(str(existing_sale['sell_date']).split('.')[0], "%Y-%m-%d %H:%M:%S") if existing_sale and existing_sale.get('sell_date') else None)

                if existing_sale and effective_buy_dt and effective_sell_dt:
                    if effective_sell_dt < effective_buy_dt:
                        raise Exception(f"تعارض زمني غير منطقي: تاريخ البيع ({effective_sell_dt.strftime('%Y-%m-%d')}) لا يمكن أن يكون أقدم من تاريخ الشراء ({effective_buy_dt.strftime('%Y-%m-%d')})!")

                old_price = float(old_dev['buy_price'] or 0)
                old_supp_id = old_dev.get('supplier_id')
                old_inv_id = old_dev.get('invoice_id')
                target_supp_id = _clean_int_id(supplier_id) or old_supp_id
                target_inv_id = old_inv_id

                if target_inv_id:
                    cur.execute("SELECT * FROM supplier_invoices WHERE id = %s FOR UPDATE;", (target_inv_id,))
                    inv = cur.fetchone()
                    if inv:
                        curr_paid = float(inv['paid_amount'] or 0)
                        old_cred = float(inv.get('supplier_credit') or 0)
                        new_tot = new_buy_price

                        if curr_paid > new_tot:
                            excess = curr_paid - new_tot
                            new_cred = old_cred + excess
                            new_rem = 0.0
                            status = 'PAID'
                        else:
                            new_rem = max(0.0, new_tot - curr_paid)
                            new_cred = old_cred
                            status = 'PAID' if new_rem <= 0 else 'UNPAID'

                        inv_date_to_set = parsed_buy_date.date() if parsed_buy_date else inv['invoice_date']

                        cur.execute("""
                            UPDATE supplier_invoices
                            SET supplier_id = %s, total_amount = %s, remaining_amount = %s,
                                supplier_credit = %s, status = %s, invoice_date = %s
                            WHERE id = %s;
                        """, (target_supp_id, new_tot, new_rem, new_cred, status, inv_date_to_set, target_inv_id))

                        cur.execute("UPDATE supplier_payments SET supplier_id = %s WHERE invoice_id = %s;", (target_supp_id, target_inv_id))

                b_date_val = parsed_buy_date.strftime("%Y-%m-%d %H:%M:%S") if parsed_buy_date else old_dev.get('buy_date')
                acc_val = accessories.strip() if accessories else (old_dev.get('accessories') or '')

                if new_init_sp is not None:
                    cur.execute("""
                        UPDATE devices 
                        SET category = %s, model = %s, storage = %s, ram = %s,
                            battery_health = %s, imei_serial = %s, buy_price = %s,
                            device_condition = %s, has_box = %s, notes = %s,
                            supplier_id = %s, invoice_id = %s, color = %s, has_tax = %s,
                            accessories = %s, initial_selling_price = %s, buy_date = %s
                        WHERE id = %s;
                    """, (category, model, storage, ram_val, bat_val, clean_imei, new_buy_price, cond_val, box_val, notes, target_supp_id, target_inv_id, color_val, tax_val, acc_val, new_init_sp, b_date_val, dev_id))
                else:
                    cur.execute("""
                        UPDATE devices 
                        SET category = %s, model = %s, storage = %s, ram = %s,
                            battery_health = %s, imei_serial = %s, buy_price = %s,
                            device_condition = %s, has_box = %s, notes = %s,
                            supplier_id = %s, invoice_id = %s, color = %s, has_tax = %s,
                            accessories = %s, buy_date = %s
                        WHERE id = %s;
                    """, (category, model, storage, ram_val, bat_val, clean_imei, new_buy_price, cond_val, box_val, notes, target_supp_id, target_inv_id, color_val, tax_val, acc_val, b_date_val, dev_id))

                if existing_sale:
                    cur_sp = float(sell_price) if sell_price is not None else float(existing_sale['sell_price'])
                    cur_cash = float(cash_received) if cash_received is not None else float(existing_sale['cash_received'])
                    cur_cust_name = customer_name.strip() if customer_name else existing_sale['customer_name']
                    cur_cust_phone = customer_phone.strip() if customer_phone is not None else (existing_sale['customer_phone'] or '')
                    cur_rem = max(0.0, cur_sp - cur_cash)
                    cur_profit = cur_sp - new_buy_price

                    s_date_str = parsed_sell_date.strftime("%Y-%m-%d %H:%M:%S") if parsed_sell_date else existing_sale['sell_date']

                    cur.execute("""
                        UPDATE sales 
                        SET sell_price = %s, cash_received = %s, remaining_balance = %s,
                            net_profit = %s, customer_name = %s, customer_phone = %s,
                            sell_date = %s::timestamp
                        WHERE id = %s;
                    """, (cur_sp, cur_cash, cur_rem, cur_profit, cur_cust_name, cur_cust_phone, s_date_str, existing_sale['id']))

                    if parsed_sell_date:
                        cur.execute("UPDATE customer_payments SET payment_date = %s::timestamp WHERE sale_id = %s AND notes LIKE '%%دفعة مقدمة%%';", (s_date_str, existing_sale['id']))

                conn.commit()

        updated_fields = {
            "category": category, "model": model, "storage": storage, "ram": ram_val,
            "battery": bat_val, "imei": clean_imei, "buy_price": new_buy_price,
            "supplier_id": target_supp_id, "color": color_val, "has_tax": tax_val,
            "accessories": acc_val, "device_condition": cond_val, "has_box": box_val,
            "notes": notes
        }
        if new_init_sp is not None:
            updated_fields["initial_selling_price"] = new_init_sp
        if parsed_buy_date:
            updated_fields["buy_date"] = str(b_date_val)
        if parsed_sell_date:
            updated_fields["sell_date"] = str(parsed_sell_date)

        old_init_sp = float(old_dev.get('initial_selling_price') or 0.0) if old_dev and old_dev.get('initial_selling_price') is not None else None

        if new_init_sp is not None and old_init_sp is not None and abs(new_init_sp - old_init_sp) > 0.01:
            diff_sp = new_init_sp - old_init_sp
            diff_label = f"بزيادة {diff_sp:+,.2f} ج.م" if diff_sp > 0 else f"بتخفيض {abs(diff_sp):,.2f} ج.م"
            act_sp_type = "UPDATE_PRICE_ABOVE" if diff_sp > 0 else "UPDATE_PRICE_BELOW"
            self.add_audit_log(
                user_id=user_id,
                user_name=None,
                action_type=act_sp_type,
                entity_type="DEVICE",
                entity_id=dev_id,
                description=f"⚠️ {'تعديل ورفع السعر المبدئي' if diff_sp > 0 else 'تعديل وتخفيض السعر المبدئي'} للجهاز #{dev_id} ({category} {model}): من {old_init_sp:,.2f} ج.م إلى {new_init_sp:,.2f} ج.م ({diff_label})",
                old_values={"initial_selling_price": old_init_sp, "buy_price": old_price},
                new_values={"initial_selling_price": new_init_sp, "price_diff": diff_sp, "difference_type": act_sp_type}
            )

        self.add_audit_log(
            user_id=user_id,
            user_name=None,
            action_type="EDIT_DEVICE",
            entity_type="DEVICE",
            entity_id=dev_id,
            description=f"تعديل بيانات ومواصفات الجهاز #{dev_id} ({category} {model}) وتحديث فاتورته المستقلة #{target_inv_id}",
            old_values=dict(old_dev) if old_dev else None,
            new_values=updated_fields
        )

    # =========================================================================
    # سداد دفعة مجمعة لمورد وتوزيعها على الأجهزة (Bulk Supplier Payment)
    # =========================================================================
    def pay_supplier_bulk_batch(self, supplier_id, total_amount, selected_device_ids=None, user_id=None, custom_date=None, notes=None):
        s_id = _clean_int_id(supplier_id)
        if not s_id:
            raise Exception("المورد غير محدد بشكل صحيح!")

        amount_to_distribute = float(total_amount or 0)
        if amount_to_distribute <= 0:
            raise Exception("يرجى إدخال مبلغ سداد صحيح أكبر من الصفر!")

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT name FROM suppliers WHERE id = %s;", (s_id,))
                supp = cur.fetchone()
                supp_name = supp['name'] if supp else f"مورد #{s_id}"

                if selected_device_ids and len(selected_device_ids) > 0:
                    clean_d_ids = [_clean_int_id(x) for x in selected_device_ids if _clean_int_id(x)]
                    cur.execute("""
                        SELECT i.id, i.total_amount, i.paid_amount, i.remaining_amount, i.supplier_credit, i.invoice_date,
                               d.id as dev_id, d.category, d.model
                        FROM supplier_invoices i
                        JOIN devices d ON d.invoice_id = i.id
                        WHERE i.supplier_id = %s AND i.remaining_amount > 0 AND COALESCE(d.is_archived, FALSE) = FALSE AND d.id = ANY(%s)
                        ORDER BY i.invoice_date ASC, i.id ASC
                        FOR UPDATE OF i;
                    """, (s_id, clean_d_ids))
                else:
                    cur.execute("""
                        SELECT i.id, i.total_amount, i.paid_amount, i.remaining_amount, i.supplier_credit, i.invoice_date,
                               d.id as dev_id, d.category, d.model
                        FROM supplier_invoices i
                        LEFT JOIN devices d ON d.invoice_id = i.id
                        WHERE i.supplier_id = %s AND i.remaining_amount > 0 AND COALESCE(d.is_archived, FALSE) = FALSE
                        ORDER BY i.invoice_date ASC, i.id ASC
                        FOR UPDATE OF i;
                    """, (s_id,))

                unpaid_invoices = cur.fetchall()

                remaining_pool = amount_to_distribute
                distribution_summary = []

                c_date = custom_date.strip() if (custom_date and str(custom_date).strip()) else None

                for inv in unpaid_invoices:
                    if remaining_pool <= 0:
                        break

                    inv_id = inv['id']
                    inv_rem = float(inv['remaining_amount'] or 0)
                    if inv_rem <= 0:
                        continue

                    pay_for_this = min(inv_rem, remaining_pool)
                    new_paid = float(inv['paid_amount'] or 0) + pay_for_this
                    new_rem = max(0.0, inv_rem - pay_for_this)
                    new_status = 'PAID' if new_rem <= 0 else 'UNPAID'

                    cur.execute("""
                        UPDATE supplier_invoices
                        SET paid_amount = %s, remaining_amount = %s, status = %s
                        WHERE id = %s;
                    """, (new_paid, new_rem, new_status, inv_id))

                    dev_name = f"{inv.get('category') or ''} {inv.get('model') or ''}".strip()
                    pay_note = f"دفعة مجمعة - سداد لجهاز #{inv.get('dev_id') or '-'} ({dev_name})"
                    if notes:
                        pay_note += f" - {notes}"

                    if c_date:
                        cur.execute("""
                            INSERT INTO supplier_payments (invoice_id, supplier_id, payment_amount, notes, created_by_user_id, payment_date)
                            VALUES (%s, %s, %s, %s, %s, %s::timestamp);
                        """, (inv_id, s_id, pay_for_this, pay_note, _clean_int_id(user_id), c_date))
                    else:
                        cur.execute("""
                            INSERT INTO supplier_payments (invoice_id, supplier_id, payment_amount, notes, created_by_user_id)
                            VALUES (%s, %s, %s, %s, %s);
                        """, (inv_id, s_id, pay_for_this, pay_note, _clean_int_id(user_id)))

                    distribution_summary.append({
                        'invoice_id': inv_id,
                        'device_id': inv.get('dev_id'),
                        'device_name': dev_name,
                        'paid_amount': pay_for_this,
                        'new_remaining': new_rem
                    })
                    remaining_pool -= pay_for_this

                excess_credit = max(0.0, remaining_pool)
                if excess_credit > 0:
                    cur.execute("SELECT id, supplier_credit FROM supplier_invoices WHERE supplier_id = %s ORDER BY id DESC LIMIT 1 FOR UPDATE;", (s_id,))
                    last_inv = cur.fetchone()
                    if last_inv:
                        cur_cred = float(last_inv['supplier_credit'] or 0)
                        cur.execute("UPDATE supplier_invoices SET supplier_credit = %s WHERE id = %s;", (cur_cred + excess_credit, last_inv['id']))
                    else:
                        cur.execute("""
                            INSERT INTO supplier_invoices (supplier_id, total_amount, paid_amount, remaining_amount, supplier_credit, status, invoice_date, created_by_user_id, notes)
                            VALUES (%s, 0.00, %s, 0.00, %s, 'PAID', CURRENT_DATE, %s, 'رصيد دائن فائض من دفعة مجمعة') RETURNING id;
                        """, (s_id, excess_credit, excess_credit, _clean_int_id(user_id)))

                conn.commit()

        self.add_audit_log(
            user_id=user_id,
            user_name=None,
            action_type="PAY_SUPPLIER_BULK",
            entity_type="SUPPLIER",
            entity_id=s_id,
            description=f"سداد دفعة مجمعة للمورد ({supp_name}) بقيمة {amount_to_distribute:,.2f} ج.م تم توزيعها على {len(distribution_summary)} جهاز/فاتورة" + (f" مع تسجيل فائض دائن {excess_credit:,.2f} ج.م" if excess_credit > 0 else ""),
            old_values=None,
            new_values={"total_paid": amount_to_distribute, "devices_count": len(distribution_summary), "excess_credit": excess_credit, "distribution": distribution_summary}
        )
        return {
            'total_paid': amount_to_distribute,
            'distributed_count': len(distribution_summary),
            'excess_credit': excess_credit,
            'details': distribution_summary
        }

    # =========================================================================
    # نظام أرشفة الأجهزة بالكامل (عزل مالي وحسابي وجدولي صارم)
    # =========================================================================
    def can_device_be_archived(self, device_id):
        dev_id = _clean_int_id(device_id)
        if not dev_id:
            return False, "كود الجهاز غير صالح!"

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM devices WHERE id = %s;", (dev_id,))
                dev = cur.fetchone()
                if not dev:
                    return False, "الجهاز غير موجود!"
                if dev.get('is_deleted'):
                    return False, "الجهاز محذوف ولا يمكن أرشفته!"

                if not dev.get('is_sold'):
                    return False, "الجهاز غير مباع حتى الآن (متاح في المخزون)! يشترط أن يكون الجهاز مباعاً ومسدداً."

                cur.execute("SELECT remaining_balance, sell_price, customer_name FROM sales WHERE device_id = %s;", (dev_id,))
                sale = cur.fetchone()
                if not sale:
                    return False, "لا توجد فاتورة بيع مسجلة لهذا الجهاز!"

                cust_rem = float(sale.get('remaining_balance') or 0)
                if cust_rem > 0:
                    return False, f"الجهاز غير مسدد من العميل بالكامل! متبقي عليه ({cust_rem:,.2f} ج.م)."

                inv_id = dev.get('invoice_id')
                if inv_id:
                    cur.execute("SELECT remaining_amount FROM supplier_invoices WHERE id = %s;", (inv_id,))
                    inv = cur.fetchone()
                    if inv:
                        supp_rem = float(inv.get('remaining_amount') or 0)
                        if supp_rem > 0:
                            return False, f"الجهاز غير مسدد للمورد بالكامل! متبقي في فاتورة المورد ({supp_rem:,.2f} ج.م)."

                return True, "الجهاز مؤهل تماماً للأرشفة (مباع ومسدد للطرفين)."

    def set_device_archived(self, device_id, is_archived=True, user_id=None):
        dev_id = _clean_int_id(device_id)
        if not dev_id:
            raise Exception("كود الجهاز غير صالح!")

        if is_archived:
            can_arch, reason = self.can_device_be_archived(dev_id)
            if not can_arch:
                raise Exception(reason)

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM devices WHERE id = %s FOR UPDATE;", (dev_id,))
                dev = cur.fetchone()
                if not dev:
                    raise Exception("الجهاز غير موجود!")

                if is_archived:
                    cur.execute("""
                        UPDATE devices 
                        SET is_archived = TRUE, archived_at = CURRENT_TIMESTAMP, archived_by_user_id = %s
                        WHERE id = %s;
                    """, (_clean_int_id(user_id), dev_id))
                    act = "ARCHIVE_DEVICE"
                    desc = f"أرشفة الجهاز #{dev_id} ({dev.get('category')} {dev.get('model')}) وعزل تأثيره المالي والجدولي بالكامل"
                else:
                    cur.execute("""
                        UPDATE devices 
                        SET is_archived = FALSE, archived_at = NULL, archived_by_user_id = NULL
                        WHERE id = %s;
                    """, (dev_id,))
                    act = "UNARCHIVE_DEVICE"
                    desc = f"إلغاء أرشفة الجهاز #{dev_id} ({dev.get('category')} {dev.get('model')}) وإعادته للعمليات النشطة"

                conn.commit()

        self.add_audit_log(
            user_id=user_id,
            user_name=None,
            action_type=act,
            entity_type="DEVICE",
            entity_id=dev_id,
            description=desc,
            old_values={"is_archived": dev.get('is_archived')},
            new_values={"is_archived": is_archived}
        )
        return True

    def archive_device(self, device_id, user_id=None):
        return self.set_device_archived(device_id, is_archived=True, user_id=user_id)

    def unarchive_device(self, device_id, user_id=None):
        return self.set_device_archived(device_id, is_archived=False, user_id=user_id)

    # =========================================================================
    # تعديل تاريخ العمليات
    # =========================================================================
    def update_operation_date(self, entity_type, entity_id, new_date, user_id=None, notes=None):
        clean_id = _clean_int_id(entity_id)
        if not clean_id:
            raise Exception("معرف العملية غير صالح!")
        if not new_date or not str(new_date).strip():
            raise Exception("التاريخ غير محدد!")

        parsed_dt = None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                parsed_dt = datetime.strptime(str(new_date).strip(), fmt)
                break
            except ValueError:
                continue
        if not parsed_dt:
            raise Exception("صيغة التاريخ غير صالحة! يرجى استخدام صيغة YYYY-MM-DD HH:MM")

        if parsed_dt.date() > datetime.now().date():
            raise Exception("لا يمكن تعيين تاريخ مستقبلي لأي عملية! يُسمح فقط بالتواريخ السابقة أو تاريخ اليوم.")

        date_str = parsed_dt.strftime("%Y-%m-%d %H:%M:%S")
        day_str = parsed_dt.strftime("%Y-%m-%d")

        old_date_val = None
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                ent_upper = str(entity_type).upper()
                if ent_upper in ("SALE", "SALES"):
                    cur.execute("SELECT sell_date, device_id FROM sales WHERE id = %s FOR UPDATE;", (clean_id,))
                    row = cur.fetchone()
                    if not row:
                        raise Exception("عملية البيع غير موجودة!")
                    old_date_val = str(row['sell_date'])

                    if row.get('device_id'):
                        cur.execute("SELECT buy_date FROM devices WHERE id = %s;", (row['device_id'],))
                        d_row = cur.fetchone()
                        if d_row and d_row.get('buy_date'):
                            buy_dt = datetime.strptime(str(d_row['buy_date']).split('.')[0], "%Y-%m-%d %H:%M:%S")
                            if parsed_dt < buy_dt:
                                raise Exception(f"لا يمكن أن يكون تاريخ البيع ({parsed_dt.strftime('%Y-%m-%d')}) أقدم من تاريخ شراء الجهاز ({buy_dt.strftime('%Y-%m-%d')})!")

                    cur.execute("UPDATE sales SET sell_date = %s::timestamp WHERE id = %s;", (date_str, clean_id))
                    cur.execute("UPDATE customer_payments SET payment_date = %s::timestamp WHERE sale_id = %s AND notes LIKE '%%دفعة مقدمة%%';", (date_str, clean_id))

                elif ent_upper in ("SUPPLIER_INVOICE", "INVOICE", "BUY_INVOICE"):
                    cur.execute("SELECT invoice_date FROM supplier_invoices WHERE id = %s FOR UPDATE;", (clean_id,))
                    row = cur.fetchone()
                    if not row:
                        raise Exception("فاتورة المورد غير موجودة!")
                    old_date_val = str(row['invoice_date'])
                    cur.execute("UPDATE supplier_invoices SET invoice_date = %s::date WHERE id = %s;", (day_str, clean_id))

                elif ent_upper in ("CUSTOMER_PAYMENT", "CUST_PAYMENT"):
                    cur.execute("SELECT payment_date FROM customer_payments WHERE id = %s FOR UPDATE;", (clean_id,))
                    row = cur.fetchone()
                    if not row:
                        raise Exception("دفعة العميل غير موجودة!")
                    old_date_val = str(row['payment_date'])
                    cur.execute("UPDATE customer_payments SET payment_date = %s::timestamp WHERE id = %s;", (date_str, clean_id))

                elif ent_upper in ("SUPPLIER_PAYMENT", "SUPP_PAYMENT"):
                    cur.execute("SELECT payment_date FROM supplier_payments WHERE id = %s FOR UPDATE;", (clean_id,))
                    row = cur.fetchone()
                    if not row:
                        raise Exception("دفعة المورد غير موجودة!")
                    old_date_val = str(row['payment_date'])
                    cur.execute("UPDATE supplier_payments SET payment_date = %s::timestamp WHERE id = %s;", (date_str, clean_id))

                elif ent_upper in ("CAPITAL_TRANSACTION", "LIQUIDITY"):
                    cur.execute("SELECT created_at FROM capital_transactions WHERE id = %s FOR UPDATE;", (clean_id,))
                    row = cur.fetchone()
                    if not row:
                        raise Exception("حركة السيولة غير موجودة!")
                    old_date_val = str(row['created_at'])
                    cur.execute("UPDATE capital_transactions SET created_at = %s::timestamp WHERE id = %s;", (date_str, clean_id))

                elif ent_upper in ("DEVICE", "DEVICES"):
                    cur.execute("SELECT buy_date, is_sold, invoice_id FROM devices WHERE id = %s FOR UPDATE;", (clean_id,))
                    row = cur.fetchone()
                    if not row:
                        raise Exception("الجهاز غير موجود!")
                    old_date_val = str(row['buy_date'])

                    if row.get('is_sold'):
                        cur.execute("SELECT sell_date FROM sales WHERE device_id = %s;", (clean_id,))
                        s_row = cur.fetchone()
                        if s_row and s_row.get('sell_date'):
                            sell_dt = datetime.strptime(str(s_row['sell_date']).split('.')[0], "%Y-%m-%d %H:%M:%S")
                            if parsed_dt > sell_dt:
                                raise Exception(f"لا يمكن أن يكون تاريخ شراء الجهاز ({parsed_dt.strftime('%Y-%m-%d')}) بعد تاريخ بيعه ({sell_dt.strftime('%Y-%m-%d')})!")

                    cur.execute("UPDATE devices SET buy_date = %s::timestamp WHERE id = %s;", (date_str, clean_id))
                    inv_id_val = row.get('invoice_id')
                    if inv_id_val:
                        cur.execute("UPDATE supplier_invoices SET invoice_date = %s::date WHERE id = %s;", (day_str, inv_id_val))
                else:
                    raise Exception(f"نوع العملية غير مدعوم ({entity_type})!")

                conn.commit()

        desc_extra = ""
        if ent_upper in ("DEVICE", "DEVICES") and row.get('invoice_id'):
            desc_extra = f" وتحديث تاريخ فاتورة المورد #{row['invoice_id']} التابع لها إلى ({day_str})"

        self.add_audit_log(
            user_id=user_id,
            user_name=None,
            action_type="UPDATE_DATE",
            entity_type=str(entity_type).upper(),
            entity_id=clean_id,
            description=f"تعديل تاريخ {entity_type} #{clean_id} من ({old_date_val}) إلى ({date_str}){desc_extra}" + (f" - ملاحظة: {notes}" if notes else ""),
            old_values={"old_date": str(old_date_val)},
            new_values={"new_date": str(date_str), "notes": notes, "synced_invoice_id": row.get('invoice_id') if ent_upper in ("DEVICE", "DEVICES") else None}
        )
        return True

    def get_device_supplier_invoice_status(self, device_id):
        dev_id = _clean_int_id(device_id)
        if not dev_id:
            return None
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT d.*, s.name as supplier_name FROM devices d LEFT JOIN suppliers s ON d.supplier_id = s.id WHERE d.id = %s;", (dev_id,))
                    dev = cur.fetchone()
                    if not dev:
                        return None
                    buy_price = float(dev['buy_price'] or 0)
                    inv_id = dev.get('invoice_id')
                    supp_id = dev.get('supplier_id')
                    supp_name = dev.get('supplier_name') or 'غير محدد'

                    if not inv_id and supp_id:
                        cur.execute("SELECT id FROM supplier_invoices WHERE supplier_id = %s ORDER BY id DESC LIMIT 1;", (supp_id,))
                        res = cur.fetchone()
                        if res:
                            inv_id = res['id']

                    if not inv_id:
                        return {'has_invoice': False, 'buy_price': buy_price, 'overpaid': 0.0, 'is_paid': False, 'supplier_name': supp_name}

                    cur.execute("SELECT * FROM supplier_invoices WHERE id = %s;", (inv_id,))
                    inv = cur.fetchone()
                    if not inv:
                        return {'has_invoice': False, 'buy_price': buy_price, 'overpaid': 0.0, 'is_paid': False, 'supplier_name': supp_name}

                    tot = float(inv['total_amount'] or 0)
                    paid = float(inv['paid_amount'] or 0)
                    rem = float(inv['remaining_amount'] or 0)
                    new_tot = max(0.0, tot - buy_price)
                    overpaid = max(0.0, paid - new_tot)
                    return {
                        'has_invoice': True,
                        'invoice_id': inv_id,
                        'supplier_id': inv['supplier_id'],
                        'supplier_name': supp_name,
                        'total_amount': tot,
                        'paid_amount': paid,
                        'remaining_amount': rem,
                        'new_total': new_tot,
                        'buy_price': buy_price,
                        'overpaid': overpaid,
                        'is_paid': paid > 0
                    }
        except Exception as ex:
            print(f"Error checking supplier invoice status: {ex}")
            return None

    # =========================================================================
    # حذف الجهاز مع معالجة الدفعات وتنظيفها لمنع ظهورها في الحسابات
    # =========================================================================
    def soft_delete_device(self, device_id, user_id=None, refund_mode="FROM_DEBT_FIRST"):
        dev_id = _clean_int_id(device_id)
        if dev_id is None:
            raise Exception("كود الجهاز غير صالح!")

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM devices WHERE id = %s FOR UPDATE;", (dev_id,))
                dev = cur.fetchone()
                if not dev:
                    raise Exception("الجهاز غير موجود!")

                if dev.get('is_archived'):
                    raise Exception("الجهاز مؤرشف ومقفل تماماً، لا يمكن حذفه أو إجراء أي تعديل مالي عليه!")

                if dev.get('is_deleted'):
                    return {"device_id": dev_id, "refund_mode": refund_mode, "excess_amount": 0.0}

                buy_price = float(dev['buy_price'] or 0)
                inv_id = dev.get('invoice_id')
                supp_id = dev.get('supplier_id')

                cur.execute("UPDATE devices SET is_deleted = TRUE, is_sold = FALSE WHERE id = %s;", (dev_id,))

                if not inv_id and supp_id:
                    cur.execute("SELECT id FROM supplier_invoices WHERE supplier_id = %s ORDER BY id DESC LIMIT 1;", (supp_id,))
                    res = cur.fetchone()
                    if res:
                        inv_id = res['id']

                excess_paid = 0.0
                if inv_id:
                    cur.execute("SELECT * FROM supplier_invoices WHERE id = %s FOR UPDATE;", (inv_id,))
                    inv = cur.fetchone()
                    if inv:
                        tot = float(inv['total_amount'] or 0)
                        paid = float(inv['paid_amount'] or 0)
                        old_credit = float(inv.get('supplier_credit') or 0.0)

                        new_tot = max(0.0, tot - buy_price)
                        overpaid = max(0.0, paid - new_tot)
                        excess_paid = overpaid

                        if refund_mode == "CASH_REFUND":
                            new_paid = new_tot
                            new_rem = 0.0
                            status = 'CANCELLED' if new_tot <= 0 else ('PAID' if new_rem <= 0 else 'UNPAID')

                            cur.execute("""
                                UPDATE supplier_invoices 
                                SET total_amount = %s, paid_amount = %s, remaining_amount = %s, status = %s
                                WHERE id = %s;
                            """, (new_tot, new_paid, new_rem, status, inv_id))

                            if excess_paid > 0:
                                cur.execute("""
                                    INSERT INTO capital_transactions (amount, transaction_type, notes, created_by_user_id)
                                    VALUES (%s, 'SUPPLIER_REFUND', %s, %s);
                                """, (excess_paid, f"استرداد نقدي فوري بالخزينة لحذف الجهاز #{dev_id} ({dev.get('category')} {dev.get('model')})", _clean_int_id(user_id)))

                        elif refund_mode == "SUPPLIER_CREDIT":
                            new_paid = paid
                            new_rem = 0.0
                            new_credit = old_credit + overpaid
                            status = 'REFUNDED_CREDIT' if new_tot <= 0 else 'PAID'

                            cur.execute("""
                                UPDATE supplier_invoices 
                                SET total_amount = %s, paid_amount = %s, remaining_amount = %s, supplier_credit = %s, status = %s
                                WHERE id = %s;
                            """, (new_tot, new_paid, new_rem, new_credit, status, inv_id))

                        else:  # FROM_DEBT_FIRST
                            if overpaid > 0:
                                new_paid = paid
                                new_rem = 0.0
                                new_credit = old_credit + overpaid
                                status = 'CANCELLED' if new_tot <= 0 else 'PAID'
                                cur.execute("""
                                    UPDATE supplier_invoices 
                                    SET total_amount = %s, paid_amount = %s, remaining_amount = %s, supplier_credit = %s, status = %s
                                    WHERE id = %s;
                                """, (new_tot, new_paid, new_rem, new_credit, status, inv_id))
                            else:
                                new_paid = paid
                                new_rem = max(0.0, new_tot - new_paid)
                                status = 'CANCELLED' if new_tot <= 0 else ('PAID' if new_rem <= 0 else 'UNPAID')
                                cur.execute("""
                                    UPDATE supplier_invoices 
                                    SET total_amount = %s, paid_amount = %s, remaining_amount = %s, status = %s
                                    WHERE id = %s;
                                """, (new_tot, new_paid, new_rem, status, inv_id))

                # تنظيف وحذف تحصيلات المبيعات التابعة للجهاز المحذوف حتى لا تظهر في سجلات الدفع
                cur.execute("SELECT id FROM sales WHERE device_id = %s;", (dev_id,))
                sale = cur.fetchone()
                if sale:
                    sale_id = sale['id']
                    cur.execute("DELETE FROM customer_payments WHERE sale_id = %s;", (sale_id,))
                    cur.execute("DELETE FROM sales WHERE id = %s;", (sale_id,))

                conn.commit()

        action_type_desc = (
            f"مرتجع للمورد مع استرداد نقدي فوري للخزينة بقيمة {excess_paid:,.2f} ج.م" if refund_mode == "CASH_REFUND" and excess_paid > 0
            else f"مرتجع للمورد مع ترحيل رصيد دائن للمورد بقيمة {excess_paid:,.2f} ج.م" if refund_mode == "SUPPLIER_CREDIT" and excess_paid > 0
            else f"مرتجع جهاز للمورد وخصم تكلفته من مديونية المورد" + (f" مع حفظ فائض {excess_paid:,.2f} ج.م كرصيد دائن" if excess_paid > 0 else "")
        )
        self.add_audit_log(
            user_id=user_id,
            user_name=None,
            action_type="DEVICE_RETURN_TO_SUPPLIER",
            entity_type="DEVICE",
            entity_id=dev_id,
            description=f"{action_type_desc} #{dev_id} ({dev.get('category')} {dev.get('model')})",
            old_values=dict(dev),
            new_values={"is_deleted": True, "refund_mode": refund_mode, "excess_amount": excess_paid, "buy_price": buy_price}
        )
        return {"device_id": dev_id, "refund_mode": refund_mode, "excess_amount": excess_paid}

    def delete_device(self, device_id, user_id=None, refund_mode="FROM_DEBT_FIRST"):
        return self.soft_delete_device(device_id, user_id=user_id, refund_mode=refund_mode)

    def refund_supplier_credit_to_cash(self, invoice_id, amount=None, user_id=None):
        inv_id = _clean_int_id(invoice_id)
        if inv_id is None:
            raise Exception("رقم الفاتورة غير صالح!")

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT i.*, s.name as supplier_name FROM supplier_invoices i LEFT JOIN suppliers s ON i.supplier_id = s.id WHERE i.id = %s FOR UPDATE OF i;", (inv_id,))
                inv = cur.fetchone()
                if not inv:
                    raise Exception("الفاتورة غير موجودة!")

                cur.execute("SELECT 1 FROM devices WHERE invoice_id = %s AND COALESCE(is_archived, FALSE) = TRUE;", (inv_id,))
                if cur.fetchone():
                    raise Exception("هذه الفاتورة تابعة لجهاز مؤرشف ومقفل تماماً، لا يمكن إجراء أي استرداد مالي لها!")

                available_credit = float(inv.get('supplier_credit') or 0.0)
                if available_credit <= 0:
                    raise Exception("لا يوجد رصيد دائن مستحق لنا في هذه الفاتورة!")

                if amount is None or str(amount).strip() == "":
                    refund_amt = available_credit
                else:
                    try:
                        refund_amt = float(amount)
                    except ValueError:
                        raise Exception("المبلغ المدخل غير صالح!")

                if refund_amt <= 0:
                    raise Exception("مبلغ الاسترداد يجب أن يكون أكبر من الصفر!")
                if refund_amt > available_credit:
                    raise Exception(f"المبلغ المطلوب استرداده ({refund_amt:,.2f} ج.م) يتجاوز الرصيد الدائن المتاح ({available_credit:,.2f} ج.م)!")

                new_credit = max(0.0, available_credit - refund_amt)
                rem = float(inv.get('remaining_amount') or 0.0)
                tot_amt = float(inv.get('total_amount') or 0.0)
                supp_name = inv.get('supplier_name') or f"مورد #{inv.get('supplier_id')}"

                curr_paid = float(inv.get('paid_amount') or 0.0)
                new_paid = max(0.0, curr_paid - refund_amt)

                new_status = 'CANCELLED' if (new_credit <= 0 and rem <= 0 and tot_amt <= 0) else ('PAID' if rem <= 0 else 'UNPAID')

                cur.execute("""
                    UPDATE supplier_invoices 
                    SET supplier_credit = %s, paid_amount = %s, status = %s 
                    WHERE id = %s;
                """, (new_credit, new_paid, new_status, inv_id))

                try:
                    clean_uid = _clean_int_id(user_id)
                    cur.execute("""
                        INSERT INTO capital_transactions (amount, transaction_type, notes, created_by_user_id)
                        VALUES (%s, 'SUPPLIER_REFUND', %s, %s);
                    """, (refund_amt, f"استرداد نقدي من رصيد دائن لدى المورد {supp_name} (فاتورة #{inv_id})", clean_uid))
                except Exception as tx_e:
                    print(f"Notice: capital transaction insert for refund: {tx_e}")

                conn.commit()

        self.add_audit_log(
            user_id=user_id,
            user_name=None,
            action_type="CLAIM_SUPPLIER_CREDIT",
            entity_type="SUPPLIER_INVOICE",
            entity_id=inv_id,
            description=f"استرداد نقدي لرصيد دائن من المورد ({supp_name}) بقيمة {refund_amt:,.2f} ج.م وإيداعه في خزينة السيولة (فاتورة #{inv_id}) - المتبقي دائن: {new_credit:,.2f} ج.م",
            old_values={"supplier_credit": available_credit, "paid_amount": curr_paid},
            new_values={"supplier_credit": new_credit, "refunded_amount": refund_amt, "paid_amount": new_paid}
        )
        return refund_amt

    # =========================================================================
    # استعلام المخزون - استبعاد المؤرشفين افتراضياً
    # =========================================================================
    def get_inventory(self, include_sold=False, include_archived=False, archived_only=False):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    where_clauses = ["COALESCE(d.is_deleted, FALSE) = FALSE"]

                    if archived_only:
                        where_clauses.append("COALESCE(d.is_archived, FALSE) = TRUE")
                    elif not include_archived:
                        where_clauses.append("COALESCE(d.is_archived, FALSE) = FALSE")

                    if not include_sold and not archived_only:
                        where_clauses.append("COALESCE(d.is_sold, FALSE) = FALSE")

                    where_sql = " AND ".join(where_clauses)
                    cur.execute(f"""
                        SELECT d.id, d.category, d.model, d.storage, d.ram, d.battery_health,
                               COALESCE(d.device_condition, 'مستعمل') as device_condition,
                               COALESCE(d.has_box, FALSE) as has_box,
                               COALESCE(d.color, 'أسود') as color,
                               COALESCE(d.has_tax, FALSE) as has_tax,
                               COALESCE(d.accessories, '') as accessories,
                               COALESCE(d.notes, '') as notes,
                               d.imei_serial, d.buy_price,
                               COALESCE(d.initial_selling_price, d.buy_price) as initial_selling_price,
                               COALESCE(d.is_sold, FALSE) as is_sold,
                               COALESCE(d.is_deleted, FALSE) as is_deleted,
                               COALESCE(d.is_archived, FALSE) as is_archived,
                               TO_CHAR(d.archived_at, 'YYYY-MM-DD HH24:MI') as archived_at_formatted,
                               COALESCE(s.name, 'غير محدد') as supplier_name,
                               COALESCE(s.supplier_type, 'تاجر') as supplier_type,
                               TO_CHAR(d.buy_date, 'YYYY-MM-DD HH24:MI') as buy_date_formatted
                        FROM devices d
                        LEFT JOIN suppliers s ON d.supplier_id = s.id
                        WHERE {where_sql}
                        ORDER BY d.id DESC;
                    """)
                    return cur.fetchall()
        except Exception as e:
            print(f"get_inventory error: {e}")
            return []

    def search_available_devices(self, query):
        return self.get_available_inventory(search_query=query, search_by='ALL')

    def get_device_by_id(self, device_id):
        dev_id = _clean_int_id(device_id)
        if not dev_id:
            return None
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT d.*,
                               COALESCE(d.device_condition, 'مستعمل') as device_condition,
                               COALESCE(d.has_box, FALSE) as has_box,
                               COALESCE(NULLIF(d.color, 'بدون'), 'أسود') as color,
                               COALESCE(d.has_tax, FALSE) as has_tax,
                               COALESCE(d.accessories, '') as accessories,
                               COALESCE(d.initial_selling_price, d.buy_price) as initial_selling_price,
                               COALESCE(d.is_archived, FALSE) as is_archived,
                               TO_CHAR(d.archived_at, 'YYYY-MM-DD HH24:MI') as archived_at_formatted,
                               COALESCE(s.name, 'غير محدد') as supplier_name,
                               COALESCE(s.supplier_type, 'تاجر') as supplier_type,
                               TO_CHAR(d.buy_date, 'YYYY-MM-DD HH24:MI') as buy_date_formatted
                        FROM devices d
                        LEFT JOIN suppliers s ON d.supplier_id = s.id
                        WHERE d.id = %s AND COALESCE(d.is_deleted, FALSE) = FALSE;
                    """, (dev_id,))
                    return cur.fetchone()
        except Exception:
            return None

    def get_available_inventory(self, search_query=None, search_by='ALL', filters=None):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT d.id, d.category, d.model, d.storage, d.ram, d.battery_health,
                               COALESCE(d.device_condition, 'مستعمل') as device_condition,
                               COALESCE(d.has_box, FALSE) as has_box,
                               COALESCE(NULLIF(d.color, 'بدون'), 'أسود') as color,
                               COALESCE(d.has_tax, FALSE) as has_tax,
                               COALESCE(d.accessories, '') as accessories,
                               COALESCE(d.notes, '') as notes,
                               d.imei_serial, d.buy_price,
                               COALESCE(d.initial_selling_price, d.buy_price) as initial_selling_price,
                               COALESCE(s.name, 'غير محدد') as supplier_name,
                               COALESCE(s.supplier_type, 'تاجر') as supplier_type,
                               TO_CHAR(d.buy_date, 'YYYY-MM-DD HH24:MI') as buy_date_formatted
                        FROM devices d
                        LEFT JOIN suppliers s ON d.supplier_id = s.id
                        WHERE COALESCE(d.is_sold, FALSE) = FALSE 
                          AND COALESCE(d.is_deleted, FALSE) = FALSE
                          AND COALESCE(d.is_archived, FALSE) = FALSE
                    """
                    params = []
                    if search_query:
                        q_str = str(search_query).strip()
                        q_clean = q_str.lstrip('#')
                        if search_by == 'ID':
                            query += " AND CAST(d.id AS TEXT) = %s"
                            params.append(q_clean)
                        elif search_by == 'SERIAL':
                            query += " AND d.imei_serial ILIKE %s"
                            params.append(f"%{q_str}%")
                        elif search_by == 'NAME':
                            query += " AND (d.model ILIKE %s OR d.category ILIKE %s OR (d.category || ' ' || d.model) ILIKE %s)"
                            params.extend([f"%{q_str}%", f"%{q_str}%", f"%{q_str}%"])
                        else:
                            query += " AND (d.model ILIKE %s OR d.imei_serial ILIKE %s OR d.category ILIKE %s OR (d.category || ' ' || d.model) ILIKE %s OR CAST(d.id AS TEXT) = %s)"
                            params.extend([f"%{q_str}%", f"%{q_str}%", f"%{q_str}%", f"%{q_str}%", q_clean])

                    query += " ORDER BY d.id DESC;"
                    cur.execute(query, params)
                    return cur.fetchall()
        except Exception as e:
            print(f"Inventory query error: {e}")
            return []

    def search_device_by_criteria(self, query, search_by='SERIAL', include_archived=False):
        try:
            q_str = str(query or "").strip()
            if not q_str:
                return None
            q_id = q_str.lstrip('#')

            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    arch_clause = "" if include_archived else " AND COALESCE(d.is_archived, FALSE) = FALSE"
                    base_select = f"""
                        SELECT d.*,
                               COALESCE(d.device_condition, 'مستعمل') as device_condition,
                               COALESCE(d.has_box, FALSE) as has_box,
                               COALESCE(NULLIF(d.color, 'بدون'), 'أسود') as color,
                               COALESCE(d.has_tax, FALSE) as has_tax,
                               COALESCE(d.accessories, '') as accessories,
                               COALESCE(d.is_archived, FALSE) as is_archived,
                               TO_CHAR(d.archived_at, 'YYYY-MM-DD HH24:MI') as archived_at_formatted,
                               COALESCE(s.name, 'غير محدد') as supplier_name,
                               TO_CHAR(d.buy_date, 'YYYY-MM-DD HH24:MI') as buy_date_formatted,
                               sl.id as sale_id, sl.sell_price, sl.customer_name, sl.customer_phone,
                               sl.cash_received, sl.remaining_balance, sl.notes as sale_notes,
                               TO_CHAR(sl.sell_date, 'YYYY-MM-DD HH24:MI') as sell_date_formatted
                        FROM devices d
                        LEFT JOIN suppliers s ON d.supplier_id = s.id
                        LEFT JOIN sales sl ON d.id = sl.device_id
                        WHERE COALESCE(d.is_deleted, FALSE) = FALSE {arch_clause}
                    """

                    if search_by == 'ID':
                        sql = base_select + " AND CAST(d.id AS TEXT) = %s ORDER BY d.is_sold ASC, d.id DESC LIMIT 1;"
                        cur.execute(sql, (q_id,))
                        return cur.fetchone()

                    elif search_by in ('SERIAL', 'IMEI'):
                        sql_exact = base_select + " AND LOWER(TRIM(d.imei_serial)) = LOWER(%s) ORDER BY d.is_sold ASC, d.id DESC LIMIT 1;"
                        cur.execute(sql_exact, (q_str,))
                        res = cur.fetchone()
                        if res:
                            return res
                        sql_like = base_select + " AND d.imei_serial ILIKE %s ORDER BY d.is_sold ASC, d.id DESC LIMIT 1;"
                        cur.execute(sql_like, (f"%{q_str}%",))
                        return cur.fetchone()

                    elif search_by in ('NAME', 'MODEL'):
                        sql = base_select + """
                            AND (d.model ILIKE %s OR d.category ILIKE %s OR (d.category || ' ' || d.model) ILIKE %s)
                            ORDER BY d.is_sold ASC, d.id DESC LIMIT 1;
                        """
                        cur.execute(sql, (f"%{q_str}%", f"%{q_str}%", f"%{q_str}%"))
                        return cur.fetchone()

                    else:
                        sql = base_select + """
                            AND (LOWER(TRIM(d.imei_serial)) = LOWER(%s)
                                 OR CAST(d.id AS TEXT) = %s
                                 OR d.imei_serial ILIKE %s
                                 OR d.model ILIKE %s
                                 OR d.category ILIKE %s
                                 OR (d.category || ' ' || d.model) ILIKE %s)
                            ORDER BY 
                                CASE 
                                    WHEN LOWER(TRIM(d.imei_serial)) = LOWER(%s) THEN 1
                                    WHEN CAST(d.id AS TEXT) = %s THEN 2
                                    ELSE 3
                                END ASC,
                                d.is_sold ASC,
                                d.id DESC
                            LIMIT 1;
                        """
                        cur.execute(sql, (q_str, q_id, f"%{q_str}%", f"%{q_str}%", f"%{q_str}%", f"%{q_str}%", q_str, q_id))
                        return cur.fetchone()
        except Exception as e:
            print(f"Search error: {e}")
            return None

    def search_device_by_imei_or_id(self, query, include_archived=False):
        return self.search_device_by_criteria(query, search_by='ALL', include_archived=include_archived)

    # =========================================================================
    # إتمام البيع الفوري (Instant Sale Logic)
    # =========================================================================
    def process_sale(self, device_id, sell_price, customer_name, customer_phone, cash_received, notes, user_id, original_price=None, discount=0.0, custom_date=None, customer_address=""):
        dev_id = _clean_int_id(device_id)
        if dev_id is None:
            raise Exception("كود الجهاز غير صالح!")

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT buy_price, is_deleted, is_archived, category, model, initial_selling_price FROM devices WHERE id = %s AND COALESCE(is_sold, FALSE) = FALSE FOR UPDATE", (dev_id,))
                dev = cur.fetchone()
                if not dev or dev.get('is_deleted'):
                    raise Exception("الجهاز غير متاح للبيع أو تم حذفه مسبقاً!")

                if dev.get('is_archived'):
                    raise Exception("هذا الجهاز مؤرشف، لا يمكن بيعه!")

                buy_price = float(dev['buy_price'])
                sell_val = float(sell_price)
                orig_val = float(original_price) if original_price is not None else sell_val
                disc_val = float(discount or 0.0)

                cash = float(cash_received or 0)
                if cash > sell_val:
                    raise Exception("المبلغ المدفوع أكبر من سعر البيع النهائي!")

                rem = max(0.0, sell_val - cash)
                clean_addr = (customer_address or "").strip()
                if rem > 0 and not clean_addr:
                    raise Exception("يجب إدخال عنوان العميل في حالة البيع الآجل (وجود متبقي دين)!")

                net_profit = sell_val - buy_price
                init_p = float(dev['initial_selling_price']) if dev.get('initial_selling_price') is not None else None

                c_date = custom_date.strip() if (custom_date and str(custom_date).strip()) else None
                if c_date:
                    cur.execute("""
                        INSERT INTO sales (device_id, original_price, discount, sell_price, customer_name, customer_phone, customer_address, cash_received, remaining_balance, net_profit, notes, created_by_user_id, sell_date)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::timestamp) RETURNING id;
                    """, (dev_id, orig_val, disc_val, sell_val, customer_name or 'عميل نقدي', customer_phone or '', clean_addr, cash, rem, net_profit, notes or '', _clean_int_id(user_id), c_date))
                else:
                    cur.execute("""
                        INSERT INTO sales (device_id, original_price, discount, sell_price, customer_name, customer_phone, customer_address, cash_received, remaining_balance, net_profit, notes, created_by_user_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
                    """, (dev_id, orig_val, disc_val, sell_val, customer_name or 'عميل نقدي', customer_phone or '', clean_addr, cash, rem, net_profit, notes or '', _clean_int_id(user_id)))
                sale_id = cur.fetchone()['id']

                if cash > 0:
                    if c_date:
                        cur.execute("""
                            INSERT INTO customer_payments (sale_id, payment_amount, notes, created_by_user_id, payment_date)
                            VALUES (%s, %s, %s, %s, %s::timestamp);
                        """, (sale_id, cash, 'دفعة مقدمة عند البيع', _clean_int_id(user_id), c_date))
                    else:
                        cur.execute("""
                            INSERT INTO customer_payments (sale_id, payment_amount, notes, created_by_user_id)
                            VALUES (%s, %s, %s, %s);
                        """, (sale_id, cash, 'دفعة مقدمة عند البيع', _clean_int_id(user_id)))

                cur.execute("UPDATE devices SET is_sold = TRUE WHERE id = %s;", (dev_id,))
                conn.commit()

        price_diff_note = ""
        if init_p is not None and abs(sell_val - init_p) > 0.01:
            p_diff = sell_val - init_p
            diff_str = f"بزيادة {p_diff:+,.2f} ج.م" if p_diff > 0 else f"بخصم {abs(p_diff):,.2f} ج.م"
            price_diff_note = f" [تعديل عن المبدئي: {init_p:,.2f} ج.م {diff_str}]"

            act_diff_type = "SALE_PRICE_ABOVE_INITIAL" if p_diff > 0 else "SALE_PRICE_BELOW_INITIAL"
            self.add_audit_log(
                user_id=user_id,
                user_name=None,
                action_type=act_diff_type,
                entity_type="SALE",
                entity_id=sale_id,
                description=f"⚠️ {'بيع بأعلى من السعر المبدئي' if p_diff > 0 else 'بيع بأقل من السعر المبدئي'} للجهاز #{dev_id} ({dev.get('category', '')} {dev.get('model', '')}): من {init_p:,.2f} ج.م إلى {sell_val:,.2f} ج.م ({diff_str})",
                old_values={"initial_selling_price": init_p, "device_id": dev_id},
                new_values={"final_selling_price": sell_val, "sale_id": sale_id, "price_difference": p_diff, "difference_type": act_diff_type}
            )

        if buy_price is not None and sell_val < (buy_price - 0.01):
            loss_amt = buy_price - sell_val
            self.add_audit_log(
                user_id=user_id,
                user_name=None,
                action_type="SALE_BELOW_COST",
                entity_type="SALE",
                entity_id=sale_id,
                description=f"⚠️ بيع بأقل من سعر الشراء (خسارة) للجهاز #{dev_id} ({dev.get('category', '')} {dev.get('model', '')}): تكلفة الشراء {buy_price:,.2f} ج.م وسعر البيع {sell_val:,.2f} ج.م (خسارة {loss_amt:,.2f} ج.م)",
                old_values={"buy_price": buy_price, "device_id": dev_id},
                new_values={"sell_price": sell_val, "sale_id": sale_id, "loss_amount": loss_amt, "difference_type": "SALE_BELOW_COST"}
            )

        self.add_audit_log(
            user_id=user_id,
            user_name=None,
            action_type="SALE",
            entity_type="SALE",
            entity_id=sale_id,
            description=f"إتمام بيع جهاز #{dev_id} للعميل ({customer_name or 'عميل نقدي'}) بسعر {sell_val:,.2f} ج.م ومتبقي {rem:,.2f} ج.م{price_diff_note}",
            old_values={"is_sold": False, "device_id": dev_id, "initial_selling_price": init_p, "buy_price": buy_price},
            new_values={"sale_id": sale_id, "sell_price": sell_val, "cash_received": cash, "remaining": rem, "customer_name": customer_name, "price_adjusted": bool(price_diff_note)}
        )
        return sale_id

    # =========================================================================
    # استرجاع جهاز مباع للمخزون (مع منع الأجهزة المؤرشفة تماماً)
    # =========================================================================
    def process_return(self, device_id, user_id=None):
        dev_id = _clean_int_id(device_id)
        if not dev_id:
            raise Exception("كود الجهاز غير صالح!")

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM devices WHERE id = %s FOR UPDATE;", (dev_id,))
                dev = cur.fetchone() or {}
                if not dev:
                    raise Exception("الجهاز غير موجود!")

                if dev.get('is_archived'):
                    raise Exception("هذا الجهاز مؤرشف ومقفل تماماً، لا يمكن استرجاعه أو إجراء أي حركة عليه!")

                cur.execute("SELECT * FROM sales WHERE device_id = %s FOR UPDATE;", (dev_id,))
                sale = cur.fetchone()
                if not sale:
                    raise Exception("لا توجد فاتورة بيع مسجلة لهذا الجهاز لإرجاعه!")

                cash_back = float(sale.get('cash_received') or 0.0)

                cur.execute("DELETE FROM customer_payments WHERE sale_id = %s;", (sale['id'],))
                cur.execute("DELETE FROM sales WHERE id = %s;", (sale['id'],))

                cur.execute("UPDATE devices SET is_sold = FALSE, is_archived = FALSE WHERE id = %s;", (dev_id,))
                conn.commit()

        sale_info = dict(sale) if sale else {}
        self.add_audit_log(
            user_id=user_id,
            user_name=None,
            action_type="RETURN_DEVICE",
            entity_type="DEVICE",
            entity_id=dev_id,
            description=f"⚠️ استرجاع جهاز مباع #{dev_id} ({dev.get('category', '')} {dev.get('model', '')}) وإلغاء فاتورة البيع #{sale_info.get('id', '-')} للعميل ({sale_info.get('customer_name', 'نقدي')}) بقيمة {float(sale_info.get('sell_price') or 0):,.2f} ج.م مع رد نقدية {cash_back:,.2f} ج.م وإعادة الجهاز للمخزون",
            old_values={"is_sold": True, "sale_id": sale_info.get('id'), "sell_price": float(sale_info.get('sell_price') or 0), "customer_name": sale_info.get('customer_name'), "cash_received": cash_back, "remaining_balance": float(sale_info.get('remaining_balance') or 0)},
            new_values={"is_sold": False, "device_id": dev_id, "inventory_status": "IN_STOCK", "cash_refunded_to_customer": cash_back}
        )

    # =========================================================================
    # ديون العملاء (استبعاد المؤرشف والمحذوف بشكل كامل)
    # =========================================================================
    def get_customer_debts(self, search_query=None, include_archived=False):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    arch_clause = "" if include_archived else "AND COALESCE(d.is_archived, FALSE) = FALSE"
                    query = f"""
                        SELECT s.id as sale_id, s.id as id, d.id as device_id, d.category, d.model, d.imei_serial,
                               d.storage, d.ram,
                               COALESCE(d.device_condition, 'مستعمل') as device_condition,
                               COALESCE(d.has_box, FALSE) as has_box,
                               COALESCE(NULLIF(d.color, 'بدون'), 'أسود') as color,
                               COALESCE(d.has_tax, FALSE) as has_tax,
                               COALESCE(d.is_archived, FALSE) as is_archived,
                               s.customer_name, s.customer_phone,
                               s.sell_price, s.sell_price as total_amount,
                               s.cash_received, s.cash_received as paid_amount,
                               s.remaining_balance, s.remaining_balance as remaining_amount,
                               COALESCE(s.notes, '') as sale_notes,
                               TO_CHAR(s.sell_date, 'YYYY-MM-DD HH24:MI') as sell_date_formatted,
                               TO_CHAR(s.sell_date, 'YYYY-MM-DD HH24:MI') as created_at,
                               COALESCE(u.full_name, u.username, 'بائع النظام') as seller_name
                        FROM sales s
                        JOIN devices d ON s.device_id = d.id
                        LEFT JOIN users u ON s.created_by_user_id = u.id
                        WHERE s.remaining_balance > 0 
                          AND COALESCE(d.is_deleted, FALSE) = FALSE 
                          {arch_clause}
                    """
                    params = []
                    if search_query and str(search_query).strip():
                        q = str(search_query).strip()
                        q_clean = q.lstrip('#')
                        query += " AND (s.customer_name ILIKE %s OR COALESCE(s.customer_phone, '') ILIKE %s OR d.model ILIKE %s OR d.imei_serial ILIKE %s OR CAST(s.id AS TEXT) = %s OR CAST(d.id AS TEXT) = %s OR TO_CHAR(s.sell_date, 'YYYY-MM-DD') ILIKE %s)"
                        params.extend([f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", q_clean, q_clean, f"%{q}%"])
                    query += " ORDER BY s.id DESC;"
                    cur.execute(query, params)
                    rows = cur.fetchall()
                    for r in rows:
                        r['invoice_code'] = f"INV-DEBT-{r['sale_id']:05d}"
                    return rows
        except Exception as e:
            print(f"Customer debts error: {e}")
            return []

    def get_customer_sale_payments(self, sale_id):
        s_id = _clean_int_id(sale_id)
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT cp.id, cp.payment_amount,
                               COALESCE(cp.notes, '') as notes,
                               TO_CHAR(cp.payment_date, 'YYYY-MM-DD HH24:MI') as payment_date_formatted,
                               COALESCE(u.full_name, u.username, 'مستخدم النظام') as receiver_name
                        FROM customer_payments cp
                        LEFT JOIN users u ON cp.created_by_user_id = u.id
                        WHERE cp.sale_id = %s
                        ORDER BY cp.id ASC;
                    """, (s_id,))
                    return cur.fetchall()
        except Exception:
            return []

    def get_customer_debt_payments(self, sale_id):
        return self.get_customer_sale_payments(sale_id)

    def pay_customer_debt(self, sale_id, amount, user_id, notes="", custom_date=None):
        s_id = _clean_int_id(sale_id)
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT s.remaining_balance, s.cash_received, COALESCE(d.is_archived, FALSE) as is_archived 
                    FROM sales s 
                    LEFT JOIN devices d ON s.device_id = d.id 
                    WHERE s.id = %s FOR UPDATE OF s;
                """, (s_id,))
                sale = cur.fetchone()
                if not sale:
                    raise Exception("الفاتورة غير موجودة!")

                if sale.get('is_archived'):
                    raise Exception("فاتورة البيع هذه تابعة لجهاز مؤرشف ومقفل، لا يمكن تحصيل أي مبالغ لها!")

                rem = float(sale['remaining_balance'] or 0.0)
                if rem <= 0.00:
                    raise Exception("تم سداد كامل مديونية هذا العميل مسبقاً! (المتبقي: 0.00 ج.م)")

                pay_amt = float(amount or 0.0)
                if pay_amt <= 0:
                    raise Exception("يرجى إدخال مبلغ تحصيل صحيح أكبر من الصفر!")
                if pay_amt > rem:
                    raise Exception(f"المبلغ المدفوع ({pay_amt:,.2f} ج.م) أكبر من المتبقي ({rem:,.2f} ج.م)!")

                new_cash = float(sale['cash_received']) + amount
                new_rem = max(0.0, rem - amount)

                c_date = custom_date.strip() if (custom_date and str(custom_date).strip()) else None
                cur.execute("UPDATE sales SET cash_received = %s, remaining_balance = %s WHERE id = %s;", (new_cash, new_rem, s_id))
                if c_date:
                    cur.execute("INSERT INTO customer_payments (sale_id, payment_amount, notes, created_by_user_id, payment_date) VALUES (%s, %s, %s, %s, %s::timestamp);", (s_id, amount, notes or 'تحصيل دفعة من العميل', _clean_int_id(user_id), c_date))
                else:
                    cur.execute("INSERT INTO customer_payments (sale_id, payment_amount, notes, created_by_user_id) VALUES (%s, %s, %s, %s);", (s_id, amount, notes or 'تحصيل دفعة من العميل', _clean_int_id(user_id)))
                conn.commit()

        self.add_audit_log(
            user_id=user_id,
            user_name=None,
            action_type="COLLECT_DEBT",
            entity_type="CUSTOMER_DEBT",
            entity_id=s_id,
            description=f"تحصيل دفعة مديونية بقيمة {amount:,.2f} ج.م للفاتورة #{s_id} (متبقي جديد: {new_rem:,.2f} ج.م)" + (f" [تاريخ: {c_date}]" if c_date else ""),
            old_values={"remaining_balance": rem},
            new_values={"paid_now": amount, "new_remaining": new_rem}
        )

    def collect_debt_installment(self, sale_id, amount, user_id, notes="", custom_date=None):
        return self.pay_customer_debt(sale_id, amount, user_id, notes=notes, custom_date=custom_date)

    # =========================================================================
    # فواتير الموردين - استبعاد فواتير الأجهزة المؤرشفة والمحذوفة
    # =========================================================================
    def get_supplier_invoices(self, search_query=None, status_filter='ALL', search_by='ALL', supplier_id=None, unpaid_only=False, date_from=None, date_to=None, include_archived=False, archived_only=False):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT i.id, i.supplier_id,
                               COALESCE(s.name, 'غير محدد') as supplier_name,
                               COALESCE(s.phone, '-') as supplier_phone,
                               COALESCE(s.supplier_type, 'تاجر') as supplier_type,
                               TO_CHAR(i.invoice_date, 'YYYY-MM-DD') as inv_date,
                               TO_CHAR(i.invoice_date, 'YYYY-MM-DD') as invoice_date,
                               TO_CHAR(i.invoice_date, 'YYYY-MM-DD') as date_formatted,
                               COALESCE(d_agg.devices_count, 0) as devices_count,
                               d_agg.is_device_archived,
                               d_agg.device_id,
                               d_agg.device_name,
                               d_agg.device_imei,
                               i.total_amount, i.paid_amount, i.remaining_amount,
                               COALESCE(i.supplier_credit, 0.00) as supplier_credit,
                               i.status,
                               COALESCE(i.notes, '') as notes
                        FROM supplier_invoices i
                        LEFT JOIN suppliers s ON i.supplier_id = s.id
                        LEFT JOIN (
                            SELECT d.invoice_id,
                                   COUNT(*) as devices_count,
                                   BOOL_OR(COALESCE(d.is_archived, FALSE)) as is_device_archived,
                                   MAX(d.id) as device_id,
                                   MAX(d.category || ' ' || d.model) as device_name,
                                   MAX(d.imei_serial) as device_imei
                            FROM devices d
                            WHERE COALESCE(d.is_deleted, FALSE) = FALSE
                            GROUP BY d.invoice_id
                        ) d_agg ON d_agg.invoice_id = i.id
                        WHERE (
                            i.total_amount > 0 
                            OR COALESCE(i.supplier_credit, 0.00) > 0 
                            OR COALESCE(i.paid_amount, 0.00) > 0 
                            OR COALESCE(d_agg.devices_count, 0) > 0
                            OR EXISTS (SELECT 1 FROM supplier_payments sp WHERE sp.invoice_id = i.id)
                        )
                    """
                    params = []
                    if supplier_id is not None:
                        s_id_int = _clean_int_id(supplier_id)
                        if s_id_int is not None:
                            query += " AND i.supplier_id = %s"
                            params.append(s_id_int)

                    if unpaid_only or status_filter == 'UNPAID':
                        query += " AND i.remaining_amount > 0"
                    elif status_filter == 'PAID':
                        query += " AND i.remaining_amount <= 0"

                    if archived_only:
                        query += " AND EXISTS (SELECT 1 FROM devices d WHERE d.invoice_id = i.id AND COALESCE(d.is_archived, FALSE) = TRUE)"
                    elif not include_archived:
                        query += " AND NOT EXISTS (SELECT 1 FROM devices d WHERE d.invoice_id = i.id AND COALESCE(d.is_archived, FALSE) = TRUE)"

                    if date_from and str(date_from).strip():
                        query += " AND i.invoice_date >= %s::date"
                        params.append(str(date_from).strip())

                    if date_to and str(date_to).strip():
                        query += " AND i.invoice_date <= %s::date"
                        params.append(str(date_to).strip())

                    if search_query:
                        q_str = str(search_query).strip()
                        q_clean = q_str.lstrip('#')
                        if search_by == 'ID':
                            query += " AND CAST(i.id AS TEXT) = %s"
                            params.append(q_clean)
                        elif search_by == 'NAME':
                            query += " AND s.name ILIKE %s"
                            params.append(f"%{q_str}%")
                        elif search_by == 'DATE':
                            query += " AND TO_CHAR(i.invoice_date, 'YYYY-MM-DD') ILIKE %s"
                            params.append(f"%{q_str}%")
                        else:
                            query += """
                                AND (s.name ILIKE %s OR CAST(i.id AS TEXT) = %s 
                                     OR TO_CHAR(i.invoice_date, 'YYYY-MM-DD') ILIKE %s
                                     OR EXISTS (SELECT 1 FROM devices d WHERE d.invoice_id = i.id AND (d.model ILIKE %s OR d.imei_serial ILIKE %s OR CAST(d.id AS TEXT) = %s)))
                            """
                            params.extend([f"%{q_str}%", q_clean, f"%{q_str}%", f"%{q_str}%", f"%{q_str}%", q_clean])

                    query += " ORDER BY i.id DESC;"
                    cur.execute(query, params)
                    rows = cur.fetchall()
                    for r in rows:
                        r['invoice_code'] = f"INV-BUY-{r['id']:05d}"
                    return rows
        except Exception:
            return []

    def get_supplier_invoice_payments(self, invoice_id):
        inv_id = _clean_int_id(invoice_id)
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT sp.id, sp.payment_amount, sp.payment_amount as amount,
                               COALESCE(sp.notes, '') as notes,
                               TO_CHAR(sp.payment_date, 'YYYY-MM-DD HH24:MI') as payment_date_formatted,
                               TO_CHAR(sp.payment_date, 'YYYY-MM-DD HH24:MI') as payment_date_fmt,
                               COALESCE(u.full_name, u.username, 'مستخدم النظام') as user_name,
                               COALESCE(u.full_name, u.username, 'مستخدم النظام') as paid_by_name,
                               COALESCE(u.full_name, u.username, 'مستخدم النظام') as payer_name
                        FROM supplier_payments sp
                        LEFT JOIN users u ON sp.created_by_user_id = u.id
                        WHERE sp.invoice_id = %s
                        ORDER BY sp.id ASC;
                    """, (inv_id,))
                    return cur.fetchall()
        except Exception:
            return []

    def get_supplier_payments_history(self, invoice_id):
        return self.get_supplier_invoice_payments(invoice_id)

    def get_invoice_devices(self, invoice_id):
        inv_id = _clean_int_id(invoice_id)
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT d.id, d.category, d.model, COALESCE(d.storage, '-') as storage,
                               COALESCE(d.ram, '') as ram,
                               d.battery_health,
                               d.imei_serial, d.buy_price,
                               COALESCE(d.is_sold, FALSE) as is_sold,
                               COALESCE(d.is_archived, FALSE) as is_archived,
                               COALESCE(d.device_condition, 'مستعمل') as device_condition,
                               COALESCE(d.device_condition, 'مستعمل') as condition,
                               COALESCE(d.has_box, FALSE) as has_box,
                               COALESCE(d.has_box, FALSE) as with_box,
                               COALESCE(NULLIF(d.color, 'بدون'), 'أسود') as color,
                               COALESCE(d.has_tax, FALSE) as has_tax,
                               COALESCE(d.accessories, '') as accessories,
                               COALESCE(d.notes, '') as notes,
                               CASE 
                                   WHEN d.is_archived THEN 'ARCHIVED'
                                   WHEN d.is_sold THEN 'SOLD' 
                                   ELSE 'IN_STOCK' 
                               END as status
                        FROM devices d
                        WHERE d.invoice_id = %s AND COALESCE(d.is_deleted, FALSE) = FALSE
                        ORDER BY d.id DESC;
                    """, (inv_id,))
                    return cur.fetchall()
        except Exception:
            return []

    def get_devices_by_supplier_invoice(self, invoice_id):
        return self.get_invoice_devices(invoice_id)

    def get_devices_by_invoice(self, invoice_id):
        return self.get_invoice_devices(invoice_id)

    def get_supplier_invoice_full_details(self, invoice_id):
        inv_id = _clean_int_id(invoice_id)
        if not inv_id:
            return None
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT i.*, TO_CHAR(i.invoice_date, 'YYYY-MM-DD') as invoice_date_str,
                               COALESCE(s.name, 'غير محدد') as supplier_name,
                               COALESCE(s.phone, '-') as supplier_phone,
                               COALESCE(s.supplier_type, 'تاجر') as supplier_type,
                               COALESCE(u.full_name, u.username, 'مدير النظام') as creator_name
                        FROM supplier_invoices i
                        LEFT JOIN suppliers s ON i.supplier_id = s.id
                        LEFT JOIN users u ON i.created_by_user_id = u.id
                        WHERE i.id = %s;
                    """, (inv_id,))
                    inv = cur.fetchone()
                    if not inv:
                        return None
                    inv['devices'] = self.get_invoice_devices(inv_id)
                    inv['payments'] = self.get_supplier_invoice_payments(inv_id)
                    return inv
        except Exception:
            return None

    def pay_supplier_debt(self, invoice_id, amount, user_id, notes="", custom_date=None):
        inv_id = _clean_int_id(invoice_id)
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM supplier_invoices WHERE id = %s FOR UPDATE;", (inv_id,))
                inv = cur.fetchone()
                if not inv:
                    raise Exception("الفاتورة غير موجودة!")

                cur.execute("SELECT 1 FROM devices WHERE invoice_id = %s AND COALESCE(is_archived, FALSE) = TRUE;", (inv_id,))
                if cur.fetchone():
                    raise Exception("هذه الفاتورة تابعة لجهاز مؤرشف ومقفل تماماً، لا يمكن تسجيل أي سداد مالي لها!")

                rem = float(inv['remaining_amount'] or 0.0)
                if rem <= 0.00:
                    raise Exception("هذه الفاتورة مسددة بالكامل ولا توجد أي مديونية متبقية عليها للسداد! (المتبقي: 0.00 ج.م)")

                pay_amt = float(amount or 0.0)
                if pay_amt <= 0:
                    raise Exception("يرجى إدخال مبلغ سداد صحيح أكبر من الصفر!")

                old_credit = float(inv.get('supplier_credit') or 0.0)
                excess = max(0.0, pay_amt - rem)
                new_paid = float(inv['paid_amount'] or 0.0) + pay_amt
                new_rem = max(0.0, rem - pay_amt)
                new_credit = old_credit + excess
                status = 'PAID' if new_rem <= 0 else 'UNPAID'

                c_date = custom_date.strip() if (custom_date and str(custom_date).strip()) else None
                cur.execute("""
                    UPDATE supplier_invoices 
                    SET paid_amount = %s, remaining_amount = %s, supplier_credit = %s, status = %s 
                    WHERE id = %s;
                """, (new_paid, new_rem, new_credit, status, inv_id))

                note_msg = notes or ('سداد دفعة من الفاتورة' + (f" (مع تحويل فائض {excess:,.2f} ج.م كرصيد دائن)" if excess > 0 else ""))
                if c_date:
                    cur.execute("""
                        INSERT INTO supplier_payments (invoice_id, supplier_id, payment_amount, notes, created_by_user_id, payment_date)
                        VALUES (%s, %s, %s, %s, %s, %s::timestamp);
                    """, (inv_id, inv['supplier_id'], pay_amt, note_msg, _clean_int_id(user_id), c_date))
                else:
                    cur.execute("""
                        INSERT INTO supplier_payments (invoice_id, supplier_id, payment_amount, notes, created_by_user_id)
                        VALUES (%s, %s, %s, %s, %s);
                    """, (inv_id, inv['supplier_id'], pay_amt, note_msg, _clean_int_id(user_id)))

                conn.commit()

        self.add_audit_log(
            user_id=user_id,
            user_name=None,
            action_type="PAY_SUPPLIER",
            entity_type="SUPPLIER_INVOICE",
            entity_id=inv_id,
            description=f"سداد دفعة للمورد بمبلغ {pay_amt:,.2f} ج.م للفاتورة #{inv_id} (متبقي جديد: {new_rem:,.2f} ج.م، رصيد دائن جديد: {new_credit:,.2f} ج.م)" + (f" [تاريخ: {c_date}]" if c_date else ""),
            old_values={"remaining_amount": rem, "supplier_credit": old_credit},
            new_values={"paid_now": pay_amt, "new_remaining": new_rem, "supplier_credit": new_credit}
        )

    def add_capital_transaction(self, amount, transaction_type='INJECTION', notes='', user_id=None, custom_date=None):
        t_up = str(transaction_type).upper()
        tx_type = 'WITHDRAWAL' if t_up in ('WITHDRAWAL', 'WITHDRAW') else 'INJECTION'
        c_date = custom_date.strip() if (custom_date and str(custom_date).strip()) else None
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                if c_date:
                    cur.execute("""
                        INSERT INTO capital_transactions (amount, transaction_type, notes, created_by_user_id, created_at)
                        VALUES (%s, %s, %s, %s, %s::timestamp) RETURNING id;
                    """, (amount, tx_type, notes or ('إضافة سيولة نقدية' if tx_type == 'INJECTION' else 'حركة سحب ومصروف'), _clean_int_id(user_id), c_date))
                else:
                    cur.execute("""
                        INSERT INTO capital_transactions (amount, transaction_type, notes, created_by_user_id)
                        VALUES (%s, %s, %s, %s) RETURNING id;
                    """, (amount, tx_type, notes or ('إضافة سيولة نقدية' if tx_type == 'INJECTION' else 'حركة سحب ومصروف'), _clean_int_id(user_id)))
                tx_id = cur.fetchone()['id']
                conn.commit()

        self.add_audit_log(
            user_id=user_id,
            user_name=None,
            action_type="CAPITAL_INJECTION" if tx_type == 'INJECTION' else "CAPITAL_WITHDRAWAL",
            entity_type="CAPITAL",
            entity_id=tx_id,
            description=f"{'إضافة وتغذية سيولة نقدية' if tx_type == 'INJECTION' else 'تسجيل مصروف / سحب'}: {amount:,.2f} ج.م - {notes}" + (f" [تاريخ: {c_date}]" if c_date else ""),
            new_values={"amount": amount, "type": tx_type, "notes": notes}
        )
        return tx_id

    def get_capital_transactions(self, search_query=None, date_from=None, date_to=None):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT ct.id, ct.amount,
                               CASE 
                                   WHEN ct.transaction_type IN ('WITHDRAWAL', 'WITHDRAW') THEN 'WITHDRAW' 
                                   WHEN ct.transaction_type = 'SUPPLIER_REFUND' THEN 'SUPPLIER_REFUND'
                                   ELSE 'DEPOSIT' 
                               END as transaction_type,
                               COALESCE(ct.notes, 'تغذية سيولة مالية') as notes,
                               TO_CHAR(ct.created_at, 'YYYY-MM-DD HH24:MI') as created_at_formatted,
                               TO_CHAR(ct.created_at, 'YYYY-MM-DD HH24:MI') as created_at_fmt,
                               TO_CHAR(ct.created_at, 'YYYY-MM-DD HH24:MI') as date_formatted,
                               COALESCE(u.full_name, u.username, 'مستخدم النظام') as added_by_name,
                               COALESCE(u.full_name, u.username, 'مستخدم النظام') as created_by_name
                        FROM capital_transactions ct
                        LEFT JOIN users u ON ct.created_by_user_id = u.id
                        WHERE 1=1
                    """
                    params = []
                    if search_query and str(search_query).strip():
                        q = str(search_query).strip()
                        query += " AND (COALESCE(ct.notes, '') ILIKE %s OR COALESCE(u.full_name, '') ILIKE %s OR COALESCE(u.username, '') ILIKE %s OR CAST(ct.id AS TEXT) = %s OR TO_CHAR(ct.created_at, 'YYYY-MM-DD') ILIKE %s)"
                        params.extend([f"%{q}%", f"%{q}%", f"%{q}%", q.lstrip('#'), f"%{q}%"])
                    if date_from and str(date_from).strip():
                        query += " AND DATE(ct.created_at) >= %s::date"
                        params.append(str(date_from).strip())
                    if date_to and str(date_to).strip():
                        query += " AND DATE(ct.created_at) <= %s::date"
                        params.append(str(date_to).strip())
                    query += " ORDER BY ct.id DESC;"
                    cur.execute(query, params)
                    return cur.fetchall()
        except Exception as e:
            print(f"Error fetching capital transactions: {e}")
            return []

    def delete_capital_transaction(self, tx_id, user_id=None):
        t_id = _clean_int_id(tx_id)
        if t_id is None:
            raise Exception("رقم حركة السيولة غير صالح!")
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM capital_transactions WHERE id = %s;", (t_id,))
                tx = cur.fetchone()
                if not tx:
                    raise Exception("حركة السيولة غير موجودة أو تم حذفها مسبقاً!")
                cur.execute("DELETE FROM capital_transactions WHERE id = %s;", (t_id,))
                conn.commit()
        self.add_audit_log(
            user_id=user_id,
            user_name=None,
            action_type="DELETE_CAPITAL_TX",
            entity_type="CAPITAL",
            entity_id=t_id,
            description=f"حذف وتسوية حركة سيولة #{t_id} بقيمة {float(tx.get('amount') or 0):,.2f} ج.م ({tx.get('transaction_type')}) - البيان: {tx.get('notes') or '-'}",
            old_values=dict(tx)
        )

    # =========================================================================
    # حساب المركز المالي والسيولة - استبعاد الأجهزة المؤرشفة تماماً
    # =========================================================================
    def get_financial_summary(self):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # قيمة المخزون المتاح (فقط غير المباع وغير المحذوف وغير المؤرشف)
                    cur.execute("""
                        SELECT COUNT(*) as cnt, COALESCE(SUM(buy_price), 0) as inv_cost 
                        FROM devices 
                        WHERE COALESCE(is_sold, FALSE) = FALSE 
                          AND COALESCE(is_deleted, FALSE) = FALSE 
                          AND COALESCE(is_archived, FALSE) = FALSE;
                    """)
                    inv_row = cur.fetchone()
                    inv_cost = float(inv_row['inv_cost'] or 0)
                    avail_cnt = int(inv_row['cnt'] or 0)

                    # ديون العملاء النشطة (استبعاد الأجهزة المؤرشفة أو المحذوفة)
                    cur.execute("""
                        SELECT COALESCE(SUM(s.remaining_balance), 0) as cust_debts 
                        FROM sales s 
                        JOIN devices d ON s.device_id = d.id 
                        WHERE COALESCE(d.is_deleted, FALSE) = FALSE 
                          AND COALESCE(d.is_archived, FALSE) = FALSE;
                    """)
                    cust_debts = float(cur.fetchone()['cust_debts'])

                    # مديونيات الموردين النشطة (استبعاد فواتير الأجهزة المؤرشفة والمحذوفة التي ليس عليها التزام)
                    cur.execute("""
                        SELECT COALESCE(SUM(i.remaining_amount), 0) as supp_debts 
                        FROM supplier_invoices i
                        WHERE i.remaining_amount > 0
                          AND NOT EXISTS (SELECT 1 FROM devices d WHERE d.invoice_id = i.id AND (COALESCE(d.is_archived, FALSE) = TRUE OR COALESCE(d.is_deleted, FALSE) = TRUE));
                    """)
                    supp_debts = float(cur.fetchone()['supp_debts'])

                    # الأرصدة الدائنة للموردين النشطة (تحتسب حتى للأجهزة المحذوفة التي تم إبقاؤها كرصيد دائن لنا)
                    cur.execute("""
                        SELECT COALESCE(SUM(i.supplier_credit), 0) as supp_credit 
                        FROM supplier_invoices i
                        WHERE i.supplier_credit > 0
                          AND NOT EXISTS (SELECT 1 FROM devices d WHERE d.invoice_id = i.id AND COALESCE(d.is_archived, FALSE) = TRUE);
                    """)
                    supp_credit = float(cur.fetchone()['supp_credit'])

                    # مقبوضات المبيعات النشطة فقط
                    cur.execute("""
                        SELECT COALESCE(SUM(s.cash_received), 0) as total_sales_cash 
                        FROM sales s 
                        JOIN devices d ON s.device_id = d.id 
                        WHERE COALESCE(d.is_deleted, FALSE) = FALSE 
                          AND COALESCE(d.is_archived, FALSE) = FALSE;
                    """)
                    total_sales_cash = float(cur.fetchone()['total_sales_cash'])

                    # مدفوعات الموردين النشطة (تستبعد فقط إذا كان الجهاز مؤرشف، مع بقاء مدفوعات الفواتير التي بها رصيد دائن)
                    cur.execute("""
                        SELECT COALESCE(SUM(i.paid_amount), 0) as supp_payments 
                        FROM supplier_invoices i
                        WHERE NOT EXISTS (SELECT 1 FROM devices d WHERE d.invoice_id = i.id AND COALESCE(d.is_archived, FALSE) = TRUE);
                    """)
                    supp_payments = float(cur.fetchone()['supp_payments'])

                    # حركات السيولة المباشرة (رأس المال المضاف من الملاك فقط بدون مضاعفة الاستردادات)
                    cur.execute("SELECT COALESCE(SUM(amount), 0) as injections FROM capital_transactions WHERE COALESCE(transaction_type, 'INJECTION') IN ('INJECTION', 'DEPOSIT');")
                    injections = float(cur.fetchone()['injections'])

                    cur.execute("SELECT COALESCE(SUM(amount), 0) as withdrawals FROM capital_transactions WHERE transaction_type IN ('WITHDRAWAL', 'WITHDRAW');")
                    withdrawals = float(cur.fetchone()['withdrawals'])

                    # أرباح الشهر الحالي (للأجهزة النشطة فقط)
                    cur.execute("""
                        SELECT COALESCE(SUM(s.net_profit), 0) as m_profit 
                        FROM sales s 
                        JOIN devices d ON s.device_id = d.id
                        WHERE COALESCE(d.is_deleted, FALSE) = FALSE 
                          AND COALESCE(d.is_archived, FALSE) = FALSE 
                          AND TO_CHAR(s.sell_date, 'YYYY-MM') = TO_CHAR(CURRENT_DATE, 'YYYY-MM');
                    """)
                    m_profit = float(cur.fetchone()['m_profit'])

                    # إجمالي الأرباح النشطة
                    cur.execute("""
                        SELECT COALESCE(SUM(s.net_profit), 0) as tot_profit 
                        FROM sales s 
                        JOIN devices d ON s.device_id = d.id
                        WHERE COALESCE(d.is_deleted, FALSE) = FALSE 
                          AND COALESCE(d.is_archived, FALSE) = FALSE;
                    """)
                    tot_profit = float(cur.fetchone()['tot_profit'])

                    # مستحقات العهد والسلف والأمانات القائمة غير المستردة (بند الأصول القائمة)
                    cur.execute("""
                        SELECT COALESCE(SUM(remaining_amount), 0) as gen_assets
                        FROM general_financial_transactions
                        WHERE is_asset = TRUE AND status != 'FULLY_REFUNDED';
                    """)
                    total_general_assets = float(cur.fetchone()['gen_assets'])

                    # إجمالي المبالغ المنصرفة في المعاملات المالية العامة
                    cur.execute("SELECT COALESCE(SUM(amount), 0) as gen_disbursed FROM general_financial_transactions;")
                    total_gen_disbursed = float(cur.fetchone()['gen_disbursed'])

                    # إجمالي المبالغ المستردة نقداً من العهد والسلف
                    cur.execute("SELECT COALESCE(SUM(refund_amount), 0) as gen_refunded FROM general_transaction_refunds;")
                    total_gen_refunded = float(cur.fetchone()['gen_refunded'])

                    # المصروفات التشغيلية للشهر الحالي
                    cur.execute("""
                        SELECT COALESCE(SUM(amount), 0) as m_exp
                        FROM general_financial_transactions
                        WHERE is_asset = FALSE AND TO_CHAR(created_at, 'YYYY-MM') = TO_CHAR(CURRENT_DATE, 'YYYY-MM');
                    """)
                    month_operational_expenses = float(cur.fetchone()['m_exp'])

                    # إجمالي المصروفات التشغيلية الكلية
                    cur.execute("""
                        SELECT COALESCE(SUM(amount), 0) as tot_exp
                        FROM general_financial_transactions
                        WHERE is_asset = FALSE;
                    """)
                    total_operational_expenses = float(cur.fetchone()['tot_exp'])

                    net_injections = injections - withdrawals
                    current_liquidity = (net_injections + total_sales_cash + total_gen_refunded) - (supp_payments + total_gen_disbursed)
                    total_capital = (current_liquidity + inv_cost + cust_debts + supp_credit + total_general_assets) - supp_debts
                    net_monthly_profit = max(0.0, m_profit - month_operational_expenses)
                    net_total_profit = max(0.0, tot_profit - total_operational_expenses)

                    return {
                        'inventory_cost': inv_cost,
                        'inventory_value': inv_cost,
                        'total_inventory_cost': inv_cost,
                        'available_devices_count': avail_cnt,
                        'customer_debts': cust_debts,
                        'total_customer_debts': cust_debts,
                        'supplier_debts': supp_debts,
                        'total_supplier_debts': supp_debts,
                        'supplier_credit': supp_credit,
                        'total_supplier_credit': supp_credit,
                        'general_assets': total_general_assets,
                        'total_general_assets': total_general_assets,
                        'total_general_disbursed': total_gen_disbursed,
                        'total_general_refunded': total_gen_refunded,
                        'monthly_operational_expenses': month_operational_expenses,
                        'total_operational_expenses': total_operational_expenses,
                        'current_liquidity': current_liquidity,
                        'available_liquidity': current_liquidity,
                        'total_capital': total_capital,
                        'monthly_profit': net_monthly_profit,
                        'current_month_profit': net_monthly_profit,
                        'gross_monthly_profit': m_profit,
                        'total_profit': net_total_profit,
                        'total_injections': net_injections
                    }
        except Exception as e:
            print(f"Error financial summary: {e}")
            return {
                'inventory_cost': 0, 'inventory_value': 0, 'total_inventory_cost': 0,
                'available_devices_count': 0,
                'customer_debts': 0, 'total_customer_debts': 0,
                'supplier_debts': 0, 'total_supplier_debts': 0,
                'supplier_credit': 0, 'total_supplier_credit': 0,
                'current_liquidity': 0, 'available_liquidity': 0,
                'total_capital': 0, 'monthly_profit': 0, 'current_month_profit': 0,
                'total_profit': 0, 'total_injections': 0
            }

    # =========================================================================
    # تقرير المبيعات والأرباح - عزل تام للأجهزة المؤرشفة والمحذوفة
    # =========================================================================
    def get_sales_report(self, date_from=None, date_to=None, search_query=None, start_date=None, end_date=None, include_archived=False):
        df = date_from if date_from is not None else start_date
        dt = date_to if date_to is not None else end_date
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    arch_clause = "" if include_archived else "AND COALESCE(d.is_archived, FALSE) = FALSE"
                    query = f"""
                        SELECT s.id as sale_id, s.id as id, d.id as device_id, d.category, d.model,
                               d.storage, d.ram, d.battery_health, d.imei_serial, d.buy_price,
                               COALESCE(d.device_condition, 'مستعمل') as device_condition,
                               COALESCE(d.device_condition, 'مستعمل') as condition,
                               COALESCE(d.has_box, FALSE) as has_box,
                               COALESCE(d.has_box, FALSE) as with_box,
                               COALESCE(NULLIF(d.color, 'بدون'), 'أسود') as color,
                               COALESCE(d.has_tax, FALSE) as has_tax,
                               COALESCE(d.accessories, '') as accessories,
                               COALESCE(d.is_archived, FALSE) as is_archived,
                               s.sell_price, s.sell_price as final_sell_price,
                               s.cash_received, s.remaining_balance,
                               s.net_profit, s.net_profit as profit,
                               s.customer_name, COALESCE(s.customer_phone, '') as customer_phone,
                               COALESCE(s.notes, '') as sale_notes,
                               TO_CHAR(s.sell_date, 'YYYY-MM-DD HH24:MI') as sell_date_formatted,
                               COALESCE(u.full_name, u.username, 'بائع النظام') as seller_name
                        FROM sales s
                        JOIN devices d ON s.device_id = d.id
                        LEFT JOIN users u ON s.created_by_user_id = u.id
                        WHERE COALESCE(d.is_deleted, FALSE) = FALSE {arch_clause}
                    """
                    params = []
                    if df and str(df).strip():
                        query += " AND DATE(s.sell_date) >= %s::date"
                        params.append(str(df).strip())
                    if dt and str(dt).strip():
                        query += " AND DATE(s.sell_date) <= %s::date"
                        params.append(str(dt).strip())
                    if search_query and str(search_query).strip():
                        q = str(search_query).strip()
                        query += " AND (d.model ILIKE %s OR d.category ILIKE %s OR d.imei_serial ILIKE %s OR s.customer_name ILIKE %s OR COALESCE(u.full_name, '') ILIKE %s OR CAST(s.id AS TEXT) = %s)"
                        params.extend([f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", q.lstrip('#')])
                    query += " ORDER BY s.id DESC;"
                    cur.execute(query, params)
                    raw_rows = cur.fetchall()
                    rows = []
                    for r in raw_rows:
                        item = dict(r)
                        s_id = item.get('sale_id') or item.get('id') or 0
                        item['id'] = s_id
                        item['sale_id'] = s_id
                        rem = float(item.get('remaining_balance') or 0)
                        item['invoice_code'] = f"INV-SALE-{s_id:05d}" if rem <= 0 else f"INV-DEBT-{s_id:05d}"
                        rows.append(item)
                    return rows
        except Exception as e:
            print(f"Sales report error: {e}")
            return []

    def get_profit_report(self, date_from=None, date_to=None, search_query=None):
        sales = self.get_sales_report(date_from=date_from, date_to=date_to, search_query=search_query, include_archived=False)
        total_sales_val = sum(float(s.get('sell_price') or 0) for s in sales)
        total_cost_val = sum(float(s.get('buy_price') or 0) for s in sales)
        total_profit_val = sum(float(s.get('net_profit') or 0) for s in sales)
        total_discount_val = sum(float(s.get('discount') or 0) for s in sales)
        margin_pct = (total_profit_val / total_cost_val * 100) if total_cost_val > 0 else 0.0

        return {
            'sales': sales,
            'summary': {
                'sales_count': len(sales),
                'total_sales_value': total_sales_val,
                'total_cost_value': total_cost_val,
                'total_net_profit': total_profit_val,
                'total_discount': total_discount_val,
                'profit_margin_pct': margin_pct
            }
        }

    def get_supplier_comprehensive_period_report(self, supplier_id, date_from=None, date_to=None):
        s_id = _clean_int_id(supplier_id)
        if not s_id:
            raise Exception("يرجى اختيار المورد أولاً!")

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM suppliers WHERE id = %s;", (s_id,))
                supp = cur.fetchone()
                if not supp:
                    raise Exception("المورد غير موجود!")

                date_filter_sql = ""
                params = [s_id]
                if date_from and str(date_from).strip():
                    date_filter_sql += " AND i.invoice_date >= %s::date"
                    params.append(str(date_from).strip())
                if date_to and str(date_to).strip():
                    date_filter_sql += " AND i.invoice_date <= %s::date"
                    params.append(str(date_to).strip())

                cur.execute(f"""
                    SELECT i.id as invoice_id, i.total_amount, i.paid_amount, i.remaining_amount,
                           COALESCE(i.supplier_credit, 0.00) as supplier_credit,
                           TO_CHAR(i.invoice_date, 'YYYY-MM-DD') as invoice_date_formatted,
                           i.status, COALESCE(i.notes, '') as invoice_notes,
                           d.id as device_id, d.category, d.model, d.storage, d.ram, d.imei_serial,
                           d.buy_price, COALESCE(d.device_condition, 'مستعمل') as device_condition,
                           COALESCE(d.color, 'أسود') as color, COALESCE(d.has_box, FALSE) as has_box,
                           COALESCE(d.has_tax, FALSE) as has_tax, COALESCE(d.battery_health, 100) as battery_health,
                           COALESCE(d.accessories, '') as accessories,
                           COALESCE(d.notes, '') as device_notes,
                           COALESCE(d.is_sold, FALSE) as is_sold,
                           COALESCE(d.is_archived, FALSE) as is_archived
                    FROM supplier_invoices i
                    JOIN devices d ON d.invoice_id = i.id
                    WHERE i.supplier_id = %s 
                      AND COALESCE(i.status, '') != 'CANCELLED'
                      AND COALESCE(d.is_deleted, FALSE) = FALSE
                      AND COALESCE(d.is_archived, FALSE) = FALSE
                      {date_filter_sql}
                    ORDER BY i.invoice_date DESC, i.id DESC;
                """, params)
                invoices_devices = cur.fetchall()

                tot_purchases = sum(float(x.get('total_amount') or 0) for x in invoices_devices if not x.get('is_archived'))
                tot_paid = sum(float(x.get('paid_amount') or 0) for x in invoices_devices if not x.get('is_archived'))
                tot_remaining = sum(float(x.get('remaining_amount') or 0) for x in invoices_devices if not x.get('is_archived'))
                tot_credit = sum(float(x.get('supplier_credit') or 0) for x in invoices_devices if not x.get('is_archived'))

                pay_params = [s_id]
                pay_date_sql = ""
                if date_from and str(date_from).strip():
                    pay_date_sql += " AND DATE(sp.payment_date) >= %s::date"
                    pay_params.append(str(date_from).strip())
                if date_to and str(date_to).strip():
                    pay_date_sql += " AND DATE(sp.payment_date) <= %s::date"
                    pay_params.append(str(date_to).strip())

                cur.execute(f"""
                    SELECT sp.id, sp.invoice_id, sp.payment_amount,
                           COALESCE(sp.notes, '') as notes,
                           TO_CHAR(sp.payment_date, 'YYYY-MM-DD HH24:MI') as payment_date_formatted,
                           COALESCE(u.full_name, u.username, 'مستخدم') as paid_by_name
                    FROM supplier_payments sp
                    LEFT JOIN supplier_invoices i ON sp.invoice_id = i.id
                    LEFT JOIN devices d ON d.invoice_id = i.id
                    LEFT JOIN users u ON sp.created_by_user_id = u.id
                    WHERE sp.supplier_id = %s 
                      AND (i.id IS NULL OR COALESCE(i.status, '') != 'CANCELLED')
                      AND (d.id IS NULL OR (COALESCE(d.is_deleted, FALSE) = FALSE AND COALESCE(d.is_archived, FALSE) = FALSE))
                      {pay_date_sql}
                    ORDER BY sp.payment_date DESC, sp.id DESC;
                """, pay_params)
                payments_history = cur.fetchall()
                total_payments_in_period = sum(float(p.get('payment_amount') or 0) for p in payments_history)

                cur.execute("""
                    SELECT COALESCE(SUM(remaining_amount), 0) as all_rem,
                           COALESCE(SUM(supplier_credit), 0) as all_cred
                    FROM supplier_invoices i
                    WHERE i.supplier_id = %s
                      AND COALESCE(i.status, '') != 'CANCELLED'
                      AND NOT EXISTS (
                          SELECT 1 FROM devices d 
                          WHERE d.invoice_id = i.id 
                          AND (COALESCE(d.is_deleted, FALSE) = TRUE OR COALESCE(d.is_archived, FALSE) = TRUE)
                      );
                """, (s_id,))
                all_stat = cur.fetchone()

                return {
                    'supplier': dict(supp),
                    'period': {'date_from': date_from, 'date_to': date_to},
                    'summary': {
                        'devices_count': len([x for x in invoices_devices if x.get('device_id')]),
                        'invoices_count': len(invoices_devices),
                        'total_purchases_amount': tot_purchases,
                        'total_paid_invoices': tot_paid,
                        'total_remaining_debt': tot_remaining,
                        'total_supplier_credit': tot_credit,
                        'payments_in_period_sum': total_payments_in_period,
                        'net_period_change': tot_purchases - total_payments_in_period,
                        'all_time_remaining_debt': float(all_stat['all_rem'] or 0),
                        'all_time_supplier_credit': float(all_stat['all_cred'] or 0)
                    },
                    'devices_invoices': invoices_devices,
                    'payments': payments_history
                }

    def get_device_full_details(self, device_id):
        try:
            dev_id = _clean_int_id(device_id)
            if dev_id is None:
                return None

            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT d.*,
                               COALESCE(d.device_condition, 'مستعمل') as device_condition,
                               COALESCE(d.has_box, FALSE) as has_box,
                               COALESCE(NULLIF(d.color, 'بدون'), 'أسود') as color,
                               COALESCE(d.has_tax, FALSE) as has_tax,
                               COALESCE(d.accessories, '') as accessories,
                               COALESCE(d.notes, '') as notes,
                               COALESCE(d.is_archived, FALSE) as is_archived,
                               TO_CHAR(d.archived_at, 'YYYY-MM-DD HH24:MI') as archived_at_formatted,
                               COALESCE(s.name, 'غير محدد') as supplier_name,
                               COALESCE(s.supplier_type, 'تاجر') as supplier_type,
                               TO_CHAR(d.buy_date, 'YYYY-MM-DD HH24:MI') as buy_date_formatted,
                               COALESCE(u.full_name, u.username, 'مستخدم النظام') as created_by_name
                        FROM devices d
                        LEFT JOIN suppliers s ON d.supplier_id = s.id
                        LEFT JOIN users u ON d.created_by_user_id = u.id
                        WHERE d.id = %s;
                    """, (dev_id,))
                    dev = cur.fetchone()
                    if not dev:
                        return None

                    cur.execute("""
                        SELECT sl.*,
                               COALESCE(sl.notes, '') as notes,
                               TO_CHAR(sl.sell_date, 'YYYY-MM-DD HH24:MI') as sell_date_formatted,
                               COALESCE(u.full_name, u.username, 'بائع النظام') as seller_name,
                               CASE WHEN sl.remaining_balance <= 0 THEN 'مكتمل الدفع 🟢' ELSE 'غير مكتمل (آجل) 🔴' END as payment_status
                        FROM sales sl
                        LEFT JOIN users u ON sl.created_by_user_id = u.id
                        WHERE sl.device_id = %s;
                    """, (dev_id,))
                    sale = cur.fetchone()

                    payments = []
                    if sale:
                        cur.execute("""
                            SELECT cp.*, TO_CHAR(cp.payment_date, 'YYYY-MM-DD HH24:MI') as payment_date_formatted,
                                   COALESCE(u.full_name, u.username, 'مستلم النظام') as receiver_name
                            FROM customer_payments cp
                            LEFT JOIN users u ON cp.created_by_user_id = u.id
                            WHERE cp.sale_id = %s
                            ORDER BY cp.id ASC;
                        """, (sale['id'],))
                        payments = cur.fetchall()

                    return {
                        'device': dev,
                        'sale': sale,
                        'customer_payments': payments
                    }
        except Exception as e:
            print(f"Error fetching device full details: {e}")
            return None

    def get_sale_by_id(self, sale_id):
        s_id = _clean_int_id(sale_id)
        if not s_id:
            return None
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT s.*, 
                               d.category, d.model, d.storage, d.ram, d.battery_health,
                               d.imei_serial, d.buy_price, COALESCE(d.device_condition, 'مستعمل') as device_condition,
                               COALESCE(d.has_box, FALSE) as has_box,
                               COALESCE(NULLIF(d.color, 'بدون'), 'أسود') as color,
                               COALESCE(d.has_tax, FALSE) as has_tax,
                               COALESCE(d.accessories, '') as accessories,
                               COALESCE(d.is_archived, FALSE) as is_archived,
                               TO_CHAR(s.sell_date, 'YYYY-MM-DD HH24:MI') as sell_date_formatted,
                               COALESCE(u.full_name, u.username, 'بائع النظام') as seller_name
                        FROM sales s
                        JOIN devices d ON s.device_id = d.id
                        LEFT JOIN users u ON s.created_by_user_id = u.id
                        WHERE s.id = %s;
                    """, (s_id,))
                    row = cur.fetchone()
                    if not row:
                        return None
                    row_dict = dict(row)
                    row_dict['payments'] = self.get_customer_debt_payments(s_id)
                    rem = float(row_dict.get('remaining_balance') or 0)
                    row_dict['invoice_code'] = f"INV-SALE-{s_id:05d}" if rem <= 0 else f"INV-DEBT-{s_id:05d}"
                    return row_dict
        except Exception as ex:
            print(f"Error in get_sale_by_id: {ex}")
            return None

    def search_all_by_qr_or_code(self, query):
        q = str(query or "").strip()
        if not q:
            return None

        m_sale = re.search(r'(?:INV-)?SALE-(\d+)', q, re.I)
        if m_sale:
            sale_id = int(m_sale.group(1))
            sale_info = self.get_sale_by_id(sale_id)
            if sale_info:
                return {
                    'entity_type': 'SALE',
                    'title': f"فاتورة بيع #{sale_id}",
                    'id': sale_id,
                    'code': sale_info.get('invoice_code') or f"INV-SALE-{sale_id:05d}",
                    'data': sale_info
                }

        m_debt = re.search(r'(?:INV-)?DEBT-(\d+)', q, re.I)
        if m_debt:
            sale_id = int(m_debt.group(1))
            sale_info = self.get_sale_by_id(sale_id)
            if sale_info:
                return {
                    'entity_type': 'CUSTOMER_DEBT',
                    'title': f"مديونية عميل (خرج) #{sale_id}",
                    'id': sale_id,
                    'code': f"INV-DEBT-{sale_id:05d}",
                    'data': sale_info
                }

        m_buy = re.search(r'(?:INV-)?BUY-(\d+)|SUPP(?:-INV)?-(\d+)', q, re.I)
        if m_buy:
            inv_id = int(m_buy.group(1) or m_buy.group(2))
            inv_info = self.get_supplier_invoice_full_details(inv_id)
            if inv_info:
                return {
                    'entity_type': 'SUPPLIER_INVOICE',
                    'title': f"فاتورة شراء مورد #{inv_id}",
                    'id': inv_id,
                    'code': f"INV-BUY-{inv_id:05d}",
                    'data': inv_info
                }

        dev_by_serial = self.search_device_by_criteria(q, search_by='SERIAL', include_archived=True)
        if dev_by_serial:
            full_dev = self.get_device_full_details(dev_by_serial['id'])
            return {
                'entity_type': 'DEVICE',
                'title': f"جهاز بالسيريال: {dev_by_serial.get('category')} {dev_by_serial.get('model')}",
                'id': dev_by_serial['id'],
                'code': dev_by_serial.get('imei_serial') or f"DEV-{dev_by_serial['id']}",
                'data': full_dev or {'device': dev_by_serial}
            }

        clean_num = _clean_int_id(q)
        if clean_num:
            dev_obj = self.get_device_full_details(clean_num)
            if dev_obj and dev_obj.get('device'):
                d_rec = dev_obj['device']
                return {
                    'entity_type': 'DEVICE',
                    'title': f"جهاز #{clean_num} ({d_rec.get('category')} {d_rec.get('model')})",
                    'id': clean_num,
                    'code': d_rec.get('imei_serial') or f"DEV-{clean_num:05d}",
                    'data': dev_obj
                }

            s_obj = self.get_sale_by_id(clean_num)
            if s_obj:
                is_debt = float(s_obj.get('remaining_balance') or 0) > 0
                return {
                    'entity_type': 'CUSTOMER_DEBT' if is_debt else 'SALE',
                    'title': f"{'مديونية عميل' if is_debt else 'فاتورة بيع'} #{clean_num}",
                    'id': clean_num,
                    'code': s_obj.get('invoice_code') or (f"INV-DEBT-{clean_num:05d}" if is_debt else f"INV-SALE-{clean_num:05d}"),
                    'data': s_obj
                }

            supp_obj = self.get_supplier_invoice_full_details(clean_num)
            if supp_obj:
                return {
                    'entity_type': 'SUPPLIER_INVOICE',
                    'title': f"فاتورة شراء مورد #{clean_num}",
                    'id': clean_num,
                    'code': f"INV-BUY-{clean_num:05d}",
                    'data': supp_obj
                }

        return None

    # =========================================================================
    # المعاملات المالية العامة وتكامل الأصول ورأس المال
    # =========================================================================
    def get_financial_presets(self, preset_type=None):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    if preset_type:
                        cur.execute("""
                            SELECT preset_value 
                            FROM financial_presets 
                            WHERE preset_type = %s 
                            ORDER BY id ASC;
                        """, (preset_type,))
                    else:
                        cur.execute("""
                            SELECT preset_type, preset_value 
                            FROM financial_presets 
                            ORDER BY id ASC;
                        """)
                    rows = cur.fetchall()
                    if preset_type:
                        return [r['preset_value'] for r in rows]
                    return rows
        except Exception as ex:
            print(f"get_financial_presets error: {ex}")
            return []

    def save_financial_preset(self, preset_type, preset_value):
        clean_v = str(preset_value or '').strip()
        if not clean_v:
            return
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO financial_presets (preset_type, preset_value)
                        VALUES (%s, %s)
                        ON CONFLICT (preset_value) DO NOTHING;
                    """, (preset_type, clean_v))
                    conn.commit()
        except Exception as ex:
            print(f"save_financial_preset error: {ex}")

    def add_general_transaction(self, trans_type, recipient, category, amount, payment_method='كاش', notes='', user_id=None, custom_date=None):
        rec_clean = str(recipient or '').strip()
        cat_clean = str(category or '').strip()
        if not rec_clean or not cat_clean:
            raise Exception("يجب تحديد المستلم والبيان / الغرض بشكل صحيح!")

        try:
            amt = float(amount or 0)
        except ValueError:
            amt = 0.0

        if amt <= 0:
            raise Exception("يرجى إدخال مبلغ صحيح أكبر من الصفر!")

        t_type = str(trans_type or 'OPERATIONAL_EXP').upper()
        # تصنيف الأصول: العهد والسلف والتحويلات والأمانات تُعد أصلاً ومستحقاً قائماً
        is_asset = t_type in ('CUSTODY', 'ADVANCE', 'TRANSFER', 'SECURITY_DEPOSIT', 'DEPOSIT')
        rem_amount = amt if is_asset else 0.00
        pay_method = str(payment_method or 'كاش').strip() or 'كاش'
        c_date = custom_date.strip() if (custom_date and str(custom_date).strip()) else None

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                if c_date:
                    cur.execute("""
                        INSERT INTO general_financial_transactions (
                            trans_type, is_asset, recipient, category, amount,
                            paid_back_amount, remaining_amount, status,
                            payment_method, notes, user_id, created_at, updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, 0.00, %s, 'OPEN', %s, %s, %s, %s::timestamp, %s::timestamp)
                        RETURNING id;
                    """, (t_type, is_asset, rec_clean, cat_clean, amt, rem_amount, pay_method, notes or '', _clean_int_id(user_id), c_date, c_date))
                else:
                    cur.execute("""
                        INSERT INTO general_financial_transactions (
                            trans_type, is_asset, recipient, category, amount,
                            paid_back_amount, remaining_amount, status,
                            payment_method, notes, user_id
                        )
                        VALUES (%s, %s, %s, %s, %s, 0.00, %s, 'OPEN', %s, %s, %s)
                        RETURNING id;
                    """, (t_type, is_asset, rec_clean, cat_clean, amt, rem_amount, pay_method, notes or '', _clean_int_id(user_id)))

                tx_id = cur.fetchone()['id']
                conn.commit()

        # حفظ القوالب تلقائياً لسرعة الإكمال التلقائي في المرات القادمة
        self.save_financial_preset('RECIPIENT', rec_clean)
        self.save_financial_preset('CATEGORY', cat_clean)

        trans_type_names = {
            'CUSTODY': 'عهدة لقسم أو شخص',
            'ADVANCE': 'سلفة موظف',
            'TRANSFER': 'تحويل بين الخزائن',
            'SECURITY_DEPOSIT': 'أمانة معلقة طرف الغير',
            'DEPOSIT': 'أمانة معلقة',
            'OPERATIONAL_EXP': 'مصروف تشغيلي نهائي'
        }
        ar_type = trans_type_names.get(t_type, t_type)

        self.add_audit_log(
            user_id=user_id,
            user_name=None,
            action_type="GENERAL_TRANSACTION_CREATE",
            entity_type="GENERAL_TRANSACTION",
            entity_id=tx_id,
            description=f"تسجيل معاملة مالية عامة ({ar_type}) بمبلغ {amt:,.2f} ج.م [طريقة الدفع: {pay_method}] - المستلم: {rec_clean} - البيان: {cat_clean}" + (f" [تاريخ: {c_date}]" if c_date else ""),
            old_values=None,
            new_values={
                'trans_type': t_type,
                'is_asset': is_asset,
                'recipient': rec_clean,
                'category': cat_clean,
                'amount': amt,
                'payment_method': pay_method,
                'notes': notes,
                'remaining_amount': rem_amount
            }
        )
        return tx_id

    def refund_general_transaction(self, transaction_id, refund_amount, payment_method='كاش', notes='', user_id=None, custom_date=None):
        tx_id = _clean_int_id(transaction_id)
        if not tx_id:
            raise Exception("رقم المعاملة غير صالح!")

        try:
            ref_amt = float(refund_amount or 0)
        except ValueError:
            ref_amt = 0.0

        if ref_amt <= 0:
            raise Exception("يرجى إدخال مبلغ استرداد صحيح أكبر من الصفر!")

        pay_method = str(payment_method or 'كاش').strip() or 'كاش'
        c_date = custom_date.strip() if (custom_date and str(custom_date).strip()) else None

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM general_financial_transactions 
                    WHERE id = %s 
                    FOR UPDATE;
                """, (tx_id,))
                tx = cur.fetchone()
                if not tx:
                    raise Exception("المعاملة المالية غير موجودة!")

                if not tx.get('is_asset'):
                    raise Exception("هذه المعاملة تم تسجيلها كمصروف نهائي مستهلك ولا تقبل الاسترداد!")

                rem = float(tx.get('remaining_amount') or 0)
                if rem <= 0.01:
                    raise Exception("تم استرداد كامل مبلغ هذه العهدة / السلفة مسبقاً!")

                if ref_amt > (rem + 0.01):
                    raise Exception(f"مبلغ الاسترداد المطلوب ({ref_amt:,.2f} ج.م) أكبر من المتبقي القائم ({rem:,.2f} ج.م)!")

                curr_paid_back = float(tx.get('paid_back_amount') or 0)
                tot_amount = float(tx.get('amount') or 0)
                new_paid_back = curr_paid_back + ref_amt
                new_rem = max(0.0, tot_amount - new_paid_back)
                new_status = 'FULLY_REFUNDED' if new_rem <= 0.01 else 'PARTIALLY_REFUNDED'

                cur.execute("""
                    UPDATE general_financial_transactions
                    SET paid_back_amount = %s, remaining_amount = %s, status = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s;
                """, (new_paid_back, new_rem, new_status, tx_id))

                if c_date:
                    cur.execute("""
                        INSERT INTO general_transaction_refunds (
                            transaction_id, refund_amount, payment_method, notes, user_id, created_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s::timestamp)
                        RETURNING id;
                    """, (tx_id, ref_amt, pay_method, notes or '', _clean_int_id(user_id), c_date))
                else:
                    cur.execute("""
                        INSERT INTO general_transaction_refunds (
                            transaction_id, refund_amount, payment_method, notes, user_id
                        )
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id;
                    """, (tx_id, ref_amt, pay_method, notes or '', _clean_int_id(user_id)))

                rf_id = cur.fetchone()['id']
                conn.commit()

        self.add_audit_log(
            user_id=user_id,
            user_name=None,
            action_type="GENERAL_TRANSACTION_REFUND",
            entity_type="GENERAL_TRANSACTION",
            entity_id=tx_id,
            description=f"استرداد مبلغ {ref_amt:,.2f} ج.م نقداً من المعاملة #{tx_id} [المستلم: {tx.get('recipient')} - الغرض: {tx.get('category')}] (طريقة الاستلام: {pay_method}) - المتبقي: {new_rem:,.2f} ج.م" + (f" [تاريخ: {c_date}]" if c_date else ""),
            old_values={'remaining_amount': rem, 'paid_back_amount': curr_paid_back, 'status': tx.get('status')},
            new_values={'refund_id': rf_id, 'refund_amount': ref_amt, 'new_remaining': new_rem, 'new_status': new_status, 'payment_method': pay_method}
        )
        return rf_id

    def get_general_transactions(self, trans_type=None, is_asset=None, status=None, search_query=None, date_from=None, date_to=None, limit=500):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT g.*,
                               TO_CHAR(g.created_at, 'YYYY-MM-DD HH24:MI') as date_formatted,
                               COALESCE(u.full_name, u.username, 'مستخدم النظام') as user_name,
                               COALESCE(g.remaining_amount, g.amount - COALESCE(g.paid_back_amount, 0)) as calculated_remaining
                        FROM general_financial_transactions g
                        LEFT JOIN users u ON g.user_id = u.id
                        WHERE 1=1
                    """
                    params = []

                    if trans_type and trans_type != 'ALL':
                        query += " AND g.trans_type = %s"
                        params.append(trans_type)

                    if is_asset is not None:
                        query += " AND g.is_asset = %s"
                        params.append(bool(is_asset))

                    if status and status != 'ALL':
                        query += " AND g.status = %s"
                        params.append(status)

                    if date_from and str(date_from).strip():
                        query += " AND DATE(g.created_at) >= %s::date"
                        params.append(str(date_from).strip())

                    if date_to and str(date_to).strip():
                        query += " AND DATE(g.created_at) <= %s::date"
                        params.append(str(date_to).strip())

                    if search_query and str(search_query).strip():
                        q = str(search_query).strip()
                        query += " AND (g.recipient ILIKE %s OR g.category ILIKE %s OR COALESCE(g.notes, '') ILIKE %s OR CAST(g.id AS TEXT) = %s OR COALESCE(u.full_name, '') ILIKE %s)"
                        params.extend([f"%{q}%", f"%{q}%", f"%{q}%", q.lstrip('#'), f"%{q}%"])

                    query += " ORDER BY g.created_at DESC, g.id DESC LIMIT %s;"
                    params.append(limit)

                    cur.execute(query, params)
                    return cur.fetchall()
        except Exception as ex:
            print(f"get_general_transactions error: {ex}")
            return []

    def get_general_transaction_refunds(self, transaction_id):
        tx_id = _clean_int_id(transaction_id)
        if not tx_id:
            return []
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT r.*,
                               TO_CHAR(r.created_at, 'YYYY-MM-DD HH24:MI') as date_formatted,
                               COALESCE(u.full_name, u.username, 'مستخدم النظام') as user_name
                        FROM general_transaction_refunds r
                        LEFT JOIN users u ON r.user_id = u.id
                        WHERE r.transaction_id = %s
                        ORDER BY r.created_at ASC, r.id ASC;
                    """, (tx_id,))
                    return cur.fetchall()
        except Exception as ex:
            print(f"get_general_transaction_refunds error: {ex}")
            return []

