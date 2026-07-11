# ====================================================
# ملف sheets.py - كل التعامل مع Google Sheets هنا
# ====================================================

import gspread  # المكتبة اللي بتتكلم مع Google Sheets
from google.oauth2.service_account import Credentials  # عشان نثبت هويتنا مع Google
from datetime import datetime  # عشان نسجل تاريخ التسجيل
from config import SHEET_ID, SHEET_NAME, CREDENTIALS_FILE, COLUMNS  # بنجيب الإعدادات


# ====================================================
# الصلاحيات اللي محتاجينها من Google
# ====================================================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",  # صلاحية تعديل الشيت
    "https://www.googleapis.com/auth/drive"           # صلاحية الوصول للدرايف
]


def connect_to_sheet():
    """
    بتوصل بـ Google Sheets وترجع الورقة جاهزة للاستخدام
    """
    # بنثبت هويتنا باستخدام ملف الـ credentials
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    
    # بنعمل اتصال بـ Google
    client = gspread.authorize(creds)
    
    # بنفتح الملف بالـ ID بتاعه
    spreadsheet = client.open_by_key(SHEET_ID)
    
    # بنفتح الورقة المطلوبة
    sheet = spreadsheet.worksheet(SHEET_NAME)
    
    return sheet


def setup_sheet():
    """
    بتعمل الأعمدة في أول سطر لو الشيت فاضي
    بتتنادى مرة واحدة بس في الأول
    """
    sheet = connect_to_sheet()
    
    # بنشوف لو في بيانات موجودة
    existing = sheet.get_all_values()
    
    # لو الشيت فاضي، نحط الأعمدة
    if not existing:
        sheet.append_row(COLUMNS)
        print("✅ تم إنشاء أعمدة الشيت")
    else:
        print("✅ الشيت موجود ومعمول")


def add_student(data: dict) -> bool:
    """
    بتضيف طالب جديد في الشيت
    الترتيب: الكود|الاسم|المنطقة|التليفون|ولي الأمر|السنة|التخصص|المواد|المدرسين|التسجيل
    """
    try:
        sheet = connect_to_sheet()
        row = [
            data.get("كود", ""),                          # A - الكود
            data.get("اسم", ""),                          # B - الاسم
            data.get("المنطقة", ""),                      # C - المنطقة
            data.get("تليفون", ""),                       # D - التليفون
            data.get("ولي الأمر", ""),                    # E - ولي الأمر
            data.get("السنة", ""),                        # F - السنة الدراسية
            data.get("التخصص", ""),                       # G - التخصص
            data.get("المواد", ""),                       # H - المواد
            data.get("المدرسين", ""),                     # I - المدرسين
            datetime.now().strftime("%Y-%m-%d %H:%M")     # J - تاريخ التسجيل
        ]
        sheet.append_row(row)
        return True
    except Exception as e:
        print(f"❌ خطأ في إضافة الطالب: {e}")
        return False


def get_last_code_per_year() -> dict:
    """
    بتجيب آخر كود مسجل لكل سنة دراسية
    بترجع dict فيه آخر كود لـ ث1 وث2 وث3
    """
    try:
        sheet = connect_to_sheet()
        all_data = sheet.get_all_records()
        result = {"ث1": "لا يوجد", "ث2": "لا يوجد", "ث3": "لا يوجد"}
        for year in ["ث1", "ث2", "ث3"]:
            # بنفلتر طلاب السنة دي
            year_students = [s for s in all_data if s.get("السنة الدراسية") == year]
            if year_students:
                # آخر طالب مسجل = آخر عنصر في القائمة
                result[year] = str(year_students[-1].get("الكود", "لا يوجد"))
        return result
    except Exception as e:
        print(f"❌ خطأ في جلب آخر الأكواد: {e}")
        return {"ث1": "خطأ", "ث2": "خطأ", "ث3": "خطأ"}


def search_by_code(code: str) -> dict | None:
    """
    بتبحث عن طالب بالكود بتاعه
    بترجع بيانات الطالب dict، أو None لو مش موجود
    """
    try:
        sheet = connect_to_sheet()
        
        # بنجيب كل البيانات
        all_data = sheet.get_all_records()
        
        # بنبحث عن الكود في كل الصفوف
        for student in all_data:
            if str(student.get("الكود", "")).strip() == str(code).strip():
                return student  # لقيناه! نرجعه
        
        return None  # مش موجود
        
    except Exception as e:
        print(f"❌ خطأ في البحث: {e}")
        return None


def get_students_by_year(year: str = None) -> list:
    """
    بتجيب قائمة الطلاب
    لو حددت السنة (ث1/ث2/ث3) بتجيب طلابها بس
    لو مش حددت، بتجيب كل الطلاب
    """
    try:
        sheet = connect_to_sheet()
        all_data = sheet.get_all_records()
        
        # لو مش محدد سنة، رجع كل الطلاب
        if not year:
            return all_data
        
        # فلترة بالسنة المطلوبة
        filtered = [s for s in all_data if s.get("السنة الدراسية") == year]
        return filtered
        
    except Exception as e:
        print(f"❌ خطأ في جلب الطلاب: {e}")
        return []


