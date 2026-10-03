import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt
import json
import os
import re

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
    """استخراج الرقم الصحيح بأمان من أي قيمة ID حتى مع وجود رموز اتجاه النص أو #."""
    if val is None:
        return None
    if isinstance(val, int):
        return val
    s = str(val).replace('\u200f', '').replace('\u200e', '').replace('#', '').strip()
    if s.isdigit():
        return int(s)
    m = re.search(r'\d+', s)
    return int(m.group(0)) if m else None


class DatabaseManager:
    def __init__(self):
        self.conn_params = load_db_config()
        self.ensure_tables_exist()

    def get_connection(self):
        try:
            return psycopg2.connect(**self.conn_params, cursor_factory=RealDictCursor)
        except Exception as e:
            raise Exception(f"فشل الاتصال بقاعدة البيانات: {e}")

    def ensure_tables_exist(self):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # 1. جدول المستخدمين والصلاحيات التفصيلية
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
                            status VARCHAR(20) DEFAULT 'UNPAID',
                            invoice_date DATE DEFAULT CURRENT_DATE,
                            created_by_user_id INT REFERENCES users(id),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    cur.execute("ALTER TABLE supplier_invoices ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'UNPAID';")
                    cur.execute("ALTER TABLE supplier_invoices ADD COLUMN IF NOT EXISTS created_by_user_id INT REFERENCES users(id);")

                    # 4. جدول الأجهزة
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
                    """)
                    cur.execute("ALTER TABLE devices ADD COLUMN IF NOT EXISTS storage VARCHAR(50);")
                    cur.execute("ALTER TABLE devices ADD COLUMN IF NOT EXISTS ram VARCHAR(50) DEFAULT 'لا يوجد';")
                    cur.execute("ALTER TABLE devices ADD COLUMN IF NOT EXISTS battery_health INT DEFAULT 0;")
                    cur.execute("ALTER TABLE devices ADD COLUMN IF NOT EXISTS accessories TEXT;")
                    cur.execute("ALTER TABLE devices ADD COLUMN IF NOT EXISTS device_condition VARCHAR(20) DEFAULT 'مستعمل';")
                    cur.execute("ALTER TABLE devices ADD COLUMN IF NOT EXISTS has_box BOOLEAN DEFAULT TRUE;")
                    cur.execute("ALTER TABLE devices ADD COLUMN IF NOT EXISTS invoice_id INT REFERENCES supplier_invoices(id);")
                    cur.execute("ALTER TABLE devices ADD COLUMN IF NOT EXISTS notes TEXT;")
                    cur.execute("ALTER TABLE devices ADD COLUMN IF NOT EXISTS is_sold BOOLEAN DEFAULT FALSE;")
                    cur.execute("ALTER TABLE devices ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;")
                    cur.execute("ALTER TABLE devices ADD COLUMN IF NOT EXISTS created_by_user_id INT REFERENCES users(id);")

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
                    cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS cash_received NUMERIC(12, 2) DEFAULT 0.00;")
                    cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS remaining_balance NUMERIC(12, 2) DEFAULT 0.00;")
                    cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS net_profit NUMERIC(12, 2) DEFAULT 0.00;")
                    cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS notes TEXT;")
                    cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS sell_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
                    cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS created_by_user_id INT REFERENCES users(id);")

                    cur.execute("""
                        DO $$
                        BEGIN
                            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='sales' AND column_name='original_price') THEN
                                ALTER TABLE sales ALTER COLUMN original_price DROP NOT NULL;
                                ALTER TABLE sales ALTER COLUMN original_price SET DEFAULT 0.00;
                            END IF;
                            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='sales' AND column_name='discount') THEN
                                ALTER TABLE sales ALTER COLUMN discount DROP NOT NULL;
                                ALTER TABLE sales ALTER COLUMN discount SET DEFAULT 0.00;
                            END IF;
                        END $$;
                    """)

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

                    # 7. جدول دفعات الموردين (الأقساط)
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
                            transaction_type VARCHAR(20) NOT NULL DEFAULT 'INJECTION',
                            notes TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            created_by_user_id INT REFERENCES users(id)
                        );
                    """)
                    cur.execute("ALTER TABLE capital_transactions ADD COLUMN IF NOT EXISTS transaction_type VARCHAR(20) DEFAULT 'INJECTION';")
                    cur.execute("ALTER TABLE capital_transactions ADD COLUMN IF NOT EXISTS notes TEXT;")
                    cur.execute("ALTER TABLE capital_transactions ADD COLUMN IF NOT EXISTS created_by_user_id INT REFERENCES users(id);")

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

                    # إنشاء مستخدم admin افتراضي بكامل الصلاحيات إذا كان جدول المستخدمين فارغاً
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
                        json.dumps(old_values or {}),
                        json.dumps(new_values or {})
                    ))
                    conn.commit()
        except Exception as e:
            print(f"Audit log error: {e}")

    def get_audit_logs(self, limit=200, action_type=None, search_query=None):
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
                    if action_type and action_type != 'ALL':
                        q += " AND a.action_type = %s"
                        params.append(action_type)
                    if search_query:
                        sq = f"%{search_query.strip()}%"
                        q += " AND (a.description ILIKE %s OR a.user_name ILIKE %s OR a.entity_type ILIKE %s OR CAST(a.entity_id AS TEXT) ILIKE %s)"
                        params.extend([sq, sq, sq, sq])
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

    def add_user(self, username, password, full_name, permissions, role='custom'):
        hashed = self.hash_password(password)
        perm_json = json.dumps(permissions)
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (username, password_hash, full_name, role, permissions, is_active)
                    VALUES (%s, %s, %s, %s, %s::jsonb, TRUE) RETURNING id;
                """, (username.strip(), hashed, full_name.strip(), role or 'custom', perm_json))
                uid = cur.fetchone()['id']
                conn.commit()
                return uid

    def create_user(self, username, password, full_name, permissions, role='custom'):
        return self.add_user(username, password, full_name, permissions, role=role)

    def update_user(self, user_id, full_name, permissions, new_password=None, role=None, username=None, is_active=None):
        perm_json = json.dumps(permissions)
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT username, role, is_active FROM users WHERE id = %s;", (user_id,))
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

    def archive_supplier(self, supp_id):
        s_id = _clean_int_id(supp_id)
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE suppliers SET is_active = FALSE WHERE id = %s;", (s_id,))
                conn.commit()

    def restore_supplier(self, supp_id):
        s_id = _clean_int_id(supp_id)
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE suppliers SET is_active = TRUE WHERE id = %s;", (s_id,))
                conn.commit()

    def get_suppliers_with_stats(self, search_query=None):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT s.id, s.name, COALESCE(s.phone, '-') as phone,
                               COALESCE(s.supplier_type, 'تاجر') as supplier_type,
                               COUNT(DISTINCT d.id) FILTER (WHERE COALESCE(d.is_deleted, FALSE) = FALSE) as devices_count,
                               COALESCE((SELECT SUM(total_amount) FROM supplier_invoices si WHERE si.supplier_id = s.id), 0) as total_bought,
                               COALESCE((SELECT SUM(paid_amount) FROM supplier_invoices si WHERE si.supplier_id = s.id), 0) as total_paid,
                               COALESCE((SELECT SUM(remaining_amount) FROM supplier_invoices si WHERE si.supplier_id = s.id), 0) as total_remaining
                        FROM suppliers s
                        LEFT JOIN devices d ON d.supplier_id = s.id
                        WHERE COALESCE(s.is_active, TRUE) = TRUE
                    """
                    params = []
                    if search_query and str(search_query).strip():
                        q = str(search_query).strip()
                        query += " AND (s.name ILIKE %s OR COALESCE(s.phone, '') ILIKE %s OR COALESCE(s.supplier_type, '') ILIKE %s OR CAST(s.id AS TEXT) = %s)"
                        params.extend([f"%{q}%", f"%{q}%", f"%{q}%", q.lstrip('#')])
                    query += " GROUP BY s.id ORDER BY s.id DESC;"
                    cur.execute(query, params)
                    return cur.fetchall()
        except Exception as e:
            print(f"Supplier stats error: {e}")
            return []

    def get_devices_by_supplier(self, supplier_id):
        supp_id = _clean_int_id(supplier_id)
        if not supp_id:
            return []
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT d.id, d.category, d.model, COALESCE(d.storage, '-') as storage,
                               COALESCE(d.ram, '') as ram,
                               d.imei_serial, d.buy_price,
                               COALESCE(d.device_condition, 'مستعمل') as device_condition,
                               COALESCE(d.device_condition, 'مستعمل') as condition,
                               COALESCE(d.has_box, TRUE) as has_box,
                               COALESCE(d.has_box, TRUE) as with_box,
                               CASE WHEN d.is_sold THEN 'مباع 🔴' ELSE 'بالمخزون 🟢' END as status,
                               TO_CHAR(d.buy_date, 'YYYY-MM-DD HH24:MI') as buy_date_fmt
                        FROM devices d
                        WHERE d.supplier_id = %s AND COALESCE(d.is_deleted, FALSE) = FALSE
                        ORDER BY d.id DESC;
                    """, (supp_id,))
                    return cur.fetchall()
        except Exception:
            return []

    def add_supplier(self, name, phone, supplier_type='تاجر'):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO suppliers (name, phone, supplier_type) VALUES (%s, %s, %s) RETURNING id;",
                    (name.strip(), phone.strip() if phone else '', supplier_type or 'تاجر')
                )
                supp_id = cur.fetchone()['id']
                conn.commit()
                return supp_id

    def update_supplier(self, supp_id, name, phone, supplier_type='تاجر'):
        s_id = _clean_int_id(supp_id)
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE suppliers SET name = %s, phone = %s, supplier_type = %s WHERE id = %s;",
                    (name.strip(), phone.strip() if phone else '', supplier_type or 'تاجر', s_id)
                )
                conn.commit()

    def delete_supplier(self, supp_id):
        s_id = _clean_int_id(supp_id)
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COALESCE(SUM(remaining_amount), 0) as rem FROM supplier_invoices WHERE supplier_id = %s;", (s_id,))
                rem = float(cur.fetchone()['rem'] or 0)
                if rem > 0:
                    raise Exception(f"لا يمكن حذف المورد لوجود مديونية متبقية له بقيمة ({rem:,.2f} ج.م)!")
                cur.execute("UPDATE suppliers SET is_active = FALSE WHERE id = %s;", (s_id,))
                conn.commit()

    def get_distinct_models_by_category(self, category=None):
        """جلب الموديلات المسجلة سابقاً في قاعدة البيانات لدعم الاقتراح التلقائي الذكي."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    if category and category.strip():
                        cur.execute("""
                            SELECT DISTINCT model FROM devices
                            WHERE category ILIKE %s AND COALESCE(is_deleted, FALSE) = FALSE
                            ORDER BY model ASC LIMIT 40;
                        """, (f"%{category.strip()}%",))
                    else:
                        cur.execute("""
                            SELECT DISTINCT model FROM devices
                            WHERE COALESCE(is_deleted, FALSE) = FALSE
                            ORDER BY model ASC LIMIT 40;
                        """)
                    return [r['model'] for r in cur.fetchall() if r.get('model')]
        except Exception:
            return []

    def add_device(self, category, model, storage="", ram="", battery=None, accessories="", imei="", buy_price=0.0, supplier_id=None, notes="", user_id=None, device_condition="مستعمل", has_box=True, paid_amount=0.0):
        if not supplier_id:
            raise Exception("يجب اختيار المورد أولاً لإتمام عملية الشراء!")

        ram_val = ram.strip() if ram else ""
        bat_val = int(battery) if (battery is not None and str(battery).replace('.', '', 1).isdigit()) else 0
        if bat_val < 0 or bat_val > 100:
            raise Exception("نسبة صحة البطارية غير منطقية! يجب أن تكون بين 1% و 100%.")

        cond_val = device_condition if device_condition in ("جديد", "مستعمل", "كسر زيرو") else "مستعمل"
        box_val = bool(has_box)
        b_price = float(buy_price or 0)
        paid_now = max(0.0, min(b_price, float(paid_amount if paid_amount is not None else b_price)))
        rem_now = max(0.0, b_price - paid_now)

        clean_imei = (imei or "").strip()

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # التحقق من عدم تكرار السيريال IMEI لجهاز متاح أو غير محذوف
                if clean_imei:
                    cur.execute("SELECT id, model FROM devices WHERE imei_serial = %s AND COALESCE(is_sold, FALSE) = FALSE AND COALESCE(is_deleted, FALSE) = FALSE;", (clean_imei,))
                    dup = cur.fetchone()
                    if dup:
                        raise Exception(f"السيريال ({clean_imei}) مسجل بالفعل بالمخزون للجهاز #{dup['id']} ({dup['model']})!")

                inv_id = None
                cur.execute("SELECT id, total_amount, paid_amount FROM supplier_invoices WHERE supplier_id = %s AND invoice_date = CURRENT_DATE ORDER BY id DESC LIMIT 1 FOR UPDATE;", (supplier_id,))
                inv = cur.fetchone()
                if inv:
                    inv_id = inv['id']
                    new_tot = float(inv['total_amount'] or 0) + b_price
                    new_paid = float(inv['paid_amount'] or 0) + paid_now
                    new_rem = max(0.0, new_tot - new_paid)
                    st = 'PAID' if new_rem <= 0 else 'UNPAID'
                    cur.execute("""
                        UPDATE supplier_invoices 
                        SET total_amount = %s, paid_amount = %s, remaining_amount = %s, status = %s 
                        WHERE id = %s;
                    """, (new_tot, new_paid, new_rem, st, inv_id))
                else:
                    st = 'PAID' if rem_now <= 0 else 'UNPAID'
                    cur.execute("""
                        INSERT INTO supplier_invoices (supplier_id, total_amount, paid_amount, remaining_amount, status, invoice_date, created_by_user_id) 
                        VALUES (%s, %s, %s, %s, %s, CURRENT_DATE, %s) RETURNING id;
                    """, (supplier_id, b_price, paid_now, rem_now, st, user_id))
                    inv_id = cur.fetchone()['id']

                if paid_now > 0:
                    cur.execute("""
                        INSERT INTO supplier_payments (invoice_id, supplier_id, payment_amount, notes, created_by_user_id)
                        VALUES (%s, %s, %s, %s, %s);
                    """, (inv_id, supplier_id, paid_now, f"دفعة فورية عند شراء {category} {model}", user_id))

                cur.execute("""
                    INSERT INTO devices (
                        category, model, storage, ram, battery_health, accessories,
                        device_condition, has_box, imei_serial, buy_price,
                        supplier_id, invoice_id, notes, created_by_user_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
                """, (category, model, storage, ram_val, bat_val, accessories, cond_val, box_val, clean_imei, b_price, supplier_id, inv_id, notes, user_id))
                device_id = cur.fetchone()['id']

                conn.commit()

        # تسجيل حركة الشراء في سجل التدقيق
        self.add_audit_log(
            user_id=user_id,
            user_name=None,
            action_type="ADD_DEVICE",
            entity_type="DEVICE",
            entity_id=device_id,
            description=f"إضافة وشراء جهاز للمخزون #{device_id} ({category} {model}) بسعر {b_price:,.2f} ج.م",
            old_values=None,
            new_values={"category": category, "model": model, "storage": storage, "ram": ram_val, "battery": bat_val, "imei": clean_imei, "buy_price": b_price, "supplier_id": supplier_id}
        )
        return device_id

    def update_device(self, device_id, category, model, storage="", ram="", battery=None, imei="", buy_price=0.0, device_condition="مستعمل", has_box=True, notes=""):
        dev_id = _clean_int_id(device_id)
        if dev_id is None:
            raise Exception("كود الجهاز غير صالح!")

        cond_val = device_condition if device_condition in ("جديد", "مستعمل", "كسر زيرو") else "مستعمل"
        box_val = bool(has_box)
        bat_val = int(battery) if (battery is not None and str(battery).replace('.', '', 1).isdigit()) else 0
        if bat_val < 0 or bat_val > 100:
            raise Exception("نسبة صحة البطارية غير منطقية! يجب أن تكون بين 1% و 100%.")

        ram_val = ram.strip() if ram else ""
        clean_imei = (imei or "").strip()

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                if clean_imei:
                    cur.execute("SELECT id, model FROM devices WHERE imei_serial = %s AND id != %s AND COALESCE(is_sold, FALSE) = FALSE AND COALESCE(is_deleted, FALSE) = FALSE;", (clean_imei, dev_id))
                    dup = cur.fetchone()
                    if dup:
                        raise Exception(f"السيريال ({clean_imei}) مستخدم بالفعل في جهاز آخر بالمخزون #{dup['id']} ({dup['model']})!")

                cur.execute("SELECT * FROM devices WHERE id = %s FOR UPDATE;", (dev_id,))
                old_dev = cur.fetchone()
                if old_dev:
                    old_price = float(old_dev['buy_price'] or 0)
                    inv_id = old_dev.get('invoice_id')
                    supp_id = old_dev.get('supplier_id')
                    diff = float(buy_price) - old_price

                    if not inv_id and supp_id:
                        cur.execute("SELECT id FROM supplier_invoices WHERE supplier_id = %s ORDER BY id DESC LIMIT 1;", (supp_id,))
                        res = cur.fetchone()
                        if res:
                            inv_id = res['id']

                    if inv_id and diff != 0:
                        cur.execute("SELECT total_amount, paid_amount FROM supplier_invoices WHERE id = %s FOR UPDATE;", (inv_id,))
                        inv = cur.fetchone()
                        if inv:
                            new_tot = max(0.0, float(inv['total_amount'] or 0) + diff)
                            paid = float(inv['paid_amount'] or 0)
                            new_rem = max(0.0, new_tot - paid)
                            status = 'PAID' if new_rem <= 0 else 'UNPAID'
                            cur.execute("""
                                UPDATE supplier_invoices 
                                SET total_amount = %s, remaining_amount = %s, status = %s
                                WHERE id = %s;
                            """, (new_tot, new_rem, status, inv_id))

                cur.execute("""
                    UPDATE devices 
                    SET category = %s, model = %s, storage = %s, ram = %s,
                        battery_health = %s, imei_serial = %s, buy_price = %s,
                        device_condition = %s, has_box = %s, notes = %s
                    WHERE id = %s;
                """, (category, model, storage, ram_val, bat_val, clean_imei, buy_price, cond_val, box_val, notes, dev_id))

                cur.execute("UPDATE sales SET net_profit = sell_price - %s WHERE device_id = %s;", (buy_price, dev_id))
                conn.commit()

        self.add_audit_log(
            user_id=None,
            user_name=None,
            action_type="EDIT_DEVICE",
            entity_type="DEVICE",
            entity_id=dev_id,
            description=f"تعديل بيانات الجهاز #{dev_id} ({category} {model})",
            old_values=dict(old_dev) if old_dev else None,
            new_values={"category": category, "model": model, "storage": storage, "ram": ram_val, "battery": bat_val, "imei": clean_imei, "buy_price": buy_price}
        )

    def soft_delete_device(self, device_id, user_id=None, deduct_mode="FROM_DEBT_FIRST"):
        dev_id = _clean_int_id(device_id)
        if dev_id is None:
            raise Exception("كود الجهاز غير صالح!")

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM devices WHERE id = %s FOR UPDATE;", (dev_id,))
                dev = cur.fetchone()
                if not dev:
                    raise Exception("الجهاز غير موجود!")

                if dev.get('is_deleted'):
                    raise Exception("الجهاز محذوف بالفعل!")

                buy_price = float(dev['buy_price'] or 0)
                inv_id = dev.get('invoice_id')
                supp_id = dev.get('supplier_id')

                cur.execute("UPDATE devices SET is_deleted = TRUE, is_sold = FALSE WHERE id = %s;", (dev_id,))

                if not inv_id and supp_id:
                    cur.execute("SELECT id FROM supplier_invoices WHERE supplier_id = %s ORDER BY id DESC LIMIT 1;", (supp_id,))
                    res = cur.fetchone()
                    if res:
                        inv_id = res['id']

                if inv_id:
                    cur.execute("SELECT * FROM supplier_invoices WHERE id = %s FOR UPDATE;", (inv_id,))
                    inv = cur.fetchone()
                    if inv:
                        tot = float(inv['total_amount'] or 0)
                        paid = float(inv['paid_amount'] or 0)

                        new_tot = max(0.0, tot - buy_price)
                        if deduct_mode == "FROM_PAID_AND_TOTAL":
                            new_paid = max(0.0, paid - buy_price)
                            if new_paid > new_tot:
                                new_paid = new_tot
                        else:
                            new_paid = min(paid, new_tot)

                        deducted_paid = max(0.0, paid - new_paid)
                        new_rem = max(0.0, new_tot - new_paid)
                        status = 'PAID' if new_rem <= 0 else 'UNPAID'

                        cur.execute("""
                            UPDATE supplier_invoices 
                            SET total_amount = %s, paid_amount = %s, remaining_amount = %s, status = %s
                            WHERE id = %s;
                        """, (new_tot, new_paid, new_rem, status, inv_id))

                        if deducted_paid > 0:
                            cur.execute("""
                                SELECT id, payment_amount 
                                FROM supplier_payments 
                                WHERE invoice_id = %s 
                                ORDER BY id DESC FOR UPDATE;
                            """, (inv_id,))
                            pay_rows = cur.fetchall()
                            rem_to_deduct = deducted_paid
                            for pr in pay_rows:
                                if rem_to_deduct <= 0:
                                    break
                                p_amt = float(pr['payment_amount'] or 0)
                                if p_amt <= rem_to_deduct:
                                    cur.execute("DELETE FROM supplier_payments WHERE id = %s;", (pr['id'],))
                                    rem_to_deduct -= p_amt
                                else:
                                    cur.execute("UPDATE supplier_payments SET payment_amount = %s WHERE id = %s;", (p_amt - rem_to_deduct, pr['id']))
                                    rem_to_deduct = 0.0

                cur.execute("SELECT id FROM sales WHERE device_id = %s;", (dev_id,))
                sale = cur.fetchone()
                if sale:
                    sale_id = sale['id']
                    cur.execute("DELETE FROM customer_payments WHERE sale_id = %s;", (sale_id,))
                    cur.execute("DELETE FROM sales WHERE id = %s;", (sale_id,))

                conn.commit()

        self.add_audit_log(
            user_id=user_id,
            user_name=None,
            action_type="DELETE_DEVICE",
            entity_type="DEVICE",
            entity_id=dev_id,
            description=f"حذف ذكي للجهاز #{dev_id} ({dev.get('category')} {dev.get('model')}) مع تسوية حساب المورد",
            old_values=dict(dev),
            new_values={"is_deleted": True}
        )

    def delete_device(self, device_id, user_id=None):
        return self.soft_delete_device(device_id, user_id=user_id, deduct_mode="FROM_DEBT_FIRST")

    def get_inventory(self, include_sold=False):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    where_sold = "" if include_sold else "AND COALESCE(d.is_sold, FALSE) = FALSE"
                    cur.execute(f"""
                        SELECT d.id, d.category, d.model, d.storage, d.ram, d.battery_health,
                               COALESCE(d.device_condition, 'مستعمل') as device_condition,
                               COALESCE(d.has_box, TRUE) as has_box,
                               COALESCE(d.notes, '') as notes,
                               d.imei_serial, d.buy_price,
                               COALESCE(d.is_sold, FALSE) as is_sold,
                               COALESCE(d.is_deleted, FALSE) as is_deleted,
                               COALESCE(s.name, 'غير محدد') as supplier_name,
                               COALESCE(s.supplier_type, 'تاجر') as supplier_type,
                               TO_CHAR(d.buy_date, 'YYYY-MM-DD HH24:MI') as buy_date_formatted
                        FROM devices d
                        LEFT JOIN suppliers s ON d.supplier_id = s.id
                        WHERE COALESCE(d.is_deleted, FALSE) = FALSE {where_sold}
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
                               COALESCE(d.has_box, TRUE) as has_box,
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
                               COALESCE(d.has_box, TRUE) as has_box,
                               COALESCE(d.notes, '') as notes,
                               d.imei_serial, d.buy_price,
                               COALESCE(s.name, 'غير محدد') as supplier_name,
                               COALESCE(s.supplier_type, 'تاجر') as supplier_type,
                               TO_CHAR(d.buy_date, 'YYYY-MM-DD HH24:MI') as buy_date_formatted
                        FROM devices d
                        LEFT JOIN suppliers s ON d.supplier_id = s.id
                        WHERE COALESCE(d.is_sold, FALSE) = FALSE AND COALESCE(d.is_deleted, FALSE) = FALSE
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

                    if filters and isinstance(filters, dict):
                        cond = filters.get('condition') or filters.get('device_condition')
                        if cond in ('جديد', 'مستعمل'):
                            query += " AND COALESCE(d.device_condition, 'مستعمل') = %s"
                            params.append(cond)

                        hbox = filters.get('has_box')
                        if hbox in ('بعلبة', 'YES', True):
                            query += " AND COALESCE(d.has_box, TRUE) = TRUE"
                        elif hbox in ('بدون علبة', 'NO', False):
                            query += " AND COALESCE(d.has_box, TRUE) = FALSE"

                        cat = (filters.get('category') or '').strip()
                        if cat and cat != 'الكل':
                            query += " AND d.category ILIKE %s"
                            params.append(f"%{cat}%")

                        supp_id = filters.get('supplier_id')
                        if supp_id and str(supp_id) != 'ALL':
                            s_id_int = _clean_int_id(supp_id)
                            if s_id_int is not None:
                                query += " AND d.supplier_id = %s"
                                params.append(s_id_int)

                        date_from = (filters.get('date_from') or '').strip()
                        if date_from:
                            query += " AND DATE(d.buy_date) >= %s"
                            params.append(date_from)

                        date_to = (filters.get('date_to') or '').strip()
                        if date_to:
                            query += " AND DATE(d.buy_date) <= %s"
                            params.append(date_to)

                    query += " ORDER BY d.id DESC;"
                    cur.execute(query, params)
                    return cur.fetchall()
        except Exception as e:
            print(f"Inventory query error: {e}")
            return []

    def get_capital_statistics(self):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) as total_devices, COALESCE(SUM(buy_price), 0) as total_capital FROM devices WHERE COALESCE(is_sold, FALSE) = FALSE AND COALESCE(is_deleted, FALSE) = FALSE;")
                    return cur.fetchone()
        except Exception:
            return {'total_devices': 0, 'total_capital': 0}

    def search_device_by_criteria(self, query, search_by='SERIAL'):
        try:
            q_str = str(query or "").strip()
            if not q_str:
                return None
            q_id = q_str.lstrip('#')

            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    base_select = """
                        SELECT d.*,
                               COALESCE(d.device_condition, 'مستعمل') as device_condition,
                               COALESCE(d.has_box, TRUE) as has_box,
                               COALESCE(s.name, 'غير محدد') as supplier_name,
                               TO_CHAR(d.buy_date, 'YYYY-MM-DD HH24:MI') as buy_date_formatted,
                               sl.id as sale_id, sl.sell_price, sl.customer_name, sl.customer_phone,
                               sl.cash_received, sl.remaining_balance, sl.notes as sale_notes
                        FROM devices d
                        LEFT JOIN suppliers s ON d.supplier_id = s.id
                        LEFT JOIN sales sl ON d.id = sl.device_id
                        WHERE COALESCE(d.is_deleted, FALSE) = FALSE
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

    def search_device_by_imei_or_id(self, query):
        return self.search_device_by_criteria(query, search_by='ALL')

    def process_sale(self, device_id, sell_price, customer_name, customer_phone, cash_received, notes, user_id, original_price=None, discount=0.0):
        dev_id = _clean_int_id(device_id)
        if dev_id is None:
            raise Exception("كود الجهاز غير صالح!")

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT buy_price, is_deleted FROM devices WHERE id = %s AND COALESCE(is_sold, FALSE) = FALSE FOR UPDATE", (dev_id,))
                dev = cur.fetchone()
                if not dev or dev.get('is_deleted'):
                    raise Exception("الجهاز غير متاح للبيع أو تم حذفه!")

                buy_price = float(dev['buy_price'])
                sell_val = float(sell_price)
                orig_val = float(original_price) if original_price is not None else sell_val
                disc_val = float(discount or 0.0)

                if sell_val < buy_price:
                    raise Exception(f"لا يمكن البيع بأقل من سعر الشراء ({buy_price:,.2f} ج.م)!")

                cash = float(cash_received or 0)
                if cash > sell_val:
                    raise Exception("المبلغ المدفوع أكبر من سعر البيع النهائي!")

                rem = max(0.0, sell_val - cash)
                net_profit = sell_val - buy_price

                cur.execute("""
                    INSERT INTO sales (device_id, original_price, discount, sell_price, customer_name, customer_phone, cash_received, remaining_balance, net_profit, notes, created_by_user_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
                """, (dev_id, orig_val, disc_val, sell_val, customer_name or 'عميل نقدي', customer_phone or '', cash, rem, net_profit, notes or '', user_id))
                sale_id = cur.fetchone()['id']

                if cash > 0:
                    cur.execute("""
                        INSERT INTO customer_payments (sale_id, payment_amount, notes, created_by_user_id)
                        VALUES (%s, %s, %s, %s);
                    """, (sale_id, cash, 'دفعة مقدمة عند البيع', user_id))

                cur.execute("UPDATE devices SET is_sold = TRUE WHERE id = %s;", (dev_id,))
                conn.commit()

        self.add_audit_log(
            user_id=user_id,
            user_name=None,
            action_type="SALE",
            entity_type="SALE",
            entity_id=sale_id,
            description=f"إتمام بيع جهاز #{dev_id} للعميل ({customer_name or 'عميل نقدي'}) بسعر {sell_val:,.2f} ج.م ومتبقي {rem:,.2f} ج.م",
            old_values={"is_sold": False, "device_id": dev_id},
            new_values={"sale_id": sale_id, "sell_price": sell_val, "cash_received": cash, "remaining": rem, "customer_name": customer_name}
        )
        return sale_id

    def process_return(self, device_id, user_id=None):
        dev_id = _clean_int_id(device_id)
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM sales WHERE device_id = %s;", (dev_id,))
                sale = cur.fetchone()
                if sale:
                    cur.execute("DELETE FROM customer_payments WHERE sale_id = %s;", (sale['id'],))
                    cur.execute("DELETE FROM sales WHERE id = %s;", (sale['id'],))
                cur.execute("UPDATE devices SET is_sold = FALSE WHERE id = %s;", (dev_id,))
                conn.commit()

        self.add_audit_log(
            user_id=user_id,
            user_name=None,
            action_type="RETURN_DEVICE",
            entity_type="DEVICE",
            entity_id=dev_id,
            description=f"استرجاع جهاز مباع #{dev_id} وإلغاء فاتورة البيع وإعادته للمخزون"
        )

    def get_customer_debts(self, search_query=None):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT s.id as sale_id, s.id as id, d.id as device_id, d.category, d.model, d.imei_serial,
                               d.storage, d.ram,
                               COALESCE(d.device_condition, 'مستعمل') as device_condition,
                               COALESCE(d.has_box, TRUE) as has_box,
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
                        WHERE s.remaining_balance > 0 AND COALESCE(d.is_deleted, FALSE) = FALSE
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

    def pay_customer_debt(self, sale_id, amount, user_id, notes=""):
        s_id = _clean_int_id(sale_id)
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT remaining_balance, cash_received FROM sales WHERE id = %s FOR UPDATE;", (s_id,))
                sale = cur.fetchone()
                if not sale:
                    raise Exception("الفاتورة غير موجودة!")

                rem = float(sale['remaining_balance'])
                if amount > rem:
                    raise Exception(f"المبلغ المدفوع أكبر من المتبقي ({rem:,.2f} ج.م)!")

                new_cash = float(sale['cash_received']) + amount
                new_rem = max(0.0, rem - amount)

                cur.execute("UPDATE sales SET cash_received = %s, remaining_balance = %s WHERE id = %s;", (new_cash, new_rem, s_id))
                cur.execute("INSERT INTO customer_payments (sale_id, payment_amount, notes, created_by_user_id) VALUES (%s, %s, %s, %s);", (s_id, amount, notes or 'تحصيل دفعة من العميل', user_id))
                conn.commit()

        self.add_audit_log(
            user_id=user_id,
            user_name=None,
            action_type="COLLECT_DEBT",
            entity_type="CUSTOMER_DEBT",
            entity_id=s_id,
            description=f"تحصيل دفعة مديونية بقيمة {amount:,.2f} ج.م للفاتورة #{s_id} (متبقي جديد: {new_rem:,.2f} ج.م)",
            old_values={"remaining_balance": rem},
            new_values={"paid_now": amount, "new_remaining": new_rem}
        )

    def collect_debt_installment(self, sale_id, amount, user_id, notes=""):
        return self.pay_customer_debt(sale_id, amount, user_id, notes=notes)

    def get_supplier_invoices(self, search_query=None, status_filter='ALL', search_by='ALL', supplier_id=None, unpaid_only=False):
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
                               (SELECT COUNT(*) FROM devices d WHERE d.invoice_id = i.id AND COALESCE(d.is_deleted, FALSE) = FALSE) as devices_count,
                               i.total_amount, i.paid_amount, i.remaining_amount, i.status
                        FROM supplier_invoices i
                        LEFT JOIN suppliers s ON i.supplier_id = s.id
                        WHERE i.total_amount > 0
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
                            query += " AND (s.name ILIKE %s OR CAST(i.id AS TEXT) = %s OR TO_CHAR(i.invoice_date, 'YYYY-MM-DD') ILIKE %s)"
                            params.extend([f"%{q_str}%", q_clean, f"%{q_str}%"])

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
                               COALESCE(d.device_condition, 'مستعمل') as device_condition,
                               COALESCE(d.device_condition, 'مستعمل') as condition,
                               COALESCE(d.has_box, TRUE) as has_box,
                               COALESCE(d.has_box, TRUE) as with_box,
                               COALESCE(d.notes, '') as notes,
                               CASE WHEN d.is_sold THEN 'SOLD' ELSE 'IN_STOCK' END as status
                        FROM devices d
                        WHERE d.invoice_id = %s AND COALESCE(d.is_deleted, FALSE) = FALSE
                        ORDER BY d.id DESC;
                    """, (inv_id,))
                    devs = cur.fetchall()
                    if not devs:
                        cur.execute("""
                            SELECT d.id, d.category, d.model, COALESCE(d.storage, '-') as storage,
                                   COALESCE(d.ram, '') as ram,
                                   d.battery_health,
                                   d.imei_serial, d.buy_price,
                                   COALESCE(d.is_sold, FALSE) as is_sold,
                                   COALESCE(d.device_condition, 'مستعمل') as device_condition,
                                   COALESCE(d.device_condition, 'مستعمل') as condition,
                                   COALESCE(d.has_box, TRUE) as has_box,
                                   COALESCE(d.has_box, TRUE) as with_box,
                                   COALESCE(d.notes, '') as notes,
                                   CASE WHEN d.is_sold THEN 'SOLD' ELSE 'IN_STOCK' END as status
                            FROM devices d
                            JOIN supplier_invoices i ON d.supplier_id = i.supplier_id AND DATE(d.buy_date) = i.invoice_date
                            WHERE i.id = %s AND COALESCE(d.is_deleted, FALSE) = FALSE
                            ORDER BY d.id DESC;
                        """, (inv_id,))
                        devs = cur.fetchall()
                    return devs
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

    def pay_supplier_debt(self, invoice_id, amount, user_id, notes=""):
        inv_id = _clean_int_id(invoice_id)
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM supplier_invoices WHERE id = %s FOR UPDATE;", (inv_id,))
                inv = cur.fetchone()
                if not inv:
                    raise Exception("الفاتورة غير موجودة!")

                rem = float(inv['remaining_amount'])
                if amount > rem:
                    raise Exception(f"مبلغ الدفعة ({amount:,.2f}) أكبر من المتبقي ({rem:,.2f})!")

                new_paid = float(inv['paid_amount']) + amount
                new_rem = max(0.0, rem - amount)
                status = 'PAID' if new_rem <= 0 else 'UNPAID'

                cur.execute("""
                    UPDATE supplier_invoices 
                    SET paid_amount = %s, remaining_amount = %s, status = %s 
                    WHERE id = %s;
                """, (new_paid, new_rem, status, inv_id))

                cur.execute("""
                    INSERT INTO supplier_payments (invoice_id, supplier_id, payment_amount, notes, created_by_user_id)
                    VALUES (%s, %s, %s, %s, %s);
                """, (inv_id, inv['supplier_id'], amount, notes or 'سداد دفعة من الفاتورة', user_id))

                conn.commit()

        self.add_audit_log(
            user_id=user_id,
            user_name=None,
            action_type="PAY_SUPPLIER",
            entity_type="SUPPLIER_INVOICE",
            entity_id=inv_id,
            description=f"سداد دفعة للمورد بمبلغ {amount:,.2f} ج.م للفاتورة #{inv_id} (متبقي جديد: {new_rem:,.2f} ج.م)",
            old_values={"remaining_amount": rem},
            new_values={"paid_now": amount, "new_remaining": new_rem}
        )

    def add_capital_injection(self, amount, notes, user_id):
        return self.add_capital_transaction(amount=amount, transaction_type='INJECTION', notes=notes, user_id=user_id)

    def add_capital_transaction(self, amount, transaction_type='INJECTION', notes='', user_id=None):
        t_up = str(transaction_type).upper()
        tx_type = 'WITHDRAWAL' if t_up in ('WITHDRAWAL', 'WITHDRAW') else 'INJECTION'
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO capital_transactions (amount, transaction_type, notes, created_by_user_id)
                    VALUES (%s, %s, %s, %s) RETURNING id;
                """, (amount, tx_type, notes or ('إضافة سيولة نقدية' if tx_type == 'INJECTION' else 'حركة سحب ومصروف'), user_id))
                tx_id = cur.fetchone()['id']
                conn.commit()

        self.add_audit_log(
            user_id=user_id,
            user_name=None,
            action_type="CAPITAL_INJECTION" if tx_type == 'INJECTION' else "EXPENSE",
            entity_type="CAPITAL",
            entity_id=tx_id,
            description=f"{'إضافة وتغذية سيولة نقدية' if tx_type == 'INJECTION' else 'تسجيل مصروف / سحب'}: {amount:,.2f} ج.م - {notes}",
            new_values={"amount": amount, "type": tx_type, "notes": notes}
        )
        return tx_id

    def get_capital_transactions(self, search_query=None, date_from=None, date_to=None):
        """
        جلب سجل وتفاصيل حركات إضافة السيولة المالية مع إظهار التاريخ والمضيف والكمية والملاحظة.
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT ct.id, ct.amount,
                               CASE WHEN ct.transaction_type IN ('WITHDRAWAL', 'WITHDRAW') THEN 'WITHDRAW' ELSE 'DEPOSIT' END as transaction_type,
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
                        query += " AND DATE(ct.created_at) >= %s"
                        params.append(str(date_from).strip())
                    if date_to and str(date_to).strip():
                        query += " AND DATE(ct.created_at) <= %s"
                        params.append(str(date_to).strip())
                    query += " ORDER BY ct.id DESC;"
                    cur.execute(query, params)
                    return cur.fetchall()
        except Exception as e:
            print(f"Error fetching capital transactions: {e}")
            return []

    def delete_capital_transaction(self, tx_id):
        t_id = _clean_int_id(tx_id)
        if t_id is None:
            raise Exception("رقم الحركة غير صالح!")
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM capital_transactions WHERE id = %s;", (t_id,))
                conn.commit()

    def get_financial_summary(self):
        """
        حساب الملخص المالي الشامل:
        رأس المال = السيولة + المخزون + الخرج - المديونية
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) as cnt, COALESCE(SUM(buy_price), 0) as inv_cost FROM devices WHERE COALESCE(is_sold, FALSE) = FALSE AND COALESCE(is_deleted, FALSE) = FALSE;")
                    inv_row = cur.fetchone()
                    inv_cost = float(inv_row['inv_cost'] or 0)
                    avail_cnt = int(inv_row['cnt'] or 0)

                    cur.execute("SELECT COALESCE(SUM(remaining_balance), 0) as cust_debts FROM sales s JOIN devices d ON s.device_id = d.id WHERE COALESCE(d.is_deleted, FALSE) = FALSE;")
                    cust_debts = float(cur.fetchone()['cust_debts'])

                    cur.execute("SELECT COALESCE(SUM(remaining_amount), 0) as supp_debts FROM supplier_invoices WHERE remaining_amount > 0;")
                    supp_debts = float(cur.fetchone()['supp_debts'])

                    cur.execute("SELECT COALESCE(SUM(cash_received), 0) as total_sales_cash FROM sales s JOIN devices d ON s.device_id = d.id WHERE COALESCE(d.is_deleted, FALSE) = FALSE;")
                    total_sales_cash = float(cur.fetchone()['total_sales_cash'])

                    cur.execute("SELECT COALESCE(SUM(paid_amount), 0) as supp_payments FROM supplier_invoices;")
                    supp_payments = float(cur.fetchone()['supp_payments'])

                    cur.execute("SELECT COALESCE(SUM(amount), 0) as injections FROM capital_transactions WHERE COALESCE(transaction_type, 'INJECTION') IN ('INJECTION', 'DEPOSIT');")
                    injections = float(cur.fetchone()['injections'])

                    cur.execute("SELECT COALESCE(SUM(amount), 0) as withdrawals FROM capital_transactions WHERE transaction_type IN ('WITHDRAWAL', 'WITHDRAW');")
                    withdrawals = float(cur.fetchone()['withdrawals'])

                    cur.execute("""
                        SELECT COALESCE(SUM(net_profit), 0) as m_profit 
                        FROM sales s JOIN devices d ON s.device_id = d.id
                        WHERE COALESCE(d.is_deleted, FALSE) = FALSE AND TO_CHAR(s.sell_date, 'YYYY-MM') = TO_CHAR(CURRENT_DATE, 'YYYY-MM');
                    """)
                    m_profit = float(cur.fetchone()['m_profit'])

                    cur.execute("""
                        SELECT COALESCE(SUM(net_profit), 0) as tot_profit 
                        FROM sales s JOIN devices d ON s.device_id = d.id
                        WHERE COALESCE(d.is_deleted, FALSE) = FALSE;
                    """)
                    tot_profit = float(cur.fetchone()['tot_profit'])

                    net_injections = injections - withdrawals
                    current_liquidity = (net_injections + total_sales_cash) - supp_payments
                    # المعادلة المحدثة لرأس المال: السيولة + المخزون + الخرج - المديونية
                    total_capital = (current_liquidity + inv_cost + cust_debts) - supp_debts

                    return {
                        'inventory_cost': inv_cost,
                        'inventory_value': inv_cost,
                        'total_inventory_cost': inv_cost,
                        'available_devices_count': avail_cnt,
                        'customer_debts': cust_debts,
                        'total_customer_debts': cust_debts,
                        'supplier_debts': supp_debts,
                        'total_supplier_debts': supp_debts,
                        'current_liquidity': current_liquidity,
                        'available_liquidity': current_liquidity,
                        'total_capital': total_capital,
                        'monthly_profit': m_profit,
                        'current_month_profit': m_profit,
                        'total_profit': tot_profit,
                        'total_injections': net_injections
                    }
        except Exception as e:
            print(f"Error financial summary: {e}")
            return {
                'inventory_cost': 0, 'inventory_value': 0, 'total_inventory_cost': 0,
                'available_devices_count': 0,
                'customer_debts': 0, 'total_customer_debts': 0,
                'supplier_debts': 0, 'total_supplier_debts': 0,
                'current_liquidity': 0, 'available_liquidity': 0,
                'total_capital': 0, 'monthly_profit': 0, 'current_month_profit': 0,
                'total_profit': 0, 'total_injections': 0
            }

    def get_sales_report_advanced(self, date_from=None, date_to=None, search_query=None):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT s.id as sale_id, d.id as device_id, d.category, d.model, d.imei_serial, d.buy_price,
                               COALESCE(d.device_condition, 'مستعمل') as device_condition,
                               COALESCE(d.device_condition, 'مستعمل') as condition,
                               COALESCE(d.has_box, TRUE) as has_box,
                               COALESCE(d.has_box, TRUE) as with_box,
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
                        WHERE COALESCE(d.is_deleted, FALSE) = FALSE
                    """
                    params = []
                    if date_from and str(date_from).strip():
                        query += " AND DATE(s.sell_date) >= %s"
                        params.append(str(date_from).strip())
                    if date_to and str(date_to).strip():
                        query += " AND DATE(s.sell_date) <= %s"
                        params.append(str(date_to).strip())
                    if search_query and str(search_query).strip():
                        q = str(search_query).strip()
                        query += " AND (d.model ILIKE %s OR d.category ILIKE %s OR d.imei_serial ILIKE %s OR s.customer_name ILIKE %s OR COALESCE(u.full_name, '') ILIKE %s OR CAST(s.id AS TEXT) = %s)"
                        params.extend([f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", q.lstrip('#')])
                    query += " ORDER BY s.id DESC;"
                    cur.execute(query, params)
                    rows = cur.fetchall()
                    for r in rows:
                        rem = float(r.get('remaining_balance') or 0)
                        r['invoice_code'] = f"INV-SALE-{r['id']:05d}" if rem <= 0 else f"INV-DEBT-{r['id']:05d}"
                    return rows
        except Exception as e:
            print(f"Sales report error: {e}")
            return []

    def get_sales_report(self, date_from=None, date_to=None, search_query=None, start_date=None, end_date=None):
        df = date_from if date_from is not None else start_date
        dt = date_to if date_to is not None else end_date
        return self.get_sales_report_advanced(df, dt, search_query)

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
                               COALESCE(d.has_box, TRUE) as has_box,
                               COALESCE(d.notes, '') as notes,
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
                               COALESCE(d.has_box, TRUE) as has_box,
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
        """
        بحث شامل ذكي وموحد يتعرف تلقائياً على الباركود، كود الـ QR، السيريال، أو أكواد الفواتير.
        يدعم التعرف على:
        1. كود فاتورة بيع: INV-SALE-00001 أو SALE-1
        2. كود دين عميل / خرج: INV-DEBT-00001 أو DEBT-1
        3. كود فاتورة مورد: INV-BUY-00001 أو BUY-1
        4. كود سند مصروف / سيولة: EXP-00001
        5. سيريال IMEI للجهاز (بحث فوري مباشر)
        6. الرقم التعريفي المباشر #ID
        """
        q = str(query or "").strip()
        if not q:
            return None

        # 1. كود فاتورة بيع
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

        # 2. كود دين عميل (الخرج)
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

        # 3. كود فاتورة مشتريات مورد
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

        # 4. كود سند مصروف / خرج
        m_exp = re.search(r'EXP-(\d+)', q, re.I)
        if m_exp:
            exp_id = int(m_exp.group(1))
            txs = self.get_capital_transactions(search_query=str(exp_id))
            target = next((t for t in txs if t['id'] == exp_id), None)
            if target:
                return {
                    'entity_type': 'EXPENSE',
                    'title': f"سند مصروف / سيولة #{exp_id}",
                    'id': exp_id,
                    'code': f"EXP-{exp_id:05d}",
                    'data': target
                }

        # 5. السيريال IMEI (بحث مباشر وسريع بالأجهزة)
        dev_by_serial = self.search_device_by_criteria(q, search_by='SERIAL')
        if dev_by_serial:
            full_dev = self.get_device_full_details(dev_by_serial['id'])
            return {
                'entity_type': 'DEVICE',
                'title': f"جهاز بالسيريال: {dev_by_serial.get('category')} {dev_by_serial.get('model')}",
                'id': dev_by_serial['id'],
                'code': dev_by_serial.get('imei_serial') or f"DEV-{dev_by_serial['id']}",
                'data': full_dev or {'device': dev_by_serial}
            }

        # 6. البحث برقم المعرف المباشر ID
        clean_num = _clean_int_id(q)
        if clean_num:
            # التحقق أولاً من الأجهزة
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

            # التحقق من فواتير البيع
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

            # التحقق من فواتير الموردين
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

    def seed_demo_data(self):
        """
        بذر وتعبئة قاعدة البيانات المحددة ببيانات واقعية متكاملة لمركز الهواتف
        (موردين، أجهزة، فواتير مشتريات، عمليات بيع، مديونيات، تحصيلات، وحركات سيولة).
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # 1. الموردين
                    cur.execute("""
                        INSERT INTO suppliers (name, phone, supplier_type, is_active)
                        VALUES 
                            ('شركة الفجر للاستيراد والتوزيع', '01012345678', 'شركة / موزع معتمد', TRUE),
                            ('مؤسسة كيوان للهواتف والأجهزة', '01198765432', 'مستورد', TRUE),
                            ('الحاج محمود للتجارة العامة', '01234567890', 'تاجر جملة', TRUE);
                    """)
                    conn.commit()

                    cur.execute("SELECT id, name FROM suppliers ORDER BY id ASC;")
                    supp_rows = cur.fetchall()
                    s1 = supp_rows[0]['id'] if supp_rows else 1
                    s2 = supp_rows[1]['id'] if len(supp_rows) > 1 else s1
                    s3 = supp_rows[2]['id'] if len(supp_rows) > 2 else s1

                    # 2. فواتير مشتريات الموردين
                    cur.execute("""
                        INSERT INTO supplier_invoices (supplier_id, total_amount, paid_amount, remaining_amount, status, invoice_date)
                        VALUES 
                            (%s, 145000.00, 100000.00, 45000.00, 'PARTIAL', CURRENT_DATE - INTERVAL '10 days'),
                            (%s, 88000.00, 88000.00, 0.00, 'PAID', CURRENT_DATE - INTERVAL '5 days'),
                            (%s, 62000.00, 30000.00, 32000.00, 'PARTIAL', CURRENT_DATE - INTERVAL '2 days')
                        RETURNING id;
                    """, (s1, s2, s3))
                    inv_rows = cur.fetchall()
                    inv1 = inv_rows[0]['id'] if inv_rows else 1
                    inv2 = inv_rows[1]['id'] if len(inv_rows) > 1 else inv1
                    inv3 = inv_rows[2]['id'] if len(inv_rows) > 2 else inv1
                    conn.commit()

                    # 3. الأجهزة
                    demo_devices = [
                        ('iPhone', '15 Pro Max', '256', '8', 96, 'شاحن أصلي', 'كسر زيرو', True, '354892091234561', 48000.00, s1, inv1, 'حالة ممتازة وارد دبي', False),
                        ('iPhone', '14 Pro', '128', '6', 88, 'جراب + لاصقة', 'مستعمل', True, '354892091234562', 32000.00, s1, inv1, 'بدون خدوش', False),
                        ('iPhone', '13', '128', '4', 85, 'كرتونة كاملة', 'مستعمل', True, '354892091234563', 21000.00, s1, inv1, 'بطارية أصلية', True),
                        ('iPhone', '12 Pro Max', '256', '6', 84, 'شاحن', 'مستعمل', False, '354892091234564', 23500.00, s1, inv1, 'جهاز شغال تمام', True),
                        ('Samsung', 'Galaxy S24 Ultra', '512', '12', 100, 'علبة مقفولة', 'جديد', True, '864920041234565', 52000.00, s2, inv2, 'ضمان محلي', False),
                        ('Samsung', 'Galaxy S23 FE', '256', '8', 92, 'شاحن + كرتونة', 'كسر زيرو', True, '864920041234566', 22000.00, s2, inv2, 'استخدام بسيط جداً', False),
                        ('Samsung', 'A54 5G', '128', '8', 90, 'وصلة الشحن', 'مستعمل', True, '864920041234567', 11500.00, s2, inv2, 'حالة ممتازة', True),
                        ('Xiaomi', '13T Pro', '512', '12', 95, 'شاحن 120 واط', 'كسر زيرو', True, '869820051234568', 24000.00, s3, inv3, 'شحن فائق السرعة', False),
                        ('Xiaomi', 'Redmi Note 13 Pro', '256', '8', 100, 'كرتونة أصلية', 'جديد', True, '869820051234569', 12500.00, s3, inv3, 'جديد متبرشم', False),
                        ('Realme', '11 Pro Plus', '256', '12', 91, 'جراب أصلي', 'مستعمل', True, '862340061234570', 13000.00, s3, inv3, 'كاميرا 200 ميجا', False),
                    ]

                    dev_ids = []
                    for dev in demo_devices:
                        cur.execute("""
                            INSERT INTO devices (
                                category, model, storage, ram, battery_health, accessories,
                                device_condition, has_box, imei_serial, buy_price, supplier_id,
                                invoice_id, notes, is_sold, is_deleted
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE)
                            RETURNING id;
                        """, dev)
                        dev_ids.append(cur.fetchone()['id'])
                    conn.commit()

                    # 4. المبيعات
                    if len(dev_ids) > 2:
                        d_sold1 = dev_ids[2]
                        cur.execute("""
                            INSERT INTO sales (device_id, original_price, discount, sell_price, customer_name, customer_phone, cash_received, remaining_balance, net_profit, sell_date)
                            VALUES (%s, 23500.00, 500.00, 23000.00, 'طارق عبد الله', '01055667788', 23000.00, 0.00, 2000.00, CURRENT_TIMESTAMP - INTERVAL '3 days');
                        """, (d_sold1,))

                    if len(dev_ids) > 3:
                        d_sold2 = dev_ids[3]
                        cur.execute("""
                            INSERT INTO sales (device_id, original_price, discount, sell_price, customer_name, customer_phone, cash_received, remaining_balance, net_profit, sell_date)
                            VALUES (%s, 26000.00, 0.00, 26000.00, 'محمد إبراهيم حسن', '01144332211', 18000.00, 8000.00, 2500.00, CURRENT_TIMESTAMP - INTERVAL '1 day')
                            RETURNING id;
                        """, (d_sold2,))
                        s_row = cur.fetchone()
                        if s_row:
                            cur.execute("""
                                INSERT INTO customer_payments (sale_id, payment_amount, notes)
                                VALUES (%s, 3000.00, 'دفعة نقدية بالمعرض');
                            """, (s_row['id'],))

                    # 5. حركة رأس المال
                    cur.execute("""
                        INSERT INTO capital_transactions (amount, transaction_type, notes)
                        VALUES 
                            (250000.00, 'INJECTION', 'رأس مال افتتاحي للمركز'),
                            (50000.00, 'INJECTION', 'تغذية خزينة السيولة النقدية'),
                            (4200.00, 'WITHDRAWAL', 'مصروفات تشغيلية وفواتير المعرض');
                    """)
                    conn.commit()

            self.add_audit_log(None, "مدير النظام", "SYSTEM_INIT", "DATABASE", None, "تم بذر وتغذية البيانات الافتراضية التجريبية بنجاح")
            return True
        except Exception as ex:
            print(f"Error seeding demo data: {ex}")
            return False

