import os
import tempfile
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# محاولة تحميل مكتبات تشكيل العربي لمنع تقطيع الحروف أو انعكاس الكلمات الإنجليزية مع العربية
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_BIDI = True
except ImportError:
    HAS_BIDI = False

try:
    import qrcode
    HAS_QR = True
except ImportError:
    HAS_QR = False


def _clean_num_val(val):
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).replace('\u200f', '').replace('\u200e', '').replace('ج.م', '').replace(',', '').strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


def fmt_money(val):
    num = _clean_num_val(val)
    return f"{num:,.2f} ج.م"


def fix_arabic_text(text):
    """إعادة تشكيل النص العربي مع الحفاظ على ترتيب الكلمات الإنجليزية والأرقام بدون تشوه."""
    if text is None:
        return ""
    s = str(text).replace('\u200f', '').replace('\u200e', '').replace('\u202b', '').replace('\u202c', '').strip()
    if not s:
        return ""
    if HAS_BIDI:
        try:
            reshaped = arabic_reshaper.reshape(s)
            return get_display(reshaped)
        except Exception:
            return s
    return s


def _load_fonts(scale=1.0):
    font_candidates_bold = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/tahomabd.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "arialbd.ttf",
        "arial.ttf"
    ]
    font_candidates_reg = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "arial.ttf"
    ]

    bold_path = next((p for p in font_candidates_bold if os.path.exists(p)), None)
    reg_path = next((p for p in font_candidates_reg if os.path.exists(p)), None)

    try:
        if bold_path and reg_path:
            return {
                "title": ImageFont.truetype(bold_path, int(28 * scale)),
                "subtitle": ImageFont.truetype(bold_path, int(18 * scale)),
                "section": ImageFont.truetype(bold_path, int(16 * scale)),
                "bold": ImageFont.truetype(bold_path, int(14 * scale)),
                "body": ImageFont.truetype(reg_path, int(14 * scale)),
                "small": ImageFont.truetype(reg_path, int(12 * scale)),
            }
    except Exception:
        pass

    default_f = ImageFont.load_default()
    return {
        "title": default_f,
        "subtitle": default_f,
        "section": default_f,
        "bold": default_f,
        "body": default_f,
        "small": default_f,
    }


def _get_palette(style_name="color"):
    if style_name == "burgundy":
        return {
            "primary": "#7f1d1d",
            "secondary": "#991b1b",
            "header_bg": "#fef2f2",
            "table_hdr": "#7f1d1d",
            "table_hdr_text": "#ffffff",
            "accent_box": "#fff1f2",
            "border": "#450a0a",
            "text": "#111827",
            "muted": "#4b5563"
        }
    elif style_name == "grayscale":
        return {
            "primary": "#000000",
            "secondary": "#262626",
            "header_bg": "#f5f5f5",
            "table_hdr": "#262626",
            "table_hdr_text": "#ffffff",
            "accent_box": "#f5f5f5",
            "border": "#000000",
            "text": "#000000",
            "muted": "#404040"
        }
    else:
        return {
            "primary": "#1e3a8a",
            "secondary": "#1d4ed8",
            "header_bg": "#eff6ff",
            "table_hdr": "#1e3a8a",
            "table_hdr_text": "#ffffff",
            "accent_box": "#f0fdf4",
            "border": "#1e3a8a",
            "text": "#0f172a",
            "muted": "#475569"
        }


