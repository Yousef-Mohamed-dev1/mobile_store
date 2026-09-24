import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

def generate_invoice_image(inv_data):
    if not os.path.exists("invoices"):
        os.makedirs("invoices")

    sale_id = inv_data.get('sale_id', '000')
    customer_name = inv_data.get('customer_name', 'عميل نقدي')
    customer_phone = inv_data.get('customer_phone', '-')
    dev = inv_data.get('device', {})
    
    orig_price = inv_data.get('original_price', 0.0)
    discount = inv_data.get('discount', 0.0)
    sell_price = inv_data.get('sell_price', 0.0)
    cash_received = inv_data.get('cash_received', 0.0)
    remaining_balance = inv_data.get('remaining_balance', 0.0)
    custom_terms = inv_data.get('custom_terms', None)
    print_style = inv_data.get('print_style', 'color')

    width = 1200
    height = 1600

    if print_style == 'burgundy':
        PRIMARY = (128, 0, 32)
        ACCENT = (180, 40, 60)
        TEXT_COLOR = (30, 30, 30)
        CARD_BG = (250, 245, 245)
    elif print_style == 'grayscale':
        PRIMARY = (40, 40, 40)
        ACCENT = (80, 80, 80)
        TEXT_COLOR = (20, 20, 20)
        CARD_BG = (245, 245, 245)
    else:
        PRIMARY = (15, 23, 42)
        ACCENT = (14, 116, 144)
        TEXT_COLOR = (15, 23, 42)
        CARD_BG = (241, 245, 249)

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("arial.ttf", 36)
        font_sub = ImageFont.truetype("arial.ttf", 22)
        font_body = ImageFont.truetype("arial.ttf", 20)
        font_bold = ImageFont.truetype("arial.ttf", 22)
    except IOError:
        font_title = font_sub = font_body = font_bold = ImageFont.load_default()

    # رأس الفاتورة
    draw.rectangle([(0, 0), (width, 140)], fill=PRIMARY)
    draw.text((600, 40), "\u200fمركز هشام كيوان لإدارة الهواتف الذكية\u200f", fill="white", font=font_title, anchor="mm")
    draw.text((600, 95), "\u200fفاتورة بيع ومعاملة مالية معتمدة\u200f", fill=(200, 220, 255), font=font_sub, anchor="mm")

    # بيانات الفاتورة
    draw.rectangle([(60, 170), (width - 60, 250)], fill=CARD_BG, outline=PRIMARY, width=2)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    draw.text((width - 90, 190), f"\u200fرقم الفاتورة: #{sale_id}\u200f", fill=TEXT_COLOR, font=font_bold, anchor="ra")
    draw.text((90, 190), f"\u200fالتاريخ: {now_str}\u200f", fill=TEXT_COLOR, font=font_body, anchor="la")

    # بيانات العميل
    draw.rectangle([(60, 270), (width - 60, 370)], fill="white", outline=ACCENT, width=2)
    draw.text((width - 90, 300), f"\u200fاسم العميل: {customer_name}\u200f", fill=TEXT_COLOR, font=font_bold, anchor="ra")
    draw.text((90, 300), f"\u200fرقم الهاتف: {customer_phone}\u200f", fill=TEXT_COLOR, font=font_body, anchor="la")

    # مواصفات الجهاز
    draw.rectangle([(60, 390), (width - 60, 750)], fill=CARD_BG, outline=PRIMARY, width=2)
    draw.text((width - 90, 420), "\u200f📱 مواصفات الجهاز المباع:\u200f", fill=PRIMARY, font=font_title, anchor="ra")

    dev_category = dev.get('category', '-')
    dev_model = dev.get('model', '-')
    dev_storage = dev.get('storage', '-')
    dev_ram = dev.get('ram', '-')
    dev_imei = dev.get('imei_serial', '-')
    dev_battery = f"{dev.get('battery_health', 0)}%" if dev.get('battery_health') else "لا يوجد"

    specs = [
        (f"\u200fالماركة / النوع: {dev_category}\u200f", f"\u200fالموديل: {dev_model}\u200f"),
        (f"\u200fالمساحة: {dev_storage}\u200f", f"\u200fالرامات: {dev_ram}\u200f"),
        (f"\u200fنسبة البطارية: {dev_battery}\u200f", f"\u200fالسيريال / IMEI: {dev_imei}\u200f")
    ]

    y_pos = 480
    for s1, s2 in specs:
        draw.text((width - 90, y_pos), s1, fill=TEXT_COLOR, font=font_body, anchor="ra")
        draw.text((90, y_pos), s2, fill=TEXT_COLOR, font=font_body, anchor="la")
        y_pos += 70

    # جدول الحسابات
    draw.rectangle([(60, 770), (width - 60, 1050)], fill="white", outline=PRIMARY, width=2)
    draw.text((width - 90, 800), "\u200f💰 التفاصيل المالية والحسابية:\u200f", fill=PRIMARY, font=font_title, anchor="ra")

    fin_grid = [
        (f"\u200fإجمالي السعر: {orig_price:,.2f} ج.م\u200f", f"\u200fالخصم: {discount:,.2f} ج.م\u200f"),
        (f"\u200fالصافي للبيع: {sell_price:,.2f} ج.م\u200f", f"\u200fالمدفوع نقداً: {cash_received:,.2f} ج.م\u200f"),
        (f"\u200fالمتبقي (الآجل): {remaining_balance:,.2f} ج.م\u200f", f"\u200fحالة الدفع: {'تم السداد بالكامل 🟢' if remaining_balance <= 0 else 'متبقي آجل 🔴'}\u200f")
    ]

    y_pos = 860
    for f1, f2 in fin_grid:
        draw.text((width - 90, y_pos), f1, fill=TEXT_COLOR, font=font_bold, anchor="ra")
        draw.text((90, y_pos), f2, fill=TEXT_COLOR, font=font_bold, anchor="la")
        y_pos += 60

    # الشروط والتعليمات
    draw.rectangle([(60, 1070), (width - 60, 1380)], fill=CARD_BG, outline=ACCENT, width=1)
    draw.text((width - 90, 1090), "\u200fالشروط والأحكام والضمان:\u200f", fill=ACCENT, font=font_bold, anchor="ra")

    if not custom_terms:
        terms_lines = [
            "\u200f1. البضاعة المباعة تخضع للضمان المحدد من المحل حسب الحالة والاتفاق.\u200f",
            "\u200f2. لا يحق للعميل استرجاع الجهاز بعد مضي المدة المتفق عليها إلا بشرط العيوب الفنية.\u200f",
            "\u200f3. أجهزة الكسر زيرو تضمن سلامة السيريال والمعالجة الخالية من العيوب الخفية.\u200f",
            "\u200f4. هذه الفاتورة سند قانوني ورسمي لإثبات ملكية الجهاز والمعاملة المالية.\u200f"
        ]
    else:
        terms_lines = [f"\u200f{line.strip()}\u200f" for line in custom_terms.split('\n') if line.strip()]

    y_pos = 1140
    for line in terms_lines:
        draw.text((width - 90, y_pos), line, fill=TEXT_COLOR, font=font_body, anchor="ra")
        y_pos += 45

    # التوقيعات
    draw.text((width - 150, 1460), "\u200fتوقيع المستلم / البائع\u200f", fill=PRIMARY, font=font_bold, anchor="ra")
    draw.text((150, 1460), "\u200fتوقيع العميل\u200f", fill=PRIMARY, font=font_bold, anchor="la")

    draw.line([(width - 300, 1530), (width - 80, 1530)], fill=PRIMARY, width=2)
    draw.line([(80, 1530), (300, 1530)], fill=PRIMARY, width=2)

    filename = f"invoices/invoice_{sale_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    img.save(filename)
    return filename