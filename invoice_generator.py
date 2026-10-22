# =================================================================================
# محرك طباعة ومعاينة الفواتير عالي الدقة - مركز هشام كيوان لإدارة الهواتف
# يدعم مقاسات A4/A5 القياسية، أنماط ألوان فاخرة، باركود و QR
# =================================================================================

import os
import tempfile
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# دعم معالجة النصوص العربية وعكس الاتجاه لمنع تشوه النصوص والأرقام
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

PAGE_WIDTH = 1240
PAGE_HEIGHT = 1754


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
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/tahomabd.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
        "/usr/share/fonts/truetype/kacst/KacstTitle.ttf",
        "/usr/share/fonts/truetype/kacst/KacstOffice.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "arialbd.ttf",
        "arial.ttf"
    ]
    font_candidates_reg = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/kacst/KacstBook.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "arial.ttf"
    ]

    bold_path = next((p for p in font_candidates_bold if os.path.exists(p)), None)
    reg_path = next((p for p in font_candidates_reg if os.path.exists(p)), None)
    effective_reg = reg_path or bold_path

    try:
        if bold_path:
            return {
                "banner": ImageFont.truetype(bold_path, int(46 * scale)),
                "huge": ImageFont.truetype(bold_path, int(36 * scale)),
                "title": ImageFont.truetype(bold_path, int(30 * scale)),
                "subtitle": ImageFont.truetype(bold_path, int(26 * scale)),
                "section": ImageFont.truetype(bold_path, int(23 * scale)),
                "bold": ImageFont.truetype(bold_path, int(21 * scale)),
                "body": ImageFont.truetype(effective_reg or bold_path, int(19 * scale)),
                "small": ImageFont.truetype(bold_path, int(16 * scale)),
                "tiny": ImageFont.truetype(effective_reg or bold_path, int(14 * scale)),
            }
    except Exception:
        pass

    default_f = ImageFont.load_default()
    return {
        "banner": default_f,
        "huge": default_f,
        "title": default_f,
        "subtitle": default_f,
        "section": default_f,
        "bold": default_f,
        "body": default_f,
        "small": default_f,
        "tiny": default_f,
    }


def _get_palette(style_name="color"):
    if style_name == "burgundy":
        return {
            "primary": "#881337",
            "secondary": "#be123c",
            "accent": "#9f1239",
            "header_bg": "#fff1f2",
            "table_hdr": "#881337",
            "table_hdr_text": "#ffffff",
            "card_bg": "#fff5f5",
            "accent_box": "#ffe4e6",
            "total_box": "#fff1f2",
            "border": "#9f1239",
            "border_light": "#fecdd3",
            "text": "#1e293b",
            "text_muted": "#475569",
            "danger": "#e11d48",
            "success": "#15803d",
            "gold": "#b45309"
        }
    elif style_name == "grayscale":
        return {
            "primary": "#0f172a",
            "secondary": "#334155",
            "accent": "#1e293b",
            "header_bg": "#f8fafc",
            "table_hdr": "#1e293b",
            "table_hdr_text": "#ffffff",
            "card_bg": "#f8fafc",
            "accent_box": "#f1f5f9",
            "total_box": "#f8fafc",
            "border": "#0f172a",
            "border_light": "#cbd5e1",
            "text": "#0f172a",
            "text_muted": "#334155",
            "danger": "#0f172a",
            "success": "#0f172a",
            "gold": "#334155"
        }
    else:
        return {
            "primary": "#0f2b5c",
            "secondary": "#1d4ed8",
            "accent": "#0284c7",
            "header_bg": "#f0f7ff",
            "table_hdr": "#0f2b5c",
            "table_hdr_text": "#ffffff",
            "card_bg": "#f8fafc",
            "accent_box": "#f0fdf4",
            "total_box": "#f0fdf4",
            "border": "#0f2b5c",
            "border_light": "#cbd5e1",
            "text": "#0f172a",
            "text_muted": "#334155",
            "danger": "#dc2626",
            "success": "#16a34a",
            "gold": "#b45309"
        }


