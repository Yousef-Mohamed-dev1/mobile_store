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


def _load_fonts():
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
                "title": ImageFont.truetype(bold_path, 28),
                "subtitle": ImageFont.truetype(bold_path, 18),
                "section": ImageFont.truetype(bold_path, 16),
                "bold": ImageFont.truetype(bold_path, 14),
                "body": ImageFont.truetype(reg_path, 14),
                "small": ImageFont.truetype(reg_path, 12),
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
    """
    if not os.path.exists("invoices"):
        try:
            os.makedirs("invoices", exist_ok=True)
        except Exception:
            pass

    style_name = invoice_data.get("print_style", "color")
    palette = _get_palette(style_name)
    fonts = _load_fonts()

    devices_list = invoice_data.get("devices_list") or []
    if not devices_list and invoice_data.get("device"):
        devices_list = [invoice_data["device"]]

    payments_list = invoice_data.get("payments_list") or []
    extra_rows_height = max(0, (len(devices_list) - 1) * 38) + (len(payments_list) * 30 if payments_list else 0)

    width = 900
    height = max(1180, 1120 + extra_rows_height)
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
    if doc_type == "CUSTOMER_DEBT":
        sub_label = "بيان مديونية وتحصيل عميل (الخرج)"
    elif doc_type == "SUPPLIER_DEBT":
        sub_label = "كشف حساب وفاتورة مديونية مورد"
    else:
        sub_label = "فاتورة بيع وضمان جهاز"

    draw.text((width // 2, 68), fix_arabic_text("مركز هشام كيوان لإدارة وتجارة الهواتف الذكية"), fill=palette["primary"], font=fonts["title"], anchor="mm")
    draw.text((width // 2, 112), fix_arabic_text(sub_label), fill=palette["secondary"], font=fonts["subtitle"], anchor="mm")

    # بيانات المستند والعميل / المورد
    sale_id = invoice_data.get("sale_id", "-")
    cust_name = invoice_data.get("customer_name") or "عميل نقدي"
    cust_phone = invoice_data.get("customer_phone") or "غير مسجل"
    inv_date = invoice_data.get("date_str") or datetime.now().strftime("%Y-%m-%d %H:%M")
    seller_name = invoice_data.get("seller_name") or ""

    y = 162
    draw.rectangle([(36, y), (width - 36, y + 92)], fill="#ffffff", outline=palette["border"], width=1)

    right_x = width - 52
    left_x = 52

    inv_code = invoice_data.get("invoice_code") or (f"INV-{doc_type}-{sale_id}" if sale_id != "-" else f"INV-{doc_type}")
    draw.text((right_x, y + 18), fix_arabic_text(f"كود الفاتورة: {inv_code}  (#{sale_id})"), fill=palette["primary"], font=fonts["bold"], anchor="ra")
    draw.text((left_x, y + 18), fix_arabic_text(f"التاريخ والوقت: {inv_date}"), fill=palette["text"], font=fonts["body"], anchor="la")

    draw.text((right_x, y + 52), fix_arabic_text(f"العميل / الجهة: {cust_name}"), fill=palette["text"], font=fonts["bold"], anchor="ra")
    phone_or_seller = f"رقم الهاتف: {cust_phone}" + (f"   |   المسؤول: {seller_name}" if seller_name else "")
    draw.text((left_x, y + 52), fix_arabic_text(phone_or_seller), fill=palette["muted"], font=fonts["body"], anchor="la")

    # جدول الأجهزة
    y += 110
    headers = ["القيمة / السعر", "السيريال (IMEI)", "الحالة / العلبة", "المساحة / الرام", "الماركة والموديل"]
    col_widths = [145, 205, 145, 145, 188]  # مجموعها = 828 (من 36 إلى width-36)

    curr_x = width - 36
    for idx, head in enumerate(headers):
        w = col_widths[idx]
        draw.rectangle([(curr_x - w, y), (curr_x, y + 36)], fill=palette["table_hdr"], outline=palette["border"], width=1)
        draw.text((curr_x - w // 2, y + 18), fix_arabic_text(head), fill=palette["table_hdr_text"], font=fonts["bold"], anchor="mm")
        curr_x -= w

    y += 36
    sell_p = _clean_num_val(invoice_data.get("sell_price", 0.0))

    for d_idx, dev in enumerate(devices_list):
        category = dev.get("category", "")
        model = dev.get("model", "")
        storage = str(dev.get("storage") or "-").replace("GB", "").strip() or "-"
        ram = str(dev.get("ram") or "-").replace("GB", "").strip() or "-"
        cond = dev.get("device_condition") or "مستعمل"
        box_txt = "بعلبة" if dev.get("has_box", True) else "بدون علبة"
        imei = str(dev.get("imei_serial") or "-")
        row_price = _clean_num_val(dev.get("buy_price") if doc_type == "SUPPLIER_DEBT" and dev.get("buy_price") is not None else sell_p)

        row_vals = [
            fmt_money(row_price),
            imei,
            f"{cond} - {box_txt}",
            f"{storage} / {ram}",
            f"{category} {model}".strip() or "-"
        ]

        row_bg = "#ffffff" if d_idx % 2 == 0 else "#f8fafc"
        curr_x = width - 36
        for idx, val in enumerate(row_vals):
            w = col_widths[idx]
            draw.rectangle([(curr_x - w, y), (curr_x, y + 38)], fill=row_bg, outline=palette["border"], width=1)
            draw.text((curr_x - w // 2, y + 19), fix_arabic_text(val), fill=palette["text"], font=fonts["body"], anchor="mm")
            curr_x -= w
        y += 38

    # سجل الدفعات (إن وجد في الخرج أو مديونية المورد)
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
            p_user = str(p_row.get("receiver_name") or p_row.get("user_name") or "-")
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
    paid = _clean_num_val(invoice_data.get("cash_received", 0.0))
    rem = _clean_num_val(invoice_data.get("remaining_balance", 0.0))

    fin_box_top = y
    fin_box_bottom = y + 145
    draw.rectangle([(width - 420, fin_box_top), (width - 36, fin_box_bottom)], fill=palette["accent_box"], outline=palette["border"], width=2)

    fy = fin_box_top + 18
    if disc > 0:
        draw.text((width - 50, fy), fix_arabic_text(f"السعر قبل الخصم: {fmt_money(orig_p)}   |   الخصم: {fmt_money(disc)}"), fill=palette["muted"], font=fonts["small"], anchor="ra")
        fy += 26

    draw.text((width - 50, fy), fix_arabic_text(f"إجمالي المبلغ المطلوب:  {fmt_money(sell_p)}"), fill=palette["text"], font=fonts["bold"], anchor="ra")
    fy += 32
    draw.text((width - 50, fy), fix_arabic_text(f"إجمالي المدفوع نقداً:  {fmt_money(paid)}"), fill=palette["primary"], font=fonts["bold"], anchor="ra")
    fy += 32
    rem_label = "المتبقي (المديونية الآجلة):" if rem > 0 else "المتبقي (خالص بالكامل):"
    draw.text((width - 50, fy), fix_arabic_text(f"{rem_label}  {fmt_money(rem)}"), fill=palette["secondary"] if rem > 0 else palette["primary"], font=fonts["section"], anchor="ra")

    # الشروط والملاحظات على اليسار بمحاذاة الملخص المالي
    terms_box_right = width - 435
    draw.rectangle([(36, fin_box_top), (terms_box_right, fin_box_bottom)], fill="#ffffff", outline=palette["border"], width=1)
    draw.text((terms_box_right - 15, fin_box_top + 16), fix_arabic_text("الشروط والملاحظات المعتمدة:"), fill=palette["primary"], font=fonts["bold"], anchor="ra")

    custom_terms = invoice_data.get(
        "custom_terms",
        "1. البضاعة المباعة تخضع للمراجعة والضمان المتفق عليه.\n"
        "2. الضمان لا يشمل الكسر أو السوائل أو سوء الاستخدام.\n"
        "3. يرجى الاحتفاظ بالفاتورة لمراجعة المركز عند الحاجة."
    )
    sale_notes = (invoice_data.get("sale_notes") or "").strip()
    if sale_notes and sale_notes not in custom_terms:
        custom_terms = f"ملاحظة: {sale_notes}\n" + custom_terms

    ty = fin_box_top + 44
    for line in custom_terms.split("\n")[:4]:
        if line.strip():
            draw.text((terms_box_right - 15, ty), fix_arabic_text(line.strip()), fill=palette["text"], font=fonts["small"], anchor="ra")
            ty += 23

    # رسم كود QR والباركود للتحقق السريع بالسكانر وقارئ الكاميرا
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
            qr_w, qr_h = 74, 74
            qr_img = qr_img.resize((qr_w, qr_h), Image.Resampling.LANCZOS)
            
            qr_x = 48
            qr_y = fin_box_bottom - qr_h - 6
            img.paste(qr_img, (qr_x, qr_y))
            draw.rectangle([(qr_x, qr_y), (qr_x + qr_w, qr_y + qr_h)], outline=palette["border"], width=1)
            qr_pasted = True
        except Exception:
            qr_pasted = False

    bc_w, bc_h = (190, 44) if qr_pasted else (240, 44)
    bc_x = 130 if qr_pasted else 48
    bc_y = fin_box_bottom - bc_h - 8
    draw.rectangle([(bc_x, bc_y), (bc_x + bc_w, bc_y + bc_h)], fill="#ffffff", outline=palette["border"], width=1)
    curr_bx = bc_x + 8
    pattern = [2, 1, 3, 1, 2, 2, 1, 3, 2, 1, 1, 2, 3, 1, 2, 1, 3, 2, 1, 2, 1, 3, 1, 2, 2, 1, 3, 1, 2]
    for b_w in pattern:
        if curr_bx + b_w > bc_x + bc_w - 8:
            break
        draw.rectangle([(curr_bx, bc_y + 4), (curr_bx + b_w, bc_y + bc_h - 15)], fill=palette["text"])
        curr_bx += b_w + 2
    draw.text((bc_x + bc_w // 2, bc_y + bc_h - 7), f"*{inv_code}*", fill=palette["muted"], font=fonts["small"], anchor="mm")

    # التوقيعات والتذييل
    footer_y = height - 110
    draw.line([(45, footer_y), (width - 45, footer_y)], fill=palette["border"], width=1)
    draw.text((170, footer_y + 25), fix_arabic_text("توقيع العميل / المستلم"), fill=palette["text"], font=fonts["bold"], anchor="ma")
    draw.text((width - 170, footer_y + 25), fix_arabic_text("ختم وتوقيع إدارة المركز"), fill=palette["text"], font=fonts["bold"], anchor="ma")

    draw.rectangle([(24, height - 55), (width - 24, height - 24)], fill=palette["table_hdr"])
    draw.text((width // 2, height - 39), fix_arabic_text("شكراً لثقتكم بمركز هشام كيوان لإدارة الهواتف الذكية - نسعد بخدمتكم دائماً"), fill="#ffffff", font=fonts["bold"], anchor="mm")

    safe_id = str(sale_id).replace("/", "_").replace("\\", "_").replace("#", "")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = os.path.abspath(os.path.join("invoices", f"invoice_{safe_id}_{timestamp}.png"))
    try:
        img.save(archive_path)
        return archive_path
    except Exception:
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, f"temp_invoice_{safe_id}.png")
        img.save(file_path)
        return file_path


def trigger_system_print_or_open(file_path, mode="open"):
    """
    تشغيل الطباعة المباشرة أو فتح الفاتورة للمعاينة على نظام التشغيل بأمان.
    mode: 'print' لإرسالها للطابعة الافتراضية مباشرة، أو 'open' لفتح الصورة.
    """
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
