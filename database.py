import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt
import json
import os

CONFIG_FILE = "config.json"

def load_db_config():
    default_config = {
        "host": "localhost",
        "database": "mobile_store_db_v1",
        "user": "postgres",
        "password": "yousef1312012",
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
                    cur.execute("SELECT id, username, full_name, permissions, is_active FROM users ORDER BY id ASC")
                    return cur.fetchall()
        except Exception as e:
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

    def update_user_permissions(self, user_id, permissions):
        perm_json = json.dumps(permissions)
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE users SET permissions = %s WHERE id = %s;", (perm_json, user_id))
                conn.commit()

    def reset_user_password(self, user_id, new_password):
        hashed = self.hash_password(new_password)
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE users SET password_hash = %s WHERE id = %s;", (hashed, user_id))
                conn.commit()

    def delete_user(self, user_id):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE users SET is_active = FALSE WHERE id = %s;", (user_id,))
                conn.commit()

    def get_all_suppliers(self):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM suppliers WHERE is_active = TRUE ORDER BY name ASC;")
                    return cur.fetchall()
        except Exception as e:
            return []

    def add_supplier(self, name, phone):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO suppliers (name, phone) VALUES (%s, %s) RETURNING id;", (name, phone))
                supp_id = cur.fetchone()['id']
                conn.commit()
                return supp_id

    def update_supplier(self, supp_id, name, phone):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE suppliers SET name = %s, phone = %s WHERE id = %s;", (name, phone, supp_id))
                conn.commit()

    def delete_supplier(self, supp_id):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE suppliers SET is_active = FALSE WHERE id = %s;", (supp_id,))
                conn.commit()

    def add_device(self, category, model, storage, ram, battery, accessories, imei, buy_price, supplier_id, notes, user_id):
        ram_val = ram if ram else "لا يوجد"
        bat_val = int(battery) if (battery and str(battery).isdigit()) else 0
        
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO devices (category, model, storage, ram, battery_health, accessories, imei_serial, buy_price, supplier_id, notes, created_by_user_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
                """, (category, model, storage, ram_val, bat_val, accessories, imei, buy_price, supplier_id, notes, user_id))
                device_id = cur.fetchone()['id']

                if supplier_id:
                    cur.execute("SELECT id FROM supplier_invoices WHERE supplier_id = %s AND invoice_date = CURRENT_DATE;", (supplier_id,))
                    inv = cur.fetchone()
                    if inv:
                        cur.execute("UPDATE supplier_invoices SET total_amount = total_amount + %s, remaining_amount = remaining_amount + %s WHERE id = %s;", (buy_price, buy_price, inv['id']))
                    else:
                        cur.execute("INSERT INTO supplier_invoices (supplier_id, total_amount, paid_amount, remaining_amount, status, invoice_date, created_by_user_id) VALUES (%s, %s, 0, %s, 'UNPAID', CURRENT_DATE, %s);", (supplier_id, buy_price, buy_price, user_id))

                conn.commit()
                return device_id

    def update_device(self, device_id, category, model, storage, ram, battery, imei, buy_price):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE devices 
                    SET category = %s, model = %s, storage = %s, ram = %s, battery_health = %s, imei_serial = %s, buy_price = %s
                    WHERE id = %s;
                """, (category, model, storage, ram, battery, imei, buy_price, device_id))
                conn.commit()

    def delete_device(self, device_id):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM devices WHERE id = %s AND is_sold = FALSE;", (device_id,))
                conn.commit()

    def get_available_inventory(self, search_query=None):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT d.id, d.category, d.model, d.storage, d.ram, d.battery_health, 
                               d.imei_serial, d.buy_price, COALESCE(s.name, 'غير محدد / مباشر') as supplier_name, 
                               TO_CHAR(d.buy_date, 'YYYY-MM-DD HH24:MI') as buy_date_formatted
                        FROM devices d
                        LEFT JOIN suppliers s ON d.supplier_id = s.id
                        WHERE d.is_sold = FALSE
                    """
                    params = []
                    if search_query:
                        query += " AND (d.model ILIKE %s OR d.imei_serial ILIKE %s OR d.category ILIKE %s OR CAST(d.id AS TEXT) = %s)"
                        params.extend([f"%{search_query}%", f"%{search_query}%", f"%{search_query}%", search_query])
                    query += " ORDER BY d.id DESC;"
                    cur.execute(query, params)
                    return cur.fetchall()
        except Exception as e:
            return []

    def get_capital_statistics(self):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) as total_devices, COALESCE(SUM(buy_price), 0) as total_capital FROM devices WHERE is_sold = FALSE;")
                    return cur.fetchone()
        except Exception as e:
            return {'total_devices': 0, 'total_capital': 0}

    def search_device_by_imei_or_id(self, query):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT d.*, COALESCE(s.name, 'غير محدد / مباشر') as supplier_name,
                               TO_CHAR(d.buy_date, 'YYYY-MM-DD HH24:MI') as buy_date_formatted,
                               sl.id as sale_id, sl.sell_price, sl.customer_name, sl.customer_phone,
                               sl.cash_received, sl.remaining_balance
                        FROM devices d
                        LEFT JOIN suppliers s ON d.supplier_id = s.id
                        LEFT JOIN sales sl ON d.id = sl.device_id
                        WHERE d.imei_serial ILIKE %s OR CAST(d.id AS TEXT) = %s OR d.model ILIKE %s;
                    """, (f"%{query}%", query, f"%{query}%"))
                    return cur.fetchone()
        except Exception as e:
            return None

    def process_sale(self, device_id, sell_price, customer_name, customer_phone, cash_received, notes, user_id):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT buy_price FROM devices WHERE id = %s AND is_sold = FALSE FOR UPDATE", (device_id,))
                dev = cur.fetchone()
                if not dev: raise Exception("الجهاز غير متاح للبيع!")

                buy_price = float(dev['buy_price'])
                sell_val = float(sell_price)
                if sell_val < buy_price:
                    raise Exception(f"لا يمكن البيع بأقل من سعر الشراء ({buy_price:,.2f} ج.م)!")

                cash_val = float(cash_received)
                remaining = max(0.0, sell_val - cash_val)
                net_profit = sell_val - buy_price
                status = 'PAID' if remaining <= 0 else 'PARTIAL'

                cur.execute("UPDATE devices SET is_sold = TRUE WHERE id = %s", (device_id,))
                cur.execute("""
                    INSERT INTO sales (device_id, sell_price, customer_name, customer_phone, cash_received, remaining_balance, payment_status, net_profit, notes, sold_by_user_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
                """, (device_id, sell_val, customer_name, customer_phone, cash_val, remaining, status, net_profit, notes, user_id))
                sale_id = cur.fetchone()['id']

                if cash_val > 0:
                    cur.execute("INSERT INTO customer_payments (sale_id, payment_amount, received_by_user_id) VALUES (%s, %s, %s);", (sale_id, cash_val, user_id))
                conn.commit()
                return sale_id

    def process_return(self, device_id, user_id):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM sales WHERE device_id = %s;", (device_id,))
                cur.execute("UPDATE devices SET is_sold = FALSE WHERE id = %s;", (device_id,))
                conn.commit()

    def get_customer_debts(self, search_query=None):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT sl.id as sale_id, d.id as device_id, d.model, sl.customer_name, sl.customer_phone,
                               TO_CHAR(sl.sell_date, 'YYYY-MM-DD HH24:MI') as sell_date_formatted,
                               sl.sell_price, sl.cash_received, sl.remaining_balance
                        FROM sales sl
                        JOIN devices d ON sl.device_id = d.id
                        WHERE sl.remaining_balance > 0
                    """
                    params = []
                    if search_query:
                        query += " AND (sl.customer_name ILIKE %s OR sl.customer_phone ILIKE %s OR d.model ILIKE %s OR CAST(sl.id AS TEXT) = %s)"
                        params.extend([f"%{search_query}%", f"%{search_query}%", f"%{search_query}%", search_query])
                    query += " ORDER BY sl.sell_date DESC;"
                    cur.execute(query, params)
                    return cur.fetchall()
        except Exception as e:
            return []

    def pay_customer_debt(self, sale_id, amount, user_id):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT sell_price, cash_received, remaining_balance FROM sales WHERE id = %s FOR UPDATE;", (sale_id,))
                sale = cur.fetchone()
                if not sale: raise Exception("الفاتورة غير موجودة")

                rem = float(sale['remaining_balance'])
                if float(amount) > rem:
                    raise Exception(f"المبلغ المدفوع أسرع/أكبر من المتبقي ({rem:,.2f} ج.م)!")

                new_cash_received = float(sale['cash_received']) + float(amount)
                new_remaining = max(0.0, float(sale['sell_price']) - new_cash_received)
                new_status = 'PAID' if new_remaining <= 0 else 'PARTIAL'

                cur.execute("INSERT INTO customer_payments (sale_id, payment_amount, received_by_user_id) VALUES (%s, %s, %s);", (sale_id, amount, user_id))
                cur.execute("""
                    UPDATE sales 
                    SET cash_received = %s, remaining_balance = %s, payment_status = %s
                    WHERE id = %s;
                """, (new_cash_received, new_remaining, new_status, sale_id))
                conn.commit()

    def get_supplier_invoices(self, search_query=None, filter_status="UNPAID"):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT si.id, s.name as supplier_name, TO_CHAR(si.invoice_date, 'YYYY-MM-DD') as inv_date,
                               si.total_amount, si.paid_amount, si.remaining_amount, si.status
                        FROM supplier_invoices si
                        JOIN suppliers s ON si.supplier_id = s.id
                        WHERE 1=1
                    """
                    params = []
                    if filter_status == "UNPAID":
                        query += " AND si.remaining_amount > 0"
                    elif filter_status == "PAID":
                        query += " AND si.remaining_amount <= 0"
                    
                    if search_query:
                        query += " AND (s.name ILIKE %s OR CAST(si.id AS TEXT) = %s)"
                        params.extend([f"%{search_query}%", search_query])

                    query += " ORDER BY si.invoice_date DESC;"
                    cur.execute(query, params)
                    return cur.fetchall()
        except Exception as e:
            return []

    def get_invoice_devices(self, invoice_id):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT d.id, d.category, d.model, d.imei_serial, d.buy_price
                        FROM devices d
                        JOIN supplier_invoices si ON d.supplier_id = si.supplier_id 
                        WHERE si.id = %s AND DATE(d.buy_date) = si.invoice_date;
                    """, (invoice_id,))
                    return cur.fetchall()
        except Exception as e:
            return []

    def pay_supplier_debt(self, invoice_id, amount, user_id):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT supplier_id, total_amount, paid_amount, remaining_amount FROM supplier_invoices WHERE id = %s FOR UPDATE;", (invoice_id,))
                inv = cur.fetchone()
                if not inv: raise Exception("الفاتورة غير موجودة")

                rem = float(inv['remaining_amount'])
                if float(amount) > rem:
                    raise Exception(f"لا يمكن تسديد مبلغ أكبر من المبلغ المتبقي للفاتورة ({rem:,.2f} ج.م)!")

                new_paid = float(inv['paid_amount']) + float(amount)
                new_remaining = max(0.0, float(inv['total_amount']) - new_paid)
                new_status = 'PAID' if new_remaining <= 0 else 'PARTIAL'

                cur.execute("INSERT INTO supplier_payments (supplier_id, payment_amount, received_by_user_id) VALUES (%s, %s, %s);", (inv['supplier_id'], amount, user_id))
                cur.execute("""
                    UPDATE supplier_invoices 
                    SET paid_amount = %s, remaining_amount = %s, status = %s
                    WHERE id = %s;
                """, (new_paid, new_remaining, new_status, invoice_id))
                conn.commit()

    def get_sales_report_advanced(self, start_date=None, end_date=None):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT d.id as device_id, d.category, d.model, d.imei_serial, d.buy_price,
                               sl.sell_price, sl.cash_received, sl.remaining_balance,
                               sl.net_profit, sl.customer_name,
                               TO_CHAR(sl.sell_date, 'YYYY-MM-DD HH24:MI') as sell_date_formatted,
                               u.full_name as seller_name
                        FROM sales sl
                        JOIN devices d ON sl.device_id = d.id
                        JOIN users u ON sl.sold_by_user_id = u.id
                        WHERE 1=1
                    """
                    params = []
                    if start_date and end_date:
                        query += " AND DATE(sl.sell_date) BETWEEN %s AND %s"
                        params.extend([start_date, end_date])
                    query += " ORDER BY sl.sell_date DESC;"
                    cur.execute(query, params)
                    return cur.fetchall()
        except Exception as e:
            return []

    def add_capital_injection(self, amount, notes, user_id):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO capital_transactions (amount, notes, created_by_user_id)
                    VALUES (%s, %s, %s) RETURNING id;
                """, (amount, notes, user_id))
                conn.commit()

    def get_financial_summary(self):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COALESCE(SUM(amount), 0) as val FROM capital_transactions;")
                    injected_cap = float(cur.fetchone()['val'])

                    cur.execute("SELECT COALESCE(SUM(payment_amount), 0) as val FROM customer_payments;")
                    collected_cust = float(cur.fetchone()['val'])

                    cur.execute("SELECT COALESCE(SUM(payment_amount), 0) as val FROM supplier_payments;")
                    supplier_paid = float(cur.fetchone()['val'])

                    current_liquidity = injected_cap + collected_cust - supplier_paid

                    cur.execute("SELECT COALESCE(SUM(buy_price), 0) as val FROM devices WHERE is_sold = FALSE;")
                    inv_cost = float(cur.fetchone()['val'])

                    total_capital = current_liquidity + inv_cost

                    cur.execute("SELECT COALESCE(SUM(remaining_balance), 0) as val FROM sales WHERE remaining_balance > 0;")
                    customer_debts = float(cur.fetchone()['val'])

                    cur.execute("SELECT COALESCE(SUM(remaining_amount), 0) as val FROM supplier_invoices WHERE remaining_amount > 0;")
                    supplier_debts = float(cur.fetchone()['val'])

                    cur.execute("""
                        SELECT COALESCE(SUM(net_profit), 0) as val 
                        FROM sales 
                        WHERE EXTRACT(MONTH FROM sell_date) = EXTRACT(MONTH FROM CURRENT_DATE)
                          AND EXTRACT(YEAR FROM sell_date) = EXTRACT(YEAR FROM CURRENT_DATE);
                    """)
                    monthly_profit = float(cur.fetchone()['val'])

                    return {
                        'injected_capital': injected_cap,
                        'collected_customers': collected_cust,
                        'paid_suppliers': supplier_paid,
                        'current_liquidity': current_liquidity,
                        'inventory_cost': inv_cost,
                        'total_capital': total_capital,
                        'customer_debts': customer_debts,
                        'supplier_debts': supplier_debts,
                        'monthly_profit': monthly_profit
                    }
        except Exception as e:
            print(f"Error calculating financial summary: {e}")
            return {
                'injected_capital': 0.0, 'collected_customers': 0.0, 'paid_suppliers': 0.0,
                'current_liquidity': 0.0, 'inventory_cost': 0.0, 'total_capital': 0.0,
                'customer_debts': 0.0, 'supplier_debts': 0.0, 'monthly_profit': 0.0
            }

    def get_device_full_details(self, device_id):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT d.*, 
                               COALESCE(s.name, 'غير محدد / شراء مباشر') as supplier_name,
                               COALESCE(s.phone, '-') as supplier_phone,
                               COALESCE(u.full_name, 'غير معروف') as created_by_name,
                               TO_CHAR(d.buy_date, 'YYYY-MM-DD HH24:MI') as buy_date_formatted
                        FROM devices d
                        LEFT JOIN suppliers s ON d.supplier_id = s.id
                        LEFT JOIN users u ON d.created_by_user_id = u.id
                        WHERE d.id = %s;
                    """, (device_id,))
                    dev = cur.fetchone()
                    if not dev:
                        return None

                    sale_info = None
                    cust_payments = []
                    if dev['is_sold']:
                        cur.execute("""
                            SELECT sl.*, COALESCE(u.full_name, 'غير معروف') as seller_name,
                                   TO_CHAR(sl.sell_date, 'YYYY-MM-DD HH24:MI') as sell_date_formatted
                            FROM sales sl
                            LEFT JOIN users u ON sl.sold_by_user_id = u.id
                            WHERE sl.device_id = %s;
                        """, (device_id,))
                        sale_info = cur.fetchone()

                        if sale_info:
                            cur.execute("""
                                SELECT cp.*, COALESCE(u.full_name, 'غير معروف') as receiver_name,
                                       TO_CHAR(cp.payment_date, 'YYYY-MM-DD HH24:MI') as payment_date_formatted
                                FROM customer_payments cp
                                LEFT JOIN users u ON cp.received_by_user_id = u.id
                                WHERE cp.sale_id = %s
                                ORDER BY cp.payment_date ASC;
                            """, (sale_info['id'],))
                            cust_payments = cur.fetchall()

                    return {
                        'device': dev,
                        'sale': sale_info,
                        'customer_payments': cust_payments
                    }
        except Exception as e:
            print(f"Error fetching device details: {e}")
            return None