def generate_invoice_image(invoice_data):
    if not os.path.exists("invoices"):
        try:
            os.makedirs("invoices", exist_ok=True)
        except Exception:
            pass

    style_name = invoice_data.get("print_style", "color")
    palette = _get_palette(style_name)
    fonts = _load_fonts(scale=1.0)

    width = PAGE_WIDTH
    height = PAGE_HEIGHT
    img = Image.new("RGB", (width, height), color="#ffffff")
    draw = ImageDraw.Draw(img)

    margin_x = 44
    content_width = width - (2 * margin_x)
    right_x = width - margin_x
    left_x = margin_x

    # 1. إطار الورقة الخارجي الملكي
    draw.rectangle([(14, 14), (width - 14, height - 14)], outline=palette["border"], width=3)
    draw.rectangle([(22, 22), (width - 22, height - 22)], outline=palette["border"], width=1)

    # 2. ترويسة المتجر والوثيقة الرسمية
    header_top = 34
    header_h = 138
    draw.rectangle([(margin_x, header_top), (right_x, header_top + header_h)], fill=palette["header_bg"], outline=palette["border"], width=2)

    if os.path.exists("logo.png"):
        try:
            logo = Image.open("logo.png").convert("RGBA")
            logo.thumbnail((110, 110), Image.Resampling.LANCZOS)
            img.paste(logo, (margin_x + 20, header_top + 14), logo)
        except Exception:
            pass

    doc_type = invoice_data.get("doc_type", "SALE")
    is_supp_doc = doc_type in ("SUPPLIER_INVOICE", "SUPPLIER_DEBT", "SUPPLIER_STATEMENT")
    is_archived = bool(invoice_data.get("is_archived"))

    if is_archived:
        sub_label = "فاتورة مؤرشفة وسجل تاريخي معتمد (خالص بالكامل 🗄️)"
    elif doc_type == "CUSTOMER_DEBT":
        sub_label = "بيان مديونية وحساب عميل معتمد"
    elif doc_type == "SUPPLIER_STATEMENT":
        sub_label = "كشف حساب مشتريات وسداد مورد بالفترة"
    elif is_supp_doc:
        sub_label = "فاتورة مشتريات وتوريد بضاعة معتمدة"
    else:
        sub_label = "فاتورة بيع وضمان رسمي معتمد للأجهزة الذكية"

    draw.text((width // 2, header_top + 38), fix_arabic_text("مركز هشام كيوان لإدارة الهواتف"), fill=palette["primary"], font=fonts["banner"], anchor="mm")
    draw.text((width // 2, header_top + 84), fix_arabic_text(sub_label), fill=palette["secondary"], font=fonts["subtitle"], anchor="mm")
    draw.text((width // 2, header_top + 116), fix_arabic_text("خدمة عملاء معتمدة  •  أجهزة أصلية ومفحوصة  •  ضمان صريح ومسجل بالنظام"), fill=palette["text_muted"], font=fonts["small"], anchor="mm")

    # 3. بطاقة بيانات الفاتورة
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
    inv_code = invoice_data.get("invoice_code") or (f"INV-{doc_type}-{sale_id}" if sale_id != "-" else f"INV-{doc_type}")

    page_n = invoice_data.get("page_num", 1)
    tot_p = invoice_data.get("total_pages", 1)

    card_y = header_top + header_h + 16
    card_h = 124
    draw.rectangle([(margin_x, card_y), (right_x, card_y + card_h)], fill="#ffffff", outline=palette["border"], width=1)
    draw.line([(margin_x + 12, card_y + 60), (right_x - 12, card_y + 60)], fill=palette["border_light"], width=1)

    draw.text((right_x - 20, card_y + 30), fix_arabic_text(f"كود الفاتورة: {inv_code}  (#{sale_id})"), fill=palette["primary"], font=fonts["section"], anchor="ra")

    page_badge_txt = f"صفحة {page_n} من {tot_p}"
    draw.rectangle([(width // 2 - 110, card_y + 13), (width // 2 + 110, card_y + 47)], fill=palette["header_bg"], outline=palette["secondary"], width=1)
    draw.text((width // 2, card_y + 30), fix_arabic_text(page_badge_txt), fill=palette["secondary"], font=fonts["bold"], anchor="mm")

    draw.text((left_x + 20, card_y + 30), fix_arabic_text(f"التاريخ: {inv_date}"), fill=palette["text"], font=fonts["section"], anchor="la")

    draw.text((right_x - 20, card_y + 92), fix_arabic_text(f"{party_label} {cust_name}"), fill=palette["text"], font=fonts["huge"], anchor="ra")
    phone_seller_txt = f"الهاتف: {cust_phone}" + (f"  |  المسؤول: {seller_name}" if seller_name else "")
    draw.text((left_x + 20, card_y + 92), fix_arabic_text(phone_seller_txt), fill=palette["text_muted"], font=fonts["bold"], anchor="la")

    # 4. جدول أو بطاقة الأجهزة المشمولة
    devices_list = invoice_data.get("devices_list") or []
    if not devices_list and invoice_data.get("device"):
        devices_list = [invoice_data["device"]]

    payments_list = invoice_data.get("payments_list") or []
    is_final_page = (page_n == tot_p)

    price_col_title = "سعر الشراء / التكلفة" if is_supp_doc else "القيمة / السعر"
    sell_p = _clean_num_val(invoice_data.get("sell_price") if invoice_data.get("sell_price") is not None else invoice_data.get("total_amount", 0.0))

    y = card_y + card_h + 20

    if len(devices_list) == 1 and tot_p == 1:
        dev = devices_list[0]
        dev_id = dev.get("id") or dev.get("device_id") or "-"
        category = str(dev.get("category") or "").strip()
        model = str(dev.get("model") or "").strip()
        dev_full_name = f"{category} {model}".strip() or "جهاز غير محدد"

        storage = str(dev.get("storage") or "-").replace("GB", "").strip() or "-"
        ram = str(dev.get("ram") or "").replace("GB", "").strip()
        ram_txt = f" / {ram}GB RAM" if ram and ram not in ("لا يوجد", "-") else ""

        bat_val = dev.get("battery_health") or dev.get("battery") or 0
        try:
            bat_num = int(bat_val)
            bat_txt = f"{bat_num}%" if bat_num > 0 else "-"
        except Exception:
            bat_txt = str(bat_val) if bat_val else "-"

        cond = str(dev.get("device_condition") or "مستعمل").strip()
        has_box_val = dev.get("has_box")
        box_txt = "علبة أصلية 📦" if has_box_val and str(has_box_val).lower() not in ("false", "0", "بدون") else "بدون علبة"
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

        card_h_single = 350 if accessories and accessories not in ("بدون", "-") else 300
        draw.rectangle([(margin_x, y), (right_x, y + card_h_single)], fill="#ffffff", outline=palette["primary"], width=2)

        draw.rectangle([(margin_x, y), (right_x, y + 66)], fill=palette["header_bg"], outline=palette["border"], width=1)
        draw.text((right_x - 18, y + 33), fix_arabic_text(f"📱 نوع وموديل الجهاز: {dev_full_name}  (كود: #{dev_id})"), fill=palette["primary"], font=fonts["section"], anchor="ra")
        draw.text((left_x + 18, y + 33), fix_arabic_text(f"{price_col_title}: {fmt_money(row_price)}"), fill=palette["secondary"], font=fonts["huge"], anchor="la")

        y_imei = y + 76
        draw.rectangle([(margin_x + 14, y_imei), (right_x - 14, y_imei + 56)], fill=palette["card_bg"], outline=palette["border_light"], width=1)
        draw.text((right_x - 24, y_imei + 28), fix_arabic_text("السيريال المعتمد (IMEI):"), fill=palette["text"], font=fonts["bold"], anchor="ra")
        draw.text((left_x + 24, y_imei + 28), imei, fill=palette["primary"], font=fonts["huge"], anchor="la")

        y_badges = y_imei + 66
        badge_w = (content_width - 40) // 3
        badge_row1 = [
            (f"💾 السعة: {storage} GB{ram_txt}", 0),
            (f"🔋 صحة البطارية: {bat_txt}", 1),
            (f"🎨 اللون: {color}", 2),
        ]
        for b_text, col_idx in badge_row1:
            bx_r = right_x - 14 - (col_idx * badge_w)
            bx_l = bx_r - badge_w + 8
            draw.rectangle([(bx_l, y_badges), (bx_r, y_badges + 44)], fill="#f8fafc", outline=palette["border_light"], width=1)
            draw.text((bx_r - 12, y_badges + 22), fix_arabic_text(b_text), fill=palette["text"], font=fonts["bold"], anchor="ra")

        y_badges2 = y_badges + 52
        badge_row2 = [
            (f"🏷️ الحالة: {cond}", 0),
            (f"📦 العلبة: {box_txt}", 1),
            (f"🏛️ الضريبة: {tax_txt}", 2),
        ]
        for b_text, col_idx in badge_row2:
            bx_r = right_x - 14 - (col_idx * badge_w)
            bx_l = bx_r - badge_w + 8
            draw.rectangle([(bx_l, y_badges2), (bx_r, y_badges2 + 44)], fill="#f8fafc", outline=palette["border_light"], width=1)
            draw.text((bx_r - 12, y_badges2 + 22), fix_arabic_text(b_text), fill=palette["text"], font=fonts["bold"], anchor="ra")

        if accessories and accessories not in ("بدون", "-"):
            y_acc = y_badges2 + 52
            draw.rectangle([(margin_x + 14, y_acc), (right_x - 14, y_acc + 42)], fill="#f1f5f9", outline=palette["border_light"], width=1)
            draw.text((right_x - 24, y_acc + 21), fix_arabic_text(f"🎧 الملحقات المرفقة: {accessories}"), fill=palette["text_muted"], font=fonts["bold"], anchor="ra")

        y += card_h_single + 24

    else:
        price_col_w = int(content_width * 0.16)
        cond_col_w = int(content_width * 0.17)
        specs_col_w = int(content_width * 0.19)
        imei_col_w = int(content_width * 0.22)
        model_col_w = content_width - (price_col_w + cond_col_w + specs_col_w + imei_col_w)

        headers = [
            (price_col_title, price_col_w),
            ("الحالة واللون والعلبة", cond_col_w),
            ("المواصفات (سعة/بطارية)", specs_col_w),
            ("السيريال IMEI", imei_col_w),
            ("كود وموديل الجهاز", model_col_w)
        ]

        hdr_h = 54
        curr_x = right_x
        for head_text, w in reversed(headers):
            draw.rectangle([(curr_x - w, y), (curr_x, y + hdr_h)], fill=palette["table_hdr"], outline=palette["border"], width=1)
            draw.text((curr_x - w // 2, y + hdr_h // 2), fix_arabic_text(head_text), fill=palette["table_hdr_text"], font=fonts["bold"], anchor="mm")
            curr_x -= w

        y += hdr_h

        row_h = 58
        for d_idx, dev in enumerate(devices_list):
            dev_id = dev.get("id") or dev.get("device_id") or "-"
            category = str(dev.get("category") or "").strip()
            model = str(dev.get("model") or "").strip()
            dev_full_name = f"{category} {model}".strip() or "جهاز غير محدد"
            dev_title_txt = f"{dev_full_name} (#{dev_id})"

            storage = str(dev.get("storage") or "-").replace("GB", "").strip() or "-"
            ram = str(dev.get("ram") or "").replace("GB", "").strip()
            ram_txt = f"/{ram}G" if ram and ram not in ("لا يوجد", "-") else ""

            bat_val = dev.get("battery_health") or dev.get("battery") or 0
            try:
                bat_num = int(bat_val)
                bat_txt = f"{bat_num}%" if bat_num > 0 else "-"
            except Exception:
                bat_txt = str(bat_val) if bat_val else "-"

            cond = str(dev.get("device_condition") or "مستعمل").strip()
            has_box_val = dev.get("has_box")
            box_txt = "علبة 📦" if has_box_val and str(has_box_val).lower() not in ("false", "0", "بدون") else "بدون علبة"
            imei = str(dev.get("imei_serial") or "-").strip()
            color = str(dev.get("color") or "أسود").strip()
            if not color or color == "بدون":
                color = "أسود"

            if is_supp_doc:
                row_price = _clean_num_val(dev.get("buy_price") if dev.get("buy_price") is not None else sell_p)
            else:
                row_price = _clean_num_val(dev.get("sell_price") if dev.get("sell_price") is not None else sell_p)

            row_bg = "#ffffff" if d_idx % 2 == 0 else "#f8fafc"

            cell_x_model = right_x
            draw.rectangle([(cell_x_model - model_col_w, y), (cell_x_model, y + row_h)], fill=row_bg, outline=palette["border_light"], width=1)
            draw.text((cell_x_model - 14, y + row_h // 2), fix_arabic_text(dev_title_txt), fill=palette["primary"], font=fonts["bold"], anchor="ra")

            cell_x_imei = cell_x_model - model_col_w
            draw.rectangle([(cell_x_imei - imei_col_w, y), (cell_x_imei, y + row_h)], fill=row_bg, outline=palette["border_light"], width=1)
            draw.text((cell_x_imei - imei_col_w // 2, y + row_h // 2), imei, fill=palette["text"], font=fonts["bold"], anchor="mm")

            cell_x_specs = cell_x_imei - imei_col_w
            specs_txt = f"{storage}GB{ram_txt}  (🔋{bat_txt})"
            draw.rectangle([(cell_x_specs - specs_col_w, y), (cell_x_specs, y + row_h)], fill=row_bg, outline=palette["border_light"], width=1)
            draw.text((cell_x_specs - specs_col_w // 2, y + row_h // 2), fix_arabic_text(specs_txt), fill=palette["secondary"], font=fonts["body"], anchor="mm")

            cell_x_cond = cell_x_specs - specs_col_w
            cond_summary = f"{cond} | {color} | {box_txt}"
            draw.rectangle([(cell_x_cond - cond_col_w, y), (cell_x_cond, y + row_h)], fill=row_bg, outline=palette["border_light"], width=1)
            draw.text((cell_x_cond - cond_col_w // 2, y + row_h // 2), fix_arabic_text(cond_summary), fill=palette["text_muted"], font=fonts["small"], anchor="mm")

            draw.rectangle([(left_x, y), (left_x + price_col_w, y + row_h)], fill=row_bg, outline=palette["border_light"], width=1)
            draw.text((left_x + price_col_w // 2, y + row_h // 2), fix_arabic_text(fmt_money(row_price)), fill=palette["text"], font=fonts["bold"], anchor="mm")

            y += row_h

        y += 20

    if not is_final_page:
        cont_y = min(y + 20, height - 230)
        draw.rectangle([(margin_x, cont_y), (right_x, cont_y + 80)], fill=palette["header_bg"], outline=palette["secondary"], width=2)
        draw.text((width // 2, cont_y + 40), fix_arabic_text(f"⬅️ بقية تفاصيل الفاتورة وملخص الحساب في الصفحة رقم {page_n + 1} من {tot_p}"), fill=palette["secondary"], font=fonts["huge"], anchor="mm")

    else:
        if payments_list:
            y += 8
            draw.text((right_x, y), fix_arabic_text("سجل الدفعات والتحصيلات المسجلة:"), fill=palette["primary"], font=fonts["section"], anchor="ra")
            y += 32
            p_headers = ["المسؤول المستلم", "تاريخ ووقت الدفعة", "المبلغ المسدد", "م"]
            p_widths = [int(content_width * 0.32), int(content_width * 0.34), int(content_width * 0.24), int(content_width * 0.10)]
            curr_x = right_x
            for idx, ph in enumerate(p_headers):
                w = p_widths[idx]
                draw.rectangle([(curr_x - w, y), (curr_x, y + 36)], fill=palette["header_bg"], outline=palette["border_light"], width=1)
                draw.text((curr_x - w // 2, y + 18), fix_arabic_text(ph), fill=palette["primary"], font=fonts["bold"], anchor="mm")
                curr_x -= w
            y += 36
            for p_i, p_row in enumerate(payments_list[:4], start=1):
                p_amt = fmt_money(p_row.get("payment_amount", 0))
                p_date = str(p_row.get("payment_date_formatted") or p_row.get("date") or "-")
                p_user = str(p_row.get("receiver_name") or p_row.get("payer_name") or p_row.get("user_name") or "-")
                p_vals = [p_user, p_date, p_amt, str(p_i)]
                curr_x = right_x
                for idx, pv in enumerate(p_vals):
                    w = p_widths[idx]
                    draw.rectangle([(curr_x - w, y), (curr_x, y + 34)], fill="#ffffff", outline=palette["border_light"], width=1)
                    draw.text((curr_x - w // 2, y + 17), fix_arabic_text(pv), fill=palette["text"], font=fonts["body"], anchor="mm")
                    curr_x -= w
                y += 34
            y += 12

        orig_p = _clean_num_val(invoice_data.get("original_price", sell_p))
        disc = _clean_num_val(invoice_data.get("discount", 0.0))
        paid = _clean_num_val(invoice_data.get("cash_received") if invoice_data.get("cash_received") is not None else invoice_data.get("paid_amount", 0.0))
        rem = _clean_num_val(invoice_data.get("remaining_balance") if invoice_data.get("remaining_balance") is not None else invoice_data.get("remaining_amount", 0.0))
        supp_credit = _clean_num_val(invoice_data.get("supplier_credit", 0.0))

        fin_box_top = max(y + 20, height - 660)
        fin_box_h = 264
        fin_box_bottom = fin_box_top + fin_box_h

        half_w = (content_width - 24) // 2
        fin_box_left = right_x - half_w
        terms_box_right = fin_box_left - 24

        draw.rectangle([(fin_box_left, fin_box_top), (right_x, fin_box_bottom)], fill=palette["total_box"], outline=palette["border"], width=2)
        draw.rectangle([(fin_box_left, fin_box_top), (right_x, fin_box_top + 46)], fill=palette["header_bg"], outline=palette["border"], width=1)
        draw.text((right_x - 18, fin_box_top + 23), fix_arabic_text("💰 ملخص الحساب المالي للفاتورة:"), fill=palette["primary"], font=fonts["section"], anchor="ra")

        fy = fin_box_top + 62
        if disc > 0 and not is_supp_doc:
            draw.text((right_x - 22, fy), fix_arabic_text(f"السعر قبل الخصم: {fmt_money(orig_p)}  |  الخصم: {fmt_money(disc)}"), fill=palette["text_muted"], font=fonts["bold"], anchor="ra")
            fy += 36

        tot_label = "إجمالي فاتورة المشتريات:" if is_supp_doc else "إجمالي المبلغ المستحق:"
        paid_label = "إجمالي المسدد للمورد:" if is_supp_doc else "إجمالي المدفوع نقداً:"
        draw.text((right_x - 22, fy), fix_arabic_text(f"{tot_label}  {fmt_money(sell_p)}"), fill=palette["text"], font=fonts["huge"], anchor="ra")
        fy += 46
        draw.text((right_x - 22, fy), fix_arabic_text(f"{paid_label}  {fmt_money(paid)}"), fill=palette["success"], font=fonts["huge"], anchor="ra")
        fy += 46
        if supp_credit > 0:
            draw.text((right_x - 22, fy), fix_arabic_text(f"🌟 رصيد دائن لنا لدى المورد:  {fmt_money(supp_credit)}"), fill=palette["secondary"], font=fonts["section"], anchor="ra")
            fy += 38

        if is_supp_doc:
            rem_label = "المتبقي للمورد (الآجل):" if rem > 0 else "المتبقي للمورد (خالص 🟢):"
        else:
            rem_label = "المتبقي (المديونية):" if rem > 0 else "المتبقي (خالص بالكامل 🟢):"
        rem_color = palette["danger"] if rem > 0 else palette["success"]
        draw.text((right_x - 22, fy), fix_arabic_text(f"{rem_label}  {fmt_money(rem)}"), fill=rem_color, font=fonts["huge"], anchor="ra")

        draw.rectangle([(left_x, fin_box_top), (terms_box_right, fin_box_bottom)], fill="#ffffff", outline=palette["border"], width=1)
        draw.rectangle([(left_x, fin_box_top), (terms_box_right, fin_box_top + 46)], fill=palette["header_bg"], outline=palette["border"], width=1)
        draw.text((terms_box_right - 18, fin_box_top + 23), fix_arabic_text("📝 الشروط والضمان والملاحظات المعتمدة:"), fill=palette["primary"], font=fonts["section"], anchor="ra")

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
            custom_terms = f"ملاحظة: يوجد رصيد دائن مستحق لنا لدى المورد بقيمة {fmt_money(supp_credit)}.\n" + custom_terms
        sale_notes = (invoice_data.get("sale_notes") or invoice_data.get("notes") or "").strip()
        if sale_notes and sale_notes not in custom_terms:
            custom_terms = f"ملاحظة إضافية: {sale_notes}\n" + custom_terms

        ty = fin_box_top + 58
        for line in custom_terms.split("\n")[:5]:
            if line.strip():
                draw.text((terms_box_right - 18, ty), fix_arabic_text(line.strip()), fill=palette["text"], font=fonts["bold"], anchor="ra")
                ty += 34

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
                qr_w, qr_h = 78, 78
                qr_img = qr_img.resize((qr_w, qr_h), Image.Resampling.LANCZOS)

                qr_x = left_x + 10
                qr_y = bc_area_top + 2
                img.paste(qr_img, (qr_x, qr_y))
                draw.rectangle([(qr_x, qr_y), (qr_x + qr_w, qr_y + qr_h)], outline=palette["border"], width=1)
                qr_pasted = True
            except Exception:
                qr_pasted = False

        bc_w, bc_h = (260, 52) if qr_pasted else (320, 52)
        bc_x = (left_x + 105) if qr_pasted else (left_x + 10)
        bc_y = bc_area_top + 14
        draw.rectangle([(bc_x, bc_y), (bc_x + bc_w, bc_y + bc_h)], fill="#ffffff", outline=palette["border"], width=1)
        curr_bx = bc_x + 14
        pattern = [2, 1, 3, 1, 2, 2, 1, 3, 2, 1, 1, 2, 3, 1, 2, 1, 3, 2, 1, 2, 1, 3, 1, 2, 2, 1, 3, 1, 2, 2, 1, 3]
        for b_w in pattern:
            if curr_bx + b_w > bc_x + bc_w - 14:
                break
            draw.rectangle([(curr_bx, bc_y + 4), (curr_bx + b_w, bc_y + bc_h - 18)], fill=palette["text"])
            curr_bx += b_w + 2
        draw.text((bc_x + bc_w // 2, bc_y + bc_h - 9), f"*{inv_code}*", fill=palette["text_muted"], font=fonts["small"], anchor="mm")

        draw.text((right_x - 10, bc_area_top + 32), fix_arabic_text("مسح الباركود للتحقق الفوري من صحة الفاتورة وسيريال الأجهزة في النظام"), fill=palette["text_muted"], font=fonts["bold"], anchor="ra")

        sig_y = bc_area_top + 96
        draw.line([(left_x + 20, sig_y), (right_x - 20, sig_y)], fill=palette["border_light"], width=1)
        sig_label = "توقيع المورد / المستلم" if is_supp_doc else "توقيع العميل / المستلم"
        draw.text((left_x + 180, sig_y + 24), fix_arabic_text(sig_label), fill=palette["text"], font=fonts["section"], anchor="ma")
        draw.text((right_x - 180, sig_y + 24), fix_arabic_text("ختم وتوقيع محل هشام كيوان"), fill=palette["text"], font=fonts["section"], anchor="ma")

    footer_bar_top = height - 56
    draw.rectangle([(24, footer_bar_top), (width - 24, height - 24)], fill=palette["table_hdr"])
    draw.text((width // 2, footer_bar_top + 16), fix_arabic_text(f"شكراً لثقتكم بمحل هشام كيوان - نسعد بخدمتكم دائماً  •  صفحة {page_n} من {tot_p}"), fill="#ffffff", font=fonts["bold"], anchor="mm")

    page_suffix = f"_p{page_n}" if tot_p > 1 else ""
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
    devices_list = invoice_data.get("devices_list") or []
    if not devices_list and invoice_data.get("device"):
        devices_list = [invoice_data["device"]]

    if len(devices_list) <= 6:
        inv_copy = dict(invoice_data)
        inv_copy["devices_list"] = devices_list
        inv_copy["page_num"] = 1
        inv_copy["total_pages"] = 1
        return [generate_invoice_image(inv_copy)]

    pages_items = []
    rem_devices = list(devices_list)

    while len(rem_devices) > 6:
        chunk = rem_devices[:12]
        rem_devices = rem_devices[12:]
        pages_items.append(chunk)

    if rem_devices:
        pages_items.append(rem_devices)

    total_pages = len(pages_items)
    generated_pages = []

    for idx, chunk in enumerate(pages_items, start=1):
        page_data = dict(invoice_data)
        page_data["devices_list"] = chunk
        page_data["page_num"] = idx
        page_data["total_pages"] = total_pages
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