def update_student(code: str, field: str, new_value: str) -> bool:
    """
    بتعدل بيانات طالب موجود
    code = كود الطالب
    field = اسم العمود اللي عايزين نعدله
    new_value = القيمة الجديدة
    بترجع True لو نجح، False لو فشل
    """
    try:
        sheet = connect_to_sheet()
        
        # بنجيب كل البيانات عشان نعرف رقم الصف
        all_data = sheet.get_all_records()
        headers = sheet.row_values(1)  # الصف الأول فيه أسماء الأعمدة
        
        # بنبحث عن الطالب
        for i, student in enumerate(all_data):
            if str(student.get("الكود", "")).strip() == str(code).strip():
                
                # رقم الصف = رقمه في الـ list + 2 (عشان الـ header في سطر 1 والـ list بتبدأ من 0)
                row_num = i + 2
                
                # بنعرف رقم العمود من أسماء الأعمدة
                col_num = headers.index(field) + 1
                
                # بنعدل الخلية المطلوبة
                sheet.update_cell(row_num, col_num, new_value)
                return True
        
        return False  # الطالب مش موجود
        
    except Exception as e:
        print(f"❌ خطأ في التعديل: {e}")
        return False


def delete_student(code: str) -> bool:
    """
    بتمسح طالب من الشيت بالكود بتاعه
    بترجع True لو نجح، False لو فشل
    """
    try:
        sheet = connect_to_sheet()
        all_data = sheet.get_all_records()
        
        # بنبحث عن الطالب
        for i, student in enumerate(all_data):
            if str(student.get("الكود", "")).strip() == str(code).strip():
                
                # رقم الصف = رقمه في الـ list + 2
                row_num = i + 2
                
                # بنمسح الصف كله
                sheet.delete_rows(row_num)
                return True
        
        return False  # مش موجود
        
    except Exception as e:
        print(f"❌ خطأ في الحذف: {e}")
        return False


def get_statistics() -> dict:
    """
    بتجيب إحصائيات عامة عن الطلاب
    بترجع dict فيه إجمالي الطلاب وتوزيعهم على السنوات
    """
    try:
        sheet = connect_to_sheet()
        all_data = sheet.get_all_records()
        
        # بنحسب الأرقام
        stats = {
            "الإجمالي": len(all_data),
            "ث1": len([s for s in all_data if s.get("السنة الدراسية") == "ث1"]),
            "ث2": len([s for s in all_data if s.get("السنة الدراسية") == "ث2"]),
            "ث3": len([s for s in all_data if s.get("السنة الدراسية") == "ث3"]),
        }
        
        return stats
        
    except Exception as e:
        print(f"❌ خطأ في الإحصائيات: {e}")
        return {}


def search_by_name(name: str) -> list:
    """
    بتبحث عن طالب بالاسم أو جزء منه
    بترجع قائمة بكل النتائج المتطابقة
    """
    try:
        sheet = connect_to_sheet()
        all_data = sheet.get_all_records()

        # بنبحث عن الاسم (جزئي - مش لازم اسم كامل)
        name_lower = name.strip().lower()
        results = [
            s for s in all_data
            if name_lower in str(s.get("الاسم", "")).lower()
        ]

        return results

    except Exception as e:
        print(f"❌ خطأ في البحث بالاسم: {e}")
        return []


def get_statistics_updated() -> dict:
    """
    إحصائيات موسعة تشمل التخصصات
    """
    try:
        sheet = connect_to_sheet()
        all_data = sheet.get_all_records()
        stats = {
            "الإجمالي": len(all_data),
            "ث1": len([s for s in all_data if s.get("السنة الدراسية") == "ث1"]),
            "ث2": len([s for s in all_data if s.get("السنة الدراسية") == "ث2"]),
            "ث3": len([s for s in all_data if s.get("السنة الدراسية") == "ث3"]),
            "عام": len([s for s in all_data if s.get("التخصص") == "عام"]),
            "أزهر": len([s for s in all_data if s.get("التخصص") == "أزهر"]),
            "بكالوريا": len([s for s in all_data if "بكالوريا" in str(s.get("التخصص", ""))]),
        }
        return stats
    except Exception as e:
        print(f"❌ خطأ في الإحصائيات: {e}")
        return {}


def get_teacher_stats(teacher_name: str = None) -> dict | list:
    """
    لو بعتلها اسم مدرس: بترجع كام طالب معاه وتفاصيلهم
    لو مبعتلهاش اسم: بترجع كل المدرسين وعدد طلاب كل واحد
    """
    try:
        sheet = connect_to_sheet()
        all_data = sheet.get_all_records()

        # dict فيه كل مدرس وطلابه
        teachers = {}

        for student in all_data:
            teachers_str = str(student.get("المدرسين", ""))
            if not teachers_str.strip():
                continue

            # المدرسين بتاعت الطالب مكتوبة زي:
            # "عربي: مستر أحمد، رياضة: مستر محمد"
            for pair in teachers_str.split("،"):
                pair = pair.strip()
                if ":" in pair:
                    parts = pair.split(":", 1)
                    teacher = parts[1].strip()
                else:
                    teacher = pair.strip()

                if not teacher:
                    continue

                if teacher not in teachers:
                    teachers[teacher] = []
                teachers[teacher].append({
                    "اسم": student.get("الاسم", ""),
                    "كود": student.get("الكود", ""),
                    "السنة": student.get("السنة الدراسية", ""),
                    "المادة": parts[0].strip() if ":" in pair else ""
                })

        if teacher_name:
            # بحث جزئي - مش لازم الاسم كامل
            teacher_name_lower = teacher_name.strip().lower()
            results = {}
            for t, students in teachers.items():
                if teacher_name_lower in t.lower():
                    results[t] = students
            return results

        # كل المدرسين مرتبين من الأكتر للأقل
        sorted_teachers = dict(
            sorted(teachers.items(), key=lambda x: len(x[1]), reverse=True)
        )
        return sorted_teachers

    except Exception as e:
        print(f"❌ خطأ في إحصائيات المدرسين: {e}")
        return {}
