import os
import tempfile
from PIL import Image, ImageDraw, ImageFont

# محاولة تحميل مكتبات تشكيل العربي لمنع تقطيع الحروف
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_BIDI = True
except ImportError:
    HAS_BIDI = False

def fix_arabic_text(text):
    """إعادة تشكيل النص العربي ليظهر متصلاً وباتجاه صحيح RTL."""
    if text is None:
        return ""
    s = str(text).strip()
    if not s:
        return ""
    if HAS_BIDI:
        try:
            reshaped = arabic_reshaper.reshape(s)
            return get_display(reshaped)
        except Exception:
            return s
    return s

def generate_invoice_image(invoice_data):
    """
    توليد فاتورة طباعة عالية الدقة بدون حفظ في الداتا بيز.
    """
    width, height = 800, 1100
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)

    font_path = "arial.ttf"
    try:
        font_title = ImageFont.truetype(font_path, 24)
        font_header = ImageFont.truetype(font_path, 16)
        font_body = ImageFont.truetype(font_path, 13)
        font_bold = ImageFont.truetype(font_path, 14)
    except Exception:
        font_title = font_header = font_body = font_bold = ImageFont.load_default()

    draw.rectangle([(20, 20), (width - 20, height - 20)], outline="black", width=2)
    draw.rectangle([(25, 25), (width - 25, height - 25)], outline="black", width=1)

    title_text = fix_arabic_text("مركز هشام كيوان لإدارة الهواتف الذكية")
    sub_title = fix_arabic_text("فاتورة بيع / تسليم جهاز")
    
    draw.text((width // 2, 50), title_text, fill="black", font=font_title, anchor="mm")
    draw.text((width // 2, 85), sub_title, fill="black", font=font_header, anchor="mm")
    draw.line([(40, 110), (width - 40, 110)], fill="black", width=2)

    sale_id = invoice_data.get('sale_id', '-')
    cust_name = invoice_data.get('customer_name', '-')
    cust_phone = invoice_data.get('customer_phone', '-')
    inv_date = invoice_data.get('date_str', '')

    right_x = width - 50
    left_x = 50
    y = 130

    draw.text((right_x, y), fix_arabic_text(f"رقم الفاتورة: #{sale_id}"), fill="black", font=font_bold, anchor="ra")
    if inv_date:
        draw.text((left_x, y), fix_arabic_text(f"التاريخ: {inv_date}"), fill="black", font=font_body, anchor="la")
    
    y += 30
    draw.text((right_x, y), fix_arabic_text(f"اسم العميل: {cust_name}"), fill="black", font=font_body, anchor="ra")
    draw.text((left_x, y), fix_arabic_text(f"رقم الهاتف: {cust_phone}"), fill="black", font=font_body, anchor="la")

    y += 40
    draw.line([(40, y), (width - 40, y)], fill="black", width=1)
    y += 10

    headers = ["الإجمالي", "السيريال / IMEI", "المواصفات", "الموديل / الجهاز"]
    col_widths = [120, 220, 180, 200]
    
    curr_x = width - 40
    for idx, head in enumerate(headers):
        w = col_widths[idx]
        draw.rectangle([(curr_x - w, y), (curr_x, y + 30)], fill="#e6e6e6", outline="black", width=1)
        draw.text((curr_x - w // 2, y + 15), fix_arabic_text(head), fill="black", font=font_bold, anchor="mm")
        curr_x -= w

    y += 30
    dev = invoice_data.get('device', {})
    category = dev.get('category', '')
    model = dev.get('model', '')
    storage = dev.get('storage', '')
    ram = dev.get('ram', '')
    imei = dev.get('imei_serial', '-')
    sell_p = invoice_data.get('sell_price', 0.0)

    item_row = [
        f"{float(sell_p):,.2f} ج.م",
        str(imei),
        f"{storage} / {ram}",
        f"{category} {model}"
    ]

    curr_x = width - 40
    for idx, val in enumerate(item_row):
        w = col_widths[idx]
        draw.rectangle([(curr_x - w, y), (curr_x, y + 40)], outline="black", width=1)
        draw.text((curr_x - w // 2, y + 20), fix_arabic_text(val), fill="black", font=font_body, anchor="mm")
        curr_x -= w

    y += 60

    paid = invoice_data.get('cash_received', 0.0)
    rem = invoice_data.get('remaining_balance', 0.0)

    draw.rectangle([(width - 350, y), (width - 40, y + 110)], outline="black", width=1)
    draw.text((width - 50, y + 20), fix_arabic_text(f"إجمالي المطلوب: {float(sell_p):,.2f} ج.م"), fill="black", font=font_bold, anchor="ra")
    draw.text((width - 50, y + 50), fix_arabic_text(f"المدفوع نقداً: {float(paid):,.2f} ج.م"), fill="black", font=font_body, anchor="ra")
    draw.text((width - 50, y + 80), fix_arabic_text(f"المتبقي (الآجل): {float(rem):,.2f} ج.م"), fill="black", font=font_bold, anchor="ra")

    y += 130
    draw.line([(40, y), (width - 40, y)], fill="black", width=1)
    y += 15

    custom_terms = invoice_data.get('custom_terms', "1. البضاعة المباعة تخضع للمراجعة والضمان المعين.\n2. يحتفظ المحل بحقه في المتابعة المالية للآجل.")
    draw.text((right_x, y), fix_arabic_text("الشروط والملاحظات:"), fill="black", font=font_bold, anchor="ra")
    
    y += 25
    for line in custom_terms.split('\n'):
        draw.text((right_x - 10, y), fix_arabic_text(line), fill="black", font=font_body, anchor="ra")
        y += 22

    y = height - 90
    draw.line([(40, y), (width - 40, y)], fill="black", width=1)
    y += 25
    draw.text((100, y), fix_arabic_text("توقيع العميل / المستلم"), fill="black", font=font_bold, anchor="ma")
    draw.text((width - 100, y), fix_arabic_text("توقيع الإدارة / المحل"), fill="black", font=font_bold, anchor="ma")

    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, f"temp_invoice_{sale_id}.png")
    img.save(file_path)
    return file_path