def generate_invoice_image(invoice_data):
    """
    توليد فاتورة احترافية عالية الدقة تدعم:
    1. فواتير البيع السريع (SALE)
    2. فواتير / إيصالات الخرج وديون العملاء (CUSTOMER_DEBT)
    3. فواتير وكشوف حساب الموردين (SUPPLIER_DEBT)
    مع خفض موضع الباركود والـ QR للأسفل وتوسيع الهوامش السفلية للقراءة الفورية بالسكانر.
    """
    if not os.path.exists("invoices"):
        try:
            os.makedirs("invoices", exist_ok=True)
        except Exception:
            pass

    paper_size = str(invoice_data.get("paper_size", "a4")).lower().strip()
    is_a5 = (paper_size == "a5")

    style_name = invoice_data.get("print_style", "color")
    palette = _get_palette(style_name)
    font_scale = 0.92 if is_a5 else 1.0
    fonts = _load_fonts(scale=font_scale)

    devices_list = invoice_data.get("devices_list") or []
    if not devices_list and invoice_data.get("device"):
        devices_list = [invoice_data["device"]]

    payments_list = invoice_data.get("payments_list") or []
    extra_rows_height = max(0, (len(devices_list) - 1) * 64) + (len(payments_list) * 30 if payments_list else 0)

    width = 820 if is_a5 else 900
    base_height = 1140 if is_a5 else 1180
    height = max(base_height, (1080 if is_a5 else 1120) + extra_rows_height)
    img = Image.new("RGB", (width, height), color="#ffffff")
    draw = ImageDraw.Draw(img)

    # الإطار الخارجي المزدوج
    draw.rectangle([(18, 18), (width - 18, height - 18)], outline=palette["border"], width=3)
    draw.rectangle([(24, 24), (width - 24, height - 24)], outline=palette["border"], width=1)

    # ترويسة المركز
    draw.rectangle([(36, 36), (width - 36, 145)], fill=palette["header_bg"], outline=palette["border"], width=2)

    if os.path.exists("logo.png"):
        try:
            logo = Image.open("logo.png").convert("RGBA")
            logo.thumbnail((85, 85), Image.Resampling.LANCZOS)
            img.paste(logo, (55, 48), logo)
        except Exception:
            pass

    doc_type = invoice_data.get("doc_type", "SALE")
    is_supp_doc = doc_type in ("SUPPLIER_INVOICE", "SUPPLIER_DEBT")

    if doc_type == "CUSTOMER_DEBT":
        sub_label = "بيان مديونية وتحصيل عميل (الخرج)"
    elif is_supp_doc:
        sub_label = "فاتورة مشتريات وتوريد بضاعة"
    else:
        sub_label = "فاتورة بيع وضمان معتمد"

    draw.text((width // 2, 68), fix_arabic_text("محل هشام كيوان"), fill=palette["primary"], font=fonts["title"], anchor="mm")
    draw.text((width // 2, 112), fix_arabic_text(sub_label), fill=palette["secondary"], font=fonts["subtitle"], anchor="mm")

    # بيانات المستند والعميل / المورد
    sale_id = invoice_data.get("sale_id") or invoice_data.get("invoice_id") or "-"
    if is_supp_doc:
        party_label = "المورد / التاجر:"
        cust_name = invoice_data.get("supplier_name") or "مورد تجاري"
        cust_phone = invoice_data.get("supplier_phone") or "غير مسجل"
    else:
        party_label = "العميل / المستلم:"
        cust_name = invoice_data.get("customer_name") or "عميل نقدي"
        cust_phone = invoice_data.get("customer_phone") or "غير مسجل"

    inv_date = invoice_data.get("date_str") or datetime.now().strftime("%Y-%m-%d %H:%M")
    seller_name = invoice_data.get("seller_name") or ""

    y = 162
    draw.rectangle([(36, y), (width - 36, y + 92)], fill="#ffffff", outline=palette["border"], width=1)

    right_x = width - 52
    left_x = 52

    inv_code = invoice_data.get("invoice_code") or (f"INV-{doc_type}-{sale_id}" if sale_id != "-" else f"INV-{doc_type}")
    page_n = invoice_data.get("page_num", 1)
    tot_p = invoice_data.get("total_pages", 1)
    page_txt = f"  (صفحة {page_n} من {tot_p})" if tot_p > 1 else ""
    draw.text((right_x, y + 18), fix_arabic_text(f"كود الفاتورة: {inv_code}  (#{sale_id}){page_txt}"), fill=palette["primary"], font=fonts["bold"], anchor="ra")
    draw.text((left_x, y + 18), fix_arabic_text(f"التاريخ والوقت: {inv_date}"), fill=palette["text"], font=fonts["body"], anchor="la")

    draw.text((right_x, y + 52), fix_arabic_text(f"{party_label} {cust_name}"), fill=palette["text"], font=fonts["bold"], anchor="ra")
    phone_or_seller = f"رقم الهاتف: {cust_phone}" + (f"   |   المسؤول: {seller_name}" if seller_name else "")
    draw.text((left_x, y + 52), fix_arabic_text(phone_or_seller), fill=palette["muted"], font=fonts["body"], anchor="la")

    y += 105
    price_col_title = "سعر الشراء / التكلفة" if is_supp_doc else "القيمة / السعر"
    table_left = 36
    table_right = width - 36
    total_table_w = table_right - table_left
    sell_p = _clean_num_val(invoice_data.get("sell_price") if invoice_data.get("sell_price") is not None else invoice_data.get("total_amount", 0.0))

    if len(devices_list) == 1:
        dev = devices_list[0]
        dev_id = dev.get("id") or dev.get("device_id") or "-"
        category = str(dev.get("category") or "").strip()
        model = str(dev.get("model") or "").strip()
        dev_full_name = f"{category} {model}".strip() or "جهاز غير محدد"
        
        storage = str(dev.get("storage") or "-").replace("GB", "").strip() or "-"
        ram = str(dev.get("ram") or "").replace("GB", "").strip()
        ram_txt = f" / {ram}GB RAM" if ram and ram != "لا يوجد" and ram != "-" else ""
        
        bat_val = dev.get("battery_health") or dev.get("battery") or 0
        try:
            bat_num = int(bat_val)
            bat_txt = f"{bat_num}%" if bat_num > 0 else "-"
        except Exception:
            bat_txt = str(bat_val) if bat_val else "-"

        cond = str(dev.get("device_condition") or "مستعمل").strip()
        has_box_val = dev.get("has_box")
        box_txt = "بعلبة أصلية 📦" if has_box_val and str(has_box_val).lower() not in ("false", "0", "بدون") else "بدون علبة"
        imei = str(dev.get("imei_serial") or "-").strip()
        color = str(dev.get("color") or "أسود").strip()
        if not color or color == "بدون":
            color = "أسود"
        has_tax = bool(dev.get("has_tax"))
        tax_txt = "شامل الضريبة 🏛️" if has_tax else "بدون ضريبة"
        accessories = str(dev.get("accessories") or "").strip()

        if is_supp_doc:
            row_price = _clean_num_val(dev.get("buy_price") if dev.get("buy_price") is not None else sell_p)
        else:
            row_price = _clean_num_val(dev.get("sell_price") if dev.get("sell_price") is not None else sell_p)

        card_h = 168 if accessories and accessories not in ("بدون", "-") else 140
        draw.rectangle([(table_left, y), (table_right, y + card_h)], fill="#ffffff", outline=palette["primary"], width=2)
        
        draw.rectangle([(table_left, y), (table_right, y + 36)], fill=palette["header_bg"], outline=palette["border"], width=1)
        draw.text((table_right - 14, y + 18), fix_arabic_text(f"📱 بيانات الجهاز: {dev_full_name}  (كود: #{dev_id})"), fill=palette["primary"], font=fonts["bold"], anchor="ra")
        draw.text((table_left + 14, y + 18), fix_arabic_text(f"{price_col_title}: {fmt_money(row_price)}"), fill=palette["secondary"], font=fonts["bold"], anchor="la")

        y_imei = y + 42
        draw.rectangle([(table_left + 10, y_imei), (table_right - 10, y_imei + 32)], fill=palette["accent_box"], outline=palette["border"], width=1)
        draw.text((table_right - 20, y_imei + 16), fix_arabic_text("السيريال الكامل المعتمد (IMEI):"), fill=palette["text"], font=fonts["bold"], anchor="ra")
        draw.text((table_left + 24, y_imei + 16), imei, fill=palette["primary"], font=fonts["bold"], anchor="la")

        y_badges = y_imei + 38
        b_w = (total_table_w - 30) // 3
        badge_row1 = [
            (f"💾 السعة: {storage} GB{ram_txt}", 0),
            (f"🔋 صحة البطارية: {bat_txt}", 1),
            (f"🎨 اللون: {color}", 2),
        ]
        for b_text, col_idx in badge_row1:
            bx_r = table_right - 10 - (col_idx * b_w)
            bx_l = bx_r - b_w + 6
            draw.rectangle([(bx_l, y_badges), (bx_r, y_badges + 26)], fill="#f8fafc", outline=palette["border"], width=1)
            draw.text((bx_r - 8, y_badges + 13), fix_arabic_text(b_text), fill=palette["text"], font=fonts["small"], anchor="ra")

        y_badges2 = y_badges + 28
        badge_row2 = [
            (f"🏷️ الحالة: {cond}", 0),
            (f"📦 العلبة: {box_txt}", 1),
            (f"🏛️ الضريبة: {tax_txt}", 2),
        ]
        for b_text, col_idx in badge_row2:
            bx_r = table_right - 10 - (col_idx * b_w)
            bx_l = bx_r - b_w + 6
            draw.rectangle([(bx_l, y_badges2), (bx_r, y_badges2 + 26)], fill="#f8fafc", outline=palette["border"], width=1)
            draw.text((bx_r - 8, y_badges2 + 13), fix_arabic_text(b_text), fill=palette["text"], font=fonts["small"], anchor="ra")

        if accessories and accessories not in ("بدون", "-"):
            y_acc = y_badges2 + 28
            draw.rectangle([(table_left + 10, y_acc), (table_right - 10, y_acc + 24)], fill="#f1f5f9", outline=palette["border"], width=1)
            draw.text((table_right - 18, y_acc + 12), fix_arabic_text(f"🎧 الملحقات والإكسسوارات المرفقة: {accessories}"), fill=palette["muted"], font=fonts["small"], anchor="ra")

        y += card_h + 8

    else:
        price_col_w = int(total_table_w * 0.16)
        cond_col_w = int(total_table_w * 0.20)
        specs_col_w = int(total_table_w * 0.20)
        imei_col_w = int(total_table_w * 0.24)
        model_col_w = total_table_w - (price_col_w + cond_col_w + specs_col_w + imei_col_w)

        headers = [
            (price_col_title, price_col_w),
            ("الحالة واللون والعلبة", cond_col_w),
            ("المواصفات (سعة/رام/بطارية)", specs_col_w),
            ("السيريال IMEI", imei_col_w),
            ("كود وموديل الجهاز", model_col_w)
        ]

        curr_x = table_right
        for head_text, w in reversed(headers):
            draw.rectangle([(curr_x - w, y), (curr_x, y + 36)], fill=palette["table_hdr"], outline=palette["border"], width=1)
            draw.text((curr_x - w // 2, y + 18), fix_arabic_text(head_text), fill=palette["table_hdr_text"], font=fonts["bold"], anchor="mm")
            curr_x -= w

        y += 36

        for d_idx, dev in enumerate(devices_list):
            dev_id = dev.get("id") or dev.get("device_id") or "-"
            category = str(dev.get("category") or "").strip()
            model = str(dev.get("model") or "").strip()
            dev_full_name = f"{category} {model}".strip() or "جهاز غير محدد"
            dev_title_txt = f"{dev_full_name} (#{dev_id})"

            storage = str(dev.get("storage") or "-").replace("GB", "").strip() or "-"
            ram = str(dev.get("ram") or "").replace("GB", "").strip()
            ram_txt = f" / {ram}GB" if ram and ram != "لا يوجد" and ram != "-" else ""
            
            bat_val = dev.get("battery_health") or dev.get("battery") or 0
            try:
                bat_num = int(bat_val)
                bat_txt = f"{bat_num}%" if bat_num > 0 else "-"
            except Exception:
                bat_txt = str(bat_val) if bat_val else "-"

            cond = str(dev.get("device_condition") or "مستعمل").strip()
            has_box_val = dev.get("has_box")
            box_txt = "بعلبة 📦" if has_box_val and str(has_box_val).lower() not in ("false", "0", "بدون") else "بدون علبة"
            imei = str(dev.get("imei_serial") or "-").strip()
            color = str(dev.get("color") or "أسود").strip()
            if not color or color == "بدون":
                color = "أسود"

            if is_supp_doc:
                row_price = _clean_num_val(dev.get("buy_price") if dev.get("buy_price") is not None else sell_p)
            else:
                row_price = _clean_num_val(dev.get("sell_price") if dev.get("sell_price") is not None else sell_p)

            row_h = 36
            row_bg = "#ffffff" if d_idx % 2 == 0 else "#f8fafc"

            cell_x_model = table_right
            draw.rectangle([(cell_x_model - model_col_w, y), (cell_x_model, y + row_h)], fill=row_bg, outline=palette["border"], width=1)
            draw.text((cell_x_model - 10, y + 18), fix_arabic_text(dev_title_txt), fill=palette["primary"], font=fonts["bold"], anchor="ra")

            cell_x_imei = cell_x_model - model_col_w
            draw.rectangle([(cell_x_imei - imei_col_w, y), (cell_x_imei, y + row_h)], fill=row_bg, outline=palette["border"], width=1)
            draw.text((cell_x_imei - imei_col_w // 2, y + 18), imei, fill=palette["text"], font=fonts["bold"], anchor="mm")

            cell_x_specs = cell_x_imei - imei_col_w
            specs_txt = f"{storage}GB{ram_txt}  (🔋{bat_txt})"
            draw.rectangle([(cell_x_specs - specs_col_w, y), (cell_x_specs, y + row_h)], fill=row_bg, outline=palette["border"], width=1)
            draw.text((cell_x_specs - specs_col_w // 2, y + 18), fix_arabic_text(specs_txt), fill=palette["secondary"], font=fonts["small"], anchor="mm")

            cell_x_cond = cell_x_specs - specs_col_w
            cond_summary = f"{cond} | {color} | {box_txt}"
            draw.rectangle([(cell_x_cond - cond_col_w, y), (cell_x_cond, y + row_h)], fill=row_bg, outline=palette["border"], width=1)
            draw.text((cell_x_cond - cond_col_w // 2, y + 18), fix_arabic_text(cond_summary), fill=palette["muted"], font=fonts["small"], anchor="mm")

            cell_x_price = cell_x_cond - cond_col_w
            draw.rectangle([(table_left, y), (cell_x_price, y + row_h)], fill=row_bg, outline=palette["border"], width=1)
            draw.text((table_left + price_col_w // 2, y + 18), fix_arabic_text(fmt_money(row_price)), fill=palette["text"], font=fonts["bold"], anchor="mm")

            y += row_h

    # سجل الدفعات (إن وجد)
    if payments_list:
        y += 16
        draw.text((right_x, y), fix_arabic_text("سجل الدفعات والتحصيلات المسجلة:"), fill=palette["primary"], font=fonts["section"], anchor="ra")
        y += 26
        p_headers = ["المسؤول", "تاريخ الدفعة", "المبلغ المسدد", "م"]
        p_widths = [240, 260, 240, 88]
        curr_x = width - 36
        for idx, ph in enumerate(p_headers):
            w = p_widths[idx]
            draw.rectangle([(curr_x - w, y), (curr_x, y + 30)], fill=palette["header_bg"], outline=palette["border"], width=1)
            draw.text((curr_x - w // 2, y + 15), fix_arabic_text(ph), fill=palette["primary"], font=fonts["bold"], anchor="mm")
            curr_x -= w
        y += 30
        for p_i, p_row in enumerate(payments_list[:8], start=1):
            p_amt = fmt_money(p_row.get("payment_amount", 0))
            p_date = str(p_row.get("payment_date_formatted") or p_row.get("date") or "-")
            p_user = str(p_row.get("receiver_name") or p_row.get("payer_name") or p_row.get("user_name") or "-")
            p_vals = [p_user, p_date, p_amt, str(p_i)]
            curr_x = width - 36
            for idx, pv in enumerate(p_vals):
                w = p_widths[idx]
                draw.rectangle([(curr_x - w, y), (curr_x, y + 28)], fill="#ffffff", outline=palette["border"], width=1)
                draw.text((curr_x - w // 2, y + 14), fix_arabic_text(pv), fill=palette["text"], font=fonts["small"], anchor="mm")
                curr_x -= w
            y += 28

    # الملخص المالي
    y += 22
    orig_p = _clean_num_val(invoice_data.get("original_price", sell_p))
    disc = _clean_num_val(invoice_data.get("discount", 0.0))
    paid = _clean_num_val(invoice_data.get("cash_received") if invoice_data.get("cash_received") is not None else invoice_data.get("paid_amount", 0.0))
    rem = _clean_num_val(invoice_data.get("remaining_balance") if invoice_data.get("remaining_balance") is not None else invoice_data.get("remaining_amount", 0.0))
    supp_credit = _clean_num_val(invoice_data.get("supplier_credit", 0.0))

    fin_box_height = 175 if supp_credit > 0 else 145
    fin_box_top = y
    fin_box_bottom = y + fin_box_height
    draw.rectangle([(width - 420, fin_box_top), (width - 36, fin_box_bottom)], fill=palette["accent_box"], outline=palette["border"], width=2)

    fy = fin_box_top + 18
    if disc > 0 and not is_supp_doc:
        draw.text((width - 50, fy), fix_arabic_text(f"السعر قبل الخصم: {fmt_money(orig_p)}   |   الخصم: {fmt_money(disc)}"), fill=palette["muted"], font=fonts["small"], anchor="ra")
        fy += 26

    tot_label = "إجمالي فاتورة المشتريات:" if is_supp_doc else "إجمالي المبلغ المطلوب:"
    paid_label = "إجمالي المسدد للمورد:" if is_supp_doc else "إجمالي المدفوع نقداً:"
    draw.text((width - 50, fy), fix_arabic_text(f"{tot_label}  {fmt_money(sell_p)}"), fill=palette["text"], font=fonts["bold"], anchor="ra")
    fy += 30
    draw.text((width - 50, fy), fix_arabic_text(f"{paid_label}  {fmt_money(paid)}"), fill=palette["primary"], font=fonts["bold"], anchor="ra")
    fy += 30
    if supp_credit > 0:
        draw.text((width - 50, fy), fix_arabic_text(f"🌟 رصيد دائن لنا لدى المورد:  {fmt_money(supp_credit)}"), fill="#16a34a", font=fonts["bold"], anchor="ra")
        fy += 28
    if is_supp_doc:
        rem_label = "المتبقي للمورد (الآجل):" if rem > 0 else "المتبقي للمورد (خالص بالكامل):"
    else:
        rem_label = "المتبقي (المديونية الآجلة):" if rem > 0 else "المتبقي (خالص بالكامل):"
    draw.text((width - 50, fy), fix_arabic_text(f"{rem_label}  {fmt_money(rem)}"), fill=palette["secondary"] if rem > 0 else palette["primary"], font=fonts["section"], anchor="ra")

    terms_box_right = width - 435
    draw.rectangle([(36, fin_box_top), (terms_box_right, fin_box_bottom)], fill="#ffffff", outline=palette["border"], width=1)
    draw.text((terms_box_right - 15, fin_box_top + 16), fix_arabic_text("الشروط والملاحظات المعتمدة:"), fill=palette["primary"], font=fonts["bold"], anchor="ra")

    if is_supp_doc:
        default_terms_text = (
            "1. استلام ومطابقة البضاعة حسب المواصفات المتفق عليها.\n"
            "2. أرقام السيريال IMEI معتمدة ومسجلة بدفاتر النظام.\n"
            "3. أي رصيد دائن يسوى في الدفعات أو يسترد نقداً."
        )
    else:
        default_terms_text = (
            "1. البضاعة المباعة تخضع للمراجعة والضمان المتفق عليه.\n"
            "2. الضمان لا يشمل الكسر أو السوائل أو سوء الاستخدام.\n"
            "3. يرجى الاحتفاظ بالفاتورة لمراجعة المحل عند الحاجة."
        )

    custom_terms = invoice_data.get("custom_terms", default_terms_text)
    if supp_credit > 0:
        custom_terms = f"ملاحظة هامة: يوجد رصيد دائن مستحق لنا لدى المورد بقيمة {fmt_money(supp_credit)} على هذه الفاتورة.\n" + custom_terms
    sale_notes = (invoice_data.get("sale_notes") or invoice_data.get("notes") or "").strip()
    if sale_notes and sale_notes not in custom_terms:
        custom_terms = f"ملاحظة: {sale_notes}\n" + custom_terms

    ty = fin_box_top + 44
    for line in custom_terms.split("\n")[:4]:
        if line.strip():
            draw.text((terms_box_right - 15, ty), fix_arabic_text(line.strip()), fill=palette["text"], font=fonts["small"], anchor="ra")
            ty += 23

    # خفض موضع الباركود والـ QR للأسفل مع هوامش مريحة وقراءة فورية بالسكانر
    bc_area_top = fin_box_bottom + 16
    qr_pasted = False
    if HAS_QR:
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=3,
                border=1,
            )
            qr_payload = f"{inv_code}|{cust_name}|{sell_p:.2f}|{inv_date}"
            qr.add_data(qr_payload)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
            qr_w, qr_h = 72, 72
            qr_img = qr_img.resize((qr_w, qr_h), Image.Resampling.LANCZOS)
            
            qr_x = 48
            qr_y = bc_area_top + 4
            img.paste(qr_img, (qr_x, qr_y))
            draw.rectangle([(qr_x, qr_y), (qr_x + qr_w, qr_y + qr_h)], outline=palette["border"], width=1)
            qr_pasted = True
        except Exception:
            qr_pasted = False

    bc_w, bc_h = (220, 50) if qr_pasted else (280, 50)
    bc_x = 138 if qr_pasted else 48
    bc_y = bc_area_top + (15 if qr_pasted else 8)
    draw.rectangle([(bc_x, bc_y), (bc_x + bc_w, bc_y + bc_h)], fill="#ffffff", outline=palette["border"], width=1)
    curr_bx = bc_x + 12
    pattern = [2, 1, 3, 1, 2, 2, 1, 3, 2, 1, 1, 2, 3, 1, 2, 1, 3, 2, 1, 2, 1, 3, 1, 2, 2, 1, 3, 1, 2]
    for b_w in pattern:
        if curr_bx + b_w > bc_x + bc_w - 12:
            break
        draw.rectangle([(curr_bx, bc_y + 4), (curr_bx + b_w, bc_y + bc_h - 18)], fill=palette["text"])
        curr_bx += b_w + 2
    draw.text((bc_x + bc_w // 2, bc_y + bc_h - 8), f"*{inv_code}*", fill=palette["muted"], font=fonts["small"], anchor="mm")

    # التوقيعات والتذييل
    footer_y = max(bc_area_top + 88, height - 105)
    draw.line([(45, footer_y), (width - 45, footer_y)], fill=palette["border"], width=1)
    sig_label = "توقيع المورد / المستلم" if is_supp_doc else "توقيع العميل / المستلم"
    draw.text((170, footer_y + 22), fix_arabic_text(sig_label), fill=palette["text"], font=fonts["bold"], anchor="ma")
    draw.text((width - 170, footer_y + 22), fix_arabic_text("ختم وتوقيع محل هشام كيوان"), fill=palette["text"], font=fonts["bold"], anchor="ma")

    draw.rectangle([(24, height - 52), (width - 24, height - 24)], fill=palette["table_hdr"])
    draw.text((width // 2, height - 38), fix_arabic_text("شكراً لثقتكم بمحل هشام كيوان - نسعد بخدمتكم دائماً"), fill="#ffffff", font=fonts["bold"], anchor="mm")

    page_suffix = f"_p{invoice_data.get('page_num', 1)}" if invoice_data.get("total_pages", 1) > 1 else ""
    safe_id = str(sale_id).replace("/", "_").replace("\\", "_").replace("#", "")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.abspath(os.path.join(temp_dir, f"temp_invoice_{safe_id}{page_suffix}_{timestamp}.png"))
    try:
        img.save(temp_path)
        return temp_path
    except Exception:
        fallback_path = os.path.abspath(os.path.join("invoices", f"temp_invoice_{safe_id}{page_suffix}.png"))
        os.makedirs("invoices", exist_ok=True)
        img.save(fallback_path)
        return fallback_path


def generate_invoice_pages(invoice_data):
    """
    توليد صفحات الفاتورة (صفحة واحدة أو عدة صفحات متسلسلة إذا تجاوزت الأجهزة 8 أجهزة).
    تقسم الفواتير الطويلة وترقمها بوضوح (صفحة 1 من 3، صفحة 2 من 3...).
    """
    devices_list = invoice_data.get("devices_list") or []
    if not devices_list and invoice_data.get("device"):
        devices_list = [invoice_data["device"]]

    # إذا كانت القائمة 8 أجهزة أو أقل، تطبع في صفحة واحدة كاملة
    if len(devices_list) <= 8:
        inv_copy = dict(invoice_data)
        inv_copy["page_num"] = 1
        inv_copy["total_pages"] = 1
        return [generate_invoice_image(inv_copy)]

    # تجزئة الأجهزة إلى صفحات متتالية (8 أجهزة لكل صفحة)
    chunk_size = 8
    chunks = [devices_list[i:i + chunk_size] for i in range(0, len(devices_list), chunk_size)]
    total_pages = len(chunks)
    generated_pages = []

    for idx, chunk in enumerate(chunks, start=1):
        page_data = dict(invoice_data)
        page_data["devices_list"] = chunk
        page_data["page_num"] = idx
        page_data["total_pages"] = total_pages
        # الصفحة الأخيرة فقط تحتفظ بسجل الدفعات والملاحظات الختامية إذا تعددت الصفحات
        if idx < total_pages:
            page_data["payments_list"] = []
        p_path = generate_invoice_image(page_data)
        generated_pages.append(p_path)

    return generated_pages


def trigger_system_print_or_open(file_path, mode="open"):
    if not file_path or not os.path.exists(file_path):
        raise FileNotFoundError("ملف الفاتورة غير موجود!")

    if hasattr(os, "startfile"):
        if mode == "print":
            try:
                os.startfile(file_path, "print")
                return True
            except Exception:
                os.startfile(file_path)
                return True
        else:
            os.startfile(file_path)
            return True
    return False
