import tkinter as tk
from tkinter import ttk, messagebox
from database import DatabaseManager
from datetime import datetime
import tempfile
import os

class MasterMobileApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("نظام الهاواتف مركز هشام كيوان")
        self.geometry("1300x780")
        
        self.is_dark_mode = True
        self.apply_theme_colors()

        self.configure(bg=self.COLOR_BG)
        self.db = DatabaseManager()
        self.current_user = None
        self.current_view_func = None

        self.setup_styles()
        self.withdraw()
        self.show_login_dialog()

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
                             rowheight=35, 
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
        login_win.title("تسجيل الدخول للنظام")
        login_win.geometry("420x350")
        login_win.configure(bg=self.COLOR_CARD)
        login_win.resizable(False, False)
        login_win.protocol("WM_DELETE_WINDOW", self.destroy)
        login_win.grab_set()

        tk.Label(login_win, text="🔐 تسجيل الدخول للنظام", font=("Segoe UI", 16, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_BLUE).pack(pady=20)

        tk.Label(login_win, text="اسم المستخدم:", bg=self.COLOR_CARD, fg=self.COLOR_MUTED, font=("Segoe UI", 10)).pack()
        users_list = self.db.get_all_users()
        user_cb = ttk.Combobox(login_win, values=[u['username'] for u in users_list], font=("Segoe UI", 10))
        if user_cb['values']: user_cb.current(0)
        user_cb.pack(pady=5)

        tk.Label(login_win, text="كلمة السر:", bg=self.COLOR_CARD, fg=self.COLOR_MUTED, font=("Segoe UI", 10)).pack()
        pass_entry = tk.Entry(login_win, show="*", justify="center", font=("Segoe UI", 11), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT)
        pass_entry.pack(pady=5)
        pass_entry.focus()

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
                self.build_main_ui()
                self.view_inventory()
            else:
                messagebox.showerror("خطأ", "كلمة السر أو اسم المستخدم غير صحيح!", parent=login_win)

        pass_entry.bind("<Return>", lambda e: try_login())
        tk.Button(login_win, text="دخول للنظام", command=try_login, bg=self.COLOR_ACCENT, fg="#ffffff", font=("Segoe UI", 11, "bold"), width=15, relief="flat", cursor="hand2").pack(pady=20)

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

        top_bar = tk.Frame(self, bg=self.COLOR_TOPBAR, height=55)
        top_bar.pack(fill="x", side="top")

        tk.Label(top_bar, text="📱 نظام المحل الذكي", font=("Segoe UI", 13, "bold"), bg=self.COLOR_TOPBAR, fg=self.COLOR_ACCENT).pack(side="right", padx=20)
        
        user_info = f"المستخدم: {self.current_user['full_name']}" if self.current_user else ""
        tk.Label(top_bar, text=user_info, font=("Segoe UI", 10, "bold"), bg=self.COLOR_TOPBAR, fg=self.COLOR_TEXT).pack(side="left", padx=20)
        
        tk.Button(top_bar, text="تسجيل الخروج", command=self.logout, bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2").pack(side="left", padx=5)
        tk.Button(top_bar, text="🌓 تبديل الوضع (ليلي/نهاري)", command=self.toggle_theme, bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2").pack(side="left", padx=5)

        nav_frame = tk.Frame(self, bg=self.COLOR_TOPBAR, width=220)
        nav_frame.pack(fill="y", side="right")

        self.content_frame = tk.Frame(self, bg=self.COLOR_BG)
        self.content_frame.pack(fill="both", expand=True, side="left")

        buttons = [
            ("📦 المخزون ورأس المال", self.view_inventory),
            ("🔍 الاستعلام والبيع", self.view_search_sale),
            ("🛒 الشراء (إدخال جهاز)", self.view_buy),
            ("💳 ديون العملاء (الخرج)", self.view_customer_debts),
            ("🏭 مديونية الموردين", self.view_supplier_debts),
            ("📊 التقارير والأرباح", self.view_reports)
        ]

        for text, cmd in buttons:
            btn = tk.Button(nav_frame, text=text, command=cmd, bg=self.COLOR_CARD, fg=self.COLOR_TEXT, 
                            font=("Segoe UI", 10, "bold"), anchor="e", padx=20, relief="flat", height=2, cursor="hand2")
            btn.pack(fill="x", pady=2)

    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def view_buy(self):
        self.current_view_func = self.view_buy
        self.clear_content()
        tk.Label(self.content_frame, text="تسجيل جهاز جديد في المخزون", font=("Segoe UI", 15, "bold"), bg=self.COLOR_BG, fg=self.COLOR_BLUE).pack(pady=15)

        form = tk.Frame(self.content_frame, bg=self.COLOR_CARD, padx=25, pady=25)
        form.pack(pady=10)

        labels = ["الماركة (النوع):", "الموديل:", "المساحة:", "الرامات:", "نسبة البطارية:", "السيريال / IMEI:", "سعر الشراء:", "المورد:"]
        self.buy_entries = {}

        for i, text in enumerate(labels):
            row, col = divmod(i, 2)
            tk.Label(form, text=text, bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10)).grid(row=row*2, column=col*2, sticky="e", padx=10, pady=5)
            
            if text == "المورد:":
                supp_frame = tk.Frame(form, bg=self.COLOR_CARD)
                suppliers = self.db.get_all_suppliers()
                cb = ttk.Combobox(supp_frame, values=[s['name'] for s in suppliers], state="readonly", font=("Segoe UI", 10))
                if suppliers: cb.current(0)
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
                    
                    tk.Label(ns_win, text="رقم الهاتف:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT).pack(pady=5)
                    p_entry = tk.Entry(ns_win, bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, justify="right")
                    p_entry.pack(pady=5)

                    def save_supp():
                        name = n_entry.get().strip()
                        phone = p_entry.get().strip()
                        if name:
                            self.db.add_supplier(name, phone)
                            updated_supps = self.db.get_all_suppliers()
                            cb['values'] = [s['name'] for s in updated_supps]
                            cb.current(len(updated_supps)-1)
                            self.buy_entries['supplier'] = (cb, updated_supps)
                            ns_win.destroy()
                    tk.Button(ns_win, text="حفظ", command=save_supp, bg=self.COLOR_ACCENT, fg="white").pack(pady=10)

                tk.Button(supp_frame, text="+", command=add_new_supplier_popup, bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 9, "bold")).pack(side="right")
                supp_frame.grid(row=row*2+1, column=col*2, padx=10, pady=5)
                self.buy_entries['supplier'] = (cb, suppliers)
            else:
                entry = tk.Entry(form, font=("Segoe UI", 10), justify="right", bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT)
                entry.grid(row=row*2+1, column=col*2, padx=10, pady=5)
                self.buy_entries[text] = entry

        self.buy_entries["السيريال / IMEI:"].focus()

        save_btn = tk.Button(self.content_frame, text="💾 حفظ وإدخال للمخزون", bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 11, "bold"), padx=25, pady=6, relief="flat", cursor="hand2")
        save_btn.pack(pady=20)

        def save_device():
            save_btn.config(state="disabled")
            try:
                cat = self.buy_entries["الماركة (النوع):"].get().strip()
                model = self.buy_entries["الموديل:"].get().strip()
                storage = self.buy_entries["المساحة:"].get().strip()
                ram = self.buy_entries["الرامات:"].get().strip()
                bat = int(self.buy_entries["نسبة البطارية:"].get().strip() or 100)
                imei = self.buy_entries["السيريال / IMEI:"].get().strip()
                price = float(self.buy_entries["سعر الشراء:"].get().strip())

                if not cat or not model or not imei:
                    messagebox.showwarning("تنبيه", "يرجى ملء كافة البيانات الأساسية والسيريال!")
                    save_btn.config(state="normal")
                    return
                
                cb, supps = self.buy_entries['supplier']
                supp_id = supps[cb.current()]['id'] if supps and cb.current() >= 0 else None

                dev_id = self.db.add_device(cat, model, storage, ram, bat, "", imei, price, supp_id, "", self.current_user['id'])
                messagebox.showinfo("نجاح", f"تم إضافة الجهاز بنجاح! ID المفتاح: #{dev_id}")
                
                if messagebox.yesno("طباعة", "هل تريد طباعة سند شراء الجهاز للمورد؟"):
                    self.print_purchase_receipt(cat, model, imei, price)

                for key, widget in self.buy_entries.items():
                    if key != 'supplier':
                        widget.delete(0, tk.END)
                self.buy_entries["السيريال / IMEI:"].focus()
                save_btn.config(state="normal")
            except ValueError:
                messagebox.showerror("خطأ", "يرجى التأكد من كتابة الأرقام بشكل صحيح في السعر والبطارية!")
                save_btn.config(state="normal")
            except Exception as e:
                messagebox.showerror("خطأ", f"تعذر الإضافة: {str(e)}")
                save_btn.config(state="normal")

        save_btn.config(command=save_device)

    def print_purchase_receipt(self, cat, model, imei, price):
        receipt_text = f"""
========================================
         سند إدخال جهاز (شراء)
========================================
التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}
الجهاز: {cat} {model}
السيريال IMEI: {imei}
سعر الشراء: {price} ج.م
المشرف: {self.current_user['full_name']}
========================================
"""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as f:
                f.write(receipt_text)
                temp_path = f.name
            os.startfile(temp_path, "print")
        except Exception as e:
            messagebox.showerror("خطأ", f"تعذر إرسال السند للطابعة: {str(e)}")

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

        columns = ("ID", "النوع", "الموديل", "المساحة", "الرامات", "البطارية", "السيريال / IMEI", "سعر الشراء", "المورد", "تاريخ الشراء")
        tree = ttk.Treeview(self.content_frame, columns=columns, show="headings")
        
        tree.tag_configure('even', background=self.COLOR_TREE_BG)
        tree.tag_configure('odd', background=self.COLOR_TREE_ALT)

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100, anchor="center")

        tree.pack(fill="both", expand=True, padx=15, pady=5)

        def load_tree(q=None):
            for row in tree.get_children(): tree.delete(row)
            devices = self.db.get_available_inventory(q)
            for idx, d in enumerate(devices):
                tag = 'even' if idx % 2 == 0 else 'odd'
                can_see = self.current_user['permissions'].get('can_view_buy_price', True) if isinstance(self.current_user['permissions'], dict) else True
                buy_p = f"{d['buy_price']} ج.م" if can_see else "***"
                tree.insert("", "end", values=(d['id'], d['category'], d['model'], d['storage'], d['ram'], 
                                              f"{d['battery_health']}%", d['imei_serial'], buy_p, 
                                              d['supplier_name'], d['buy_date_formatted']), tags=(tag,))

        load_tree()

        stat_bar = tk.Frame(self.content_frame, bg=self.COLOR_TOPBAR, height=45)
        stat_bar.pack(fill="x", side="bottom")

        overview = self.db.get_capital_statistics()
        info_text = f"إجمالي الأجهزة المتاحة: {overview['total_devices']} جهاز  |  رأس المال بالمخزن: {overview['total_capital']} ج.م"
        tk.Label(stat_bar, text=info_text, bg=self.COLOR_TOPBAR, fg=self.COLOR_ACCENT, font=("Segoe UI", 11, "bold")).pack(pady=8)

    def view_search_sale(self):
        self.current_view_func = self.view_search_sale
        self.clear_content()
        tk.Label(self.content_frame, text="الاستعلام والبيع السريع", font=("Segoe UI", 15, "bold"), bg=self.COLOR_BG, fg=self.COLOR_BLUE).pack(pady=15)

        search_bar = tk.Frame(self.content_frame, bg=self.COLOR_BG)
        search_bar.pack(pady=5)

        tk.Label(search_bar, text="امسح الباركود أو أدخل IMEI / ID:", bg=self.COLOR_BG, fg=self.COLOR_TEXT, font=("Segoe UI", 11)).pack(side="right", padx=5)
        search_entry = tk.Entry(search_bar, font=("Segoe UI", 12), width=25, bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT)
        search_entry.pack(side="right", padx=5)
        search_entry.focus()

        card = tk.Frame(self.content_frame, bg=self.COLOR_CARD, padx=25, pady=25)
        card.pack(pady=15, fill="x", padx=40)

        def perform_search(event=None):
            for widget in card.winfo_children(): widget.destroy()
            q = search_entry.get().strip()
            if not q: return

            dev = self.db.search_device_by_imei_or_id(q)
            if not dev:
                tk.Label(card, text="❌ لم يتم العثور على أي جهاز بهذا الرقم!", bg=self.COLOR_CARD, fg=self.COLOR_DANGER, font=("Segoe UI", 12, "bold")).pack()
                return

            can_see = self.current_user['permissions'].get('can_view_buy_price', True) if isinstance(self.current_user['permissions'], dict) else True
            buy_p_str = f"{dev['buy_price']} ج.م" if can_see else "***"

            info_frame = tk.Frame(card, bg=self.COLOR_CARD)
            info_frame.pack(fill="x", pady=5)

            tk.Label(info_frame, text=f"📱 الجهاز: {dev['category']} {dev['model']}", font=("Segoe UI", 14, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_BLUE).pack(anchor="e", pady=3)
            tk.Label(info_frame, text=f"🔹 المساحة: {dev['storage']} | الرامات: {dev['ram']} | البطارية: {dev['battery_health']}%", font=("Segoe UI", 11), bg=self.COLOR_CARD, fg=self.COLOR_TEXT).pack(anchor="e", pady=2)
            tk.Label(info_frame, text=f"🔢 السيريال IMEI: {dev['imei_serial']} | رقم التتبع ID: #{dev['id']}", font=("Segoe UI", 11), bg=self.COLOR_CARD, fg=self.COLOR_TEXT).pack(anchor="e", pady=2)
            tk.Label(info_frame, text=f"💰 سعر الشراء: {buy_p_str} | 🏭 المورد: {dev['supplier_name']}", font=("Segoe UI", 11), bg=self.COLOR_CARD, fg=self.COLOR_MUTED).pack(anchor="e", pady=2)

            if not dev['is_sold']:
                tk.Label(card, text="الحالة بالمخزن: متاح للبيع ✅", bg=self.COLOR_CARD, fg=self.COLOR_ACCENT, font=("Segoe UI", 12, "bold")).pack(pady=10)
                tk.Button(card, text="🛒 فتح شاشة البيع ", command=lambda: open_sale_popup(dev), bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 12, "bold"), padx=20, pady=8, relief="flat", cursor="hand2").pack(pady=10)
            else:
                tk.Label(card, text=f"الحالة بالمخزن: مباع للعميل ({dev['customer_name']}) ❌ - بسعر بيع: {dev['sell_price']} ج.م", bg=self.COLOR_CARD, fg=self.COLOR_DANGER, font=("Segoe UI", 12, "bold")).pack(pady=10)
                tk.Button(card, text="🔄 عمل مرتجع وإرجاعه للمخزن", command=lambda: do_return(dev['id']), bg=self.COLOR_DANGER, fg="white", font=("Segoe UI", 11, "bold"), padx=15, pady=6, relief="flat", cursor="hand2").pack(pady=10)

        search_entry.bind("<Return>", perform_search)
        tk.Button(search_bar, text="بحث", command=perform_search, bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold")).pack(side="right")

        def open_sale_popup(dev):
            pop = tk.Toplevel(self)
            pop.title("شاشة البيع")
            pop.geometry("480x550")
            pop.configure(bg=self.COLOR_CARD)
            pop.grab_set()

            tk.Label(pop, text="🛒 إتمام فاتورة البيع للعميل", font=("Segoe UI", 15, "bold"), bg=self.COLOR_CARD, fg=self.COLOR_BLUE).pack(pady=15)

            form_frame = tk.Frame(pop, bg=self.COLOR_CARD, padx=20)
            form_frame.pack(fill="both", expand=True)

            entries = {}
            fields = [
                ("سعر البيع الاتفاقي:", "0.0"),
                ("اسم العميل:", ""),
                ("رقم الهاتف:", ""),
                ("المبلغ المدفوع الآن:", "0.0")
            ]

            for label_text, default_val in fields:
                tk.Label(form_frame, text=label_text, bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 11)).pack(anchor="e", pady=3)
                e = tk.Entry(form_frame, justify="right", font=("Segoe UI", 12), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT)
                if default_val != "":
                    e.insert(0, default_val)
                e.pack(fill="x", pady=3)
                entries[label_text] = e

            # أزرار الفصل المستقلة: زر للحفظ، وزر مستقل للطباعة
            btn_frame = tk.Frame(pop, bg=self.COLOR_CARD, pady=15)
            btn_frame.pack(fill="x")

            save_sale_btn = tk.Button(btn_frame, text="💾 تأكيد وحفظ البيع", bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 11, "bold"), width=18, relief="flat", cursor="hand2")
            save_sale_btn.pack(side="right", padx=10)

            print_invoice_btn = tk.Button(btn_frame, text="🖨️ طباعة الفاتورة", bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 11, "bold"), width=15, relief="flat", cursor="hand2", state="disabled")
            print_invoice_btn.pack(side="left", padx=10)

            saved_sale_data = {}

            def confirm_sale():
                save_sale_btn.config(state="disabled")
                try:
                    price = float(entries["سعر البيع الاتفاقي:"].get().strip())
                    c_name = entries["اسم العميل:"].get().strip()
                    c_phone = entries["رقم الهاتف:"].get().strip()
                    paid = float(entries["المبلغ المدفوع الآن:"].get().strip() or 0)

                    if not c_name:
                        messagebox.showwarning("تنبيه", "يرجى كتابة اسم العميل!", parent=pop)
                        save_sale_btn.config(state="normal")
                        return

                    sale_id = self.db.process_sale(dev['id'], price, c_name, c_phone, paid, "", self.current_user['id'])
                    
                    saved_sale_data.update({
                        'price': price, 'customer': c_name, 'paid': paid, 'remaining': max(0.0, price - paid)
                    })

                    messagebox.showinfo("نجاح", "تم حفظ وتأكيد عملية البيع بنجاح!", parent=pop)
                    print_invoice_btn.config(state="normal")
                    self.view_search_sale()
                except ValueError:
                    messagebox.showerror("خطأ", "يرجى التأكد من كتابة الأرقام بشكل صحيح!", parent=pop)
                    save_sale_btn.config(state="normal")
                except Exception as ex:
                    messagebox.showerror("خطأ", str(ex), parent=pop)
                    save_sale_btn.config(state="normal")

            def print_only():
                if not saved_sale_data:
                    messagebox.showwarning("تنبيه", "يجب حفظ الفاتورة أولاً قبل طباعتها!", parent=pop)
                    return
                self.print_customer_invoice(dev, saved_sale_data['price'], saved_sale_data['customer'], saved_sale_data['paid'], saved_sale_data['remaining'])
                pop.destroy()

            save_sale_btn.config(command=confirm_sale)
            print_invoice_btn.config(command=print_only)

        def do_return(dev_id):
            if messagebox.askyesno("تأكيد", "هل أنت متأكد من إجراء مرتجع لهذا الجهاز؟"):
                self.db.process_return(dev_id, self.current_user['id'])
                messagebox.showinfo("تم", "تم إرجاع الجهاز للمخزون بنجاح!")
                self.view_search_sale()

    def print_customer_invoice(self, dev, price, customer, paid, remaining):
        invoice_text = f"""
========================================
           فاتورة مبيعات هاتف
========================================
التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}
اسم العميل: {customer}
----------------------------------------
الجهاز: {dev['category']} {dev['model']}
المساحة: {dev['storage']} | الرامات: {dev['ram']}
السيريال IMEI: {dev['imei_serial']}
----------------------------------------
إجمالي السعر: {price} ج.م
المدفوع: {paid} ج.م
المتبقي: {remaining} ج.م
----------------------------------------
البائع: {self.current_user['full_name']}
شكراً لتعاملكم معنا!
========================================
"""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as f:
                f.write(invoice_text)
                temp_path = f.name
            os.startfile(temp_path, "print")
        except Exception as e:
            messagebox.showerror("خطأ طباعة", f"تعذر إرسال الفاتورة للطابعة: {str(e)}")

    def view_customer_debts(self):
        self.current_view_func = self.view_customer_debts
        self.clear_content()

        top_frame = tk.Frame(self.content_frame, bg=self.COLOR_BG)
        top_frame.pack(fill="x", padx=15, pady=10)

        tk.Label(top_frame, text="مستحقات وتأخيرات العملاء (الخرج)", font=("Segoe UI", 15, "bold"), bg=self.COLOR_BG, fg=self.COLOR_BLUE).pack(side="right")

        search_entry = tk.Entry(top_frame, font=("Segoe UI", 10), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT)
        search_entry.pack(side="left", padx=5)
        
        def filter_debts(e=None): load_debts(search_entry.get().strip())
        search_entry.bind("<Return>", filter_debts)
        tk.Button(top_frame, text="بحث", command=filter_debts, bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 9, "bold")).pack(side="left")

        columns = ("رقم الفاتورة", "ID الجهاز", "الموديل", "اسم العميل", "الهاتف", "تاريخ البيع", "الإجمالي", "المدفوع", "المتبقي")
        tree = ttk.Treeview(self.content_frame, columns=columns, show="headings")
        
        tree.tag_configure('even', background=self.COLOR_TREE_BG)
        tree.tag_configure('odd', background=self.COLOR_TREE_ALT)

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100, anchor="center")

        tree.pack(fill="both", expand=True, padx=15, pady=5)

        def load_debts(q=None):
            for row in tree.get_children(): tree.delete(row)
            debts = self.db.get_customer_debts(q)
            for idx, d in enumerate(debts):
                tag = 'even' if idx % 2 == 0 else 'odd'
                tree.insert("", "end", values=(d['sale_id'], d['device_id'], d['model'], d['customer_name'], 
                                              d['customer_phone'], d['sell_date_formatted'], d['sell_price'], 
                                              d['cash_received'], d['remaining_balance']), tags=(tag,))

        load_debts()

        pay_frame = tk.Frame(self.content_frame, bg=self.COLOR_CARD, pady=10)
        pay_frame.pack(fill="x", padx=15, pady=10)

        tk.Label(pay_frame, text="مبلغ التحصيل:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10)).pack(side="right", padx=5)
        amount_entry = tk.Entry(pay_frame, font=("Segoe UI", 10), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT)
        amount_entry.pack(side="right", padx=5)

        pay_btn = tk.Button(pay_frame, text="💵 تحصيل الدفعة", bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2")
        pay_btn.pack(side="right", padx=10)

        def pay_selected():
            pay_btn.config(state="disabled")
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("تنبيه", "حدد صَفاً من الجدول أولاً!")
                pay_btn.config(state="normal")
                return
            sale_id = tree.item(selected[0])['values'][0]
            try:
                amt = float(amount_entry.get().strip())
                self.db.pay_customer_debt(sale_id, amt, self.current_user['id'])
                messagebox.showinfo("نجاح", "تم تسجيل الدفعة وتحصيلها بدقة!")
                load_debts()
                amount_entry.delete(0, tk.END)
            except Exception as e:
                messagebox.showerror("خطأ", f"يرجى إدخال مبلغ صحيح! {str(e)}")
            pay_btn.config(state="normal")

        pay_btn.config(command=pay_selected)

    def view_supplier_debts(self):
        self.current_view_func = self.view_supplier_debts
        self.clear_content()

        top_frame = tk.Frame(self.content_frame, bg=self.COLOR_BG)
        top_frame.pack(fill="x", padx=15, pady=10)

        tk.Label(top_frame, text="مديونيات وفواتير الموردين", font=("Segoe UI", 15, "bold"), bg=self.COLOR_BG, fg=self.COLOR_BLUE).pack(side="right")

        search_entry = tk.Entry(top_frame, font=("Segoe UI", 10), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT)
        search_entry.pack(side="left", padx=5)
        
        def filter_supp(e=None): load_invoices(search_entry.get().strip())
        search_entry.bind("<Return>", filter_supp)
        tk.Button(top_frame, text="بحث", command=filter_supp, bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 9, "bold")).pack(side="left")

        columns = ("رقم الفاتورة", "اسم المورد", "التاريخ", "الإجمالي", "المدفوع", "المتبقي", "الحالة")
        tree = ttk.Treeview(self.content_frame, columns=columns, show="headings", height=8)
        
        tree.tag_configure('even', background=self.COLOR_TREE_BG)
        tree.tag_configure('odd', background=self.COLOR_TREE_ALT)

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100, anchor="center")

        tree.pack(fill="both", expand=False, padx=15, pady=5)

        tk.Label(self.content_frame, text="أجهزة الفاتورة الموردة:", font=("Segoe UI", 12, "bold"), bg=self.COLOR_BG, fg=self.COLOR_TEXT).pack(pady=5)
        dev_columns = ("ID", "النوع", "الموديل", "السيريال IMEI", "سعر الشراء")
        dev_tree = ttk.Treeview(self.content_frame, columns=dev_columns, show="headings", height=6)
        for col in dev_columns:
            dev_tree.heading(col, text=col)
            dev_tree.column(col, width=120, anchor="center")
        dev_tree.pack(fill="both", expand=True, padx=15, pady=5)

        def on_invoice_select(event):
            selected = tree.selection()
            if not selected: return
            inv_id = tree.item(selected[0])['values'][0]
            for row in dev_tree.get_children(): dev_tree.delete(row)
            devices = self.db.get_invoice_devices(inv_id)
            for d in devices:
                dev_tree.insert("", "end", values=(d['id'], d['category'], d['model'], d['imei_serial'], d['buy_price']))

        tree.bind("<<TreeviewSelect>>", on_invoice_select)

        def load_invoices(q=None):
            for row in tree.get_children(): tree.delete(row)
            invs = self.db.get_supplier_invoices(q)
            for idx, i in enumerate(invs):
                tag = 'even' if idx % 2 == 0 else 'odd'
                tree.insert("", "end", values=(i['id'], i['supplier_name'], i['inv_date'], i['total_amount'], 
                                              i['paid_amount'], i['remaining_amount'], i['status']), tags=(tag,))

        load_invoices()

        pay_frame = tk.Frame(self.content_frame, bg=self.COLOR_CARD, pady=10)
        pay_frame.pack(fill="x", padx=15, pady=10)

        tk.Label(pay_frame, text="مبلغ التسديد للمورد:", bg=self.COLOR_CARD, fg=self.COLOR_TEXT, font=("Segoe UI", 10)).pack(side="right", padx=5)
        amount_entry = tk.Entry(pay_frame, font=("Segoe UI", 10), bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT)
        amount_entry.pack(side="right", padx=5)

        pay_supp_btn = tk.Button(pay_frame, text="📤 تسديد المبلغ", bg=self.COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2")
        pay_supp_btn.pack(side="right", padx=10)

        def pay_supp():
            pay_supp_btn.config(state="disabled")
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("تنبيه", "حدد فاتورة أولاً!")
                pay_supp_btn.config(state="normal")
                return
            inv_id = tree.item(selected[0])['values'][0]
            try:
                amt = float(amount_entry.get().strip())
                self.db.pay_supplier_debt(inv_id, amt, self.current_user['id'])
                messagebox.showinfo("تم", "تم تسجيل دفع المبلغ للمورد!")
                load_invoices()
                amount_entry.delete(0, tk.END)
            except Exception as e:
                messagebox.showerror("خطأ", f"يرجى إدخال مبلغ صحيح! {str(e)}")
            pay_supp_btn.config(state="normal")

        pay_supp_btn.config(command=pay_supp)

        def print_supplier_invoice():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("تنبيه", "حدد فاتورة المورد للطباعة!")
                return
            vals = tree.item(selected[0])['values']
            inv_id, supp_name, inv_date, total, paid, rem, status = vals
            devices = self.db.get_invoice_devices(inv_id)

            inv_content = f"""
========================================
       فاتورة دين / استلام للمورد
========================================
رقم الفاتورة: #{inv_id} | التاريخ: {inv_date}
المورد: {supp_name}
----------------------------------------
قائمة الأجهزة الموردة بالسيريالات:
"""
            for d in devices:
                inv_content += f"- {d['category']} {d['model']} | IMEI: {d['imei_serial']} | السعر: {d['buy_price']} ج.م\n"

            inv_content += f"""----------------------------------------
إجمالي الفاتورة: {total} ج.م
المدفوع للمورد: {paid} ج.م
المتبقي للمورد: {rem} ج.م
الحالة: {status}
========================================
"""
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as f:
                    f.write(inv_content)
                    temp_path = f.name
                os.startfile(temp_path, "print")
            except Exception as e:
                messagebox.showerror("خطأ", f"تعذر طباعة فاتورة المورد: {str(e)}")

        tk.Button(pay_frame, text="🖨️ طباعة فاتورة المورد", command=print_supplier_invoice, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2").pack(side="right", padx=10)

    def view_reports(self):
        self.current_view_func = self.view_reports
        self.clear_content()
        tk.Label(self.content_frame, text="تقارير المبيعات والأرباح الشاملة", font=("Segoe UI", 15, "bold"), bg=self.COLOR_BG, fg=self.COLOR_BLUE).pack(pady=15)

        filter_frame = tk.Frame(self.content_frame, bg=self.COLOR_BG)
        filter_frame.pack(pady=5)

        now = datetime.now()
        tk.Label(filter_frame, text="الشهر:", bg=self.COLOR_BG, fg=self.COLOR_TEXT).pack(side="right", padx=2)
        m_entry = tk.Entry(filter_frame, width=5, justify="center", bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT)
        m_entry.insert(0, str(now.month))
        m_entry.pack(side="right", padx=5)

        tk.Label(filter_frame, text="السنة:", bg=self.COLOR_BG, fg=self.COLOR_TEXT).pack(side="right", padx=2)
        y_entry = tk.Entry(filter_frame, width=8, justify="center", bg=self.COLOR_ENTRY_BG, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT)
        y_entry.insert(0, str(now.year))
        y_entry.pack(side="right", padx=5)

        columns = ("ID الجهاز", "الموديل", "السيريال", "الشراء", "البيع", "النقدي", "المتبقي", "الربح", "العميل", "التاريخ", "البائع")
        tree = ttk.Treeview(self.content_frame, columns=columns, show="headings")

        tree.tag_configure('even', background=self.COLOR_TREE_BG)
        tree.tag_configure('odd', background=self.COLOR_TREE_ALT)

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=90, anchor="center")

        tree.pack(fill="both", expand=True, padx=15, pady=5)

        def load_rep():
            for row in tree.get_children(): tree.delete(row)
            try:
                m = int(m_entry.get().strip())
                y = int(y_entry.get().strip())
            except ValueError:
                messagebox.showwarning("تنبيه", "يرجى كتابة الشهر والسنة بشكل صحيح كأرقام!", parent=self.content_frame)
                return

            sales = self.db.get_monthly_sales_report(m, y)
            for idx, s in enumerate(sales):
                tag = 'even' if idx % 2 == 0 else 'odd'
                can_see = self.current_user['permissions'].get('can_view_buy_price', True) if isinstance(self.current_user['permissions'], dict) else True
                buy_p = f"{s['buy_price']}" if can_see else "***"
                profit = f"{s['net_profit']}" if can_see else "***"
                
                tree.insert("", "end", values=(s['device_id'], s['model'], s['imei_serial'], buy_p, 
                                              s['sell_price'], s['cash_received'], s['remaining_balance'], 
                                              profit, s['customer_name'], s['sell_date_formatted'], s['seller_name']), tags=(tag,))

        # ربط الزر الأخضر بشكل صحيح لدالة load_rep ليعمل بكفاءة تامة وتحديث الجدول
        tk.Button(filter_frame, text="عرض التقرير", command=load_rep, bg=self.COLOR_ACCENT, fg="white", font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="right", padx=5)
        
        # ربط مفتاح Enter عند الكتابة في خانات الشهر أو السنة لتنفيذ العرض مباشرة
        m_entry.bind("<Return>", lambda e: load_rep())
        y_entry.bind("<Return>", lambda e: load_rep())

        load_rep()

if __name__ == "__main__":
    app = MasterMobileApp()
    app.mainloop()