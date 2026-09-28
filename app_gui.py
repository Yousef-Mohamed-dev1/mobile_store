import tkinter as tk
from tkinter import ttk, messagebox
from database import DatabaseManager
from invoice_generator import generate_invoice_image
from datetime import datetime
from PIL import Image, ImageTk
import calendar
import os
import json
import re

PERMISSIONS_DICT = {
    'can_view_buy_price': 'رؤية سعر الشراء والتكلفة',
    'can_manage_inventory': 'إدارة المخزون (إضافة/تعديل/حذف أجهزة وموردين)',
    'can_manage_users': 'إدارة المستخدمين والصلاحيات بالكامل',
    'can_view_reports': 'عرض التقارير والسيولة والأرباح',
    'can_process_returns': 'إجراء مرتجعات المبيعات',
    'can_edit_prices': 'تعديل أسعار البيع والخصومات'
}

BRAND_MODELS_SUGGESTIONS = {
    "iPhone": [
        # 17 Series (2025/2026)
        "17 Pro Max", "17 Pro", "Air", "17",
        # 16 Series
        "16 Pro Max", "16 Pro", "16 Plus", "16",
        # 15 Series
        "15 Pro Max", "15 Pro", "15 Plus", "15",
        # 14 Series
        "14 Pro Max", "14 Pro", "14 Plus", "14",
        # 13 Series
        "13 Pro Max", "13 Pro", "13", "13 Mini",
        # 12 Series
        "12 Pro Max", "12 Pro", "12", "12 Mini",
        # 11 Series
        "11 Pro Max", "11 Pro", "11",
        # X / XS / XR
        "XS Max", "XS", "XR", "X",
        # 8 / 7 / 6 Series
        "8 Plus", "8", "7 Plus", "7", "6s Plus", "6s", "6 Plus", "6",
        # SE Series
        "SE 4 (2025)", "SE (2022)", "SE (2020)"
    ],
    "Samsung": [
        # S Series (Up to 2026)
        "S26 Ultra", "S26 Plus", "S26",
        "S25 Ultra", "S25 Plus", "S25", "S25 Slim",
        "S24 Ultra", "S24 Plus", "S24", "S24 FE",
        "S23 Ultra", "S23 Plus", "S23", "S23 FE",
        "S22 Ultra", "S22 Plus", "S22",
        "S21 Ultra", "S21 Plus", "S21", "S21 FE",
        "S20 Ultra", "S20 FE", "S10 Plus", "S10", "S9 Plus", "S8",
        # Note Series
        "Note 20 Ultra", "Note 20", "Note 10 Plus", "Note 10", "Note 9", "Note 8",
        # A Series (Up to A56/A36/A26)
        "A56", "A55", "A54", "A53", "A52s 5G", "A52", "A51", "A50",
        "A36", "A35", "A34", "A33", "A32", "A31", "A30",
        "A26", "A25", "A24", "A23", "A22", "A21s", "A20",
        "A16", "A15", "A14", "A13", "A12", "A11", "A10s",
        "A06", "A05s", "A05", "A04s", "A03s",
        # M Series
        "M55", "M54", "M53", "M52 5G", "M51", "M35", "M34", "M33", "M15",
        # Z Series (Fold / Flip)
        "Z Fold 7", "Z Fold 6", "Z Fold 5", "Z Fold 4", "Z Fold 3",
        "Z Flip 7", "Z Flip 6", "Z Flip 5", "Z Flip 4"
    ],
    "Oppo": [
        # Reno Series
        "14 Pro", "14", "14 F",
        "13 Pro", "13", "13 F",
        "12 Pro", "12", "12 F",
        "11 Pro", "11", "11 F",
        "10 Pro", "10",
        "8 Pro", "8", "8T 5G", "8T",
        "7 Pro", "7 5G", "7", "6 Pro", "6 5G", "6", "5 5G", "5", "4 Pro", "4", "3 Pro", "3", "2F", "2",
        # A Series
        "A80", "A79", "A78", "A77s", "A60", "A58", "A57", "A55", "A54", "A53", "A52", "A5s",
        "A38", "A31", "A18", "A17", "A16", "A15", "A12", "A5",
        # Find Series
        "Find X8 Ultra", "Find X8 Pro", "Find X7 Ultra", "Find X6 Pro", "Find X5 Pro", "Find N3", "Find N3 Flip"
    ],
    "Honor": [
        # Number Series
        "300 Pro", "300", "300 Lite",
        "200 Pro", "200", "200 Lite",
        "90", "90 Lite", "70", "50", "20 Pro", "20", "10 Lite", "8X", "9X",
        # X Series
        "X9c", "X9b", "X9a", "X9",
        "X8c", "X8b", "X8a", "X8",
        "X7c", "X7b", "X7a", "X7",
        "X6b", "X6a", "X5 Plus",
        # Magic Series
        "Magic 7 Pro", "Magic 6 Pro", "Magic 5 Pro", "Magic V3", "Magic V2"
    ],
    "Realme": [
        # Number Series
        "14 Pro Plus", "14 Pro", "14", "13 Pro Plus", "13 Pro", "13",
        "12 Pro Plus", "12 Pro", "12", "12x",
        "11 Pro Plus", "11 Pro", "11", "10 Pro Plus", "10",
        "9 Pro Plus", "9 Pro", "9i", "8 Pro", "8", "7 Pro", "7", "6 Pro", "6", "6i", "5 Pro", "5", "3 Pro",
        # C Series
        "C67", "C65", "C63", "C55", "C53", "C51", "C35", "C33", "C31", "C25s", "C21Y", "C11",
        # GT & Note Series
        "GT 7 Pro", "GT 6", "GT Neo 6", "GT Master Edition", "Note 60", "Note 50"
    ],
    "Infinix": [
        # Note Series
        "Note 50 Pro Plus", "Note 50 Pro", "Note 50",
        "Note 40 Pro Plus", "Note 40 Pro", "Note 40",
        "Note 30 VIP", "Note 30 Pro", "Note 30", "Note 12 Pro", "Note 12", "Note 11", "Note 10 Pro", "Note 8", "Note 7",
        # Hot Series
        "Hot 50 Pro Plus", "Hot 50 Pro", "Hot 50", "Hot 50i",
        "Hot 40 Pro", "Hot 40", "Hot 40i", "Hot 30", "Hot 30i", "Hot 20", "Hot 12", "Hot 11", "Hot 10", "Hot 9", "Hot 8",
        # Smart Series
        "Smart 9", "Smart 8 Pro", "Smart 8", "Smart 7", "Smart 6",
        # Zero & GT Series
        "Zero 40 5G", "Zero 30 5G", "GT 30 Pro", "GT 20 Pro", "GT 10 Pro"
    ],
    "Huawei": [
        # P / Pura Series
        "Pura 80 Ultra", "Pura 80 Pro", "Pura 70 Ultra", "Pura 70 Pro", "Pura 70",
        "P60 Pro", "P50 Pro", "P40 Pro", "P30 Pro", "P30 Lite", "P20 Pro",
        # Mate Series
        "Mate 70 Pro", "Mate 60 Pro", "Mate 50 Pro", "Mate 40 Pro", "Mate 30 Pro", "Mate 20 Pro",
        # Nova Series
        "13 Pro", "13",
        "12s", "12i", "12 SE",
        "11 Pro", "11i", "11", "10 Pro", "10 SE", "9 SE", "8i", "7i", "5T", "3i",
        # Y / Nova Y Series
        "Y91", "Y72", "Y90", "Y70", "Y9 Prime 2019", "Y9 2019", "Y7 Prime"
    ],
    "Xiaomi": [
        # Note Series (Redmi)
        "14 Pro Plus", "14 Pro", "14",
        "13 Pro Plus", "13 Pro", "13",
        "12 Pro Plus", "12 Pro", "12", "12S",
        "11 Pro Plus", "11 Pro", "11", "11S",
        "10 Pro", "10", "10S", "9 Pro", "9S", "9", "8 Pro", "8", "7",
        # Number Series (Redmi)
        "14", "14C", "13", "13C", "12", "12C", "10", "10C", "9", "9A", "9C", "A3", "A2 Plus",
        # Flagship Series
        "15 Ultra", "15 Pro", "15", "14 Ultra", "14", "14T Pro", "14T", "13T Pro", "13T", "12T Pro", "11T Pro",
        # Poco Series
        "X7 Pro", "X7", "X6 Pro", "X6", "X5 Pro", "X3 Pro", "X3 NFC",
        "F7 Pro", "F7", "F6 Pro", "F6", "F5", "F3",
        "M7 Pro", "M6 Pro", "M5", "C75", "C65"
    ]
}

BRAND_LIST = ["iPhone", "Samsung", "Oppo", "Honor", "Realme", "Infinix", "Huawei", "Xiaomi"]

def fix_bidi(text):
    if text is None: return ""
    s = str(text)
    return f"\u200f{s}\u200f"

def fmt_curr(val):
    try:
        f = float(val)
        return f"\u200f{f:,.2f} ج.م\u200f"
    except (ValueError, TypeError):
        return "\u200f0.00 ج.م\u200f"

def fmt_num(val):
    try:
        f = float(val)
        if f.is_integer():
            return f"\u200f{int(f):,}\u200f"
        return f"\u200f{f:,.2f}\u200f"
    except (ValueError, TypeError):
        return f"\u200f{str(val)}\u200f"

