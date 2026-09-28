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
                    # 1. جدول المستخدمين
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS users (
                            id SERIAL PRIMARY KEY,
                            username VARCHAR(50) UNIQUE NOT NULL,
                            password_hash VARCHAR(255) NOT NULL,
                            full_name VARCHAR(100) NOT NULL DEFAULT 'مدير النظام',
                            permissions JSONB DEFAULT '{}'::jsonb,
                            is_active BOOLEAN DEFAULT TRUE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(100) DEFAULT 'مستخدم النظام';")
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
                            ram VARCHAR(50),
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
                    cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS customer_name VARCHAR(100) DEFAULT 'عميل نقدي';")
                    cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS customer_phone VARCHAR(30);")
                    cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS cash_received NUMERIC(12, 2) DEFAULT 0.00;")
                    cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS remaining_balance NUMERIC(12, 2) DEFAULT 0.00;")
                    cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS net_profit NUMERIC(12, 2) DEFAULT 0.00;")
                    cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS notes TEXT;")
                    cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS sell_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
                    cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS created_by_user_id INT REFERENCES users(id);")

                    # معالجة أي أعمدة قديمة في جدول sales قد تمنع الحفظ (مثل original_price أو discount)
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
                            payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            created_by_user_id INT REFERENCES users(id)
                        );
                    """)
                    cur.execute("ALTER TABLE customer_payments ADD COLUMN IF NOT EXISTS created_by_user_id INT REFERENCES users(id);")

                    # 7. جدول دفعات الموردين (الأقساط)
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS supplier_payments (
                            id SERIAL PRIMARY KEY,
                            invoice_id INT REFERENCES supplier_invoices(id) ON DELETE CASCADE,
                            supplier_id INT REFERENCES suppliers(id),
                            payment_amount NUMERIC(12, 2) NOT NULL,
                            payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            created_by_user_id INT REFERENCES users(id)
                        );
                    """)
                    cur.execute("ALTER TABLE supplier_payments ADD COLUMN IF NOT EXISTS supplier_id INT REFERENCES suppliers(id);")
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

                    conn.commit()
        except Exception as e:
            print(f"Table verification notice: {e}")

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
                    cur.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(%s) AND is_active = TRUE", (username.strip(),))
                    user = cur.fetchone()
                    if user:
                        stored_pass = str(user['password_hash']).strip()
                        input_pass = str(password).strip()

                        if self.check_password(input_pass, stored_pass):
                            return user

                        if stored_pass == input_pass:
                            new_hash = self.hash_password(input_pass)
                            cur.execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_hash, user['id']))
                            conn.commit()
                            user['password_hash'] = new_hash
                            return user
            return None
        except Exception as e:
            print(f"Error Authenticating: {e}")
            return None

    def get_all_users(self):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id, username, COALESCE(full_name, username) as full_name, permissions, is_active FROM users ORDER BY id ASC")
                    return cur.fetchall()
        except Exception:
            return []

    def add_user(self, username, password, full_name, permissions):
        hashed = self.hash_password(password)
        perm_json = json.dumps(permissions)
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (username, password_hash, full_name, permissions)
                    VALUES (%s, %s, %s, %s) RETURNING id;
                """, (username, hashed, full_name, perm_json))
                uid = cur.fetchone()['id']
                conn.commit()
                return uid

    def update_user(self, user_id, full_name, permissions, new_password=None):
        perm_json = json.dumps(permissions)
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                if new_password and new_password.strip():
                    hashed = self.hash_password(new_password.strip())
                    cur.execute("""
                        UPDATE users 
                        SET full_name = %s, permissions = %s, password_hash = %s 
                        WHERE id = %s;
                    """, (full_name, perm_json, hashed, user_id))
                else:
                    cur.execute("""
                        UPDATE users 
                        SET full_name = %s, permissions = %s 
                        WHERE id = %s;
                    """, (full_name, perm_json, user_id))
                conn.commit()

    def toggle_user_active(self, user_id):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE users SET is_active = NOT is_active WHERE id = %s;", (user_id,))
                conn.commit()

    def get_all_suppliers(self, search_query=None):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    query = "SELECT id, name, phone, COALESCE(supplier_type, 'تاجر') as supplier_type, is_active FROM suppliers WHERE is_active = TRUE"
                    params = []
                    if search_query:
                        query += " AND (name ILIKE %s OR phone ILIKE %s OR COALESCE(supplier_type, '') ILIKE %s OR CAST(id AS TEXT) = %s)"
                        params.extend([f"%{search_query}%", f"%{search_query}%", f"%{search_query}%", str(search_query)])
                    query += " ORDER BY name ASC;"
                    cur.execute(query, params)
                    return cur.fetchall()
        except Exception:
            return []

    def add_supplier(self, name, phone, supplier_type='تاجر'):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO suppliers (name, phone, supplier_type) VALUES (%s, %s, %s) RETURNING id;", (name, phone, supplier_type or 'تاجر'))
                supp_id = cur.fetchone()['id']
                conn.commit()
                return supp_id

    def update_supplier(self, supp_id, name, phone, supplier_type='تاجر'):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE suppliers SET name = %s, phone = %s, supplier_type = %s WHERE id = %s;", (name, phone, supplier_type or 'تاجر', supp_id))
                conn.commit()

    def delete_supplier(self, supp_id):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE suppliers SET is_active = FALSE WHERE id = %s;", (supp_id,))
                conn.commit()

    def get_distinct_models_by_category(self, category=None):
        """جلب الموديلات المسجلة سابقاً في قاعدة البيانات لدعم الاقتراح التلقائي الذكي."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    if category and category.strip():
                        cur.execute("""
                            SELECT DISTINCT model FROM devices
                            WHERE category ILIKE %s AND is_deleted = FALSE
                            ORDER BY model ASC LIMIT 40;
                        """, (f"%{category.strip()}%",))
                    else:
                        cur.execute("""
                            SELECT DISTINCT model FROM devices
                            WHERE is_deleted = FALSE
                            ORDER BY model ASC LIMIT 40;
                        """)
                    return [r['model'] for r in cur.fetchall() if r.get('model')]
        except Exception:
            return []

    def add_device(self, category, model, storage, ram, battery, accessories, imei, buy_price, supplier_id, notes, user_id, device_condition="مستعمل", has_box=True):
        if not supplier_id:
            raise Exception("يجب اختيار المورد أولاً لإتمام عملية الشراء!")

        ram_val = ram if ram else "لا يوجد"
        bat_val = int(battery) if (battery is not None and str(battery).replace('.', '', 1).isdigit()) else 0
        cond_val = device_condition if device_condition in ("جديد", "مستعمل") else "مستعمل"
        box_val = bool(has_box)

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                inv_id = None
                cur.execute("SELECT id FROM supplier_invoices WHERE supplier_id = %s AND invoice_date = CURRENT_DATE ORDER BY id DESC LIMIT 1;", (supplier_id,))
                inv = cur.fetchone()
                if inv:
                    inv_id = inv['id']
                    cur.execute("""
                        UPDATE supplier_invoices 
                        SET total_amount = total_amount + %s, remaining_amount = remaining_amount + %s, status = 'UNPAID' 
                        WHERE id = %s;
                    """, (buy_price, buy_price, inv_id))
                else:
                    cur.execute("""
                        INSERT INTO supplier_invoices (supplier_id, total_amount, paid_amount, remaining_amount, status, invoice_date, created_by_user_id) 
                        VALUES (%s, %s, 0, %s, 'UNPAID', CURRENT_DATE, %s) RETURNING id;
                    """, (supplier_id, buy_price, buy_price, user_id))
                    inv_id = cur.fetchone()['id']

                cur.execute("""
                    INSERT INTO devices (
                        category, model, storage, ram, battery_health, accessories,
                        device_condition, has_box, imei_serial, buy_price,
                        supplier_id, invoice_id, notes, created_by_user_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
                """, (category, model, storage, ram_val, bat_val, accessories, cond_val, box_val, imei, buy_price, supplier_id, inv_id, notes, user_id))
                device_id = cur.fetchone()['id']

                conn.commit()
                return device_id

    def update_device(self, device_id, category, model, storage, ram, battery, imei, buy_price, device_condition="مستعمل", has_box=True, notes=""):
        dev_id = _clean_int_id(device_id)
        if dev_id is None:
            raise Exception("كود الجهاز غير صالح!")

        cond_val = device_condition if device_condition in ("جديد", "مستعمل") else "مستعمل"
        box_val = bool(has_box)
        bat_val = int(battery) if (battery is not None and str(battery).replace('.', '', 1).isdigit()) else 0

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT buy_price, invoice_id, supplier_id, buy_date FROM devices WHERE id = %s FOR UPDATE;", (dev_id,))
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
                """, (category, model, storage, ram, bat_val, imei, buy_price, cond_val, box_val, notes, dev_id))

                cur.execute("UPDATE sales SET net_profit = sell_price - %s WHERE device_id = %s;", (buy_price, dev_id))
                conn.commit()

    def soft_delete_device(self, device_id, user_id=None):
        """
        تحويل حالة الجهاز لمحذوف وتعديل المديونية والمدفوع والخرج والتقرير المالي تلقائياً:
        مثال: لو فاتورة إجماليها 100 والجهاز بـ 50 والمدفوع منها 70:
        - يتخصم 50 من الإجمالي ليصبح الإجمالي = 50
        - ويتخصم 50 من المدفوع ليصبح المدفوع = 20
        - ويصبح المتبقي = 50 - 20 = 30
        """
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

                # 1. تحويل حالة الجهاز إلى محذوف
                cur.execute("UPDATE devices SET is_deleted = TRUE, is_sold = FALSE WHERE id = %s;", (dev_id,))

                # 2. الخصم من فاتورة ومديونية المورد (من الإجمالي ومن المدفوع)
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
                        new_paid = max(0.0, paid - buy_price)
                        if new_paid > new_tot:
                            new_paid = new_tot
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

                # 3. خصم تأثير البيع والخرج والتحصيلات إن كان الجهاز مباعاً
                cur.execute("SELECT id FROM sales WHERE device_id = %s;", (dev_id,))
                sale = cur.fetchone()
                if sale:
                    sale_id = sale['id']
                    cur.execute("DELETE FROM customer_payments WHERE sale_id = %s;", (sale_id,))
                    cur.execute("DELETE FROM sales WHERE id = %s;", (sale_id,))

                conn.commit()

    def delete_device(self, device_id):
        dev_id = _clean_int_id(device_id)
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM devices WHERE id = %s AND is_sold = FALSE;", (dev_id,))
                conn.commit()

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
                        WHERE d.is_sold = FALSE AND d.is_deleted = FALSE
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
                    cur.execute("SELECT COUNT(*) as total_devices, COALESCE(SUM(buy_price), 0) as total_capital FROM devices WHERE is_sold = FALSE AND is_deleted = FALSE;")
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
                        WHERE d.is_deleted = FALSE
                    """

                    if search_by == 'ID':
                        sql = base_select + " AND CAST(d.id AS TEXT) = %s ORDER BY d.is_sold ASC, d.id DESC LIMIT 1;"
                        cur.execute(sql, (q_id,))
                        return cur.fetchone()

                    elif search_by == 'SERIAL':
                        sql_exact = base_select + " AND LOWER(TRIM(d.imei_serial)) = LOWER(%s) ORDER BY d.is_sold ASC, d.id DESC LIMIT 1;"
                        cur.execute(sql_exact, (q_str,))
                        res = cur.fetchone()
                        if res:
                            return res
                        sql_like = base_select + " AND d.imei_serial ILIKE %s ORDER BY d.is_sold ASC, d.id DESC LIMIT 1;"
                        cur.execute(sql_like, (f"%{q_str}%",))
                        return cur.fetchone()

                    elif search_by == 'NAME':
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

    def process_sale(self, device_id, sell_price, customer_name, customer_phone, cash_received, notes, user_id):
        dev_id = _clean_int_id(device_id)
        if dev_id is None:
            raise Exception("كود الجهاز غير صالح!")

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT buy_price, is_deleted FROM devices WHERE id = %s AND is_sold = FALSE FOR UPDATE", (dev_id,))
                dev = cur.fetchone()
                if not dev or dev.get('is_deleted'):
                    raise Exception("الجهاز غير متاح للبيع أو تم حذفه!")

                buy_price = float(dev['buy_price'])
                sell_val = float(sell_price)
                if sell_val < buy_price:
                    raise Exception(f"لا يمكن البيع بأقل من سعر الشراء ({buy_price:,.2f} ج.م)!")

                cash = float(cash_received or 0)
                if cash > sell_val:
                    raise Exception("المبلغ المدفوع أكبر من سعر البيع!")

                rem = max(0.0, sell_val - cash)
                net_profit = sell_val - buy_price

                cur.execute("""
                    INSERT INTO sales (device_id, sell_price, customer_name, customer_phone, cash_received, remaining_balance, net_profit, notes, created_by_user_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
                """, (dev_id, sell_val, customer_name or 'عميل نقدي', customer_phone or '', cash, rem, net_profit, notes or '', user_id))
                sale_id = cur.fetchone()['id']

                if cash > 0:
                    cur.execute("""
                        INSERT INTO customer_payments (sale_id, payment_amount, created_by_user_id)
                        VALUES (%s, %s, %s);
                    """, (sale_id, cash, user_id))

                cur.execute("UPDATE devices SET is_sold = TRUE WHERE id = %s;", (dev_id,))
                conn.commit()
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

    def get_customer_debts(self):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT s.id as sale_id, d.id as device_id, d.model, s.customer_name, s.customer_phone,
                               s.sell_price, s.cash_received, s.remaining_balance,
                               TO_CHAR(s.sell_date, 'YYYY-MM-DD HH24:MI') as sell_date_formatted
                        FROM sales s
                        JOIN devices d ON s.device_id = d.id
                        WHERE s.remaining_balance > 0 AND d.is_deleted = FALSE
                        ORDER BY s.id DESC;
                    """)
                    return cur.fetchall()
        except Exception:
            return []

    def pay_customer_debt(self, sale_id, amount, user_id):
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
                cur.execute("INSERT INTO customer_payments (sale_id, payment_amount, created_by_user_id) VALUES (%s, %s, %s);", (s_id, amount, user_id))
                conn.commit()

    def get_supplier_invoices(self, search_query=None, status_filter='UNPAID', search_by='ALL'):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT i.id, i.supplier_id, COALESCE(s.name, 'غير محدد') as supplier_name,
                               COALESCE(s.supplier_type, 'تاجر') as supplier_type,
                               TO_CHAR(i.invoice_date, 'YYYY-MM-DD') as inv_date,
                               i.total_amount, i.paid_amount, i.remaining_amount, i.status
                        FROM supplier_invoices i
                        LEFT JOIN suppliers s ON i.supplier_id = s.id
                        WHERE i.total_amount > 0
                    """
                    params = []
                    if status_filter == 'UNPAID':
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
                    return cur.fetchall()
        except Exception:
            return []

    def get_supplier_invoice_payments(self, invoice_id):
        inv_id = _clean_int_id(invoice_id)
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT sp.id, sp.payment_amount, 
                               TO_CHAR(sp.payment_date, 'YYYY-MM-DD HH24:MI') as payment_date_formatted,
                               COALESCE(u.full_name, u.username, 'مستخدم النظام') as user_name
                        FROM supplier_payments sp
                        LEFT JOIN users u ON sp.created_by_user_id = u.id
                        WHERE sp.invoice_id = %s
                        ORDER BY sp.id ASC;
                    """, (inv_id,))
                    return cur.fetchall()
        except Exception:
            return []

    def get_invoice_devices(self, invoice_id):
        inv_id = _clean_int_id(invoice_id)
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT d.id, d.category, d.model, d.imei_serial, d.buy_price,
                               COALESCE(d.device_condition, 'مستعمل') as device_condition,
                               COALESCE(d.has_box, TRUE) as has_box,
                               COALESCE(d.notes, '') as notes
                        FROM devices d
                        WHERE d.invoice_id = %s AND d.is_deleted = FALSE
                        ORDER BY d.id DESC;
                    """, (inv_id,))
                    devs = cur.fetchall()
                    if not devs:
                        cur.execute("""
                            SELECT d.id, d.category, d.model, d.imei_serial, d.buy_price,
                                   COALESCE(d.device_condition, 'مستعمل') as device_condition,
                                   COALESCE(d.has_box, TRUE) as has_box,
                                   COALESCE(d.notes, '') as notes
                            FROM devices d
                            JOIN supplier_invoices i ON d.supplier_id = i.supplier_id AND DATE(d.buy_date) = i.invoice_date
                            WHERE i.id = %s AND d.is_deleted = FALSE
                            ORDER BY d.id DESC;
                        """, (inv_id,))
                        devs = cur.fetchall()
                    return devs
        except Exception:
            return []

    def pay_supplier_debt(self, invoice_id, amount, user_id):
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
                    INSERT INTO supplier_payments (invoice_id, supplier_id, payment_amount, created_by_user_id)
                    VALUES (%s, %s, %s, %s);
                """, (inv_id, inv['supplier_id'], amount, user_id))

                conn.commit()

    def add_capital_injection(self, amount, notes, user_id):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO capital_transactions (amount, transaction_type, notes, created_by_user_id)
                    VALUES (%s, 'INJECTION', %s, %s);
                """, (amount, notes, user_id))
                conn.commit()

    def get_financial_summary(self):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COALESCE(SUM(buy_price), 0) as inv_cost FROM devices WHERE is_sold = FALSE AND is_deleted = FALSE;")
                    inv_cost = float(cur.fetchone()['inv_cost'])

                    cur.execute("SELECT COALESCE(SUM(remaining_balance), 0) as cust_debts FROM sales s JOIN devices d ON s.device_id = d.id WHERE d.is_deleted = FALSE;")
                    cust_debts = float(cur.fetchone()['cust_debts'])

                    cur.execute("SELECT COALESCE(SUM(remaining_amount), 0) as supp_debts FROM supplier_invoices WHERE remaining_amount > 0;")
                    supp_debts = float(cur.fetchone()['supp_debts'])

                    cur.execute("SELECT COALESCE(SUM(cash_received), 0) as total_sales_cash FROM sales s JOIN devices d ON s.device_id = d.id WHERE d.is_deleted = FALSE;")
                    total_sales_cash = float(cur.fetchone()['total_sales_cash'])

                    cur.execute("SELECT COALESCE(SUM(paid_amount), 0) as supp_payments FROM supplier_invoices;")
                    supp_payments = float(cur.fetchone()['supp_payments'])

                    cur.execute("SELECT COALESCE(SUM(amount), 0) as injections FROM capital_transactions WHERE transaction_type = 'INJECTION';")
                    injections = float(cur.fetchone()['injections'])

                    cur.execute("""
                        SELECT COALESCE(SUM(net_profit), 0) as m_profit 
                        FROM sales s JOIN devices d ON s.device_id = d.id
                        WHERE d.is_deleted = FALSE AND TO_CHAR(s.sell_date, 'YYYY-MM') = TO_CHAR(CURRENT_DATE, 'YYYY-MM');
                    """)
                    m_profit = float(cur.fetchone()['m_profit'])

                    current_liquidity = (injections + total_sales_cash) - supp_payments
                    total_capital = current_liquidity + inv_cost

                    return {
                        'inventory_cost': inv_cost,
                        'customer_debts': cust_debts,
                        'supplier_debts': supp_debts,
                        'current_liquidity': current_liquidity,
                        'total_capital': total_capital,
                        'monthly_profit': m_profit
                    }
        except Exception as e:
            print(f"Error financial summary: {e}")
            return {
                'inventory_cost': 0, 'customer_debts': 0, 'supplier_debts': 0,
                'current_liquidity': 0, 'total_capital': 0, 'monthly_profit': 0
            }

    def get_sales_report_advanced(self, date_from, date_to):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT s.id as sale_id, d.id as device_id, d.model, d.imei_serial, d.buy_price,
                               COALESCE(d.device_condition, 'مستعمل') as device_condition,
                               COALESCE(d.has_box, TRUE) as has_box,
                               s.sell_price, s.cash_received, s.remaining_balance, s.net_profit, s.customer_name,
                               COALESCE(s.notes, '') as sale_notes,
                               TO_CHAR(s.sell_date, 'YYYY-MM-DD HH24:MI') as sell_date_formatted,
                               COALESCE(u.full_name, u.username, 'بائع النظام') as seller_name
                        FROM sales s
                        JOIN devices d ON s.device_id = d.id
                        LEFT JOIN users u ON s.created_by_user_id = u.id
                        WHERE d.is_deleted = FALSE 
                          AND DATE(s.sell_date) >= %s AND DATE(s.sell_date) <= %s
                        ORDER BY s.id DESC;
                    """, (date_from, date_to))
                    return cur.fetchall()
        except Exception:
            return []

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
            print(f"Error fetching device details: {e}")
            return None
