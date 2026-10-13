import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from database import DatabaseManager
from invoice_generator import generate_invoice_image, generate_invoice_pages, trigger_system_print_or_open
from datetime import datetime
from PIL import Image, ImageTk
import calendar
import os
import json
import re
import shutil

# =================================================================================
# قاموس الصلاحيات الشامل (35+ صلاحية)
# =================================================================================
PERMISSIONS_DICT = {
    'can_view_buy_price': 'رؤية سعر الشراء والتكلفة',
    'can_manage_inventory': 'إدارة المخزون والموردين',
    'can_manage_users': 'إدارة المستخدمين والصلاحيات',
    'can_view_reports': 'الدخول لشاشة التقارير المالية',
    'can_process_returns': 'إجراء مرتجعات المبيعات',
    'can_edit_prices': 'تعديل أسعار البيع',

    'can_view_inventory': 'عرض شاشة المخزون',
    'can_edit_inventory': 'تعديل بيانات الأجهزة بالمخزون',
    'can_delete_inventory': 'حذف الأجهزة من المخزون',
    'can_view_device_details': 'فتح بطاقة فحص ومواصفات الجهاز',

    'can_buy_devices': 'فتح شاشة المشتريات وإدخال أجهزة',
    'can_add_supplier_in_buy': 'إضافة مورد أثناء الشراء',

    'can_view_sales_screen': 'فتح شاشة المبيعات',
    'can_execute_sale': 'تأكيد وإتمام عمليات البيع',
    'can_print_sale_invoice': 'طباعة فواتير البيع',
    'can_sell_below_cost': 'السماح بالبيع بأقل من سعر التكلفة',
    'can_edit_transactions': 'تعديل وحذف العمليات والديون',
    'can_delete_sales': 'إلغاء وحذف عمليات البيع واسترجاعها للمخزون',
    'can_edit_operation_dates': 'صلاحية تحديد وتعديل تواريخ العمليات (يدوياً أو تلقائياً)',
    'can_edit_transaction_date': 'تعديل تاريخ العمليات يدوياً أو تركه تلقائي',
    'can_custom_print_terms': 'تخصيص بنود وضمان الفاتورة المطبوعة',

    'can_view_customer_debts': 'عرض شاشة ديون العملاء (الخرج)',
    'can_collect_customer_debt': 'تحصيل دفعات من ديون العملاء',
    'can_print_customer_debt': 'طباعة إيصال / كشف حساب عميل',

    'can_view_supplier_debts': 'عرض شاشة حسابات الموردين',
    'can_pay_supplier_debt': 'سداد دفعات لفواتير الموردين',
    'can_refund_supplier_credit': 'استرداد رصيد وأمانات الموردين نقداً للخزينة',
    'can_manage_suppliers': 'إدارة وتعديل بيانات الموردين',
    'can_delete_suppliers': 'حذف وأرشفة الموردين',
    'can_print_supplier_invoice': 'طباعة فواتير وكشوف الموردين',

    'can_view_capital_details': 'عرض تفاصيل ومعادلة رأس المال الشامل',
    'can_view_liquidity': 'رؤية السيولة ورأس المال',
    'can_add_liquidity': 'إضافة سيولة مالية جديدة',
    'can_delete_liquidity_tx': 'حذف وتسوية حركات السيولة',
    'can_view_liquidity_log': 'عرض سجل حركات السيولة',
    'can_view_profits': 'رؤية الأرباح',
    'can_view_sales_report': 'عرض سجل المبيعات بالتواريخ',
    'can_export_reports': 'تصدير وطباعة السجل والتقارير المالية',
    'can_view_audit_logs': 'عرض السجل الدقيق لعمليات وتعديلات النظام',
    'can_filter_audit_logs': 'البحث والفلترة المتقدمة في سجل العمليات'
}

PERMISSION_GROUPS = [
    ("📦 المخزون والأجهزة", [
        ('can_view_inventory', 'عرض شاشة المخزون والبحث'),
        ('can_edit_inventory', 'تعديل بيانات ومواصفات الأجهزة'),
        ('can_delete_inventory', 'حذف الأجهزة من المخزون'),
        ('can_view_buy_price', 'رؤية سعر الشراء والتكلفة'),
        ('can_view_device_details', 'فتح بطاقة فحص ومواصفات الجهاز'),
        ('can_manage_inventory', 'الصلاحية العامة لإدارة المخزون'),
    ]),
    ("📥 المشتريات والتوريد", [
        ('can_buy_devices', 'فتح شاشة المشتريات وإدخال أجهزة'),
        ('can_add_supplier_in_buy', 'إضافة مورد من شاشة المشتريات'),
    ]),
    ("🛒 المبيعات والمرتجعات", [
        ('can_view_sales_screen', 'فتح شاشة المبيعات'),
        ('can_execute_sale', 'إتمام وتأكيد عمليات البيع'),
        ('can_edit_prices', 'تعديل أسعار البيع المباشرة'),
        ('can_sell_below_cost', 'السماح بالبيع بأقل من سعر التكلفة'),
        ('can_edit_transactions', 'تعديل وحذف العمليات والديون'),
        ('can_delete_sales', 'إلغاء وحذف عمليات البيع والاسترجاع'),
        ('can_edit_operation_dates', 'تحديد وتعديل تواريخ العمليات (يدوياً أو تلقائياً)'),
        ('can_edit_transaction_date', 'تعديل تاريخ العمليات يدوياً أو تركه تلقائي'),
        ('can_print_sale_invoice', 'طباعة فواتير البيع'),
        ('can_custom_print_terms', 'تخصيص بنود وضمان الفاتورة المطبوعة'),
        ('can_process_returns', 'استرجاع الأجهزة المباعة للمخزون'),
    ]),
    ("💳 ديون العملاء (الخرج)", [
        ('can_view_customer_debts', 'عرض شاشة ديون العملاء (الخرج)'),
        ('can_collect_customer_debt', 'تحصيل دفعات من العملاء'),
        ('can_print_customer_debt', 'طباعة إيصال / كشف حساب عميل'),
    ]),
    ("🏭 حسابات الموردين", [
        ('can_view_supplier_debts', 'عرض فواتير ومديونيات الموردين'),
        ('can_pay_supplier_debt', 'سداد دفعات للموردين'),
        ('can_refund_supplier_credit', 'استرداد رصيد الموردين للخزينة'),
        ('can_manage_suppliers', 'إدارة وتعديل بيانات الموردين'),
        ('can_delete_suppliers', 'حذف وأرشفة الموردين'),
        ('can_print_supplier_invoice', 'طباعة فواتير الموردين'),
    ]),
    ("📊 التقارير والسيولة والأرباح", [
        ('can_view_reports', 'الدخول لشاشة التقارير المالية'),
        ('can_view_capital_details', 'عرض تفاصيل ومعادلة رأس المال'),
        ('can_view_liquidity', 'رؤية السيولة ورأس المال'),
        ('can_add_liquidity', 'إضافة سيولة مالية جديدة'),
        ('can_delete_liquidity_tx', 'حذف وتسوية حركات السيولة'),
        ('can_view_liquidity_log', 'عرض سجل حركات السيولة'),
        ('can_view_profits', 'رؤية صافي الأرباح'),
        ('can_view_sales_report', 'عرض سجل المبيعات بالتواريخ'),
        ('can_export_reports', 'تصدير وطباعة السجل والتقارير'),
    ]),
    ("📜 سجل العمليات والرقابة", [
        ('can_view_audit_logs', 'عرض السجل الدقيق لعمليات النظام'),
        ('can_filter_audit_logs', 'البحث والفلترة المتقدمة في السجل'),
    ]),
    ("👥 إدارة المستخدمين", [
        ('can_manage_users', 'إدارة المستخدمين والصلاحيات'),
    ])
]

BRAND_LIST = [
    "iPhone", "Samsung", "Xiaomi", "Redmi", "Oppo", "Realme", "Honor", "Infinix", "Huawei"
]

BRAND_MODELS_SUGGESTIONS = {
    "iPhone": [
        "17 Pro Max", "17 Pro", "Air", "17",
        "16 Pro Max", "16 Pro", "16 Plus", "16",
        "15 Pro Max", "15 Pro", "15 Plus", "15",
        "14 Pro Max", "14 Pro", "14 Plus", "14",
        "13 Pro Max", "13 Pro", "13", "13 Mini",
        "12 Pro Max", "12 Pro", "12", "12 Mini",
        "11 Pro Max", "11 Pro", "11",
        "XS Max", "XS", "XR", "X", "8 Plus", "8", "7 Plus", "7", "6s Plus", "6s",
        "SE 4 (2025)", "SE (2022)", "SE (2020)"
    ],
    "Samsung": [
        "S26 Ultra", "S26 Plus", "S26", "S25 Ultra", "S25 Plus", "S25", "S24 Ultra", "S24 Plus", "S24", "S24 FE",
        "S23 Ultra", "S23 Plus", "S23", "S23 FE", "S22 Ultra", "S22 Plus", "S22", "S21 Ultra", "S21 Plus", "S21 FE",
        "Note 20 Ultra", "Note 20", "Note 10 Plus", "Note 10", "Z Fold 6", "Z Fold 5", "Z Flip 6", "Z Flip 5",
        "A56", "A55", "A54", "A53", "A52s 5G", "A36", "A35", "A34", "A25", "A16", "A15", "A14", "A06", "A05s"
    ],
    "Xiaomi": [
        "15 Ultra", "15 Pro", "15", "14 Ultra", "14 Pro", "14", "13T Pro", "13T", "12T Pro", "12T",
        "F7 Pro", "F6 Pro", "F6", "X7 Pro", "X6 Pro", "M7 Pro", "M6 Pro", "C75", "C65"
    ],
    "Redmi": [
        "Note 14 Pro Plus", "Note 14 Pro", "Note 14", "Note 13 Pro Plus", "Note 13 Pro", "Note 13", "Note 13C",
        "Note 12 Pro Plus", "Note 12 Pro", "Note 12", "14C", "13C", "12C", "A3", "A3x"
    ],
    "Oppo": [
        "Find X8 Ultra", "Find X8 Pro", "Find X8", "Reno 14 Pro", "Reno 13 Pro", "Reno 12 Pro", "Reno 12", "Reno 11",
        "A80", "A79", "A78", "A60", "A58", "A38", "A18"
    ],
    "Realme": [
        "GT 7 Pro", "GT 6", "14 Pro Plus", "13 Pro Plus", "12 Pro Plus", "11 Pro Plus", "C67", "C65", "C63", "C55", "C53"
    ],
    "Honor": [
        "Magic 7 Pro", "Magic 6 Pro", "300 Pro", "200 Pro", "200", "90", "X9c", "X9b", "X8b", "X7c", "X6b"
    ],
    "Infinix": [
        "Zero 40 5G", "GT 20 Pro", "Note 50 Pro", "Note 40 Pro", "Hot 50 Pro", "Hot 40", "Smart 9", "Smart 8"
    ],
    "Huawei": [
        "Pura 80 Ultra", "Pura 70 Ultra", "Pura 70 Pro", "Pura 70", "Mate 70 Pro", "Mate 60 Pro", "Nova 13 Pro", "Nova 12s"
    ]
}


def fix_bidi(text):
    if text is None:
        return ""
    s = str(text).replace('\u200f', '').replace('\u200e', '').replace('\u202b', '').replace('\u202c', '').strip()
    if not s:
        return ""
    return f"\u200f{s}\u200f"


def fmt_curr(val):
    try:
        s = str(val).replace('\u200f', '').replace('\u200e', '').replace('ج.م', '').replace(',', '').strip()
        f = float(s)
        return f"\u200f{f:,.2f} ج.م\u200f"
    except (ValueError, TypeError):
        return "\u200f0.00 ج.م\u200f"


def fmt_num(val):
    try:
        s = str(val).replace('\u200f', '').replace('\u200e', '').replace('ج.م', '').replace(',', '').strip()
        f = float(s)
        if f.is_integer():
            return f"{int(f)}"
        return f"{f:.2f}"
    except (ValueError, TypeError):
        return str(val or "")


def clean_id_val(val):
    if val is None:
        return None
    if isinstance(val, int):
        return val
    s = str(val).replace('\u200f', '').replace('\u200e', '').replace('#', '').strip()
    if s.isdigit():
        return int(s)
    m = re.search(r'\d+', s)
    return int(m.group(0)) if m else None


class MasterMobileApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("مركز هشام كيوان لإدارة الهواتف")
        self.geometry("1340x840")

        self.BRAND_LIST = BRAND_LIST
        self.BRAND_MODELS_SUGGESTIONS = BRAND_MODELS_SUGGESTIONS

        self.logo_top = None
        self.logo_login = None
        self.load_logo_icon()

        self.is_dark_mode = True
        self.is_colorful_mode = True
        self.apply_theme_colors()

        self.configure(bg=self.COLOR_BG)
        self.db = DatabaseManager()
        self.current_user = None
        self.current_view_func = None
        self.current_view_name = None

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
                img_login.thumbnail((95, 95), Image.Resampling.LANCZOS)
                self.logo_login = ImageTk.PhotoImage(img_login)

                self.iconphoto(True, self.logo_top)
            except Exception as e:
                print(f"Notice: Logo load: {e}")

    def _create_scrollable_frame(self, parent_win, bg_color=None, pad_x=14, pad_y=8):
        bg_c = bg_color or self.COLOR_BG
        outer = tk.Frame(parent_win, bg=bg_c)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg=bg_c, highlightthickness=0, bd=0)
        v_scroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=v_scroll.set)

        v_scroll.pack(side="left", fill="y")
        canvas.pack(side="right", fill="both", expand=True)

        inner_frame = tk.Frame(canvas, bg=bg_c, padx=pad_x, pady=pad_y)
        win_id = canvas.create_window((0, 0), window=inner_frame, anchor="nw")

        def _on_frame_configure(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            canvas.itemconfig(win_id, width=event.width)

        inner_frame.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(event):
            if not canvas.winfo_exists():
                return
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")
            elif event.delta:
                step = -1 if event.delta > 0 else 1
                canvas.yview_scroll(step, "units")

        parent_win.bind("<MouseWheel>", _on_mousewheel)
        parent_win.bind("<Button-4>", _on_mousewheel)
        parent_win.bind("<Button-5>", _on_mousewheel)

        return inner_frame

    def _bind_enter_chain(self, widgets_list, final_callback=None):
        for idx, w in enumerate(widgets_list):
            nxt = widgets_list[idx + 1] if idx < len(widgets_list) - 1 else None
            if isinstance(w, tk.Checkbutton):
                try:
                    w.config(takefocus=True)
                except Exception:
                    pass
                def _make_toggle(cb):
                    return lambda e: (cb.invoke(), "break")[1]
                w.bind("<Shift_L>", _make_toggle(w), add="+")
                w.bind("<Shift_R>", _make_toggle(w), add="+")
                w.bind("<Shift-KeyPress>", _make_toggle(w), add="+")
                w.bind("<space>", _make_toggle(w), add="+")

            if nxt is not None:
                def _make_jump(target):
                    def _do_jump(e):
                        target.focus_set()
                        return "break"
                    return _do_jump
                w.bind("<Return>", _make_jump(nxt), add="+")
            elif final_callback:
                def _make_final(fn):
                    def _do_final(e):
                        fn()
                        return "break"
                    return _do_final
                w.bind("<Return>", _make_final(final_callback), add="+")

    @property
    def current_user_id(self):
        if self.current_user and isinstance(self.current_user, dict):
            return self.current_user.get('id')
        return None

    def has_permission(self, perm_key):
        if not self.current_user:
            return False

        uname = str(self.current_user.get('username') or '').strip().lower()
        urole = str(self.current_user.get('role') or '').strip().lower()
        is_admin_account = (uname == 'admin' or urole == 'admin')

        perms = self.current_user.get('permissions', {})
        if isinstance(perms, str):
            try:
                perms = json.loads(perms)
            except Exception:
                perms = {}
        if not isinstance(perms, dict):
            perms = {}

        if perm_key in ('can_edit_operation_dates', 'can_edit_transaction_date'):
            if 'can_edit_operation_dates' in perms or 'can_edit_transaction_date' in perms:
                return bool(perms.get('can_edit_operation_dates') or perms.get('can_edit_transaction_date'))

        if perm_key in ('can_refund_supplier_credit',):
            if 'can_refund_supplier_credit' in perms:
                return bool(perms.get('can_refund_supplier_credit'))

        if perm_key in ('can_view_audit_logs', 'can_filter_audit_logs'):
            if perm_key in perms:
                return bool(perms.get(perm_key))

        if perm_key in perms:
            return bool(perms[perm_key])

        if is_admin_account:
            return True

        fallback_map = {
            'can_view_inventory': None,
            'can_edit_inventory': 'can_manage_inventory',
            'can_delete_inventory': 'can_manage_inventory',
            'can_buy_devices': 'can_manage_inventory',
            'can_add_supplier_in_buy': 'can_manage_inventory',
            'can_view_sales_screen': None,
            'can_execute_sale': None,
            'can_print_sale_invoice': None,
            'can_view_customer_debts': None,
            'can_collect_customer_debt': None,
            'can_print_customer_debt': None,
            'can_view_supplier_debts': 'can_manage_inventory',
            'can_pay_supplier_debt': 'can_manage_inventory',
            'can_manage_suppliers': 'can_manage_inventory',
            'can_print_supplier_invoice': 'can_manage_inventory',
            'can_view_liquidity': 'can_view_reports',
            'can_add_liquidity': 'can_view_reports',
            'can_view_liquidity_log': 'can_view_reports',
            'can_view_profits': 'can_view_reports',
            'can_view_sales_report': 'can_view_reports',
            'can_delete_sales': 'can_edit_transactions',
            'can_refund_supplier_credit': 'can_manage_suppliers',
            'can_view_capital_details': 'can_view_reports',
            'can_delete_liquidity_tx': 'can_manage_users',
            'can_edit_operation_dates': 'can_manage_users',
            'can_edit_transaction_date': 'can_manage_users',
        }
        parent_key = fallback_map.get(perm_key, perm_key)
        if parent_key is None:
            return True
        return bool(perms.get(parent_key, False))

    def get_model_suggestions_for_brand(self, brand_text):
        b_clean = (brand_text or "").strip()
        arabic_alias = {
            "ايفون": "iPhone", "آيفون": "iPhone", "ابل": "iPhone", "أبل": "iPhone", "apple": "iPhone",
            "سامسونج": "Samsung", "سام": "Samsung", "شاومي": "Xiaomi", "ريدمي": "Redmi",
            "ريلمي": "Realme", "اوبو": "Oppo", "أوبو": "Oppo", "هونر": "Honor", "انفينكس": "Infinix", "هواوي": "Huawei"
        }
        target_brand = arabic_alias.get(b_clean.lower(), b_clean)
        suggestions = []
        for k, models in BRAND_MODELS_SUGGESTIONS.items():
            if not target_brand or k.lower() == target_brand.lower() or target_brand.lower() in k.lower() or k.lower() in target_brand.lower():
                suggestions.extend(models)
        db_models = self.db.get_distinct_models_by_category(target_brand)
        for m in db_models:
            if m not in suggestions:
                suggestions.append(m)
        return suggestions

    def detect_brand_from_model(self, model_name):
        m_clean = (model_name or "").strip().lower()
        if not m_clean:
            return None
        for brand, models in BRAND_MODELS_SUGGESTIONS.items():
            for m in models:
                if m.lower() == m_clean or m_clean in m.lower():
                    return brand
        return None

    def apply_theme_colors(self):
        if self.is_dark_mode:
            self.COLOR_BORDER = "#2e3b52"
            if self.is_colorful_mode:
                self.COLOR_BG = "#0b192c"
                self.COLOR_CARD = "#152238"
                self.COLOR_ACCENT = "#10b981"
                self.COLOR_BLUE = "#38bdf8"
                self.COLOR_PURPLE = "#0284c7"
                self.COLOR_WARN = "#f59e0b"
                self.COLOR_TEAL = "#14b8a6"
                self.COLOR_INDIGO = "#2563eb"
                self.COLOR_TEXT = "#ffffff"
                self.COLOR_MUTED = "#94a3b8"
                self.COLOR_DANGER = "#ef4444"
                self.COLOR_ENTRY_BG = "#1e293b"
                self.COLOR_TOPBAR = "#070f1e"
                self.COLOR_TREE_BG = "#0b192c"
                self.COLOR_TREE_ALT = "#1e3a5f"
                self.NAV_COLORS = {
                    "inventory": ("#1e40af", "#2563eb"),
                    "sale": ("#0f766e", "#0d9488"),
                    "buy": ("#0369a1", "#0284c7"),
                    "cust_debts": ("#1d4ed8", "#3b82f6"),
                    "supp_debts": ("#0e7490", "#06b6d4"),
                    "reports": ("#1e3a8a", "#2563eb"),
                    "audit": ("#0f766e", "#14b8a6"),
                    "users": ("#334155", "#475569"),
                }
            else:
                self.COLOR_BG = "#0b192c"
                self.COLOR_CARD = "#152238"
                self.COLOR_ACCENT = "#10b981"
                self.COLOR_BLUE = "#38bdf8"
                self.COLOR_PURPLE = "#64748b"
                self.COLOR_WARN = "#f59e0b"
                self.COLOR_TEAL = "#0284c7"
                self.COLOR_INDIGO = "#3b82f6"
                self.COLOR_TEXT = "#ffffff"
                self.COLOR_MUTED = "#94a3b8"
                self.COLOR_DANGER = "#ef4444"
                self.COLOR_ENTRY_BG = "#1e293b"
                self.COLOR_TOPBAR = "#070f1e"
                self.COLOR_TREE_BG = "#0b192c"
                self.COLOR_TREE_ALT = "#1e3a5f"
                self.NAV_COLORS = {}
        else:
            self.COLOR_BG = "#f8fafc"
            self.COLOR_CARD = "#ffffff"
            self.COLOR_ENTRY_BG = "#ffffff"
            self.COLOR_BORDER = "#cbd5e1"
            self.COLOR_TEXT = "#0f172a"
            self.COLOR_MUTED = "#64748b"
            self.COLOR_TOPBAR = "#ffffff"
            self.COLOR_TREE_BG = "#ffffff"
            self.COLOR_TREE_ALT = "#bae6fd"
            self.COLOR_ACCENT = "#059669"
            self.COLOR_BLUE = "#0284c7"
            self.COLOR_WARN = "#d97706"
            self.COLOR_TEAL = "#0d9488"
            self.COLOR_INDIGO = "#2563eb"
            self.COLOR_DANGER = "#dc2626"
            if self.is_colorful_mode:
                self.COLOR_PURPLE = "#0284c7"
                self.NAV_COLORS = {
                    "inventory": ("#2563eb", "#1d4ed8"),
                    "sale": ("#0d9488", "#0f766e"),
                    "buy": ("#0284c7", "#0369a1"),
                    "cust_debts": ("#3b82f6", "#2563eb"),
                    "supp_debts": ("#0891b2", "#0e7490"),
                    "reports": ("#1d4ed8", "#1e40af"),
                    "audit": ("#0f766e", "#14b8a6"),
                    "users": ("#475569", "#334155"),
                }
            else:
                self.COLOR_PURPLE = "#475569"
                self.NAV_COLORS = {}

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure(
            "Treeview",
            background=self.COLOR_TREE_BG,
            foreground=self.COLOR_TEXT,
            rowheight=40,
            fieldbackground=self.COLOR_TREE_BG,
            font=("Segoe UI", 11, "bold")
        )
        self.style.map("Treeview", background=[('selected', self.COLOR_BLUE)], foreground=[('selected', '#ffffff')])

        heading_bg = self.COLOR_BLUE if not self.is_dark_mode else (self.COLOR_INDIGO if self.is_colorful_mode else self.COLOR_TOPBAR)
        heading_fg = "#ffffff"
        self.style.configure(
            "Treeview.Heading",
            background=heading_bg,
            foreground=heading_fg,
            font=("Segoe UI", 11, "bold"),
            relief="flat"
        )
        self.style.map("Treeview.Heading", background=[('active', self.COLOR_BLUE)])
        self.style.configure("TNotebook", background=self.COLOR_BG, borderwidth=0)
        self.style.configure("TNotebook.Tab", background=self.COLOR_CARD, foreground=self.COLOR_TEXT, padding=[16, 6], font=("Segoe UI", 10, "bold"))
        self.style.map("TNotebook.Tab", background=[("selected", self.COLOR_BLUE)], foreground=[("selected", "#ffffff")])

        self.style.configure(
            "TCombobox",
            fieldbackground=self.COLOR_ENTRY_BG,
            background=self.COLOR_CARD,
            foreground=self.COLOR_TEXT,
            arrowcolor=self.COLOR_TEXT,
            darkcolor=self.COLOR_BORDER,
            lightcolor=self.COLOR_BORDER
        )
        self.style.map(
            "TCombobox",
            fieldbackground=[('readonly', self.COLOR_ENTRY_BG)],
            foreground=[('readonly', self.COLOR_TEXT)]
        )
        self.style.configure(
            "Vertical.TScrollbar",
            background=self.COLOR_CARD,
            troughcolor=self.COLOR_BG,
            bordercolor=self.COLOR_BORDER,
            arrowcolor=self.COLOR_MUTED
        )

    def configure_tree_row_colors(self, tree):
        if not self.is_dark_mode:
            odd_bg = "#ffffff"
            even_bg = "#e0f2fe"
            fg_col = "#090d16"
        else:
            odd_bg = "#0d1b2e"
            even_bg = "#182c47"
            fg_col = "#ffffff"

        tree.tag_configure('oddrow', background=odd_bg, foreground=fg_col)
        tree.tag_configure('evenrow', background=even_bg, foreground=fg_col)

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme_colors()
        self.configure(bg=self.COLOR_BG)
        self.setup_styles()
        current_func = self.current_view_func
        self.build_main_ui(keep_view=True)
        if current_func:
            current_func()

    def toggle_colorful_mode(self):
        self.is_colorful_mode = not self.is_colorful_mode
        self.apply_theme_colors()
        self.configure(bg=self.COLOR_BG)
        self.setup_styles()
        current_func = self.current_view_func
        self.build_main_ui(keep_view=True)
        if current_func:
            current_func()

    def _build_rtl_info_grid(self, parent, pairs_list):
        grid_f = tk.Frame(parent, bg=self.COLOR_CARD)
        grid_f.pack(fill="x", padx=6, pady=4)
        for c_i in range(4):
            grid_f.grid_columnconfigure(c_i, weight=1 if c_i in (0, 2) else 0)

        for r_idx, row_item in enumerate(pairs_list):
            if not row_item:
                continue

            if isinstance(row_item, (tuple, list)) and len(row_item) == 2 and isinstance(row_item[0], str):
                lbl1, val1 = row_item
                item2 = None
            elif isinstance(row_item, (tuple, list)) and len(row_item) >= 1 and isinstance(row_item[0], (tuple, list)):
                lbl1, val1 = row_item[0]
                item2 = row_item[1] if len(row_item) > 1 else None
            else:
                continue

            def get_cell_colors(lbl, val):
                lbl_s = str(lbl or "").strip()
                if any(k in lbl_s for k in ["سعر الشراء", "التكلفة"]):
                    return (self.COLOR_WARN, "#7c2d12" if not self.is_dark_mode else "#fef3c7")
                elif any(k in lbl_s for k in ["سعر البيع", "المبدئي", "الربح"]):
                    return (self.COLOR_ACCENT, "#064e3b" if not self.is_dark_mode else "#d1fae5")
                elif any(k in lbl_s for k in ["السيريال", "IMEI"]):
                    return (self.COLOR_BLUE, "#0c4a6e" if not self.is_dark_mode else "#e0f2fe")
                elif any(k in lbl_s for k in ["الخرج", "المتبقي", "خسارة"]):
                    return (self.COLOR_DANGER, "#7f1d1d" if not self.is_dark_mode else "#fee2e2")
                return (self.COLOR_ENTRY_BG, self.COLOR_TEXT)

            bg1, fg1 = get_cell_colors(lbl1, val1)

            tk.Label(
                grid_f, text=fix_bidi(lbl1), font=("Segoe UI", 11, "bold"),
                bg=self.COLOR_CARD, fg=self.COLOR_TEXT, anchor="e"
            ).grid(row=r_idx, column=3, sticky="e", padx=(8, 4), pady=5)
            tk.Label(
                grid_f, text=fix_bidi(val1), font=("Segoe UI", 11, "bold"),
                bg=bg1, fg=fg1, anchor="e", padx=12, pady=5
            ).grid(row=r_idx, column=2, sticky="ew", padx=(10, 4), pady=5)

            if item2 and isinstance(item2, (tuple, list)) and len(item2) >= 2 and item2[0]:
                lbl2, val2 = item2[0], item2[1]
                bg2, fg2 = get_cell_colors(lbl2, val2)
                tk.Label(
                    grid_f, text=fix_bidi(lbl2), font=("Segoe UI", 11, "bold"),
                    bg=self.COLOR_CARD, fg=self.COLOR_TEXT, anchor="e"
                ).grid(row=r_idx, column=1, sticky="e", padx=(8, 4), pady=5)
                tk.Label(
                    grid_f, text=fix_bidi(val2), font=("Segoe UI", 11, "bold"),
                    bg=bg2, fg=fg2, anchor="e", padx=12, pady=5
                ).grid(row=r_idx, column=0, sticky="ew", padx=(4, 4), pady=5)

        return grid_f

    def _create_operation_date_picker(self, parent, label_text="📅 تاريخ وتوقيت العملية:"):
        can_edit = self.has_permission('can_edit_operation_dates') or self.has_permission('can_edit_transaction_date')
        lbl_txt = label_text if (label_text and label_text.strip()) else "📅 تاريخ وتوقيت العملية:"
        
        if not can_edit:
            ro_box = tk.Frame(parent, bg=self.COLOR_CARD, padx=12, pady=5, highlightthickness=1, highlightbackground=self.COLOR_BORDER)
            ro_box.pack(fill="x", pady=4)
            tk.Label(
                ro_box, text=fix_bidi(lbl_txt),
                font=("Segoe UI", 10, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_TEXT
            ).pack(side="right", padx=6)
            cur_time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            tk.Label(
                ro_box, text=cur_time_str,
                font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_BLUE,
                padx=10, pady=2, relief="flat"
            ).pack(side="right", padx=4)
            tk.Label(
                ro_box, text="🔒 مسجل تلقائياً بالوقت الفعلي",
                font=("Segoe UI", 9, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_MUTED
            ).pack(side="right", padx=6)
            return lambda: None

        date_box = tk.Frame(parent, bg=self.COLOR_CARD, padx=12, pady=5, highlightthickness=1, highlightbackground=self.COLOR_BORDER)
        date_box.pack(fill="x", pady=4)

        tk.Label(
            date_box, text=fix_bidi(lbl_txt),
            font=("Segoe UI", 10, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_BLUE
        ).pack(side="right", padx=6)

        ent_date = tk.Entry(
            date_box, font=("Segoe UI", 11, "bold"),
            bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT,
            justify="center", width=18, state="normal"
        )
        ent_date.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M"))
        ent_date.pack(side="right", padx=4, ipady=3)

        def open_calendar_picker():
            def on_cal_selected():
                cur = ent_date.get().strip()
                if len(cur) == 10:
                    ent_date.delete(0, tk.END)
                    ent_date.insert(0, f"{cur} {datetime.now().strftime('%H:%M')}")
            self.open_date_picker(ent_date, on_select_callback=on_cal_selected, allow_future=False)

        btn_cal = tk.Button(
            date_box, text="📅", font=("Segoe UI", 10, "bold"),
            bg=self.COLOR_ENTRY_BG, fg=self.COLOR_BLUE, relief="flat", cursor="hand2",
            padx=8, pady=2, command=open_calendar_picker
        )
        btn_cal.pack(side="right", padx=2)

        def set_to_today():
            ent_date.delete(0, tk.END)
            ent_date.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M"))

        def set_to_this_month():
            ent_date.delete(0, tk.END)
            ent_date.insert(0, datetime.now().strftime("%Y-%m-01 00:00"))

        def clear_date_field():
            ent_date.delete(0, tk.END)

        tk.Button(
            date_box, text="اليوم", font=("Segoe UI", 8, "bold"),
            bg=self.COLOR_ACCENT, fg="white", relief="flat", cursor="hand2",
            padx=6, pady=2, command=set_to_today
        ).pack(side="right", padx=2)

        tk.Button(
            date_box, text="هذا الشهر", font=("Segoe UI", 8, "bold"),
            bg=self.COLOR_PURPLE, fg="white", relief="flat", cursor="hand2",
            padx=6, pady=2, command=set_to_this_month
        ).pack(side="right", padx=2)

        tk.Button(
            date_box, text="مسح", font=("Segoe UI", 8, "bold"),
            bg=self.COLOR_ENTRY_BG, fg=self.COLOR_MUTED, relief="flat", cursor="hand2",
            padx=6, pady=2, command=clear_date_field
        ).pack(side="right", padx=2)

        def get_date_val():
            val = ent_date.get().strip()
            if not val:
                return None
            parsed_dt = None
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    parsed_dt = datetime.strptime(val, fmt)
                    break
                except ValueError:
                    continue
            if not parsed_dt:
                raise ValueError(f"صيغة التاريخ غير صحيحة ({val})! يرجى استخدام صيغة YYYY-MM-DD HH:MM مثل 2026-05-15 14:30")
            if parsed_dt.date() > datetime.now().date():
                raise ValueError("لا يمكن تسجيل عملية بتاريخ مستقبلي! يُسمح فقط بالتواريخ السابقة أو تاريخ اليوم.")
            return parsed_dt.strftime("%Y-%m-%d %H:%M:%S")

        return get_date_val

    def open_edit_record_date_modal(self, record_type, record_id, current_date_str="", on_success_callback=None):
        if not (self.has_permission('can_edit_operation_dates') or self.has_permission('can_edit_transaction_date')):
            messagebox.showerror("صلاحيات غير كافية", "لا تملك صلاحية تعديل تواريخ العمليات المسجلة!")
            return

        clean_id = clean_id_val(record_id)
        if not clean_id:
            messagebox.showwarning("تنبيه", "كود العملية غير محدد!")
            return

        type_names = {
            "SALE": "فاتورة بيع",
            "SUPPLIER_INVOICE": "فاتورة مورد",
            "CUSTOMER_PAYMENT": "دفعة عميل (خرج)",
            "SUPPLIER_PAYMENT": "دفعة مورد",
            "CAPITAL_TRANSACTION": "حركة سيولة",
            "DEVICE": "تاريخ تسجيل جهاز"
        }
        ar_type = type_names.get(str(record_type).upper(), str(record_type))

        dwin = tk.Toplevel(self)
        dwin.title(f"تعديل تاريخ {ar_type} #{clean_id}")
        dwin.geometry("520x400")
        dwin.configure(bg=self.COLOR_BG)
        dwin.grab_set()

        top_b = tk.Frame(dwin, bg=self.COLOR_TOPBAR, pady=10, padx=16)
        top_b.pack(fill="x")
        tk.Label(
            top_b, text=fix_bidi(f"✏️ تعديل تاريخ {ar_type} #{clean_id}"),
            font=("Segoe UI", 13, "bold"), bg=self.COLOR_TOPBAR, fg="#38bdf8"
        ).pack(side="right")

        card = tk.Frame(dwin, bg=self.COLOR_CARD, padx=18, pady=16, highlightthickness=1, highlightbackground=self.COLOR_BORDER)
        card.pack(fill="both", expand=True, padx=16, pady=14)

        tk.Label(card, text="التاريخ والوقت الحالي المسجل:", font=("Segoe UI", 10, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_MUTED).pack(anchor="e", pady=(0, 2))
        tk.Label(card, text=str(current_date_str or "-"), font=("Segoe UI", 12, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, padx=10, pady=4).pack(fill="x", pady=(0, 10))

        tk.Label(card, text="التاريخ والوقت الجديد (لا يُسمح بتاريخ مستقبلي):", font=("Segoe UI", 10, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_BLUE).pack(anchor="e", pady=(0, 2))
        
        entry_f = tk.Frame(card, bg=self.COLOR_CARD)
        entry_f.pack(fill="x", pady=(0, 10))
        
        ent_new_date = tk.Entry(entry_f, font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="center")
        init_val = str(current_date_str).split(".")[0] if current_date_str else datetime.now().strftime("%Y-%m-%d %H:%M")
        ent_new_date.insert(0, init_val)
        ent_new_date.pack(side="right", fill="x", expand=True, ipady=3)

        def pick_new_cal():
            def on_sel():
                cur = ent_new_date.get().strip()
                if len(cur) == 10:
                    ent_new_date.delete(0, tk.END)
                    ent_new_date.insert(0, f"{cur} 12:00")
            self.open_date_picker(ent_new_date, on_select_callback=on_sel, allow_future=False)

        tk.Button(
            entry_f, text="📅", command=pick_new_cal,
            bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold"), padx=8, pady=2, relief="flat", cursor="hand2"
        ).pack(side="left", padx=2)

        def set_edit_today():
            ent_new_date.delete(0, tk.END)
            ent_new_date.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M"))

        tk.Button(
            entry_f, text="اليوم", command=set_edit_today,
            bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 8, "bold"), padx=6, pady=2, relief="flat", cursor="hand2"
        ).pack(side="left", padx=2)

        if str(record_type).upper() in ("DEVICE", "DEVICES"):
            tk.Label(
                card, text="ℹ️ تنبيه: تعديل تاريخ شراء الجهاز سيقوم تلقائياً بتحديث تاريخ فاتورة المورد التابع لها.",
                font=("Segoe UI", 9, "bold"), bg="#eff6ff", fg="#1d4ed8", padx=10, pady=5, anchor="e", justify="right"
            ).pack(fill="x", pady=(0, 10))

        tk.Label(card, text="سبب أو ملاحظات التعديل:", font=("Segoe UI", 10, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_MUTED).pack(anchor="e", pady=(0, 2))
        ent_notes = tk.Entry(card, font=("Segoe UI", 10, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="right")
        ent_notes.pack(fill="x", ipady=3, pady=(0, 14))

        def save_date_action():
            nv = ent_new_date.get().strip()
            if not nv:
                messagebox.showwarning("تنبيه", "يرجى إدخال التاريخ الجديد!", parent=dwin)
                return
            nt = ent_notes.get().strip()
            try:
                self.db.update_operation_date(
                    entity_type=record_type,
                    entity_id=clean_id,
                    new_date=nv,
                    user_id=self.current_user['id'] if self.current_user else None,
                    notes=nt
                )
                messagebox.showinfo("تم التعديل", f"تم تحديث تاريخ {ar_type} #{clean_id} بنجاح وتوثيقه في سجل العمليات!", parent=dwin)
                dwin.destroy()
                if on_success_callback:
                    on_success_callback()
            except Exception as ex:
                messagebox.showerror("خطأ", str(ex), parent=dwin)

        bot_b = tk.Frame(dwin, bg=self.COLOR_TOPBAR, pady=8, padx=16)
        bot_b.pack(side="bottom", fill="x")

        tk.Button(
            bot_b, text="💾 حفظ وتحديث التاريخ", command=save_date_action,
            bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"),
            padx=16, pady=4, relief="flat", cursor="hand2"
        ).pack(side="right", padx=5)

        tk.Button(
            bot_b, text="إلغاء", command=dwin.destroy,
            bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 10, "bold"),
            padx=14, pady=4, relief="flat", cursor="hand2"
        ).pack(side="left", padx=5)

    def open_invoice_preview_and_print(self, invoice_data, title_text="معاينة وطباعة الفاتورة"):
        p_win = tk.Toplevel(self)
        p_win.title(title_text)
        p_win.geometry("1020x860")
        p_win.minsize(980, 720)
        p_win.configure(bg=self.COLOR_BG)
        p_win.grab_set()

        btn_bar = tk.Frame(p_win, bg=self.COLOR_BG, pady=10)
        btn_bar.pack(side="bottom", fill="x", padx=15, pady=(4, 10))

        top_hdr = tk.Frame(p_win, bg=self.COLOR_TOPBAR, pady=10, padx=15)
        top_hdr.pack(side="top", fill="x")
        tk.Label(top_hdr, text=fix_bidi(f"🖨️ {title_text}"), font=("Segoe UI", 14, "bold"), bg=self.COLOR_TOPBAR, fg=self.COLOR_BLUE).pack(side="right")

        ctrl_panel = tk.Frame(p_win, bg=self.COLOR_CARD, padx=15, pady=6, highlightthickness=1, highlightbackground=self.COLOR_TOPBAR)
        ctrl_panel.pack(side="top", fill="x", padx=15, pady=4)

        tk.Label(ctrl_panel, text="🎨 نمط ألوان الطباعة:", font=("Segoe UI", 10, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_TEXT).pack(side="right", padx=5)
        style_var = tk.StringVar(value=invoice_data.get("print_style", "color"))

        for st_label, st_val in [("أزرق فاخر", "color"), ("عنابي مميز", "burgundy"), ("أبيض وأسود عالي الوضوح", "grayscale")]:
            tk.Radiobutton(
                ctrl_panel, text=st_label, variable=style_var, value=st_val,
                bg=self.COLOR_CARD, fg=self.COLOR_TEXT, selectcolor=self.COLOR_ENTRY_BG,
                font=("Segoe UI", 9, "bold"), command=lambda: render_preview()
            ).pack(side="right", padx=6)

        tk.Label(ctrl_panel, text="📄 مقاس الطباعة:", font=("Segoe UI", 10, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_TEXT).pack(side="right", padx=(14, 5))
        size_var = tk.StringVar(value="standard_a4_a5")

        tk.Label(
            ctrl_panel, text="مقاس قياسي موحد A4 / A5 مستغل لكامل الصفحة (Ultra Clear) 📄✨",
            bg=self.COLOR_ENTRY_BG, fg=self.COLOR_ACCENT, font=("Segoe UI", 9, "bold"), padx=10, pady=3
        ).pack(side="right", padx=5)

        nav_panel = tk.Frame(p_win, bg=self.COLOR_TOPBAR, padx=15, pady=6)
        nav_panel.pack(side="top", fill="x", padx=15, pady=(0, 4))

        lbl_pages_counter = tk.Label(nav_panel, text="صفحة 1 من 1", font=("Segoe UI", 11, "bold"), bg=self.COLOR_TOPBAR, fg="#ffffff")
        lbl_pages_counter.pack(side="right", padx=10)

        terms_frame = tk.Frame(p_win, bg=self.COLOR_CARD, padx=15, pady=4)
        terms_frame.pack(side="top", fill="x", padx=15, pady=(0, 4))
        tk.Label(terms_frame, text="📝 الشروط والضمان والملاحظات المطبوعة على الفاتورة:", font=("Segoe UI", 9, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_MUTED).pack(anchor="e")
        terms_entry = tk.Text(terms_frame, height=2, font=("Segoe UI", 10, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT)
        terms_entry.pack(fill="x", pady=2)
        default_terms = invoice_data.get(
            "custom_terms",
            "1. استلام ومطابقة البضاعة حسب المواصفات المتفق عليها.\n"
            "2. أرقام السيريال IMEI معتمدة ومسجلة بدفاتر النظام.\n"
            "3. يرجى الاحتفاظ بالفاتورة لمراجعة المحل عند الحاجة."
        )
        terms_entry.insert("1.0", default_terms)

        preview_container = tk.Frame(p_win, bg=self.COLOR_CARD, padx=10, pady=8)
        preview_container.pack(fill="both", expand=True, padx=15, pady=4)

        prev_canvas = tk.Canvas(preview_container, bg=self.COLOR_CARD, highlightthickness=0)
        prev_vsb = ttk.Scrollbar(preview_container, orient="vertical", command=prev_canvas.yview)
        prev_hsb = ttk.Scrollbar(preview_container, orient="horizontal", command=prev_canvas.xview)
        prev_canvas.configure(yscrollcommand=prev_vsb.set, xscrollcommand=prev_hsb.set)

        prev_vsb.pack(side="left", fill="y")
        prev_hsb.pack(side="bottom", fill="x")
        prev_canvas.pack(side="right", fill="both", expand=True)

        inner_prev_frame = tk.Frame(prev_canvas, bg=self.COLOR_CARD)
        prev_win_id = prev_canvas.create_window((0, 0), window=inner_prev_frame, anchor="nw")

        def _on_prev_configure(event=None):
            prev_canvas.configure(scrollregion=prev_canvas.bbox("all"))

        inner_prev_frame.bind("<Configure>", _on_prev_configure)

        lbl_preview_img = tk.Label(inner_prev_frame, bg=self.COLOR_CARD, text="جاري تجهيز المعاينة...")
        lbl_preview_img.pack(padx=10, pady=10)

        state_holder = {
            "all_pages": [],
            "current_idx": 0,
            "img_path": None,
            "tk_img": None,
            "all_temp_paths": [],
            "zoom_mode": False
        }

        def cleanup_temp_files():
            for p in list(state_holder.get("all_temp_paths", [])):
                try:
                    if p and os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass
            state_holder["all_temp_paths"] = []

        def show_current_page():
            pages = state_holder["all_pages"]
            if not pages:
                return
            idx = state_holder["current_idx"]
            cur_path = pages[idx]
            state_holder["img_path"] = cur_path
            lbl_pages_counter.config(text=f"صفحة {idx + 1} من {len(pages)}  |  مقاس A4/A5 القياسي (1240 × 1754 px)")
            try:
                pil_img = Image.open(cur_path)
                preview_size = (800, 1130) if state_holder["zoom_mode"] else (580, 820)
                pil_img.thumbnail(preview_size, Image.Resampling.LANCZOS)
                state_holder["tk_img"] = ImageTk.PhotoImage(pil_img)
                lbl_preview_img.config(image=state_holder["tk_img"], text="")
                prev_canvas.yview_moveto(0.0)
                prev_canvas.xview_moveto(0.0)
            except Exception as ex:
                lbl_preview_img.config(text=f"تعذر عرض الصفحة: {ex}")

        def prev_page():
            if state_holder["current_idx"] > 0:
                state_holder["current_idx"] -= 1
                show_current_page()

        def next_page():
            if state_holder["current_idx"] < len(state_holder["all_pages"]) - 1:
                state_holder["current_idx"] += 1
                show_current_page()

        def toggle_zoom():
            state_holder["zoom_mode"] = not state_holder["zoom_mode"]
            btn_zoom.config(text="🔍 تصغير العرض" if state_holder["zoom_mode"] else "🔍 تكبير العرض")
            show_current_page()

        btn_prev = tk.Button(nav_panel, text="الصفحة السابقة ➡️", font=("Segoe UI", 9, "bold"), bg=self.COLOR_BLUE, fg="white", relief="flat", cursor="hand2", command=prev_page)
        btn_prev.pack(side="right", padx=5)

        btn_next = tk.Button(nav_panel, text="⬅️ الصفحة التالية", font=("Segoe UI", 9, "bold"), bg=self.COLOR_BLUE, fg="white", relief="flat", cursor="hand2", command=next_page)
        btn_next.pack(side="right", padx=5)

        btn_zoom = tk.Button(nav_panel, text="🔍 تكبير العرض", font=("Segoe UI", 9, "bold"), bg=self.COLOR_INDIGO, fg="white", relief="flat", cursor="hand2", command=toggle_zoom)
        btn_zoom.pack(side="left", padx=5)

        def render_preview():
            invoice_data["print_style"] = style_var.get()
            invoice_data["paper_size"] = size_var.get()
            invoice_data["custom_terms"] = terms_entry.get("1.0", tk.END).strip()
            try:
                pages = generate_invoice_pages(invoice_data)
                state_holder["all_pages"] = pages
                for p in pages:
                    if p not in state_holder["all_temp_paths"]:
                        state_holder["all_temp_paths"].append(p)
                state_holder["current_idx"] = min(state_holder["current_idx"], len(pages) - 1)
                show_current_page()
            except Exception as ex:
                lbl_preview_img.config(text=f"تعذر توليد المعاينة: {ex}")

        def do_direct_print():
            render_preview()
            cur_img = state_holder.get("img_path")
            if cur_img:
                try:
                    trigger_system_print_or_open(cur_img, mode="print")
                    messagebox.showinfo("طباعة", "تم إرسال الصفحة المحددة إلى أمر الطباعة بنجاح!", parent=p_win)
                except Exception as ex:
                    messagebox.showerror("خطأ", f"تعذر إرسال الصفحة للطابعة: {ex}", parent=p_win)

        def do_print_all():
            render_preview()
            pages = state_holder.get("all_pages", [])
            if not pages:
                return
            count = 0
            for p in pages:
                try:
                    trigger_system_print_or_open(p, mode="print")
                    count += 1
                except Exception:
                    pass
            messagebox.showinfo("طباعة الكل", f"تم إرسال جميع الصفحات ({count} صفحة) إلى أمر الطباعة بنجاح!", parent=p_win)

        def do_open_image():
            render_preview()
            if state_holder["img_path"]:
                try:
                    trigger_system_print_or_open(state_holder["img_path"], mode="open")
                except Exception as ex:
                    messagebox.showerror("خطأ", f"الملف محفوظ في:\n{state_holder['img_path']}\n({ex})", parent=p_win)

        def do_save_copy():
            render_preview()
            if not state_holder["img_path"]:
                return
            dest = filedialog.asksaveasfilename(
                parent=p_win,
                title="حفظ صورة الفاتورة",
                defaultextension=".png",
                initialfile=os.path.basename(state_holder["img_path"]),
                filetypes=[("PNG Image", "*.png")]
            )
            if dest:
                shutil.copy2(state_holder["img_path"], dest)
                messagebox.showinfo("تم الحفظ", f"تم حفظ الفاتورة بنجاح في:\n{dest}", parent=p_win)

        def on_close_preview():
            cleanup_temp_files()
            p_win.destroy()

        p_win.protocol("WM_DELETE_WINDOW", on_close_preview)

        tk.Button(btn_bar, text="🖨️ طباعة جميع الصفحات", command=do_print_all, bg="#059669", fg="white", font=("Segoe UI", 11, "bold"), padx=16, pady=7, cursor="hand2").pack(side="right", padx=5)
        tk.Button(btn_bar, text="🖨️ طباعة هذه الصفحة", command=do_direct_print, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"), padx=14, pady=7, cursor="hand2").pack(side="right", padx=5)
        tk.Button(btn_bar, text="🖼️ فتح الصورة الأصلية (HD)", command=do_open_image, bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold"), padx=12, pady=7, cursor="hand2").pack(side="right", padx=5)
        tk.Button(btn_bar, text="💾 حفظ باسم", command=do_save_copy, bg=self.COLOR_TEAL, fg="white", font=("Segoe UI", 10, "bold"), padx=12, pady=7, cursor="hand2").pack(side="right", padx=5)
        tk.Button(btn_bar, text="🔄 تحديث المعاينة", command=render_preview, bg=self.COLOR_TOPBAR, fg="#ffffff", font=("Segoe UI", 10, "bold"), padx=12, pady=7, cursor="hand2").pack(side="left", padx=5)
        tk.Button(btn_bar, text="❌ إغلاق المعاينة", command=on_close_preview, bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 10, "bold"), padx=14, pady=7, cursor="hand2").pack(side="left", padx=5)

        render_preview()

    def open_date_picker(self, target_entry, on_select_callback=None, allow_future=True):
        cal_win = tk.Toplevel(self)
        cal_win.title("📅 اختيار التاريخ")
        cal_win.geometry("330x350")
        cal_win.configure(bg=self.COLOR_CARD)
        cal_win.resizable(False, False)
        cal_win.grab_set()

        now = datetime.now()
        cur_val = target_entry.get().strip()
        try:
            dt_init = datetime.strptime(cur_val.split()[0], "%Y-%m-%d")
            sel_year, sel_month = dt_init.year, dt_init.month
        except Exception:
            sel_year, sel_month = now.year, now.month

        if not allow_future and sel_year > now.year:
            sel_year = now.year
        if not allow_future and sel_year == now.year and sel_month > now.month:
            sel_month = now.month

        top_ctrl = tk.Frame(cal_win, bg=self.COLOR_TOPBAR, pady=8, padx=8)
        top_ctrl.pack(fill="x")

        max_year = now.year if not allow_future else now.year + 3
        years = [str(y) for y in range(2022, max_year + 1)]
        months_ar = [
            "01 - يناير", "02 - فبراير", "03 - مارس", "04 - أبريل",
            "05 - مايو", "06 - يونيو", "07 - يوليو", "08 - أغسطس",
            "09 - سبتمبر", "10 - أكتوبر", "11 - نوفمبر", "12 - ديسمبر"
        ]

        cb_year = ttk.Combobox(top_ctrl, values=years, width=7, state="readonly", font=("Segoe UI", 10, "bold"))
        cb_year.set(str(sel_year))
        cb_year.pack(side="left", padx=4)

        cb_month = ttk.Combobox(top_ctrl, values=months_ar, width=13, state="readonly", font=("Segoe UI", 10, "bold"))
        cb_month.current(min(sel_month - 1, 11))
        cb_month.pack(side="right", padx=4)

        days_frame = tk.Frame(cal_win, bg=self.COLOR_CARD, padx=10, pady=8)
        days_frame.pack(fill="both", expand=True)

        def pick_date(y, m, d):
            chosen = datetime(int(y), int(m), int(d))
            if not allow_future and chosen.date() > now.date():
                messagebox.showwarning("تنبيه", "لا يمكن اختيار تاريخ مستقبلي للعمليات! يرجى اختيار تاريخ حالي أو سابق.", parent=cal_win)
                return
            date_str = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
            target_entry.delete(0, tk.END)
            target_entry.insert(0, date_str)
            cal_win.destroy()
            if on_select_callback:
                on_select_callback()

        def render_calendar(e=None):
            for w in days_frame.winfo_children():
                w.destroy()
            y = int(cb_year.get())
            m = cb_month.current() + 1

            if not allow_future and y == now.year and m > now.month:
                cb_month.current(now.month - 1)
                m = now.month

            week_headers = ["سبت", "أحد", "إثنين", "ثلاثاء", "أربعاء", "خميس", "جمعة"]
            for col_i, h_txt in enumerate(week_headers):
                tk.Label(days_frame, text=h_txt, bg=self.COLOR_TOPBAR, fg=self.COLOR_BLUE, font=("Segoe UI", 8, "bold"), width=5, pady=3).grid(row=0, column=6 - col_i, padx=1, pady=2)

            cal = calendar.Calendar(firstweekday=5)
            month_days = cal.monthdayscalendar(y, m)
            for r_idx, week in enumerate(month_days, start=1):
                for c_idx, day_num in enumerate(week):
                    if day_num == 0:
                        tk.Label(days_frame, text="", bg=self.COLOR_CARD, width=5).grid(row=r_idx, column=6 - c_idx, padx=1, pady=1)
                    else:
                        is_today = (y == now.year and m == now.month and day_num == now.day)
                        is_future = (y > now.year) or (y == now.year and m > now.month) or (y == now.year and m == now.month and day_num > now.day)
                        if not allow_future and is_future:
                            btn = tk.Button(
                                days_frame, text=str(day_num), bg=self.COLOR_BG, fg=self.COLOR_MUTED,
                                font=("Segoe UI", 9, "normal"), width=4, relief="flat", state="disabled"
                            )
                        else:
                            btn_bg = self.COLOR_ACCENT if is_today else self.COLOR_ENTRY_BG
                            btn = tk.Button(
                                days_frame, text=str(day_num), bg=btn_bg, fg=self.COLOR_TEXT,
                                font=("Segoe UI", 9, "bold"), width=4, relief="flat", cursor="hand2",
                                command=lambda dn=day_num: pick_date(y, m, dn)
                            )
                        btn.grid(row=r_idx, column=6 - c_idx, padx=1, pady=1)

        cb_year.bind("<<ComboboxSelected>>", render_calendar)
        cb_month.bind("<<ComboboxSelected>>", render_calendar)
        render_calendar()

        bot_bar = tk.Frame(cal_win, bg=self.COLOR_CARD, pady=6)
        bot_bar.pack(fill="x")
        tk.Button(bot_bar, text="📍 اليوم", command=lambda: pick_date(now.year, now.month, now.day), bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, cursor="hand2").pack(side="right", padx=15)
        tk.Button(bot_bar, text="🗑️ مسح", command=lambda: (target_entry.delete(0, tk.END), cal_win.destroy(), on_select_callback() if on_select_callback else None), bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, cursor="hand2").pack(side="left", padx=15)

    def attach_autocomplete(self, entry_widget, get_options_callable, next_focus_widget=None, on_chosen_callback=None):
        popup_state = {"win": None, "lb": None, "items": []}

        def close_popup():
            if popup_state["win"] is not None:
                try:
                    popup_state["win"].destroy()
                except Exception:
                    pass
                popup_state["win"] = None
                popup_state["lb"] = None
                popup_state["items"] = []

        def apply_selection(chosen_text, move_next=True):
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, chosen_text)
            close_popup()
            if on_chosen_callback:
                try:
                    on_chosen_callback(chosen_text)
                except Exception:
                    pass
            if move_next and next_focus_widget:
                next_focus_widget.focus_set()

        def find_best_match(query_text):
            all_opts = get_options_callable() or []
            ft = (query_text or "").strip().lower()
            if not ft:
                return all_opts[0] if all_opts else None
            for o in all_opts:
                if o.lower() == ft:
                    return o
            for o in all_opts:
                if o.lower().startswith(ft):
                    return o
            for o in all_opts:
                words = o.lower().split()
                if any(w.startswith(ft) for w in words):
                    return o
            for o in all_opts:
                if ft in o.lower():
                    return o
            return None

        def get_filtered_matches(filter_text=""):
            all_opts = get_options_callable() or []
            ft = (filter_text or "").strip().lower()
            if not ft:
                return list(all_opts)
            starts = [o for o in all_opts if o.lower().startswith(ft)]
            word_starts = [o for o in all_opts if any(w.startswith(ft) for w in o.lower().split()) and o not in starts]
            contains = [o for o in all_opts if ft in o.lower() and o not in starts and o not in word_starts]
            return starts + word_starts + contains

        def show_or_update_popup(filter_text=""):
            matched = get_filtered_matches(filter_text)
            if not matched:
                close_popup()
                return

            popup_state["items"] = matched[:12]

            if popup_state["win"] is None or not popup_state["win"].winfo_exists():
                pop = tk.Toplevel(entry_widget)
                pop.wm_overrideredirect(True)
                pop.configure(bg=self.COLOR_BLUE)
                lb = tk.Listbox(
                    pop, font=("Segoe UI", 10, "bold"),
                    bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT,
                    selectbackground=self.COLOR_BLUE, selectforeground="#ffffff",
                    activestyle="none", exportselection=False, relief="flat", highlightthickness=1,
                    highlightbackground=self.COLOR_BLUE
                )
                lb.pack(fill="both", expand=True)

                def on_lb_click(ev):
                    idx = lb.nearest(ev.y)
                    if 0 <= idx < len(popup_state["items"]):
                        apply_selection(popup_state["items"][idx], move_next=True)

                def on_lb_motion(ev):
                    idx = lb.nearest(ev.y)
                    if 0 <= idx < len(popup_state["items"]):
                        lb.selection_clear(0, tk.END)
                        lb.selection_set(idx)
                        lb.activate(idx)

                lb.bind("<ButtonRelease-1>", on_lb_click)
                lb.bind("<Motion>", on_lb_motion)
                popup_state["win"] = pop
                popup_state["lb"] = lb

            lb = popup_state["lb"]
            lb.delete(0, tk.END)
            for item in popup_state["items"]:
                lb.insert(tk.END, f"  {item}  ")

            lb.selection_set(0)
            lb.activate(0)

            entry_widget.update_idletasks()
            x = entry_widget.winfo_rootx()
            y = entry_widget.winfo_rooty() + entry_widget.winfo_height() + 2
            w = max(entry_widget.winfo_width(), 200)
            h = min(len(popup_state["items"]), 7) * 25 + 6
            popup_state["win"].geometry(f"{w}x{h}+{x}+{y}")
            popup_state["win"].lift()

        def on_key_release(event):
            if event.keysym in ("Up", "Down", "Return", "Tab", "Escape", "Shift_L", "Shift_R", "Control_L", "Control_R"):
                return
            show_or_update_popup(entry_widget.get())

        def on_down(event):
            if popup_state["lb"] is None:
                show_or_update_popup(entry_widget.get())
                return "break"
            lb = popup_state["lb"]
            sel = lb.curselection()
            idx = sel[0] if sel else -1
            next_idx = min(idx + 1, lb.size() - 1)
            lb.selection_clear(0, tk.END)
            lb.selection_set(next_idx)
            lb.activate(next_idx)
            lb.see(next_idx)
            return "break"

        def on_up(event):
            if popup_state["lb"] is None:
                return
            lb = popup_state["lb"]
            sel = lb.curselection()
            idx = sel[0] if sel else 0
            prev_idx = max(idx - 1, 0)
            lb.selection_clear(0, tk.END)
            lb.selection_set(prev_idx)
            lb.activate(prev_idx)
            lb.see(prev_idx)
            return "break"

        def on_tab_key(event):
            cur_txt = entry_widget.get().strip()
            if popup_state["lb"] is not None and popup_state["items"]:
                sel = popup_state["lb"].curselection()
                idx = sel[0] if sel else 0
                if 0 <= idx < len(popup_state["items"]):
                    apply_selection(popup_state["items"][idx], move_next=True)
                    return "break"
            elif cur_txt:
                best = find_best_match(cur_txt)
                if best:
                    apply_selection(best, move_next=True)
                    return "break"
            close_popup()
            if next_focus_widget:
                next_focus_widget.focus_set()
                return "break"

        def on_return_key(event):
            if popup_state["lb"] is not None and popup_state["items"]:
                sel = popup_state["lb"].curselection()
                idx = sel[0] if sel else 0
                if 0 <= idx < len(popup_state["items"]):
                    apply_selection(popup_state["items"][idx], move_next=True)
                    return "break"
            close_popup()
            if next_focus_widget:
                next_focus_widget.focus_set()
                return "break"

        def on_right_key(event):
            cur_txt = entry_widget.get().strip()
            if cur_txt and entry_widget.index(tk.INSERT) >= len(cur_txt):
                best = popup_state["items"][0] if (popup_state["items"]) else find_best_match(cur_txt)
                if best and best.lower() != cur_txt.lower():
                    apply_selection(best, move_next=False)
                    return "break"

        entry_widget.bind("<KeyRelease>", on_key_release, add="+")
        entry_widget.bind("<Down>", on_down)
        entry_widget.bind("<Up>", on_up)
        entry_widget.bind("<Return>", on_return_key)
        entry_widget.bind("<Tab>", on_tab_key)
        entry_widget.bind("<Right>", on_right_key)
        entry_widget.bind("<Escape>", lambda e: close_popup())
        entry_widget.bind("<Button-1>", lambda e: self.after(60, lambda: show_or_update_popup(entry_widget.get())), add="+")
        entry_widget.bind("<FocusOut>", lambda e: self.after(180, close_popup), add="+")

    def show_login_dialog(self):
        login_win = tk.Toplevel(self)
        login_win.title("تسجيل الدخول - مركز هشام كيوان")
        login_win.state("zoomed")
        login_win.configure(bg=self.COLOR_BG)
        login_win.protocol("WM_DELETE_WINDOW", self.destroy)
        login_win.grab_set()

        login_top = tk.Frame(
            login_win, bg=self.COLOR_TOPBAR, pady=12, padx=25,
            highlightthickness=1 if not self.is_dark_mode else 0,
            highlightbackground=self.COLOR_BORDER
        )
        login_top.pack(fill="x", side="top")

        tk.Label(
            login_top, text=fix_bidi("📱 مركز هشام كيوان لإدارة وتجارة الهواتف"),
            bg=self.COLOR_TOPBAR, fg=self.COLOR_BLUE, font=("Segoe UI", 13, "bold")
        ).pack(side="right")

        def switch_login_theme(colorful_toggle=False):
            if colorful_toggle:
                self.is_colorful_mode = not self.is_colorful_mode
            else:
                self.is_dark_mode = not self.is_dark_mode
            self.apply_theme_colors()
            self.setup_styles()
            login_win.destroy()
            self.show_login_dialog()

        tk.Button(
            login_top, text="🌓 المظهر", command=lambda: switch_login_theme(False),
            bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=3, cursor="hand2"
        ).pack(side="left", padx=5)
        tk.Button(
            login_top, text=f"🎨 الألوان: {'مفعل' if self.is_colorful_mode else 'عادي'}",
            command=lambda: switch_login_theme(True),
            bg=self.COLOR_TEAL, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=3, cursor="hand2"
        ).pack(side="left", padx=5)

        footer_bar = tk.Frame(
            login_win, bg=self.COLOR_TOPBAR, pady=8, padx=25,
            highlightthickness=1 if not self.is_dark_mode else 0,
            highlightbackground=self.COLOR_BORDER
        )
        footer_bar.pack(side="bottom", fill="x")
        tk.Label(footer_bar, text=fix_bidi("© 2026 مركز هشام كيوان لإدارة الهواتف"), bg=self.COLOR_TOPBAR, fg=self.COLOR_MUTED, font=("Segoe UI", 9, "bold")).pack(side="right")
        tk.Label(footer_bar, text=fix_bidi("🟢 متصل بقاعدة البيانات"), bg=self.COLOR_TOPBAR, fg=self.COLOR_ACCENT, font=("Segoe UI", 9, "bold")).pack(side="left")

        border_col = self.COLOR_INDIGO if self.is_colorful_mode else self.COLOR_BLUE
        card = tk.Frame(login_win, bg=self.COLOR_CARD, padx=45, pady=38, highlightthickness=2, highlightbackground=border_col)
        card.place(relx=0.5, rely=0.5, anchor="center")

        if self.logo_login:
            lbl_logo = tk.Label(card, image=self.logo_login, bg=self.COLOR_CARD)
            lbl_logo.pack(pady=(0, 8))
        else:
            tk.Label(card, text="📱", font=("Segoe UI", 42), bg=self.COLOR_CARD, fg=self.COLOR_BLUE).pack(pady=(0, 4))

        tk.Label(card, text="مركز هشام كيوان", font=("Segoe UI", 20, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_TEXT).pack()
        tk.Label(card, text="تسجيل الدخول للنظام", font=("Segoe UI", 11, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_BLUE).pack(pady=(2, 18))

        user_lbl_frame = tk.Frame(card, bg=self.COLOR_CARD)
        user_lbl_frame.pack(fill="x")
        tk.Label(user_lbl_frame, text="👤 اسم المستخدم:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right")

        users_list = self.db.get_all_users()
        active_usernames = [u['username'] for u in users_list if u.get('is_active', True)]
        user_cb = ttk.Combobox(card, values=active_usernames, font=("Segoe UI", 12, "bold"), width=28, justify="right")
        if active_usernames:
            user_cb.current(0)
        user_cb.pack(pady=(4, 14), ipady=3)

        pass_lbl_frame = tk.Frame(card, bg=self.COLOR_CARD)
        pass_lbl_frame.pack(fill="x")
        tk.Label(pass_lbl_frame, text="🔑 كلمة المرور:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right")

        pass_row = tk.Frame(card, bg=self.COLOR_ENTRY_BG, highlightthickness=1, highlightbackground=self.COLOR_BLUE)
        pass_row.pack(fill="x", pady=(4, 18))

        pass_entry = tk.Entry(pass_row, show="●", justify="center", font=("Segoe UI", 12, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, relief="flat", width=24)
        pass_entry.pack(side="right", fill="x", expand=True, ipady=6, padx=6)
        pass_entry.focus()

        show_pw = {"val": False}
        def toggle_pw_vis():
            show_pw["val"] = not show_pw["val"]
            pass_entry.config(show="" if show_pw["val"] else "●")
            btn_eye.config(text="🙈" if show_pw["val"] else "👁️")

        btn_eye = tk.Button(pass_row, text="👁️", command=toggle_pw_vis, bg=self.COLOR_ENTRY_BG, fg=self.COLOR_MUTED, relief="flat", font=("Segoe UI", 10), cursor="hand2", padx=6)
        btn_eye.pack(side="left")

        user_cb.bind("<Return>", lambda e: pass_entry.focus())

        def try_login():
            username = user_cb.get().strip()
            password = pass_entry.get().strip()
            if not username or not password:
                messagebox.showwarning("تنبيه", "برجاء إدخال اسم المستخدم وكلمة المرور!", parent=login_win)
                return

            user = self.db.authenticate_user(username, password)
            if user:
                self.current_user = user
                login_win.destroy()
                self.deiconify()
                self.state("zoomed")
                self.build_main_ui()
                self.navigate_to_first_permitted_view()
            else:
                messagebox.showerror("خطأ في الدخول", "اسم المستخدم أو كلمة المرور غير صحيحة أو الحساب معطل!", parent=login_win)
                pass_entry.select_range(0, tk.END)
                pass_entry.focus()

        pass_entry.bind("<Return>", lambda e: try_login())
        btn_login = tk.Button(
            card, text="🚀 دخول (Enter)", command=try_login,
            bg=self.COLOR_ACCENT, fg="#ffffff", font=("Segoe UI", 12, "bold"),
            width=26, pady=8, relief="flat", cursor="hand2"
        )
        btn_login.pack(pady=(5, 4))

    def navigate_to_first_permitted_view(self):
        if self.has_permission('can_view_inventory'):
            self.view_inventory()
        elif self.has_permission('can_view_sales_screen'):
            self.view_search_sale()
        elif self.has_permission('can_buy_devices'):
            self.view_buy()
        elif self.has_permission('can_view_customer_debts'):
            self.view_customer_debts()
        elif self.has_permission('can_view_supplier_debts'):
            self.view_supplier_debts()
        elif self.has_permission('can_view_reports'):
            self.view_reports()
        elif self.has_permission('can_manage_users'):
            self.view_user_management()
        else:
            self.clear_content()
            tk.Label(self.content_frame, text="⚠️ لا توجد شاشات مفعلة لهذا الحساب. يرجى مراجعة مدير النظام.", font=("Segoe UI", 14, "bold"), bg=self.COLOR_BG, fg=self.COLOR_DANGER).pack(pady=60)

    def logout(self):
        self.current_user = None
        self.current_view_func = None
        self.current_view_name = None
        self.withdraw()
        for widget in self.winfo_children():
            widget.destroy()
        self.show_login_dialog()

    def build_main_ui(self, keep_view=False):
        for widget in self.winfo_children():
            widget.destroy()

        top_bar = tk.Frame(
            self, bg=self.COLOR_TOPBAR, height=58,
            highlightthickness=1 if not self.is_dark_mode else 0,
            highlightbackground=self.COLOR_BORDER
        )
        top_bar.pack(fill="x", side="top")

        right_top = tk.Frame(top_bar, bg=self.COLOR_TOPBAR)
        right_top.pack(side="right", padx=15, pady=8)

        if self.logo_top:
            lbl_logo_top = tk.Label(right_top, image=self.logo_top, bg=self.COLOR_TOPBAR)
            lbl_logo_top.pack(side="right", padx=8)

        top_title_fg = "#0284c7" if not self.is_dark_mode else "#38bdf8"
        tk.Label(right_top, text="📱 مركز هشام كيوان لإدارة الهواتف", font=("Segoe UI", 14, "bold"), bg=self.COLOR_TOPBAR, fg=top_title_fg).pack(side="right")

        left_top = tk.Frame(top_bar, bg=self.COLOR_TOPBAR)
        left_top.pack(side="left", padx=15, pady=8)

        user_info = fix_bidi(f"👤 {self.current_user['full_name']}") if self.current_user else ""
        top_user_fg = "#0f172a" if not self.is_dark_mode else "#f8fafc"
        tk.Label(left_top, text=user_info, font=("Segoe UI", 10, "bold"), bg=self.COLOR_TOPBAR, fg=top_user_fg).pack(side="left", padx=12)

        tk.Button(left_top, text="🚪 خروج", command=self.logout, bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2", padx=12, pady=4, activebackground="#b91c1c", activeforeground="#ffffff").pack(side="left", padx=4)
        tk.Button(left_top, text=f"🌓 {'نهاري' if self.is_dark_mode else 'ليلي'}", command=self.toggle_theme, bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2", padx=12, pady=4, activebackground="#0284c7", activeforeground="#ffffff").pack(side="left", padx=4)
        tk.Button(
            left_top,
            text=f"🎨 الألوان: {'مفعل' if self.is_colorful_mode else 'عادي'}",
            command=self.toggle_colorful_mode,
            bg=self.COLOR_BLUE if self.is_colorful_mode else ("#64748b" if not self.is_dark_mode else "#334155"),
            fg="white",
            font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2", padx=12, pady=4,
            activebackground=self.COLOR_BLUE, activeforeground="#ffffff"
        ).pack(side="left", padx=4)

        tk.Button(
            left_top,
            text="⚡ البحث السريع (QR / كود)",
            command=self.open_quick_qr_search_modal,
            bg=self.COLOR_INDIGO,
            fg="white",
            font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2", padx=12, pady=4,
            activebackground="#1d4ed8", activeforeground="#ffffff"
        ).pack(side="left", padx=4)

        nav_frame = tk.Frame(
            self, bg=self.COLOR_TOPBAR, width=215, padx=8, pady=10,
            highlightthickness=1 if not self.is_dark_mode else 0,
            highlightbackground=self.COLOR_BORDER
        )
        nav_frame.pack(fill="y", side="right")
        nav_frame.pack_propagate(False)

        nav_lbl_fg = "#64748b" if not self.is_dark_mode else "#94a3b8"
        tk.Label(nav_frame, text="الأقسام الرئيسية", font=("Segoe UI", 10, "bold"), bg=self.COLOR_TOPBAR, fg=nav_lbl_fg, pady=6).pack(fill="x")

        self.content_frame = tk.Frame(self, bg=self.COLOR_BG)
        self.content_frame.pack(fill="both", expand=True, side="left")

        buttons = [
            ("inventory", "📦 المخزون", self.view_inventory, self.has_permission('can_view_inventory')),
            ("sale", "🛒 المبيعات", self.view_search_sale, self.has_permission('can_view_sales_screen')),
            ("buy", "📥 المشتريات", self.view_buy, self.has_permission('can_buy_devices')),
            ("cust_debts", "💳 ديون العملاء", self.view_customer_debts, self.has_permission('can_view_customer_debts')),
            ("supp_debts", "🏭 حسابات الموردين", self.view_supplier_debts, self.has_permission('can_view_supplier_debts')),
            ("reports", "📊 التقارير المالية", self.view_reports, self.has_permission('can_view_reports')),
            ("audit", "📜 سجل العمليات", self.view_audit_logs, self.has_permission('can_view_audit_logs')),
            ("users", "👥 المستخدمين", self.view_user_management, self.has_permission('can_manage_users')),
        ]

        for key_id, text, cmd, perm in buttons:
            if perm:
                if self.is_colorful_mode and key_id in self.NAV_COLORS:
                    btn_bg, btn_hover = self.NAV_COLORS[key_id]
                    btn_fg = "#ffffff"
                    active_fg = "#ffffff"
                else:
                    if not self.is_dark_mode:
                        btn_bg = "#ffffff"
                        btn_hover = "#e0f2fe"
                        btn_fg = "#0f172a"
                        active_fg = "#0369a1"
                    else:
                        btn_bg = self.COLOR_CARD
                        btn_hover = self.COLOR_BLUE
                        btn_fg = self.COLOR_TEXT
                        active_fg = "#ffffff"

                is_active_view = (self.current_view_func == cmd)
                active_bg = btn_hover if (self.is_colorful_mode or self.is_dark_mode) else "#e0f2fe"
                active_text = "#ffffff" if (self.is_colorful_mode or self.is_dark_mode) else "#0369a1"

                btn = tk.Button(
                    nav_frame, text=text, command=cmd,
                    bg=active_bg if is_active_view else btn_bg,
                    fg=active_text if is_active_view else btn_fg,
                    activebackground=btn_hover, activeforeground=active_fg,
                    font=("Segoe UI", 11, "bold"), anchor="e", padx=16,
                    relief="flat", height=2, cursor="hand2",
                    highlightthickness=2 if is_active_view else (1 if not self.is_dark_mode else 0),
                    highlightbackground="#0284c7" if is_active_view else self.COLOR_BORDER
                )
                btn.pack(fill="x", pady=4)

    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def bind_treeview_double_click(self, tree, target_column_name="ID"):
        def on_double_click(event):
            row_id = tree.identify_row(event.y)
            if not row_id:
                selected = tree.selection()
                if not selected:
                    return
                row_id = selected[0]

            iid_clean = clean_id_val(row_id)
            item_vals = tree.item(row_id).get('values', [])
            cols = list(tree['columns'])

            idx = -1
            for search_col in [target_column_name, "ID الجهاز", "كود الجهاز", "ID", "id"]:
                if search_col in cols:
                    idx = cols.index(search_col)
                    break

            dev_id_clean = None
            if 0 <= idx < len(item_vals):
                dev_id_clean = clean_id_val(item_vals[idx])
            if dev_id_clean is None and iid_clean is not None:
                dev_id_clean = iid_clean

            if dev_id_clean is not None:
                self.show_device_details_modal(dev_id_clean)

        tree.bind("<Double-1>", on_double_click)

    def open_quick_qr_search_modal(self, initial_query=""):
        qwin = tk.Toplevel(self)
        qwin.title("⚡ البحث السريع الذكي وقارئ الباركود / الـ QR")
        qwin.geometry("820x620")
        qwin.configure(bg=self.COLOR_BG)
        qwin.grab_set()

        top_hdr = tk.Frame(qwin, bg=self.COLOR_TOPBAR, pady=10, padx=16)
        top_hdr.pack(fill="x")
        tk.Label(
            top_hdr, text="⚡ قارئ الباركود والـ QR والبحث السريع الموحد",
            font=("Segoe UI", 13, "bold"), bg=self.COLOR_TOPBAR, fg="#38bdf8"
        ).pack(side="right")
        tk.Label(
            top_hdr, text="جاهز للمسح بالسكانر 🟢",
            font=("Segoe UI", 10, "bold"), bg=self.COLOR_ACCENT, fg="white", padx=10, pady=3
        ).pack(side="left")

        bot_bar = tk.Frame(qwin, bg=self.COLOR_TOPBAR, pady=8, padx=16)
        bot_bar.pack(side="bottom", fill="x")
        tk.Button(
            bot_bar, text="إغلاق (Esc)", command=qwin.destroy,
            bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 10, "bold"),
            padx=16, pady=4, relief="flat", cursor="hand2"
        ).pack(side="left")

        qwin.bind("<Escape>", lambda e: qwin.destroy())

        body = tk.Frame(qwin, bg=self.COLOR_BG, padx=16, pady=12)
        body.pack(fill="both", expand=True)

        input_card = tk.LabelFrame(
            body, text="📷 مسح الباركود / QR أو كتابة الكود",
            bg=self.COLOR_CARD, fg=self.COLOR_BLUE, font=("Segoe UI", 11, "bold"), padx=14, pady=10
        )
        input_card.pack(fill="x", pady=(0, 10))

        hints_lbl = tk.Label(
            input_card,
            text="يدعم: فواتير البيع (INV-SALE) | ديون العملاء (INV-DEBT) | فواتير الموردين (INV-BUY) | السيريال IMEI | كود الجهاز #ID",
            font=("Segoe UI", 9, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_MUTED
        )
        hints_lbl.pack(anchor="e", pady=(0, 6))

        in_row = tk.Frame(input_card, bg=self.COLOR_CARD)
        in_row.pack(fill="x")

        search_btn = tk.Button(
            in_row, text="🔍 فحص وبحث", command=lambda: do_search(),
            bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 11, "bold"),
            padx=18, pady=5, relief="flat", cursor="hand2", activebackground="#0284c7", activeforeground="#ffffff"
        )
        search_btn.pack(side="left", padx=4)

        qr_entry = tk.Entry(
            in_row, font=("Segoe UI", 13, "bold"),
            bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT,
            justify="center"
        )
        qr_entry.pack(side="right", fill="x", expand=True, padx=4, ipady=5)
        qr_entry.focus_set()

        results_holder = tk.Frame(body, bg=self.COLOR_CARD, padx=14, pady=12)
        results_holder.pack(fill="both", expand=True)

        def clear_holder():
            for w in results_holder.winfo_children():
                w.destroy()

        def show_empty_state():
            clear_holder()
            tk.Label(
                results_holder,
                text="👈 قم بمسح باركود أي فاتورة أو سيريال جهاز أو كتابة الكود واضغط Enter\nليتم التعرف عليه تلقائياً وفتح بياناته مباشرة",
                font=("Segoe UI", 12, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_MUTED,
                justify="center", pady=60
            ).pack(expand=True)

        show_empty_state()

        def do_search(event=None):
            q_val = qr_entry.get().strip()
            if not q_val:
                show_empty_state()
                return

            res = self.db.search_all_by_qr_or_code(q_val)
            clear_holder()

            if not res:
                tk.Label(
                    results_holder,
                    text=f"❌ لم يتم العثور على أي سجل مطابق للكود: ({q_val})\nتأكد من صحة رقم السيريال أو كود الفاتورة وحاول مجدداً.",
                    font=("Segoe UI", 12, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_DANGER,
                    justify="center", pady=60
                ).pack(expand=True)
                return

            e_type = res.get('entity_type')
            title = res.get('title', 'تفاصيل السجل')
            code = res.get('code', q_val)
            data = res.get('data', {})

            hdr_box = tk.Frame(results_holder, bg=self.COLOR_CARD)
            hdr_box.pack(fill="x", pady=(0, 10))

            badge_col = self.COLOR_ACCENT if e_type == 'SALE' else (self.COLOR_WARN if e_type == 'CUSTOMER_DEBT' else self.COLOR_BLUE)
            tk.Label(
                hdr_box, text=fix_bidi(title),
                font=("Segoe UI", 14, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_TEXT
            ).pack(side="right")

            tk.Label(
                hdr_box, text=f"كود: {code}",
                font=("Segoe UI", 10, "bold"), bg=badge_col, fg="#111111" if badge_col == self.COLOR_WARN else "white",
                padx=12, pady=4
            ).pack(side="left")

            if e_type in ('SALE', 'CUSTOMER_DEBT'):
                s_obj = data
                dev_title = f"{s_obj.get('category') or ''} {s_obj.get('model') or ''}".strip()
                rem_amt = float(s_obj.get('remaining_balance') or 0)
                sp_amt = float(s_obj.get('sell_price') or 0)
                cash_amt = float(s_obj.get('cash_received') or 0)

                info_pairs = [
                    [("نوع الفاتورة:", "بيع نقدي 🟢" if rem_amt <= 0 else "مديونية عميل (خرج) 🔴"), ("تاريخ العملية:", s_obj.get('sell_date_formatted') or "-")],
                    [("اسم العميل:", s_obj.get('customer_name') or "-"), ("هاتف العميل:", s_obj.get('customer_phone') or "-")],
                    [("الجهاز المباع:", dev_title or "-"), ("السيريال IMEI:", s_obj.get('imei_serial') or "-")],
                    [("إجمالي السعر:", fmt_curr(sp_amt)), ("المدفوع نقداً:", fmt_curr(cash_amt))],
                    [("المتبقي (الخرج):", fmt_curr(rem_amt)), ("المسؤول والبائع:", s_obj.get('seller_name') or "-")],
                ]
                self._build_rtl_info_grid(results_holder, info_pairs)

                btn_box = tk.Frame(results_holder, bg=self.COLOR_CARD, pady=12)
                btn_box.pack(fill="x")

                if self.has_permission('can_print_sale_invoice'):
                    tk.Button(
                        btn_box, text="🖨️ طباعة الفاتورة",
                        command=lambda: self._print_sale_obj(s_obj),
                        bg=self.COLOR_PURPLE, fg="white", font=("Segoe UI", 10, "bold"),
                        padx=14, pady=5, relief="flat", cursor="hand2"
                    ).pack(side="right", padx=4)

                if rem_amt > 0 and self.has_permission('can_collect_customer_debt'):
                    tk.Button(
                        btn_box, text="💵 تحصيل دفعة فورية",
                        command=lambda: [qwin.destroy(), self.view_customer_debts()],
                        bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"),
                        padx=14, pady=5, relief="flat", cursor="hand2"
                    ).pack(side="right", padx=4)

                if s_obj.get('device_id'):
                    tk.Button(
                        btn_box, text="📱 عرض بطاقة الجهاز الكاملة",
                        command=lambda: self.show_device_details_modal(s_obj['device_id']),
                        bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold"),
                        padx=14, pady=5, relief="flat", cursor="hand2"
                    ).pack(side="left", padx=4)

            elif e_type == 'SUPPLIER_INVOICE':
                inv_obj = data
                info_pairs = [
                    [("المورد:", inv_obj.get('supplier_name') or "-"), ("هاتف المورد:", inv_obj.get('supplier_phone') or "-")],
                    [("تاريخ الفاتورة:", inv_obj.get('invoice_date_str') or "-"), ("حالة السداد:", "خالص بالكامل 🟢" if float(inv_obj.get('remaining_amount') or 0) <= 0 else "متبقي للمورد 🔴")],
                    [("إجمالي الفاتورة:", fmt_curr(inv_obj.get('total_amount'))), ("المدفوع للمورد:", fmt_curr(inv_obj.get('paid_amount')))],
                    [("المتبقي للمورد:", fmt_curr(inv_obj.get('remaining_amount'))), ("عدد الأجهزة:", str(len(inv_obj.get('devices', []))))],
                ]
                self._build_rtl_info_grid(results_holder, info_pairs)

                btn_box = tk.Frame(results_holder, bg=self.COLOR_CARD, pady=12)
                btn_box.pack(fill="x")

                tk.Button(
                    btn_box, text="📋 فتح تفاصيل الفاتورة وسجل الأجهزة والسداد",
                    command=lambda: self.show_supplier_invoice_details_modal(inv_obj['id']),
                    bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold"),
                    padx=16, pady=5, relief="flat", cursor="hand2"
                ).pack(side="right", padx=4)

            elif e_type == 'DEVICE':
                dev_dict = data.get('device', data)
                st_clean = str(dev_dict.get('storage') or "-").replace("GB", "").strip() or "-"
                rm_clean = str(dev_dict.get('ram') or "-").replace("GB", "").strip() or "-"
                bat_str = f"{dev_dict['battery_health']}%" if dev_dict.get('battery_health') else "-"
                box_str = "بعلبة 📦" if dev_dict.get('has_box') else "بدون علبة"
                color_str = dev_dict.get('color') or "أسود"
                tax_str = "خاضع لضريبة 🏛️" if dev_dict.get('has_tax') else "بدون ضريبة"

                info_pairs = [
                    [("كود الجهاز:", f"#{dev_dict.get('id')}"), ("الماركة والموديل:", f"{dev_dict.get('category')} {dev_dict.get('model')}")],
                    [("المساحة والرامات:", f"{st_clean} / {rm_clean}"), ("البطارية والعلبة:", f"{bat_str} - {box_str}")],
                    [("اللون:", color_str), ("الضريبة:", tax_str)],
                    [("السيريال IMEI:", dev_dict.get('imei_serial') or "-"), ("الحالة بالمخزون:", "مباع 🔴" if dev_dict.get('is_sold') else "متاح 🟢")],
                    [("المورد:", dev_dict.get('supplier_name') or "-"), ("سعر التكلفة:", fmt_curr(dev_dict.get('buy_price')) if self.has_permission('can_view_buy_price') else "🔒 مخفي")],
                ]
                self._build_rtl_info_grid(results_holder, info_pairs)

                btn_box = tk.Frame(results_holder, bg=self.COLOR_CARD, pady=12)
                btn_box.pack(fill="x")

                tk.Button(
                    btn_box, text="📱 فتح بطاقة الجهاز الكاملة",
                    command=lambda: self.show_device_details_modal(dev_dict['id']),
                    bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold"),
                    padx=16, pady=5, relief="flat", cursor="hand2"
                ).pack(side="right", padx=4)

            elif e_type == 'EXPENSE':
                exp_obj = data
                info_pairs = [
                    [("رقم السند:", f"#{exp_obj.get('id')}"), ("نوع الحركة:", exp_obj.get('transaction_type') or "سند")],
                    [("المبلغ:", fmt_curr(exp_obj.get('amount'))), ("التاريخ:", exp_obj.get('created_at_formatted') or "-")],
                    [("المسؤول / المضيف:", exp_obj.get('created_by_name') or "-"), ("البيان والملاحظات:", exp_obj.get('notes') or "-")],
                ]
                self._build_rtl_info_grid(results_holder, info_pairs)

        qr_entry.bind("<Return>", do_search)

        if initial_query:
            qr_entry.insert(0, initial_query)
            do_search()

    def _print_sale_obj(self, sale_obj):
        if not sale_obj:
            return
        rem = float(sale_obj.get('remaining_balance') or 0)
        inv_data = {
            'doc_type': 'SALE' if rem <= 0 else 'CUSTOMER_DEBT',
            'sale_id': sale_obj['id'],
            'customer_name': sale_obj.get('customer_name') or 'عميل نقدي',
            'customer_phone': sale_obj.get('customer_phone') or '-',
            'seller_name': sale_obj.get('seller_name') or '',
            'device': {
                'id': sale_obj.get('device_id'),
                'category': sale_obj.get('category'),
                'model': sale_obj.get('model'),
                'storage': sale_obj.get('storage'),
                'ram': sale_obj.get('ram'),
                'battery_health': sale_obj.get('battery_health'),
                'imei_serial': sale_obj.get('imei_serial'),
                'device_condition': sale_obj.get('device_condition') or 'مستعمل',
                'has_box': sale_obj.get('has_box', False),
                'color': sale_obj.get('color') or 'أسود',
                'has_tax': bool(sale_obj.get('has_tax')),
                'accessories': sale_obj.get('accessories') or ''
            },
            'original_price': float(sale_obj.get('sell_price') or 0),
            'discount': 0.0,
            'sell_price': float(sale_obj.get('sell_price') or 0),
            'cash_received': float(sale_obj.get('cash_received') or 0),
            'remaining_balance': rem,
            'sale_notes': sale_obj.get('notes') or '',
            'payments_list': sale_obj.get('payments', []),
            'date_str': sale_obj.get('sell_date_formatted') or ''
        }
        self.open_invoice_preview_and_print(inv_data, f"طباعة فاتورة #{sale_obj['id']}")

    def print_sale_invoice_by_id(self, sale_id):
        s_id = clean_id_val(sale_id)
        if not s_id:
            messagebox.showwarning("تنبيه", "رقم الفاتورة غير محدد أو غير صالح!")
            return
        sale_obj = self.db.get_sale_by_id(s_id)
        if not sale_obj:
            messagebox.showerror("خطأ", f"تعذر العثور على فاتورة البيع #{s_id} بقاعدة البيانات!")
            return
        self._print_sale_obj(sale_obj)

    def show_device_details_modal(self, device_id):
        dev_id_clean = clean_id_val(device_id)
        details = self.db.get_device_full_details(dev_id_clean)
        if not details or not details.get('device'):
            messagebox.showerror("خطأ", f"تعذر جلب بيانات الجهاز #{device_id}")
            return

        dev = details['device']
        sale = details.get('sale')
        payments = details.get('customer_payments', [])

        dwin = tk.Toplevel(self)
        dwin.title(f"بيانات الجهاز #{dev['id']} - {dev['category']} {dev['model']}")
        dwin.geometry("860x720")
        dwin.configure(bg=self.COLOR_BG)
        dwin.grab_set()

        header = tk.Frame(dwin, bg=self.COLOR_TOPBAR, pady=10, padx=16)
        header.pack(fill="x")
        title_txt = fix_bidi(f"📱 بيانات الجهاز: {dev['category']} {dev['model']}  |  كود #{dev['id']}")
        tk.Label(header, text=title_txt, font=("Segoe UI", 14, "bold"), bg=self.COLOR_TOPBAR, fg="#38bdf8").pack(side="right")

        status_badge_txt = "محذوف 🗑️" if dev.get('is_deleted') else ("مباع 🔴" if dev.get('is_sold') else "متاح بالمخزون 🟢")
        status_badge_col = self.COLOR_DANGER if (dev.get('is_deleted') or dev.get('is_sold')) else self.COLOR_ACCENT
        tk.Label(header, text=fix_bidi(status_badge_txt), font=("Segoe UI", 10, "bold"), bg=status_badge_col, fg="white", padx=12, pady=3).pack(side="left")

        def trigger_edit_from_details():
            if not self.has_permission('can_edit_inventory'):
                messagebox.showerror("صلاحيات غير كافية", "عفواً، لا تملك صلاحية تعديل بيانات الأجهزة!", parent=dwin)
                return
            def on_edit_done():
                dwin.destroy()
                self.show_device_details_modal(dev['id'])
                if self.current_view_func:
                    self.current_view_func()
            self.open_edit_device_modal(dev, on_success_callback=on_edit_done)

        if self.has_permission('can_edit_inventory') and not dev.get('is_deleted'):
            tk.Button(
                header, text="✏️ تعديل بيانات الجهاز", command=trigger_edit_from_details,
                bg=self.COLOR_INDIGO, fg="white", font=("Segoe UI", 10, "bold"),
                padx=14, pady=4, relief="flat", cursor="hand2"
            ).pack(side="left", padx=8)

        bot_bar = tk.Frame(dwin, bg=self.COLOR_TOPBAR, pady=8, padx=16)
        bot_bar.pack(side="bottom", fill="x")
        tk.Button(bot_bar, text="إغلاق النافذة", command=dwin.destroy, bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 10, "bold"), padx=20, pady=4, relief="flat", cursor="hand2").pack(side="left")
        if self.has_permission('can_edit_inventory') and not dev.get('is_deleted'):
            tk.Button(
                bot_bar, text="✏️ تعديل بيانات الجهاز", command=trigger_edit_from_details,
                bg=self.COLOR_INDIGO, fg="white", font=("Segoe UI", 10, "bold"),
                padx=16, pady=4, relief="flat", cursor="hand2"
            ).pack(side="right", padx=6)

        scroll_body = self._create_scrollable_frame(dwin, bg_color=self.COLOR_BG, pad_x=16, pad_y=10)

        card1 = tk.LabelFrame(scroll_body, text="📋 المواصفات الفنية وبيانات الشراء", bg=self.COLOR_CARD, fg=self.COLOR_BLUE, font=("Segoe UI", 11, "bold"), padx=12, pady=8)
        card1.pack(fill="x", pady=6)

        can_see_cost = self.has_permission('can_view_buy_price')
        buy_p_str = fmt_curr(dev['buy_price']) if can_see_cost else "🔒 مخفي للمصرح لهم فقط"
        init_sp_val = dev.get('initial_selling_price') or dev.get('selling_price') or dev.get('buy_price') or 0
        init_sp_str = fmt_curr(init_sp_val)

        bat_str = f"{dev['battery_health']}%" if dev.get('battery_health') else "-"
        ram_str = str(dev.get('ram') or "-").replace("GB", "").strip() or "-"
        storage_str = str(dev.get('storage') or "-").replace("GB", "").strip() or "-"
        cond_str = dev.get('device_condition') or "مستعمل"
        box_str = "بعلبة 📦" if dev.get('has_box') else "بدون علبة ❌"
        buy_notes_str = dev.get('notes') or "-"
        color_str = dev.get('color') or "أسود"
        tax_str = "خاضع لضريبة 🏛️" if dev.get('has_tax') else "بدون ضريبة"
        acc_str = dev.get('accessories') or "-"

        pairs1 = [
            [("الماركة:", dev['category']), ("الموديل:", dev['model'])],
            [("كود الجهاز (ID):", f"#{dev['id']}"), ("السيريال (IMEI):", dev['imei_serial'])],
            [("حالة الجهاز:", cond_str), ("العلبة:", box_str)],
            [("اللون:", color_str), ("الضريبة:", tax_str)],
            [("المساحة:", storage_str), ("الرامات (RAM):", ram_str)],
            [("سعر الشراء (للمصرح):", buy_p_str), ("سعر البيع المبدئي:", init_sp_str)],
            [("البطارية:", bat_str), ("المورد:", f"{dev.get('supplier_name') or '-'} ({dev.get('supplier_type', 'تاجر')})")],
            [("تاريخ الشراء:", dev.get('buy_date_formatted') or "-"), ("الملحقات:", acc_str)],
            [("مُدخل الجهاز:", dev.get('created_by_name') or "-"), ("ملاحظات الشراء:", buy_notes_str)],
        ]
        self._build_rtl_info_grid(card1, pairs1)

        can_edit_dt = self.has_permission('can_edit_operation_dates') or self.has_permission('can_edit_transaction_date')
        if can_edit_dt and not dev.get('is_deleted'):
            card1_act = tk.Frame(card1, bg=self.COLOR_CARD)
            card1_act.pack(fill="x", pady=(4, 2))
            tk.Button(
                card1_act, text="📅 تعديل تاريخ الشراء (وتحديث فاتورة المورد)",
                command=lambda: self.open_edit_record_date_modal("DEVICE", dev['id'], dev.get('buy_date_formatted'), on_success_callback=lambda: (dwin.destroy(), self.show_device_details_modal(dev['id']))),
                bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 9, "bold"),
                padx=12, pady=4, relief="flat", cursor="hand2"
            ).pack(side="right", padx=6)

        card2 = tk.LabelFrame(scroll_body, text="🛒 بيانات البيع والعميل", bg=self.COLOR_CARD, fg=self.COLOR_ACCENT, font=("Segoe UI", 11, "bold"), padx=12, pady=8)
        card2.pack(fill="x", pady=6)

        if sale:
            can_see_profit = self.has_permission('can_view_profits') and can_see_cost
            net_p_str = fmt_curr(sale['net_profit']) if can_see_profit else "🔒 مخفي"
            sale_notes_str = sale.get('notes') or "-"
            pairs2 = [
                [("رقم فاتورة البيع:", f"#{sale['id']}"), ("تاريخ البيع:", sale.get('sell_date_formatted') or "-")],
                [("اسم العميل:", sale['customer_name']), ("هاتف العميل:", sale.get('customer_phone') or "-")],
                [("سعر البيع:", fmt_curr(sale['sell_price'])), ("المدفوع نقداً:", fmt_curr(sale['cash_received']))],
                [("المتبقي (الخرج):", fmt_curr(sale['remaining_balance'])), ("حالة السداد:", sale.get('payment_status') or "-")],
                [("البائع:", sale.get('seller_name') or "-"), ("صافي الربح:", net_p_str)],
                [("ملاحظات البيع:", sale_notes_str), ("", "")],
            ]
            self._build_rtl_info_grid(card2, pairs2)

            sale_actions_row = tk.Frame(card2, bg=self.COLOR_CARD)
            sale_actions_row.pack(pady=6)

            if can_edit_dt:
                tk.Button(
                    sale_actions_row, text="📅 تعديل تاريخ البيع",
                    command=lambda: self.open_edit_record_date_modal("SALE", sale['id'], sale.get('sell_date_formatted'), on_success_callback=lambda: (dwin.destroy(), self.show_device_details_modal(dev['id']))),
                    bg="#0284c7", fg="white", font=("Segoe UI", 10, "bold"),
                    padx=14, pady=5, relief="flat", cursor="hand2"
                ).pack(side="right", padx=6)

            if self.has_permission('can_print_sale_invoice'):
                def print_this_sale():
                    inv_data = {
                        'doc_type': 'SALE' if float(sale.get('remaining_balance') or 0) <= 0 else 'CUSTOMER_DEBT',
                        'sale_id': sale['id'],
                        'customer_name': sale['customer_name'],
                        'customer_phone': sale.get('customer_phone') or '-',
                        'seller_name': sale.get('seller_name') or '',
                        'device': dev,
                        'original_price': float(sale['sell_price']),
                        'discount': 0.0,
                        'sell_price': float(sale['sell_price']),
                        'cash_received': float(sale['cash_received']),
                        'remaining_balance': float(sale['remaining_balance']),
                        'sale_notes': sale.get('notes') or '',
                        'payments_list': payments,
                        'date_str': sale.get('sell_date_formatted') or ''
                    }
                    self.open_invoice_preview_and_print(inv_data, f"طباعة فاتورة بيع #{sale['id']}")

                tk.Button(sale_actions_row, text="🖨️ طباعة الفاتورة", command=print_this_sale, bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold"), padx=16, pady=5, relief="flat", cursor="hand2").pack(side="right", padx=6)

            if self.has_permission('can_process_returns'):
                def return_this_sold_device():
                    if messagebox.askyesno("تأكيد استرجاع الجهاز", "هل أنت متأكد من إلغاء بيع هذا الجهاز وإعادته للمخزون؟", parent=dwin):
                        try:
                            self.db.process_return(dev['id'], self.current_user_id)
                            messagebox.showinfo("تم الإرجاع", "تم استرجاع الجهاز وإعادته للمخزون بنجاح!", parent=dwin)
                            dwin.destroy()
                            if self.current_view_func:
                                self.current_view_func()
                        except Exception as ex:
                            messagebox.showerror("خطأ", str(ex), parent=dwin)

                tk.Button(sale_actions_row, text="🔄 استرجاع للمخزون", command=return_this_sold_device, bg=self.COLOR_WARN, fg="#111", font=("Segoe UI", 10, "bold"), padx=16, pady=5, relief="flat", cursor="hand2").pack(side="right", padx=6)
        else:
            tk.Label(card2, text="🟢 الجهاز متاح حالياً في المخزون.", font=("Segoe UI", 11, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_ACCENT).pack(pady=8)

        card3 = tk.LabelFrame(scroll_body, text="💳 سجل دفعات العميل (الخرج)", bg=self.COLOR_CARD, fg=self.COLOR_WARN, font=("Segoe UI", 11, "bold"), padx=12, pady=8)
        card3.pack(fill="x", pady=6)

        if payments:
            cols = ("الموظف المستلم", "تاريخ الدفعة", "المبلغ المسدد", "م")
            ptree = ttk.Treeview(card3, columns=cols, show="headings", height=max(4, min(8, len(payments) + 1)))
            self.configure_tree_row_colors(ptree)
            for c in cols:
                ptree.heading(c, text=c)
                ptree.column(c, anchor="center", width=160 if c != "م" else 60)
            ptree.pack(fill="x", pady=4)

            for idx_p, p in enumerate(payments, 1):
                row_tag = 'evenrow' if idx_p % 2 == 0 else 'oddrow'
                ptree.insert("", "end", tags=(row_tag,), values=(fix_bidi(p['receiver_name']), p['payment_date_formatted'], fmt_curr(p['payment_amount']), idx_p))
        else:
            tk.Label(card3, text="لا توجد دفعات مسجلة لهذا الجهاز.", font=("Segoe UI", 10, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_MUTED).pack(pady=6)

    def open_permissions_guide_dialog(self):
        gwin = tk.Toplevel(self)
        gwin.title("📖 دليل وشرح صلاحيات النظام الشامل - مركز هشام كيوان")
        gwin.geometry("880x720")
        gwin.configure(bg=self.COLOR_BG)
        gwin.grab_set()

        top_b = tk.Frame(gwin, bg=self.COLOR_TOPBAR, pady=12, padx=18)
        top_b.pack(fill="x")

        tk.Label(
            top_b, text="📖 دليل وشرح صلاحيات النظام الشامل (مركز هشام كيوان)",
            font=("Segoe UI", 15, "bold"), bg=self.COLOR_TOPBAR, fg="#38bdf8"
        ).pack(side="right")

        tk.Label(
            top_b, text="شرح تفصيلي لدور وتأثير كل صلاحية أمنياً ومالياً",
            font=("Segoe UI", 10, "bold"), bg=self.COLOR_TOPBAR, fg=self.COLOR_MUTED
        ).pack(side="left")

        search_f = tk.Frame(gwin, bg=self.COLOR_CARD, padx=16, pady=10, highlightthickness=1, highlightbackground=self.COLOR_BORDER)
        search_f.pack(fill="x", padx=16, pady=8)

        tk.Label(search_f, text="🔍 ابحث في الصلاحيات:", font=("Segoe UI", 11, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_BLUE).pack(side="right", padx=6)
        guide_search_ent = tk.Entry(search_f, font=("Segoe UI", 12, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="right", width=30)
        guide_search_ent.pack(side="right", padx=6, ipady=3)
        guide_search_ent.focus_set()

        lbl_guide_count = tk.Label(search_f, text=f"إجمالي الصلاحيات: {len(PERMISSIONS_DICT)}", font=("Segoe UI", 10, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_MUTED)
        lbl_guide_count.pack(side="left", padx=8)

        scroll_body = self._create_scrollable_frame(gwin, bg_color=self.COLOR_BG, pad_x=16, pad_y=8)

        perm_details_map = {
            'can_view_buy_price': {
                'role': 'إظهار سعر التكلفة وسعر الشراء الحقيقي للأجهزة في المخزون والمبيعات والتقارير.',
                'impact': 'حساس للغاية: إخفاؤه يمنع الموظف أو الكاشير من معرفة هامش الربح أو أسرار التكلفة.',
                'recommended': 'المدير العام والمحاسب وأمين المخزن فقط.'
            },
            'can_manage_inventory': {
                'role': 'التحكم الإداري الكامل ببطاقات الأجهزة وإجراءات المخزون والتوريد.',
                'impact': 'إداري وتنظيمي للمستودع وضبط الأجهزة المتاحة والمباعة.',
                'recommended': 'المدير العام وأمين المخزن.'
            },
            'can_manage_users': {
                'role': 'إضافة حسابات الموظفين وتعديل بياناتهم وتفعيلهم وإلغاء قفلهم وتعيين الصلاحيات.',
                'impact': 'أعلى مستوى أمني (Root Admin): يجب منحه بحذر شديد لأنه يتحكم بكل الحسابات.',
                'recommended': 'مدير النظام التنفيذي فقط.'
            },
            'can_view_reports': {
                'role': 'الدخول لشاشة التقارير المالية والإحصائيات العامة للمحل.',
                'impact': 'اطلاع على المركز المالي وحجم المبيعات العام للمركز.',
                'recommended': 'المدير والمحاسب المالي.'
            },
            'can_process_returns': {
                'role': 'إجراء مرتجع لجهاز مباع، واسترداد المبلغ للعميل، وإعادة الجهاز للمخزون تلقائياً.',
                'impact': 'يؤثر على الخزينة النقدية ورصيد العميل ويعيد الجهاز للمخزون.',
                'recommended': 'المدير العام أو مسؤول المبيعات المعتمد.'
            },
            'can_edit_prices': {
                'role': 'تعديل سعر البيع المباشر للأجهزة أثناء إتمام الفاتورة بالمعرض.',
                'impact': 'مرونة في البيع والخصم، مسجلة بالكامل في سجل العمليات.',
                'recommended': 'مسؤول المبيعات الموثوق والمدير.'
            },
            'can_view_inventory': {
                'role': 'عرض شاشة المخزون والبحث في الأجهزة المتاحة وحالاتها.',
                'impact': 'استعراض البيانات فقط دون إمكانية التعديل أو الحذف.',
                'recommended': 'جميع الموظفين والكاشير.'
            },
            'can_edit_inventory': {
                'role': 'تعديل مواصفات الأجهزة وسيريال IMEI واللون والبطارية وسعر البيع المبدئي.',
                'impact': 'تعديل مباشر على بيانات الأجهزة بالمخزون مع تسجيل الفرق بسجل الرقابة.',
                'recommended': 'أمين المخزن والمدير العام.'
            },
            'can_delete_inventory': {
                'role': 'حذف أجهزة من المخزون أو أرشفتها وتخيير المستخدم عند حذف جهاز مسدد.',
                'impact': 'خطير وحساس: يحذف الجهاز ويعدل فواتير المورد المرتبطة.',
                'recommended': 'المدير العام فقط.'
            },
            'can_view_device_details': {
                'role': 'فتح بطاقة الفحص الشامل وسجل الجهاز المالي ودفعات العميل المرتبطة.',
                'impact': 'استعراض سجل الجهاز التاريخي الكامل.',
                'recommended': 'كافة الموظفين والفنيين.'
            },
            'can_buy_devices': {
                'role': 'فتح شاشة المشتريات وإدخال أجهزة جديدة وفواتير توريد.',
                'impact': 'إضافة أصول جديدة للمخزون وتسجيل مديونيات على المحل للموردين.',
                'recommended': 'أمين المخزن ومسؤول المشتريات والمدير.'
            },
            'can_add_supplier_in_buy': {
                'role': 'إضافة وتوثيق مورد أو تاجر جديد سريعاً أثناء إدخال فاتورة الشراء.',
                'impact': 'تسجيل مورد جديد بدفاتر النظام.',
                'recommended': 'أمين المخزن والمدير.'
            },
            'can_view_sales_screen': {
                'role': 'فتح نافذة المبيعات والكاشير والبحث عن الأجهزة.',
                'impact': 'تشغيل نقطة البيع اليومية.',
                'recommended': 'مسؤولو المبيعات والكاشير.'
            },
            'can_execute_sale': {
                'role': 'تأكيد وإتمام عمليات البيع وتوليد الفواتير واستلام النقدية.',
                'impact': 'توليد فاتورة بيع، خصم الجهاز من المخزون، وتحديث الخزينة والديون.',
                'recommended': 'الكاشير والمدير.'
            },
            'can_print_sale_invoice': {
                'role': 'طباعة فواتير البيع للعملاء بالمقاسات والأنماط المعتمدة.',
                'impact': 'إصدار مستند ورقي وضمان رسمي معتمد باسم المحل.',
                'recommended': 'الكاشير والمبيعات.'
            },
            'can_sell_below_cost': {
                'role': 'السماح بإتمام البيع بسعر يقل عن سعر التكلفة المسجل.',
                'impact': 'تحقيق خسارة مباشرة على الجهاز - يقتصر على الصفقات الخاصة وتصفية الأجهزة.',
                'recommended': 'المدير العام حصراً.'
            },
            'can_edit_transactions': {
                'role': 'تعديل أو إلغاء المعاملات والديون السابقة.',
                'impact': 'تعديل القيود المالية المسجلة.',
                'recommended': 'المدير العام والمحاسب.'
            },
            'can_delete_sales': {
                'role': 'إلغاء وحذف عمليات بيع كاملة واسترجاع أجهزتها للمخزون.',
                'impact': 'إلغاء قيد مالي وفاتورة مبيعات بالكامل وتصحيح الخزينة.',
                'recommended': 'المدير العام فقط.'
            },
            'can_edit_operation_dates': {
                'role': 'تحديد وتعديل تواريخ العمليات (بيع، شراء، سداد، سيولة) يدوياً أو اختيار تاريخ سابق.',
                'impact': 'تأثير زمني بأثر رجعي، يُمنع فيه التاريخ المستقبلي ويُسجل بسجل الرقابة.',
                'recommended': 'المدير العام والمحاسب المعتمد.'
            },
            'can_edit_transaction_date': {
                'role': 'تعديل تاريخ العمليات والحركات المالية في النظام يدوياً.',
                'impact': 'تسجيل العمليات بتواريخ سابقة لتسوية الحسابات القديمة.',
                'recommended': 'المحاسب المالي والمدير.'
            },
            'can_custom_print_terms': {
                'role': 'تخصيص وكتابة بنود وشروط الضمان المطبوعة على الفاتورة.',
                'impact': 'تعديل نص الالتزام القانوني والضماني تجاه العميل.',
                'recommended': 'المدير العام.'
            },
            'can_view_customer_debts': {
                'role': 'عرض شاشة ديون العملاء (الخرج) وكشوفات الحسابات الآجلة.',
                'impact': 'متابعة المبالغ المستحقة على العملاء لدى المحل.',
                'recommended': 'الكاشير والمحاسب والمدير.'
            },
            'can_collect_customer_debt': {
                'role': 'تسجيل تحصيل أقساط ودفعات نقدية من ديون العملاء وإيداعها بالخزينة.',
                'impact': 'زيادة نقدية الخزينة وتخفيض مديونية العميل وإصدار إيصال قبض.',
                'recommended': 'الكاشير والمحاسب والمدير.'
            },
            'can_print_customer_debt': {
                'role': 'طباعة إيصال سداد أو كشف حساب ديون للعميل.',
                'impact': 'إصدار سند مالي ورقي معتمد للعميل.',
                'recommended': 'الكاشير والمحاسب.'
            },
            'can_view_supplier_debts': {
                'role': 'عرض فواتير وحسابات الموردين والأرصدة الدائنة والمدينة وفلترة التواريخ.',
                'impact': 'متابعة التزامات المركز تجاه التجار والموردين.',
                'recommended': 'المحاسب والمدير وأمين المخزن.'
            },
            'can_pay_supplier_debt': {
                'role': 'تسجيل سداد دفعات نقدية للموردين مع تحويل الفائض لرصيد دائن تلقائياً.',
                'impact': 'صرف نقدي من الخزينة وسداد مديونية مورد.',
                'recommended': 'المدير العام والمحاسب المالي.'
            },
            'can_refund_supplier_credit': {
                'role': 'استرداد الأرصدة الدائنة المستحقة لنا لدى المورد نقداً إلى الخزينة (كلياً أو جزئياً).',
                'impact': 'إيداع نقدي في الخزينة وتسوية رصيد أمانات المورد.',
                'recommended': 'المدير العام والمحاسب.'
            },
            'can_manage_suppliers': {
                'role': 'إضافة وتعديل بيانات وهواتف الموردين والشركات.',
                'impact': 'تنظيم دليل الموردين المعتمدين.',
                'recommended': 'أمين المخزن والمدير.'
            },
            'can_delete_suppliers': {
                'role': 'أرشفة وحذف الموردين غير النشطين بعد التأكد من تصفية المديونية والرصيد الدائن.',
                'impact': 'إخفاء أو أرشفة ملف المورد دون الإضرار بالفواتير التاريخية.',
                'recommended': 'المدير العام حصراً.'
            },
            'can_print_supplier_invoice': {
                'role': 'طباعة فواتير التوريد وكشوف حسابات الموردين متعددة الصفحات.',
                'impact': 'مستند تسوية ومطابقة معتمد بين المحل والمورد.',
                'recommended': 'المحاسب والمدير وأمين المخزن.'
            },
            'can_view_capital_details': {
                'role': 'عرض تفاصيل ومعادلة رأس المال الشامل مع الرصيد الدائن والمخزون.',
                'impact': 'رؤية المركز المالي الصافي للمنشأة بالكامل.',
                'recommended': 'المالك والمدير العام فقط.'
            },
            'can_view_liquidity': {
                'role': 'رؤية رصيد الخزينة والسيولة النقدية المتاحة حالياً.',
                'impact': 'معرفة المتاح النقدي بالدرج أو الخزينة.',
                'recommended': 'المدير والمحاسب.'
            },
            'can_add_liquidity': {
                'role': 'إيداع وضخ مبالغ نقدية إضافية في الخزينة ورأس المال.',
                'impact': 'زيادة الرصيد النقدي الفعلي للخزينة.',
                'recommended': 'المالك والمدير العام.'
            },
            'can_delete_liquidity_tx': {
                'role': 'حذف وتسوية حركات الخزينة والسيولة.',
                'impact': 'تعديل قيود الخزينة (حساس للغاية).',
                'recommended': 'المدير العام فقط.'
            },
            'can_view_liquidity_log': {
                'role': 'عرض السجل التاريخي لحركات الإيداع والسحب بالخزينة.',
                'impact': 'تتبع حركة النقدية اليومية.',
                'recommended': 'المحاسب والمدير.'
            },
            'can_view_profits': {
                'role': 'رؤية صافي الأرباح المحققة على مستوى العمليات والفترات.',
                'impact': 'معلومات ربحية سرية خاصة بالإدارة.',
                'recommended': 'المالك والمدير العام.'
            },
            'can_view_sales_report': {
                'role': 'عرض سجل المبيعات التفصيلي وفلاتر التواريخ والمبيعات.',
                'impact': 'تحليل حركة البيع والعملاء.',
                'recommended': 'المحاسب والمدير.'
            },
            'can_export_reports': {
                'role': 'تصدير وطباعة التقارير المالية وسجلات المبيعات إلى ملفات خارجية.',
                'impact': 'إخراج البيانات المالية خارج النظام.',
                'recommended': 'المدير العام والمحاسب.'
            },
            'can_view_audit_logs': {
                'role': 'عرض سجل الرقابة الدقيق لكافة عمليات وتعديلات النظام والمستخدمين.',
                'impact': 'كشف أي تلاعب أو حذف أو تعديل أو فروق أسعار بالثانية واسم الموظف.',
                'recommended': 'المدير العام ومسؤول الرقابة الداخلية.'
            },
            'can_filter_audit_logs': {
                'role': 'البحث والفلترة المتقدمة بالتواريخ ونوع الحركة في سجل العمليات.',
                'impact': 'أدوات تحقيق ومراجعة دقيقة وسريعة.',
                'recommended': 'المدير العام.'
            }
        }

        group_lookup = {}
        for g_title, g_items in PERMISSION_GROUPS:
            for pk, _ in g_items:
                group_lookup[pk] = g_title

        cards_holder = tk.Frame(scroll_body, bg=self.COLOR_BG)
        cards_holder.pack(fill="both", expand=True)

        def build_cards(search_query=""):
            for w in cards_holder.winfo_children():
                w.destroy()

            q_clean = search_query.strip().lower()
            matched_count = 0

            for p_key, p_name in PERMISSIONS_DICT.items():
                p_info = perm_details_map.get(p_key, {})
                p_role = p_info.get('role', 'إجراء عمليات محددة في الشاشة المخصصة.')
                p_impact = p_info.get('impact', 'تأثير تشغيلي مسجل في سجل العمليات.')
                p_rec = p_info.get('recommended', 'حسب طبيعة عمل الموظف.')
                p_grp = group_lookup.get(p_key, "عام")

                searchable_str = f"{p_name} {p_key} {p_grp} {p_role} {p_impact} {p_rec}".lower()
                if q_clean and q_clean not in searchable_str:
                    continue

                matched_count += 1

                card_f = tk.LabelFrame(
                    cards_holder, text=f"🔐 {p_name} ({p_grp})",
                    bg=self.COLOR_CARD, fg=self.COLOR_BLUE, font=("Segoe UI", 12, "bold"),
                    padx=14, pady=10, highlightthickness=1, highlightbackground=self.COLOR_BORDER
                )
                card_f.pack(fill="x", pady=6)

                hdr_sub = tk.Frame(card_f, bg=self.COLOR_CARD)
                hdr_sub.pack(fill="x", pady=(0, 6))

                tk.Label(
                    hdr_sub, text=f"الكود البرمجي: {p_key}",
                    font=("Consolas", 10, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT,
                    padx=8, pady=2
                ).pack(side="left")

                tk.Label(
                    hdr_sub, text=f"القسم: {p_grp}",
                    font=("Segoe UI", 10, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_MUTED
                ).pack(side="right")

                body_grid = tk.Frame(card_f, bg=self.COLOR_CARD)
                body_grid.pack(fill="x", pady=4)
                body_grid.grid_columnconfigure(0, weight=1)

                tk.Label(body_grid, text="• الدور الوظيفي:", font=("Segoe UI", 10, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_TEXT).grid(row=0, column=1, sticky="ne", padx=4, pady=3)
                tk.Label(body_grid, text=p_role, font=("Segoe UI", 10, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_BLUE, wraplength=580, justify="right", anchor="e").grid(row=0, column=0, sticky="ew", padx=4, pady=3)

                tk.Label(body_grid, text="• الأثر الأمني والمالي:", font=("Segoe UI", 10, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_TEXT).grid(row=1, column=1, sticky="ne", padx=4, pady=3)
                tk.Label(body_grid, text=p_impact, font=("Segoe UI", 10, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_ACCENT, wraplength=580, justify="right", anchor="e").grid(row=1, column=0, sticky="ew", padx=4, pady=3)

                tk.Label(body_grid, text="• الأدوار الموصى بها:", font=("Segoe UI", 10, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_TEXT).grid(row=2, column=1, sticky="ne", padx=4, pady=3)
                tk.Label(body_grid, text=p_rec, font=("Segoe UI", 10, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_PURPLE, wraplength=580, justify="right", anchor="e").grid(row=2, column=0, sticky="ew", padx=4, pady=3)

            lbl_guide_count.config(text=f"الصلاحيات المعروضة: {matched_count} من {len(PERMISSIONS_DICT)}")

        guide_search_ent.bind("<KeyRelease>", lambda e: build_cards(guide_search_ent.get()))
        build_cards()

        bot_f = tk.Frame(gwin, bg=self.COLOR_TOPBAR, pady=8, padx=16)
        bot_f.pack(side="bottom", fill="x")

        tk.Button(
            bot_f, text="إغلاق الدليل", command=gwin.destroy,
            bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold"),
            padx=18, pady=4, relief="flat", cursor="hand2"
        ).pack(side="left")

    def view_user_management(self):
        if not self.has_permission('can_manage_users'):
            messagebox.showerror("صلاحيات غير كافية", "عفواً، لا تملك صلاحية إدارة المستخدمين!")
            return

        self.current_view_func = self.view_user_management
        self.build_main_ui(keep_view=True)
        self.clear_content()

        hdr = tk.Frame(self.content_frame, bg=self.COLOR_BG, pady=10, padx=18)
        hdr.pack(fill="x")

        tk.Label(
            hdr, text="👥 إدارة المستخدمين والصلاحيات",
            font=("Segoe UI", 16, "bold"), bg=self.COLOR_BG, fg=self.COLOR_BLUE
        ).pack(side="right")

        btn_bar = tk.Frame(hdr, bg=self.COLOR_BG)
        btn_bar.pack(side="left")

        tk.Button(
            btn_bar, text="➕ إضافة مستخدم", command=lambda: self._open_user_editor_modal(None),
            bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"),
            padx=16, pady=6, relief="flat", cursor="hand2", activebackground="#047857", activeforeground="#ffffff"
        ).pack(side="right", padx=5)

        tk.Button(
            btn_bar, text="📖 دليل وشرح الصلاحيات", command=self.open_permissions_guide_dialog,
            bg="#6366f1", fg="white", font=("Segoe UI", 10, "bold"),
            padx=14, pady=6, relief="flat", cursor="hand2", activebackground="#4f46e5", activeforeground="#ffffff"
        ).pack(side="right", padx=5)

        tk.Button(
            btn_bar, text="✏️ تعديل المستخدم", command=lambda: edit_selected_user(),
            bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold"),
            padx=16, pady=6, relief="flat", cursor="hand2", activebackground="#0284c7", activeforeground="#ffffff"
        ).pack(side="right", padx=5)

        tk.Button(
            btn_bar, text="🔄 تفعيل / إيقاف", command=lambda: toggle_selected_user_status(),
            bg=self.COLOR_WARN, fg="#111111", font=("Segoe UI", 10, "bold"),
            padx=16, pady=6, relief="flat", cursor="hand2", activebackground="#d97706", activeforeground="#ffffff"
        ).pack(side="right", padx=5)

        tk.Button(
            btn_bar, text="🔄 تحديث", command=lambda: load_users(),
            bg=self.COLOR_TEAL, fg="white", font=("Segoe UI", 10, "bold"),
            padx=14, pady=6, relief="flat", cursor="hand2", activebackground="#0f766e", activeforeground="#ffffff"
        ).pack(side="left", padx=5)

        table_frame = tk.Frame(self.content_frame, bg=self.COLOR_CARD, padx=14, pady=12)
        table_frame.pack(fill="both", expand=True, padx=18, pady=(0, 16))

        cols = ("الحالة", "عدد الصلاحيات", "الدور الوظيفي", "الاسم بالكامل", "اسم الدخول", "كود")
        utree = ttk.Treeview(table_frame, columns=cols, show="headings")
        self.configure_tree_row_colors(utree)
        col_widths = {
            "الحالة": 110, "عدد الصلاحيات": 130, "الدور الوظيفي": 140,
            "الاسم بالكامل": 220, "اسم الدخول": 160, "كود": 70
        }
        for c in cols:
            utree.heading(c, text=c)
            utree.column(c, anchor="center", width=col_widths.get(c, 130))

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=utree.yview)
        utree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="left", fill="y")
        utree.pack(side="right", fill="both", expand=True)

        role_labels = {
            "admin": "مدير عام", "sales": "مسؤول مبيعات",
            "inventory": "أمين مخزن", "accountant": "محاسب مالي", "custom": "مخصص"
        }
        users_cache = {}

        def load_users():
            utree.delete(*utree.get_children())
            users_cache.clear()
            for u in self.db.get_all_users():
                uid = u['id']
                users_cache[uid] = u
                perms = u.get('permissions') or {}
                if isinstance(perms, str):
                    try:
                        perms = json.loads(perms)
                    except Exception:
                        perms = {}
                active_perms_count = sum(1 for k in PERMISSIONS_DICT if perms.get(k))
                if str(u.get('username')).lower() == 'admin' or str(u.get('role')).lower() == 'admin':
                    active_perms_count = len(PERMISSIONS_DICT)

                r_code = str(u.get('role') or 'custom').lower()
                r_txt = role_labels.get(r_code, "مخصص")
                st_txt = "نشط 🟢" if u.get('is_active', True) else "موقوف 🔴"
                row_tag = 'evenrow' if len(users_cache) % 2 == 0 else 'oddrow'

                utree.insert("", "end", iid=str(uid), tags=(row_tag,), values=(
                    fix_bidi(st_txt),
                    f"{active_perms_count} / {len(PERMISSIONS_DICT)}",
                    fix_bidi(r_txt),
                    fix_bidi(u.get('full_name') or u['username']),
                    u['username'],
                    f"#{uid}"
                ))

        def get_selected_user_obj():
            sel = utree.selection()
            if not sel:
                messagebox.showwarning("تنبيه", "يرجى تحديد مستخدم من الجدول أولاً!")
                return None
            uid = clean_id_val(sel[0])
            return users_cache.get(uid)

        def edit_selected_user():
            u = get_selected_user_obj()
            if u:
                self._open_user_editor_modal(u, on_saved_callback=load_users)

        def toggle_selected_user_status():
            u = get_selected_user_obj()
            if not u:
                return
            if str(u['username']).lower() == 'admin':
                messagebox.showwarning("تنبيه", "لا يمكن إيقاف حساب المدير الرئيسي للنظام!")
                return
            new_st = not bool(u.get('is_active', True))
            action_str = "تفعيل" if new_st else "إيقاف"
            if messagebox.askyesno("تأكيد", f"هل تريد {action_str} حساب المستخدم ({u['username']})؟"):
                try:
                    self.db.toggle_user_active(u['id'], new_st)
                    load_users()
                except Exception as ex:
                    messagebox.showerror("خطأ", str(ex))

        utree.bind("<Double-1>", lambda e: edit_selected_user())
        load_users()

    def _open_user_editor_modal(self, user_obj=None, on_saved_callback=None):
        is_edit = user_obj is not None
        uwin = tk.Toplevel(self)
        uwin.title("تعديل بيانات وصلاحيات مستخدم" if is_edit else "إضافة مستخدم جديد")
        uwin.geometry("820x720")
        uwin.configure(bg=self.COLOR_BG)
        uwin.grab_set()

        top_bar = tk.Frame(uwin, bg=self.COLOR_TOPBAR, pady=10, padx=16)
        top_bar.pack(fill="x")
        hdr_title = f"✏️ تعديل حساب: {user_obj['username']}" if is_edit else "➕ إضافة مستخدم جديد وتخصيص الصلاحيات"
        tk.Label(top_bar, text=fix_bidi(hdr_title), font=("Segoe UI", 13, "bold"), bg=self.COLOR_TOPBAR, fg="#38bdf8").pack(side="right")

        bot_bar = tk.Frame(uwin, bg=self.COLOR_TOPBAR, pady=10, padx=16)
        bot_bar.pack(side="bottom", fill="x")

        scroll_body = self._create_scrollable_frame(uwin, bg_color=self.COLOR_BG, pad_x=16, pad_y=10)

        info_card = tk.LabelFrame(scroll_body, text="👤 البيانات الأساسية للحساب", bg=self.COLOR_CARD, fg=self.COLOR_BLUE, font=("Segoe UI", 11, "bold"), padx=14, pady=10)
        info_card.pack(fill="x", pady=6)

        for c_i in range(4):
            info_card.grid_columnconfigure(c_i, weight=1 if c_i in (0, 2) else 0)

        tk.Label(info_card, text="اسم الدخول (Username):", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=0, column=3, sticky="e", padx=6, pady=6)
        ent_username = tk.Entry(info_card, font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="right")
        ent_username.grid(row=0, column=2, sticky="ew", padx=6, pady=6, ipady=3)

        tk.Label(info_card, text="الاسم بالكامل:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky="e", padx=6, pady=6)
        ent_fullname = tk.Entry(info_card, font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="right")
        ent_fullname.grid(row=0, column=0, sticky="ew", padx=6, pady=6, ipady=3)

        pw_lbl_txt = "كلمة المرور الجديدة (اتركها فارغة لعدم التغيير):" if is_edit else "كلمة المرور:"
        tk.Label(info_card, text=pw_lbl_txt, bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=1, column=3, sticky="e", padx=6, pady=6)
        ent_password = tk.Entry(info_card, font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="center", show="●")
        ent_password.grid(row=1, column=2, sticky="ew", padx=6, pady=6, ipady=3)

        active_var = tk.BooleanVar(value=bool(user_obj.get('is_active', True)) if is_edit else True)
        chk_active = tk.Checkbutton(
            info_card, text="الحساب نشط ويسمح له بالدخول", variable=active_var,
            bg=self.COLOR_CARD, fg=self.COLOR_ACCENT, selectcolor=self.COLOR_ENTRY_BG,
            font=("Segoe UI", 10, "bold")
        )
        chk_active.grid(row=1, column=0, columnspan=2, sticky="e", padx=6, pady=6)

        if is_edit:
            ent_username.insert(0, user_obj['username'])
            if str(user_obj['username']).lower() == 'admin':
                ent_username.configure(state="disabled")
                chk_active.configure(state="disabled")
            ent_fullname.insert(0, user_obj.get('full_name') or '')

        role_var = tk.StringVar(value=str(user_obj.get('role') or 'custom') if is_edit else 'sales')
        perm_vars = {k: tk.BooleanVar(value=False) for k in PERMISSIONS_DICT}

        if is_edit:
            existing_p = user_obj.get('permissions') or {}
            if isinstance(existing_p, str):
                try:
                    existing_p = json.loads(existing_p)
                except Exception:
                    existing_p = {}
            is_adm = (str(user_obj['username']).lower() == 'admin' or str(user_obj.get('role')).lower() == 'admin')
            for k in PERMISSIONS_DICT:
                perm_vars[k].set(True if is_adm else bool(existing_p.get(k, False)))

        presets_card = tk.LabelFrame(scroll_body, text="⚡ قوالب الصلاحيات الجاهزة", bg=self.COLOR_CARD, fg=self.COLOR_PURPLE, font=("Segoe UI", 11, "bold"), padx=14, pady=8)
        presets_card.pack(fill="x", pady=6)

        def apply_role_preset(preset_name):
            role_var.set(preset_name)
            for k in perm_vars:
                perm_vars[k].set(False)

            if preset_name == "admin":
                for k in perm_vars:
                    perm_vars[k].set(True)
            elif preset_name == "sales":
                for k in [
                    'can_view_inventory', 'can_view_sales_screen', 'can_execute_sale',
                    'can_print_sale_invoice', 'can_view_customer_debts',
                    'can_collect_customer_debt', 'can_print_customer_debt'
                ]:
                    perm_vars[k].set(True)
            elif preset_name == "inventory":
                for k in [
                    'can_view_inventory', 'can_edit_inventory', 'can_view_buy_price',
                    'can_manage_inventory', 'can_buy_devices', 'can_add_supplier_in_buy',
                    'can_view_supplier_debts', 'can_manage_suppliers'
                ]:
                    perm_vars[k].set(True)
            elif preset_name == "accountant":
                for k in [
                    'can_view_inventory', 'can_view_buy_price', 'can_view_customer_debts',
                    'can_collect_customer_debt', 'can_print_customer_debt',
                    'can_view_supplier_debts', 'can_pay_supplier_debt', 'can_print_supplier_invoice',
                    'can_view_reports', 'can_view_liquidity', 'can_add_liquidity',
                    'can_view_liquidity_log', 'can_view_profits', 'can_view_sales_report',
                    'can_edit_transaction_date'
                ]:
                    perm_vars[k].set(True)

        preset_btns = [
            ("👑 مدير كامل الصلاحيات", "admin", self.COLOR_ACCENT),
            ("🛒 مبيعات وكاشير", "sales", self.COLOR_BLUE),
            ("📦 أمين مخزن ومشتريات", "inventory", self.COLOR_PURPLE),
            ("📊 محاسب مالي", "accountant", self.COLOR_TEAL),
            ("🧹 مسح الكل", "custom", self.COLOR_DANGER),
        ]
        for b_txt, p_key, b_col in preset_btns:
            tk.Button(
                presets_card, text=b_txt, command=lambda pk=p_key: apply_role_preset(pk),
                bg=b_col, fg="white", font=("Segoe UI", 9, "bold"),
                padx=12, pady=4, relief="flat", cursor="hand2"
            ).pack(side="right", padx=4, pady=2)

        tk.Button(
            presets_card, text="📖 شرح وتفاصيل كل صلاحية", command=self.open_permissions_guide_dialog,
            bg="#6366f1", fg="white", font=("Segoe UI", 9, "bold"),
            padx=12, pady=4, relief="flat", cursor="hand2"
        ).pack(side="left", padx=4, pady=2)

        if not is_edit:
            apply_role_preset("sales")

        perms_container = tk.LabelFrame(scroll_body, text="🔐 تخصيص الصلاحيات التفصيلية", bg=self.COLOR_CARD, fg=self.COLOR_ACCENT, font=("Segoe UI", 11, "bold"), padx=14, pady=10)
        perms_container.pack(fill="x", pady=6)

        for grp_title, grp_items in PERMISSION_GROUPS:
            g_frame = tk.LabelFrame(perms_container, text=grp_title, bg=self.COLOR_CARD, fg=self.COLOR_BLUE, font=("Segoe UI", 10, "bold"), padx=10, pady=6)
            g_frame.pack(fill="x", pady=5)
            g_frame.grid_columnconfigure(0, weight=1)
            g_frame.grid_columnconfigure(1, weight=1)

            grp_keys = [pk for pk, _ in grp_items]
            grp_bar = tk.Frame(g_frame, bg=self.COLOR_CARD)
            grp_bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))

            def make_toggle_actions(keys):
                def select_all_g():
                    for k in keys:
                        perm_vars[k].set(True)
                def deselect_all_g():
                    for k in keys:
                        perm_vars[k].set(False)
                return select_all_g, deselect_all_g

            s_all_func, ds_all_func = make_toggle_actions(grp_keys)
            tk.Button(grp_bar, text="✓ تحديد كل القسم", font=("Segoe UI", 8, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_BLUE, relief="flat", cursor="hand2", padx=6, pady=1, command=s_all_func).pack(side="right", padx=3)
            tk.Button(grp_bar, text="✗ إلغاء القسم", font=("Segoe UI", 8, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_MUTED, relief="flat", cursor="hand2", padx=6, pady=1, command=ds_all_func).pack(side="right", padx=3)

            for idx_item, (p_key, p_label) in enumerate(grp_items):
                r_i = (idx_item // 2) + 1
                c_i = 1 - (idx_item % 2)
                cb = tk.Checkbutton(
                    g_frame, text=p_label, variable=perm_vars[p_key],
                    bg=self.COLOR_CARD, fg=self.COLOR_TEXT, selectcolor=self.COLOR_ENTRY_BG,
                    activebackground=self.COLOR_CARD, activeforeground=self.COLOR_ACCENT,
                    font=("Segoe UI", 10, "bold"), anchor="e"
                )
                cb.grid(row=r_i, column=c_i, sticky="e", padx=10, pady=3)

        def save_user_action():
            uname = ent_username.get().strip()
            fname = ent_fullname.get().strip() or uname
            pw = ent_password.get().strip()

            if not uname:
                messagebox.showwarning("تنبيه", "يرجى إدخال اسم الدخول!", parent=uwin)
                return
            if not is_edit and not pw:
                messagebox.showwarning("تنبيه", "يرجى إدخال كلمة المرور للمستخدم الجديد!", parent=uwin)
                return

            collected_perms = {k: bool(v.get()) for k, v in perm_vars.items()}
            if collected_perms.get('can_edit_inventory') or collected_perms.get('can_buy_devices'):
                collected_perms['can_manage_inventory'] = True

            try:
                if is_edit:
                    self.db.update_user(
                        user_id=user_obj['id'],
                        username=uname,
                        full_name=fname,
                        permissions=collected_perms,
                        is_active=active_var.get(),
                        new_password=pw if pw else None,
                        role=role_var.get(),
                        admin_user_id=self.current_user_id
                    )
                    if self.current_user and self.current_user['id'] == user_obj['id']:
                        self.current_user['full_name'] = fname
                        self.current_user['permissions'] = collected_perms
                        self.current_user['role'] = role_var.get()
                    messagebox.showinfo("تم الحفظ", "تم تحديث بيانات وصلاحيات المستخدم بنجاح!", parent=uwin)
                else:
                    self.db.create_user(
                        username=uname,
                        password=pw,
                        full_name=fname,
                        permissions=collected_perms,
                        role=role_var.get(),
                        admin_user_id=self.current_user_id
                    )
                    messagebox.showinfo("تم الإضافة", f"تم إنشاء حساب ({uname}) بنجاح!", parent=uwin)

                uwin.destroy()
                if on_saved_callback:
                    on_saved_callback()
                elif self.current_view_func == self.view_user_management:
                    self.view_user_management()
            except Exception as ex:
                messagebox.showerror("خطأ", str(ex), parent=uwin)

        self._bind_enter_chain([ent_username, ent_fullname, ent_password], final_callback=save_user_action)

        tk.Button(
            bot_bar, text="💾 حفظ بيانات المستخدم", command=save_user_action,
            bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 11, "bold"),
            padx=22, pady=5, relief="flat", cursor="hand2"
        ).pack(side="right", padx=6)

        tk.Button(
            bot_bar, text="إغلاق", command=uwin.destroy,
            bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 10, "bold"),
            padx=18, pady=5, relief="flat", cursor="hand2"
        ).pack(side="left", padx=6)

    def view_inventory(self):
        if not self.has_permission('can_view_inventory'):
            messagebox.showerror("صلاحيات غير كافية", "عفواً، لا تملك صلاحية عرض المخزون!")
            return

        self.current_view_func = self.view_inventory
        self.build_main_ui(keep_view=True)
        self.clear_content()

        top_hdr = tk.Frame(self.content_frame, bg=self.COLOR_BG, padx=18, pady=8)
        top_hdr.pack(fill="x")

        tk.Label(
            top_hdr, text="📦 المخزون والأجهزة",
            font=("Segoe UI", 16, "bold"), bg=self.COLOR_BG, fg=self.COLOR_BLUE
        ).pack(side="right")

        stats_frame = tk.Frame(top_hdr, bg=self.COLOR_BG)
        stats_frame.pack(side="left")

        lbl_avail_count = tk.Label(stats_frame, text="المتاح: 0", bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"), padx=12, pady=4)
        lbl_avail_count.pack(side="right", padx=4)

        lbl_sold_count = tk.Label(stats_frame, text="المباع: 0", bg=self.COLOR_WARN, fg="#111111", font=("Segoe UI", 10, "bold"), padx=12, pady=4)
        lbl_sold_count.pack(side="right", padx=4)

        filter_bar = tk.Frame(self.content_frame, bg=self.COLOR_CARD, padx=14, pady=10)
        filter_bar.pack(fill="x", padx=18, pady=(0, 8))

        tk.Label(filter_bar, text="🔍 البحث بـ:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right", padx=(4, 2))
        inv_search_type_cb = ttk.Combobox(filter_bar, values=["الكل (شامل)", "سيريال IMEI", "الموديل", "كود الجهاز #ID", "المورد"], state="readonly", width=13, font=("Segoe UI", 10, "bold"), justify="right")
        inv_search_type_cb.current(0)
        inv_search_type_cb.pack(side="right", padx=(0, 6), ipady=2)

        search_entry = tk.Entry(filter_bar, font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="right", width=20)
        search_entry.pack(side="right", padx=6, ipady=3)

        tk.Label(filter_bar, text="الماركة:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right", padx=(10, 4))
        brand_cb = ttk.Combobox(filter_bar, values=["الكل"] + self.BRAND_LIST, state="readonly", width=12, font=("Segoe UI", 10, "bold"), justify="right")
        brand_cb.current(0)
        brand_cb.pack(side="right", padx=4, ipady=2)

        tk.Label(filter_bar, text="الحالة:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right", padx=(10, 4))
        status_cb = ttk.Combobox(filter_bar, values=["المتاح بالمخزون", "المباع", "الكل"], state="readonly", width=14, font=("Segoe UI", 10, "bold"), justify="right")
        status_cb.current(0)
        status_cb.pack(side="right", padx=4, ipady=2)

        actions_bar = tk.Frame(self.content_frame, bg=self.COLOR_BG, padx=18, pady=4)
        actions_bar.pack(fill="x")

        tk.Button(
            actions_bar, text="🔍 بيانات الجهاز", command=lambda: open_selected_device_details(),
            bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold"),
            padx=14, pady=5, relief="flat", cursor="hand2"
        ).pack(side="right", padx=4)

        if self.has_permission('can_edit_inventory'):
            tk.Button(
                actions_bar, text="✏️ تعديل الجهاز", command=lambda: edit_selected_device(),
                bg=self.COLOR_INDIGO, fg="white", font=("Segoe UI", 10, "bold"),
                padx=14, pady=5, relief="flat", cursor="hand2"
            ).pack(side="right", padx=4)

        if self.has_permission('can_process_returns'):
            tk.Button(
                actions_bar, text="🔄 استرجاع للمخزون", command=lambda: return_selected_device(),
                bg=self.COLOR_WARN, fg="#111111", font=("Segoe UI", 10, "bold"),
                padx=14, pady=5, relief="flat", cursor="hand2"
            ).pack(side="right", padx=4)

        if self.has_permission('can_delete_inventory'):
            tk.Button(
                actions_bar, text="🗑️ حذف الجهاز", command=lambda: delete_selected_device(),
                bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 10, "bold"),
                padx=14, pady=5, relief="flat", cursor="hand2"
            ).pack(side="right", padx=4)

        tk.Button(
            actions_bar, text="🔄 تحديث", command=lambda: refresh_inventory_table(),
            bg=self.COLOR_TEAL, fg="white", font=("Segoe UI", 10, "bold"),
            padx=14, pady=5, relief="flat", cursor="hand2"
        ).pack(side="left", padx=4)

        table_container = tk.Frame(self.content_frame, bg=self.COLOR_CARD, padx=12, pady=10)
        table_container.pack(fill="both", expand=True, padx=18, pady=(4, 14))

        cols = ("حالة التوفر", "سعر البيع", "الحالة", "المساحة", "الموديل", "الماركة", "كود الجهاز")
        tree = ttk.Treeview(table_container, columns=cols, show="headings")
        self.configure_tree_row_colors(tree)

        widths = {
            "حالة التوفر": 115, "سعر البيع": 140, "الحالة": 125,
            "المساحة": 110, "الموديل": 170, "الماركة": 130, "كود الجهاز": 105
        }
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, anchor="center", width=widths.get(c, 120))

        vsb = ttk.Scrollbar(table_container, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(table_container, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="left", fill="y")
        hsb.pack(side="bottom", fill="x")
        tree.pack(side="right", fill="both", expand=True)

        self.bind_treeview_double_click(tree, target_column_name="كود الجهاز")

        devices_map = {}

        def refresh_inventory_table(event=None):
            tree.delete(*tree.get_children())
            devices_map.clear()

            all_devs = self.db.get_inventory(include_sold=True)
            avail_c = sum(1 for d in all_devs if not d.get('is_sold'))
            sold_c = sum(1 for d in all_devs if d.get('is_sold'))
            lbl_avail_count.config(text=f"المتاح: {avail_c}")
            lbl_sold_count.config(text=f"المباع: {sold_c}")

            q = search_entry.get().strip().lower()
            b_filter = brand_cb.get()
            st_filter = status_cb.get()

            for d in all_devs:
                is_sold = bool(d.get('is_sold'))
                if st_filter == "المتاح بالمخزون" and is_sold:
                    continue
                if st_filter == "المباع" and not is_sold:
                    continue
                if b_filter != "الكل" and str(d.get('category') or '').lower() != b_filter.lower():
                    continue
                if q:
                    stype = inv_search_type_cb.get()
                    if "سيريال" in stype:
                        if q not in str(d.get('imei_serial') or '').lower():
                            continue
                    elif "الموديل" in stype:
                        if q not in f"{d.get('category') or ''} {d.get('model') or ''}".lower():
                            continue
                    elif "كود" in stype or "#ID" in stype:
                        clean_q_id = clean_id_val(q)
                        if clean_q_id is None or d['id'] != clean_q_id:
                            continue
                    elif "المورد" in stype:
                        if q not in str(d.get('supplier_name') or '').lower():
                            continue
                    else:
                        searchable = f"{d.get('id')} {d.get('category')} {d.get('model')} {d.get('imei_serial')} {d.get('supplier_name') or ''}".lower()
                        if q not in searchable:
                            continue

                did = d['id']
                devices_map[did] = d
                sp_val = d.get('initial_selling_price') or d.get('selling_price') or d.get('buy_price') or 0
                st_txt = "مباع 🔴" if is_sold else "متاح 🟢"
                cond_txt = d.get('device_condition') or "مستعمل"
                raw_st = str(d.get('storage') or "-").replace("GB", "").strip()
                storage_txt = f"{raw_st} GB" if (raw_st and raw_st != "-") else "-"
                row_tag = 'evenrow' if len(devices_map) % 2 == 0 else 'oddrow'

                tree.insert("", "end", iid=str(did), tags=(row_tag,), values=(
                    fix_bidi(st_txt),
                    fmt_curr(sp_val),
                    fix_bidi(cond_txt),
                    fix_bidi(storage_txt),
                    fix_bidi(d.get('model') or "-"),
                    fix_bidi(d.get('category') or "-"),
                    f"#{did}"
                ))

            self.after(50, lambda: tree.xview_moveto(1.0))

        def get_selected_dev():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("تنبيه", "يرجى تحديد جهاز من الجدول أولاً!")
                return None
            did = clean_id_val(sel[0])
            return devices_map.get(did)

        def open_selected_device_details():
            d = get_selected_dev()
            if d:
                self.show_device_details_modal(d['id'])

        def edit_selected_device():
            d = get_selected_dev()
            if not d:
                return
            self.open_edit_device_modal(d, on_success_callback=refresh_inventory_table)

        def return_selected_device():
            d = get_selected_dev()
            if not d:
                return
            if not d.get('is_sold'):
                messagebox.showinfo("تنبيه", "هذا الجهاز متاح بالفعل في المخزون وليس مباعاً!")
                return
            if messagebox.askyesno("تأكيد الاسترجاع", f"هل تريد استرجاع الجهاز #{d['id']} ({d['category']} {d['model']}) وإعادته للمخزون؟"):
                try:
                    self.db.process_return(d['id'], self.current_user_id)
                    messagebox.showinfo("تم الاسترجاع", "تم إرجاع الجهاز للمخزون بنجاح!")
                    refresh_inventory_table()
                except Exception as ex:
                    messagebox.showerror("خطأ", str(ex))

        def delete_selected_device():
            d = get_selected_dev()
            if not d:
                return
            if d.get('is_sold'):
                messagebox.showwarning("تنبيه مالي", "لا يمكن حذف جهاز مباع مباشرة! يرجى عمل (استرجاع للمخزون) أولاً لضبط الحسابات والسيولة.")
                return

            inv_stat = self.db.get_device_supplier_invoice_status(d['id'])
            is_overpaid = inv_stat and inv_stat.get('is_paid') and inv_stat.get('overpaid', 0) > 0

            if is_overpaid:
                excess_amt = inv_stat['overpaid']
                supp_name = inv_stat.get('supplier_name') or d.get('supplier_name') or 'المورد'

                choice_win = tk.Toplevel(self)
                choice_win.title("تسوية مستحقات حذف الجهاز")
                choice_win.geometry("540x360")
                choice_win.configure(bg=self.COLOR_CARD)
                choice_win.resizable(False, False)
                choice_win.grab_set()

                top_c = tk.Frame(choice_win, bg=self.COLOR_TOPBAR, pady=10, padx=14)
                top_c.pack(fill="x")
                tk.Label(
                    top_c, text=fix_bidi(f"⚠️ تسوية حذف الجهاز #{d['id']} - مسدد ثمنه"),
                    font=("Segoe UI", 12, "bold"), bg=self.COLOR_TOPBAR, fg=self.COLOR_WARN
                ).pack(side="right")

                body_c = tk.Frame(choice_win, bg=self.COLOR_CARD, padx=16, pady=12)
                body_c.pack(fill="both", expand=True)

                msg_t = (
                    f"الجهاز #{d['id']} ({d['category']} {d['model']}) مسدد ثمنه في فاتورة {supp_name}!\n\n"
                    f"المبلغ المسدد الزائد المستحق لنا: {fmt_curr(excess_amt)}\n\n"
                    "يرجى تحديد طريقة التسوية المالية المناسبة لنظامكم:"
                )
                tk.Label(body_c, text=fix_bidi(msg_t), font=("Segoe UI", 10, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_TEXT, justify="right", wraplength=500).pack(pady=8)

                def do_cash_refund():
                    try:
                        self.db.delete_device(d['id'], self.current_user_id, refund_mode='CASH_REFUND')
                        choice_win.destroy()
                        messagebox.showinfo("تم الحذف والاسترداد", f"تم حذف الجهاز وإيداع مبلغ {fmt_curr(excess_amt)} كاسترداد نقدي في السيولة بالخزينة!")
                        refresh_inventory_table()
                    except Exception as ex:
                        messagebox.showerror("خطأ", str(ex), parent=choice_win)

                def do_supplier_credit():
                    try:
                        self.db.delete_device(d['id'], self.current_user_id, refund_mode='SUPPLIER_CREDIT')
                        choice_win.destroy()
                        messagebox.showinfo("تم الحذف وتسجيل الرصيد", f"تم حذف الجهاز وتسجيل مبلغ {fmt_curr(excess_amt)} كرصيد دائن مستحق لنا لدى المورد في الفاتورة!")
                        refresh_inventory_table()
                    except Exception as ex:
                        messagebox.showerror("خطأ", str(ex), parent=choice_win)

                btn_frame = tk.Frame(body_c, bg=self.COLOR_CARD, pady=10)
                btn_frame.pack(fill="x")

                tk.Button(
                    btn_frame, text="💵 استرداد نقدي فوري للخزينة", command=do_cash_refund,
                    bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"),
                    padx=14, pady=8, relief="flat", cursor="hand2"
                ).pack(fill="x", pady=4)

                tk.Button(
                    btn_frame, text="📝 تسجيل رصيد دائن لنا لدى المورد", command=do_supplier_credit,
                    bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold"),
                    padx=14, pady=8, relief="flat", cursor="hand2"
                ).pack(fill="x", pady=4)

                tk.Button(
                    btn_frame, text="❌ إلغاء العملية", command=choice_win.destroy,
                    bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 9, "bold"),
                    padx=12, pady=4, relief="flat", cursor="hand2"
                ).pack(fill="x", pady=(8, 0))

            else:
                buy_p = float(d.get('buy_price') or 0)
                msg = (
                    f"هل أنت متأكد من حذف الجهاز #{d['id']} ({d['category']} {d['model']})؟\n\n"
                    f"ملاحظة مالية: سيتم خصم تكلفة الجهاز ({fmt_curr(buy_p)}) بالكامل من المبلغ المتبقي المطلوب للمورد (المديونية)."
                )
                if messagebox.askyesno("تأكيد حذف الجهاز", msg):
                    try:
                        self.db.delete_device(d['id'], self.current_user_id, refund_mode='FROM_DEBT_FIRST')
                        messagebox.showinfo("تم الحذف", "تم حذف الجهاز وخصم تكلفته من مديونية المورد بنجاح!")
                        refresh_inventory_table()
                    except Exception as ex:
                        messagebox.showerror("خطأ", str(ex))

        search_entry.bind("<KeyRelease>", refresh_inventory_table)
        inv_search_type_cb.bind("<<ComboboxSelected>>", refresh_inventory_table)
        brand_cb.bind("<<ComboboxSelected>>", refresh_inventory_table)
        status_cb.bind("<<ComboboxSelected>>", refresh_inventory_table)
        refresh_inventory_table()

    def open_edit_device_modal(self, dev_obj, on_success_callback=None):
        if not self.has_permission('can_edit_inventory'):
            messagebox.showerror("صلاحيات غير كافية", "لا تملك صلاحية تعديل بيانات الأجهزة!")
            return

        ewin = tk.Toplevel(self)
        ewin.title(f"تعديل بيانات الجهاز #{dev_obj['id']}")
        ewin.geometry("720x680")
        ewin.configure(bg=self.COLOR_BG)
        ewin.grab_set()

        top_bar = tk.Frame(ewin, bg=self.COLOR_TOPBAR, pady=10, padx=16)
        top_bar.pack(fill="x")
        tk.Label(
            top_bar, text=fix_bidi(f"✏️ تعديل بيانات الجهاز #{dev_obj['id']}"),
            font=("Segoe UI", 13, "bold"), bg=self.COLOR_TOPBAR, fg="#38bdf8"
        ).pack(side="right")

        bot_bar = tk.Frame(ewin, bg=self.COLOR_TOPBAR, pady=10, padx=16)
        bot_bar.pack(side="bottom", fill="x")

        scroll_body = self._create_scrollable_frame(ewin, bg_color=self.COLOR_BG, pad_x=16, pad_y=10)

        form_card = tk.LabelFrame(scroll_body, text="📱 المواصفات والبيانات الكاملة للجهاز", bg=self.COLOR_CARD, fg=self.COLOR_BLUE, font=("Segoe UI", 11, "bold"), padx=16, pady=12)
        form_card.pack(fill="x", pady=6)
        form_card.grid_columnconfigure(0, weight=1)

        def make_row(r_idx, label_txt):
            tk.Label(form_card, text=label_txt, bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=r_idx, column=1, sticky="e", padx=8, pady=5)

        make_row(0, "الماركة:")
        cb_cat = ttk.Combobox(form_card, values=self.BRAND_LIST, font=("Segoe UI", 11, "bold"), justify="right")
        cb_cat.set(dev_obj.get('category') or '')
        cb_cat.grid(row=0, column=0, sticky="ew", padx=8, pady=5, ipady=3)

        make_row(1, "الموديل:")
        ent_model = tk.Entry(form_card, font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="right")
        ent_model.insert(0, dev_obj.get('model') or '')
        ent_model.grid(row=1, column=0, sticky="ew", padx=8, pady=5, ipady=3)

        make_row(2, "المساحة التخزينية:")
        cb_storage = ttk.Combobox(form_card, values=["", "32", "64", "128", "256", "512", "1TB"], font=("Segoe UI", 11, "bold"), justify="right")
        cb_storage.set(str(dev_obj.get('storage') or '').replace("GB", "").strip())
        cb_storage.grid(row=2, column=0, sticky="ew", padx=8, pady=5, ipady=3)

        make_row(3, "الرامات (RAM):")
        cb_ram = ttk.Combobox(form_card, values=["", "2", "3", "4", "6", "8", "12", "16"], font=("Segoe UI", 11, "bold"), justify="right")
        cb_ram.set(str(dev_obj.get('ram') or '').replace("GB", "").strip())
        cb_ram.grid(row=3, column=0, sticky="ew", padx=8, pady=5, ipady=3)

        make_row(4, "اللون:")
        color_suggestions = ["أسود", "فضي", "أبيض", "رمادي", "تيتانيوم طبيعي", "تيتانيوم أسود", "تيتانيوم صحراوي", "أزرق", "ذهبي", "أخضر", "كحلي", "أحمر", "وردي"]
        cb_color = ttk.Combobox(form_card, values=color_suggestions, font=("Segoe UI", 11, "bold"), justify="right")
        cur_col = dev_obj.get('color') or "أسود"
        if not cur_col or cur_col == "بدون":
            cur_col = "أسود"
        cb_color.set(cur_col)
        cb_color.grid(row=4, column=0, sticky="ew", padx=8, pady=5, ipady=3)

        make_row(5, "نسبة البطارية (%):")
        ent_bat = tk.Entry(form_card, font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="center")
        if dev_obj.get('battery_health'):
            ent_bat.insert(0, str(dev_obj['battery_health']))
        ent_bat.grid(row=5, column=0, sticky="ew", padx=8, pady=5, ipady=3)

        make_row(6, "حالة الجهاز:")
        cb_cond = ttk.Combobox(form_card, values=["جديد", "كسر زيرو", "مستعمل"], state="readonly", font=("Segoe UI", 11, "bold"), justify="right")
        cb_cond.set(dev_obj.get('device_condition') or "مستعمل")
        cb_cond.grid(row=6, column=0, sticky="ew", padx=8, pady=5, ipady=3)

        make_row(7, "العلبة والضريبة:")
        box_and_tax_row = tk.Frame(form_card, bg=self.COLOR_CARD)
        box_and_tax_row.grid(row=7, column=0, sticky="ew", padx=8, pady=5)

        box_var = tk.BooleanVar(value=bool(dev_obj.get('has_box')))
        tk.Checkbutton(
            box_and_tax_row, text="الجهاز معه علبة 📦", variable=box_var,
            bg=self.COLOR_CARD, fg=self.COLOR_ACCENT, selectcolor=self.COLOR_ENTRY_BG,
            font=("Segoe UI", 10, "bold")
        ).pack(side="right", padx=(0, 16))

        tax_var = tk.BooleanVar(value=bool(dev_obj.get('has_tax')))
        tk.Checkbutton(
            box_and_tax_row, text="خاضع لضريبة 🏛️", variable=tax_var,
            bg=self.COLOR_CARD, fg=self.COLOR_BLUE, selectcolor=self.COLOR_ENTRY_BG,
            font=("Segoe UI", 10, "bold")
        ).pack(side="right", padx=8)

        make_row(8, "الملحقات المرفقة:")
        ent_acc = tk.Entry(form_card, font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="right")
        ent_acc.insert(0, dev_obj.get('accessories') or '')
        ent_acc.grid(row=8, column=0, sticky="ew", padx=8, pady=5, ipady=3)

        make_row(9, "السيريال (IMEI):")
        ent_imei = tk.Entry(form_card, font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="center")
        ent_imei.insert(0, dev_obj.get('imei_serial') or '')
        ent_imei.grid(row=9, column=0, sticky="ew", padx=8, pady=5, ipady=3)

        can_see_buy = self.has_permission('can_view_buy_price')
        ent_buy_price = tk.Entry(form_card, validate="key", validatecommand=self.vcmd_num, font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_ACCENT, insertbackground=self.COLOR_TEXT, justify="center")
        ent_buy_price.insert(0, fmt_num(dev_obj.get('buy_price') or 0))
        if can_see_buy:
            make_row(10, "سعر الشراء (التكلفة):")
            ent_buy_price.grid(row=10, column=0, sticky="ew", padx=8, pady=5, ipady=3)

        make_row(11, "سعر البيع المبدئي *:")
        ent_init_selling_price = tk.Entry(form_card, validate="key", validatecommand=self.vcmd_num, font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="center")
        cur_init_sp = dev_obj.get('initial_selling_price') or dev_obj.get('selling_price') or dev_obj.get('buy_price') or 0
        ent_init_selling_price.insert(0, fmt_num(cur_init_sp))
        ent_init_selling_price.grid(row=11, column=0, sticky="ew", padx=8, pady=5, ipady=3)

        make_row(12, "المورد:")
        supp_edit_row = tk.Frame(form_card, bg=self.COLOR_CARD)
        supp_edit_row.grid(row=12, column=0, sticky="ew", padx=8, pady=5)
        cb_supp = ttk.Combobox(supp_edit_row, state="readonly", font=("Segoe UI", 11, "bold"), justify="right")
        cb_supp.pack(side="right", fill="x", expand=True, ipady=3)

        edit_supp_map = {}
        s_list = self.db.get_suppliers(active_only=False)
        supp_display_vals = []
        cur_supp_idx = 0
        target_s_id = dev_obj.get('supplier_id')
        for idx_s, s in enumerate(s_list):
            lbl = f"{s['name']} ({s.get('supplier_type', 'تاجر')})"
            edit_supp_map[lbl] = s['id']
            supp_display_vals.append(lbl)
            if target_s_id and s['id'] == target_s_id:
                cur_supp_idx = idx_s

        cb_supp['values'] = supp_display_vals
        if supp_display_vals:
            cb_supp.current(cur_supp_idx)

        make_row(13, "تاريخ الشراء / الإضافة:")
        date_edit_f = tk.Frame(form_card, bg=self.COLOR_CARD)
        date_edit_f.grid(row=13, column=0, sticky="ew", padx=8, pady=5)

        can_edit_date = self.has_permission('can_edit_operation_dates') or self.has_permission('can_edit_transaction_date')
        ent_buy_date = tk.Entry(date_edit_f, font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="center", state="normal" if can_edit_date else "disabled")
        init_date_str = str(dev_obj.get('buy_date_formatted') or dev_obj.get('buy_date') or datetime.now().strftime("%Y-%m-%d %H:%M")).split(".")[0]
        ent_buy_date.insert(0, init_date_str)
        ent_buy_date.pack(side="right", fill="x", expand=True, ipady=3)

        if can_edit_date:
            def pick_edit_date():
                def on_dt_sel():
                    cur = ent_buy_date.get().strip()
                    if len(cur) == 10:
                        ent_buy_date.delete(0, tk.END)
                        ent_buy_date.insert(0, f"{cur} 12:00")
                self.open_date_picker(ent_buy_date, on_select_callback=on_dt_sel, allow_future=False)

            tk.Button(date_edit_f, text="📅", command=pick_edit_date, bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold"), padx=8, pady=2, relief="flat", cursor="hand2").pack(side="left", padx=2)
            def set_buy_today():
                ent_buy_date.delete(0, tk.END)
                ent_buy_date.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M"))
            tk.Button(date_edit_f, text="اليوم", command=set_buy_today, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 8, "bold"), padx=6, pady=2, relief="flat", cursor="hand2").pack(side="left", padx=2)

        ent_sell_date = None
        current_row_idx = 14
        if dev_obj.get('is_sold'):
            make_row(current_row_idx, "تاريخ البيع:")
            date_sell_f = tk.Frame(form_card, bg=self.COLOR_CARD)
            date_sell_f.grid(row=current_row_idx, column=0, sticky="ew", padx=8, pady=5)

            ent_sell_date = tk.Entry(date_sell_f, font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="center", state="normal" if can_edit_date else "disabled")
            init_sdate_str = str(dev_obj.get('sell_date_formatted') or dev_obj.get('sell_date') or datetime.now().strftime("%Y-%m-%d %H:%M")).split(".")[0]
            ent_sell_date.insert(0, init_sdate_str)
            ent_sell_date.pack(side="right", fill="x", expand=True, ipady=3)

            if can_edit_date:
                def pick_sell_date():
                    def on_sdt_sel():
                        cur = ent_sell_date.get().strip()
                        if len(cur) == 10:
                            ent_sell_date.delete(0, tk.END)
                            ent_sell_date.insert(0, f"{cur} 12:00")
                    self.open_date_picker(ent_sell_date, on_select_callback=on_sdt_sel, allow_future=False)

                tk.Button(date_sell_f, text="📅", command=pick_sell_date, bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold"), padx=8, pady=2, relief="flat", cursor="hand2").pack(side="left", padx=2)
                def set_sell_today():
                    ent_sell_date.delete(0, tk.END)
                    ent_sell_date.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M"))
                tk.Button(date_sell_f, text="اليوم", command=set_sell_today, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 8, "bold"), padx=6, pady=2, relief="flat", cursor="hand2").pack(side="left", padx=2)

            current_row_idx += 1

        make_row(current_row_idx, "الملاحظات وشارة التوفر:")
        notes_f = tk.Frame(form_card, bg=self.COLOR_CARD)
        notes_f.grid(row=current_row_idx, column=0, sticky="ew", padx=8, pady=5)
        ent_notes = tk.Entry(notes_f, font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="right")
        ent_notes.insert(0, dev_obj.get('notes') or '')
        ent_notes.pack(side="right", fill="x", expand=True, ipady=3)

        st_label_txt = "🔴 مباع" if dev_obj.get('is_sold') else "🟢 متاح بالمخزون"
        tk.Label(notes_f, text=st_label_txt, font=("Segoe UI", 10, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_WARN if dev_obj.get('is_sold') else self.COLOR_ACCENT, padx=10, pady=3).pack(side="left", padx=4)

        self.attach_autocomplete(cb_cat, lambda: self.BRAND_LIST, next_focus_widget=ent_model)
        self.attach_autocomplete(ent_model, lambda: self.get_model_suggestions_for_brand(cb_cat.get()), next_focus_widget=cb_storage)

        def save_edits():
            cat_val = cb_cat.get().strip()
            mod_val = ent_model.get().strip()
            imei_val = ent_imei.get().strip()
            if not cat_val or not mod_val or not imei_val:
                messagebox.showwarning("تنبيه", "الماركة والموديل والسيريال حقول أساسية لا يمكن تركها فارغة!", parent=ewin)
                return

            try:
                bp_val = float(ent_buy_price.get().strip() or 0) if can_see_buy else float(dev_obj.get('buy_price') or 0)
            except ValueError:
                bp_val = float(dev_obj.get('buy_price') or 0)

            try:
                sp_edit_val = float(ent_init_selling_price.get().strip() or 0)
            except ValueError:
                sp_edit_val = float(dev_obj.get('initial_selling_price') or 0)

            if sp_edit_val < bp_val:
                messagebox.showwarning(
                    "⚠️ تنبيه أمان مالي",
                    f"لا يمكن أن يكون سعر البيع المبدئي ({fmt_curr(sp_edit_val)}) أقل من سعر الشراء ({fmt_curr(bp_val)})!\n"
                    "يرجى تعديل سعر البيع المبدئي ليكون مساوياً أو أكبر من سعر التكلفة.",
                    parent=ewin
                )
                ent_init_selling_price.focus_set()
                return

            confirm = messagebox.askyesno(
                "تأكيد حفظ التعديلات",
                f"هل أنت متأكد من حفظ التعديلات الجديدة على الجهاز #{dev_obj['id']}؟\n\n"
                f"• الجهاز: {cat_val} {mod_val}\n"
                f"• السيريال: {imei_val}\n"
                f"• سعر البيع المبدئي: {fmt_curr(sp_edit_val)}\n"
                f"• المورد: {cb_supp.get() or 'غير محدد'}",
                parent=ewin
            )
            if not confirm:
                return

            chosen_supp_label = cb_supp.get()
            chosen_supp_id = edit_supp_map.get(chosen_supp_label, dev_obj.get('supplier_id'))
            b_date_val = ent_buy_date.get().strip() if can_edit_date else None
            s_date_val = ent_sell_date.get().strip() if (ent_sell_date and can_edit_date) else None

            try:
                self.db.update_device(
                    device_id=dev_obj['id'],
                    category=cat_val,
                    model=mod_val,
                    storage=cb_storage.get().strip(),
                    battery=ent_bat.get().strip() or None,
                    imei=imei_val,
                    buy_price=bp_val,
                    ram=cb_ram.get().strip(),
                    device_condition=cb_cond.get().strip(),
                    has_box=box_var.get(),
                    notes=ent_notes.get().strip(),
                    supplier_id=chosen_supp_id,
                    color=(cb_color.get().strip() or "أسود") if cb_color.get().strip() != "بدون" else "أسود",
                    has_tax=tax_var.get(),
                    initial_selling_price=sp_edit_val,
                    accessories=ent_acc.get().strip(),
                    buy_date=b_date_val,
                    sell_date=s_date_val,
                    user_id=self.current_user_id
                )
                messagebox.showinfo("تم الحفظ", "تم تحديث كافة بيانات ومواصفات الجهاز بنجاح!", parent=ewin)
                ewin.destroy()
                if on_success_callback:
                    on_success_callback()
            except Exception as ex:
                messagebox.showerror("خطأ", str(ex), parent=ewin)

        chain_widgets = [cb_cat, ent_model, cb_storage, cb_ram, cb_color, ent_bat, ent_acc, ent_imei, ent_init_selling_price]
        if can_see_buy:
            chain_widgets.append(ent_buy_price)
        chain_widgets.append(ent_notes)
        self._bind_enter_chain(chain_widgets, final_callback=save_edits)

        tk.Button(
            bot_bar, text="💾 حفظ التعديلات", command=save_edits,
            bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 11, "bold"),
            padx=22, pady=5, relief="flat", cursor="hand2"
        ).pack(side="right", padx=6)

        tk.Button(
            bot_bar, text="إلغاء", command=ewin.destroy,
            bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 10, "bold"),
            padx=18, pady=5, relief="flat", cursor="hand2"
        ).pack(side="left", padx=6)

    def view_search_sale(self):
        if not self.has_permission('can_view_sales_screen'):
            messagebox.showerror("صلاحيات غير كافية", "عفواً، لا تملك صلاحية فتح شاشة المبيعات!")
            return

        self.current_view_func = self.view_search_sale
        self.build_main_ui(keep_view=True)
        self.clear_content()

        top_hdr = tk.Frame(self.content_frame, bg=self.COLOR_BG, padx=18, pady=8)
        top_hdr.pack(fill="x")

        tk.Label(
            top_hdr, text="🛒 المبيعات وإصدار الفواتير",
            font=("Segoe UI", 16, "bold"), bg=self.COLOR_BG, fg=self.COLOR_ACCENT
        ).pack(side="right")

        if self.has_permission('can_process_returns'):
            tk.Button(
                top_hdr, text="🔄 استرجاع جهاز مباع", command=self.open_return_device_modal,
                bg=self.COLOR_WARN, fg="#111111", font=("Segoe UI", 10, "bold"),
                padx=14, pady=5, relief="flat", cursor="hand2"
            ).pack(side="left", padx=4)

        op_date_bar = tk.Frame(self.content_frame, bg=self.COLOR_BG)
        op_date_bar.pack(fill="x", padx=18, pady=(0, 4))
        get_sale_custom_date = self._create_operation_date_picker(op_date_bar, label_text="📅 تاريخ وتوقيت عملية البيع:")

        search_card = tk.Frame(self.content_frame, bg=self.COLOR_CARD, padx=14, pady=10)
        search_card.pack(fill="x", padx=18, pady=(0, 8))

        tk.Label(
            search_card, text="🔍 البحث بـ:",
            bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 11, "bold")
        ).pack(side="right", padx=(4, 2))

        search_type_cb = ttk.Combobox(
            search_card,
            values=["بحث شامل ذكي ⚡", "سيريال IMEI", "كود الجهاز #ID", "الموديل والماركة", "اسم المورد"],
            state="readonly", width=16, font=("Segoe UI", 10, "bold"), justify="right"
        )
        search_type_cb.current(0)
        search_type_cb.pack(side="right", padx=(0, 8), ipady=3)

        search_entry = tk.Entry(
            search_card, font=("Segoe UI", 12, "bold"),
            bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT,
            justify="right", width=26
        )
        search_entry.pack(side="right", padx=6, ipady=4)
        search_entry.focus_set()

        tk.Button(
            search_card, text="🔍 فحص واختيار", command=lambda: perform_device_search(),
            bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold"),
            padx=16, pady=5, relief="flat", cursor="hand2", activebackground="#0284c7", activeforeground="#ffffff"
        ).pack(side="right", padx=4)

        tk.Label(
            search_card, text="جاهز لمسح السكانر 🟢",
            bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 9, "bold"), padx=8, pady=3
        ).pack(side="left", padx=4)

        results_frame = tk.Frame(self.content_frame, bg=self.COLOR_CARD, padx=12, pady=6)
        results_frame.pack(fill="x", padx=18, pady=(0, 8))

        cols = ("حالة التوفر", "سعر البيع المبدئي", "الحالة", "المساحة", "السيريال IMEI", "الموديل", "الماركة", "كود الجهاز")
        rtree = ttk.Treeview(results_frame, columns=cols, show="headings", height=5)
        self.configure_tree_row_colors(rtree)
        r_widths = {
            "حالة التوفر": 100, "سعر البيع المبدئي": 125, "الحالة": 100, "المساحة": 90,
            "السيريال IMEI": 135, "الموديل": 140, "الماركة": 105, "كود الجهاز": 85
        }
        for c in cols:
            rtree.heading(c, text=c)
            rtree.column(c, anchor="center", width=r_widths.get(c, 100))

        rvsb = ttk.Scrollbar(results_frame, orient="vertical", command=rtree.yview)
        rtree.configure(yscrollcommand=rvsb.set)
        rvsb.pack(side="left", fill="y")
        rtree.pack(side="right", fill="x", expand=True)

        split_container = tk.Frame(self.content_frame, bg=self.COLOR_BG)
        split_container.pack(fill="both", expand=True, padx=18, pady=(0, 14))
        split_container.grid_columnconfigure(0, weight=1)
        split_container.grid_columnconfigure(1, weight=1)
        split_container.grid_rowconfigure(0, weight=1)

        tech_card = tk.LabelFrame(
            split_container, text="📱 البيانات الفنية للجهاز المختار",
            bg=self.COLOR_CARD, fg=self.COLOR_BLUE, font=("Segoe UI", 11, "bold"), padx=14, pady=10
        )
        tech_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        fin_card = tk.LabelFrame(
            split_container, text="💰 البيانات المالية وبيانات العميل",
            bg=self.COLOR_CARD, fg=self.COLOR_ACCENT, font=("Segoe UI", 11, "bold"), padx=16, pady=10
        )
        fin_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        fin_card.grid_columnconfigure(0, weight=1)

        selected_state = {"dev": None}
        avail_map = {}

        tech_info_holder = tk.Frame(tech_card, bg=self.COLOR_CARD)
        tech_info_holder.pack(fill="both", expand=True)

        can_see_buy = self.has_permission('can_view_buy_price')

        def render_selected_device_specs(dev):
            for w in tech_info_holder.winfo_children():
                w.destroy()

            if not dev:
                tk.Label(
                    tech_info_holder, text="👈 اختر جهازاً من الجدول بالأعلى أو ابحث بالسيريال لعرض مواصفاته وإتمام البيع",
                    font=("Segoe UI", 11, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_MUTED, wraplength=380, pady=45
                ).pack(expand=True)
                return

            buy_p_str = fmt_curr(dev.get('buy_price')) if can_see_buy else "🔒 مخفي"
            bat_str = f"{dev['battery_health']}%" if dev.get('battery_health') else "-"
            box_str = "بعلبة 📦" if dev.get('has_box') else "بدون علبة"

            st_clean = str(dev.get('storage') or "-").replace("GB", "").strip() or "-"
            rm_clean = str(dev.get('ram') or "-").replace("GB", "").strip() or "-"
            raw_c = str(dev.get('color') or '').strip()
            color_clean = "أسود" if (not raw_c or raw_c == "بدون") else raw_c
            tax_clean = "خاضع لضريبة 🏛️" if dev.get('has_tax') else "بدون ضريبة"

            spec_pairs = [
                [("كود الجهاز:", f"#{dev['id']}"), ("الماركة:", dev.get('category') or "-")],
                [("الموديل:", dev.get('model') or "-"), ("حالة الجهاز:", dev.get('device_condition') or "مستعمل")],
                [("اللون:", color_clean), ("الضريبة:", tax_clean)],
                [("المساحة:", st_clean), ("الرامات:", rm_clean)],
                [("البطارية:", bat_str), ("العلبة:", box_str)],
                [("السيريال IMEI:", dev.get('imei_serial') or "-"), ("سعر التكلفة:", buy_p_str)],
                [("المورد:", dev.get('supplier_name') or "-"), ("ملاحظات:", dev.get('notes') or "-")],
            ]
            self._build_rtl_info_grid(tech_info_holder, spec_pairs)

            tk.Button(
                tech_info_holder, text="🔍 فتح بطاقة الجهاز الكاملة",
                command=lambda: self.show_device_details_modal(dev['id']),
                bg=self.COLOR_TOPBAR, fg="#38bdf8", font=("Segoe UI", 9, "bold"),
                padx=12, pady=4, relief="flat", cursor="hand2"
            ).pack(anchor="w", padx=6, pady=6)

        render_selected_device_specs(None)

        def add_fin_label(r_i, txt):
            tk.Label(fin_card, text=txt, bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=r_i, column=1, sticky="e", padx=8, pady=6)

        add_fin_label(0, "سعر البيع (ج.م):")
        ent_sell_price = tk.Entry(fin_card, validate="key", validatecommand=self.vcmd_num, font=("Segoe UI", 12, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_ACCENT, insertbackground=self.COLOR_TEXT, justify="center")
        ent_sell_price.grid(row=0, column=0, sticky="ew", padx=8, pady=6, ipady=4)

        add_fin_label(1, "المدفوع نقداً (ج.م):")
        cash_row = tk.Frame(fin_card, bg=self.COLOR_CARD)
        cash_row.grid(row=1, column=0, sticky="ew", padx=8, pady=6)

        ent_cash = tk.Entry(cash_row, validate="key", validatecommand=self.vcmd_num, font=("Segoe UI", 12, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="center")
        ent_cash.pack(side="right", fill="x", expand=True, ipady=4)

        def fill_full_cash():
            sp = ent_sell_price.get().strip()
            if sp:
                ent_cash.delete(0, tk.END)
                ent_cash.insert(0, sp)
                update_remaining_lbl()
                ent_cust_name.focus_set()

        tk.Button(
            cash_row, text="كامل المبلغ", command=fill_full_cash,
            bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 9, "bold"),
            padx=10, pady=4, relief="flat", cursor="hand2"
        ).pack(side="left", padx=(0, 6))

        add_fin_label(2, "المتبقي على العميل (الخرج):")
        lbl_remaining = tk.Label(fin_card, text=fmt_curr(0), font=("Segoe UI", 12, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_WARN, pady=5)
        lbl_remaining.grid(row=2, column=0, sticky="ew", padx=8, pady=6)

        add_fin_label(3, "اسم العميل:")
        ent_cust_name = tk.Entry(fin_card, font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="right")
        ent_cust_name.grid(row=3, column=0, sticky="ew", padx=8, pady=6, ipady=4)

        add_fin_label(4, "رقم هاتف العميل:")
        ent_cust_phone = tk.Entry(fin_card, font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="center")
        ent_cust_phone.grid(row=4, column=0, sticky="ew", padx=8, pady=6, ipady=4)

        add_fin_label(5, "ملاحظات البيع:")
        ent_sale_notes = tk.Entry(fin_card, font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="right")
        ent_sale_notes.grid(row=5, column=0, sticky="ew", padx=8, pady=6, ipady=4)

        last_sell_price_tracked = [""]

        def on_sell_price_typing(event=None):
            sp_val = ent_sell_price.get().strip()
            cur_c = ent_cash.get().strip()
            if not cur_c or cur_c == last_sell_price_tracked[0]:
                ent_cash.delete(0, tk.END)
                ent_cash.insert(0, sp_val)
            last_sell_price_tracked[0] = sp_val
            update_remaining_lbl()

        def update_remaining_lbl(event=None):
            try:
                sp = float(ent_sell_price.get().strip() or 0)
            except ValueError:
                sp = 0.0
            try:
                cr = float(ent_cash.get().strip() or 0)
            except ValueError:
                cr = 0.0
            rem = max(0.0, sp - cr)
            lbl_remaining.config(
                text=fmt_curr(rem),
                fg=self.COLOR_DANGER if rem > 0 else self.COLOR_ACCENT
            )

        ent_sell_price.bind("<KeyRelease>", on_sell_price_typing)
        ent_cash.bind("<KeyRelease>", update_remaining_lbl)

        def select_device_for_sale(dev):
            selected_state["dev"] = dev
            render_selected_device_specs(dev)
            if dev:
                target_p = dev.get('initial_selling_price') or dev.get('selling_price') or dev.get('buy_price')
                if target_p:
                    ent_sell_price.delete(0, tk.END)
                    ent_sell_price.insert(0, fmt_num(target_p))
                    on_sell_price_typing()
                ent_sell_price.focus_set()
                ent_sell_price.select_range(0, tk.END)

        def on_tree_select(event=None):
            sel = rtree.selection()
            if not sel:
                return
            did = clean_id_val(sel[0])
            dev = avail_map.get(did)
            if dev:
                select_device_for_sale(dev)

        def on_tree_enter_or_tab(event=None):
            sel = rtree.selection()
            if sel:
                dev = avail_map.get(clean_id_val(sel[0]))
                if dev:
                    select_device_for_sale(dev)
            ent_sell_price.focus_set()
            return "break"

        rtree.bind("<<TreeviewSelect>>", on_tree_select)
        rtree.bind("<Return>", on_tree_enter_or_tab)
        rtree.bind("<Tab>", on_tree_enter_or_tab)

        def perform_device_search(event=None):
            q = search_entry.get().strip()
            stype = search_type_cb.get()
            rtree.delete(*rtree.get_children())
            avail_map.clear()

            all_avail = self.db.get_inventory(include_sold=False)
            if not q:
                results = all_avail
            else:
                q_lower = q.lower()
                clean_q_id = clean_id_val(q)
                if "سيريال" in stype:
                    results = [d for d in all_avail if q_lower in str(d.get('imei_serial') or '').lower()]
                elif "كود" in stype or "#ID" in stype:
                    results = [d for d in all_avail if clean_q_id is not None and d['id'] == clean_q_id]
                elif "الموديل" in stype:
                    results = [d for d in all_avail if q_lower in f"{d.get('category') or ''} {d.get('model') or ''}".lower()]
                elif "المورد" in stype:
                    results = [d for d in all_avail if q_lower in str(d.get('supplier_name') or '').lower()]
                else:
                    results = self.db.search_available_devices(q)
                    if clean_q_id is not None and not results:
                        d_by_id = self.db.get_device_by_id(clean_q_id)
                        if d_by_id and not d_by_id.get('is_sold') and not d_by_id.get('is_deleted'):
                            results = [d_by_id]

            for idx_r, d in enumerate(results):
                did = d['id']
                avail_map[did] = d
                st_val = str(d.get('storage') or "-").replace("GB", "").strip() or "-"
                sp_val = d.get('initial_selling_price') or d.get('selling_price') or d.get('buy_price') or 0
                row_tag = 'evenrow' if idx_r % 2 == 0 else 'oddrow'
                st_disp = f"{st_val} GB" if (st_val and st_val != "-") else "-"

                rtree.insert("", "end", iid=str(did), tags=(row_tag,), values=(
                    fix_bidi("متاح 🟢" if not d.get('is_sold') else "مباع 🔴"),
                    fmt_curr(sp_val),
                    fix_bidi(d.get('device_condition') or "مستعمل"),
                    fix_bidi(st_disp),
                    d.get('imei_serial') or "-",
                    fix_bidi(d.get('model') or "-"),
                    fix_bidi(d.get('category') or "-"),
                    f"#{did}"
                ))

            if len(results) == 1 or (q and len(results) > 0 and (q == results[0].get('imei_serial') or q.lstrip('#') == str(results[0].get('id')))):
                first_id = str(results[0]['id'])
                rtree.selection_set(first_id)
                rtree.focus(first_id)
                select_device_for_sale(results[0])
                ent_sell_price.focus_set()
                ent_sell_price.select_range(0, tk.END)

        search_type_cb.bind("<<ComboboxSelected>>", perform_device_search)

        def on_search_return(event=None):
            perform_device_search()
            children = rtree.get_children()
            if children:
                sel = rtree.selection()
                target_iid = sel[0] if sel else children[0]
                rtree.selection_set(target_iid)
                rtree.focus(target_iid)
                dev = avail_map.get(clean_id_val(target_iid))
                if dev:
                    select_device_for_sale(dev)
                    ent_sell_price.focus_set()
                    ent_sell_price.select_range(0, tk.END)
            return "break"

        def on_search_tab(event=None):
            children = rtree.get_children()
            if children:
                sel = rtree.selection()
                target_iid = sel[0] if sel else children[0]
                rtree.selection_set(target_iid)
                rtree.focus(target_iid)
                dev = avail_map.get(clean_id_val(target_iid))
                if dev:
                    select_device_for_sale(dev)
            ent_sell_price.focus_set()
            return "break"

        def on_search_down(event=None):
            children = rtree.get_children()
            if children:
                rtree.focus_set()
                if not rtree.selection():
                    rtree.selection_set(children[0])
                    rtree.focus(children[0])
                    dev = avail_map.get(clean_id_val(children[0]))
                    if dev:
                        select_device_for_sale(dev)
            return "break"

        search_entry.bind("<Tab>", on_search_tab)
        search_entry.bind("<Down>", on_search_down)
        search_entry.bind("<Return>", on_search_return)
        search_entry.bind("<KeyRelease>", lambda e: perform_device_search() if e.keysym not in ("Return", "Up", "Down", "Tab") else None)
        self.bind("<F2>", lambda e: [search_entry.focus_set(), search_entry.select_range(0, tk.END)])

        def confirm_sale_action():
            if not self.has_permission('can_execute_sale'):
                messagebox.showerror("صلاحيات غير كافية", "عفواً، لا تملك صلاحية إتمام عمليات البيع!")
                return

            dev = selected_state["dev"]
            if not dev:
                messagebox.showwarning("تنبيه", "يرجى اختيار الجهاز المراد بيعه أولاً!")
                search_entry.focus_set()
                return

            try:
                sell_price = float(ent_sell_price.get().strip() or 0)
            except ValueError:
                sell_price = 0.0

            if sell_price <= 0:
                messagebox.showwarning("تنبيه", "يرجى إدخال سعر البيع بشكل صحيح!")
                ent_sell_price.focus_set()
                return

            buy_price = float(dev.get('buy_price') or 0)

            # تحسين أمني حاسم: فرض صلاحية can_sell_below_cost
            if sell_price < buy_price:
                loss = buy_price - sell_price
                if not self.has_permission('can_sell_below_cost'):
                    messagebox.showerror(
                        "صلاحيات غير كافية ⛔",
                        f"لا تملك صلاحية البيع بأقل من سعر التكلفة (سعر الشراء: {fmt_curr(buy_price)})!\n"
                        f"يرجى مراجعة مدير النظام.",
                        parent=self
                    )
                    ent_sell_price.focus_set()
                    return

                if not messagebox.askyesno(
                    "⚠️ تحذير مالي - بيع بخسارة",
                    f"تنبيه: سعر البيع ({fmt_curr(sell_price)}) أقل من سعر التكلفة ({fmt_curr(buy_price)})!\n"
                    f"العملية ستسجل خسارة بمقدار ({fmt_curr(loss)}).\n\n"
                    "هل أنت متأكد تماماً من إتمام عملية البيع بخسارة؟",
                    parent=self
                ):
                    ent_sell_price.focus_set()
                    return

            raw_cash = ent_cash.get().strip()
            try:
                cash_received = float(raw_cash) if raw_cash != "" else sell_price
            except ValueError:
                cash_received = sell_price

            if cash_received > sell_price:
                messagebox.showwarning("تنبيه", "المبلغ المدفوع نقداً لا يمكن أن يكون أكبر من سعر البيع!")
                ent_cash.focus_set()
                return

            remaining = round(sell_price - cash_received, 2)
            cust_name = ent_cust_name.get().strip() or "عميل نقدي"
            cust_phone = ent_cust_phone.get().strip()
            notes_val = ent_sale_notes.get().strip()

            # تحسين إجرائي: في حالة المتبقي (الخرج) يلزم اسم ثلاثي ورقم هاتف للمتابعة
            if remaining > 0:
                if cust_name == "عميل نقدي" or len(cust_name.strip()) < 3:
                    messagebox.showwarning("تنبيه", "في حالة وجود مبلغ متبقي (خرج)، يرجى كتابة اسم العميل الثلاثي!", parent=self)
                    ent_cust_name.focus_set()
                    return
                if not cust_phone or len(cust_phone.strip()) < 7:
                    messagebox.showwarning("تنبيه", "في حالة وجود مبلغ متبقي (خرج)، رقم هاتف العميل إجباري للمتابعة والتحصيل!", parent=self)
                    ent_cust_phone.focus_set()
                    return

            confirm_sale_msg = (
                f"هل أنت متأكد من إتمام وتأكيد عملية البيع التالية؟\n\n"
                f"• الجهاز: {dev.get('category')} {dev.get('model')} (#{dev['id']})\n"
                f"• السيريال: {dev.get('imei_serial') or '-'}\n"
                f"• سعر البيع: {fmt_curr(sell_price)}\n"
                f"• المدفوع نقداً: {fmt_curr(cash_received)}\n"
                f"• المتبقي (خرج): {fmt_curr(remaining)}\n"
                f"• العميل: {cust_name} ({cust_phone or 'بدون هاتف'})"
            )
            if not messagebox.askyesno("تأكيد إتمام عملية البيع", confirm_sale_msg, parent=self):
                return

            try:
                sale_custom_dt = get_sale_custom_date()
            except ValueError as val_err:
                messagebox.showerror("خطأ في التاريخ", str(val_err))
                return

            try:
                sale_res = self.db.process_sale(
                    device_id=dev['id'],
                    user_id=self.current_user_id,
                    customer_name=cust_name,
                    customer_phone=cust_phone,
                    sell_price=sell_price,
                    cash_received=cash_received,
                    discount=0.0,
                    notes=notes_val,
                    custom_date=sale_custom_dt
                )
                sale_id = sale_res['sale_id'] if isinstance(sale_res, dict) else sale_res

                if self.has_permission('can_print_sale_invoice'):
                    if messagebox.askyesno("تم البيع بنجاح", f"تم تسجيل فاتورة البيع #{sale_id} بنجاح!\nهل ترغب في معاينة وطباعة الفاتورة الآن؟"):
                        inv_data = {
                            'doc_type': 'SALE' if remaining <= 0 else 'CUSTOMER_DEBT',
                            'sale_id': sale_id,
                            'customer_name': cust_name,
                            'customer_phone': cust_phone or '-',
                            'seller_name': self.current_user.get('full_name') or self.current_user['username'],
                            'device': dev,
                            'original_price': sell_price,
                            'discount': 0.0,
                            'sell_price': sell_price,
                            'cash_received': cash_received,
                            'remaining_balance': remaining,
                            'sale_notes': notes_val,
                            'payments_list': []
                        }
                        self.open_invoice_preview_and_print(inv_data, f"طباعة فاتورة بيع #{sale_id}")
                else:
                    messagebox.showinfo("تم البيع", f"تم تسجيل فاتورة البيع #{sale_id} بنجاح!")

                selected_state["dev"] = None
                render_selected_device_specs(None)
                for e_w in (ent_sell_price, ent_cash, ent_cust_name, ent_cust_phone, ent_sale_notes, search_entry):
                    e_w.delete(0, tk.END)
                update_remaining_lbl()
                perform_device_search()
                search_entry.focus_set()
            except Exception as ex:
                messagebox.showerror("خطأ أثناء البيع", str(ex))

        self._bind_enter_chain(
            [ent_sell_price, ent_cash, ent_cust_name, ent_cust_phone, ent_sale_notes],
            final_callback=confirm_sale_action
        )

        btn_row = tk.Frame(fin_card, bg=self.COLOR_CARD, pady=8)
        btn_row.grid(row=6, column=0, columnspan=2, sticky="ew")

        if self.has_permission('can_execute_sale'):
            tk.Button(
                btn_row, text="✅ تأكيد وإتمام البيع (Enter)", command=confirm_sale_action,
                bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 12, "bold"),
                padx=24, pady=7, relief="flat", cursor="hand2"
            ).pack(side="right", padx=8, fill="x", expand=True)

        perform_device_search()

    def view_sell(self):
        return self.view_search_sale()

    def open_return_device_modal(self):
        if not self.has_permission('can_process_returns'):
            messagebox.showerror("صلاحيات غير كافية", "عفواً، لا تملك صلاحية إجراء المرتجعات!")
            return

        rwin = tk.Toplevel(self)
        rwin.title("استرجاع جهاز مباع إلى المخزون")
        rwin.geometry("820x540")
        rwin.configure(bg=self.COLOR_BG)
        rwin.grab_set()

        top_bar = tk.Frame(rwin, bg=self.COLOR_TOPBAR, pady=10, padx=16)
        top_bar.pack(fill="x")
        tk.Label(top_bar, text="🔄 استرجاع جهاز مباع إلى المخزون", font=("Segoe UI", 13, "bold"), bg=self.COLOR_TOPBAR, fg=self.COLOR_WARN).pack(side="right")

        s_bar = tk.Frame(rwin, bg=self.COLOR_CARD, padx=14, pady=8)
        s_bar.pack(fill="x", padx=16, pady=8)
        tk.Label(s_bar, text="🔍 بحث بالسيريال أو اسم العميل أو الكود:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right", padx=4)
        s_ent = tk.Entry(s_bar, font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="right", width=28)
        s_ent.pack(side="right", padx=6, ipady=3)
        s_ent.focus_set()

        t_frame = tk.Frame(rwin, bg=self.COLOR_CARD, padx=12, pady=8)
        t_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        cols = ("تاريخ البيع", "سعر البيع", "العميل", "حالة الجهاز", "المساحة", "السيريال IMEI", "الموديل", "الماركة", "كود الجهاز")
        tree = ttk.Treeview(t_frame, columns=cols, show="headings")
        self.configure_tree_row_colors(tree)
        r_widths = {
            "تاريخ البيع": 120, "سعر البيع": 105, "العميل": 120, "حالة الجهاز": 95,
            "المساحة": 85, "السيريال IMEI": 130, "الموديل": 120, "الماركة": 100, "كود الجهاز": 80
        }
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, anchor="center", width=r_widths.get(c, 100))

        vsb = ttk.Scrollbar(t_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="left", fill="y")
        tree.pack(side="right", fill="both", expand=True)

        def load_sold_devices(event=None):
            tree.delete(*tree.get_children())
            q = s_ent.get().strip().lower()
            sold_list = self.db.get_sales_report()
            for s in sold_list:
                searchable = f"{s.get('device_id')} {s.get('category')} {s.get('model')} {s.get('imei_serial')} {s.get('customer_name')}".lower()
                if q and q not in searchable:
                    continue
                st_val = str(s.get('storage') or '-').replace('GB', '').strip() or '-'
                cond_val = s.get('device_condition') or 'مستعمل'
                row_tag = 'evenrow' if len(tree.get_children()) % 2 == 0 else 'oddrow'
                tree.insert("", "end", iid=str(s['device_id']), tags=(row_tag,), values=(
                    s.get('sell_date_formatted') or "-",
                    fmt_curr(s.get('sell_price')),
                    fix_bidi(s.get('customer_name') or "-"),
                    fix_bidi(cond_val),
                    st_val,
                    s.get('imei_serial') or "-",
                    fix_bidi(s.get('model') or "-"),
                    fix_bidi(s.get('category') or "-"),
                    f"#{s['device_id']}"
                ))

        def confirm_return():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("تنبيه", "يرجى تحديد الجهاز المراد استرجاعه من الجدول!", parent=rwin)
                return
            dev_id = clean_id_val(sel[0])
            if messagebox.askyesno("تأكيد الاسترجاع", f"هل أنت متأكد من استرجاع الجهاز #{dev_id} وإعادته للمخزون وتسوية مبالغ النقدية؟", parent=rwin):
                try:
                    self.db.process_return(dev_id, self.current_user_id)
                    messagebox.showinfo("تم الاسترجاع", "تم استرجاع الجهاز وإعادته للمخزون وتسوية الخزينة بنجاح!", parent=rwin)
                    rwin.destroy()
                    if self.current_view_func:
                        self.current_view_func()
                except Exception as ex:
                    messagebox.showerror("خطأ", str(ex), parent=rwin)

        s_ent.bind("<KeyRelease>", load_sold_devices)
        load_sold_devices()

        bot_bar = tk.Frame(rwin, bg=self.COLOR_TOPBAR, pady=10, padx=16)
        bot_bar.pack(fill="x", side="bottom")
        tk.Button(bot_bar, text="🔄 تأكيد استرجاع الجهاز للمخزون", command=confirm_return, bg=self.COLOR_WARN, fg="#111", font=("Segoe UI", 11, "bold"), padx=18, pady=5, relief="flat", cursor="hand2").pack(side="right", padx=6)
        tk.Button(bot_bar, text="إغلاق", command=rwin.destroy, bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 10, "bold"), padx=16, pady=5, relief="flat", cursor="hand2").pack(side="left", padx=6)

    def view_buy(self):
        if not self.has_permission('can_buy_devices'):
            messagebox.showerror("صلاحيات غير كافية", "عفواً، لا تملك صلاحية فتح شاشة المشتريات!")
            return

        self.current_view_func = self.view_buy
        self.build_main_ui(keep_view=True)
        self.clear_content()

        top_hdr = tk.Frame(self.content_frame, bg=self.COLOR_BG, padx=18, pady=8)
        top_hdr.pack(fill="x")

        tk.Label(
            top_hdr, text="📥 تسجيل المشتريات وإدخال الأجهزة",
            font=("Segoe UI", 16, "bold"), bg=self.COLOR_BG, fg=self.COLOR_PURPLE
        ).pack(side="right")

        if self.has_permission('can_manage_suppliers'):
            tk.Button(
                top_hdr, text="⚙️ إدارة الموردين", command=lambda: self.open_manage_suppliers_modal(on_close_callback=refresh_suppliers_combo),
                bg=self.COLOR_TEAL, fg="white", font=("Segoe UI", 10, "bold"),
                padx=14, pady=5, relief="flat", cursor="hand2"
            ).pack(side="left", padx=4)

        if self.has_permission('can_add_supplier_in_buy'):
            tk.Button(
                top_hdr, text="➕ إضافة مورد", command=lambda: self.open_quick_add_supplier_modal(on_added_callback=refresh_suppliers_combo),
                bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold"),
                padx=14, pady=5, relief="flat", cursor="hand2"
            ).pack(side="left", padx=4)

        op_date_bar = tk.Frame(self.content_frame, bg=self.COLOR_BG)
        op_date_bar.pack(fill="x", padx=18, pady=(0, 4))
        get_buy_custom_date = self._create_operation_date_picker(op_date_bar, label_text="📅 تاريخ وتوقيت عملية الشراء:")

        split_frame = tk.Frame(self.content_frame, bg=self.COLOR_BG)
        split_frame.pack(fill="both", expand=True, padx=18, pady=(4, 14))
        split_frame.grid_columnconfigure(0, weight=1)
        split_frame.grid_columnconfigure(1, weight=1)
        split_frame.grid_rowconfigure(0, weight=1)

        tech_card = tk.LabelFrame(
            split_frame, text="📱 المواصفات الفنية للجهاز",
            bg=self.COLOR_CARD, fg=self.COLOR_BLUE, font=("Segoe UI", 11, "bold"), padx=16, pady=12
        )
        tech_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        tech_card.grid_columnconfigure(0, weight=1)

        fin_card = tk.LabelFrame(
            split_frame, text="💰 البيانات المالية وبيانات المورد",
            bg=self.COLOR_CARD, fg=self.COLOR_ACCENT, font=("Segoe UI", 11, "bold"), padx=16, pady=12
        )
        fin_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        fin_card.grid_columnconfigure(0, weight=1)

        tpl_frame = tk.Frame(tech_card, bg=self.COLOR_CARD)
        tpl_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        tk.Label(tpl_frame, text="⚡ قالب سريع:", bg=self.COLOR_CARD, fg=self.COLOR_MUTED, font=("Segoe UI", 9, "bold")).pack(side="right", padx=4)

        def apply_spec_template(st_val, rm_val):
            cb_storage.set(st_val)
            cb_ram.set(rm_val)
            ent_bat.focus_set()

        for st_t, rm_t in [("64", "4"), ("128", "4"), ("128", "6"), ("128", "8"), ("256", "8"), ("256", "12")]:
            tk.Button(
                tpl_frame, text=f"{st_t}/{rm_t}",
                command=lambda s=st_t, r=rm_t: apply_spec_template(s, r),
                bg=self.COLOR_ENTRY_BG, fg=self.COLOR_BLUE, font=("Segoe UI", 8, "bold"),
                padx=7, pady=2, relief="flat", cursor="hand2"
            ).pack(side="right", padx=2)

        def add_tech_lbl(r_i, txt):
            tk.Label(tech_card, text=txt, bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=r_i, column=1, sticky="e", padx=8, pady=6)

        add_tech_lbl(1, "الماركة:")
        cb_cat = ttk.Combobox(tech_card, values=self.BRAND_LIST, font=("Segoe UI", 11, "bold"), justify="right")
        if self.BRAND_LIST:
            cb_cat.current(0)
        cb_cat.grid(row=1, column=0, sticky="ew", padx=8, pady=6, ipady=3)

        add_tech_lbl(2, "الموديل:")
        ent_model = tk.Entry(tech_card, font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="right")
        ent_model.grid(row=2, column=0, sticky="ew", padx=8, pady=6, ipady=4)

        add_tech_lbl(3, "المساحة التخزينية:")
        cb_storage = ttk.Combobox(tech_card, values=["", "32", "64", "128", "256", "512", "1TB"], font=("Segoe UI", 11, "bold"), justify="right")
        cb_storage.set("128")
        cb_storage.grid(row=3, column=0, sticky="ew", padx=8, pady=6, ipady=3)

        add_tech_lbl(4, "الرامات (RAM):")
        cb_ram = ttk.Combobox(tech_card, values=["", "2", "3", "4", "6", "8", "12", "16"], font=("Segoe UI", 11, "bold"), justify="right")
        cb_ram.set("")
        cb_ram.grid(row=4, column=0, sticky="ew", padx=8, pady=6, ipady=3)

        add_tech_lbl(5, "نسبة البطارية (%):")
        ent_bat = tk.Entry(tech_card, validate="key", validatecommand=self.vcmd_num, font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="center")
        ent_bat.grid(row=5, column=0, sticky="ew", padx=8, pady=6, ipady=4)

        add_tech_lbl(6, "السيريال (IMEI):")
        imei_row = tk.Frame(tech_card, bg=self.COLOR_CARD)
        imei_row.grid(row=6, column=0, sticky="ew", padx=8, pady=6)

        def trigger_scan_focus():
            ent_imei.focus_set()
            ent_imei.select_range(0, tk.END)
            scan_btn.config(bg=self.COLOR_ACCENT, text="جاهز للمسح 🟢")
            self.after(2500, lambda: scan_btn.config(bg=self.COLOR_BLUE, text="📷 مسح سكانر"))

        scan_btn = tk.Button(
            imei_row, text="📷 مسح سكانر", command=trigger_scan_focus,
            bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 9, "bold"),
            padx=8, pady=2, relief="flat", cursor="hand2"
        )
        scan_btn.pack(side="left", padx=(4, 0))

        ent_imei = tk.Entry(imei_row, font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="center")
        ent_imei.pack(side="right", fill="x", expand=True, ipady=4)

        def on_imei_scanner_trigger(event=None):
            im_val = ent_imei.get().strip()
            if im_val:
                dup = self.db.search_device_by_criteria(im_val, search_by='SERIAL')
                if dup and not dup.get('is_sold') and not dup.get('is_deleted'):
                    messagebox.showwarning(
                        "⚠️ تنبيه التكرار",
                        f"هذا السيريال ({im_val}) مسجل بالفعل بالمخزون للجهاز #{dup['id']} ({dup.get('category')} {dup.get('model')})!"
                    )
            bat_txt = ent_bat.get().strip()
            if bat_txt:
                try:
                    bv = int(bat_txt)
                    if bv < 0 or bv > 100:
                        messagebox.showwarning("تنبيه", "نسبة صحة البطارية يجب أن تكون بين 1% و 100%!")
                        ent_bat.focus_set()
                        return "break"
                except ValueError:
                    pass
            ent_buy_price.focus_set()
            return "break"

        ent_imei.bind("<Return>", on_imei_scanner_trigger)

        add_tech_lbl(7, "حالة الجهاز:")
        cond_row = tk.Frame(tech_card, bg=self.COLOR_CARD)
        cond_row.grid(row=7, column=0, sticky="ew", padx=8, pady=6)

        cb_cond = ttk.Combobox(cond_row, values=["جديد", "كسر زيرو", "مستعمل"], state="readonly", width=11, font=("Segoe UI", 10, "bold"), justify="right")
        cb_cond.current(2)
        cb_cond.pack(side="right", ipady=2)

        box_var = tk.BooleanVar(value=False)
        chk_box = tk.Checkbutton(
            cond_row, text="معه علبة 📦", variable=box_var,
            bg=self.COLOR_CARD, fg=self.COLOR_ACCENT, selectcolor=self.COLOR_ENTRY_BG,
            font=("Segoe UI", 10, "bold"), takefocus=True
        )
        chk_box.pack(side="right", padx=(8, 4))

        tax_var = tk.BooleanVar(value=False)
        chk_tax = tk.Checkbutton(
            cond_row, text="ضريبة 🏛️", variable=tax_var,
            bg=self.COLOR_CARD, fg=self.COLOR_BLUE, selectcolor=self.COLOR_ENTRY_BG,
            font=("Segoe UI", 10, "bold"), takefocus=True
        )
        chk_tax.pack(side="right", padx=4)

        add_tech_lbl(8, "اللون:")
        color_row = tk.Frame(tech_card, bg=self.COLOR_CARD)
        color_row.grid(row=8, column=0, sticky="ew", padx=8, pady=6)

        color_options = ["أسود", "فضي", "أبيض", "رمادي", "تيتانيوم طبيعي", "تيتانيوم أسود", "تيتانيوم صحراوي", "أزرق", "ذهبي", "أخضر", "كحلي", "أحمر", "وردي"]
        cb_color = ttk.Combobox(color_row, values=color_options, font=("Segoe UI", 11, "bold"), justify="right")
        cb_color.set("أسود")
        cb_color.pack(side="right", fill="x", expand=True, ipady=3)
        self.attach_autocomplete(cb_color, lambda: color_options, next_focus_widget=None)

        self.attach_autocomplete(cb_cat, lambda: self.BRAND_LIST, next_focus_widget=ent_model)

        def on_buy_model_chosen(chosen_model):
            det_brand = self.detect_brand_from_model(chosen_model)
            if det_brand and (not cb_cat.get() or cb_cat.get() not in self.BRAND_LIST):
                cb_cat.set(det_brand)

        self.attach_autocomplete(
            ent_model,
            lambda: self.get_model_suggestions_for_brand(cb_cat.get()),
            next_focus_widget=cb_storage,
            on_chosen_callback=on_buy_model_chosen
        )

        def add_fin_lbl(r_i, txt):
            tk.Label(fin_card, text=txt, bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=r_i, column=1, sticky="e", padx=8, pady=8)

        add_fin_lbl(0, "المورد:")
        supp_row = tk.Frame(fin_card, bg=self.COLOR_CARD)
        supp_row.grid(row=0, column=0, sticky="ew", padx=8, pady=8)

        cb_supp = ttk.Combobox(supp_row, state="readonly", font=("Segoe UI", 11, "bold"), justify="right")
        cb_supp.pack(side="right", fill="x", expand=True, ipady=3)

        suppliers_map = {}

        def refresh_suppliers_combo(selected_id=None):
            suppliers_map.clear()
            s_list = self.db.get_suppliers(active_only=True)
            display_vals = []
            target_idx = 0
            for idx_s, s in enumerate(s_list):
                label = f"{s['name']} ({s.get('supplier_type', 'تاجر')})"
                suppliers_map[label] = s['id']
                display_vals.append(label)
                if selected_id and s['id'] == selected_id:
                    target_idx = idx_s
            cb_supp['values'] = display_vals
            if display_vals:
                cb_supp.current(target_idx)

        refresh_suppliers_combo()

        add_fin_lbl(1, "سعر الشراء (ج.م):")
        ent_buy_price = tk.Entry(fin_card, validate="key", validatecommand=self.vcmd_num, font=("Segoe UI", 12, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_ACCENT, insertbackground=self.COLOR_TEXT, justify="center")
        ent_buy_price.grid(row=1, column=0, sticky="ew", padx=8, pady=8, ipady=4)

        add_fin_lbl(2, "سعر البيع المبدئي *:")
        ent_init_selling_price = tk.Entry(fin_card, validate="key", validatecommand=self.vcmd_num, font=("Segoe UI", 12, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="center")
        ent_init_selling_price.grid(row=2, column=0, sticky="ew", padx=8, pady=8, ipady=4)

        add_fin_lbl(3, "المدفوع للمورد (ج.م):")
        paid_row = tk.Frame(fin_card, bg=self.COLOR_CARD)
        paid_row.grid(row=3, column=0, sticky="ew", padx=8, pady=8)

        ent_paid = tk.Entry(paid_row, validate="key", validatecommand=self.vcmd_num, font=("Segoe UI", 12, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="center")
        ent_paid.pack(side="right", fill="x", expand=True, ipady=4)

        def fill_full_supplier_paid():
            bp = ent_buy_price.get().strip()
            if bp:
                ent_paid.delete(0, tk.END)
                ent_paid.insert(0, bp)
                update_supp_rem()
                ent_notes.focus_set()

        tk.Button(
            paid_row, text="دفع كامل", command=fill_full_supplier_paid,
            bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 9, "bold"),
            padx=10, pady=4, relief="flat", cursor="hand2"
        ).pack(side="left", padx=(0, 6))

        add_fin_lbl(4, "المتبقي للمورد (أجل):")
        lbl_supp_rem = tk.Label(fin_card, text=fmt_curr(0), font=("Segoe UI", 12, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_WARN, pady=5)
        lbl_supp_rem.grid(row=4, column=0, sticky="ew", padx=8, pady=8)

        add_fin_lbl(5, "ملاحظات الشراء:")
        ent_notes = tk.Entry(fin_card, font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="right")
        ent_notes.grid(row=5, column=0, sticky="ew", padx=8, pady=8, ipady=4)

        last_buy_price_tracked = [""]

        def on_buy_price_typing(event=None):
            bp_val = ent_buy_price.get().strip()
            cur_p = ent_paid.get().strip()
            if not cur_p or cur_p == last_buy_price_tracked[0]:
                ent_paid.delete(0, tk.END)
                ent_paid.insert(0, bp_val)
            last_buy_price_tracked[0] = bp_val
            update_supp_rem()

        def update_supp_rem(event=None):
            try:
                bp = float(ent_buy_price.get().strip() or 0)
            except ValueError:
                bp = 0.0
            raw_p = ent_paid.get().strip()
            try:
                pd = float(raw_p) if raw_p != "" else bp
            except ValueError:
                pd = bp
            rem = max(0.0, bp - pd)
            lbl_supp_rem.config(
                text=fmt_curr(rem),
                fg=self.COLOR_DANGER if rem > 0 else self.COLOR_ACCENT
            )

        ent_buy_price.bind("<KeyRelease>", on_buy_price_typing)
        ent_paid.bind("<KeyRelease>", update_supp_rem)

        def save_device_action():
            cat_val = cb_cat.get().strip()
            mod_val = ent_model.get().strip()
            st_val = cb_storage.get().strip()
            rm_val = cb_ram.get().strip()
            bat_raw = ent_bat.get().strip()
            imei_val = ent_imei.get().strip()
            cond_val = cb_cond.get().strip()
            color_val = cb_color.get().strip() or "أسود"
            if color_val == "بدون":
                color_val = "أسود"
            tax_val = tax_var.get()
            supp_label = cb_supp.get()
            supp_id = suppliers_map.get(supp_label)

            if not cat_val or not mod_val or not imei_val:
                messagebox.showwarning("تنبيه", "يرجى إدخال الماركة والموديل والسيريال (IMEI)!")
                if not mod_val:
                    ent_model.focus_set()
                else:
                    ent_imei.focus_set()
                return

            if not supp_id:
                messagebox.showwarning("تنبيه", "يرجى اختيار المورد أولاً!")
                return

            try:
                buy_price = float(ent_buy_price.get().strip() or 0)
            except ValueError:
                buy_price = 0.0

            if buy_price <= 0:
                messagebox.showwarning("تنبيه", "يرجى إدخال سعر الشراء بشكل صحيح!")
                ent_buy_price.focus_set()
                return

            raw_init_sp = ent_init_selling_price.get().strip()
            if not raw_init_sp:
                messagebox.showwarning("تنبيه", "سعر البيع المبدئي حقل إجباري! يرجى إدخال سعر البيع المتوقع للجهاز.")
                ent_init_selling_price.focus_set()
                return

            try:
                init_sp_val = float(raw_init_sp)
            except ValueError:
                init_sp_val = 0.0

            if init_sp_val <= 0:
                messagebox.showwarning("تنبيه", "يرجى إدخال سعر بيع مبدئي أكبر من الصفر!")
                ent_init_selling_price.focus_set()
                return

            if init_sp_val < buy_price:
                messagebox.showwarning(
                    "⚠️ تنبيه أمان مالي",
                    f"لا يمكن أن يكون سعر البيع المبدئي ({fmt_curr(init_sp_val)}) أقل من سعر الشراء ({fmt_curr(buy_price)})!\n"
                    "يرجى تحديد سعر بيع مبدئي يغطي سعر التكلفة على الأقل."
                )
                ent_init_selling_price.focus_set()
                return

            raw_paid = ent_paid.get().strip()
            try:
                paid_amount = float(raw_paid) if raw_paid != "" else buy_price
            except ValueError:
                paid_amount = buy_price

            if paid_amount > buy_price:
                messagebox.showwarning("تنبيه", "المبلغ المدفوع للمورد لا يمكن أن يتجاوز سعر الشراء!")
                ent_paid.focus_set()
                return

            rem_supplier = max(0.0, buy_price - paid_amount)

            confirm_msg = (
                f"هل أنت متأكد من حفظ وإضافة الجهاز للمخزون؟\n\n"
                f"• الجهاز: {cat_val} {mod_val}\n"
                f"• السيريال: {imei_val}\n"
                f"• اللون: {color_val}  |  العلبة: {'بعلبة' if box_var.get() else 'بدون علبة'}\n"
                f"• الضريبة: {'خاضع' if tax_val else 'بدون'}\n"
                f"• المورد: {supp_label}\n"
                f"• سعر الشراء: {fmt_curr(buy_price)}\n"
                f"• سعر البيع المبدئي: {fmt_curr(init_sp_val)}\n"
                f"• المدفوع للمورد: {fmt_curr(paid_amount)}\n"
                f"• المتبقي أجل: {fmt_curr(rem_supplier)}"
            )
            if not messagebox.askyesno("تأكيد حفظ الشراء", confirm_msg, parent=self):
                return

            bat_val = int(bat_raw) if bat_raw.isdigit() else None

            try:
                buy_custom_dt = get_buy_custom_date()
            except ValueError as val_err:
                messagebox.showerror("خطأ في التاريخ", str(val_err))
                return

            try:
                res = self.db.add_device(
                    category=cat_val,
                    model=mod_val,
                    storage=st_val,
                    battery=bat_val,
                    imei=imei_val,
                    buy_price=buy_price,
                    supplier_id=supp_id,
                    user_id=self.current_user_id,
                    paid_amount=paid_amount,
                    ram=rm_val,
                    device_condition=cond_val,
                    has_box=box_var.get(),
                    notes=ent_notes.get().strip(),
                    color=color_val,
                    has_tax=tax_val,
                    initial_selling_price=init_sp_val,
                    custom_date=buy_custom_dt
                )
                dev_id = res['device_id'] if isinstance(res, dict) else res
                messagebox.showinfo("تم الإدخال بنجاح", f"تم إضافة الجهاز #{dev_id} ({cat_val} {mod_val}) إلى المخزون بنجاح!")

                ent_model.delete(0, tk.END)
                cb_ram.set("")
                ent_bat.delete(0, tk.END)
                ent_imei.delete(0, tk.END)
                ent_buy_price.delete(0, tk.END)
                ent_init_selling_price.delete(0, tk.END)
                ent_paid.delete(0, tk.END)
                ent_notes.delete(0, tk.END)
                cb_color.set("أسود")
                box_var.set(False)
                tax_var.set(False)
                last_buy_price_tracked[0] = ""
                update_supp_rem()
                ent_model.focus_set()
            except Exception as ex:
                messagebox.showerror("خطأ في الإدخال", str(ex))

        self._bind_enter_chain(
            [cb_cat, ent_model, cb_storage, cb_ram, ent_bat, cb_color, cb_cond, chk_box, chk_tax, ent_imei, cb_supp, ent_buy_price, ent_init_selling_price, ent_paid, ent_notes],
            final_callback=save_device_action
        )

        btn_save_holder = tk.Frame(fin_card, bg=self.COLOR_CARD, pady=12)
        btn_save_holder.grid(row=5, column=0, columnspan=2, sticky="ew")

        tk.Button(
            btn_save_holder, text="💾 حفظ وإضافة للمخزون (Enter)", command=save_device_action,
            bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 12, "bold"),
            padx=24, pady=8, relief="flat", cursor="hand2"
        ).pack(fill="x", padx=8)

        ent_model.focus_set()

    def open_quick_add_supplier_modal(self, on_added_callback=None):
        swin = tk.Toplevel(self)
        swin.title("إضافة مورد جديد")
        swin.geometry("440x320")
        swin.configure(bg=self.COLOR_CARD)
        swin.resizable(False, False)
        swin.grab_set()

        top_bar = tk.Frame(swin, bg=self.COLOR_TOPBAR, pady=10, padx=14)
        top_bar.pack(fill="x")
        tk.Label(top_bar, text="➕ إضافة مورد جديد", font=("Segoe UI", 12, "bold"), bg=self.COLOR_TOPBAR, fg="#38bdf8").pack(side="right")

        body = tk.Frame(swin, bg=self.COLOR_CARD, padx=18, pady=14)
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=1)

        tk.Label(body, text="اسم المورد:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky="e", padx=6, pady=8)
        ent_name = tk.Entry(body, font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="right")
        ent_name.grid(row=0, column=0, sticky="ew", padx=6, pady=8, ipady=3)
        ent_name.focus_set()

        tk.Label(body, text="رقم الهاتف:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=1, column=1, sticky="e", padx=6, pady=8)
        ent_phone = tk.Entry(body, font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="center")
        ent_phone.grid(row=1, column=0, sticky="ew", padx=6, pady=8, ipady=3)

        tk.Label(body, text="النوع:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=2, column=1, sticky="e", padx=6, pady=8)
        cb_type = ttk.Combobox(body, values=["تاجر", "زبون"], state="readonly", font=("Segoe UI", 10, "bold"), justify="right")
        cb_type.current(0)
        cb_type.grid(row=2, column=0, sticky="ew", padx=6, pady=8, ipady=2)

        def save_supp():
            nm = ent_name.get().strip()
            ph = ent_phone.get().strip()
            tp = cb_type.get().strip() or "تاجر"
            if not nm:
                messagebox.showwarning("تنبيه", "يرجى إدخال اسم المورد!", parent=swin)
                return
            try:
                new_id = self.db.add_supplier(nm, ph, tp, user_id=self.current_user_id)
                swin.destroy()
                if on_added_callback:
                    on_added_callback(new_id)
            except Exception as ex:
                messagebox.showerror("خطأ", str(ex), parent=swin)

        self._bind_enter_chain([ent_name, ent_phone], final_callback=save_supp)

        btn_bar = tk.Frame(swin, bg=self.COLOR_TOPBAR, pady=8, padx=14)
        btn_bar.pack(fill="x", side="bottom")
        tk.Button(btn_bar, text="💾 حفظ المورد", command=save_supp, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"), padx=18, pady=4, relief="flat", cursor="hand2").pack(side="right", padx=4)
        tk.Button(btn_bar, text="إلغاء", command=swin.destroy, bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 10, "bold"), padx=14, pady=4, relief="flat", cursor="hand2").pack(side="left", padx=4)

    def open_manage_suppliers_modal(self, on_close_callback=None):
        mwin = tk.Toplevel(self)
        mwin.title("إدارة بيانات الموردين")
        mwin.geometry("760x540")
        mwin.configure(bg=self.COLOR_BG)
        mwin.grab_set()

        def on_closing():
            mwin.destroy()
            if on_close_callback:
                on_close_callback()

        mwin.protocol("WM_DELETE_WINDOW", on_closing)

        top_bar = tk.Frame(mwin, bg=self.COLOR_TOPBAR, pady=10, padx=16)
        top_bar.pack(fill="x")
        tk.Label(top_bar, text="🏭 إدارة بيانات الموردين", font=("Segoe UI", 13, "bold"), bg=self.COLOR_TOPBAR, fg="#38bdf8").pack(side="right")

        form_bar = tk.Frame(mwin, bg=self.COLOR_CARD, padx=14, pady=10)
        form_bar.pack(fill="x", padx=16, pady=8)

        tk.Label(form_bar, text="الاسم:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right", padx=4)
        e_name = tk.Entry(form_bar, font=("Segoe UI", 10, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="right", width=18)
        e_name.pack(side="right", padx=4, ipady=3)

        tk.Label(form_bar, text="الهاتف:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right", padx=4)
        e_phone = tk.Entry(form_bar, font=("Segoe UI", 10, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="center", width=14)
        e_phone.pack(side="right", padx=4, ipady=3)

        tk.Label(form_bar, text="النوع:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right", padx=4)
        cb_tp = ttk.Combobox(form_bar, values=["تاجر", "زبون"], state="readonly", width=9, font=("Segoe UI", 10, "bold"), justify="right")
        cb_tp.current(0)
        cb_tp.pack(side="right", padx=4, ipady=2)

        t_frame = tk.Frame(mwin, bg=self.COLOR_CARD, padx=12, pady=8)
        t_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        cols = ("الحالة", "النوع", "رقم الهاتف", "اسم المورد", "كود")
        stree = ttk.Treeview(t_frame, columns=cols, show="headings")
        self.configure_tree_row_colors(stree)
        for c in cols:
            stree.heading(c, text=c)
            stree.column(c, anchor="center", width=130 if c != "كود" else 70)

        vsb = ttk.Scrollbar(t_frame, orient="vertical", command=stree.yview)
        stree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="left", fill="y")
        stree.pack(side="right", fill="both", expand=True)

        supp_cache = {}

        def load_supps():
            stree.delete(*stree.get_children())
            supp_cache.clear()
            for s in self.db.get_suppliers(active_only=False):
                sid = s['id']
                supp_cache[sid] = s
                st_txt = "نشط 🟢" if s.get('is_active', True) else "مؤرشف 🔴"
                row_tag = 'evenrow' if len(supp_cache) % 2 == 0 else 'oddrow'
                stree.insert("", "end", iid=str(sid), tags=(row_tag,), values=(
                    fix_bidi(st_txt),
                    fix_bidi(s.get('supplier_type') or "تاجر"),
                    s.get('phone') or "-",
                    fix_bidi(s['name']),
                    f"#{sid}"
                ))

        def on_sel_supp(event=None):
            sel = stree.selection()
            if not sel:
                return
            s = supp_cache.get(clean_id_val(sel[0]))
            if s:
                e_name.delete(0, tk.END)
                e_name.insert(0, s['name'])
                e_phone.delete(0, tk.END)
                e_phone.insert(0, s.get('phone') or '')
                cb_tp.set(s.get('supplier_type') or "تاجر")

        stree.bind("<<TreeviewSelect>>", on_sel_supp)

        def add_new_s():
            nm = e_name.get().strip()
            if not nm:
                messagebox.showwarning("تنبيه", "يرجى إدخال اسم المورد!", parent=mwin)
                return
            self.db.add_supplier(nm, e_phone.get().strip(), cb_tp.get(), user_id=self.current_user_id)
            e_name.delete(0, tk.END)
            e_phone.delete(0, tk.END)
            load_supps()

        def update_sel_s():
            sel = stree.selection()
            if not sel:
                messagebox.showwarning("تنبيه", "يرجى تحديد مورد من الجدول!", parent=mwin)
                return
            sid = clean_id_val(sel[0])
            nm = e_name.get().strip()
            if not nm:
                return
            self.db.update_supplier(sid, nm, e_phone.get().strip(), cb_tp.get(), user_id=self.current_user_id)
            load_supps()

        def toggle_archive_s():
            sel = stree.selection()
            if not sel:
                return
            sid = clean_id_val(sel[0])
            s = supp_cache.get(sid)
            if not s:
                return
            if s.get('is_active', True):
                self.db.archive_supplier(sid, user_id=self.current_user_id)
            else:
                self.db.restore_supplier(sid, user_id=self.current_user_id)
            load_supps()

        tk.Button(form_bar, text="➕ إضافة", command=add_new_s, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 9, "bold"), padx=12, pady=3, relief="flat", cursor="hand2").pack(side="right", padx=3)
        tk.Button(form_bar, text="💾 حفظ التعديل", command=update_sel_s, bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 9, "bold"), padx=12, pady=3, relief="flat", cursor="hand2").pack(side="right", padx=3)
        tk.Button(form_bar, text="🔄 تفعيل/أرشفة", command=toggle_archive_s, bg=self.COLOR_WARN, fg="#111", font=("Segoe UI", 9, "bold"), padx=10, pady=3, relief="flat", cursor="hand2").pack(side="right", padx=3)

        bot_bar = tk.Frame(mwin, bg=self.COLOR_TOPBAR, pady=8, padx=16)
        bot_bar.pack(fill="x", side="bottom")
        tk.Button(bot_bar, text="إغلاق", command=on_closing, bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 10, "bold"), padx=18, pady=4, relief="flat", cursor="hand2").pack(side="left")

        load_supps()

    def view_customer_debts(self):
        if not self.has_permission('can_view_customer_debts'):
            messagebox.showerror("صلاحيات غير كافية", "عفواً، لا تملك صلاحية عرض ديون العملاء!")
            return

        self.current_view_func = self.view_customer_debts
        self.build_main_ui(keep_view=True)
        self.clear_content()

        top_hdr = tk.Frame(self.content_frame, bg=self.COLOR_BG, padx=18, pady=8)
        top_hdr.pack(fill="x")

        tk.Label(
            top_hdr, text="💳 ديون العملاء ومتابعة التحصيل (الخرج)",
            font=("Segoe UI", 16, "bold"), bg=self.COLOR_BG, fg=self.COLOR_WARN
        ).pack(side="right")

        lbl_total_debt = tk.Label(
            top_hdr, text="إجمالي الخرج المتبقي: 0.00 ج.م",
            bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 11, "bold"), padx=14, pady=5
        )
        lbl_total_debt.pack(side="left")

        ctrl_bar = tk.Frame(self.content_frame, bg=self.COLOR_CARD, padx=14, pady=10)
        ctrl_bar.pack(fill="x", padx=18, pady=(0, 8))

        tk.Label(ctrl_bar, text="🔍 البحث بـ:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right", padx=(4, 2))
        debt_search_type_cb = ttk.Combobox(ctrl_bar, values=["الكل (شامل)", "اسم العميل", "رقم الهاتف", "سيريال IMEI", "رقم الفاتورة #ID", "الجهاز والموديل"], state="readonly", width=14, font=("Segoe UI", 10, "bold"), justify="right")
        debt_search_type_cb.current(0)
        debt_search_type_cb.pack(side="right", padx=(0, 6), ipady=2)

        search_ent = tk.Entry(ctrl_bar, font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="right", width=22)
        search_ent.pack(side="right", padx=6, ipady=3)

        if self.has_permission('can_collect_customer_debt'):
            tk.Button(
                ctrl_bar, text="💵 تحصيل دفعة", command=lambda: open_collect_modal(),
                bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"),
                padx=16, pady=5, relief="flat", cursor="hand2", activebackground="#047857", activeforeground="#ffffff"
            ).pack(side="right", padx=5)

        tk.Button(
            ctrl_bar, text="📱 بيانات الجهاز والدفعات", command=lambda: open_debt_device_details(),
            bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold"),
            padx=14, pady=5, relief="flat", cursor="hand2", activebackground="#0284c7", activeforeground="#ffffff"
        ).pack(side="right", padx=5)

        if self.has_permission('can_print_customer_debt'):
            tk.Button(
                ctrl_bar, text="🖨️ طباعة كشف العميل", command=lambda: print_customer_debt_statement(),
                bg=self.COLOR_PURPLE, fg="white", font=("Segoe UI", 10, "bold"),
                padx=14, pady=5, relief="flat", cursor="hand2", activebackground="#6d28d9", activeforeground="#ffffff"
            ).pack(side="right", padx=5)

        tk.Button(
            ctrl_bar, text="🔄 تحديث", command=lambda: refresh_debts(),
            bg=self.COLOR_TEAL, fg="white", font=("Segoe UI", 10, "bold"),
            padx=14, pady=5, relief="flat", cursor="hand2", activebackground="#0f766e", activeforeground="#ffffff"
        ).pack(side="left", padx=5)

        t_frame = tk.Frame(self.content_frame, bg=self.COLOR_BG)
        t_frame.pack(fill="both", expand=True, padx=18, pady=(0, 14))

        top_inv_card = tk.LabelFrame(
            t_frame, text="📋 سجل فواتير ومديونيات العملاء (اختر فاتورة لعرض أجهزتها بالأسفل)",
            bg=self.COLOR_CARD, fg=self.COLOR_BLUE, font=("Segoe UI", 10, "bold"), padx=10, pady=8
        )
        top_inv_card.pack(fill="both", expand=True, pady=(0, 8))

        cols = (
            "تاريخ البيع", "المتبقي (الخرج)", "المدفوع", "سعر البيع",
            "السيريال IMEI", "الجهاز", "هاتف العميل", "اسم العميل", "ID الجهاز", "رقم الفاتورة"
        )
        dtree = ttk.Treeview(top_inv_card, columns=cols, show="headings", height=7)
        self.configure_tree_row_colors(dtree)
        d_widths = {
            "تاريخ البيع": 130, "المتبقي (الخرج)": 125, "المدفوع": 115, "سعر البيع": 115,
            "السيريال IMEI": 140, "الجهاز": 160, "هاتف العميل": 115, "اسم العميل": 160,
            "ID الجهاز": 80, "رقم الفاتورة": 85
        }
        for c in cols:
            dtree.heading(c, text=c)
            dtree.column(c, anchor="center", width=d_widths.get(c, 110))

        vsb = ttk.Scrollbar(top_inv_card, orient="vertical", command=dtree.yview)
        hsb = ttk.Scrollbar(top_inv_card, orient="horizontal", command=dtree.xview)
        dtree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="left", fill="y")
        hsb.pack(side="bottom", fill="x")
        dtree.pack(side="right", fill="both", expand=True)

        self.bind_treeview_double_click(dtree, target_column_name="ID الجهاز")

        bot_dev_card = tk.LabelFrame(
            t_frame, text="📱 الأجهزة والبيانات المرتبطة بالفاتورة المحددة",
            bg=self.COLOR_CARD, fg=self.COLOR_ACCENT, font=("Segoe UI", 10, "bold"), padx=10, pady=8
        )
        bot_dev_card.pack(fill="both", expand=True)

        bot_info_bar = tk.Frame(bot_dev_card, bg=self.COLOR_CARD)
        bot_info_bar.pack(fill="x", pady=(0, 4))
        lbl_sel_debt_info = tk.Label(
            bot_info_bar, text="👈 حدد فاتورة من الجدول أعلاه لعرض تفاصيل أجهزتها والدفعات",
            font=("Segoe UI", 10, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_MUTED
        )
        lbl_sel_debt_info.pack(side="right")

        dev_cols = (
            "المتبقي (الخرج)", "سعر البيع", "الحالة", "المساحة", "السيريال IMEI", "الموديل", "الماركة", "كود الجهاز"
        )
        cust_dev_tree = ttk.Treeview(bot_dev_card, columns=dev_cols, show="headings", height=4)
        self.configure_tree_row_colors(cust_dev_tree)
        cd_widths = {
            "المتبقي (الخرج)": 120, "سعر البيع": 115, "الحالة": 105,
            "المساحة": 95, "السيريال IMEI": 135, "الموديل": 140, "الماركة": 110, "كود الجهاز": 85
        }
        for dc in dev_cols:
            cust_dev_tree.heading(dc, text=dc)
            cust_dev_tree.column(dc, anchor="center", width=cd_widths.get(dc, 110))

        cd_vsb = ttk.Scrollbar(bot_dev_card, orient="vertical", command=cust_dev_tree.yview)
        cust_dev_tree.configure(yscrollcommand=cd_vsb.set)
        cd_vsb.pack(side="left", fill="y")
        cust_dev_tree.pack(side="right", fill="both", expand=True)

        self.bind_treeview_double_click(cust_dev_tree, target_column_name="كود الجهاز")

        debts_map = {}

        def on_debt_select(event=None):
            cust_dev_tree.delete(*cust_dev_tree.get_children())
            sel = dtree.selection()
            if not sel:
                lbl_sel_debt_info.config(text="👈 حدد فاتورة من الجدول أعلاه لعرض تفاصيل أجهزتها والدفعات", fg=self.COLOR_MUTED)
                return
            d = debts_map.get(clean_id_val(sel[0]))
            if not d:
                return

            dev_id = d.get('device_id')
            full_info = self.db.get_device_full_details(dev_id) if dev_id else None
            dev_obj = (full_info.get('device') if full_info else None) or d
            
            rem = float(d.get('remaining_balance') or 0)
            raw_st = str(dev_obj.get('storage') or '-').replace('GB', '').strip()
            storage_str = f"{raw_st} GB" if (raw_st and raw_st != "-") else "-"
            cond_str = dev_obj.get('device_condition') or "مستعمل"

            row_tag = 'evenrow' if len(cust_dev_tree.get_children()) % 2 == 0 else 'oddrow'
            cust_dev_tree.insert("", "end", iid=str(dev_id or 'd1'), tags=(row_tag,), values=(
                fmt_curr(rem),
                fmt_curr(d.get('sell_price')),
                fix_bidi(cond_str),
                fix_bidi(storage_str),
                dev_obj.get('imei_serial') or "-",
                fix_bidi(dev_obj.get('model') or "-"),
                fix_bidi(dev_obj.get('category') or "-"),
                f"#{dev_id}" if dev_id else "-"
            ))

            lbl_sel_debt_info.config(
                text=fix_bidi(f"📌 الفاتورة #{d['sale_id']} | العميل: {d.get('customer_name')} ({d.get('customer_phone') or 'بدون هاتف'}) | إجمالي المتبقي: {fmt_curr(rem)}"),
                fg=self.COLOR_WARN if rem > 0 else self.COLOR_ACCENT
            )

        dtree.bind("<<TreeviewSelect>>", on_debt_select)

        def refresh_debts(event=None):
            dtree.delete(*dtree.get_children())
            debts_map.clear()
            all_debts = self.db.get_customer_debts()
            total_rem = sum(float(d.get('remaining_balance') or 0) for d in all_debts)
            lbl_total_debt.config(text=f"إجمالي الخرج المتبقي: {fmt_curr(total_rem)}")

            q = search_ent.get().strip().lower()
            stype = debt_search_type_cb.get()
            for d in all_debts:
                dev_title = f"{d.get('category') or ''} {d.get('model') or ''}".strip()
                if q:
                    if "العميل" in stype:
                        if q not in str(d.get('customer_name') or '').lower():
                            continue
                    elif "الهاتف" in stype:
                        if q not in str(d.get('customer_phone') or '').lower():
                            continue
                    elif "سيريال" in stype:
                        if q not in str(d.get('imei_serial') or '').lower():
                            continue
                    elif "الفاتورة" in stype or "#ID" in stype:
                        clean_q = clean_id_val(q)
                        if clean_q is None or (d.get('sale_id') != clean_q and d.get('device_id') != clean_q):
                            continue
                    elif "الجهاز" in stype or "الموديل" in stype:
                        if q not in dev_title.lower():
                            continue
                    else:
                        searchable = f"{d.get('sale_id')} {d.get('device_id')} {d.get('customer_name')} {d.get('customer_phone')} {dev_title} {d.get('imei_serial')}".lower()
                        if q not in searchable:
                            continue

                sid = d['sale_id']
                debts_map[sid] = d
                row_tag = 'evenrow' if len(debts_map) % 2 == 0 else 'oddrow'
                dtree.insert("", "end", iid=str(sid), tags=(row_tag,), values=(
                    d.get('sell_date_formatted') or "-",
                    fmt_curr(d.get('remaining_balance')),
                    fmt_curr(d.get('cash_received')),
                    fmt_curr(d.get('sell_price')),
                    d.get('imei_serial') or "-",
                    fix_bidi(dev_title),
                    d.get('customer_phone') or "-",
                    fix_bidi(d.get('customer_name') or "-"),
                    f"#{d['device_id']}",
                    f"#{sid}"
                ))

            self.after(50, lambda: dtree.xview_moveto(1.0))

        def get_sel_debt():
            sel = dtree.selection()
            if not sel:
                messagebox.showwarning("تنبيه", "يرجى تحديد مديونية عميل من الجدول أولاً!")
                return None
            return debts_map.get(clean_id_val(sel[0]))

        def open_debt_device_details():
            d = get_sel_debt()
            if d:
                self.show_device_details_modal(d['device_id'])

        def open_collect_modal():
            d = get_sel_debt()
            if not d:
                return
            rem_val = float(d.get('remaining_balance') or 0)

            cwin = tk.Toplevel(self)
            cwin.title(f"تحصيل دفعة - {d['customer_name']}")
            cwin.geometry("460x360")
            cwin.configure(bg=self.COLOR_CARD)
            cwin.resizable(False, False)
            cwin.grab_set()

            top_b = tk.Frame(cwin, bg=self.COLOR_TOPBAR, pady=10, padx=14)
            top_b.pack(fill="x")
            tk.Label(top_b, text=fix_bidi(f"💵 تحصيل دفعة من: {d['customer_name']}"), font=("Segoe UI", 12, "bold"), bg=self.COLOR_TOPBAR, fg=self.COLOR_ACCENT).pack(side="right")

            body = tk.Frame(cwin, bg=self.COLOR_CARD, padx=18, pady=10)
            body.pack(fill="both", expand=True)

            tk.Label(body, text=f"المبلغ المتبقي حالياً: {fmt_curr(rem_val)}", font=("Segoe UI", 12, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_WARN).pack(pady=(0, 8))

            row_in = tk.Frame(body, bg=self.COLOR_CARD)
            row_in.pack(fill="x", pady=4)
            tk.Label(row_in, text="المبلغ المحصل (ج.م):", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right", padx=6)
            ent_amt = tk.Entry(row_in, validate="key", validatecommand=self.vcmd_num, font=("Segoe UI", 12, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_ACCENT, insertbackground=self.COLOR_TEXT, justify="center", width=16)
            ent_amt.insert(0, fmt_num(rem_val))
            ent_amt.pack(side="right", padx=6, ipady=4)
            ent_amt.focus_set()
            ent_amt.select_range(0, tk.END)

            get_collect_custom_date = self._create_operation_date_picker(body, label_text="تاريخ التحصيل:")

            def confirm_collect():
                try:
                    amt = float(ent_amt.get().strip() or 0)
                except ValueError:
                    amt = 0.0
                if amt <= 0 or amt > rem_val:
                    messagebox.showwarning("تنبيه", "يرجى إدخال مبلغ صحيح لا يتجاوز المتبقي على العميل!", parent=cwin)
                    return
                try:
                    c_dt = get_collect_custom_date()
                except ValueError as err_dt:
                    messagebox.showerror("خطأ في التاريخ", str(err_dt), parent=cwin)
                    return
                try:
                    self.db.collect_debt_installment(d['sale_id'], amt, self.current_user_id, custom_date=c_dt)
                    messagebox.showinfo("تم التحصيل", f"تم تحصيل {fmt_curr(amt)} بنجاح!", parent=cwin)
                    cwin.destroy()
                    refresh_debts()
                except Exception as ex:
                    messagebox.showerror("خطأ", str(ex), parent=cwin)

            ent_amt.bind("<Return>", lambda e: confirm_collect())

            bot_b = tk.Frame(cwin, bg=self.COLOR_TOPBAR, pady=8, padx=14)
            bot_b.pack(fill="x", side="bottom")
            tk.Button(bot_b, text="✅ تأكيد التحصيل (Enter)", command=confirm_collect, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"), padx=18, pady=4, relief="flat", cursor="hand2").pack(side="right", padx=4)
            tk.Button(bot_b, text="إلغاء", command=cwin.destroy, bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 10, "bold"), padx=14, pady=4, relief="flat", cursor="hand2").pack(side="left", padx=4)

        def print_customer_debt_statement():
            d = get_sel_debt()
            if not d:
                return
            full_info = self.db.get_device_full_details(d['device_id'])
            dev_obj = full_info.get('device') or d
            payments_list = full_info.get('customer_payments', [])
            inv_data = {
                'doc_type': 'CUSTOMER_DEBT',
                'sale_id': d['sale_id'],
                'customer_name': d['customer_name'],
                'customer_phone': d.get('customer_phone') or '-',
                'seller_name': d.get('seller_name') or '',
                'device': dev_obj,
                'original_price': float(d.get('sell_price') or 0),
                'discount': 0.0,
                'sell_price': float(d.get('sell_price') or 0),
                'cash_received': float(d.get('cash_received') or 0),
                'remaining_balance': float(d.get('remaining_balance') or 0),
                'sale_notes': d.get('notes') or '',
                'payments_list': payments_list,
                'date_str': d.get('sell_date_formatted') or ''
            }
            self.open_invoice_preview_and_print(inv_data, f"كشف حساب عميل - فاتورة #{d['sale_id']}")

        search_ent.bind("<KeyRelease>", refresh_debts)
        debt_search_type_cb.bind("<<ComboboxSelected>>", refresh_debts)
        refresh_debts()

    def view_supplier_debts(self):
        if not self.has_permission('can_view_supplier_debts'):
            messagebox.showerror("صلاحيات غير كافية", "عفواً، لا تملك صلاحية عرض حسابات الموردين!")
            return

        self.current_view_func = self.view_supplier_debts
        self.build_main_ui(keep_view=True)
        self.clear_content()

        top_hdr = tk.Frame(self.content_frame, bg=self.COLOR_BG, padx=18, pady=8)
        top_hdr.pack(fill="x")

        tk.Label(
            top_hdr, text="🏭 حسابات وفواتير الموردين",
            font=("Segoe UI", 16, "bold"), bg=self.COLOR_BG, fg=self.COLOR_TEAL
        ).pack(side="right")

        supp_stats_frame = tk.Frame(top_hdr, bg=self.COLOR_BG)
        supp_stats_frame.pack(side="left")

        lbl_total_supp_debt = tk.Label(
            supp_stats_frame, text="إجمالي مديونية الموردين: 0.00 ج.م",
            bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 11, "bold"), padx=14, pady=4
        )
        lbl_total_supp_debt.pack(side="top", fill="x")

        lbl_total_supp_credit = tk.Label(
            supp_stats_frame, text="★ لنا رصيد دائن لدى الموردين: 0.00 ج.م",
            bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"), padx=14, pady=3
        )
        lbl_total_supp_credit.pack(side="top", fill="x", pady=(3, 0))

        filter_bar = tk.Frame(self.content_frame, bg=self.COLOR_CARD, padx=14, pady=10)
        filter_bar.pack(fill="x", padx=18, pady=(0, 8))

        row_f1 = tk.Frame(filter_bar, bg=self.COLOR_CARD)
        row_f1.pack(fill="x", pady=(0, 6))

        tk.Label(row_f1, text="🔍 البحث بـ:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right", padx=(4, 2))
        supp_search_type_cb = ttk.Combobox(row_f1, values=["الكل (شامل)", "اسم المورد", "رقم الفاتورة #ID", "هاتف المورد"], state="readonly", width=13, font=("Segoe UI", 10, "bold"), justify="right")
        supp_search_type_cb.current(0)
        supp_search_type_cb.pack(side="right", padx=(0, 6), ipady=2)

        supp_search_ent = tk.Entry(row_f1, font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="right", width=18)
        supp_search_ent.pack(side="right", padx=6, ipady=3)

        tk.Label(row_f1, text="المورد:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right", padx=(10, 4))
        supp_filter_cb = ttk.Combobox(row_f1, state="readonly", width=16, font=("Segoe UI", 10, "bold"), justify="right")
        supp_filter_cb.pack(side="right", padx=4, ipady=2)

        tk.Label(row_f1, text="حالة الفاتورة:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right", padx=(10, 4))
        st_filter_cb = ttk.Combobox(row_f1, values=["الكل", "متبقي (غير خالص)", "خالص"], state="readonly", width=14, font=("Segoe UI", 10, "bold"), justify="right")
        st_filter_cb.current(0)
        st_filter_cb.pack(side="right", padx=4, ipady=2)

        row_f2 = tk.Frame(filter_bar, bg=self.COLOR_CARD)
        row_f2.pack(fill="x", pady=(2, 0))

        tk.Label(row_f2, text="📅 من تاريخ:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right", padx=(4, 2))
        ent_supp_date_from = tk.Entry(row_f2, font=("Segoe UI", 10, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, justify="center", width=12)
        today_str = datetime.now().strftime("%Y-%m-%d")
        ent_supp_date_from.insert(0, today_str)
        ent_supp_date_from.pack(side="right", padx=2, ipady=2)
        tk.Button(row_f2, text="📅", command=lambda: self.open_date_picker(ent_supp_date_from, refresh_supplier_page, allow_future=False), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_BLUE, relief="flat", cursor="hand2").pack(side="right", padx=2)

        tk.Label(row_f2, text="إلى تاريخ:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right", padx=(8, 2))
        ent_supp_date_to = tk.Entry(row_f2, font=("Segoe UI", 10, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, justify="center", width=12)
        ent_supp_date_to.insert(0, today_str)
        ent_supp_date_to.pack(side="right", padx=2, ipady=2)
        tk.Button(row_f2, text="📅", command=lambda: self.open_date_picker(ent_supp_date_to, refresh_supplier_page, allow_future=False), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_BLUE, relief="flat", cursor="hand2").pack(side="right", padx=2)

        def set_supp_today():
            now_d = datetime.now().strftime("%Y-%m-%d")
            ent_supp_date_from.delete(0, tk.END)
            ent_supp_date_from.insert(0, now_d)
            ent_supp_date_to.delete(0, tk.END)
            ent_supp_date_to.insert(0, now_d)
            refresh_supplier_page()

        def set_supp_month():
            now = datetime.now()
            ent_supp_date_from.delete(0, tk.END)
            ent_supp_date_from.insert(0, now.strftime("%Y-%m-01"))
            ent_supp_date_to.delete(0, tk.END)
            ent_supp_date_to.insert(0, now.strftime("%Y-%m-%d"))
            refresh_supplier_page()

        def clear_supp_dates():
            ent_supp_date_from.delete(0, tk.END)
            ent_supp_date_to.delete(0, tk.END)
            refresh_supplier_page()

        tk.Button(row_f2, text="اليوم", command=set_supp_today, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", padx=6, pady=2).pack(side="right", padx=2)
        tk.Button(row_f2, text="هذا الشهر", command=set_supp_month, bg=self.COLOR_PURPLE, fg="white", font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", padx=6, pady=2).pack(side="right", padx=2)
        tk.Button(row_f2, text="مسح", command=clear_supp_dates, bg=self.COLOR_ENTRY_BG, fg=self.COLOR_MUTED, font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", padx=6, pady=2).pack(side="right", padx=2)

        def print_supplier_period_statement():
            sel_supp_lbl = supp_filter_cb.get()
            target_sid = supp_id_by_label.get(sel_supp_lbl) if (sel_supp_lbl and sel_supp_lbl != "الكل") else None
            d_from = ent_supp_date_from.get().strip() or None
            d_to = ent_supp_date_to.get().strip() or None
            invs = self.db.get_supplier_invoices(supplier_id=target_sid, unpaid_only=False, date_from=d_from, date_to=d_to)
            if not invs:
                messagebox.showinfo("تنبيه", "لا توجد فواتير مسجلة في النطاق الزمني المختار!", parent=self)
                return

            all_period_devs = []
            all_period_pays = []
            tot_amt = 0.0
            tot_paid = 0.0
            tot_rem = 0.0
            tot_cred = 0.0

            for iv in invs:
                tot_amt += float(iv.get('total_amount') or 0)
                tot_paid += float(iv.get('paid_amount') or 0)
                tot_rem += float(iv.get('remaining_amount') or 0)
                tot_cred += float(iv.get('supplier_credit') or 0)
                all_period_devs.extend(self.db.get_devices_by_invoice(iv['id']))
                all_period_pays.extend(self.db.get_supplier_payments_history(iv['id']))

            s_name = sel_supp_lbl if (sel_supp_lbl and sel_supp_lbl != "الكل") else "كافة الموردين (إجمالي شامل)"
            s_phone = invs[0].get('supplier_phone') if (target_sid and invs) else "متعدد"
            date_range_txt = f"{d_from or 'البداية'} إلى {d_to or 'الآن'}"
            inv_data = {
                'doc_type': 'SUPPLIER_INVOICE',
                'invoice_id': f"STMT-{target_sid or 'ALL'}",
                'supplier_name': s_name,
                'supplier_phone': s_phone,
                'supplier_type': 'كشف حساب شامل وتحليلي',
                'total_amount': tot_amt,
                'paid_amount': tot_paid,
                'remaining_amount': tot_rem,
                'supplier_credit': tot_cred,
                'devices_list': all_period_devs,
                'payments_list': all_period_pays,
                'date_str': date_range_txt,
                'custom_terms': f"كشف حساب تحليلي شامل للفترة: {date_range_txt}\nإجمالي الفواتير: {len(invs)} فاتورة | إجمالي المدفوع: {tot_paid:,.2f} ج.م | المتبقي: {tot_rem:,.2f} ج.م | الأجهزة: {len(all_period_devs)}"
            }
            self.open_invoice_preview_and_print(inv_data, f"كشف حساب {s_name} ({date_range_txt})")

        def open_supplier_analytics_modal():
            sel_supp_lbl = supp_filter_cb.get()
            target_sid = supp_id_by_label.get(sel_supp_lbl) if (sel_supp_lbl and sel_supp_lbl != "الكل") else None
            d_from = ent_supp_date_from.get().strip() or None
            d_to = ent_supp_date_to.get().strip() or None
            invs = self.db.get_supplier_invoices(supplier_id=target_sid, unpaid_only=False, date_from=d_from, date_to=d_to)
            
            an_win = tk.Toplevel(self)
            an_win.title("📊 التحليل المالي والبيانات الإجمالية لفواتير الموردين")
            an_win.geometry("820x640")
            an_win.configure(bg=self.COLOR_BG)
            an_win.grab_set()

            top_an = tk.Frame(an_win, bg=self.COLOR_TOPBAR, pady=10, padx=16)
            top_an.pack(fill="x")
            tk.Label(top_an, text="📊 التحليل المالي الشامل لفواتير الموردين", font=("Segoe UI", 13, "bold"), bg=self.COLOR_TOPBAR, fg="#38bdf8").pack(side="right")

            bot_an = tk.Frame(an_win, bg=self.COLOR_TOPBAR, pady=8, padx=16)
            bot_an.pack(side="bottom", fill="x")
            tk.Button(bot_an, text="إغلاق", command=an_win.destroy, bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 10, "bold"), padx=18, pady=4, relief="flat", cursor="hand2").pack(side="left")
            tk.Button(bot_an, text="🖨️ طباعة كشف الحساب التحليلي", command=print_supplier_period_statement, bg=self.COLOR_INDIGO, fg="white", font=("Segoe UI", 10, "bold"), padx=16, pady=4, relief="flat", cursor="hand2").pack(side="right")

            scroll_an = self._create_scrollable_frame(an_win, bg_color=self.COLOR_BG, pad_x=16, pad_y=10)

            tot_amt = sum(float(iv.get('total_amount') or 0) for iv in invs)
            tot_paid = sum(float(iv.get('paid_amount') or 0) for iv in invs)
            tot_rem = sum(float(iv.get('remaining_amount') or 0) for iv in invs)
            tot_cred = sum(float(iv.get('supplier_credit') or 0) for iv in invs)
            paid_invs_count = sum(1 for iv in invs if float(iv.get('remaining_amount') or 0) <= 0)
            unpaid_invs_count = len(invs) - paid_invs_count

            met_frame = tk.LabelFrame(scroll_an, text="📈 المؤشرات المالية للفترة المحددة", bg=self.COLOR_CARD, fg=self.COLOR_BLUE, font=("Segoe UI", 11, "bold"), padx=14, pady=10)
            met_frame.pack(fill="x", pady=6)

            s_name_display = sel_supp_lbl if (sel_supp_lbl and sel_supp_lbl != "الكل") else "كافة الموردين"
            an_pairs = [
                [("المورد المستهدف:", s_name_display), ("الفترة الزمنية:", f"{d_from or 'البداية'} إلى {d_to or 'الآن'}")],
                [("إجمالي الفواتير:", f"{len(invs)} فاتورة"), ("الفواتير الخالصة بالكامل:", f"{paid_invs_count} فاتورة")],
                [("فواتير متبقي عليها آجل:", f"{unpaid_invs_count} فاتورة"), ("إجمالي قيمة المشتريات:", fmt_curr(tot_amt))],
                [("إجمالي المسدد والمدفوع:", fmt_curr(tot_paid)), ("المتبقي مديونية للموردين:", fmt_curr(tot_rem))],
                [("★ رصيد دائن مستحق لنا:", fmt_curr(tot_cred)), ("حالة السداد العامة:", "خالص بالكامل 🟢" if tot_rem <= 0 else "يوجد متبقي آجل 🔴")]
            ]
            self._build_rtl_info_grid(met_frame, an_pairs)

            t_card = tk.LabelFrame(scroll_an, text="📋 تفاصيل فواتير الفترة (مسددة وغير مسددة)", bg=self.COLOR_CARD, fg=self.COLOR_TEAL, font=("Segoe UI", 11, "bold"), padx=12, pady=8)
            t_card.pack(fill="both", expand=True, pady=8)

            t_cols = ("الحالة", "التاريخ", "رصيد دائن", "المتبقي", "المدفوع", "الإجمالي", "المورد", "الفاتورة")
            antree = ttk.Treeview(t_card, columns=t_cols, show="headings", height=8)
            self.configure_tree_row_colors(antree)
            for c in t_cols:
                antree.heading(c, text=c)
                antree.column(c, anchor="center", width=100)
            antree.pack(fill="both", expand=True)

            for idx_a, iv in enumerate(invs, 1):
                rem_v = float(iv.get('remaining_amount') or 0)
                st_t = "خالص 🟢" if rem_v <= 0 else "متبقي 🔴"
                cr_v = float(iv.get('supplier_credit') or 0)
                cr_t = fmt_curr(cr_v) if cr_v > 0 else "-"
                row_tag = 'evenrow' if idx_a % 2 == 0 else 'oddrow'
                antree.insert("", "end", tags=(row_tag,), values=(
                    fix_bidi(st_t),
                    iv.get('date_formatted') or "-",
                    fix_bidi(cr_t),
                    fmt_curr(rem_v),
                    fmt_curr(iv.get('paid_amount')),
                    fmt_curr(iv.get('total_amount')),
                    fix_bidi(iv.get('supplier_name') or "-"),
                    f"#{iv['id']}"
                ))

        tk.Button(row_f2, text="📊 التحليل المالي الشامل", command=open_supplier_analytics_modal, bg=self.COLOR_TEAL, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2", padx=10, pady=2).pack(side="left", padx=4)
        tk.Button(row_f2, text="📄 كشف حساب المورد (شامل)", command=print_supplier_period_statement, bg=self.COLOR_INDIGO, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2", padx=10, pady=2).pack(side="left", padx=4)

        actions_bar = tk.Frame(self.content_frame, bg=self.COLOR_BG, padx=18, pady=4)
        actions_bar.pack(fill="x")

        tk.Button(
            actions_bar, text="📋 تفاصيل الفاتورة والسداد", command=lambda: open_selected_invoice_details(),
            bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold"),
            padx=16, pady=5, relief="flat", cursor="hand2"
        ).pack(side="right", padx=4)

        if self.has_permission('can_pay_supplier_debt'):
            tk.Button(
                actions_bar, text="💵 سداد دفعة للمورد", command=lambda: open_pay_supplier_modal(),
                bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"),
                padx=16, pady=5, relief="flat", cursor="hand2"
            ).pack(side="right", padx=4)

        def open_refund_credit_dialog():
            inv = get_selected_invoice()
            if not inv:
                return
            cred_val = float(inv.get('supplier_credit') or 0.0)
            if cred_val <= 0:
                messagebox.showinfo("تنبيه", "هذه الفاتورة لا تحتوي على رصيد دائن مستحق لنا!")
                return
            supp_name = inv.get('supplier_name') or f"مورد #{inv.get('supplier_id')}"

            rf_win = tk.Toplevel(self)
            rf_win.title("استرداد رصيد المورد نقداً")
            rf_win.geometry("480x350")
            rf_win.configure(bg=self.COLOR_CARD)
            rf_win.resizable(False, False)
            rf_win.grab_set()

            top_r = tk.Frame(rf_win, bg=self.COLOR_TOPBAR, pady=10, padx=14)
            top_r.pack(fill="x")
            tk.Label(top_r, text=fix_bidi(f"💰 استرداد رصيد دائن - {supp_name}"), font=("Segoe UI", 12, "bold"), bg=self.COLOR_TOPBAR, fg=self.COLOR_ACCENT).pack(side="right")

            body_r = tk.Frame(rf_win, bg=self.COLOR_CARD, padx=18, pady=12)
            body_r.pack(fill="both", expand=True)

            tk.Label(body_r, text=f"إجمالي الرصيد الدائن المتاح: {fmt_curr(cred_val)}", font=("Segoe UI", 12, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_ACCENT).pack(pady=(0, 10))

            r_row = tk.Frame(body_r, bg=self.COLOR_CARD)
            r_row.pack(fill="x", pady=6)
            tk.Label(r_row, text="المبلغ المراد استرداده (ج.م):", font=("Segoe UI", 10, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_TEXT).pack(side="right", padx=6)
            ent_ref_amt = tk.Entry(r_row, validate="key", validatecommand=self.vcmd_num, font=("Segoe UI", 12, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_ACCENT, insertbackground=self.COLOR_TEXT, justify="center", width=14)
            ent_ref_amt.insert(0, fmt_num(cred_val))
            ent_ref_amt.pack(side="right", padx=4, ipady=3)

            def set_full_ref():
                ent_ref_amt.delete(0, tk.END)
                ent_ref_amt.insert(0, fmt_num(cred_val))

            tk.Button(r_row, text="كامل الرصيد", command=set_full_ref, bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 8, "bold"), padx=8, pady=2, relief="flat", cursor="hand2").pack(side="left", padx=4)

            tk.Label(body_r, text="ℹ️ يمكنك استرداد جزء فقط وسيبقى الباقي كرصيد دائن مستحق بالفاتورة.", font=("Segoe UI", 9, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_MUTED, wraplength=420, justify="right").pack(pady=8)

            def confirm_refund_action():
                try:
                    ramt = float(ent_ref_amt.get().strip() or 0)
                except ValueError:
                    ramt = 0.0

                if ramt <= 0 or ramt > cred_val:
                    messagebox.showwarning("تنبيه", f"يرجى إدخال مبلغ صحيح بين 1 ج.م وحتى {fmt_curr(cred_val)}!", parent=rf_win)
                    return

                if messagebox.askyesno("تأكيد الاسترداد النقدي", f"هل تريد استرداد مبلغ {fmt_curr(ramt)} نقداً وإيداعه فوراً بالخزينة؟", parent=rf_win):
                    try:
                        self.db.refund_supplier_credit_to_cash(inv['id'], amount=ramt, user_id=self.current_user_id)
                        messagebox.showinfo("تم الاسترداد", f"تم استرداد {fmt_curr(ramt)} نقداً وإيداعها في خزينة السيولة بنجاح!", parent=rf_win)
                        rf_win.destroy()
                        refresh_supplier_page()
                    except Exception as ex:
                        messagebox.showerror("خطأ", str(ex), parent=rf_win)

            bot_r = tk.Frame(rf_win, bg=self.COLOR_TOPBAR, pady=8, padx=14)
            bot_r.pack(side="bottom", fill="x")
            tk.Button(bot_r, text="✅ تأكيد الاسترداد للخزينة", command=confirm_refund_action, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"), padx=16, pady=4, relief="flat", cursor="hand2").pack(side="right", padx=4)
            tk.Button(bot_r, text="إلغاء", command=rf_win.destroy, bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 10, "bold"), padx=14, pady=4, relief="flat", cursor="hand2").pack(side="left", padx=4)

        if self.has_permission('can_refund_supplier_credit'):
            tk.Button(
                actions_bar, text="💰 استرداد رصيد المورد للخزينة", command=open_refund_credit_dialog,
                bg="#0d9488", fg="white", font=("Segoe UI", 10, "bold"),
                padx=14, pady=5, relief="flat", cursor="hand2"
            ).pack(side="right", padx=4)

        if self.has_permission('can_edit_operation_dates') or self.has_permission('can_edit_transaction_date'):
            def edit_selected_supplier_invoice_date():
                inv = get_selected_invoice()
                if not inv:
                    return
                cur_dt = str(inv.get('invoice_date') or '')
                self.open_edit_record_date_modal("SUPPLIER_INVOICE", inv['id'], cur_dt, on_success_callback=refresh_supplier_page)

            tk.Button(
                actions_bar, text="📅 تعديل تاريخ الفاتورة", command=edit_selected_supplier_invoice_date,
                bg="#0284c7", fg="white", font=("Segoe UI", 10, "bold"),
                padx=14, pady=5, relief="flat", cursor="hand2"
            ).pack(side="right", padx=4)

        if self.has_permission('can_print_supplier_invoice'):
            tk.Button(
                actions_bar, text="🖨️ طباعة الفاتورة", command=lambda: print_selected_supplier_invoice(),
                bg=self.COLOR_PURPLE, fg="white", font=("Segoe UI", 10, "bold"),
                padx=16, pady=5, relief="flat", cursor="hand2"
            ).pack(side="right", padx=4)

        if self.has_permission('can_manage_suppliers'):
            tk.Button(
                actions_bar, text="⚙️ إدارة الموردين", command=lambda: self.open_manage_suppliers_modal(on_close_callback=refresh_supplier_page),
                bg=self.COLOR_TEAL, fg="white", font=("Segoe UI", 10, "bold"),
                padx=14, pady=5, relief="flat", cursor="hand2", activebackground="#0f766e", activeforeground="#ffffff"
            ).pack(side="left", padx=4)

        tk.Button(
            actions_bar, text="🔄 تحديث", command=lambda: refresh_supplier_page(),
            bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold"),
            padx=14, pady=5, relief="flat", cursor="hand2", activebackground="#0284c7", activeforeground="#ffffff"
        ).pack(side="left", padx=4)

        t_frame = tk.Frame(self.content_frame, bg=self.COLOR_BG)
        t_frame.pack(fill="both", expand=True, padx=18, pady=(4, 14))

        top_supp_card = tk.LabelFrame(
            t_frame, text="📋 سجل فواتير الموردين (اختر فاتورة لعرض أجهزتها بالأسفل)",
            bg=self.COLOR_CARD, fg=self.COLOR_TEAL, font=("Segoe UI", 10, "bold"), padx=10, pady=8
        )
        top_supp_card.pack(fill="both", expand=True, pady=(0, 8))

        cols = ("الحالة", "التاريخ", "رصيد دائن لنا", "المتبقي للمورد", "المدفوع", "إجمالي الفاتورة", "عدد الأجهزة", "هاتف المورد", "النوع", "اسم المورد", "رقم الفاتورة")
        itree = ttk.Treeview(top_supp_card, columns=cols, show="headings", height=7)
        self.configure_tree_row_colors(itree)
        i_widths = {
            "الحالة": 95, "التاريخ": 120, "رصيد دائن لنا": 115, "المتبقي للمورد": 115, "المدفوع": 110,
            "إجمالي الفاتورة": 115, "عدد الأجهزة": 85, "هاتف المورد": 110,
            "النوع": 75, "اسم المورد": 150, "رقم الفاتورة": 80
        }
        for c in cols:
            itree.heading(c, text=c)
            itree.column(c, anchor="center", width=i_widths.get(c, 100))

        vsb = ttk.Scrollbar(top_supp_card, orient="vertical", command=itree.yview)
        hsb = ttk.Scrollbar(top_supp_card, orient="horizontal", command=itree.xview)
        itree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="left", fill="y")
        hsb.pack(side="bottom", fill="x")
        itree.pack(side="right", fill="both", expand=True)

        bot_supp_dev_card = tk.LabelFrame(
            t_frame, text="📦 الأجهزة المسجلة ضمن فاتورة المورد المحددة",
            bg=self.COLOR_CARD, fg=self.COLOR_BLUE, font=("Segoe UI", 10, "bold"), padx=10, pady=8
        )
        bot_supp_dev_card.pack(fill="both", expand=True)

        bot_supp_bar = tk.Frame(bot_supp_dev_card, bg=self.COLOR_CARD)
        bot_supp_bar.pack(fill="x", pady=(0, 4))
        lbl_sel_supp_info = tk.Label(
            bot_supp_bar, text="👈 حدد فاتورة مورد من الجدول أعلاه لعرض قائمة أجهزتها",
            font=("Segoe UI", 10, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_MUTED
        )
        lbl_sel_supp_info.pack(side="right")

        s_dev_cols = (
            "حالة التوفر", "سعر الشراء", "الحالة", "المساحة", "السيريال IMEI", "الموديل", "الماركة", "كود الجهاز"
        )
        supp_dev_tree = ttk.Treeview(bot_supp_dev_card, columns=s_dev_cols, show="headings", height=4)
        self.configure_tree_row_colors(supp_dev_tree)
        sd_widths = {
            "حالة التوفر": 115, "سعر الشراء": 115, "الحالة": 105,
            "المساحة": 90, "السيريال IMEI": 135, "الموديل": 140, "الماركة": 110, "كود الجهاز": 85
        }
        for sdc in s_dev_cols:
            supp_dev_tree.heading(sdc, text=sdc)
            supp_dev_tree.column(sdc, anchor="center", width=sd_widths.get(sdc, 110))

        s_cd_vsb = ttk.Scrollbar(bot_supp_dev_card, orient="vertical", command=supp_dev_tree.yview)
        supp_dev_tree.configure(yscrollcommand=s_cd_vsb.set)
        s_cd_vsb.pack(side="left", fill="y")
        supp_dev_tree.pack(side="right", fill="both", expand=True)

        self.bind_treeview_double_click(supp_dev_tree, target_column_name="كود الجهاز")

        supp_id_by_label = {}
        invoices_map = {}

        def on_supp_inv_select(event=None):
            supp_dev_tree.delete(*supp_dev_tree.get_children())
            sel = itree.selection()
            if not sel:
                lbl_sel_supp_info.config(text="👈 حدد فاتورة مورد من الجدول أعلاه لعرض قائمة أجهزتها", fg=self.COLOR_MUTED)
                return
            inv = invoices_map.get(clean_id_val(sel[0]))
            if not inv:
                return

            iid = inv['id']
            devs = self.db.get_devices_by_supplier_invoice(iid)
            rem = float(inv.get('remaining_amount') or 0)

            for idx_d, d in enumerate(devs):
                is_sold = d.get('is_sold') or (d.get('status') == 'SOLD')
                st_badge = "مباع 🔴" if is_sold else "متاح 🟢"
                raw_st = str(d.get('storage') or '-').replace('GB', '').strip()
                storage_str = f"{raw_st} GB" if (raw_st and raw_st != "-") else "-"
                cond_str = d.get('device_condition') or "مستعمل"
                row_tag = 'evenrow' if idx_d % 2 == 0 else 'oddrow'

                supp_dev_tree.insert("", "end", iid=str(d['id']), tags=(row_tag,), values=(
                    fix_bidi(st_badge),
                    fmt_curr(d.get('buy_price')),
                    fix_bidi(cond_str),
                    fix_bidi(storage_str),
                    d.get('imei_serial') or "-",
                    fix_bidi(d.get('model') or "-"),
                    fix_bidi(d.get('category') or "-"),
                    f"#{d['id']}"
                ))

            lbl_sel_supp_info.config(
                text=fix_bidi(f"🏭 فاتورة شراء #{iid} | المورد: {inv.get('supplier_name')} | عدد الأجهزة: {len(devs)} | المتبقي: {fmt_curr(rem)}"),
                fg=self.COLOR_WARN if rem > 0 else self.COLOR_ACCENT
            )

        itree.bind("<<TreeviewSelect>>", on_supp_inv_select)

        def populate_supp_filter():
            supp_id_by_label.clear()
            s_list = self.db.get_suppliers(active_only=False)
            vals = ["الكل"]
            for s in s_list:
                lbl = f"{s['name']} ({s.get('supplier_type', 'تاجر')})"
                supp_id_by_label[lbl] = s['id']
                vals.append(lbl)
            supp_filter_cb['values'] = vals
            if not supp_filter_cb.get() or supp_filter_cb.get() not in vals:
                supp_filter_cb.current(0)

        def refresh_supplier_page(event=None):
            populate_supp_filter()
            itree.delete(*itree.get_children())
            invoices_map.clear()

            sel_supp_lbl = supp_filter_cb.get()
            filter_sid = supp_id_by_label.get(sel_supp_lbl) if sel_supp_lbl != "الكل" else None
            st_mode = st_filter_cb.get()
            d_from = ent_supp_date_from.get().strip() or None
            d_to = ent_supp_date_to.get().strip() or None

            all_invs = self.db.get_supplier_invoices(supplier_id=filter_sid, unpaid_only=False, date_from=d_from, date_to=d_to)
            total_rem_all = sum(float(inv.get('remaining_amount') or 0) for inv in all_invs)
            total_cred_all = sum(float(inv.get('supplier_credit') or 0) for inv in all_invs)
            lbl_total_supp_debt.config(text=f"إجمالي مديونية الموردين: {fmt_curr(total_rem_all)}")
            lbl_total_supp_credit.config(text=f"★ لنا رصيد دائن لدى الموردين: {fmt_curr(total_cred_all)}")

            q = supp_search_ent.get().strip().lower()
            stype = supp_search_type_cb.get()

            row_inv_idx = 0
            for inv in all_invs:
                rem = float(inv.get('remaining_amount') or 0)
                if st_mode == "متبقي (غير خالص)" and rem <= 0:
                    continue
                if st_mode == "خالص" and rem > 0:
                    continue

                if q:
                    if "المورد" in stype:
                        if q not in str(inv.get('supplier_name') or '').lower():
                            continue
                    elif "الفاتورة" in stype or "#ID" in stype:
                        clean_q = clean_id_val(q)
                        if clean_q is None or inv['id'] != clean_q:
                            continue
                    elif "هاتف" in stype:
                        if q not in str(inv.get('supplier_phone') or '').lower():
                            continue
                    else:
                        searchable = f"{inv['id']} {inv.get('supplier_name')} {inv.get('supplier_phone')} {inv.get('supplier_type')}".lower()
                        if q not in searchable:
                            continue

                iid = inv['id']
                invoices_map[iid] = inv
                st_txt = "خالص 🟢" if rem <= 0 else "متبقي 🔴"
                cred_val = float(inv.get('supplier_credit') or 0.0)
                cred_txt = fmt_curr(cred_val) if cred_val > 0 else "-"
                row_inv_idx += 1
                row_tag = 'evenrow' if row_inv_idx % 2 == 0 else 'oddrow'

                itree.insert("", "end", iid=str(iid), tags=(row_tag,), values=(
                    fix_bidi(st_txt),
                    inv.get('date_formatted') or "-",
                    fix_bidi(cred_txt),
                    fmt_curr(rem),
                    fmt_curr(inv.get('paid_amount')),
                    fmt_curr(inv.get('total_amount')),
                    inv.get('devices_count', 0),
                    inv.get('supplier_phone') or "-",
                    fix_bidi(inv.get('supplier_type') or "تاجر"),
                    fix_bidi(inv.get('supplier_name') or "-"),
                    f"#{iid}"
                ))

            self.after(50, lambda: itree.xview_moveto(1.0))

        def get_selected_invoice():
            sel = itree.selection()
            if not sel:
                messagebox.showwarning("تنبيه", "يرجى تحديد فاتورة مورد من الجدول أولاً!")
                return None
            return invoices_map.get(clean_id_val(sel[0]))

        def open_selected_invoice_details(event=None):
            inv = get_selected_invoice()
            if inv:
                self.show_supplier_invoice_details_modal(inv['id'], on_updated_callback=refresh_supplier_page)

        def open_pay_supplier_modal():
            inv = get_selected_invoice()
            if not inv:
                return
            self._open_pay_supplier_dialog(inv, on_paid_callback=refresh_supplier_page)

        def print_selected_supplier_invoice():
            inv = get_selected_invoice()
            if not inv:
                return
            self._print_supplier_invoice_obj(inv)

        itree.bind("<Double-1>", open_selected_invoice_details)
        supp_search_ent.bind("<KeyRelease>", refresh_supplier_page)
        supp_search_type_cb.bind("<<ComboboxSelected>>", refresh_supplier_page)
        supp_filter_cb.bind("<<ComboboxSelected>>", refresh_supplier_page)
        st_filter_cb.bind("<<ComboboxSelected>>", refresh_supplier_page)
        refresh_supplier_page()

    def _open_pay_supplier_dialog(self, inv_obj, parent_win=None, on_paid_callback=None):
        rem_val = float(inv_obj.get('remaining_amount') or 0)
        pwin = tk.Toplevel(parent_win or self)
        pwin.title(f"سداد دفعة للمورد - فاتورة #{inv_obj['id']}")
        pwin.geometry("460x365")
        pwin.configure(bg=self.COLOR_CARD)
        pwin.resizable(False, False)
        pwin.grab_set()

        top_b = tk.Frame(pwin, bg=self.COLOR_TOPBAR, pady=10, padx=14)
        top_b.pack(fill="x")
        tk.Label(
            top_b, text=fix_bidi(f"💵 سداد دفعة للمورد: {inv_obj.get('supplier_name')}"),
            font=("Segoe UI", 12, "bold"), bg=self.COLOR_TOPBAR, fg=self.COLOR_ACCENT
        ).pack(side="right")

        body = tk.Frame(pwin, bg=self.COLOR_CARD, padx=18, pady=10)
        body.pack(fill="both", expand=True)

        tk.Label(body, text=f"المتبقي في الفاتورة #{inv_obj['id']}: {fmt_curr(rem_val)}", font=("Segoe UI", 12, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_WARN).pack(pady=(0, 8))

        row_in = tk.Frame(body, bg=self.COLOR_CARD)
        row_in.pack(fill="x", pady=4)
        tk.Label(row_in, text="المبلغ المسدد (ج.م):", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right", padx=6)
        ent_amt = tk.Entry(row_in, validate="key", validatecommand=self.vcmd_num, font=("Segoe UI", 12, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_ACCENT, insertbackground=self.COLOR_TEXT, justify="center", width=16)
        ent_amt.insert(0, fmt_num(rem_val))
        ent_amt.pack(side="right", padx=6, ipady=4)
        ent_amt.focus_set()
        ent_amt.select_range(0, tk.END)

        get_pay_custom_date = self._create_operation_date_picker(body, label_text="تاريخ السداد:")

        def confirm_pay():
            try:
                amt = float(ent_amt.get().strip() or 0)
            except ValueError:
                amt = 0.0
            if amt <= 0:
                messagebox.showwarning("تنبيه", "يرجى إدخال مبلغ سداد صحيح أكبر من الصفر!", parent=pwin)
                return
            try:
                p_dt = get_pay_custom_date()
            except ValueError as p_err:
                messagebox.showerror("خطأ في التاريخ", str(p_err), parent=pwin)
                return
            try:
                self.db.pay_supplier_debt(inv_obj['id'], amt, self.current_user_id, custom_date=p_dt)
                messagebox.showinfo("تم السداد", f"تم تسجيل سداد {fmt_curr(amt)} للمورد بنجاح!", parent=pwin)
                pwin.destroy()
                if on_paid_callback:
                    on_paid_callback()
            except Exception as ex:
                messagebox.showerror("خطأ", str(ex), parent=pwin)

        ent_amt.bind("<Return>", lambda e: confirm_pay())

        bot_b = tk.Frame(pwin, bg=self.COLOR_TOPBAR, pady=8, padx=14)
        bot_b.pack(fill="x", side="bottom")
        tk.Button(bot_b, text="✅ تأكيد السداد (Enter)", command=confirm_pay, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"), padx=18, pady=4, relief="flat", cursor="hand2").pack(side="right", padx=4)
        tk.Button(bot_b, text="إلغاء", command=pwin.destroy, bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 10, "bold"), padx=14, pady=4, relief="flat", cursor="hand2").pack(side="left", padx=4)

    def _print_supplier_invoice_obj(self, inv_obj):
        devs = self.db.get_devices_by_invoice(inv_obj['id'])
        pays = self.db.get_supplier_payments_history(inv_obj['id'])
        inv_data = {
            'doc_type': 'SUPPLIER_INVOICE',
            'invoice_id': inv_obj['id'],
            'supplier_name': inv_obj.get('supplier_name') or '-',
            'supplier_phone': inv_obj.get('supplier_phone') or '-',
            'supplier_type': inv_obj.get('supplier_type') or 'تاجر',
            'total_amount': float(inv_obj.get('total_amount') or 0),
            'paid_amount': float(inv_obj.get('paid_amount') or 0),
            'remaining_amount': float(inv_obj.get('remaining_amount') or 0),
            'supplier_credit': float(inv_obj.get('supplier_credit') or 0),
            'devices_list': devs,
            'payments_list': pays,
            'date_str': inv_obj.get('date_formatted') or ''
        }
        self.open_invoice_preview_and_print(inv_data, f"طباعة فاتورة مورد #{inv_obj['id']}")

    def show_supplier_invoice_details_modal(self, invoice_id, on_updated_callback=None):
        inv_id_clean = clean_id_val(invoice_id)
        all_invs = self.db.get_supplier_invoices()
        inv_obj = next((x for x in all_invs if x['id'] == inv_id_clean), None)
        if not inv_obj:
            messagebox.showerror("خطأ", f"تعذر العثور على فاتورة المورد #{invoice_id}")
            return

        iwin = tk.Toplevel(self)
        iwin.title(f"تفاصيل فاتورة المورد #{inv_obj['id']} - {inv_obj.get('supplier_name')}")
        iwin.geometry("880x720")
        iwin.configure(bg=self.COLOR_BG)
        iwin.grab_set()

        top_bar = tk.Frame(iwin, bg=self.COLOR_TOPBAR, pady=10, padx=16)
        top_bar.pack(fill="x")
        tk.Label(
            top_bar,
            text=fix_bidi(f"📋 تفاصيل فاتورة المورد #{inv_obj['id']}  |  {inv_obj.get('supplier_name')}"),
            font=("Segoe UI", 14, "bold"), bg=self.COLOR_TOPBAR, fg="#38bdf8"
        ).pack(side="right")

        bot_bar = tk.Frame(iwin, bg=self.COLOR_TOPBAR, pady=10, padx=16)
        bot_bar.pack(side="bottom", fill="x")
        tk.Button(bot_bar, text="إغلاق النافذة", command=iwin.destroy, bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 10, "bold"), padx=20, pady=4, relief="flat", cursor="hand2").pack(side="left")

        scroll_body = self._create_scrollable_frame(iwin, bg_color=self.COLOR_BG, pad_x=16, pad_y=10)

        def render_modal_contents():
            for w in scroll_body.winfo_children():
                w.destroy()

            fresh_invs = self.db.get_supplier_invoices()
            cur_inv = next((x for x in fresh_invs if x['id'] == inv_id_clean), inv_obj)
            devs = self.db.get_devices_by_invoice(inv_id_clean)
            pays = self.db.get_supplier_payments_history(inv_id_clean)
            rem_amount = float(cur_inv.get('remaining_amount') or 0)
            cred_amount = float(cur_inv.get('supplier_credit') or 0)

            summary_card = tk.LabelFrame(scroll_body, text="🏭 ملخص الفاتورة وحساب المورد", bg=self.COLOR_CARD, fg=self.COLOR_TEAL, font=("Segoe UI", 11, "bold"), padx=14, pady=10)
            summary_card.pack(fill="x", pady=6)

            def do_refund_credit_action():
                if cred_amount <= 0:
                    messagebox.showinfo("تنبيه", "لا يوجد رصيد دائن مستحق للاسترداد على هذه الفاتورة!", parent=iwin)
                    return

                rf_win = tk.Toplevel(iwin)
                rf_win.title("استرداد رصيد المورد نقداً")
                rf_win.geometry("460x320")
                rf_win.configure(bg=self.COLOR_CARD)
                rf_win.resizable(False, False)
                rf_win.grab_set()

                top_r = tk.Frame(rf_win, bg=self.COLOR_TOPBAR, pady=10, padx=14)
                top_r.pack(fill="x")
                tk.Label(top_r, text=fix_bidi("💰 استرداد رصيد دائن للخزينة"), font=("Segoe UI", 12, "bold"), bg=self.COLOR_TOPBAR, fg=self.COLOR_ACCENT).pack(side="right")

                body_r = tk.Frame(rf_win, bg=self.COLOR_CARD, padx=18, pady=12)
                body_r.pack(fill="both", expand=True)

                tk.Label(body_r, text=f"الرصيد الدائن المتاح: {fmt_curr(cred_amount)}", font=("Segoe UI", 12, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_ACCENT).pack(pady=(0, 10))

                r_row = tk.Frame(body_r, bg=self.COLOR_CARD)
                r_row.pack(fill="x", pady=6)
                tk.Label(r_row, text="المبلغ المسترد (ج.م):", font=("Segoe UI", 10, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_TEXT).pack(side="right", padx=6)
                ent_r_amt = tk.Entry(r_row, font=("Segoe UI", 12, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_ACCENT, insertbackground=self.COLOR_TEXT, justify="center", width=14)
                ent_r_amt.insert(0, fmt_num(cred_amount))
                ent_r_amt.pack(side="right", padx=4, ipady=3)

                def confirm_rf():
                    try:
                        ramt = float(ent_r_amt.get().strip() or 0)
                    except ValueError:
                        ramt = 0.0
                    if ramt <= 0 or ramt > cred_amount:
                        messagebox.showwarning("تنبيه", f"يرجى إدخال مبلغ صحيح بين 1 ج.م وحتى {fmt_curr(cred_amount)}!", parent=rf_win)
                        return
                    try:
                        refunded = self.db.refund_supplier_credit_to_cash(inv_id_clean, amount=ramt, user_id=self.current_user_id)
                        messagebox.showinfo("تم الاسترداد بنجاح", f"تم تحصيل واسترداد مبلغ {fmt_curr(refunded)} نقداً وإيداعه بنجاح في خزينة السيولة!", parent=rf_win)
                        rf_win.destroy()
                        render_modal_contents()
                        if on_updated_callback:
                            on_updated_callback()
                    except Exception as ex:
                        messagebox.showerror("خطأ", str(ex), parent=rf_win)

                bot_r = tk.Frame(rf_win, bg=self.COLOR_TOPBAR, pady=8, padx=14)
                bot_r.pack(side="bottom", fill="x")
                tk.Button(bot_r, text="✅ تأكيد الاسترداد", command=confirm_rf, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"), padx=16, pady=4, relief="flat", cursor="hand2").pack(side="right", padx=4)
                tk.Button(bot_r, text="إلغاء", command=rf_win.destroy, bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 10, "bold"), padx=14, pady=4, relief="flat", cursor="hand2").pack(side="left", padx=4)

            if cred_amount > 0:
                cred_alert = tk.Frame(summary_card, bg="#064e3b", padx=14, pady=10)
                cred_alert.pack(fill="x", padx=4, pady=(2, 10))

                tk.Label(
                    cred_alert,
                    text=fix_bidi(f"🌟 رصيد دائن مستحق لنا لدى المورد: {fmt_curr(cred_amount)}"),
                    font=("Segoe UI", 11, "bold"), bg="#064e3b", fg="#6ee7b7"
                ).pack(side="right")

                tk.Button(
                    cred_alert,
                    text="💰 استرداد الرصيد نقداً للخزينة فوراً",
                    command=do_refund_credit_action,
                    bg=self.COLOR_ACCENT, fg="white",
                    font=("Segoe UI", 10, "bold"),
                    padx=14, pady=4, relief="flat", cursor="hand2"
                ).pack(side="left")

            st_txt = "خالص بالكامل 🟢" if rem_amount <= 0 else "متبقي (أجل) 🔴"
            info_pairs = [
                [("رقم الفاتورة:", f"#{cur_inv['id']}"), ("تاريخ الفاتورة:", cur_inv.get('date_formatted') or "-")],
                [("اسم المورد:", cur_inv.get('supplier_name') or "-"), ("هاتف المورد:", cur_inv.get('supplier_phone') or "-")],
                [("نوع المورد:", cur_inv.get('supplier_type') or "تاجر"), ("عدد الأجهزة بالفاتورة:", str(len(devs)))],
                [("إجمالي الفاتورة:", fmt_curr(cur_inv.get('total_amount'))), ("إجمالي المدفوع:", fmt_curr(cur_inv.get('paid_amount')))],
                [("المبلغ المتبقي:", fmt_curr(rem_amount)), ("رصيد دائن لنا:", fmt_curr(cred_amount) if cred_amount > 0 else "لا يوجد")],
            ]
            self._build_rtl_info_grid(summary_card, info_pairs)

            act_row = tk.Frame(summary_card, bg=self.COLOR_CARD)
            act_row.pack(pady=8)

            if cred_amount > 0:
                tk.Button(
                    act_row, text="💰 استرداد الرصيد نقداً للخزينة",
                    command=do_refund_credit_action,
                    bg=self.COLOR_ACCENT, fg="white",
                    font=("Segoe UI", 10, "bold"),
                    padx=16, pady=5, relief="flat", cursor="hand2"
                ).pack(side="right", padx=6)

            if self.has_permission('can_pay_supplier_debt') and rem_amount > 0:
                def pay_from_modal():
                    def after_paid():
                        render_modal_contents()
                        if on_updated_callback:
                            on_updated_callback()
                    self._open_pay_supplier_dialog(cur_inv, parent_win=iwin, on_paid_callback=after_paid)

                tk.Button(act_row, text="💵 سداد دفعة الآن", command=pay_from_modal, bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold"), padx=16, pady=5, relief="flat", cursor="hand2").pack(side="right", padx=6)

            if self.has_permission('can_print_supplier_invoice'):
                tk.Button(act_row, text="🖨️ طباعة الفاتورة", command=lambda: self._print_supplier_invoice_obj(cur_inv), bg=self.COLOR_INDIGO, fg="white", font=("Segoe UI", 10, "bold"), padx=16, pady=5, relief="flat", cursor="hand2").pack(side="right", padx=6)

            tk.Button(act_row, text="🔄 تحديث", command=render_modal_contents, bg=self.COLOR_TOPBAR, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold"), padx=14, pady=5, relief="flat", cursor="hand2").pack(side="left", padx=6)

            pays_card = tk.LabelFrame(scroll_body, text="💳 سجل دفعات السداد للمورد", bg=self.COLOR_CARD, fg=self.COLOR_ACCENT, font=("Segoe UI", 11, "bold"), padx=14, pady=10)
            pays_card.pack(fill="x", pady=6)

            if pays:
                p_cols = ("الموظف المسدد", "تاريخ ووقت الدفعة", "المبلغ المسدد", "م")
                ptree = ttk.Treeview(pays_card, columns=p_cols, show="headings", height=max(4, min(7, len(pays) + 1)))
                self.configure_tree_row_colors(ptree)
                for c in p_cols:
                    ptree.heading(c, text=c)
                    ptree.column(c, anchor="center", width=180 if c != "م" else 60)
                ptree.pack(fill="x", pady=4)
                for idx_p, p in enumerate(pays, 1):
                    row_tag = 'evenrow' if idx_p % 2 == 0 else 'oddrow'
                    ptree.insert("", "end", tags=(row_tag,), values=(
                        fix_bidi(p.get('payer_name') or "-"),
                        p.get('payment_date_formatted') or "-",
                        fmt_curr(p.get('payment_amount')),
                        idx_p
                    ))
            else:
                tk.Label(pays_card, text="لا توجد دفعات مسجلة لهذه الفاتورة حتى الآن.", font=("Segoe UI", 10, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_MUTED).pack(pady=6)

            devs_card = tk.LabelFrame(scroll_body, text="📱 الأجهزة المسجلة بهذه الفاتورة (اللون - الضريبة - العلبة - المواصفات)", bg=self.COLOR_CARD, fg=self.COLOR_BLUE, font=("Segoe UI", 11, "bold"), padx=14, pady=10)
            devs_card.pack(fill="x", pady=6)

            if devs:
                can_see_buy = self.has_permission('can_view_buy_price')
                d_cols = ("حالة التوفر", "سعر الشراء", "الحالة", "المساحة", "السيريال IMEI", "الموديل", "الماركة", "كود الجهاز")
                dtree = ttk.Treeview(devs_card, columns=d_cols, show="headings", height=max(4, min(8, len(devs) + 1)))
                self.configure_tree_row_colors(dtree)
                d_widths = {
                    "حالة التوفر": 100, "سعر الشراء": 115, "الحالة": 100, "المساحة": 95,
                    "السيريال IMEI": 135, "الموديل": 140, "الماركة": 105, "كود الجهاز": 85
                }
                for c in d_cols:
                    dtree.heading(c, text=c)
                    dtree.column(c, anchor="center", width=d_widths.get(c, 100))
                dtree.pack(fill="x", pady=4)

                for idx_d, d in enumerate(devs, 1):
                    st_d = "مباع 🔴" if d.get('is_sold') else "متاح 🟢"
                    cond_txt = d.get('device_condition') or d.get('condition') or "مستعمل"
                    bp_s = fmt_curr(d.get('buy_price')) if can_see_buy else "🔒 مخفي"
                    raw_st = str(d.get('storage') or "-").replace("GB", "").strip()
                    storage_txt = f"{raw_st} GB" if (raw_st and raw_st != "-") else "-"
                    row_tag = 'evenrow' if idx_d % 2 == 0 else 'oddrow'
                    dtree.insert("", "end", iid=str(d['id']), tags=(row_tag,), values=(
                        fix_bidi(st_d),
                        bp_s,
                        fix_bidi(cond_txt),
                        fix_bidi(storage_txt),
                        d.get('imei_serial') or "-",
                        fix_bidi(d.get('model') or "-"),
                        fix_bidi(d.get('category') or "-"),
                        f"#{d['id']}"
                    ))
                self.bind_treeview_double_click(dtree, target_column_name="كود الجهاز")
                self.after(50, lambda: dtree.xview_moveto(1.0))
            else:
                tk.Label(devs_card, text="لا توجد أجهزة نشطة مرتبطة بهذه الفاتورة.", font=("Segoe UI", 10, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_MUTED).pack(pady=6)

        render_modal_contents()

    def view_reports(self, active_tab="financial_center"):
        if not self.has_permission('can_view_reports'):
            messagebox.showerror("صلاحيات غير كافية", "عفواً، لا تملك صلاحية الدخول لشاشة التقارير المالية!")
            return

        self.current_view_func = self.view_reports
        self.build_main_ui(keep_view=True)
        self.clear_content()

        top_switcher = tk.Frame(self.content_frame, bg=self.COLOR_CARD, padx=18, pady=8, highlightthickness=1, highlightbackground=self.COLOR_TOPBAR)
        top_switcher.pack(fill="x", padx=18, pady=(10, 8))

        tk.Label(
            top_switcher, text="📊 التقارير المالية:",
            font=("Segoe UI", 14, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_BLUE
        ).pack(side="right", padx=(0, 14))

        sub_content = tk.Frame(self.content_frame, bg=self.COLOR_BG)
        sub_content.pack(fill="both", expand=True)

        tab_state = {"current": active_tab}

        btn_tab_fin = tk.Button(
            top_switcher, text="🏦 المركز المالي والسيولة",
            command=lambda: switch_report_tab("financial_center"),
            font=("Segoe UI", 11, "bold"), padx=18, pady=6, relief="flat", cursor="hand2"
        )
        btn_tab_fin.pack(side="right", padx=5)

        btn_tab_prof = tk.Button(
            top_switcher, text="📈 الأرباح وسجل المبيعات",
            command=lambda: switch_report_tab("profits_sales"),
            font=("Segoe UI", 11, "bold"), padx=18, pady=6, relief="flat", cursor="hand2"
        )
        btn_tab_prof.pack(side="right", padx=5)

        def switch_report_tab(tab_name):
            tab_state["current"] = tab_name
            for w in sub_content.winfo_children():
                w.destroy()

            if tab_name == "financial_center":
                btn_tab_fin.configure(bg=self.COLOR_BLUE, fg="white")
                btn_tab_prof.configure(bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT)
                self._render_financial_center_tab(sub_content)
            else:
                btn_tab_prof.configure(bg=self.COLOR_ACCENT, fg="white")
                btn_tab_fin.configure(bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT)
                self._render_profits_and_sales_tab(sub_content)

        switch_report_tab(active_tab)

    def show_capital_details_modal(self, fin=None):
        if fin is None:
            fin = self.db.get_financial_summary()

        cwin = tk.Toplevel(self)
        cwin.title("📊 بيان وتفاصيل حساب رأس المال الشامل")
        cwin.geometry("780x640")
        cwin.configure(bg=self.COLOR_BG)
        cwin.grab_set()

        top_b = tk.Frame(cwin, bg=self.COLOR_TOPBAR, pady=12, padx=18)
        top_b.pack(fill="x")
        tk.Label(
            top_b, text=fix_bidi("📊 بيان وتفاصيل ومعادلة حساب رأس المال الشامل"),
            font=("Segoe UI", 14, "bold"), bg=self.COLOR_TOPBAR, fg=self.COLOR_BLUE
        ).pack(side="right")

        body = tk.Frame(cwin, bg=self.COLOR_BG, padx=18, pady=12)
        body.pack(fill="both", expand=True)

        formula_card = tk.LabelFrame(
            body, text=fix_bidi("📐 المعادلة المحاسبية المعتمدة لرأس المال"),
            bg=self.COLOR_CARD, fg=self.COLOR_PURPLE, font=("Segoe UI", 11, "bold"), padx=14, pady=10
        )
        formula_card.pack(fill="x", pady=(0, 10))

        tk.Label(
            formula_card,
            text=fix_bidi("صافي رأس المال = (السيولة النقدية + تكلفة المخزون المتاح + ديون العملاء + رصيدنا لدى الموردين) - مديونية الموردين"),
            font=("Segoe UI", 11, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_TEXT, justify="center"
        ).pack(pady=4)

        grid_card = tk.LabelFrame(
            body, text=fix_bidi("📋 تفصيل وتوزيع عناصر رأس المال"),
            bg=self.COLOR_CARD, fg=self.COLOR_BLUE, font=("Segoe UI", 11, "bold"), padx=14, pady=10
        )
        grid_card.pack(fill="both", expand=True, pady=4)

        can_see_liq = self.has_permission('can_view_liquidity')
        can_see_buy = self.has_permission('can_view_buy_price')

        liq_val = fin.get('current_liquidity', 0)
        inv_val = fin.get('total_inventory_cost', 0)
        cust_val = fin.get('total_customer_debts', 0)
        cred_val = fin.get('supplier_credit', 0)
        supp_val = fin.get('total_supplier_debts', 0)
        cap_val = fin.get('total_capital', 0)
        dev_cnt = fin.get('available_devices_count', 0)

        items = [
            ("💵 السيولة النقدية الفعلية بالخزينة:", fmt_curr(liq_val) if can_see_liq else "🔒 مخفي", "موجب (+)", "النقدية الفعلية الصافية الموجودة بالدرج/الخزينة", self.COLOR_ACCENT),
            ("📦 قيمة المخزون المتاح (سعر الشراء):", fmt_curr(inv_val) if can_see_buy else "🔒 مخفي", "موجب (+)", f"قيمة بضاعة المحل الحالية بالسوق ({dev_cnt} جهاز متاح)", self.COLOR_BLUE),
            ("💳 إجمالي ديون العملاء والخرج:", fmt_curr(cust_val), "موجب (+)", "أموال مستحقة للمحل بذمة الزبائن والعملاء", self.COLOR_WARN),
            ("📥 رصيد مستحق لنا لدى الموردين:", fmt_curr(cred_val), "موجب (+)", "أموال مدفوعة ومحفوظة كأمانة أو رصيد دائن لدى الموردين", self.COLOR_TEAL),
            ("🏭 إجمالي مديونيات الموردين (المتبقي):", fmt_curr(supp_val), "سالب (-)", "فواتير بضاعة آجلة مطلوب سدادها للتجار والموردين", self.COLOR_DANGER),
        ]

        for idx, (title, val_s, sign_s, desc, col_c) in enumerate(items):
            row_f = tk.Frame(grid_card, bg=self.COLOR_CARD if idx % 2 == 0 else self.COLOR_ENTRY_BG, padx=8, pady=6)
            row_f.pack(fill="x", pady=2)

            tk.Label(row_f, text=fix_bidi(title), font=("Segoe UI", 10, "bold"), bg=row_f["bg"], fg=self.COLOR_TEXT, width=32, anchor="e").pack(side="right", padx=6)
            tk.Label(row_f, text=fix_bidi(val_s), font=("Segoe UI", 11, "bold"), bg=row_f["bg"], fg=col_c, width=18, anchor="e").pack(side="right", padx=6)
            tk.Label(row_f, text=fix_bidi(sign_s), font=("Segoe UI", 10, "bold"), bg=row_f["bg"], fg=col_c, width=10, anchor="center").pack(side="right", padx=6)
            tk.Label(row_f, text=fix_bidi(desc), font=("Segoe UI", 9, "normal"), bg=row_f["bg"], fg=self.COLOR_MUTED, anchor="e").pack(side="right", fill="x", expand=True, padx=6)

        res_card = tk.Frame(body, bg=self.COLOR_CARD, padx=16, pady=12, highlightthickness=2, highlightbackground=self.COLOR_PURPLE)
        res_card.pack(fill="x", pady=(6, 0))

        tk.Label(res_card, text=fix_bidi("🏦 صافي رأس المال الإجمالي:"), font=("Segoe UI", 12, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_TEXT).pack(side="right", padx=8)
        cap_disp = fmt_curr(cap_val) if (can_see_liq and can_see_buy) else "🔒 مخفي للمصرح لهم"
        tk.Label(res_card, text=fix_bidi(cap_disp), font=("Segoe UI", 16, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_PURPLE).pack(side="right", padx=8)

        bot_b = tk.Frame(cwin, bg=self.COLOR_TOPBAR, pady=10, padx=18)
        bot_b.pack(fill="x", side="bottom")
        tk.Button(bot_b, text="إغلاق", command=cwin.destroy, bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold"), padx=24, pady=4, relief="flat", cursor="hand2").pack(side="left")

    def _render_financial_center_tab(self, parent_frame):
        fin = self.db.get_financial_summary()
        can_see_liq = self.has_permission('can_view_liquidity')
        can_see_buy = self.has_permission('can_view_buy_price')

        cards_row = tk.Frame(parent_frame, bg=self.COLOR_BG)
        cards_row.pack(fill="x", padx=18, pady=6)
        for i in range(3):
            cards_row.grid_columnconfigure(i, weight=1)

        def build_metric_card(row_idx, col_idx, title, val_txt, subtitle, accent_col, extra_widget_fn=None):
            c = tk.Frame(cards_row, bg=self.COLOR_CARD, padx=12, pady=10, highlightthickness=2, highlightbackground=accent_col)
            c.grid(row=row_idx, column=col_idx, sticky="nsew", padx=5, pady=4)
            hdr_f = tk.Frame(c, bg=self.COLOR_CARD)
            hdr_f.pack(fill="x")
            tk.Label(hdr_f, text=title, font=("Segoe UI", 10, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_MUTED).pack(side="right")
            if extra_widget_fn:
                extra_widget_fn(hdr_f)
            tk.Label(c, text=val_txt, font=("Segoe UI", 14, "bold"), bg=self.COLOR_CARD, fg=accent_col, pady=4).pack(anchor="e")
            tk.Label(c, text=subtitle, font=("Segoe UI", 8, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_TEXT).pack(anchor="e")
            return c

        liq_str = fmt_curr(fin.get('current_liquidity', 0)) if can_see_liq else "🔒 مخفي"
        inv_str = fmt_curr(fin.get('total_inventory_cost', 0)) if can_see_buy else "🔒 مخفي"
        cust_str = fmt_curr(fin.get('total_customer_debts', 0))
        supp_str = fmt_curr(fin.get('total_supplier_debts', 0))
        cred_str = fmt_curr(fin.get('supplier_credit', 0))
        cap_str = fmt_curr(fin.get('total_capital', 0)) if (can_see_liq and can_see_buy) else "🔒 مخفي"

        def add_cap_btn(parent_hdr):
            tk.Button(
                parent_hdr, text="🔍 تفاصيل رأس المال", command=lambda: self.show_capital_details_modal(fin),
                bg=self.COLOR_ENTRY_BG, fg=self.COLOR_BLUE, font=("Segoe UI", 8, "bold"),
                relief="flat", cursor="hand2", padx=5, pady=1
            ).pack(side="left")

        build_metric_card(0, 2, "💵 السيولة النقدية المتاحة", liq_str, "النقدية الفعلية بالخزينة", self.COLOR_ACCENT)
        build_metric_card(0, 1, "📦 قيمة المخزون المتاح", inv_str, f"الأجهزة المتاحة بالمخزون: {fin.get('available_devices_count', 0)}", self.COLOR_BLUE)
        build_metric_card(0, 0, "💳 ديون العملاء (الخرج)", cust_str, "أموال مستحقة لدى العملاء بالخارج", self.COLOR_WARN)

        build_metric_card(1, 2, "📥 رصيد مستحق لنا لدى الموردين", cred_str, "أمانات وأرصدة دائنة لحسابنا (+ رأس المال)", self.COLOR_TEAL)
        build_metric_card(1, 1, "🏭 مديونية الموردين (المتبقي)", supp_str, "مبالغ متبقية مطلوب سدادها للتجار (-)", self.COLOR_DANGER)
        build_metric_card(1, 0, "🏦 صافي رأس المال الشامل", cap_str, "السيولة + المخزون + الخرج + رصيد الموردين - الديون", self.COLOR_PURPLE, extra_widget_fn=add_cap_btn)

        liq_section = tk.LabelFrame(
            parent_frame, text="💰 إدارة السيولة النقدية وحركات الخزينة",
            bg=self.COLOR_CARD, fg=self.COLOR_ACCENT, font=("Segoe UI", 12, "bold"), padx=16, pady=12
        )
        liq_section.pack(fill="x", padx=18, pady=8)

        if self.has_permission('can_add_liquidity'):
            form_row1 = tk.Frame(liq_section, bg=self.COLOR_CARD)
            form_row1.pack(fill="x", pady=4)

            tk.Label(form_row1, text="المبلغ (ج.م):", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right", padx=(0, 4))
            ent_liq_amt = tk.Entry(form_row1, validate="key", validatecommand=self.vcmd_num, font=("Segoe UI", 12, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_ACCENT, insertbackground=self.COLOR_TEXT, justify="center", width=14)
            ent_liq_amt.pack(side="right", padx=4, ipady=3)

            tk.Label(form_row1, text="نوع العملية:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right", padx=(10, 4))
            cb_liq_type = ttk.Combobox(form_row1, values=["إيداع سيولة (+)", "سحب سيولة (-)"], state="readonly", width=16, font=("Segoe UI", 10, "bold"), justify="right")
            cb_liq_type.current(0)
            cb_liq_type.pack(side="right", padx=4, ipady=2)

            tk.Label(form_row1, text="البيان / الملاحظة:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right", padx=(10, 4))
            ent_liq_note = tk.Entry(form_row1, font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="right", width=26)
            ent_liq_note.pack(side="right", padx=4, ipady=3)

            form_row2 = tk.Frame(liq_section, bg=self.COLOR_CARD)
            form_row2.pack(fill="x", pady=(6, 2))

            get_liq_custom_date = self._create_operation_date_picker(form_row2, label_text="تاريخ الحركة:")

            def submit_liquidity():
                try:
                    amt = float(ent_liq_amt.get().strip() or 0)
                except ValueError:
                    amt = 0.0
                if amt <= 0:
                    messagebox.showwarning("تنبيه", "يرجى إدخال مبلغ صحيح أكبر من صفر!")
                    ent_liq_amt.focus_set()
                    return

                is_deposit = ("إيداع" in cb_liq_type.get())
                t_type = "DEPOSIT" if is_deposit else "WITHDRAW"
                note_v = ent_liq_note.get().strip() or ("إضافة سيولة نقدية" if is_deposit else "سحب من السيولة")

                try:
                    l_dt = get_liq_custom_date()
                except ValueError as l_err:
                    messagebox.showerror("خطأ في التاريخ", str(l_err))
                    return

                try:
                    self.db.add_capital_transaction(amt, t_type, note_v, self.current_user_id, custom_date=l_dt)
                    messagebox.showinfo("تم الحفظ", "تم تسجيل حركة السيولة وتحديث المركز المالي بنجاح!")
                    self.view_reports(active_tab="financial_center")
                except Exception as ex:
                    messagebox.showerror("خطأ", str(ex))

            self._bind_enter_chain([ent_liq_amt, ent_liq_note], final_callback=submit_liquidity)

            tk.Button(
                form_row2, text="➕ حفظ الحركة بالخزينة", command=submit_liquidity,
                bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"),
                padx=16, pady=4, relief="flat", cursor="hand2"
            ).pack(side="right", padx=(12, 4))

            if self.has_permission('can_view_liquidity_log'):
                tk.Button(
                    form_row2, text="📜 سجل وتفاصيل حركات السيولة",
                    command=self.open_liquidity_log_modal,
                    bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold"),
                    padx=14, pady=4, relief="flat", cursor="hand2"
                ).pack(side="left", padx=4)

        if self.current_user and self.current_user.get('role') == 'admin':
            recent_card = tk.LabelFrame(
                parent_frame, text="📋 سجل حركات السيولة (التاريخ - المضيف - المبلغ - الملاحظة)",
                bg=self.COLOR_CARD, fg=self.COLOR_BLUE, font=("Segoe UI", 11, "bold"), padx=14, pady=10
            )
            recent_card.pack(fill="both", expand=True, padx=18, pady=(0, 14))

            cols = ("الملاحظة / البيان", "المبلغ", "نوع الحركة", "المضيف", "التاريخ والوقت", "م")
            ltree = ttk.Treeview(recent_card, columns=cols, show="headings")
            self.configure_tree_row_colors(ltree)
            l_widths = {"الملاحظة / البيان": 280, "المبلغ": 130, "نوع الحركة": 120, "المضيف": 150, "التاريخ والوقت": 150, "م": 65}
            for c in cols:
                ltree.heading(c, text=c)
                ltree.column(c, anchor="center", width=l_widths.get(c, 120))

            vsb = ttk.Scrollbar(recent_card, orient="vertical", command=ltree.yview)
            ltree.configure(yscrollcommand=vsb.set)
            vsb.pack(side="left", fill="y")
            ltree.pack(side="right", fill="both", expand=True)

            for idx_t, tr in enumerate(self.db.get_capital_transactions(), 1):
                raw_type = tr.get('transaction_type')
                if raw_type == 'SUPPLIER_REFUND':
                    tp_ar = "استرداد رصيد مورد (+)"
                elif raw_type in ('WITHDRAWAL', 'WITHDRAW'):
                    tp_ar = "سحب سيولة (-)"
                else:
                    tp_ar = "إيداع سيولة (+)"
                row_tag = 'evenrow' if idx_t % 2 == 0 else 'oddrow'
                ltree.insert("", "end", tags=(row_tag,), values=(
                    fix_bidi(tr.get('notes') or "-"),
                    fmt_curr(tr.get('amount')),
                    fix_bidi(tp_ar),
                    fix_bidi(tr.get('created_by_name') or "-"),
                    tr.get('date_formatted') or "-",
                    idx_t
                ))

    def _render_profits_and_sales_tab(self, parent_frame):
        fin = self.db.get_financial_summary()
        can_see_prof = self.has_permission('can_view_profits')
        can_see_buy = self.has_permission('can_view_buy_price')

        prof_cards = tk.Frame(parent_frame, bg=self.COLOR_BG)
        prof_cards.pack(fill="x", padx=18, pady=6)
        for i in range(4):
            prof_cards.grid_columnconfigure(i, weight=1)

        def make_p_card(col_i, title, val_s, col_c):
            f = tk.Frame(prof_cards, bg=self.COLOR_CARD, padx=14, pady=10, highlightthickness=2, highlightbackground=col_c)
            f.grid(row=0, column=col_i, sticky="nsew", padx=5)
            tk.Label(f, text=title, font=("Segoe UI", 10, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_MUTED).pack(anchor="e")
            lbl_v = tk.Label(f, text=val_s, font=("Segoe UI", 14, "bold"), bg=self.COLOR_CARD, fg=col_c, pady=4)
            lbl_v.pack(anchor="e")
            return lbl_v

        month_prof_str = fmt_curr(fin.get('current_month_profit', 0)) if (can_see_prof and can_see_buy) else "🔒 مخفي"
        make_p_card(3, "📈 صافي ربح الشهر الحالي", month_prof_str, self.COLOR_ACCENT)
        lbl_period_sales = make_p_card(2, "🛒 إجمالي مبيعات الفترة", fmt_curr(0), self.COLOR_BLUE)
        lbl_period_cost = make_p_card(1, "📦 إجمالي تكلفة المبيعات", fmt_curr(0) if can_see_buy else "🔒 مخفي", self.COLOR_WARN)
        lbl_period_profit = make_p_card(0, "💎 صافي ربح الفترة المحددة", fmt_curr(0) if (can_see_prof and can_see_buy) else "🔒 مخفي", self.COLOR_PURPLE)

        if not self.has_permission('can_view_sales_report'):
            tk.Label(parent_frame, text="🔒 لا تملك صلاحية عرض جدول سجل المبيعات التفصيلي.", font=("Segoe UI", 12, "bold"), bg=self.COLOR_BG, fg=self.COLOR_MUTED, pady=40).pack()
            return

        filter_container = tk.Frame(parent_frame, bg=self.COLOR_CARD, padx=14, pady=10, highlightthickness=1, highlightbackground=self.COLOR_BORDER)
        filter_container.pack(fill="x", padx=18, pady=(4, 8))

        date_row = tk.Frame(filter_container, bg=self.COLOR_CARD)
        date_row.pack(fill="x", pady=(0, 6))

        tk.Label(date_row, text="📅 الفترة من:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right", padx=(0, 4))
        ent_from = tk.Entry(date_row, font=("Segoe UI", 10, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="center", width=12)
        ent_from.pack(side="right", padx=2, ipady=3)
        tk.Button(date_row, text="📅", command=lambda: self.open_date_picker(ent_from, load_sales_data, allow_future=False), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_BLUE, relief="flat", cursor="hand2").pack(side="right", padx=2)

        tk.Label(date_row, text="إلى:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right", padx=(10, 4))
        ent_to = tk.Entry(date_row, font=("Segoe UI", 10, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="center", width=12)
        ent_to.pack(side="right", padx=2, ipady=3)
        tk.Button(date_row, text="📅", command=lambda: self.open_date_picker(ent_to, load_sales_data, allow_future=False), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_BLUE, relief="flat", cursor="hand2").pack(side="right", padx=2)

        def set_quick_dates(mode):
            now = datetime.now()
            ent_from.delete(0, tk.END)
            ent_to.delete(0, tk.END)
            if mode == "today":
                d_s = now.strftime("%Y-%m-%d")
                ent_from.insert(0, d_s)
                ent_to.insert(0, d_s)
            elif mode == "month":
                ent_from.insert(0, now.strftime("%Y-%m-01"))
                ent_to.insert(0, now.strftime("%Y-%m-%d"))
            load_sales_data()

        tk.Button(date_row, text="🔍 بحث وتحديث", command=lambda: load_sales_data(), bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 9, "bold"), padx=12, pady=3, relief="flat", cursor="hand2").pack(side="right", padx=(10, 4))
        tk.Button(date_row, text="اليوم", command=lambda: set_quick_dates("today"), bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 9, "bold"), padx=10, pady=3, relief="flat", cursor="hand2").pack(side="right", padx=2)
        tk.Button(date_row, text="هذا الشهر", command=lambda: set_quick_dates("month"), bg=self.COLOR_PURPLE, fg="white", font=("Segoe UI", 9, "bold"), padx=10, pady=3, relief="flat", cursor="hand2").pack(side="right", padx=2)
        tk.Button(date_row, text="عرض الكل", command=lambda: set_quick_dates("all"), bg=self.COLOR_TOPBAR, fg="white", font=("Segoe UI", 9, "bold"), padx=10, pady=3, relief="flat", cursor="hand2").pack(side="right", padx=2)

        search_actions_row = tk.Frame(filter_container, bg=self.COLOR_CARD)
        search_actions_row.pack(fill="x", pady=(4, 0))

        tk.Label(search_actions_row, text="🔍 بحث بـ:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right", padx=(0, 4))
        rep_search_type_cb = ttk.Combobox(search_actions_row, values=["الكل (شامل)", "اسم العميل", "سيريال IMEI", "كود الجهاز / الفاتورة #ID", "الموديل والماركة", "اسم البائع"], state="readonly", width=16, font=("Segoe UI", 9, "bold"), justify="right")
        rep_search_type_cb.current(0)
        rep_search_type_cb.pack(side="right", padx=(0, 4), ipady=2)

        ent_q = tk.Entry(search_actions_row, font=("Segoe UI", 10, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="right", width=20)
        ent_q.pack(side="right", padx=4, ipady=3)

        def print_selected_sale_invoice():
            sel = stree.selection()
            if not sel:
                messagebox.showwarning("تنبيه", "يرجى تحديد عملية بيع من الجدول أولاً!")
                return
            vals = stree.item(sel[0]).get('values', [])
            if len(vals) >= 12:
                s_id = clean_id_val(vals[11])
                if s_id:
                    self.print_sale_invoice_by_id(s_id)

        def return_selected_sale():
            if not (self.has_permission('can_process_returns') or self.has_permission('can_edit_transactions') or self.has_permission('can_delete_sales')):
                messagebox.showerror("صلاحيات غير كافية", "عفواً، لا تملك صلاحية استرجاع أو إلغاء عمليات البيع!")
                return
            sel = stree.selection()
            if not sel:
                messagebox.showwarning("تنبيه", "يرجى تحديد عملية بيع من الجدول أولاً!")
                return
            vals = stree.item(sel[0]).get('values', [])
            if len(vals) >= 12:
                d_id = clean_id_val(vals[10])
                s_id = clean_id_val(vals[11])
                dev_title = vals[9]
                cust_name = vals[7]
                if not d_id:
                    return
                msg = f"هل تريد بالتأكيد إلغاء عملية البيع #{s_id} واسترجاع الجهاز #{d_id} ({dev_title}) للعميل ({cust_name}) وإعادته للمخزون؟\n\nسيتم تحديث الخزينة والمخزون وحسابات العميل تلقائياً."
                if messagebox.askyesno("تأكيد الاسترجاع وإلغاء البيع", msg):
                    try:
                        self.db.process_return(d_id, self.current_user_id)
                        messagebox.showinfo("تم الاسترجاع", f"تم استرجاع الجهاز #{d_id} وإلغاء الفاتورة وإعادته للمخزون بنجاح!")
                        load_sales_data()
                    except Exception as ex:
                        messagebox.showerror("خطأ", str(ex))

        if self.has_permission('can_process_returns') or self.has_permission('can_delete_sales') or self.has_permission('can_edit_transactions'):
            tk.Button(
                search_actions_row, text="↩️ استرجاع وإلغاء البيع", command=return_selected_sale,
                bg=self.COLOR_WARN, fg="#111111", font=("Segoe UI", 9, "bold"), padx=12, pady=3, relief="flat", cursor="hand2"
            ).pack(side="left", padx=3)

        tk.Button(
            search_actions_row, text="🧾 طباعة الفاتورة", command=print_selected_sale_invoice,
            bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 9, "bold"), padx=12, pady=3, relief="flat", cursor="hand2"
        ).pack(side="left", padx=3)

        tk.Button(
            search_actions_row, text="📱 بيانات الجهاز", command=lambda: open_selected_sale_device(),
            bg=self.COLOR_TEAL, fg="white", font=("Segoe UI", 9, "bold"), padx=12, pady=3, relief="flat", cursor="hand2"
        ).pack(side="left", padx=3)

        table_card = tk.Frame(parent_frame, bg=self.COLOR_CARD, padx=12, pady=8)
        table_card.pack(fill="both", expand=True, padx=18, pady=(0, 14))

        cols = (
            "التاريخ", "البائع", "صافي الربح", "المتبقي", "المدفوع",
            "سعر البيع", "سعر الشراء", "العميل", "السيريال IMEI", "الجهاز", "ID الجهاز", "فاتورة"
        )
        stree = ttk.Treeview(table_card, columns=cols, show="headings")
        self.configure_tree_row_colors(stree)
        s_widths = {
            "التاريخ": 125, "البائع": 105, "صافي الربح": 110, "المتبقي": 100,
            "المدفوع": 105, "سعر البيع": 105, "سعر الشراء": 105, "العميل": 135,
            "السيريال IMEI": 135, "الجهاز": 150, "ID الجهاز": 75, "فاتورة": 65
        }
        for c in cols:
            stree.heading(c, text=c)
            stree.column(c, anchor="center", width=s_widths.get(c, 100))

        vsb = ttk.Scrollbar(table_card, orient="vertical", command=stree.yview)
        hsb = ttk.Scrollbar(table_card, orient="horizontal", command=stree.xview)
        stree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="left", fill="y")
        hsb.pack(side="bottom", fill="x")
        stree.pack(side="right", fill="both", expand=True)

        def on_sale_table_double_click(event):
            sel = stree.selection()
            if not sel:
                return
            vals = stree.item(sel[0]).get('values', [])
            if len(vals) >= 12:
                col = stree.identify_column(event.x)
                if col == '#12':
                    s_id = clean_id_val(vals[11])
                    if s_id:
                        self.print_sale_invoice_by_id(s_id)
                        return
                dev_id = clean_id_val(vals[10])
                if dev_id:
                    self.show_device_details_modal(dev_id)

        stree.bind("<Double-1>", on_sale_table_double_click)

        def open_selected_sale_device():
            sel = stree.selection()
            if not sel:
                messagebox.showwarning("تنبيه", "يرجى تحديد عملية بيع من الجدول أولاً!")
                return
            vals = stree.item(sel[0]).get('values', [])
            if len(vals) >= 11:
                dev_id = clean_id_val(vals[10])
                if dev_id:
                    self.show_device_details_modal(dev_id)

        def load_sales_data(event=None):
            stree.delete(*stree.get_children())
            d_from = ent_from.get().strip() or None
            d_to = ent_to.get().strip() or None
            q = ent_q.get().strip().lower()
            stype = rep_search_type_cb.get()

            rows = self.db.get_sales_report(start_date=d_from, end_date=d_to)
            tot_sales = 0.0
            tot_cost = 0.0
            tot_prof = 0.0

            for idx_r, r in enumerate(rows, 1):
                dev_name = f"{r.get('category') or ''} {r.get('model') or ''}".strip()
                s_id_val = r.get('sale_id') or r.get('id') or 0
                d_id_val = r.get('device_id') or 0
                if q:
                    if "العميل" in stype:
                        if q not in str(r.get('customer_name') or '').lower():
                            continue
                    elif "سيريال" in stype:
                        if q not in str(r.get('imei_serial') or '').lower():
                            continue
                    elif "كود" in stype or "#ID" in stype:
                        clean_q = clean_id_val(q)
                        if clean_q is None or (s_id_val != clean_q and d_id_val != clean_q):
                            continue
                    elif "الموديل" in stype:
                        if q not in dev_name.lower():
                            continue
                    elif "البائع" in stype:
                        if q not in str(r.get('seller_name') or '').lower():
                            continue
                    else:
                        searchable = f"{s_id_val} {d_id_val} {dev_name} {r.get('imei_serial')} {r.get('customer_name')} {r.get('seller_name')}".lower()
                        if q not in searchable:
                            continue

                sp = float(r.get('sell_price') or 0)
                bp = float(r.get('buy_price') or 0)
                np = float(r.get('net_profit') or (sp - bp))

                tot_sales += sp
                tot_cost += bp
                tot_prof += np

                bp_txt = fmt_curr(bp) if can_see_buy else "🔒 مخفي"
                np_txt = fmt_curr(np) if (can_see_prof and can_see_buy) else "🔒 مخفي"

                row_tag = 'evenrow' if idx_r % 2 == 0 else 'oddrow'
                item_iid = f"sale_{s_id_val}_{idx_r}"
                stree.insert("", "end", iid=item_iid, tags=(row_tag,), values=(
                    r.get('sell_date_formatted') or "-",
                    fix_bidi(r.get('seller_name') or "-"),
                    np_txt,
                    fmt_curr(r.get('remaining_balance')),
                    fmt_curr(r.get('cash_received')),
                    fmt_curr(sp),
                    bp_txt,
                    fix_bidi(r.get('customer_name') or "-"),
                    r.get('imei_serial') or "-",
                    fix_bidi(dev_name),
                    f"#{d_id_val}",
                    f"#{s_id_val}"
                ))

            lbl_period_sales.config(text=fmt_curr(tot_sales))
            if can_see_buy:
                lbl_period_cost.config(text=fmt_curr(tot_cost))
            if can_see_prof and can_see_buy:
                lbl_period_profit.config(text=fmt_curr(tot_prof))

            self.after(50, lambda: stree.xview_moveto(1.0))

        ent_q.bind("<KeyRelease>", load_sales_data)
        rep_search_type_cb.bind("<<ComboboxSelected>>", load_sales_data)
        load_sales_data()

    def open_liquidity_log_modal(self):
        if not self.has_permission('can_view_liquidity_log'):
            messagebox.showerror("صلاحيات غير كافية", "عفواً، لا تملك صلاحية عرض سجل حركات السيولة!")
            return

        lwin = tk.Toplevel(self)
        lwin.title("سجل تفاصيل حركات السيولة")
        lwin.geometry("820x560")
        lwin.configure(bg=self.COLOR_BG)
        lwin.grab_set()

        top_bar = tk.Frame(lwin, bg=self.COLOR_TOPBAR, pady=10, padx=16)
        top_bar.pack(fill="x")
        tk.Label(top_bar, text="📜 سجل تفاصيل إضافة وسحب السيولة", font=("Segoe UI", 13, "bold"), bg=self.COLOR_TOPBAR, fg="#38bdf8").pack(side="right")

        bot_bar = tk.Frame(lwin, bg=self.COLOR_TOPBAR, pady=8, padx=16)
        bot_bar.pack(side="bottom", fill="x")
        tk.Button(bot_bar, text="إغلاق", command=lwin.destroy, bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 10, "bold"), padx=18, pady=4, relief="flat", cursor="hand2").pack(side="left")

        scroll_body = self._create_scrollable_frame(lwin, bg_color=self.COLOR_BG, pad_x=16, pad_y=10)

        t_card = tk.Frame(scroll_body, bg=self.COLOR_CARD, padx=12, pady=10)
        t_card.pack(fill="both", expand=True)

        cols = ("الملاحظة / البيان", "المبلغ", "نوع العملية", "المضيف", "التاريخ والوقت", "م")
        tree = ttk.Treeview(t_card, columns=cols, show="headings", height=16)
        self.configure_tree_row_colors(tree)
        widths = {"الملاحظة / البيان": 250, "المبلغ": 120, "نوع العملية": 115, "المضيف": 135, "التاريخ والوقت": 140, "م": 55}
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, anchor="center", width=widths.get(c, 110))
        tree.pack(fill="both", expand=True)

        for idx_t, tr in enumerate(self.db.get_capital_transactions(), 1):
            raw_t = tr.get('transaction_type')
            if raw_t == 'SUPPLIER_REFUND':
                tp_ar = "استرداد رصيد مورد (+)"
            elif raw_t in ('WITHDRAWAL', 'WITHDRAW'):
                tp_ar = "سحب سيولة (-)"
            else:
                tp_ar = "إيداع سيولة (+)"
            row_tag = 'evenrow' if idx_t % 2 == 0 else 'oddrow'
            tree.insert("", "end", tags=(row_tag,), values=(
                fix_bidi(tr.get('notes') or "-"),
                fmt_curr(tr.get('amount')),
                fix_bidi(tp_ar),
                fix_bidi(tr.get('created_by_name') or "-"),
                tr.get('date_formatted') or "-",
                idx_t
            ))

    def view_audit_logs(self):
        if not self.has_permission('can_view_audit_logs'):
            messagebox.showerror("صلاحيات غير كافية", "عفواً، لا تملك صلاحية عرض سجل العمليات!")
            return

        self.current_view_func = self.view_audit_logs
        self.build_main_ui(keep_view=True)
        self.clear_content()

        top_hdr = tk.Frame(self.content_frame, bg=self.COLOR_BG, padx=18, pady=8)
        top_hdr.pack(fill="x")

        tk.Label(
            top_hdr, text="📜 السجل الدقيق للعمليات والتغييرات (Audit Trail)",
            font=("Segoe UI", 16, "bold"), bg=self.COLOR_BG, fg=self.COLOR_BLUE
        ).pack(side="right")

        lbl_total_logs = tk.Label(
            top_hdr, text="إجمالي العمليات: 0",
            bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"), padx=12, pady=4
        )
        lbl_total_logs.pack(side="left")

        filter_bar = tk.Frame(self.content_frame, bg=self.COLOR_CARD, padx=14, pady=10)
        filter_bar.pack(fill="x", padx=18, pady=(0, 8))

        row_al1 = tk.Frame(filter_bar, bg=self.COLOR_CARD)
        row_al1.pack(fill="x", pady=(0, 6))

        tk.Label(row_al1, text="🔍 بحث في السجل:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right", padx=4)
        search_ent = tk.Entry(row_al1, font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="right", width=22)
        search_ent.pack(side="right", padx=6, ipady=3)

        tk.Label(row_al1, text="نوع العملية:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right", padx=(10, 4))
        filter_choices = [
            "الكل",
            "⚠️ حالات غير اعتيادية ومشبوهة (ANOMALY)",
            "🛒 مبيعات (SALE)",
            "🔄 استرجاع أجهزة (RETURN_DEVICE)",
            "💵 تحصيل ديون عملاء (COLLECT_DEBT)",
            "🏭 سداد موردين (PAY_SUPPLIER)",
            "🌟 استرداد رصيد دائن (CLAIM_SUPPLIER_CREDIT)",
            "➕ إضافة أجهزة (ADD_DEVICE)",
            "✏️ تعديل أجهزة (EDIT_DEVICE)",
            "🗑️ حذف أجهزة (DELETE_DEVICE)",
            "💰 حركات السيولة (CAPITAL)",
            "🗑️ تسوية حركة سيولة (DELETE_CAPITAL_TX)",
            "🏭 إدارة الموردين (SUPPLIER)",
            "👤 إدارة المستخدمين (USER)",
            "📅 تعديل تواريخ العمليات (UPDATE_DATE)"
        ]
        action_filter_cb = ttk.Combobox(row_al1, values=filter_choices, state="readonly", width=28, font=("Segoe UI", 10, "bold"), justify="right")
        action_filter_cb.current(0)
        action_filter_cb.pack(side="right", padx=4, ipady=2)

        row_al2 = tk.Frame(filter_bar, bg=self.COLOR_CARD)
        row_al2.pack(fill="x", pady=(2, 0))

        tk.Label(row_al2, text="📅 من تاريخ:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right", padx=(4, 2))
        ent_audit_from = tk.Entry(row_al2, font=("Segoe UI", 10, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, justify="center", width=12)
        today_al_str = datetime.now().strftime("%Y-%m-%d")
        ent_audit_from.insert(0, today_al_str)
        ent_audit_from.pack(side="right", padx=2, ipady=2)

        btn_dp_from = tk.Button(row_al2, text="📅", bg=self.COLOR_ENTRY_BG, fg=self.COLOR_BLUE, relief="flat", cursor="hand2")
        btn_dp_from.pack(side="right", padx=2)

        tk.Label(row_al2, text="إلى تاريخ:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right", padx=(8, 2))
        ent_audit_to = tk.Entry(row_al2, font=("Segoe UI", 10, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, justify="center", width=12)
        ent_audit_to.insert(0, today_al_str)
        ent_audit_to.pack(side="right", padx=2, ipady=2)

        btn_dp_to = tk.Button(row_al2, text="📅", bg=self.COLOR_ENTRY_BG, fg=self.COLOR_BLUE, relief="flat", cursor="hand2")
        btn_dp_to.pack(side="right", padx=2)

        btn_today = tk.Button(row_al2, text="اليوم", bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", padx=6, pady=2)
        btn_today.pack(side="right", padx=2)

        btn_month = tk.Button(row_al2, text="هذا الشهر", bg=self.COLOR_PURPLE, fg="white", font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", padx=6, pady=2)
        btn_month.pack(side="right", padx=2)

        btn_clear_dates = tk.Button(row_al2, text="مسح", bg=self.COLOR_ENTRY_BG, fg=self.COLOR_MUTED, font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2", padx=6, pady=2)
        btn_clear_dates.pack(side="right", padx=2)

        btn_diff = tk.Button(
            row_al2, text="🔍 تفاصيل التغييرات (Diff)",
            bg=self.COLOR_INDIGO, fg="white", font=("Segoe UI", 9, "bold"),
            padx=14, pady=3, relief="flat", cursor="hand2"
        )
        btn_diff.pack(side="left", padx=4)

        btn_refresh = tk.Button(
            row_al2, text="🔄 تحديث",
            bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 9, "bold"),
            padx=14, pady=3, relief="flat", cursor="hand2"
        )
        btn_refresh.pack(side="left", padx=4)

        table_card = tk.Frame(self.content_frame, bg=self.COLOR_CARD, padx=12, pady=8)
        table_card.pack(fill="both", expand=True, padx=18, pady=(0, 14))

        cols = ("التاريخ والوقت", "المستخدم", "نوع العملية", "الكيان", "رقم الكيان", "تفاصيل العملية", "م")
        ltree = ttk.Treeview(table_card, columns=cols, show="headings")
        self.configure_tree_row_colors(ltree)
        l_widths = {
            "التاريخ والوقت": 140, "المستخدم": 130, "نوع العملية": 160,
            "الكيان": 100, "رقم الكيان": 85, "تفاصيل العملية": 410, "م": 50
        }
        for c in cols:
            ltree.heading(c, text=c)
            ltree.column(c, anchor="center" if c != "تفاصيل العملية" else "e", width=l_widths.get(c, 100))

        ltree.tag_configure("act_anomaly", foreground="#f43f5e")
        ltree.tag_configure("act_sale", foreground="#10b981")
        ltree.tag_configure("act_delete", foreground="#ef4444")
        ltree.tag_configure("act_edit", foreground="#f59e0b")
        ltree.tag_configure("act_add", foreground="#38bdf8")
        ltree.tag_configure("act_pay", foreground="#06b6d4")
        ltree.tag_configure("act_norm", foreground=self.COLOR_TEXT)

        vsb = ttk.Scrollbar(table_card, orient="vertical", command=ltree.yview)
        hsb = ttk.Scrollbar(table_card, orient="horizontal", command=ltree.xview)
        ltree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="left", fill="y")
        hsb.pack(side="bottom", fill="x")
        ltree.pack(side="right", fill="both", expand=True)

        logs_data_map = {}

        def open_selected_log_details(event=None):
            selected_row = None
            if event and hasattr(event, 'y'):
                row_under = ltree.identify_row(event.y)
                if row_under:
                    ltree.selection_set(row_under)
                    selected_row = row_under

            if not selected_row:
                sel = ltree.selection()
                if sel:
                    selected_row = sel[0]

            if not selected_row:
                messagebox.showwarning("تنبيه", "يرجى تحديد عملية من جدول السجل أولاً!")
                return

            log_id_val = clean_id_val(selected_row)
            log_item = logs_data_map.get(log_id_val)
            if not log_item and log_id_val:
                logs_res = self.db.get_audit_logs(limit=1, log_id=log_id_val)
                if logs_res:
                    log_item = logs_res[0]

            if not log_item:
                messagebox.showwarning("تنبيه", "تعذر العثور على بيانات هذه العملية!")
                return

            dwin = tk.Toplevel(self)
            dwin.title(f"تفاصيل العملية #{log_item['id']} - {log_item.get('action_type')}")
            dwin.geometry("720x620")
            dwin.configure(bg=self.COLOR_BG)
            dwin.grab_set()

            top_b = tk.Frame(dwin, bg=self.COLOR_TOPBAR, pady=10, padx=16)
            top_b.pack(fill="x")
            tk.Label(
                top_b,
                text=fix_bidi(f"📜 تفاصيل العملية #{log_item['id']}  |  {log_item.get('action_type')}"),
                font=("Segoe UI", 12, "bold"), bg=self.COLOR_TOPBAR,
                fg="#0284c7" if not self.is_dark_mode else "#38bdf8"
            ).pack(side="right")

            bot_b = tk.Frame(dwin, bg=self.COLOR_TOPBAR, pady=8, padx=16)
            bot_b.pack(side="bottom", fill="x")
            tk.Button(bot_b, text="إغلاق", command=dwin.destroy, bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 10, "bold"), padx=16, pady=4, relief="flat", cursor="hand2").pack(side="left")

            body_scroll = self._create_scrollable_frame(dwin, bg_color=self.COLOR_BG, pad_x=16, pad_y=12)

            act_code = str(log_item.get('action_type') or '')
            desc_text = str(log_item.get('description') or '')
            if "⚠️" in desc_text or act_code in ('SALE_PRICE_BELOW_INITIAL', 'SALE_PRICE_ABOVE_INITIAL', 'UPDATE_PRICE_BELOW', 'UPDATE_PRICE_ABOVE', 'SALE_BELOW_COST'):
                warn_card = tk.Frame(body_scroll, bg="#fef2f2", highlightthickness=1, highlightbackground="#f87171", padx=12, pady=8)
                warn_card.pack(fill="x", pady=(0, 10))
                tk.Label(warn_card, text="⚠️ تم رصد حالة خاصة / غير اعتيادية في هذه العملية (تخفيض أو تعديل سعر أو عملية استثنائية)", bg="#fef2f2", fg="#dc2626", font=("Segoe UI", 10, "bold"), anchor="e").pack(fill="x")

            info_card = tk.LabelFrame(body_scroll, text="معلومات وبيانات العملية", bg=self.COLOR_CARD, fg=self.COLOR_BLUE, font=("Segoe UI", 10, "bold"), padx=14, pady=8)
            info_card.pack(fill="x", pady=(0, 10))

            target_entity_str = f"{log_item.get('entity_type')} #{log_item.get('entity_id')}" if log_item.get('entity_id') else str(log_item.get('entity_type') or '-')
            pairs = [
                [("التاريخ والوقت:", str(log_item.get('created_at_formatted') or log_item.get('created_at') or '-')), ("المستخدم المنفذ:", str(log_item.get('user_name') or 'النظام'))],
                [("نوع العملية:", str(log_item.get('action_type') or '-')), ("الكيان المستهدف:", target_entity_str)],
            ]
            self._build_rtl_info_grid(info_card, pairs)

            desc_card = tk.LabelFrame(body_scroll, text="📝 البيان والتفاصيل الكاملة للعملية", bg=self.COLOR_CARD, fg=self.COLOR_TEAL, font=("Segoe UI", 10, "bold"), padx=14, pady=10)
            desc_card.pack(fill="x", pady=6)

            full_desc = str(log_item.get('description') or 'لا توجد ملاحظات إضافية')
            desc_lbl = tk.Label(
                desc_card, text=fix_bidi(full_desc),
                font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT,
                justify="right", wraplength=620, anchor="e", padx=12, pady=10
            )
            desc_lbl.pack(fill="x")

            old_vals = log_item.get('old_values')
            new_vals = log_item.get('new_values')
            if isinstance(old_vals, str):
                try:
                    old_vals = json.loads(old_vals)
                except Exception:
                    pass
            if isinstance(new_vals, str):
                try:
                    new_vals = json.loads(new_vals)
                except Exception:
                    pass

            has_old = isinstance(old_vals, dict) and bool(old_vals)
            has_new = isinstance(new_vals, dict) and bool(new_vals)

            if has_old or has_new:
                diff_card = tk.LabelFrame(body_scroll, text="🔄 التغييرات المسجلة (القيم السابقة مقابل الجديدة)", bg=self.COLOR_CARD, fg=self.COLOR_ACCENT, font=("Segoe UI", 10, "bold"), padx=12, pady=8)
                diff_card.pack(fill="x", pady=6)

                field_name_map = {
                    "initial_selling_price": "سعر البيع المبدئي",
                    "sell_price": "سعر البيع الفعلي",
                    "final_selling_price": "سعر البيع النهائي",
                    "buy_price": "سعر الشراء / التكلفة",
                    "discount": "الخصم الممنوح",
                    "cash_received": "المدفوع نقداً",
                    "remaining_balance": "المتبقي / المديونية",
                    "remaining": "المتبقي",
                    "customer_name": "اسم العميل",
                    "customer_phone": "هاتف العميل",
                    "model": "الموديل",
                    "category": "نوع / ماركة الجهاز",
                    "storage": "سعة التخزين (GB)",
                    "ram": "الذاكرة (RAM)",
                    "battery": "نسبة البطارية (%)",
                    "battery_health": "صحة البطارية (%)",
                    "imei": "السيريال IMEI",
                    "color": "اللون",
                    "device_condition": "حالة الجهاز",
                    "has_box": "وجود العلبة",
                    "has_tax": "شامل الضريبة",
                    "accessories": "الملحقات المرفقة",
                    "is_sold": "حالة البيع",
                    "is_deleted": "محذوف من المخزون",
                    "loss_amount": "مبلغ الخسارة",
                    "price_diff": "فارق السعر",
                    "price_difference": "فارق السعر",
                    "difference_type": "نوع الفارق والتعديل",
                    "refund_mode": "طريقة التسوية والاسترداد",
                    "excess_amount": "المبلغ الفائض",
                    "paid_now": "المسدد حالياً",
                    "new_remaining": "المتبقي الجديد",
                    "notes": "الملاحظات والبيان",
                    "supplier_id": "رقم المورد",
                    "supplier_credit": "رصيد دائن للمورد",
                    "buy_date": "تاريخ الشراء",
                    "sell_date": "تاريخ البيع"
                }

                all_keys = set()
                if isinstance(old_vals, dict):
                    all_keys.update(old_vals.keys())
                if isinstance(new_vals, dict):
                    all_keys.update(new_vals.keys())

                d_row = 0
                tk.Label(diff_card, text="القيمة الجديدة", bg=self.COLOR_CARD, fg=self.COLOR_ACCENT, font=("Segoe UI", 10, "bold")).grid(row=d_row, column=0, sticky="ew", padx=6, pady=4)
                tk.Label(diff_card, text="القيمة السابقة", bg=self.COLOR_CARD, fg=self.COLOR_DANGER, font=("Segoe UI", 10, "bold")).grid(row=d_row, column=1, sticky="ew", padx=6, pady=4)
                tk.Label(diff_card, text="الحقل / البيان", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=d_row, column=2, sticky="e", padx=6, pady=4)

                for k in sorted(all_keys):
                    d_row += 1
                    ov = old_vals.get(k) if isinstance(old_vals, dict) else "-"
                    nv = new_vals.get(k) if isinstance(new_vals, dict) else "-"
                    f_label = field_name_map.get(k, k)
                    tk.Label(diff_card, text=str(nv if nv is not None else "-"), bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=d_row, column=0, sticky="ew", padx=6, pady=3)
                    tk.Label(diff_card, text=str(ov if ov is not None else "-"), bg=self.COLOR_CARD, fg=self.COLOR_MUTED, font=("Segoe UI", 10)).grid(row=d_row, column=1, sticky="ew", padx=6, pady=3)
                    tk.Label(diff_card, text=fix_bidi(f_label), bg=self.COLOR_CARD, fg=self.COLOR_BLUE, font=("Segoe UI", 10, "bold")).grid(row=d_row, column=2, sticky="e", padx=6, pady=3)

        def refresh_logs(event=None):
            ltree.delete(*ltree.get_children())
            logs_data_map.clear()
            raw_choice = action_filter_cb.get()
            act_type = None
            if raw_choice and raw_choice != "الكل":
                for code in ["ANOMALY", "SALE", "RETURN_DEVICE", "COLLECT_DEBT", "PAY_SUPPLIER", "CLAIM_SUPPLIER_CREDIT", "ADD_DEVICE", "EDIT_DEVICE", "DELETE_DEVICE", "CAPITAL_INJECTION", "CAPITAL", "DELETE_CAPITAL_TX", "ADD_SUPPLIER", "UPDATE_SUPPLIER", "DELETE_SUPPLIER", "SUPPLIER", "ADD_USER", "UPDATE_USER_PERMISSIONS", "USER", "UPDATE_DATE"]:
                    if code in raw_choice:
                        act_type = code
                        break

            d_from = ent_audit_from.get().strip() or None
            d_to = ent_audit_to.get().strip() or None
            all_logs = self.db.get_audit_logs(action_type=act_type, limit=500, date_from=d_from, date_to=d_to)
            lbl_total_logs.config(text=f"إجمالي العمليات: {len(all_logs)}")
            q = search_ent.get().strip().lower()

            for idx, log in enumerate(all_logs, 1):
                desc = str(log.get('description') or '')
                user_nm = str(log.get('user_name') or 'النظام')
                act = str(log.get('action_type') or '')
                ent_t = str(log.get('entity_type') or '')
                ent_id = str(log.get('entity_id') or '')
                searchable = f"{desc} {user_nm} {act} {ent_t} {ent_id}".lower()
                if q and q not in searchable:
                    continue

                log_id = log['id']
                logs_data_map[log_id] = log

                act_map = {
                    'SALE': 'بيع جهاز 🛒',
                    'SALE_PRICE_BELOW_INITIAL': '⚠️ بيع بأقل من المبدئي',
                    'SALE_PRICE_ABOVE_INITIAL': '⚠️ بيع بأعلى من المبدئي',
                    'SALE_BELOW_COST': '⚠️ بيع بخسارة (أقل من الشراء)',
                    'UPDATE_PRICE_BELOW': '⚠️ تخفيض السعر المبدئي',
                    'UPDATE_PRICE_ABOVE': '⚠️ رفع السعر المبدئي',
                    'RETURN_DEVICE': 'استرجاع جهاز 🔄',
                    'COLLECT_DEBT': 'تحصيل دين عميل 💵',
                    'PAY_SUPPLIER': 'سداد مورد 🏭',
                    'ADD_DEVICE': 'إضافة جهاز جديد ➕',
                    'EDIT_DEVICE': 'تعديل بيانات جهاز ✏️',
                    'DELETE_DEVICE': 'حذف جهاز 🗑️',
                    'CAPITAL_INJECTION': 'إيداع سيولة 💰',
                    'CAPITAL_WITHDRAWAL': 'سحب سيولة 💸',
                    'DELETE_CAPITAL_TX': 'تسوية حركة سيولة 🗑️',
                    'ADD_SUPPLIER': 'إضافة مورد 🏭',
                    'UPDATE_SUPPLIER': 'تعديل مورد ✏️',
                    'DELETE_SUPPLIER': 'حذف مورد 🗑️',
                    'ADD_USER': 'إضافة مستخدم 👤',
                    'UPDATE_USER_PERMISSIONS': 'تعديل صلاحيات 🔐',
                    'EXPENSE': 'تسجيل مصروف 💸',
                    'CLAIM_SUPPLIER_CREDIT': 'استرداد نقدي من مورد 🌟',
                    'UPDATE_DATE': 'تعديل تاريخ عملية 📅'
                }
                display_act = act_map.get(act, act)

                is_anomaly = "⚠️" in desc or act in ('SALE_PRICE_BELOW_INITIAL', 'SALE_PRICE_ABOVE_INITIAL', 'UPDATE_PRICE_BELOW', 'UPDATE_PRICE_ABOVE', 'SALE_BELOW_COST')
                tag_k = "act_norm"
                if is_anomaly:
                    tag_k = "act_anomaly"
                elif "SALE" in act:
                    tag_k = "act_sale"
                elif "DELETE" in act:
                    tag_k = "act_delete"
                elif "UPDATE" in act or "EDIT" in act:
                    tag_k = "act_edit"
                elif "ADD" in act:
                    tag_k = "act_add"
                elif "PAY" in act or "COLLECT" in act or "CAPITAL" in act or "CLAIM" in act:
                    tag_k = "act_pay"

                row_tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
                ltree.insert("", "end", iid=str(log_id), tags=(row_tag, tag_k), values=(
                    log.get('created_at_formatted') or log.get('created_at') or "-",
                    fix_bidi(user_nm),
                    fix_bidi(display_act),
                    fix_bidi(ent_t),
                    f"#{ent_id}" if ent_id else "-",
                    fix_bidi(desc),
                    idx
                ))

            self.after(50, lambda: ltree.xview_moveto(1.0))

        def set_audit_today():
            now_d = datetime.now().strftime("%Y-%m-%d")
            ent_audit_from.delete(0, tk.END)
            ent_audit_from.insert(0, now_d)
            ent_audit_to.delete(0, tk.END)
            ent_audit_to.insert(0, now_d)
            refresh_logs()

        def set_audit_month():
            now = datetime.now()
            ent_audit_from.delete(0, tk.END)
            ent_audit_from.insert(0, now.strftime("%Y-%m-01"))
            ent_audit_to.delete(0, tk.END)
            ent_audit_to.insert(0, now.strftime("%Y-%m-%d"))
            refresh_logs()

        def clear_audit_dates():
            ent_audit_from.delete(0, tk.END)
            ent_audit_to.delete(0, tk.END)
            refresh_logs()

        btn_dp_from.config(command=lambda: self.open_date_picker(ent_audit_from, refresh_logs, allow_future=False))
        btn_dp_to.config(command=lambda: self.open_date_picker(ent_audit_to, refresh_logs, allow_future=False))
        btn_today.config(command=set_audit_today)
        btn_month.config(command=set_audit_month)
        btn_clear_dates.config(command=clear_audit_dates)
        btn_diff.config(command=open_selected_log_details)
        btn_refresh.config(command=refresh_logs)

        ltree.bind("<Double-1>", open_selected_log_details)
        search_ent.bind("<KeyRelease>", refresh_logs)
        action_filter_cb.bind("<<ComboboxSelected>>", refresh_logs)

        refresh_logs()


if __name__ == "__main__":
    app = MasterMobileApp()
    app.mainloop()