def clean_id_val(val):
    """استخراج الرقم الصحيح من أي قيمة أو نص بالجدول بأمان."""
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

    def clean_id_val(self, val):
        return clean_id_val(val)

    def load_logo_icon(self):
        if os.path.exists("logo.jpg"):
            try:
                img = Image.open("logo.jpg")
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
        if not self.current_user: return False
        perms = self.current_user.get('permissions', {})
        if isinstance(perms, str):
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

    def open_date_picker(self, target_entry, on_select_callback=None):
        """نافذة تقويم تفاعلية لاختيار التاريخ بسهولة بدلاً من الإدخال اليدوي."""
        cal_win = tk.Toplevel(self)
        cal_win.title("📅 اختيار التاريخ")
        cal_win.geometry("330x340")
        cal_win.configure(bg=self.COLOR_CARD)
        cal_win.resizable(False, False)
        cal_win.grab_set()

        now = datetime.now()
        cur_val = target_entry.get().strip()
        try:
            dt_init = datetime.strptime(cur_val, "%Y-%m-%d")
            sel_year, sel_month = dt_init.year, dt_init.month
        except Exception:
            sel_year, sel_month = now.year, now.month

        top_ctrl = tk.Frame(cal_win, bg=self.COLOR_TOPBAR, pady=8, padx=8)
        top_ctrl.pack(fill="x")

        years = [str(y) for y in range(2022, now.year + 3)]
        months_ar = [
            "01 - يناير", "02 - فبراير", "03 - مارس", "04 - أبريل",
            "05 - مايو", "06 - يونيو", "07 - يوليو", "08 - أغسطس",
            "09 - سبتمبر", "10 - أكتوبر", "11 - نوفمبر", "12 - ديسمبر"
        ]

        cb_year = ttk.Combobox(top_ctrl, values=years, width=7, state="readonly", font=("Segoe UI", 10, "bold"))
        cb_year.set(str(sel_year))
        cb_year.pack(side="left", padx=4)

        cb_month = ttk.Combobox(top_ctrl, values=months_ar, width=13, state="readonly", font=("Segoe UI", 10, "bold"))
        cb_month.current(sel_month - 1)
        cb_month.pack(side="right", padx=4)

        days_frame = tk.Frame(cal_win, bg=self.COLOR_CARD, padx=10, pady=8)
        days_frame.pack(fill="both", expand=True)

        def pick_date(y, m, d):
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
        tk.Button(bot_bar, text="📍 تاريخ اليوم", command=lambda: pick_date(now.year, now.month, now.day), bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, cursor="hand2").pack(side="right", padx=15)
        tk.Button(bot_bar, text="🗑️ مسح التاريخ", command=lambda: (target_entry.delete(0, tk.END), cal_win.destroy(), on_select_callback() if on_select_callback else None), bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, cursor="hand2").pack(side="left", padx=15)

    def attach_autocomplete(self, entry_widget, get_options_callable, next_focus_widget=None, on_chosen_callback=None):
        """
        قائمة اقتراحات ذكية فورية تظهر أقرب كلمة للمكتوب، مع دعم التنقل بالأسهم والماوس و Tab و Enter.
        """
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
                on_chosen_callback(chosen_text)
            if move_next and next_focus_widget:
                next_focus_widget.focus_set()

        def show_or_update_popup(filter_text=""):
            all_opts = get_options_callable() or []
            ft = filter_text.strip().lower()
            if ft:
                starts = [o for o in all_opts if o.lower().startswith(ft)]
                contains = [o for o in all_opts if ft in o.lower() and o not in starts]
                matched = starts + contains
            else:
                matched = list(all_opts)

            if not matched:
                close_popup()
                return

            popup_state["items"] = matched[:10]

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
            w = max(entry_widget.winfo_width(), 190)
            h = min(len(popup_state["items"]), 7) * 24 + 6
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

        def on_tab_or_return(event):
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

        entry_widget.bind("<KeyRelease>", on_key_release, add="+")
        entry_widget.bind("<Down>", on_down)
        entry_widget.bind("<Up>", on_up)
        entry_widget.bind("<Return>", on_tab_or_return)
        entry_widget.bind("<Tab>", on_tab_or_return)
        entry_widget.bind("<Escape>", lambda e: close_popup())
        entry_widget.bind("<Button-1>", lambda e: self.after(60, lambda: show_or_update_popup(entry_widget.get())), add="+")
        entry_widget.bind("<FocusOut>", lambda e: self.after(180, close_popup), add="+")

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
            ("📦 المخزون", self.view_inventory, True),
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
            row_id = tree.identify_row(event.y)
            if not row_id:
                selected = tree.selection()
                if not selected:
                    return
                row_id = selected[0]

            # محاولة استخراج ID الجهاز مباشرة من iid إذا كان رقمياً
            iid_clean = clean_id_val(row_id)
            item_vals = tree.item(row_id).get('values', [])
            cols = list(tree['columns'])

            idx = -1
            for search_col in [target_column_name, "ID الجهاز", "ID"]:
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

    def show_device_details_modal(self, device_id):
        dev_id_clean = clean_id_val(device_id)
        details = self.db.get_device_full_details(dev_id_clean)
        if not details or not details.get('device'):
            messagebox.showerror("خطأ", f"تعذر جلب تفاصيل الجهاز #{device_id}")
            return

        dev = details['device']
        sale = details.get('sale')
        payments = details.get('customer_payments', [])

        dwin = tk.Toplevel(self)
        dwin.title(f"تفاصيل الجهاز الشاملة #{dev['id']} - {dev['category']} {dev['model']}")
        dwin.geometry("780x760")
        dwin.configure(bg=self.COLOR_BG)
        dwin.grab_set()

        header = tk.Frame(dwin, bg=self.COLOR_TOPBAR, pady=12)
        header.pack(fill="x")
        title_txt = fix_bidi(f"📱 بيانات الجهاز التفصيلية: {dev['category']} {dev['model']} (ID: #{dev['id']})")
        tk.Label(header, text=title_txt, font=("Segoe UI", 14, "bold"), bg=self.COLOR_TOPBAR, fg=self.COLOR_BLUE).pack()

        main_scroll = tk.Frame(dwin, bg=self.COLOR_BG, padx=20, pady=12)
        main_scroll.pack(fill="both", expand=True)

        card1 = tk.LabelFrame(main_scroll, text="📋 المواصفات وبيانات الشراء", bg=self.COLOR_CARD, fg=self.COLOR_BLUE, font=("Segoe UI", 11, "bold"), padx=15, pady=10)
        card1.pack(fill="x", pady=6)

        can_see_cost = self.has_permission('can_view_buy_price')
        buy_p_str = fmt_curr(dev['buy_price']) if can_see_cost else "***"

        bat_str = f"{dev['battery_health']}%" if dev.get('battery_health') else "لا يوجد"
        ram_str = dev.get('ram') or "لا يوجد"
        cond_str = dev.get('device_condition') or "مستعمل"
        box_str = "بعلبة 📦" if dev.get('has_box') else "بدون علبة"
        buy_notes_str = dev.get('notes') or "لا يوجد"

        info_grid1 = [
            (fix_bidi(f"السيريال / IMEI: {dev['imei_serial']}"), fix_bidi(f"الماركة / الفئة: {dev['category']}")),
            (fix_bidi(f"الموديل: {dev['model']}"), fix_bidi(f"المساحة / الرام: {dev.get('storage') or '-'} / {ram_str}")),
            (fix_bidi(f"حالة الجهاز: {cond_str}"), fix_bidi(f"العلبة: {box_str}")),
            (fix_bidi(f"نسبة البطارية: {bat_str}"), fix_bidi(f"سعر الشراء: {buy_p_str}")),
            (fix_bidi(f"المورد: {dev.get('supplier_name') or '-'}"), fix_bidi(f"تاريخ الشراء: {dev.get('buy_date_formatted') or '-'}")),
            (fix_bidi(f"بواسطة المستخدم: {dev.get('created_by_name') or '-'}"), fix_bidi(f"الحالة بالمخزن: {'محذوف 🗑️' if dev.get('is_deleted') else ('مباع 🔴' if dev.get('is_sold') else 'بالمخزن 🟢')}")),
            (fix_bidi(f"ملاحظات الشراء: {buy_notes_str}"), "")
        ]

        for r_idx, (c1, c2) in enumerate(info_grid1):
            tk.Label(card1, text=c1, font=("Segoe UI", 10, "bold" if r_idx == 2 else "normal"), bg=self.COLOR_CARD, fg=self.COLOR_TEXT, anchor="e").grid(row=r_idx, column=1, sticky="ew", padx=10, pady=3)
            tk.Label(card1, text=c2, font=("Segoe UI", 10, "bold" if r_idx == 2 else "normal"), bg=self.COLOR_CARD, fg=self.COLOR_TEXT, anchor="e").grid(row=r_idx, column=0, sticky="ew", padx=10, pady=3)
            card1.grid_columnconfigure(0, weight=1)
            card1.grid_columnconfigure(1, weight=1)

        card2 = tk.LabelFrame(main_scroll, text="🛒 بيانات البيع والعميل", bg=self.COLOR_CARD, fg=self.COLOR_BLUE, font=("Segoe UI", 11, "bold"), padx=15, pady=10)
        card2.pack(fill="x", pady=6)

        if sale:
            net_p_str = fmt_curr(sale['net_profit']) if can_see_cost else "***"
            sale_notes_str = sale.get('notes') or "لا يوجد"
            info_grid2 = [
                (fix_bidi(f"رقم الفاتورة: #{sale['id']}"), fix_bidi(f"اسم العميل: {sale['customer_name']}")),
                (fix_bidi(f"هاتف العميل: {sale.get('customer_phone') or '-'}"), fix_bidi(f"سعر البيع: {fmt_curr(sale['sell_price'])}")),
                (fix_bidi(f"المدفوع: {fmt_curr(sale['cash_received'])}"), fix_bidi(f"المتبقي (الآجل): {fmt_curr(sale['remaining_balance'])}")),
                (fix_bidi(f"صافي الربح: {net_p_str}"), fix_bidi(f"تاريخ البيع: {sale.get('sell_date_formatted') or '-'}")),
                (fix_bidi(f"المستلم / البائع: {sale.get('seller_name') or '-'}"), fix_bidi(f"حالة الدفع: {sale.get('payment_status') or '-'}")),
                (fix_bidi(f"ملاحظات البيع: {sale_notes_str}"), "")
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
            card3.pack(fill="both", expand=True, pady=6)

            cols = ("المستلم", "المبلغ المدفوع", "تاريخ الدفعة")
            ptree = ttk.Treeview(card3, columns=cols, show="headings", height=4)
            for c in cols:
                ptree.heading(c, text=c)
                ptree.column(c, anchor="center")
            ptree.pack(fill="both", expand=True)

            for p in payments:
                ptree.insert("", "end", values=(p['receiver_name'], fmt_curr(p['payment_amount']), p['payment_date_formatted']))

    def view_user_management(self):
        self.current_view_func = self.view_user_management
        self.clear_content()

        tk.Label(self.content_frame, text="👥 إدارة المستخدمين والصلاحيات", font=("Segoe UI", 15, "bold"), bg=self.COLOR_BG, fg=self.COLOR_BLUE).pack(pady=10)

        columns = ("الحالة", "الاسم الكامل", "اسم المستخدم", "ID")
        tree = ttk.Treeview(self.content_frame, columns=columns, show="headings", height=8)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=140, anchor="center")
        tree.pack(fill="x", padx=15, pady=5)

        def load_users():
            for r in tree.get_children(): tree.delete(r)
            users = self.db.get_all_users()
            for u in users:
                st = "نشط 🟢" if u['is_active'] else "معطل 🔴"
                tree.insert("", "end", values=(st, u['full_name'], u['username'], u['id']))

        load_users()

        btn_bar = tk.Frame(self.content_frame, bg=self.COLOR_BG)
        btn_bar.pack(pady=15)

        def open_user_dialog(user_data=None):
            is_edit = user_data is not None
            uwin = tk.Toplevel(self)
            uwin.title("تعديل مستخدم" if is_edit else "إضافة مستخدم جديد")
            uwin.geometry("450x560")
            uwin.configure(bg=self.COLOR_CARD)
            uwin.grab_set()

            title_txt = "✏️ تعديل بيانات وصلاحيات المستخدم" if is_edit else "➕ إضافة مستخدم جديد"
            tk.Label(uwin, text=title_txt, font=("Segoe UI", 13, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_BLUE).pack(pady=10)

            form = tk.Frame(uwin, bg=self.COLOR_CARD, padx=15)
            form.pack(fill="both", expand=True)

            tk.Label(form, text="اسم المستخدم (Login):", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="e", pady=(5, 1))
            e_uname = tk.Entry(form, font=("Segoe UI", 10), justify="center", bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT)
            if is_edit:
                e_uname.insert(0, user_data['username'])
                e_uname.config(state="disabled")
            e_uname.pack(fill="x", pady=3)

            pass_label_txt = "كلمة المرور الجديدة (اتركها فارغة للتعديل بدون تغيير):" if is_edit else "كلمة المرور:"
            tk.Label(form, text=pass_label_txt, bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="e", pady=(5, 1))
            e_pass = tk.Entry(form, show="*", font=("Segoe UI", 10), justify="center", bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT)
            e_pass.pack(fill="x", pady=3)

            tk.Label(form, text="الاسم الكامل:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="e", pady=(5, 1))
            e_fname = tk.Entry(form, font=("Segoe UI", 10), justify="right", bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT)
            if is_edit:
                e_fname.insert(0, user_data['full_name'])
            e_fname.pack(fill="x", pady=3)

            tk.Label(form, text="🔒 الصلاحيات الممنوحة للمستخدم:", bg=self.COLOR_CARD, fg=self.COLOR_BLUE, font=("Segoe UI", 11, "bold")).pack(anchor="e", pady=(10, 5))

            current_perms = {}
            if is_edit:
                p_raw = user_data.get('permissions', {})
                if isinstance(p_raw, str):
                    try: current_perms = json.loads(p_raw)
                    except: current_perms = {}
                else:
                    current_perms = p_raw or {}

            perms_vars = {}
            for perm_key, ar_label in PERMISSIONS_DICT.items():
                default_val = current_perms.get(perm_key, True if not is_edit and perm_key in ['can_view_buy_price', 'can_edit_prices'] else False)
                var = tk.BooleanVar(value=default_val)
                perms_vars[perm_key] = var
                cb = tk.Checkbutton(form, text=fix_bidi(ar_label), variable=var, bg=self.COLOR_CARD, fg=self.COLOR_TEXT, selectcolor=self.COLOR_CARD, font=("Segoe UI", 10), anchor="w")
                cb.pack(fill="x", pady=2)

            if not is_edit:
                e_uname.bind("<Return>", lambda e: e_pass.focus())
            e_pass.bind("<Return>", lambda e: e_fname.focus())

            def save_user_action():
                username = e_uname.get().strip()
                password = e_pass.get().strip()
                fullname = e_fname.get().strip()

                if not is_edit and (not username or not password or not fullname):
                    messagebox.showwarning("تنبيه", "برجاء استكمال كافة البيانات الأساسية!")
                    return

                if is_edit and not fullname:
                    messagebox.showwarning("تنبيه", "برجاء إدخال الاسم الكامل!")
                    return

                p_dict = {k: v.get() for k, v in perms_vars.items()}

                if is_edit:
                    self.db.update_user(user_data['id'], fullname, p_dict, password if password else None)
                    messagebox.showinfo("تم", "تم تحديث بيانات وصلاحيات المستخدم بنجاح!")
                else:
                    self.db.add_user(username, password, fullname, p_dict)
                    messagebox.showinfo("تم", "تم إضافة المستخدم الجديد بنجاح!")

                uwin.destroy()
                load_users()

            e_fname.bind("<Return>", lambda e: save_user_action())
            tk.Button(uwin, text="💾 حفظ البيانات", command=save_user_action, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 11, "bold"), pady=5, cursor="hand2").pack(pady=12)

        def edit_selected_user():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("تنبيه", "يرجى تحديد مستخدم لتعديله!")
                return
            uid = tree.item(sel[0])['values'][3]
            users = self.db.get_all_users()
            target_u = next((u for u in users if u['id'] == uid), None)
            if target_u:
                open_user_dialog(target_u)

        def toggle_user_status():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("تنبيه", "يرجى تحديد مستخدم!")
                return
            uid = tree.item(sel[0])['values'][3]
            if uid == self.current_user['id']:
                messagebox.showwarning("تنبيه", "لا يمكنك تعطيل حسابك الحالي أثناء تسجيل الدخول!")
                return
            if messagebox.askyesno("تأكيد", "هل تريد تغيير حالة تفعيل/تعطيل هذا المستخدم؟"):
                self.db.toggle_user_active(uid)
                load_users()

        tk.Button(btn_bar, text="➕ إضافة مستخدم جديد", command=lambda: open_user_dialog(), bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"), cursor="hand2").pack(side="right", padx=5)
        tk.Button(btn_bar, text="✏️ تعديل المستخدم والصلاحيات", command=edit_selected_user, bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold"), cursor="hand2").pack(side="right", padx=5)
        tk.Button(btn_bar, text="🔄 تفعيل/تعطيل الحساب", command=toggle_user_status, bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 10, "bold"), cursor="hand2").pack(side="right", padx=5)

    def view_inventory(self):
        """شاشة المخزون مع دعم قارئ باركود السيريال الفوري، شاشة الفلترة الشاملة، التعديل، والحذف الذكي."""
        self.current_view_func = self.view_inventory
        self.clear_content()

        active_filters = {
            'search_query': '',
            'search_by': 'ALL',
            'category': 'الكل',
            'condition': 'الكل',
            'has_box': 'الكل',
            'supplier_id': 'ALL',
            'date_from': '',
            'date_to': ''
        }

        top_frame = tk.Frame(self.content_frame, bg=self.COLOR_BG)
        top_frame.pack(fill="x", padx=15, pady=8)

        tk.Label(top_frame, text="📦 المخزون", font=("Segoe UI", 16, "bold"), bg=self.COLOR_BG, fg=self.COLOR_BLUE).pack(side="right")

        search_card = tk.Frame(self.content_frame, bg=self.COLOR_CARD, padx=12, pady=8, highlightthickness=1, highlightbackground=self.COLOR_TOPBAR)
        search_card.pack(fill="x", padx=15, pady=(0, 6))

        tk.Label(search_card, text="📷 مسح سيريال IMEI / بحث سريع:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right", padx=4)
        search_entry = tk.Entry(search_card, font=("Segoe UI", 11, "bold"), width=26, justify="center", bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT)
        search_entry.pack(side="right", padx=4)
        search_entry.focus()

        tk.Label(search_card, text="بحث بـ:", bg=self.COLOR_CARD, fg=self.COLOR_MUTED, font=("Segoe UI", 9, "bold")).pack(side="right", padx=3)
        search_type_cb = ttk.Combobox(search_card, values=["السيريال / IMEI (إسكان تلقائي)", "الكل", "الاسم والموديل", "ID الجهاز"], state="readonly", width=22, font=("Segoe UI", 9, "bold"))
        search_type_cb.current(0)
        search_type_cb.pack(side="right", padx=4)

        lbl_filter_badge = tk.Label(search_card, text="الفلترة: عرض كل المتاح", bg=self.COLOR_CARD, fg=self.COLOR_ACCENT, font=("Segoe UI", 9, "bold"))
        lbl_filter_badge.pack(side="left", padx=8)

        stat_bar = tk.Frame(self.content_frame, bg=self.COLOR_TOPBAR, height=45)
        stat_bar.pack(fill="x", side="bottom")
        lbl_stat_info = tk.Label(stat_bar, text="", bg=self.COLOR_TOPBAR, fg=self.COLOR_ACCENT, font=("Segoe UI", 11, "bold"))
        lbl_stat_info.pack(pady=8)

        def update_stat_bar():
            overview = self.db.get_capital_statistics()
            can_see = self.has_permission('can_view_buy_price')
            cap_str = fmt_curr(overview['total_capital']) if can_see else "***"
            info_text = fix_bidi(f"إجمالي الأجهزة المتاحة: {fmt_num(overview['total_devices'])} جهاز  |  رأس المال بالمخزن: {cap_str}")
            lbl_stat_info.config(text=info_text)

        columns = ("النوع", "الموديل", "الحالة", "العلبة", "المساحة", "الرامات", "البطارية", "السيريال / IMEI", "سعر الشراء", "المورد", "ملاحظات الشراء", "تاريخ الشراء", "ID")
        tree = ttk.Treeview(self.content_frame, columns=columns, show="headings")

        col_widths = {
            "النوع": 85, "الموديل": 120, "الحالة": 70, "العلبة": 75,
            "المساحة": 75, "الرامات": 70, "البطارية": 70, "السيريال / IMEI": 135,
            "سعر الشراء": 95, "المورد": 110, "ملاحظات الشراء": 120, "تاريخ الشراء": 115, "ID": 60
        }
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=col_widths.get(col, 90), anchor="center")

        tree.pack(fill="both", expand=True, padx=15, pady=5)
        self.bind_treeview_double_click(tree, "ID")

        def update_filter_badge_text():
            parts = []
            if active_filters['category'] != 'الكل':
                parts.append(f"النوع: {active_filters['category']}")
            if active_filters['condition'] != 'الكل':
                parts.append(f"الحالة: {active_filters['condition']}")
            if active_filters['has_box'] != 'الكل':
                parts.append(f"العلبة: {active_filters['has_box']}")
            if active_filters['date_from'] or active_filters['date_to']:
                parts.append("بتاريخ محدد")
            if parts:
                lbl_filter_badge.config(text=fix_bidi("فلترة نشطة: " + " | ".join(parts)), fg=self.COLOR_BLUE)
            else:
                lbl_filter_badge.config(text="الفلترة: عرض كل المتاح", fg=self.COLOR_ACCENT)

        def load_tree():
            for row in tree.get_children():
                tree.delete(row)
            st_map = {
                "السيريال / IMEI (إسكان تلقائي)": "SERIAL",
                "الكل": "ALL",
                "الاسم والموديل": "NAME",
                "ID الجهاز": "ID"
            }
            active_filters['search_query'] = search_entry.get().strip()
            active_filters['search_by'] = st_map.get(search_type_cb.get(), "ALL")

            devices = self.db.get_available_inventory(
                search_query=active_filters['search_query'],
                search_by=active_filters['search_by'],
                filters=active_filters
            )
            can_see = self.has_permission('can_view_buy_price')
            for d in devices:
                buy_p = fmt_curr(d['buy_price']) if can_see else "***"
                bat_str = f"{d['battery_health']}%" if d.get('battery_health') else "لا يوجد"
                ram_str = d.get('ram') or "لا يوجد"
                cond_str = d.get('device_condition') or "مستعمل"
                box_str = "بعلبة 📦" if d.get('has_box') else "بدون علبة"
                notes_str = d.get('notes') or "-"
                tree.insert("", "end", iid=str(d['id']), values=(
                    d['category'], d['model'], cond_str, box_str, d.get('storage') or '-',
                    ram_str, bat_str, d['imei_serial'],
                    buy_p, d['supplier_name'], notes_str, d['buy_date_formatted'], d['id']
                ))
            update_stat_bar()
            update_filter_badge_text()

            if active_filters['search_query'] and active_filters['search_by'] == "SERIAL" and len(devices) == 1:
                first_iid = str(devices[0]['id'])
                tree.selection_set(first_iid)
                tree.focus(first_iid)
                search_entry.select_range(0, tk.END)

        def reset_all_filters():
            search_entry.delete(0, tk.END)
            search_type_cb.current(0)
            active_filters.update({
                'search_query': '', 'search_by': 'SERIAL',
                'category': 'الكل', 'condition': 'الكل',
                'has_box': 'الكل', 'supplier_id': 'ALL',
                'date_from': '', 'date_to': ''
            })
            load_tree()
            search_entry.focus()

        def open_inventory_filter_modal():
            """شاشة منبثقة متكاملة لفلترة المخزون (جديد/مستعمل، بعلبة/بدون، النوع، المورد، التاريخ، السيريال)."""
            fwin = tk.Toplevel(self)
            fwin.title("🎛️ شاشة فلترة وبحث المخزون المتقدم")
            fwin.geometry("540x520")
            fwin.configure(bg=self.COLOR_CARD)
            fwin.grab_set()

            tk.Label(fwin, text="🎛️ خيارات الفلترة والبحث المتقدم في المخزون", font=("Segoe UI", 13, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_BLUE).pack(pady=12)

            form = tk.Frame(fwin, bg=self.COLOR_CARD, padx=20, pady=5)
            form.pack(fill="both", expand=True)
            form.grid_columnconfigure(0, weight=1)
            form.grid_columnconfigure(1, weight=0)

            tk.Label(form, text="📷 السيريال / الكلمة البحثية:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky="e", pady=6, padx=5)
            e_f_query = tk.Entry(form, font=("Segoe UI", 10, "bold"), justify="right", bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT)
            e_f_query.insert(0, search_entry.get().strip())
            e_f_query.grid(row=0, column=0, sticky="ew", pady=6, padx=5)
            e_f_query.focus()

            tk.Label(form, text="📱 حالة الجهاز (جديد / مستعمل):", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=1, column=1, sticky="e", pady=6, padx=5)
            cond_var = tk.StringVar(value=active_filters['condition'])
            cond_box = tk.Frame(form, bg=self.COLOR_CARD)
            cond_box.grid(row=1, column=0, sticky="e", pady=6, padx=5)
            for c_opt in ["الكل", "جديد", "مستعمل"]:
                tk.Radiobutton(cond_box, text=c_opt, variable=cond_var, value=c_opt, bg=self.COLOR_CARD, fg=self.COLOR_TEXT, selectcolor=self.COLOR_ENTRY_BG, font=("Segoe UI", 10, "bold")).pack(side="right", padx=8)

            tk.Label(form, text="📦 حالة العلبة (بعلبة / بدون):", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=2, column=1, sticky="e", pady=6, padx=5)
            box_var = tk.StringVar(value=active_filters['has_box'])
            box_frame = tk.Frame(form, bg=self.COLOR_CARD)
            box_frame.grid(row=2, column=0, sticky="e", pady=6, padx=5)
            for b_opt in ["الكل", "بعلبة", "بدون علبة"]:
                tk.Radiobutton(box_frame, text=b_opt, variable=box_var, value=b_opt, bg=self.COLOR_CARD, fg=self.COLOR_TEXT, selectcolor=self.COLOR_ENTRY_BG, font=("Segoe UI", 10, "bold")).pack(side="right", padx=8)

            tk.Label(form, text="🏷️ الماركة / النوع:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=3, column=1, sticky="e", pady=6, padx=5)
            cb_f_cat = ttk.Combobox(form, values=["الكل"] + BRAND_LIST, state="readonly", font=("Segoe UI", 10))
            cb_f_cat.set(active_filters['category'] if active_filters['category'] in (["الكل"] + BRAND_LIST) else "الكل")
            cb_f_cat.grid(row=3, column=0, sticky="ew", pady=6, padx=5)

            tk.Label(form, text="🏭 المورد:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=4, column=1, sticky="e", pady=6, padx=5)
            supps = self.db.get_all_suppliers()
            supp_opts = ["الكل"] + [f"{s['id']} - {s['name']} ({s.get('supplier_type', 'تاجر')})" for s in supps]
            cb_f_supp = ttk.Combobox(form, values=supp_opts, state="readonly", font=("Segoe UI", 10))
            cb_f_supp.current(0)
            if active_filters['supplier_id'] != 'ALL':
                for idx_s, s_obj in enumerate(supps, start=1):
                    if str(s_obj['id']) == str(active_filters['supplier_id']):
                        cb_f_supp.current(idx_s)
                        break
            cb_f_supp.grid(row=4, column=0, sticky="ew", pady=6, padx=5)

            tk.Label(form, text="📅 من تاريخ شراء:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=5, column=1, sticky="e", pady=6, padx=5)
            df_frame = tk.Frame(form, bg=self.COLOR_CARD)
            df_frame.grid(row=5, column=0, sticky="ew", pady=6, padx=5)
            e_df = tk.Entry(df_frame, font=("Segoe UI", 10), justify="center", bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, width=16)
            e_df.insert(0, active_filters['date_from'])
            e_df.pack(side="right", padx=3)
            tk.Button(df_frame, text="📅 اختر التاريخ", command=lambda: self.open_date_picker(e_df), bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2").pack(side="right", padx=3)

            tk.Label(form, text="📅 إلى تاريخ شراء:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=6, column=1, sticky="e", pady=6, padx=5)
            dt_frame = tk.Frame(form, bg=self.COLOR_CARD)
            dt_frame.grid(row=6, column=0, sticky="ew", pady=6, padx=5)
            e_dt = tk.Entry(dt_frame, font=("Segoe UI", 10), justify="center", bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, width=16)
            e_dt.insert(0, active_filters['date_to'])
            e_dt.pack(side="right", padx=3)
            tk.Button(dt_frame, text="📅 اختر التاريخ", command=lambda: self.open_date_picker(e_dt), bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2").pack(side="right", padx=3)

            def apply_modal_filters(event=None):
                search_entry.delete(0, tk.END)
                search_entry.insert(0, e_f_query.get().strip())
                active_filters['condition'] = cond_var.get()
                active_filters['has_box'] = box_var.get()
                active_filters['category'] = cb_f_cat.get()
                sel_supp_idx = cb_f_supp.current()
                if sel_supp_idx > 0 and (sel_supp_idx - 1) < len(supps):
                    active_filters['supplier_id'] = supps[sel_supp_idx - 1]['id']
                else:
                    active_filters['supplier_id'] = 'ALL'
                active_filters['date_from'] = e_df.get().strip()
                active_filters['date_to'] = e_dt.get().strip()
                fwin.destroy()
                load_tree()

            e_f_query.bind("<Return>", apply_modal_filters)

            btn_f_bar = tk.Frame(fwin, bg=self.COLOR_CARD, pady=12)
            btn_f_bar.pack(fill="x", padx=20)
            tk.Button(btn_f_bar, text="✅ تطبيق الفلترة والبحث (Enter)", command=apply_modal_filters, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 11, "bold"), padx=18, pady=6, cursor="hand2").pack(side="right", padx=5)
            tk.Button(btn_f_bar, text="🔄 إعادة ضبط الفلاتر", command=lambda: (fwin.destroy(), reset_all_filters()), bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 10, "bold"), padx=12, pady=6, cursor="hand2").pack(side="left", padx=5)

        search_entry.bind("<Return>", lambda e: load_tree())
        search_type_cb.bind("<<ComboboxSelected>>", lambda e: load_tree())
        tk.Button(search_card, text="🔍 بحث فوري", command=load_tree, bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 9, "bold"), cursor="hand2", padx=10).pack(side="right", padx=3)
        tk.Button(search_card, text="🎛️ شاشة الفلترة المتقدمة", command=open_inventory_filter_modal, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 9, "bold"), cursor="hand2", padx=12).pack(side="right", padx=4)
        tk.Button(search_card, text="🔄 عرض الكل", command=reset_all_filters, bg=self.COLOR_TOPBAR, fg=self.COLOR_TEXT, font=("Segoe UI", 9, "bold"), cursor="hand2", padx=8).pack(side="right", padx=3)

        load_tree()

        if self.has_permission('can_manage_inventory'):
            act_bar = tk.Frame(self.content_frame, bg=self.COLOR_BG)
            act_bar.pack(fill="x", padx=15, pady=6)

            def open_edit_device_modal():
                sel = tree.selection()
                if not sel:
                    messagebox.showwarning("تنبيه", "يرجى تحديد جهاز لتعديل بياناته!")
                    return
                row_id = sel[0]
                item_vals = tree.item(row_id).get('values', [])
                dev_id = clean_id_val(item_vals[-1]) if item_vals else clean_id_val(row_id)
                if dev_id is None:
                    dev_id = clean_id_val(row_id)

                dev_details = self.db.get_device_full_details(dev_id)
                if not dev_details or not dev_details.get('device'):
                    messagebox.showerror("خطأ", f"تعذر جلب بيانات الجهاز #{dev_id}!")
                    return
                dev = dev_details['device']

                ewin = tk.Toplevel(self)
                ewin.title(f"تعديل بيانات الجهاز #{dev['id']}")
                ewin.geometry("480x630")
                ewin.configure(bg=self.COLOR_CARD)
                ewin.grab_set()

                tk.Label(ewin, text=f"✏️ تعديل بيانات الجهاز #{dev['id']}", font=("Segoe UI", 13, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_BLUE).pack(pady=10)

                f = tk.Frame(ewin, bg=self.COLOR_CARD, padx=20)
                f.pack(fill="both", expand=True)
                f.grid_columnconfigure(0, weight=1)

                fields = [
                    ("الماركة (النوع):", dev.get('category') or ""),
                    ("الموديل:", dev.get('model') or ""),
                    ("المساحة:", dev.get('storage') or ""),
                    ("الرامات:", dev.get('ram') or ""),
                    ("نسبة البطارية (%):", str(dev.get('battery_health') or 0)),
                    ("السيريال / IMEI:", dev.get('imei_serial') or ""),
                    ("سعر الشراء (ج.م):", str(dev.get('buy_price') or 0)),
                    ("ملاحظات الشراء:", dev.get('notes') or "")
                ]

                entries = {}
                for idx, (lbl, val) in enumerate(fields):
                    tk.Label(f, text=lbl, bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=idx, column=1, sticky="e", pady=4)
                    e = tk.Entry(f, font=("Segoe UI", 10), justify="right", bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT)
                    e.insert(0, str(val))
                    e.grid(row=idx, column=0, sticky="ew", pady=4, padx=5)
                    entries[lbl] = e

                cond_edit_var = tk.StringVar(value=dev.get('device_condition') or "مستعمل")
                tk.Label(f, text="حالة الجهاز:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=8, column=1, sticky="e", pady=5)
                cond_f = tk.Frame(f, bg=self.COLOR_CARD)
                cond_f.grid(row=8, column=0, sticky="e", pady=5, padx=5)
                tk.Radiobutton(cond_f, text="جديد", variable=cond_edit_var, value="جديد", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, selectcolor=self.COLOR_ENTRY_BG, font=("Segoe UI", 10, "bold")).pack(side="right", padx=8)
                tk.Radiobutton(cond_f, text="مستعمل", variable=cond_edit_var, value="مستعمل", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, selectcolor=self.COLOR_ENTRY_BG, font=("Segoe UI", 10, "bold")).pack(side="right", padx=8)

                box_edit_var = tk.BooleanVar(value=bool(dev.get('has_box', False)))
                tk.Label(f, text="العلبة:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=9, column=1, sticky="e", pady=5)
                tk.Checkbutton(f, text="📦 الجهاز بعلبة (معه الكرتونة)", variable=box_edit_var, bg=self.COLOR_CARD, fg=self.COLOR_TEXT, selectcolor=self.COLOR_ENTRY_BG, font=("Segoe UI", 10, "bold")).grid(row=9, column=0, sticky="e", pady=5, padx=5)

                # ربط الإكمال التلقائي للنوع والموديل في شاشة التعديل أيضاً
                e_cat_edit = entries["الماركة (النوع):"]
                e_mod_edit = entries["الموديل:"]
                self.attach_autocomplete(e_cat_edit, lambda: BRAND_LIST, next_focus_widget=e_mod_edit)
                self.attach_autocomplete(
                    e_mod_edit,
                    lambda: self.get_suggested_models_for_brand(e_cat_edit.get()),
                    next_focus_widget=entries["المساحة:"]
                )

                def save_dev_changes():
                    try:
                        cat = entries["الماركة (النوع):"].get().strip()
                        mod = entries["الموديل:"].get().strip()
                        stg = entries["المساحة:"].get().strip()
                        ram = entries["الرامات:"].get().strip()
                        bat = entries["نسبة البطارية (%):"].get().strip()
                        imei = entries["السيريال / IMEI:"].get().strip()
                        price = entries["سعر الشراء (ج.م):"].get().strip()
                        notes_val = entries["ملاحظات الشراء:"].get().strip()

                        if not cat or not mod or not imei or not price:
                            messagebox.showwarning("تنبيه", "برجاء إدخال البيانات الأساسية للجهاز!", parent=ewin)
                            return

                        self.db.update_device(
                            dev['id'], cat, mod, stg, ram,
                            int(float(bat)) if bat.replace('.', '', 1).isdigit() else 0,
                            imei, float(price),
                            device_condition=cond_edit_var.get(),
                            has_box=box_edit_var.get(),
                            notes=notes_val
                        )
                        messagebox.showinfo("تم", "تم تحديث بيانات الجهاز وإعادة حساب المديونية بنجاح!", parent=ewin)
                        ewin.destroy()
                        load_tree()
                    except Exception as ex:
                        messagebox.showerror("خطأ", str(ex), parent=ewin)

                tk.Button(ewin, text="💾 حفظ التغييرات", command=save_dev_changes, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 11, "bold"), pady=6, padx=18, cursor="hand2").pack(pady=12)

            def soft_delete_dev():
                sel = tree.selection()
                if not sel:
                    messagebox.showwarning("تنبيه", "يرجى تحديد جهاز لحذفه!")
                    return
                row_id = sel[0]
                item_vals = tree.item(row_id).get('values', [])
                dev_id = clean_id_val(item_vals[-1]) if item_vals else clean_id_val(row_id)
                if messagebox.askyesno("تأكيد الحذف الذكي", "هل أنت متأكد من تحويل حالة الجهاز إلى (محذوف)؟\nسيتم خصم قيمته من إجمالي فاتورة المورد ومن المدفوع ومن الخرج والتقرير المالي تلقائياً."):
                    try:
                        self.db.soft_delete_device(dev_id, self.current_user['id'])
                        messagebox.showinfo("تم", "تم تحويل حالة الجهاز إلى محذوف وتحديث الفاتورة والمديونية والتقرير المالي بنجاح!")
                        load_tree()
                    except Exception as ex:
                        messagebox.showerror("خطأ", str(ex))

            tk.Button(act_bar, text="✏️ تعديل بيانات الجهاز", command=open_edit_device_modal, bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold"), padx=12, pady=4, cursor="hand2").pack(side="right", padx=5)
            tk.Button(act_bar, text="🗑️ حذف الجهاز (محذوف)", command=soft_delete_dev, bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 10, "bold"), padx=12, pady=4, cursor="hand2").pack(side="right", padx=5)

    def get_suggested_models_for_brand(self, brand_text):
        """إرجاع قائمة الموديلات المقترحة بناءً على النوع المكتوب + الموديلات المسجلة سابقاً بالداتا بيز."""
        b_clean = (brand_text or "").strip().lower()
        models = []
        for brand_key, m_list in BRAND_MODELS_SUGGESTIONS.items():
            if not b_clean or brand_key.lower() == b_clean or b_clean in brand_key.lower():
                for m in m_list:
                    if m not in models:
                        models.append(m)
        db_models = self.db.get_distinct_models_by_category(brand_text)
        for dm in db_models:
            if dm and dm not in models:
                models.insert(0, dm)
        return models

    def view_search_sale(self):
        """شاشة البيع السريع مع دعم البحث المخصص ومسح الباركود الفوري لكود IMEI وعرض الحالة والعلبة وملاحظات الشراء والبيع."""
        self.current_view_func = self.view_search_sale
        self.clear_content()

        tk.Label(self.content_frame, text="🛒 شاشة البيع السريع (دعم قارئ باركود السيريال IMEI الفوري)", font=("Segoe UI", 15, "bold"), bg=self.COLOR_BG, fg=self.COLOR_BLUE).pack(pady=10)

        search_bar = tk.Frame(self.content_frame, bg=self.COLOR_CARD, padx=15, pady=10, highlightthickness=1, highlightbackground=self.COLOR_TOPBAR)
        search_bar.pack(pady=5, padx=30, fill="x")

        tk.Label(search_bar, text="البحث بحسب:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right", padx=5)
        search_type_cb = ttk.Combobox(search_bar, values=["السيريال / IMEI", "ID الجهاز", "الاسم / الموديل", "الكل"], state="readonly", width=15, font=("Segoe UI", 10))
        search_type_cb.current(0)
        search_type_cb.pack(side="right", padx=5)

        tk.Label(search_bar, text="الكود / البحث:", bg=self.COLOR_CARD, fg=self.COLOR_MUTED, font=("Segoe UI", 10, "bold")).pack(side="right", padx=5)
        search_entry = tk.Entry(search_bar, font=("Segoe UI", 12, "bold"), width=30, justify="center", bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT)
        search_entry.pack(side="right", padx=5)
        search_entry.focus()

        card = tk.Frame(self.content_frame, bg=self.COLOR_CARD, padx=20, pady=18, highlightthickness=1, highlightbackground=self.COLOR_TOPBAR)
        card.pack(pady=10, fill="both", expand=True, padx=30)

        tk.Label(card, text="📷 قم بمسح باركود السيريال (IMEI) من علبة الجهاز مباشرة أو اكتب الكود واضغط Enter", bg=self.COLOR_CARD, fg=self.COLOR_MUTED, font=("Segoe UI", 12, "bold")).pack(pady=40)

        def clear_and_refocus():
            search_entry.delete(0, tk.END)
            search_entry.focus()

        def perform_search(event=None):
            for widget in card.winfo_children():
                widget.destroy()
            q = search_entry.get().strip()
            if not q:
                tk.Label(card, text="⚠️ برجاء مسح السيريال بالباركود أو إدخال قيمة البحث أولاً!", bg=self.COLOR_CARD, fg=self.COLOR_MUTED, font=("Segoe UI", 12, "bold")).pack(pady=30)
                search_entry.focus()
                return

            st_map = {"السيريال / IMEI": "SERIAL", "ID الجهاز": "ID", "الاسم / الموديل": "NAME", "الكل": "ALL"}
            dev = self.db.search_device_by_criteria(q, st_map.get(search_type_cb.get(), "SERIAL"))

            if not dev:
                tk.Label(card, text="❌ لم يتم العثور على أي جهاز بهذه البيانات!", bg=self.COLOR_CARD, fg=self.COLOR_DANGER, font=("Segoe UI", 13, "bold")).pack(pady=20)
                search_entry.select_range(0, tk.END)
                search_entry.focus()
                return

            buy_p_str = fmt_curr(dev['buy_price']) if self.has_permission('can_view_buy_price') else "***"
            bat_str = f"{dev['battery_health']}%" if dev.get('battery_health') else "لا يوجد"
            ram_str = dev.get('ram') or "لا يوجد"
            cond_str = dev.get('device_condition') or "مستعمل"
            box_str = "بعلبة 📦" if dev.get('has_box') else "بدون علبة"
            buy_notes_str = dev.get('notes') or "لا يوجد"

            info_header = tk.Frame(card, bg=self.COLOR_TOPBAR, padx=15, pady=10)
            info_header.pack(fill="x", pady=(0, 10))

            dev_title = fix_bidi(f"📱 {dev['category']} {dev['model']} (ID: #{dev['id']}) — [{cond_str} | {box_str}]")
            tk.Label(info_header, text=dev_title, font=("Segoe UI", 14, "bold"), bg=self.COLOR_TOPBAR, fg=self.COLOR_BLUE).pack(side="right")

            st_badge = "🔴 مباع" if dev['is_sold'] else "🟢 متاح بالمخزن"
            st_color = self.COLOR_DANGER if dev['is_sold'] else self.COLOR_ACCENT
            tk.Label(info_header, text=st_badge, font=("Segoe UI", 11, "bold"), bg=self.COLOR_CARD, fg=st_color, padx=10, pady=3).pack(side="left")

            specs_box = tk.Frame(card, bg=self.COLOR_CARD)
            specs_box.pack(fill="x", pady=5)

            specs = [
                ("الماركة / الفئة", dev['category']),
                ("الموديل", dev['model']),
                ("حالة الجهاز / العلبة", f"{cond_str} — {box_str}"),
                ("المساحة / الرام", f"{dev.get('storage') or '-'} / {ram_str}"),
                ("نسبة البطارية", bat_str),
                ("السيريال IMEI", dev['imei_serial']),
                ("سعر الشراء والتكلفة", buy_p_str),
                ("المورد", dev.get('supplier_name') or '-'),
                ("ملاحظات الشراء", buy_notes_str),
                ("تاريخ الشراء", dev.get('buy_date_formatted', '-'))
            ]

            for idx, (lbl, val) in enumerate(specs):
                r, c = divmod(idx, 2)
                f_item = tk.Frame(specs_box, bg=self.COLOR_ENTRY_BG, padx=10, pady=5)
                f_item.grid(row=r, column=1-c, sticky="ew", padx=5, pady=3)
                tk.Label(f_item, text=fix_bidi(f"{lbl}:"), font=("Segoe UI", 10), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_MUTED).pack(side="right", padx=2)
                tk.Label(f_item, text=fix_bidi(val), font=("Segoe UI", 10, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT).pack(side="right", padx=5)
                specs_box.grid_columnconfigure(0, weight=1)
                specs_box.grid_columnconfigure(1, weight=1)

            if not dev['is_sold']:
                sale_box = tk.LabelFrame(card, text="💳 تفاصيل البيع والعميل", bg=self.COLOR_CARD, fg=self.COLOR_ACCENT, font=("Segoe UI", 11, "bold"), padx=15, pady=10)
                sale_box.pack(fill="x", pady=12)

                for col_i in range(4):
                    sale_box.grid_columnconfigure(col_i, weight=1)

                tk.Label(sale_box, text="سعر البيع الاتفاقي:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=0, column=3, sticky="e", padx=5, pady=5)
                e_price = tk.Entry(sale_box, justify="right", font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, validate="key", validatecommand=self.vcmd_num)
                e_price.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
                e_price.focus()

                tk.Label(sale_box, text="المدفوع نقداً (كاش):", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky="e", padx=5, pady=5)
                e_paid = tk.Entry(sale_box, justify="right", font=("Segoe UI", 11, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, validate="key", validatecommand=self.vcmd_num)
                e_paid.insert(0, "0")
                e_paid.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

                tk.Label(sale_box, text="اسم العميل:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=1, column=3, sticky="e", padx=5, pady=5)
                e_cname = tk.Entry(sale_box, justify="right", font=("Segoe UI", 11), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT)
                e_cname.grid(row=1, column=2, padx=5, pady=5, sticky="ew")

                tk.Label(sale_box, text="رقم الهاتف:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=1, column=1, sticky="e", padx=5, pady=5)
                e_cphone = tk.Entry(sale_box, justify="right", font=("Segoe UI", 11), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, validate="key", validatecommand=self.vcmd_num)
                e_cphone.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

                tk.Label(sale_box, text="ملاحظات البيع:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=2, column=3, sticky="e", padx=5, pady=5)
                e_notes = tk.Entry(sale_box, justify="right", font=("Segoe UI", 10), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT)
                e_notes.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky="ew")

                lbl_rem = tk.Label(sale_box, text="المتبقي (الآجل): 0.00 ج.م", font=("Segoe UI", 12, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_DANGER)
                lbl_rem.grid(row=3, column=0, columnspan=4, pady=8)

                e_price.bind("<Return>", lambda e: e_paid.focus())
                e_paid.bind("<Return>", lambda e: e_cname.focus())
                e_cname.bind("<Return>", lambda e: e_cphone.focus())
                e_cphone.bind("<Return>", lambda e: e_notes.focus())
                e_notes.bind("<Return>", lambda e: do_confirm_sale())

                def update_calc(e=None):
                    try:
                        price = float(e_price.get().strip() or 0)
                        paid = float(e_paid.get().strip() or 0)
                        rem = max(0.0, price - paid)
                        if price < float(dev['buy_price']):
                            lbl_rem.config(text=fix_bidi(f"⚠️ تحذير: سعر البيع أقل من سعر الشراء ({fmt_curr(dev['buy_price'])})!"), fg=self.COLOR_DANGER)
                        elif rem > 0:
                            lbl_rem.config(text=fix_bidi(f"⚠️ لم يتم السداد بالكامل! المتبقي (آجل): {fmt_curr(rem)}"), fg=self.COLOR_DANGER)
                        else:
                            lbl_rem.config(text="✅ تم السداد بالكامل نقداً", fg=self.COLOR_ACCENT)
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
                            messagebox.showerror("خطأ في البيع", fix_bidi(f"مينفعش يبقى سعر البيع أقل من سعر الشراء ({fmt_curr(buy_p)})!"))
                            return

                        paid = float(e_paid.get().strip() or 0)
                        cname = e_cname.get().strip()
                        cphone = e_cphone.get().strip()
                        notes = e_notes.get().strip()
                        
                        if not cname:
                            messagebox.showwarning("تنبيه", "برجاء إدخال اسم العميل!")
                            e_cname.focus()
                            return

                        remaining = max(0.0, price - paid)

                        sale_id = self.db.process_sale(dev['id'], price, cname, cphone, paid, notes, self.current_user['id'])
                        
                        inv_data = {
                            'sale_id': sale_id,
                            'customer_name': cname,
                            'customer_phone': cphone,
                            'device': dev,
                            'original_price': price,
                            'discount': 0.0,
                            'sell_price': price,
                            'cash_received': paid,
                            'remaining_balance': remaining,
                            'date_str': datetime.now().strftime("%Y-%m-%d %H:%M")
                        }
                        if notes:
                            inv_data['custom_terms'] = f"ملاحظات البيع: {notes}\n1. البضاعة المباعة تخضع للمراجعة والضمان المعين.\n2. يحتفظ المحل بحقه في المتابعة المالية للآجل."
                        
                        try:
                            img_path = generate_invoice_image(inv_data)
                            if hasattr(os, "startfile"):
                                os.startfile(img_path)
                        except Exception as img_err:
                            print(f"Invoice open notice: {img_err}")

                        messagebox.showinfo("تم", "تم تسجيل البيع بنجاح وتوليد الفاتورة عالية الدقة!")
                        self.view_search_sale()
                    except Exception as ex:
                        messagebox.showerror("خطأ", str(ex))

                tk.Button(card, text="💾 تأكيد البيع وطباعة الفاتورة (Enter)", command=do_confirm_sale, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 11, "bold"), pady=6, padx=20, cursor="hand2").pack(pady=8)
            else:
                sold_box = tk.Frame(card, bg=self.COLOR_CARD, pady=10)
                sold_box.pack(fill="x")
                tk.Label(sold_box, text=fix_bidi(f"الحالة: مباع للعميل ({dev.get('customer_name') or '-'})  |  سعر البيع: {fmt_curr(dev.get('sell_price', 0))}"), bg=self.COLOR_CARD, fg=self.COLOR_DANGER, font=("Segoe UI", 12, "bold")).pack(pady=5)
                if dev.get('sale_notes'):
                    tk.Label(sold_box, text=fix_bidi(f"📝 ملاحظات البيع: {dev['sale_notes']}"), bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10)).pack(pady=3)

                if self.has_permission('can_process_returns'):
                    def do_return():
                        if messagebox.askyesno("تأكيد", "إجراء مرتجع للجهاز وإرجاعه للمخزون؟"):
                            self.db.process_return(dev['id'], self.current_user['id'])
                            messagebox.showinfo("تم", "تم المرتجع بنجاح!")
                            self.view_search_sale()
                    tk.Button(card, text="🔄 إجراء مرتجع", command=do_return, bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 10, "bold"), padx=15, pady=5, cursor="hand2").pack(pady=5)
                search_entry.select_range(0, tk.END)
                search_entry.focus()

        search_entry.bind("<Return>", perform_search)
        tk.Button(search_bar, text="🔍 بحث فوري (Enter)", command=perform_search, bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold"), padx=12, cursor="hand2").pack(side="right", padx=5)
        tk.Button(search_bar, text="🧹 مسح وجاهز للإسكان", command=clear_and_refocus, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 9, "bold"), padx=10, cursor="hand2").pack(side="left", padx=5)

    def view_buy(self):
        """
        شاشة إدخال الشراء مع:
        - قائمة مساعدة ذكية للنوع (Oppo, iPhone, Samsung, Honor, Realme, Infinix, Huawei, Xiaomi) والموديل
        - اختيار جديد أو مستعمل
        - اختيار بعلبة أو لا (Checkbutton)
        - خانة ملاحظات الشراء
        - إلغاء اختيار الشراء المباشر وإلزام اختيار مورد (تاجر / زبون)
        """
        self.current_view_func = self.view_buy
        self.clear_content()

        tk.Label(self.content_frame, text="🛒 تسجيل جهاز جديد في المخزون (إدخال شراء)", font=("Segoe UI", 15, "bold"), bg=self.COLOR_BG, fg=self.COLOR_BLUE).pack(pady=10)

        main_box = tk.Frame(self.content_frame, bg=self.COLOR_BG)
        main_box.pack(pady=5, padx=30, fill="x")

        sec1 = tk.LabelFrame(main_box, text="📱 مواصفات وتفاصيل الجهاز (اكتب في النوع أو الموديل لظهور الاقتراحات الذكية)", bg=self.COLOR_CARD, fg=self.COLOR_BLUE, font=("Segoe UI", 11, "bold"), padx=20, pady=15)
        sec1.pack(fill="x", pady=5)

        sec2 = tk.LabelFrame(main_box, text="💰 بيانات الشراء والمورد والملاحظات", bg=self.COLOR_CARD, fg=self.COLOR_BLUE, font=("Segoe UI", 11, "bold"), padx=20, pady=15)
        sec2.pack(fill="x", pady=10)

        for col_i in range(4):
            sec1.grid_columnconfigure(col_i, weight=1)
            sec2.grid_columnconfigure(col_i, weight=1)

        suppliers = self.db.get_all_suppliers()

        tk.Label(sec1, text="الماركة (النوع):", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=0, column=3, sticky="e", padx=8, pady=6)
        e_cat = tk.Entry(sec1, font=("Segoe UI", 11, "bold"), justify="right", bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, width=24)
        e_cat.grid(row=0, column=2, padx=8, pady=6, sticky="ew")
        e_cat.focus()

        tk.Label(sec1, text="الموديل:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky="e", padx=8, pady=6)
        e_model = tk.Entry(sec1, font=("Segoe UI", 11, "bold"), justify="right", bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, width=24)
        e_model.grid(row=0, column=0, padx=8, pady=6, sticky="ew")

        tk.Label(sec1, text="المساحة:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=1, column=3, sticky="e", padx=8, pady=6)
        e_storage = tk.Entry(sec1, font=("Segoe UI", 10), justify="right", bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, width=24)
        e_storage.grid(row=1, column=2, padx=8, pady=6, sticky="ew")

        tk.Label(sec1, text="الرامات:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=1, column=1, sticky="e", padx=8, pady=6)
        e_ram = tk.Entry(sec1, font=("Segoe UI", 10), justify="right", bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, width=24)
        e_ram.grid(row=1, column=0, padx=8, pady=6, sticky="ew")

        tk.Label(sec1, text="نسبة البطارية (%):", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=2, column=3, sticky="e", padx=8, pady=6)
        e_bat = tk.Entry(sec1, font=("Segoe UI", 10), justify="right", bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, validate="key", validatecommand=self.vcmd_num, width=24)
        e_bat.grid(row=2, column=2, padx=8, pady=6, sticky="ew")

        tk.Label(sec1, text="السيريال / IMEI:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=2, column=1, sticky="e", padx=8, pady=6)
        e_imei = tk.Entry(sec1, font=("Segoe UI", 10, "bold"), justify="center", bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, width=24)
        e_imei.grid(row=2, column=0, padx=8, pady=6, sticky="ew")

        # الصف الثالث: حالة الجهاز (جديد / مستعمل) + اختيار بعلبة أو لا (Checkbox)
        tk.Label(sec1, text="حالة الجهاز:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=3, column=3, sticky="e", padx=8, pady=8)
        cond_var = tk.StringVar(value="مستعمل")
        cond_frame = tk.Frame(sec1, bg=self.COLOR_CARD)
        cond_frame.grid(row=3, column=2, sticky="e", padx=8, pady=8)
        tk.Radiobutton(cond_frame, text="🆕 جديد", variable=cond_var, value="جديد", bg=self.COLOR_CARD, fg=self.COLOR_ACCENT, selectcolor=self.COLOR_ENTRY_BG, font=("Segoe UI", 10, "bold")).pack(side="right", padx=10)
        tk.Radiobutton(cond_frame, text="📱 مستعمل", variable=cond_var, value="مستعمل", bg=self.COLOR_CARD, fg=self.COLOR_BLUE, selectcolor=self.COLOR_ENTRY_BG, font=("Segoe UI", 10, "bold")).pack(side="right", padx=10)

        tk.Label(sec1, text="العلبة / الكرتونة:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=3, column=1, sticky="e", padx=8, pady=8)
        has_box_var = tk.BooleanVar(value=True)
        cb_has_box = tk.Checkbutton(
            sec1, text="📦 الجهاز بعلبة (معه الكرتونة)", variable=has_box_var,
            bg=self.COLOR_CARD, fg=self.COLOR_TEXT, selectcolor=self.COLOR_ENTRY_BG,
            activebackground=self.COLOR_CARD, activeforeground=self.COLOR_ACCENT,
            font=("Segoe UI", 10, "bold"), cursor="hand2"
        )
        cb_has_box.grid(row=3, column=0, sticky="e", padx=8, pady=8)

        # ربط القائمة المساعدة الذكية للنوع والموديل (يدعم الماوس والأسهم و Tab و Enter)
        self.attach_autocomplete(e_cat, lambda: BRAND_LIST, next_focus_widget=e_model)
        self.attach_autocomplete(
            e_model,
            lambda: self.get_suggested_models_for_brand(e_cat.get()),
            next_focus_widget=e_storage
        )

        # قسم بيانات الشراء والمورد (بدون شراء مباشر)
        tk.Label(sec2, text="سعر الشراء (ج.م):", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=0, column=3, sticky="e", padx=8, pady=6)
        e_price = tk.Entry(sec2, font=("Segoe UI", 11, "bold"), justify="right", bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, validate="key", validatecommand=self.vcmd_num, width=24)
        e_price.grid(row=0, column=2, padx=8, pady=6, sticky="ew")

        tk.Label(sec2, text="اختيار المورد (تاجر/زبون):", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky="e", padx=8, pady=6)
        
        supp_frame = tk.Frame(sec2, bg=self.COLOR_CARD)
        supp_display_names = [f"{s['name']} ({s.get('supplier_type', 'تاجر')})" for s in suppliers]
        cb_supp = ttk.Combobox(supp_frame, values=supp_display_names, state="readonly", font=("Segoe UI", 10, "bold"), width=24)
        if supp_display_names:
            cb_supp.current(0)
        cb_supp.pack(side="right", padx=2)

        tk.Label(sec2, text="ملاحظات الشراء:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=1, column=3, sticky="e", padx=8, pady=8)
        e_buy_notes = tk.Entry(sec2, font=("Segoe UI", 10), justify="right", bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT)
        e_buy_notes.grid(row=1, column=0, columnspan=3, padx=8, pady=8, sticky="ew")

        def add_new_supplier_popup():
            ns_win = tk.Toplevel(self)
            ns_win.title("إضافة مورد جديد")
            ns_win.geometry("370x290")
            ns_win.configure(bg=self.COLOR_CARD)
            ns_win.grab_set()

            tk.Label(ns_win, text="➕ إضافة مورد جديد (تاجر / زبون)", bg=self.COLOR_CARD, fg=self.COLOR_BLUE, font=("Segoe UI", 12, "bold")).pack(pady=8)

            tk.Label(ns_win, text="اسم المورد:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(pady=3)
            n_entry = tk.Entry(ns_win, bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="right", font=("Segoe UI", 10), width=26)
            n_entry.pack(pady=3)
            n_entry.focus()
            
            tk.Label(ns_win, text="رقم الهاتف:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(pady=3)
            p_entry = tk.Entry(ns_win, bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="right", font=("Segoe UI", 10), width=26, validate="key", validatecommand=self.vcmd_num)
            p_entry.pack(pady=3)

            tk.Label(ns_win, text="نوع المورد (تاجر أم زبون عادي):", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(pady=3)
            type_cb = ttk.Combobox(ns_win, values=["تاجر", "زبون / بيع عادي"], state="readonly", font=("Segoe UI", 10), width=24)
            type_cb.current(0)
            type_cb.pack(pady=3)

            def save_supp():
                name = n_entry.get().strip()
                phone = p_entry.get().strip()
                stype = "تاجر" if "تاجر" in type_cb.get() else "زبون"
                if not name:
                    messagebox.showwarning("تنبيه", "برجاء إدخال اسم المورد!", parent=ns_win)
                    return
                new_id = self.db.add_supplier(name, phone, stype)
                nonlocal suppliers
                suppliers = self.db.get_all_suppliers()
                updated_display = [f"{s['name']} ({s.get('supplier_type', 'تاجر')})" for s in suppliers]
                cb_supp['values'] = updated_display
                for idx, s in enumerate(suppliers):
                    if s['id'] == new_id:
                        cb_supp.current(idx)
                        break
                ns_win.destroy()
            
            n_entry.bind("<Return>", lambda e: p_entry.focus())
            p_entry.bind("<Return>", lambda e: save_supp())
            tk.Button(ns_win, text="💾 حفظ المورد", command=save_supp, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"), padx=15, cursor="hand2").pack(pady=15)

        tk.Button(supp_frame, text="➕ إضافة مورد", command=add_new_supplier_popup, bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="right", padx=2)
        supp_frame.grid(row=0, column=0, padx=8, pady=6, sticky="e")

        e_storage.bind("<Return>", lambda e: e_ram.focus())
        e_ram.bind("<Return>", lambda e: e_bat.focus())
        e_bat.bind("<Return>", lambda e: e_imei.focus())
        e_imei.bind("<Return>", lambda e: e_price.focus())
        e_price.bind("<Return>", lambda e: e_buy_notes.focus())
        e_buy_notes.bind("<Return>", lambda e: save_device())

        def save_device():
            try:
                cat = e_cat.get().strip()
                model = e_model.get().strip()
                storage = e_storage.get().strip()
                ram = e_ram.get().strip() or "لا يوجد"
                bat_str = e_bat.get().strip()
                bat = int(float(bat_str)) if bat_str.replace('.', '', 1).isdigit() else 0
                imei = e_imei.get().strip()
                price_str = e_price.get().strip()
                notes_val = e_buy_notes.get().strip()
                cond_val = cond_var.get()
                has_box_val = has_box_var.get()

                if not cat or not model or not imei or not price_str:
                    messagebox.showwarning("تنبيه", "برجاء إدخال الماركة والموديل والسيريال وسعر الشراء!")
                    return

                curr_idx = cb_supp.current()
                if curr_idx < 0 or curr_idx >= len(suppliers):
                    messagebox.showwarning("تنبيه", "برجاء اختيار المورد (تاجر أو زبون) أو إضافة مورد جديد من زر (➕ إضافة مورد)!")
                    return

                supp_id = suppliers[curr_idx]['id']
                price = float(price_str)

                dev_id = self.db.add_device(
                    cat, model, storage, ram, bat, "", imei, price, supp_id,
                    notes_val, self.current_user['id'],
                    device_condition=cond_val, has_box=has_box_val
                )
                messagebox.showinfo("نجاح", f"تم إضافة الجهاز للمخزون بنجاح! ID: #{dev_id}")
                self.view_inventory()
            except Exception as e:
                messagebox.showerror("خطأ", str(e))

        tk.Button(self.content_frame, text="💾 حفظ وإدخال للمخزون (Enter)", command=save_device, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 11, "bold"), padx=25, pady=6, relief="flat", cursor="hand2").pack(pady=12)

    def view_customer_debts(self):
        self.current_view_func = self.view_customer_debts
        self.clear_content()

        top_frame = tk.Frame(self.content_frame, bg=self.COLOR_BG)
        top_frame.pack(fill="x", padx=15, pady=10)

        tk.Label(top_frame, text="💳 مستحقات وتأخيرات العملاء (الخرج)", font=("Segoe UI", 15, "bold"), bg=self.COLOR_BG, fg=self.COLOR_BLUE).pack(side="right")

        columns = ("رقم الفاتورة", "ID الجهاز", "الموديل", "اسم العميل", "الهاتف", "تاريخ البيع", "الإجمالي", "المدفوع", "المتبقي")
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
                tree.insert("", "end", values=(d['sale_id'], d['device_id'], d['model'],
                                              d['customer_name'], d['customer_phone'], d['sell_date_formatted'],
                                              fmt_curr(d['sell_price']), fmt_curr(d['cash_received']), 
                                              fmt_curr(d['remaining_balance'])))

        load_debts()

        pay_frame = tk.Frame(self.content_frame, bg=self.COLOR_CARD, pady=10)
        pay_frame.pack(fill="x", padx=15, pady=10)

        tk.Label(pay_frame, text="مبلغ التحصيل:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right", padx=5)
        amount_entry = tk.Entry(pay_frame, font=("Segoe UI", 10), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, validate="key", validatecommand=self.vcmd_num)
        amount_entry.pack(side="right", padx=5)

        def pay_selected():
            selected = tree.selection()
            if not selected: 
                messagebox.showwarning("تنبيه", "يرجى تحديد عميل تحصل منه الدفعة!")
                return
            sale_id = tree.item(selected[0])['values'][0]
            try:
                amt = float(amount_entry.get().strip())
                self.db.pay_customer_debt(sale_id, amt, self.current_user['id'])
                messagebox.showinfo("نجاح", "تم تحصيل الدفعة بنجاح!")
                load_debts()
                amount_entry.delete(0, tk.END)
            except Exception as e:
                messagebox.showerror("خطأ", str(e))

        amount_entry.bind("<Return>", lambda e: pay_selected())
        tk.Button(pay_frame, text="💵 تحصيل الدفعة (Enter)", command=pay_selected, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"), cursor="hand2").pack(side="right", padx=10)

    def view_supplier_debts(self):
        """شاشة الموردين والمديونيات مع الدبل كليك للفواتير والأجهزة وإدارة الموردين والبحث المطور واختيار التاريخ."""
        self.current_view_func = self.view_supplier_debts
        self.clear_content()

        top_frame = tk.Frame(self.content_frame, bg=self.COLOR_BG)
        top_frame.pack(fill="x", padx=15, pady=10)

        tk.Label(top_frame, text="🏭 مديونيات وفواتير الموردين", font=("Segoe UI", 15, "bold"), bg=self.COLOR_BG, fg=self.COLOR_BLUE).pack(side="right")

        search_box = tk.Frame(top_frame, bg=self.COLOR_CARD, padx=10, pady=5, highlightthickness=1, highlightbackground=self.COLOR_TOPBAR)
        search_box.pack(side="left")

        tk.Label(search_box, text="بحث بـ:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 9, "bold")).pack(side="right", padx=3)
        search_type_cb = ttk.Combobox(search_box, values=["الكل", "اسم المورد", "رقم الفاتورة", "التاريخ"], state="readonly", width=12, font=("Segoe UI", 9, "bold"))
        search_type_cb.current(0)
        search_type_cb.pack(side="right", padx=4)

        search_entry = tk.Entry(search_box, font=("Segoe UI", 10, "bold"), width=18, justify="right", bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT)
        search_entry.pack(side="right", padx=4, ipady=2)

        def filter_inv(e=None): load_invoices()

        cal_btn = tk.Button(
            search_box, text="📅 اختر تاريخ",
            command=lambda: (search_type_cb.set("التاريخ"), self.open_date_picker(search_entry, on_select_callback=filter_inv)),
            bg=self.COLOR_TOPBAR, fg=self.COLOR_TEXT, font=("Segoe UI", 9, "bold"), padx=6, cursor="hand2"
        )
        cal_btn.pack(side="right", padx=3)

        def on_search_type_change(e=None):
            if search_type_cb.get() == "التاريخ" and not search_entry.get().strip():
                self.open_date_picker(search_entry, on_select_callback=filter_inv)
            else:
                filter_inv()

        search_entry.bind("<Return>", filter_inv)
        search_type_cb.bind("<<ComboboxSelected>>", on_search_type_change)
        tk.Button(search_box, text="🔍 بحث", command=filter_inv, bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 9, "bold"), padx=10, cursor="hand2").pack(side="right", padx=3)
        tk.Button(search_box, text="🔄 الكل", command=lambda: (search_entry.delete(0, tk.END), search_type_cb.current(0), filter_inv()), bg=self.COLOR_TOPBAR, fg=self.COLOR_TEXT, font=("Segoe UI", 9, "bold"), padx=8, cursor="hand2").pack(side="right", padx=2)

        filter_frame = tk.Frame(top_frame, bg=self.COLOR_BG)
        filter_frame.pack(side="right", padx=15)
        status_var = tk.StringVar(value="UNPAID")
        
        tk.Radiobutton(filter_frame, text="غير مدفوع (المتبقي)", variable=status_var, value="UNPAID", command=filter_inv, bg=self.COLOR_BG, fg=self.COLOR_TEXT, selectcolor=self.COLOR_CARD, font=("Segoe UI", 9, "bold")).pack(side="right", padx=4)
        tk.Radiobutton(filter_frame, text="مدفوع بالكامل", variable=status_var, value="PAID", command=filter_inv, bg=self.COLOR_BG, fg=self.COLOR_TEXT, selectcolor=self.COLOR_CARD, font=("Segoe UI", 9, "bold")).pack(side="right", padx=4)
        tk.Radiobutton(filter_frame, text="الكل", variable=status_var, value="ALL", command=filter_inv, bg=self.COLOR_BG, fg=self.COLOR_TEXT, selectcolor=self.COLOR_CARD, font=("Segoe UI", 9, "bold")).pack(side="right", padx=4)

        tables_frame = tk.Frame(self.content_frame, bg=self.COLOR_BG)
        tables_frame.pack(fill="both", expand=True, padx=15, pady=5)

        inv_frame = tk.LabelFrame(tables_frame, text="📋 فواتير الموردين (انقر مرتين على الفاتورة لعرض سجل الدفعات والتفاصيل)", bg=self.COLOR_BG, fg=self.COLOR_BLUE, font=("Segoe UI", 11, "bold"))
        inv_frame.pack(fill="both", expand=True, side="top", pady=5)

        columns_inv = ("رقم الفاتورة", "اسم المورد", "نوع المورد", "التاريخ", "الإجمالي", "المدفوع", "المتبقي", "الحالة")
        tree_inv = ttk.Treeview(inv_frame, columns=columns_inv, show="headings", height=6)
        for col in columns_inv:
            tree_inv.heading(col, text=col)
            tree_inv.column(col, width=100, anchor="center")
        tree_inv.pack(fill="both", expand=True, padx=5, pady=5)

        dev_frame = tk.LabelFrame(tables_frame, text="📱 تفاصيل الأجهزة بالفاتورة المختارة (انقر مرتين على الجهاز لعرض كارت التفاصيل الشامل)", bg=self.COLOR_BG, fg=self.COLOR_BLUE, font=("Segoe UI", 11, "bold"))
        dev_frame.pack(fill="both", expand=True, side="bottom", pady=5)

        columns_dev = ("ID الجهاز", "الماركة", "الموديل", "الحالة", "بعلبة", "السيريال / IMEI", "سعر الشراء", "ملاحظات الشراء")
        tree_dev = ttk.Treeview(dev_frame, columns=columns_dev, show="headings", height=5)
        for col in columns_dev:
            tree_dev.heading(col, text=col)
            tree_dev.column(col, width=105, anchor="center")
        tree_dev.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.bind_treeview_double_click(tree_dev, "ID الجهاز")

        def load_invoices():
            for row in tree_inv.get_children(): tree_inv.delete(row)
            for row in tree_dev.get_children(): tree_dev.delete(row)
            q = search_entry.get().strip()
            st = status_var.get()
            st_map = {"الكل": "ALL", "اسم المورد": "NAME", "رقم الفاتورة": "ID", "التاريخ": "DATE"}
            invs = self.db.get_supplier_invoices(q, st, st_map.get(search_type_cb.get(), "ALL"))
            for i in invs:
                status_display = "تم السداد 🟢" if i['remaining_amount'] <= 0 else "غير مسدد 🔴"
                tree_inv.insert("", "end", values=(i['id'], i['supplier_name'], i.get('supplier_type', 'تاجر'), i['inv_date'],
                                                  fmt_curr(i['total_amount']), fmt_curr(i['paid_amount']),
                                                  fmt_curr(i['remaining_amount']), status_display))

        def on_invoice_select(event):
            for row in tree_dev.get_children(): tree_dev.delete(row)
            selected = tree_inv.selection()
            if not selected: return
            inv_id = self.clean_id_val(tree_inv.item(selected[0])['values'][0])
            if inv_id is None: return
            devices = self.db.get_invoice_devices(inv_id)
            can_see = self.has_permission('can_view_buy_price')
            for d in devices:
                p_val = fmt_curr(d['buy_price']) if can_see else "***"
                cond_txt = d.get('device_condition') or "مستعمل"
                box_txt = "نعم 📦" if d.get('has_box', True) else "بدون ❌"
                tree_dev.insert("", "end", values=(
                    d['id'], d['category'], d['model'], cond_txt, box_txt,
                    d['imei_serial'], p_val, d.get('notes') or '-'
                ))

        def show_supplier_invoice_details_modal(event):
            selected = tree_inv.selection()
            if not selected: return
            inv_vals = tree_inv.item(selected[0])['values']
            inv_id = self.clean_id_val(inv_vals[0])
            if inv_id is None: return

            iwin = tk.Toplevel(self)
            iwin.title(f"تفاصيل فاتورة المورد #{inv_id}")
            iwin.geometry("680x560")
            iwin.configure(bg=self.COLOR_BG)
            iwin.grab_set()

            header = tk.Frame(iwin, bg=self.COLOR_TOPBAR, pady=10)
            header.pack(fill="x")
            tk.Label(header, text=fix_bidi(f"🏭 تفاصيل فاتورة المورد: {inv_vals[1]} (رقم الفاتورة #{inv_id})"), font=("Segoe UI", 13, "bold"), bg=self.COLOR_TOPBAR, fg=self.COLOR_BLUE).pack()

            box = tk.Frame(iwin, bg=self.COLOR_BG, padx=15, pady=10)
            box.pack(fill="both", expand=True)

            sum_card = tk.LabelFrame(box, text="💰 ملخص الفاتورة والمديونية", bg=self.COLOR_CARD, fg=self.COLOR_BLUE, font=("Segoe UI", 10, "bold"), padx=10, pady=8)
            sum_card.pack(fill="x", pady=5)

            sum_info = [
                (fix_bidi(f"اسم المورد: {inv_vals[1]}"), fix_bidi(f"نوع المورد: {inv_vals[2]}")),
                (fix_bidi(f"إجمالي الفاتورة: {inv_vals[4]}"), fix_bidi(f"تاريخ الفاتورة: {inv_vals[3]}")),
                (fix_bidi(f"إجمالي المدفوع: {inv_vals[5]}"), fix_bidi(f"المتبقي (المديونية): {inv_vals[6]}")),
                (fix_bidi(f"حالة الفاتورة: {inv_vals[7]}"), "")
            ]
            for r, (c1, c2) in enumerate(sum_info):
                tk.Label(sum_card, text=c1, bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=r, column=1, sticky="e", padx=10, pady=3)
                tk.Label(sum_card, text=c2, bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).grid(row=r, column=0, sticky="e", padx=10, pady=3)
                sum_card.grid_columnconfigure(0, weight=1)
                sum_card.grid_columnconfigure(1, weight=1)

            pay_card = tk.LabelFrame(box, text="📜 سجل الدفعات والأقساط المسددة (التواريخ والمستخدم الدافع)", bg=self.COLOR_CARD, fg=self.COLOR_BLUE, font=("Segoe UI", 10, "bold"), padx=10, pady=5)
            pay_card.pack(fill="both", expand=True, pady=10)

            p_cols = ("م", "المبلغ المدفوع", "تاريخ الدفعة", "المستخدم الدافع")
            p_tree = ttk.Treeview(pay_card, columns=p_cols, show="headings", height=6)
            for c in p_cols:
                p_tree.heading(c, text=c)
                p_tree.column(c, anchor="center")
            p_tree.pack(fill="both", expand=True)

            payments = self.db.get_supplier_invoice_payments(inv_id)
            for idx, p in enumerate(payments, 1):
                p_tree.insert("", "end", values=(idx, fmt_curr(p['payment_amount']), p['payment_date_formatted'], p['user_name']))

        tree_inv.bind("<<TreeviewSelect>>", on_invoice_select)
        tree_inv.bind("<Double-1>", show_supplier_invoice_details_modal)
        load_invoices()

        act_frame = tk.Frame(self.content_frame, bg=self.COLOR_CARD, pady=10)
        act_frame.pack(fill="x", padx=15, pady=10)

        def open_supplier_management_modal():
            mwin = tk.Toplevel(self)
            mwin.title("إدارة الموردين وتعديل بياناتهم")
            mwin.geometry("760x540")
            mwin.configure(bg=self.COLOR_BG)
            mwin.grab_set()

            top_m = tk.Frame(mwin, bg=self.COLOR_BG)
            top_m.pack(fill="x", padx=15, pady=10)

            tk.Label(top_m, text="👥 إدارة الموردين وتعديل البيانات (تاجر / زبون)", font=("Segoe UI", 14, "bold"), bg=self.COLOR_BG, fg=self.COLOR_BLUE).pack(side="right")

            s_search_box = tk.Frame(top_m, bg=self.COLOR_CARD, padx=8, pady=4, highlightthickness=1, highlightbackground=self.COLOR_TOPBAR)
            s_search_box.pack(side="left")
            tk.Label(s_search_box, text="🔍 بحث بالموردين:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 9, "bold")).pack(side="right", padx=4)
            s_search_e = tk.Entry(s_search_box, font=("Segoe UI", 10, "bold"), width=22, justify="right", bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT)
            s_search_e.pack(side="right", padx=4, ipady=2)

            s_cols = ("ID", "اسم المورد", "الهاتف", "نوع المورد (تاجر / زبون)")
            s_tree = ttk.Treeview(mwin, columns=s_cols, show="headings", height=9)
            for c in s_cols:
                s_tree.heading(c, text=c)
                s_tree.column(c, anchor="center")
            s_tree.pack(fill="both", expand=True, padx=15, pady=5)

            def load_supps(e=None):
                for r in s_tree.get_children(): s_tree.delete(r)
                q_s = s_search_e.get().strip()
                for s in self.db.get_all_suppliers(q_s if q_s else None):
                    s_tree.insert("", "end", values=(s['id'], s['name'], s['phone'] or '-', s.get('supplier_type', 'تاجر')))

            s_search_e.bind("<KeyRelease>", load_supps)
            load_supps()

            sb_bar = tk.Frame(mwin, bg=self.COLOR_BG)
            sb_bar.pack(pady=10)

            def open_supp_form(supp_data=None):
                is_e = supp_data is not None
                sw = tk.Toplevel(mwin)
                sw.title("تعديل بيانات مورد" if is_e else "إضافة مورد جديد")
                sw.geometry("380x290")
                sw.configure(bg=self.COLOR_CARD)
                sw.grab_set()

                tk.Label(sw, text="✏️ تعديل بيانات المورد" if is_e else "➕ إضافة مورد جديد", bg=self.COLOR_CARD, fg=self.COLOR_BLUE, font=("Segoe UI", 12, "bold")).pack(pady=8)

                tk.Label(sw, text="اسم المورد:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(pady=3)
                en = tk.Entry(sw, bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="right", font=("Segoe UI", 10), width=26)
                if is_e: en.insert(0, supp_data['name'])
                en.pack(pady=3)
                en.focus()

                tk.Label(sw, text="رقم الهاتف:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(pady=3)
                ep = tk.Entry(sw, bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, justify="right", font=("Segoe UI", 10), width=26, validate="key", validatecommand=self.vcmd_num)
                if is_e: ep.insert(0, supp_data['phone'] or '')
                ep.pack(pady=3)

                tk.Label(sw, text="نوع المورد (تاجر أم زبون عادي):", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(pady=3)
                ecb = ttk.Combobox(sw, values=["تاجر", "زبون / بيع عادي"], state="readonly", font=("Segoe UI", 10), width=24)
                ecb.current(0 if not is_e or supp_data.get('supplier_type') == 'تاجر' else 1)
                ecb.pack(pady=3)

                def do_save():
                    name = en.get().strip()
                    phone = ep.get().strip()
                    stype = "تاجر" if "تاجر" in ecb.get() else "زبون"
                    if not name:
                        messagebox.showwarning("تنبيه", "برجاء إدخال اسم المورد!", parent=sw)
                        return
                    if is_e: self.db.update_supplier(supp_data['id'], name, phone, stype)
                    else: self.db.add_supplier(name, phone, stype)
                    sw.destroy()
                    load_supps()
                    load_invoices()

                en.bind("<Return>", lambda e: ep.focus())
                ep.bind("<Return>", lambda e: do_save())
                tk.Button(sw, text="💾 حفظ البيانات", command=do_save, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"), padx=15, cursor="hand2").pack(pady=12)

            def edit_selected_supp(event=None):
                sel = s_tree.selection()
                if not sel:
                    messagebox.showwarning("تنبيه", "يرجى تحديد مورد لتعديل بياناته!", parent=mwin)
                    return
                sid = self.clean_id_val(s_tree.item(sel[0])['values'][0])
                supps = self.db.get_all_suppliers()
                target = next((s for s in supps if s['id'] == sid), None)
                if target: open_supp_form(target)

            def del_selected_supp():
                sel = s_tree.selection()
                if not sel:
                    messagebox.showwarning("تنبيه", "يرجى تحديد مورد لتعطيله!", parent=mwin)
                    return
                sid = self.clean_id_val(s_tree.item(sel[0])['values'][0])
                if messagebox.askyesno("تأكيد", "هل أنت متأكد من تعطيل هذا المورد؟", parent=mwin):
                    self.db.delete_supplier(sid)
                    load_supps()
                    load_invoices()

            s_tree.bind("<Double-1>", edit_selected_supp)
            tk.Button(sb_bar, text="➕ إضافة مورد جديد", command=lambda: open_supp_form(), bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"), padx=12, cursor="hand2").pack(side="right", padx=5)
            tk.Button(sb_bar, text="✏️ تعديل بيانات المورد", command=edit_selected_supp, bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold"), padx=12, cursor="hand2").pack(side="right", padx=5)
            tk.Button(sb_bar, text="🗑️ تعطيل المورد", command=del_selected_supp, bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 10, "bold"), padx=12, cursor="hand2").pack(side="right", padx=5)

        tk.Button(act_frame, text="👥 إدارة الموردين", command=open_supplier_management_modal, bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold"), cursor="hand2").pack(side="left", padx=10)

        tk.Label(act_frame, text="مبلغ الدفعة للمورد:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10, "bold")).pack(side="right", padx=5)
        pay_entry = tk.Entry(act_frame, font=("Segoe UI", 10), width=15, bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, validate="key", validatecommand=self.vcmd_num)
        pay_entry.pack(side="right", padx=5)

        def do_pay_supplier():
            selected = tree_inv.selection()
            if not selected:
                messagebox.showwarning("تنبيه", "يرجى تحديد فاتورة لتسديد الدفعة لها أولاً!")
                return
            inv_vals = tree_inv.item(selected[0])['values']
            inv_id = self.clean_id_val(inv_vals[0])
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
        tk.Button(act_frame, text="💵 تسديد دفعة للمورد (Enter)", command=do_pay_supplier, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"), cursor="hand2").pack(side="right", padx=10)

        def open_print_options_popup():
            selected = tree_inv.selection()
            if not selected:
                messagebox.showwarning("تنبيه", "يرجى تحديد فاتورة لطباعتها!")
                return
            inv_vals = tree_inv.item(selected[0])['values']
            inv_id = self.clean_id_val(inv_vals[0])
            
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
                    'customer_name': f"المورد: {inv_vals[1]}",
                    'customer_phone': "-",
                    'device': first_dev,
                    'original_price': inv_vals[4],
                    'discount': 0.0,
                    'sell_price': inv_vals[4],
                    'cash_received': inv_vals[5],
                    'remaining_balance': inv_vals[6],
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

        tk.Label(fin_top, text="💰 التقرير المالي الكامل والسيولة التراكمية", font=("Segoe UI", 15, "bold"), bg=self.COLOR_BG, fg=self.COLOR_BLUE).pack(side="right")

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

            tk.Button(cap_win, text="حفظ السيولة", command=save_cap, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"), padx=15, cursor="hand2").pack(pady=15)

        tk.Button(act_fin_frame, text="➕ إضافة / تغذية سيولة مالية جديدة", command=open_add_capital_popup, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 11, "bold"), padx=15, pady=5, cursor="hand2").pack(side="right", padx=10)
        tk.Button(act_fin_frame, text="🔄 تحديث البيانات", command=refresh_fin_ui, bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold"), padx=15, pady=5, cursor="hand2").pack(side="left", padx=10)

        tk.Label(tab_sales, text="📊 تقارير المبيعات والأرباح التفصيلية", font=("Segoe UI", 15, "bold"), bg=self.COLOR_BG, fg=self.COLOR_BLUE).pack(pady=10)

        cards_frame = tk.Frame(tab_sales, bg=self.COLOR_BG)
        cards_frame.pack(fill="x", padx=15, pady=5)

        lbl_tot_sales = tk.Label(cards_frame, text="المبيعات: 0", font=("Segoe UI", 11, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_TEXT, width=25, pady=10)
        lbl_tot_sales.pack(side="right", padx=5)

        lbl_tot_profit = tk.Label(cards_frame, text="صافي الربح: 0", font=("Segoe UI", 11, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_ACCENT, width=25, pady=10)
        lbl_tot_profit.pack(side="right", padx=5)

        filter_frame = tk.Frame(tab_sales, bg=self.COLOR_CARD, padx=12, pady=6, highlightthickness=1, highlightbackground=self.COLOR_TOPBAR)
        filter_frame.pack(pady=5)

        tk.Label(filter_frame, text="من تاريخ:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 9, "bold")).pack(side="right", padx=3)
        e_from = tk.Entry(filter_frame, width=12, justify="center", font=("Segoe UI", 10, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT)
        e_from.insert(0, datetime.now().strftime("%Y-%m-01"))
        e_from.pack(side="right", padx=2)
        tk.Button(filter_frame, text="📅", command=lambda: self.open_date_picker(e_from, on_select_callback=load_rep), bg=self.COLOR_TOPBAR, fg=self.COLOR_TEXT, font=("Segoe UI", 9), padx=5, cursor="hand2").pack(side="right", padx=4)

        tk.Label(filter_frame, text="إلى تاريخ:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 9, "bold")).pack(side="right", padx=3)
        e_to = tk.Entry(filter_frame, width=12, justify="center", font=("Segoe UI", 10, "bold"), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT)
        e_to.insert(0, datetime.now().strftime("%Y-%m-%d"))
        e_to.pack(side="right", padx=2)
        tk.Button(filter_frame, text="📅", command=lambda: self.open_date_picker(e_to, on_select_callback=load_rep), bg=self.COLOR_TOPBAR, fg=self.COLOR_TEXT, font=("Segoe UI", 9), padx=5, cursor="hand2").pack(side="right", padx=4)

        can_see_cost = self.has_permission('can_view_buy_price')
        cols = ("ID الجهاز", "الموديل", "الحالة", "بعلبة", "السيريال", "الشراء", "البيع", "النقدي", "المتبقي", "الربح", "العميل", "التاريخ", "البائع")
        if not can_see_cost:
            cols = ("ID الجهاز", "الموديل", "الحالة", "بعلبة", "السيريال", "البيع", "النقدي", "المتبقي", "العميل", "التاريخ", "البائع")

        tree = ttk.Treeview(tab_sales, columns=cols, show="headings")
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=85, anchor="center")
        tree.pack(fill="both", expand=True, padx=15, pady=5)
        self.bind_treeview_double_click(tree, "ID الجهاز")

        def load_rep():
            for row in tree.get_children(): tree.delete(row)
            d_from = e_from.get().strip()
            d_to = e_to.get().strip()

            sales = self.db.get_sales_report_advanced(d_from, d_to)
            tot_s = sum(float(s['sell_price']) for s in sales)
            tot_p = sum(float(s['net_profit']) for s in sales)

            lbl_tot_sales.config(text=fix_bidi(f"إجمالي المبيعات: {fmt_curr(tot_s)}"))
            if can_see_cost:
                lbl_tot_profit.config(text=fix_bidi(f"صافي الأرباح: {fmt_curr(tot_p)}"))
            else:
                lbl_tot_profit.config(text="صافي الأرباح: ***")

            for s in sales:
                cond_txt = s.get('device_condition') or "مستعمل"
                box_txt = "نعم 📦" if s.get('has_box', True) else "بدون ❌"
                if can_see_cost:
                    vals = (s['device_id'], s['model'], cond_txt, box_txt, s['imei_serial'],
                            fmt_curr(s['buy_price']), fmt_curr(s['sell_price']),
                            fmt_curr(s['cash_received']), fmt_curr(s['remaining_balance']),
                            fmt_curr(s['net_profit']), s['customer_name'], s['sell_date_formatted'], s['seller_name'])
                else:
                    vals = (s['device_id'], s['model'], cond_txt, box_txt, s['imei_serial'],
                            fmt_curr(s['sell_price']), fmt_curr(s['cash_received']),
                            fmt_curr(s['remaining_balance']), s['customer_name'], s['sell_date_formatted'], s['seller_name'])
                tree.insert("", "end", values=vals)

        tk.Button(filter_frame, text="🔍 تطبيق الفلترة", command=load_rep, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 9, "bold"), padx=10, cursor="hand2").pack(side="right", padx=5)
        load_rep()

if __name__ == "__main__":
    app = MasterMobileApp()
    app.mainloop()

