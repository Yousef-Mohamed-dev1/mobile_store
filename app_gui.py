import tkinter as tk
from tkinter import ttk, messagebox
from database import DatabaseManager
from invoice_generator import generate_invoice_image
from datetime import datetime
from PIL import Image, ImageTk
import os

def fmt_curr(val):
    try:
        f = float(val)
        return f"{f:,.2f} ج.م"
    except (ValueError, TypeError):
        return "0.00 ج.م"

def fmt_num(val):
    try:
        f = float(val)
        if f.is_integer():
            return f"{int(f):,}"
        return f"{f:,.2f}"
    except (ValueError, TypeError):
        return str(val)

class MasterMobileApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("نظام مركز هشام كيوان - إدارة الهواتف")
        self.geometry("1300x820")
        
        self.logo_top = None
        self.logo_login = None
        self.load_logo_icon()

        self.is_dark_mode = True
        self.apply_theme_colors()

        self.configure(bg=self.COLOR_BG)
        self.db = DatabaseManager()
        self.current_user = None
        self.current_view_func = None

        self.vcmd_num = (self.register(self.validate_numeric), '%P')

        self.setup_styles()
        self.withdraw()
        self.show_login_dialog()

    def validate_numeric(self, P):
        if P == "" or P.replace('.', '', 1).isdigit():
            return True
        return False

    def load_logo_icon(self):
        if os.path.exists("logo.png"):
            try:
                img = Image.open("logo.png")
                img_top = img.copy()
                img_top.thumbnail((40, 40), Image.Resampling.LANCZOS)
                self.logo_top = ImageTk.PhotoImage(img_top)

                img_login = img.copy()
                img_login.thumbnail((90, 90), Image.Resampling.LANCZOS)
                self.logo_login = ImageTk.PhotoImage(img_login)

                self.iconphoto(True, self.logo_top)
            except Exception as e:
                print(f"Notice: Logo load: {e}")

    def has_permission(self, perm_key):
        if not self.current_user:
            return False
        perms = self.current_user.get('permissions', {})
        if isinstance(perms, str):
            import json
            try: perms = json.loads(perms)
            except: perms = {}
        return perms.get(perm_key, True)

    def apply_theme_colors(self):
        if self.is_dark_mode:
            self.COLOR_BG = "#0f172a"
            self.COLOR_CARD = "#1e293b"
            self.COLOR_ACCENT = "#10b981"
            self.COLOR_BLUE = "#38bdf8"
            self.COLOR_TEXT = "#f8fafc"
            self.COLOR_MUTED = "#94a3b8"
            self.COLOR_DANGER = "#ef4444"
            self.COLOR_ENTRY_BG = "#334155"
            self.COLOR_TOPBAR = "#020617"
            self.COLOR_TREE_BG = "#1e293b"
            self.COLOR_TREE_ALT = "#0f172a"
        else:
            self.COLOR_BG = "#f1f5f9"
            self.COLOR_CARD = "#ffffff"
            self.COLOR_ACCENT = "#059669"
            self.COLOR_BLUE = "#0284c7"
            self.COLOR_TEXT = "#0f172a"
            self.COLOR_MUTED = "#64748b"
            self.COLOR_DANGER = "#dc2626"
            self.COLOR_ENTRY_BG = "#e2e8f0"
            self.COLOR_TOPBAR = "#cbd5e1"
            self.COLOR_TREE_BG = "#ffffff"
            self.COLOR_TREE_ALT = "#f8fafc"

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("Treeview", 
                             background=self.COLOR_TREE_BG, 
                             foreground=self.COLOR_TEXT, 
                             rowheight=38, 
                             fieldbackground=self.COLOR_TREE_BG,
                             font=("Segoe UI", 10))
        self.style.map("Treeview", background=[('selected', self.COLOR_BLUE)])
        self.style.configure("Treeview.Heading", 
                             background=self.COLOR_TOPBAR, 
                             foreground=self.COLOR_BLUE, 
                             font=("Segoe UI", 11, "bold"))

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme_colors()
        self.configure(bg=self.COLOR_BG)
        self.setup_styles()
        current_func = self.current_view_func
        self.build_main_ui(keep_view=True)
        if current_func:
            current_func()

    def show_login_dialog(self):
        login_win = tk.Toplevel(self)
        login_win.title("تسجيل الدخول - نظام إدارة مركز هشام كيوان")
        login_win.state("zoomed")
        login_win.configure(bg=self.COLOR_BG)
        login_win.protocol("WM_DELETE_WINDOW", self.destroy)
        login_win.grab_set()

        top_corner = tk.Label(login_win, text="📱 مركز هشام كيوان لإدارة الهواتف الذكية", bg=self.COLOR_BG, fg=self.COLOR_BLUE, font=("Segoe UI", 11, "bold"))
        top_corner.pack(anchor="ne", padx=20, pady=15)

        footer_corner = tk.Label(login_win, text="© 2026 جميع الحقوق محفوظة", bg=self.COLOR_BG, fg=self.COLOR_MUTED, font=("Segoe UI", 10))
        footer_corner.pack(side="bottom", anchor="sw", padx=20, pady=15)

        card = tk.Frame(login_win, bg=self.COLOR_CARD, padx=40, pady=40)
        card.place(relx=0.5, rely=0.48, anchor="center")

        if self.logo_login:
            lbl_logo = tk.Label(card, image=self.logo_login, bg=self.COLOR_CARD)
            lbl_logo.pack(pady=(0, 10))

        tk.Label(card, text="🔐 تسجيل الدخول للنظام", font=("Segoe UI", 18, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_BLUE).pack(pady=10)

        tk.Label(card, text="اسم المستخدم:", bg=self.COLOR_CARD, fg=self.COLOR_MUTED, font=("Segoe UI", 11)).pack(pady=(10, 2))
        users_list = self.db.get_all_users()
        user_cb = ttk.Combobox(card, values=[u['username'] for u in users_list], font=("Segoe UI", 11), width=28)
        if user_cb['values']: user_cb.current(0)
        user_cb.pack(pady=5)

        tk.Label(card, text="كلمة السر:", bg=self.COLOR_CARD, fg=self.COLOR_MUTED, font=("Segoe UI", 11)).pack(pady=(10, 2))
        pass_entry = tk.Entry(card, show="*", justify="center", font=("Segoe UI", 12), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, width=28)
        pass_entry.pack(pady=5)
        pass_entry.focus()

        user_cb.bind("<Return>", lambda e: pass_entry.focus())

        def try_login():
            username = user_cb.get().strip()
            password = pass_entry.get().strip()
            if not username or not password:
                messagebox.showwarning("تنبيه", "برجاء إدخال اسم المستخدم وكلمة السر!", parent=login_win)
                return

            user = self.db.authenticate_user(username, password)
            if user:
                self.current_user = user
                login_win.destroy()
                self.deiconify()
                self.state("zoomed")
                self.build_main_ui()
                self.view_inventory()
            else:
                messagebox.showerror("خطأ", "كلمة السر أو اسم المستخدم غير صحيح!", parent=login_win)

        pass_entry.bind("<Return>", lambda e: try_login())
        tk.Button(card, text="دخول للنظام", command=try_login, bg=self.COLOR_ACCENT, fg="#ffffff", font=("Segoe UI", 12, "bold"), width=20, pady=6, relief="flat", cursor="hand2").pack(pady=25)

    def logout(self):
        self.current_user = None
        self.current_view_func = None
        self.withdraw()
        for widget in self.winfo_children():
            widget.destroy()
        self.show_login_dialog()

    def build_main_ui(self, keep_view=False):
        for widget in self.winfo_children():
            widget.destroy()

        top_bar = tk.Frame(self, bg=self.COLOR_TOPBAR, height=60)
        top_bar.pack(fill="x", side="top")

        right_top = tk.Frame(top_bar, bg=self.COLOR_TOPBAR)
        right_top.pack(side="right", padx=15)

        if self.logo_top:
            lbl_logo_top = tk.Label(right_top, image=self.logo_top, bg=self.COLOR_TOPBAR)
            lbl_logo_top.pack(side="right", padx=8)

        tk.Label(right_top, text="📱 نظام المحل الذكي - مركز هشام كيوان", font=("Segoe UI", 14, "bold"), bg=self.COLOR_TOPBAR, fg=self.COLOR_ACCENT).pack(side="right")

        left_top = tk.Frame(top_bar, bg=self.COLOR_TOPBAR)
        left_top.pack(side="left", padx=15)

        user_info = f"👤 المستخدم: {self.current_user['full_name']}" if self.current_user else ""
        tk.Label(left_top, text=user_info, font=("Segoe UI", 10, "bold"), bg=self.COLOR_TOPBAR, fg=self.COLOR_TEXT).pack(side="left", padx=15)

        tk.Button(left_top, text="🚪 تسجيل الخروج", command=self.logout, bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2", padx=10, pady=4).pack(side="left", padx=5)
        tk.Button(left_top, text="🌓 الوضع (ليلي/نهاري)", command=self.toggle_theme, bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2", padx=10, pady=4).pack(side="left", padx=5)

        nav_frame = tk.Frame(self, bg=self.COLOR_TOPBAR, width=220)
        nav_frame.pack(fill="y", side="right")

        self.content_frame = tk.Frame(self, bg=self.COLOR_BG)
        self.content_frame.pack(fill="both", expand=True, side="left")

        buttons = [
            ("📦 المخزون ورأس المال", self.view_inventory, True),
            ("🔍 شاشة البيع السريع", self.view_search_sale, True),
            ("🛒 الشراء (إدخال جهاز)", self.view_buy, self.has_permission('can_manage_inventory')),
            ("👥 إدارة المستخدمين", self.view_user_management, self.has_permission('can_manage_users')),
            ("💳 ديون العملاء (الخرج)", self.view_customer_debts, True),
            ("🏭 مديونية الموردين", self.view_supplier_debts, self.has_permission('can_manage_inventory')),
            ("📊 التقارير والأرباح والسيولة", self.view_reports, self.has_permission('can_view_reports'))
        ]

        for text, cmd, perm in buttons:
            if perm:
                btn = tk.Button(nav_frame, text=text, command=cmd, bg=self.COLOR_CARD, fg=self.COLOR_TEXT, 
                                font=("Segoe UI", 10, "bold"), anchor="e", padx=20, relief="flat", height=2, cursor="hand2")
                btn.pack(fill="x", pady=2)

    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def bind_treeview_double_click(self, tree, target_column_name="ID"):
        def on_double_click(event):
            selected = tree.selection()
            if not selected:
                return
            item_vals = tree.item(selected[0])['values']
            if not item_vals:
                return

            cols = list(tree['columns'])
            idx = 0
            if target_column_name in cols:
                idx = cols.index(target_column_name)
            elif "ID الجهاز" in cols:
                idx = cols.index("ID الجهاز")

            if idx < len(item_vals):
                dev_id = item_vals[idx]
                try:
                    dev_id_clean = int(str(dev_id).replace('#', '').strip())
                    self.show_device_details_modal(dev_id_clean)
                except ValueError:
                    pass

        tree.bind("<Double-1>", on_double_click)

    def show_device_details_modal(self, device_id):
        details = self.db.get_device_full_details(device_id)
        if not details or not details.get('device'):
            messagebox.showerror("خطأ", f"تعذر جلب تفاصيل الجهاز #{device_id}")
            return

        dev = details['device']
        sale = details.get('sale')
        payments = details.get('customer_payments', [])

        dwin = tk.Toplevel(self)
        dwin.title(f"تفاصيل الجهاز الشاملة #{dev['id']} - {dev['category']} {dev['model']}")
        dwin.geometry("750x700")
        dwin.configure(bg=self.COLOR_BG)
        dwin.grab_set()

        header = tk.Frame(dwin, bg=self.COLOR_TOPBAR, pady=12)
        header.pack(fill="x")
        tk.Label(header, text=f"📱 بيانات الجهاز التفصيلية: {dev['category']} {dev['model']} (ID: #{dev['id']})", 
                 font=("Segoe UI", 14, "bold"), bg=self.COLOR_TOPBAR, fg=self.COLOR_BLUE).pack()

        main_scroll = tk.Frame(dwin, bg=self.COLOR_BG, padx=20, pady=15)
        main_scroll.pack(fill="both", expand=True)

        card1 = tk.LabelFrame(main_scroll, text="📋 المواصفات والشراء", bg=self.COLOR_CARD, fg=self.COLOR_BLUE, font=("Segoe UI", 11, "bold"), padx=15, pady=10)
        card1.pack(fill="x", pady=8)

        can_see_cost = self.has_permission('can_view_buy_price')
        buy_p_str = fmt_curr(dev['buy_price']) if can_see_cost else "***"

        bat_str = f"{dev['battery_health']}%" if dev['battery_health'] else "لا يوجد"
        ram_str = dev['ram'] if dev['ram'] else "لا يوجد"

        info_grid1 = [
            (f"السيريال / IMEI: {dev['imei_serial']}", f"الماركة / الفئة: {dev['category']}"),
            (f"الموديل: {dev['model']}", f"المساحة / الرام: {dev['storage']} / {ram_str}"),
            (f"نسبة البطارية: {bat_str}", f"سعر الشراء: {buy_p_str}"),
            (f"المورد: {dev['supplier_name']}", f"تاريخ الشراء: {dev['buy_date_formatted']}"),
            (f"بواسطة المستخدم: {dev['created_by_name']}", f"الحالة الحالية: {'مباع 🔴' if dev['is_sold'] else 'بالمخزن 🟢'}")
        ]

        for r_idx, (c1, c2) in enumerate(info_grid1):
            tk.Label(card1, text=c1, font=("Segoe UI", 10), bg=self.COLOR_CARD, fg=self.COLOR_TEXT, anchor="e").grid(row=r_idx, column=1, sticky="ew", padx=10, pady=3)
            tk.Label(card1, text=c2, font=("Segoe UI", 10), bg=self.COLOR_CARD, fg=self.COLOR_TEXT, anchor="e").grid(row=r_idx, column=0, sticky="ew", padx=10, pady=3)
            card1.grid_columnconfigure(0, weight=1)
            card1.grid_columnconfigure(1, weight=1)

        card2 = tk.LabelFrame(main_scroll, text="🛒 بيانات البيع والعميل", bg=self.COLOR_CARD, fg=self.COLOR_BLUE, font=("Segoe UI", 11, "bold"), padx=15, pady=10)
        card2.pack(fill="x", pady=8)

        if sale:
            net_p_str = fmt_curr(sale['net_profit']) if can_see_cost else "***"
            info_grid2 = [
                (f"رقم الفاتورة: #{sale['id']}", f"اسم العميل: {sale['customer_name']}"),
                (f"هاتف العميل: {sale['customer_phone'] or '-'}", f"سعر البيع: {fmt_curr(sale['sell_price'])}"),
                (f"المدفوع: {fmt_curr(sale['cash_received'])}", f"المتبقي (الآجل): {fmt_curr(sale['remaining_balance'])}"),
                (f"صافي الربح: {net_p_str}", f"تاريخ البيع: {sale['sell_date_formatted']}"),
                (f"المستلم / البائع: {sale['seller_name']}", f"حالة الدفع: {sale['payment_status']}")
            ]
            for r_idx, (c1, c2) in enumerate(info_grid2):
                tk.Label(card2, text=c1, font=("Segoe UI", 10), bg=self.COLOR_CARD, fg=self.COLOR_TEXT, anchor="e").grid(row=r_idx, column=1, sticky="ew", padx=10, pady=3)
                tk.Label(card2, text=c2, font=("Segoe UI", 10), bg=self.COLOR_CARD, fg=self.COLOR_TEXT, anchor="e").grid(row=r_idx, column=0, sticky="ew", padx=10, pady=3)
                card2.grid_columnconfigure(0, weight=1)
                card2.grid_columnconfigure(1, weight=1)
        else:
            tk.Label(card2, text="الجهاز لم يتم بيعه بعد ومتاح حالياً في المخزون.", font=("Segoe UI", 11, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_ACCENT).pack(pady=10)

        if payments:
            card3 = tk.LabelFrame(main_scroll, text="💳 سجل التحصيلات والسدادات", bg=self.COLOR_CARD, fg=self.COLOR_BLUE, font=("Segoe UI", 11, "bold"), padx=10, pady=5)
            card3.pack(fill="both", expand=True, pady=8)

            cols = ("تاريخ الدفعة", "المبلغ المدفوع", "المستلم")
            ptree = ttk.Treeview(card3, columns=cols, show="headings", height=4)
            for c in cols:
                ptree.heading(c, text=c)
                ptree.column(c, anchor="center")
            ptree.pack(fill="both", expand=True)

            for p in payments:
                ptree.insert("", "end", values=(p['payment_date_formatted'], fmt_curr(p['payment_amount']), p['receiver_name']))

    def view_user_management(self):
        self.current_view_func = self.view_user_management
        self.clear_content()

        tk.Label(self.content_frame, text="إدارة المستخدمين والصلاحيات", font=("Segoe UI", 15, "bold"), bg=self.COLOR_BG, fg=self.COLOR_BLUE).pack(pady=10)

        columns = ("ID", "اسم المستخدم", "الاسم الكامل", "الحالة")
        tree = ttk.Treeview(self.content_frame, columns=columns, show="headings", height=8)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120, anchor="center")
        tree.pack(fill="x", padx=15, pady=5)

        def load_users():
            for r in tree.get_children(): tree.delete(r)
            users = self.db.get_all_users()
            for u in users:
                st = "نشط" if u['is_active'] else "معطل"
                tree.insert("", "end", values=(u['id'], u['username'], u['full_name'], st))

        load_users()

        btn_bar = tk.Frame(self.content_frame, bg=self.COLOR_BG)
        btn_bar.pack(pady=10)

        def open_add_user():
            uwin = tk.Toplevel(self)
            uwin.title("إضافة مستخدم جديد")
            uwin.geometry("400x500")
            uwin.configure(bg=self.COLOR_CARD)

            tk.Label(uwin, text="اسم المستخدم:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT).pack(pady=5)
            e_uname = tk.Entry(uwin, bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT)
            e_uname.pack(pady=5)

            tk.Label(uwin, text="كلمة المرور:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT).pack(pady=5)
            e_pass = tk.Entry(uwin, show="*", bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT)
            e_pass.pack(pady=5)

            tk.Label(uwin, text="الاسم الكامل:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT).pack(pady=5)
            e_fname = tk.Entry(uwin, bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT)
            e_fname.pack(pady=5)

            tk.Label(uwin, text="الصلاحيات:", bg=self.COLOR_CARD, fg=self.COLOR_BLUE, font=("Segoe UI", 11, "bold")).pack(pady=5)
            perms_vars = {
                'can_view_buy_price': tk.BooleanVar(value=True),
                'can_manage_inventory': tk.BooleanVar(value=False),
                'can_manage_users': tk.BooleanVar(value=False),
                'can_view_reports': tk.BooleanVar(value=False),
                'can_process_returns': tk.BooleanVar(value=False),
                'can_edit_prices': tk.BooleanVar(value=True)
            }
            for k, v in perms_vars.items():
                tk.Checkbutton(uwin, text=k, variable=v, bg=self.COLOR_CARD, fg=self.COLOR_TEXT, selectcolor=self.COLOR_CARD).pack(anchor="w", padx=40)

            def save_u():
                p_dict = {k: v.get() for k, v in perms_vars.items()}
                self.db.add_user(e_uname.get().strip(), e_pass.get().strip(), e_fname.get().strip(), p_dict)
                messagebox.showinfo("تم", "تم إضافة المستخدم بنجاح!")
                uwin.destroy()
                load_users()

            tk.Button(uwin, text="حفظ", command=save_u, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 10, "bold")).pack(pady=15)

        def delete_u():
            sel = tree.selection()
            if not sel: return
            uid = tree.item(sel[0])['values'][0]
            if messagebox.askyesno("تأكيد", "هل تريد تعطيل هذا المستخدم؟"):
                self.db.delete_user(uid)
                load_users()

        tk.Button(btn_bar, text="➕ إضافة مستخدم", command=open_add_user, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 10, "bold")).pack(side="right", padx=5)
        tk.Button(btn_bar, text="❌ تعطيل مستخدم", command=delete_u, bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 10, "bold")).pack(side="right", padx=5)

    def view_inventory(self):
        self.current_view_func = self.view_inventory
        self.clear_content()

        top_frame = tk.Frame(self.content_frame, bg=self.COLOR_BG)
        top_frame.pack(fill="x", padx=15, pady=10)

        tk.Label(top_frame, text="الأجهزة المتاحة بالمخزون", font=("Segoe UI", 15, "bold"), bg=self.COLOR_BG, fg=self.COLOR_BLUE).pack(side="right")

        search_entry = tk.Entry(top_frame, font=("Segoe UI", 10), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT)
        search_entry.pack(side="left", padx=5)
        def filter_inv(e=None): load_tree(search_entry.get().strip())
        search_entry.bind("<Return>", filter_inv)
        tk.Button(top_frame, text="بحث", command=filter_inv, bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 9, "bold")).pack(side="left")

        columns = ("ID", "تاريخ الشراء", "المورد", "سعر الشراء", "السيريال / IMEI", "البطارية", "الرامات", "المساحة", "الموديل", "النوع")
        tree = ttk.Treeview(self.content_frame, columns=columns, show="headings")

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100, anchor="center")

        tree.pack(fill="both", expand=True, padx=15, pady=5)
        self.bind_treeview_double_click(tree, "ID")

        def load_tree(q=None):
            for row in tree.get_children(): tree.delete(row)
            devices = self.db.get_available_inventory(q)
            for idx, d in enumerate(devices):
                can_see = self.has_permission('can_view_buy_price')
                buy_p = fmt_curr(d['buy_price']) if can_see else "***"
                bat_str = f"{d['battery_health']}%" if d['battery_health'] else "لا يوجد"
                ram_str = d['ram'] if d['ram'] else "لا يوجد"
                tree.insert("", "end", values=(d['id'], d['buy_date_formatted'], d['supplier_name'], 
                                              buy_p, d['imei_serial'], bat_str, 
                                              ram_str, d['storage'], d['model'], d['category']))

        load_tree()

        if self.has_permission('can_manage_inventory'):
            act_bar = tk.Frame(self.content_frame, bg=self.COLOR_BG)
            act_bar.pack(fill="x", padx=15, pady=5)

            def delete_dev():
                sel = tree.selection()
                if not sel: return
                dev_id = tree.item(sel[0])['values'][0]
                if messagebox.askyesno("تأكيد", "حذف الجهاز المحدد نهائياً من المخزون؟"):
                    self.db.delete_device(dev_id)
                    load_tree()

            tk.Button(act_bar, text="🗑️ حذف الجهاز", command=delete_dev, bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 9, "bold")).pack(side="right", padx=5)

        stat_bar = tk.Frame(self.content_frame, bg=self.COLOR_TOPBAR, height=45)
        stat_bar.pack(fill="x", side="bottom")

        overview = self.db.get_capital_statistics()
        info_text = f"إجمالي الأجهزة المتاحة: {fmt_num(overview['total_devices'])} جهاز  |  رأس المال بالمخزن: {fmt_curr(overview['total_capital'])}"
        tk.Label(stat_bar, text=info_text, bg=self.COLOR_TOPBAR, fg=self.COLOR_ACCENT, font=("Segoe UI", 11, "bold")).pack(pady=8)

    def view_search_sale(self):
        self.current_view_func = self.view_search_sale
        self.clear_content()

        tk.Label(self.content_frame, text="🛒 شاشة البيع السريع", font=("Segoe UI", 15, "bold"), bg=self.COLOR_BG, fg=self.COLOR_BLUE).pack(pady=10)

        search_bar = tk.Frame(self.content_frame, bg=self.COLOR_BG)
        search_bar.pack(pady=5)

        tk.Label(search_bar, text="امسح الباركود أو أدخل IMEI / ID أو الموديل:", bg=self.COLOR_BG, fg=self.COLOR_TEXT, font=("Segoe UI", 11)).pack(side="right", padx=5)
        search_entry = tk.Entry(search_bar, font=("Segoe UI", 12), width=25, bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT)
        search_entry.pack(side="right", padx=5)
        search_entry.focus()

        card = tk.Frame(self.content_frame, bg=self.COLOR_CARD, padx=25, pady=25)
        card.pack(pady=10, fill="both", expand=True, padx=40)

        def perform_search(event=None):
            for widget in card.winfo_children(): widget.destroy()
            q = search_entry.get().strip()
            if not q: return

            dev = self.db.search_device_by_imei_or_id(q)
            if not dev:
                tk.Label(card, text="❌ لم يتم العثور على أي جهاز بهذا البحث!", bg=self.COLOR_CARD, fg=self.COLOR_DANGER, font=("Segoe UI", 12, "bold")).pack()
                return

            buy_p_str = fmt_curr(dev['buy_price']) if self.has_permission('can_view_buy_price') else "***"
            bat_str = f"{dev['battery_health']}%" if dev['battery_health'] else "لا يوجد"
            ram_str = dev['ram'] if dev['ram'] else "لا يوجد"

            info_frame = tk.Frame(card, bg=self.COLOR_CARD)
            info_frame.pack(fill="x", pady=5)

            tk.Label(info_frame, text=f"📱 الجهاز: {dev['category']} {dev['model']}", font=("Segoe UI", 14, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_BLUE, anchor="e").pack(fill="x", pady=3)
            tk.Label(info_frame, text=f"🔹 المساحة: {dev['storage']} | الرامات: {ram_str} | البطارية: {bat_str}", font=("Segoe UI", 11), bg=self.COLOR_CARD, fg=self.COLOR_TEXT, anchor="e").pack(fill="x", pady=2)
            tk.Label(info_frame, text=f"🔢 السيريال IMEI: {dev['imei_serial']} | رقم التتبع ID: #{dev['id']}", font=("Segoe UI", 11), bg=self.COLOR_CARD, fg=self.COLOR_TEXT, anchor="e").pack(fill="x", pady=2)
            tk.Label(info_frame, text=f"💰 سعر الشراء: {buy_p_str} | المورد: {dev['supplier_name']} | تاريخ الشراء: {dev.get('buy_date_formatted', '-')}", font=("Segoe UI", 11), bg=self.COLOR_CARD, fg=self.COLOR_MUTED, anchor="e").pack(fill="x", pady=2)

            if not dev['is_sold']:
                sale_box = tk.Frame(card, bg=self.COLOR_CARD, pady=15)
                sale_box.pack(fill="x", pady=10)

                tk.Label(sale_box, text="السعر الاتفاقي (البيع):", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=0, column=3, sticky="e", padx=5, pady=5)
                e_price = tk.Entry(sale_box, justify="right", font=("Segoe UI", 11), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, validate="key", validatecommand=self.vcmd_num)
                e_price.grid(row=0, column=2, padx=5, pady=5, sticky="w")
                e_price.focus()

                tk.Label(sale_box, text="المدفوع نقداً:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky="e", padx=5, pady=5)
                e_paid = tk.Entry(sale_box, justify="right", font=("Segoe UI", 11), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, validate="key", validatecommand=self.vcmd_num)
                e_paid.insert(0, "0")
                e_paid.grid(row=0, column=0, padx=5, pady=5, sticky="w")

                tk.Label(sale_box, text="اسم العميل:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=1, column=3, sticky="e", padx=5, pady=5)
                e_cname = tk.Entry(sale_box, justify="right", font=("Segoe UI", 11), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT)
                e_cname.grid(row=1, column=2, padx=5, pady=5, sticky="w")

                tk.Label(sale_box, text="رقم الهاتف:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=1, column=1, sticky="e", padx=5, pady=5)
                e_cphone = tk.Entry(sale_box, justify="right", font=("Segoe UI", 11), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, validate="key", validatecommand=self.vcmd_num)
                e_cphone.grid(row=1, column=0, padx=5, pady=5, sticky="w")

                lbl_rem = tk.Label(sale_box, text="المتبقي (الآجل على العميل): 0.00 ج.م", font=("Segoe UI", 12, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_DANGER)
                lbl_rem.grid(row=2, column=0, columnspan=4, pady=15)

                e_price.bind("<Return>", lambda e: e_paid.focus())
                e_paid.bind("<Return>", lambda e: e_cname.focus())
                e_cname.bind("<Return>", lambda e: e_cphone.focus())
                e_cphone.bind("<Return>", lambda e: do_confirm_sale())

                def update_calc(e=None):
                    try:
                        price = float(e_price.get().strip() or 0)
                        paid = float(e_paid.get().strip() or 0)
                        rem = max(0.0, price - paid)
                        if price < float(dev['buy_price']):
                            lbl_rem.config(text=f"⚠️ تحذير: سعر البيع أقل من سعر الشراء ({fmt_curr(dev['buy_price'])})!", fg=self.COLOR_DANGER)
                        elif rem > 0:
                            lbl_rem.config(text=f"⚠️ لم يتم السداد بالكامل! المتبقي (آجل): {fmt_curr(rem)}", fg=self.COLOR_DANGER)
                        else:
                            lbl_rem.config(text="✅ تم السداد بالكامل", fg=self.COLOR_ACCENT)
                    except ValueError:
                        pass

                e_price.bind("<KeyRelease>", update_calc)
                e_paid.bind("<KeyRelease>", update_calc)
                update_calc()

                def do_confirm_sale():
                    try:
                        price_str = e_price.get().strip()
                        if not price_str:
                            messagebox.showwarning("تنبيه", "برجاء إدخال سعر البيع الاتفاقي!")
                            e_price.focus()
                            return

                        price = float(price_str)
                        buy_p = float(dev['buy_price'])

                        if price < buy_p:
                            messagebox.showerror("خطأ في البيع", f"مينفعش يبقى سعر البيع أقل من سعر الشراء ({fmt_curr(buy_p)})!")
                            return

                        paid = float(e_paid.get().strip() or 0)
                        cname = e_cname.get().strip()
                        cphone = e_cphone.get().strip()
                        
                        if not cname:
                            messagebox.showwarning("تنبيه", "برجاء إدخال اسم العميل!")
                            e_cname.focus()
                            return

                        remaining = max(0.0, price - paid)

                        sale_id = self.db.process_sale(dev['id'], price, cname, cphone, paid, "", self.current_user['id'])
                        
                        inv_data = {
                            'sale_id': sale_id,
                            'customer_name': cname,
                            'customer_phone': cphone,
                            'device': dev,
                            'original_price': price,
                            'discount': 0.0,
                            'sell_price': price,
                            'cash_received': paid,
                            'remaining_balance': remaining
                        }
                        
                        img_path = generate_invoice_image(inv_data)
                        os.startfile(img_path)
                        messagebox.showinfo("تم", "تم تسجيل البيع بنجاح وتوليد الفاتورة عالية الدقة!")
                        self.view_search_sale()
                    except Exception as ex:
                        messagebox.showerror("خطأ", str(ex))

                tk.Button(card, text="💾 تأكيد البيع وطباعة الفاتورة", command=do_confirm_sale, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 11, "bold"), pady=6, cursor="hand2").pack(pady=10)
            else:
                tk.Label(card, text=f"الحالة: مباع للعميل ({dev['customer_name']})", bg=self.COLOR_CARD, fg=self.COLOR_DANGER, font=("Segoe UI", 12, "bold")).pack(pady=10)
                if self.has_permission('can_process_returns'):
                    def do_return():
                        if messagebox.askyesno("تأكيد", "إجراء مرتجع للجهاز وإرجاعه للمخزون؟"):
                            self.db.process_return(dev['id'], self.current_user['id'])
                            messagebox.showinfo("تم", "تم المرتجع بنجاح!")
                            self.view_search_sale()
                    tk.Button(card, text="🔄 إجراء مرتجع", command=do_return, bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 10, "bold"), cursor="hand2").pack(pady=5)

        search_entry.bind("<Return>", perform_search)
        tk.Button(search_bar, text="بحث", command=perform_search, bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold")).pack(side="right")

    def view_buy(self):
        self.current_view_func = self.view_buy
        self.clear_content()
        tk.Label(self.content_frame, text="تسجيل جهاز جديد في المخزون", font=("Segoe UI", 15, "bold"), bg=self.COLOR_BG, fg=self.COLOR_BLUE).pack(pady=15)

        form = tk.Frame(self.content_frame, bg=self.COLOR_CARD, padx=25, pady=25)
        form.pack(pady=10)

        labels = ["الماركة (النوع):", "الموديل:", "المساحة:", "الرامات:", "نسبة البطارية:", "السيريال / IMEI:", "سعر الشراء:", "المورد:"]
        self.buy_entries = {}

        suppliers = self.db.get_all_suppliers()

        entries_list = []

        for i, text in enumerate(labels):
            row, col = divmod(i, 2)
            tk.Label(form, text=text, bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10)).grid(row=row*2, column=col*2, sticky="e", padx=10, pady=5)
            
            if text == "المورد:":
                supp_frame = tk.Frame(form, bg=self.COLOR_CARD)
                
                supp_display_names = ["بدون مورد / شراء مباشر"] + [s['name'] for s in suppliers]
                cb = ttk.Combobox(supp_frame, values=supp_display_names, state="readonly", font=("Segoe UI", 10))
                cb.current(0)
                cb.pack(side="right", padx=2)
                
                def add_new_supplier_popup():
                    ns_win = tk.Toplevel(self)
                    ns_win.title("إضافة مورد جديد")
                    ns_win.geometry("300x200")
                    ns_win.configure(bg=self.COLOR_CARD)
                    ns_win.grab_set()

                    tk.Label(ns_win, text="اسم المورد:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT).pack(pady=5)
                    n_entry = tk.Entry(ns_win, bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, justify="right")
                    n_entry.pack(pady=5)
                    n_entry.focus()
                    
                    tk.Label(ns_win, text="رقم الهاتف:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT).pack(pady=5)
                    p_entry = tk.Entry(ns_win, bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, justify="right", validate="key", validatecommand=self.vcmd_num)
                    p_entry.pack(pady=5)

                    n_entry.bind("<Return>", lambda e: p_entry.focus())
                    p_entry.bind("<Return>", lambda e: save_supp())

                    def save_supp():
                        name = n_entry.get().strip()
                        phone = p_entry.get().strip()
                        if name:
                            new_id = self.db.add_supplier(name, phone)
                            nonlocal suppliers
                            suppliers = self.db.get_all_suppliers()
                            updated_display = ["بدون مورد / شراء مباشر"] + [s['name'] for s in suppliers]
                            cb['values'] = updated_display
                            for idx, s in enumerate(suppliers):
                                if s['id'] == new_id:
                                    cb.current(idx + 1)
                                    break
                            ns_win.destroy()
                    
                    tk.Button(ns_win, text="حفظ", command=save_supp, bg=self.COLOR_ACCENT, fg="white").pack(pady=10)

                tk.Button(supp_frame, text="+", command=add_new_supplier_popup, bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 9, "bold")).pack(side="right")
                supp_frame.grid(row=row*2+1, column=col*2, padx=10, pady=5)
                self.buy_entries['supplier_cb'] = cb
            else:
                extra_args = {}
                if text in ["نسبة البطارية:", "سعر الشراء:"]:
                    extra_args = {"validate": "key", "validatecommand": self.vcmd_num}

                entry = tk.Entry(form, font=("Segoe UI", 10), justify="right", bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, **extra_args)
                entry.grid(row=row*2+1, column=col*2, padx=10, pady=5)
                self.buy_entries[text] = entry
                entries_list.append(entry)

        for idx_e in range(len(entries_list) - 1):
            curr_e = entries_list[idx_e]
            next_e = entries_list[idx_e + 1]
            curr_e.bind("<Return>", lambda event, nxt=next_e: nxt.focus())

        if entries_list:
            entries_list[0].focus()

        save_btn = tk.Button(self.content_frame, text="💾 حفظ وإدخال للمخزون", bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 11, "bold"), padx=25, pady=6, relief="flat", cursor="hand2")
        save_btn.pack(pady=20)

        if entries_list:
            entries_list[-1].bind("<Return>", lambda e: save_device())

        def save_device():
            try:
                cat = self.buy_entries["الماركة (النوع):"].get().strip()
                model = self.buy_entries["الموديل:"].get().strip()
                storage = self.buy_entries["المساحة:"].get().strip()
                ram = self.buy_entries["الرامات:"].get().strip() or "لا يوجد"
                bat_str = self.buy_entries["نسبة البطارية:"].get().strip()
                bat = int(bat_str) if bat_str.isdigit() else 0
                imei = self.buy_entries["السيريال / IMEI:"].get().strip()
                price_str = self.buy_entries["سعر الشراء:"].get().strip()

                if not cat or not model or not imei or not price_str:
                    messagebox.showwarning("تنبيه", "برجاء إدخال الماركة والموديل والسيريال وسعر الشراء!")
                    return

                price = float(price_str)

                cb = self.buy_entries['supplier_cb']
                curr_idx = cb.current()
                supp_id = None
                if curr_idx > 0 and (curr_idx - 1) < len(suppliers):
                    supp_id = suppliers[curr_idx - 1]['id']

                dev_id = self.db.add_device(cat, model, storage, ram, bat, "", imei, price, supp_id, "", self.current_user['id'])
                messagebox.showinfo("نجاح", f"تم إضافة الجهاز بنجاح! ID: #{dev_id}")
                self.view_inventory()
            except Exception as e:
                messagebox.showerror("خطأ", str(e))

        save_btn.config(command=save_device)

    def view_customer_debts(self):
        self.current_view_func = self.view_customer_debts
        self.clear_content()

        top_frame = tk.Frame(self.content_frame, bg=self.COLOR_BG)
        top_frame.pack(fill="x", padx=15, pady=10)

        tk.Label(top_frame, text="مستحقات وتأخيرات العملاء (الخرج)", font=("Segoe UI", 15, "bold"), bg=self.COLOR_BG, fg=self.COLOR_BLUE).pack(side="right")

        columns = ("المتبقي", "المدفوع", "الإجمالي", "تاريخ البيع", "الهاتف", "اسم العميل", "الموديل", "ID الجهاز", "رقم الفاتورة")
        tree = ttk.Treeview(self.content_frame, columns=columns, show="headings")
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100, anchor="center")
        tree.pack(fill="both", expand=True, padx=15, pady=5)
        self.bind_treeview_double_click(tree, "ID الجهاز")

        def load_debts():
            for row in tree.get_children(): tree.delete(row)
            debts = self.db.get_customer_debts()
            for d in debts:
                tree.insert("", "end", values=(fmt_curr(d['remaining_balance']), fmt_curr(d['cash_received']), 
                                              fmt_curr(d['sell_price']), d['sell_date_formatted'], 
                                              d['customer_phone'], d['customer_name'], d['model'], 
                                              d['device_id'], d['sale_id']))

        load_debts()

        pay_frame = tk.Frame(self.content_frame, bg=self.COLOR_CARD, pady=10)
        pay_frame.pack(fill="x", padx=15, pady=10)

        tk.Label(pay_frame, text="مبلغ التحصيل:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT).pack(side="right", padx=5)
        amount_entry = tk.Entry(pay_frame, font=("Segoe UI", 10), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, validate="key", validatecommand=self.vcmd_num)
        amount_entry.pack(side="right", padx=5)

        def pay_selected():
            selected = tree.selection()
            if not selected: 
                messagebox.showwarning("تنبيه", "يرجى تحديد عميل تحصل منه الدفعة!")
                return
            sale_id = tree.item(selected[0])['values'][8]
            try:
                amt = float(amount_entry.get().strip())
                self.db.pay_customer_debt(sale_id, amt, self.current_user['id'])
                messagebox.showinfo("نجاح", "تم تحصيل الدفعة بنجاح!")
                load_debts()
                amount_entry.delete(0, tk.END)
            except Exception as e:
                messagebox.showerror("خطأ", str(e))

        amount_entry.bind("<Return>", lambda e: pay_selected())
        tk.Button(pay_frame, text="💵 تحصيل الدفعة", command=pay_selected, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 10, "bold")).pack(side="right", padx=10)

    def view_supplier_debts(self):
        self.current_view_func = self.view_supplier_debts
        self.clear_content()

        top_frame = tk.Frame(self.content_frame, bg=self.COLOR_BG)
        top_frame.pack(fill="x", padx=15, pady=10)

        tk.Label(top_frame, text="🏭 مديونيات وفواتير الموردين والتفاصيل", font=("Segoe UI", 15, "bold"), bg=self.COLOR_BG, fg=self.COLOR_BLUE).pack(side="right")

        search_entry = tk.Entry(top_frame, font=("Segoe UI", 10), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT)
        search_entry.pack(side="left", padx=5)
        def filter_inv(e=None): load_invoices()
        search_entry.bind("<Return>", filter_inv)
        tk.Button(top_frame, text="بحث", command=filter_inv, bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 9, "bold")).pack(side="left")

        filter_frame = tk.Frame(top_frame, bg=self.COLOR_BG)
        filter_frame.pack(side="right", padx=20)
        
        status_var = tk.StringVar(value="UNPAID")
        
        tk.Radiobutton(filter_frame, text="غير مدفوع (المتبقي)", variable=status_var, value="UNPAID", command=filter_inv, bg=self.COLOR_BG, fg=self.COLOR_TEXT, selectcolor=self.COLOR_CARD).pack(side="right", padx=5)
        tk.Radiobutton(filter_frame, text="مدفوع بالكامل", variable=status_var, value="PAID", command=filter_inv, bg=self.COLOR_BG, fg=self.COLOR_TEXT, selectcolor=self.COLOR_CARD).pack(side="right", padx=5)
        tk.Radiobutton(filter_frame, text="الكل", variable=status_var, value="ALL", command=filter_inv, bg=self.COLOR_BG, fg=self.COLOR_TEXT, selectcolor=self.COLOR_CARD).pack(side="right", padx=5)

        tables_frame = tk.Frame(self.content_frame, bg=self.COLOR_BG)
        tables_frame.pack(fill="both", expand=True, padx=15, pady=5)

        inv_frame = tk.LabelFrame(tables_frame, text="📋 فواتير الموردين", bg=self.COLOR_BG, fg=self.COLOR_BLUE, font=("Segoe UI", 11, "bold"))
        inv_frame.pack(fill="both", expand=True, side="top", pady=5)

        columns_inv = ("الحالة", "المتبقي", "المدفوع", "الإجمالي", "التاريخ", "اسم المورد", "رقم الفاتورة")
        tree_inv = ttk.Treeview(inv_frame, columns=columns_inv, show="headings", height=6)
        for col in columns_inv:
            tree_inv.heading(col, text=col)
            tree_inv.column(col, width=100, anchor="center")
        tree_inv.pack(fill="both", expand=True, padx=5, pady=5)

        dev_frame = tk.LabelFrame(tables_frame, text="📱 تفاصيل الأجهزة بالفاتورة المختارة", bg=self.COLOR_BG, fg=self.COLOR_BLUE, font=("Segoe UI", 11, "bold"))
        dev_frame.pack(fill="both", expand=True, side="bottom", pady=5)

        columns_dev = ("سعر الشراء", "السيريال / IMEI", "الموديل", "الماركة", "ID الجهاز")
        tree_dev = ttk.Treeview(dev_frame, columns=columns_dev, show="headings", height=5)
        for col in columns_dev:
            tree_dev.heading(col, text=col)
            tree_dev.column(col, width=110, anchor="center")
        tree_dev.pack(fill="both", expand=True, padx=5, pady=5)
        self.bind_treeview_double_click(tree_dev, "ID الجهاز")

        def load_invoices():
            for row in tree_inv.get_children(): tree_inv.delete(row)
            for row in tree_dev.get_children(): tree_dev.delete(row)
            q = search_entry.get().strip()
            st = status_var.get()
            invs = self.db.get_supplier_invoices(q, st)
            for i in invs:
                status_display = "تم السداد 🟢" if i['remaining_amount'] <= 0 else "غير مسدد 🔴"
                tree_inv.insert("", "end", values=(status_display, fmt_curr(i['remaining_amount']), 
                                                  fmt_curr(i['paid_amount']), fmt_curr(i['total_amount']), 
                                                  i['inv_date'], i['supplier_name'], i['id']))

        def on_invoice_select(event):
            for row in tree_dev.get_children(): tree_dev.delete(row)
            selected = tree_inv.selection()
            if not selected: return
            inv_id = tree_inv.item(selected[0])['values'][6]
            devices = self.db.get_invoice_devices(inv_id)
            can_see = self.has_permission('can_view_buy_price')
            for d in devices:
                p_val = fmt_curr(d['buy_price']) if can_see else "***"
                tree_dev.insert("", "end", values=(p_val, d['imei_serial'], d['model'], d['category'], d['id']))

        tree_inv.bind("<<TreeviewSelect>>", on_invoice_select)
        load_invoices()

        act_frame = tk.Frame(self.content_frame, bg=self.COLOR_CARD, pady=10)
        act_frame.pack(fill="x", padx=15, pady=10)

        tk.Label(act_frame, text="مبلغ الدفعة للمورد:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right", padx=5)
        pay_entry = tk.Entry(act_frame, font=("Segoe UI", 10), width=15, bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, validate="key", validatecommand=self.vcmd_num)
        pay_entry.pack(side="right", padx=5)

        def do_pay_supplier():
            selected = tree_inv.selection()
            if not selected:
                messagebox.showwarning("تنبيه", "يرجى تحديد فاتورة لتسديد الدفعة لها أولاً!")
                return
            inv_vals = tree_inv.item(selected[0])['values']
            inv_id = inv_vals[6]
            try:
                amt = float(pay_entry.get().strip())
                if amt <= 0: raise ValueError
                self.db.pay_supplier_debt(inv_id, amt, self.current_user['id'])
                messagebox.showinfo("نجاح", "تم تسجيل التسديد للمورد وتحديث الفاتورة بنجاح!")
                pay_entry.delete(0, tk.END)
                load_invoices()
            except ValueError:
                messagebox.showerror("خطأ", "برجاء إدخال مبلغ تسديد صحيح!")
            except Exception as e:
                messagebox.showerror("خطأ", str(e))

        pay_entry.bind("<Return>", lambda e: do_pay_supplier())
        tk.Button(act_frame, text="💵 تسديد دفعة للمورد", command=do_pay_supplier, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"), cursor="hand2").pack(side="right", padx=10)

        def open_print_options_popup():
            selected = tree_inv.selection()
            if not selected:
                messagebox.showwarning("تنبيه", "يرجى تحديد فاتورة لطباعتها!")
                return
            
            inv_vals = tree_inv.item(selected[0])['values']
            inv_id = inv_vals[6]
            
            p_win = tk.Toplevel(self)
            p_win.title("خيارات طباعة فاتورة المديونية")
            p_win.geometry("500x520")
            p_win.configure(bg=self.COLOR_CARD)
            p_win.grab_set()

            tk.Label(p_win, text="🖨️ إعدادات طباعة فاتورة المديونية", font=("Segoe UI", 14, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_BLUE).pack(pady=15)

            tk.Label(p_win, text="نمط التصميم والألوان:", font=("Segoe UI", 11, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_TEXT).pack(anchor="e", padx=25)
            style_var = tk.StringVar(value="color")
            
            style_frame = tk.Frame(p_win, bg=self.COLOR_CARD)
            style_frame.pack(fill="x", padx=25, pady=5)
            tk.Radiobutton(style_frame, text="🎨 ملون (أزرق)", variable=style_var, value="color", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, selectcolor=self.COLOR_CARD, font=("Segoe UI", 10)).pack(side="right", padx=5)
            tk.Radiobutton(style_frame, text="🔴 عنابي (داكن)", variable=style_var, value="burgundy", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, selectcolor=self.COLOR_CARD, font=("Segoe UI", 10)).pack(side="right", padx=5)
            tk.Radiobutton(style_frame, text="🖨️ أبيض وأسود", variable=style_var, value="grayscale", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, selectcolor=self.COLOR_CARD, font=("Segoe UI", 10)).pack(side="right", padx=5)

            tk.Label(p_win, text="الشروط والملاحظات المسجلة بالفاتورة:", font=("Segoe UI", 11, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_TEXT).pack(anchor="e", padx=25, pady=(15, 5))
            
            terms_text = tk.Text(p_win, height=7, width=50, font=("Segoe UI", 10), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT)
            terms_text.pack(padx=25, pady=5)
            
            default_terms = "1. البضاعة المباعة أو الموردة تخضع للمراجعة خلال 3 أيام.\n2. الضمان والذمم المالية سارية طبقاً للفاتورة المعتمدة.\n3. هذه الفاتورة مستند رسمي للمديونية."
            terms_text.insert("1.0", default_terms)

            def execute_printing():
                custom_terms = terms_text.get("1.0", tk.END).strip()
                selected_style = style_var.get()
                
                devs = self.db.get_invoice_devices(inv_id)
                first_dev = devs[0] if devs else {'category': 'توريد متعدد', 'model': 'أجهزة مختلفة', 'imei_serial': 'عدّة أجهزة'}
                
                inv_data = {
                    'sale_id': f"SUPP-{inv_id}",
                    'customer_name': f"المورد: {inv_vals[5]}",
                    'customer_phone': "-",
                    'device': first_dev,
                    'original_price': inv_vals[3],
                    'discount': 0.0,
                    'sell_price': inv_vals[3],
                    'cash_received': inv_vals[2],
                    'remaining_balance': inv_vals[1],
                    'custom_terms': custom_terms,
                    'print_style': selected_style
                }
                
                img_path = generate_invoice_image(inv_data)
                os.startfile(img_path)
                p_win.destroy()

            tk.Button(p_win, text="🖨️ طباعة الفاتورة الآن", command=execute_printing, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 11, "bold"), padx=20, pady=8, cursor="hand2").pack(pady=20)

        tk.Button(act_frame, text="🖨️ إعدادات وطباعة الفاتورة", command=open_print_options_popup, bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold"), cursor="hand2").pack(side="left", padx=10)

    def view_reports(self):
        self.current_view_func = self.view_reports
        self.clear_content()

        notebook = ttk.Notebook(self.content_frame)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        tab_financial = tk.Frame(notebook, bg=self.COLOR_BG)
        tab_sales = tk.Frame(notebook, bg=self.COLOR_BG)

        notebook.add(tab_financial, text="💰 التقرير المالي الكامل والرصيد")
        notebook.add(tab_sales, text="📊 تقرير المبيعات والأرباح")

        fin_top = tk.Frame(tab_financial, bg=self.COLOR_BG)
        fin_top.pack(fill="x", padx=15, pady=10)

        tk.Label(fin_top, text="💰 التقرير المالي الكامل والسيولة التراكمية (مُحدّث دائماً)", font=("Segoe UI", 15, "bold"), bg=self.COLOR_BG, fg=self.COLOR_BLUE).pack(side="right")

        cards_container = tk.Frame(tab_financial, bg=self.COLOR_BG)
        cards_container.pack(fill="x", padx=15, pady=10)

        def build_metric_card(parent, title, val_str, bg_col, fg_col, row_i, col_i):
            f = tk.Frame(parent, bg=bg_col, padx=15, pady=15, highlightthickness=1, highlightbackground=self.COLOR_TOPBAR)
            f.grid(row=row_i, column=col_i, sticky="nsew", padx=8, pady=8)
            tk.Label(f, text=title, font=("Segoe UI", 11, "bold"), bg=bg_col, fg=self.COLOR_MUTED).pack(anchor="e")
            lbl_val = tk.Label(f, text=val_str, font=("Segoe UI", 16, "bold"), bg=bg_col, fg=fg_col)
            lbl_val.pack(anchor="e", pady=(8, 0))
            return lbl_val

        for i in range(3): cards_container.grid_columnconfigure(i, weight=1)

        fin_data = self.db.get_financial_summary()

        lbl_liq = build_metric_card(cards_container, "💵 السيولة المالية الحالية (المحصلة)", fmt_curr(fin_data['current_liquidity']), self.COLOR_CARD, self.COLOR_ACCENT, 0, 2)
        lbl_inv = build_metric_card(cards_container, "📦 إجمالي سعر أجهزة المخزون", fmt_curr(fin_data['inventory_cost']), self.COLOR_CARD, self.COLOR_BLUE, 0, 1)
        lbl_cap = build_metric_card(cards_container, "🏛️ إجمالي رأس المال (السيولة + المخزون)", fmt_curr(fin_data['total_capital']), self.COLOR_CARD, self.COLOR_TEXT, 0, 0)

        lbl_c_debt = build_metric_card(cards_container, "🔻 الخرج مجمع (ديون العملاء المتبقية)", fmt_curr(fin_data['customer_debts']), self.COLOR_CARD, self.COLOR_DANGER, 1, 2)
        lbl_s_debt = build_metric_card(cards_container, "🏭 الديون للموردين الحالية", fmt_curr(fin_data['supplier_debts']), self.COLOR_CARD, self.COLOR_DANGER, 1, 1)
        lbl_m_prof = build_metric_card(cards_container, "📈 صافي الربح للشهر الحالي", fmt_curr(fin_data['monthly_profit']), self.COLOR_CARD, self.COLOR_ACCENT, 1, 0)

        act_fin_frame = tk.Frame(tab_financial, bg=self.COLOR_CARD, pady=15, padx=20)
        act_fin_frame.pack(fill="x", padx=15, pady=15)

        def refresh_fin_ui():
            d = self.db.get_financial_summary()
            lbl_liq.config(text=fmt_curr(d['current_liquidity']))
            lbl_inv.config(text=fmt_curr(d['inventory_cost']))
            lbl_cap.config(text=fmt_curr(d['total_capital']))
            lbl_c_debt.config(text=fmt_curr(d['customer_debts']))
            lbl_s_debt.config(text=fmt_curr(d['supplier_debts']))
            lbl_m_prof.config(text=fmt_curr(d['monthly_profit']))

        def open_add_capital_popup():
            cap_win = tk.Toplevel(self)
            cap_win.title("إضافة / تغذية سيولة مالية لرأس المال")
            cap_win.geometry("380x280")
            cap_win.configure(bg=self.COLOR_CARD)
            cap_win.grab_set()

            tk.Label(cap_win, text="💵 إضافة سيولة مالية جديدة", font=("Segoe UI", 13, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_BLUE).pack(pady=15)

            tk.Label(cap_win, text="المبلغ المضاف:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT).pack(pady=2)
            amt_e = tk.Entry(cap_win, justify="center", font=("Segoe UI", 11), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, validate="key", validatecommand=self.vcmd_num)
            amt_e.pack(pady=5)
            amt_e.focus()

            tk.Label(cap_win, text="ملاحظات / البيان:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT).pack(pady=2)
            note_e = tk.Entry(cap_win, justify="right", font=("Segoe UI", 10), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT)
            note_e.pack(pady=5)

            amt_e.bind("<Return>", lambda e: note_e.focus())
            note_e.bind("<Return>", lambda e: save_cap())

            def save_cap():
                try:
                    val = float(amt_e.get().strip())
                    if val <= 0: raise ValueError
                    notes = note_e.get().strip() or "تغذية سيولة مالية"
                    self.db.add_capital_injection(val, notes, self.current_user['id'])
                    messagebox.showinfo("نجاح", "تمت إضافة السيولة المالية وتحديث التقرير بنجاح!")
                    cap_win.destroy()
                    refresh_fin_ui()
                except ValueError:
                    messagebox.showerror("خطأ", "برجاء إدخال مبلغ صحيح!")

            tk.Button(cap_win, text="حفظ السيولة", command=save_cap, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"), padx=15).pack(pady=15)

        tk.Button(act_fin_frame, text="➕ إضافة / تغذية سيولة مالية جديدة", command=open_add_capital_popup, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 11, "bold"), padx=15, pady=5, cursor="hand2").pack(side="right", padx=10)
        tk.Button(act_fin_frame, text="🔄 تحديث البيانات", command=refresh_fin_ui, bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold"), padx=15, pady=5, cursor="hand2").pack(side="left", padx=10)

        tk.Label(tab_sales, text="📊 تقارير المبيعات والأرباح التفصيلية", font=("Segoe UI", 15, "bold"), bg=self.COLOR_BG, fg=self.COLOR_BLUE).pack(pady=10)

        cards_frame = tk.Frame(tab_sales, bg=self.COLOR_BG)
        cards_frame.pack(fill="x", padx=15, pady=5)

        lbl_tot_sales = tk.Label(cards_frame, text="المبيعات: 0", font=("Segoe UI", 11, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_TEXT, width=25, pady=10)
        lbl_tot_sales.pack(side="right", padx=5)

        lbl_tot_profit = tk.Label(cards_frame, text="صافي الربح: 0", font=("Segoe UI", 11, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_ACCENT, width=25, pady=10)
        lbl_tot_profit.pack(side="right", padx=5)

        filter_frame = tk.Frame(tab_sales, bg=self.COLOR_BG)
        filter_frame.pack(pady=5)

        tk.Label(filter_frame, text="من تاريخ:", bg=self.COLOR_BG, fg=self.COLOR_TEXT).pack(side="right", padx=2)
        e_from = tk.Entry(filter_frame, width=12, justify="center", bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT)
        e_from.insert(0, datetime.now().strftime("%Y-%m-01"))
        e_from.pack(side="right", padx=5)

        tk.Label(filter_frame, text="إلى تاريخ:", bg=self.COLOR_BG, fg=self.COLOR_TEXT).pack(side="right", padx=2)
        e_to = tk.Entry(filter_frame, width=12, justify="center", bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT)
        e_to.insert(0, datetime.now().strftime("%Y-%m-%d"))
        e_to.pack(side="right", padx=5)

        can_see_cost = self.has_permission('can_view_buy_price')
        cols = ("البائع", "التاريخ", "العميل", "الربح", "المتبقي", "النقدي", "البيع", "الشراء", "السيريال", "الموديل", "ID الجهاز")
        if not can_see_cost:
            cols = ("البائع", "التاريخ", "العميل", "المتبقي", "النقدي", "البيع", "السيريال", "الموديل", "ID الجهاز")

        tree = ttk.Treeview(tab_sales, columns=cols, show="headings")
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=90, anchor="center")
        tree.pack(fill="both", expand=True, padx=15, pady=5)
        self.bind_treeview_double_click(tree, "ID الجهاز")

        def load_rep():
            for row in tree.get_children(): tree.delete(row)
            d_from = e_from.get().strip()
            d_to = e_to.get().strip()

            sales = self.db.get_sales_report_advanced(d_from, d_to)
            tot_s = sum(float(s['sell_price']) for s in sales)
            tot_p = sum(float(s['net_profit']) for s in sales)

            lbl_tot_sales.config(text=f"إجمالي المبيعات: {fmt_curr(tot_s)}")
            if can_see_cost:
                lbl_tot_profit.config(text=f"صافي الأرباح: {fmt_curr(tot_p)}")
            else:
                lbl_tot_profit.config(text="صافي الأرباح: ***")

            for s in sales:
                if can_see_cost:
                    vals = (s['seller_name'], s['sell_date_formatted'], s['customer_name'], 
                            fmt_curr(s['net_profit']), fmt_curr(s['remaining_balance']), 
                            fmt_curr(s['cash_received']), fmt_curr(s['sell_price']), 
                            fmt_curr(s['buy_price']), s['imei_serial'], s['model'], s['device_id'])
                else:
                    vals = (s['seller_name'], s['sell_date_formatted'], s['customer_name'], 
                            fmt_curr(s['remaining_balance']), fmt_curr(s['cash_received']), 
                            fmt_curr(s['sell_price']), s['imei_serial'], s['model'], s['device_id'])
                tree.insert("", "end", values=vals)

        tk.Button(filter_frame, text="تطبيق الفلترة", command=load_rep, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 9, "bold")).pack(side="right", padx=5)
        load_rep()

if __name__ == "__main__":
    app = MasterMobileApp()
    app.mainloop()