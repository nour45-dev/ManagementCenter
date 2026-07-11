# ====================================================
# ملف pdf_report.py - تقرير PDF بالعربي الكامل
# ====================================================

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from datetime import datetime
import os
import tempfile
import arabic_reshaper       # بيصلح شكل الحروف العربية
from bidi.algorithm import get_display  # بيعكس الاتجاه (RTL)

# ====================================================
# تسجيل الفونت العربي - لازم يكون في نفس المجلد
# ====================================================
FONT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_REGULAR = os.path.join(FONT_DIR, "Amiri-Regular.ttf")
FONT_BOLD = os.path.join(FONT_DIR, "Amiri-Bold.ttf")

def register_arabic_fonts():
    """بتسجل الفونت العربي في reportlab"""
    try:
        pdfmetrics.registerFont(TTFont('Amiri', FONT_REGULAR))
        pdfmetrics.registerFont(TTFont('Amiri-Bold', FONT_BOLD))
        return True
    except Exception as e:
        print(f"⚠️ مش قادر يحمل الفونت العربي: {e}")
        return False

def ar(text: str) -> str:
    """
    بتحول النص العربي لشكل صح في الـ PDF
    arabic_reshaper: بيصلح شكل الحروف المتصلة
    get_display: بيخلي الاتجاه من اليمين لليسار
    """
    if not text:
        return ""
    try:
        reshaped = arabic_reshaper.reshape(str(text))
        return get_display(reshaped)
    except:
        return str(text)


def generate_pdf(students: list, title: str = "كل الطلاب") -> str:
    """
    بتعمل ملف PDF احترافي بالعربي الكامل
    students = قائمة الطلاب من Google Sheets
    title = عنوان التقرير
    بترجع مسار ملف الـ PDF
    """

    # بنسجل الفونت
    fonts_ok = register_arabic_fonts()
    arabic_font = 'Amiri' if fonts_ok else 'Helvetica'
    arabic_font_bold = 'Amiri-Bold' if fonts_ok else 'Helvetica-Bold'

    # بنعمل ملف مؤقت
    tmp_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix='.pdf',
        prefix='araij_report_'
    )
    pdf_path = tmp_file.name
    tmp_file.close()

    # إعداد الصفحة A4
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    elements = []
    styles = getSampleStyleSheet()

    # ====== ستايل العنوان بالعربي ======
    title_style = ParagraphStyle(
        'ArabicTitle',
        parent=styles['Normal'],
        fontSize=20,
        textColor=colors.HexColor('#1a3a6b'),
        alignment=TA_CENTER,
        spaceAfter=8,
        fontName=arabic_font_bold
    )

    subtitle_style = ParagraphStyle(
        'ArabicSubtitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#555555'),
        alignment=TA_CENTER,
        spaceAfter=20,
        fontName=arabic_font
    )

    # ====== العنوان الرئيسي ======
    elements.append(Paragraph(ar("مركز الارائج - تقرير الطلاب"), title_style))
    elements.append(Spacer(1, 0.4*cm))  # مسافة بين العنوانين
    elements.append(Paragraph(
        ar(f"تقرير: {title}  |  عدد الطلاب: {len(students)}  |  التاريخ: {datetime.now().strftime('%Y-%m-%d')}"),
        subtitle_style
    ))

    # خط فاصل
    elements.append(Spacer(1, 0.3*cm))

    # ====== بناء بيانات الجدول ======
    # الهيدر بالعربي (معكوس عشان RTL)
    headers = [
        ar('م'), ar('الاسم'), ar('الكود'), ar('المنطقة'),
        ar('التليفون'), ar('ولي الأمر'), ar('السنة'),
        ar('التخصص'), ar('المواد'), ar('التسجيل'),
    ]

    table_data = [headers]

    for i, s in enumerate(students, 1):
        subjects = s.get('المواد', '')
        if len(subjects) > 20:
            subjects = subjects[:20] + '...'
        row = [
            str(i),
            ar(s.get('الاسم', '')),
            s.get('الكود', ''),
            ar(s.get('المنطقة', '')),
            s.get('التليفون', ''),
            s.get('ولي الأمر', ''),
            ar(s.get('السنة الدراسية', '')),
            ar(s.get('التخصص', '')),
            ar(subjects),
            s.get('تاريخ التسجيل', '')[:10] if s.get('تاريخ التسجيل') else '',
        ]
        table_data.append(row)

    col_widths = [0.7*cm, 2.8*cm, 1.6*cm, 2*cm, 2.3*cm, 2.3*cm, 1.2*cm, 2*cm, 2.2*cm, 1.9*cm]

    # إنشاء الجدول
    table = Table(table_data, colWidths=col_widths, repeatRows=1)

    # تنسيق الجدول
    table.setStyle(TableStyle([
        # ====== الهيدر ======
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a3a6b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), arabic_font_bold),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),

        # ====== البيانات ======
        ('FONTNAME', (0, 1), (-1, -1), arabic_font),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),

        # ====== ألوان متبادلة للصفوف ======
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [
            colors.white,
            colors.HexColor('#f0f4ff')
        ]),

        # ====== الحدود ======
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.HexColor('#1a3a6b')),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 1*cm))

    # ====== Footer ======
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#888888'),
        alignment=TA_CENTER,
        fontName=arabic_font
    )
    elements.append(Paragraph(
        ar(f"مركز الارائج التعليمي  |  تم الإنشاء: {datetime.now().strftime('%Y-%m-%d %H:%M')}"),
        footer_style
    ))

    # بنبني الـ PDF
    doc.build(elements)
    return pdf_path
