import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt

class DatabaseManager:
    def __init__(self, host="192.168.1.10", database="mobile_store_db_v1", user="postgres", password="password", port=5432):
        self.conn_params = {
            "host": host, "database": database,
            "user": user, "password": password, "port": port
        }

    def get_connection(self):
        return psycopg2.connect(**self.conn_params, cursor_factory=RealDictCursor)

    def authenticate_user(self, username, password):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(%s) AND is_active = TRUE", (username.strip(),))
                    user = cur.fetchone()
                    if user:
                        stored_pass = str(user['password_hash']).strip()
                        input_pass = str(password).strip()
                        if stored_pass == input_pass or stored_pass == str(password):
                            return user
            return None
        except Exception as e:
            print(f"Error Authenticating: {e}")
            return None

    def get_all_users(self):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id, username, full_name, permissions FROM users WHERE is_active = TRUE ORDER BY id ASC")
                    return cur.fetchall()
        except Exception as e:
            return []

    def get_all_suppliers(self):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM suppliers ORDER BY name ASC;")
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

    def add_device(self, category, model, storage, ram, battery, accessories, imei, buy_price, supplier_id, notes, user_id):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO devices (category, model, storage, ram, battery_health, accessories, imei_serial, buy_price, supplier_id, notes, created_by_user_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
                """, (category, model, storage, ram, battery, accessories, imei, buy_price, supplier_id, notes, user_id))
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

    def get_available_inventory(self, search_query=None):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT d.id, d.category, d.model, d.storage, d.ram, d.battery_health, 
                               d.imei_serial, d.buy_price, COALESCE(s.name, 'غير محدد') as supplier_name, 
                               TO_CHAR(d.buy_date, 'YYYY-MM-DD HH24:MI') as buy_date_formatted
                        FROM devices d
                        LEFT JOIN suppliers s ON d.supplier_id = s.id
                        WHERE d.is_sold = FALSE
                    """
                    params = []
                    if search_query:
                        query += " AND (d.model ILIKE %s OR d.imei_serial ILIKE %s OR d.category ILIKE %s)"
                        params.extend([f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"])
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
                        SELECT d.*, COALESCE(s.name, 'غير محدد') as supplier_name,
                               sl.id as sale_id, sl.sell_price, sl.customer_name, sl.customer_phone,
                               sl.cash_received, sl.remaining_balance
                        FROM devices d
                        LEFT JOIN suppliers s ON d.supplier_id = s.id
                        LEFT JOIN sales sl ON d.id = sl.device_id
                        WHERE d.imei_serial = %s OR CAST(d.id AS TEXT) = %s;
                    """, (query, query))
                    return cur.fetchone()
        except Exception as e:
            return None

    def process_sale(self, device_id, sell_price, customer_name, customer_phone, cash_received, notes, user_id):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT buy_price FROM devices WHERE id = %s AND is_sold = FALSE FOR UPDATE", (device_id,))
                dev = cur.fetchone()
                if not dev: raise Exception("الجهاز غير متاح للبيع أو غير موجود!")

                buy_price = float(dev['buy_price'])
                sell_val = float(sell_price)
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
                # التحقق من البيانات الحالية لتحديث الحساب بشكل دقيق دون مسح الفاتورة
                cur.execute("SELECT sell_price, cash_received FROM sales WHERE id = %s FOR UPDATE;", (sale_id,))
                sale = cur.fetchone()
                if not sale: raise Exception("فاتورة البيع غير موجودة!")

                new_cash_received = float(sale['cash_received']) + float(amount)
                new_remaining = max(0.0, float(sale['sell_price']) - new_cash_received)
                new_status = 'PAID' if new_remaining <= 0 else 'PARTIAL'

                cur.execute("INSERT INTO customer_payments (sale_id, payment_amount, received_by_user_id) VALUES (%s, %s, %s);", (sale_id, amount, user_id))
                cur.execute("""
                    UPDATE sales 
                    SET cash_received = %s, 
                        remaining_balance = %s,
                        payment_status = %s
                    WHERE id = %s;
                """, (new_cash_received, new_remaining, new_status, sale_id))
                conn.commit()

    def get_supplier_invoices(self, search_query=None):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT si.id, s.name as supplier_name, TO_CHAR(si.invoice_date, 'YYYY-MM-DD') as inv_date,
                               si.total_amount, si.paid_amount, si.remaining_amount, si.status
                        FROM supplier_invoices si
                        JOIN suppliers s ON si.supplier_id = s.id
                    """
                    params = []
                    if search_query:
                        query += " WHERE (s.name ILIKE %s OR CAST(si.id AS TEXT) = %s)"
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
                cur.execute("SELECT supplier_id, total_amount, paid_amount FROM supplier_invoices WHERE id = %s FOR UPDATE;", (invoice_id,))
                inv = cur.fetchone()
                if not inv: raise Exception("الفاتورة غير موجودة")

                new_paid = float(inv['paid_amount']) + float(amount)
                new_remaining = max(0.0, float(inv['total_amount']) - new_paid)
                new_status = 'PAID' if new_remaining <= 0 else 'PARTIAL'
                
                cur.execute("INSERT INTO supplier_payments (supplier_id, payment_amount, received_by_user_id) VALUES (%s, %s, %s);", (inv['supplier_id'], amount, user_id))
                cur.execute("""
                    UPDATE supplier_invoices 
                    SET paid_amount = %s,
                        remaining_amount = %s,
                        status = %s
                    WHERE id = %s;
                """, (new_paid, new_remaining, new_status, invoice_id))
                conn.commit()

    def get_monthly_sales_report(self, month, year):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT d.id as device_id, d.model, d.imei_serial, d.buy_price,
                               sl.sell_price, sl.cash_received, sl.remaining_balance,
                               sl.net_profit, sl.customer_name,
                               TO_CHAR(sl.sell_date, 'YYYY-MM-DD HH24:MI') as sell_date_formatted,
                               u.full_name as seller_name
                        FROM sales sl
                        JOIN devices d ON sl.device_id = d.id
                        JOIN users u ON sl.sold_by_user_id = u.id
                        WHERE EXTRACT(MONTH FROM sl.sell_date) = %s 
                          AND EXTRACT(YEAR FROM sl.sell_date) = %s
                        ORDER BY sl.sell_date DESC;
                    """, (month, year))
                    return cur.fetchall()
        except Exception as e:
            return []