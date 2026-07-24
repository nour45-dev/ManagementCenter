import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from config import SHEET_ID, SHEET_NAME, CREDENTIALS_FILE, COLUMNS

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]


def connect_to_sheet():
    import os, json
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SHEET_ID)
    sheet = spreadsheet.worksheet(SHEET_NAME)
    return sheet


def setup_sheet():
    sheet = connect_to_sheet()
    existing = sheet.get_all_values()
    if not existing:
        sheet.append_row(COLUMNS)
        print("✅ تم إنشاء أعمدة الشيت")
    else:
        print("✅ الشيت موجود ومعمول")


def add_student(data: dict) -> bool:
    try:
        sheet = connect_to_sheet()
        row = [
            data.get("كود", ""),
            data.get("اسم", ""),
            data.get("المنطقة", ""),
            data.get("تليفون", ""),
            data.get("ولي الأمر", ""),
            data.get("السنة", ""),
            data.get("التخصص", ""),
            data.get("المواد", ""),
            data.get("المدرسين", ""),
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ]
        sheet.append_row(row)
        return True
    except Exception as e:
        print(f"❌ خطأ في إضافة الطالب: {e}")
        return False


def get_last_code_per_year() -> dict:
    try:
        sheet = connect_to_sheet()
        all_data = sheet.get_all_records()
        result = {"ث1": "لا يوجد", "ث2": "لا يوجد", "ث3": "لا يوجد"}
        for year in ["ث1", "ث2", "ث3"]:
            year_students = [s for s in all_data if str(s.get("السنة الدراسية", "")).strip() == year]
            if year_students:
                result[year] = str(year_students[-1].get("الكود", "لا يوجد"))
        return result
    except Exception as e:
        print(f"❌ خطأ في جلب آخر الأكواد: {e}")
        return {"ث1": "خطأ", "ث2": "خطأ", "ث3": "خطأ"}


def search_by_code(code: str) -> dict | None:
    try:
        sheet = connect_to_sheet()
        all_data = sheet.get_all_records()
        for student in all_data:
            if str(student.get("الكود", "")).strip() == str(code).strip():
                return student
        return None
    except Exception as e:
        print(f"❌ خطأ في البحث: {e}")
        return None


def get_students_by_year(year: str = None) -> list:
    try:
        sheet = connect_to_sheet()
        all_data = sheet.get_all_records()
        if not year:
            return all_data
        return [s for s in all_data if str(s.get("السنة الدراسية", "")).strip() == str(year).strip()]
    except Exception as e:
        print(f"❌ خطأ في جلب الطلاب: {e}")
        return []


def update_student(code: str, field: str, new_value: str) -> bool:
    try:
        sheet = connect_to_sheet()
        all_data = sheet.get_all_records()
        headers = sheet.row_values(1)
        for i, student in enumerate(all_data):
            if str(student.get("الكود", "")).strip() == str(code).strip():
                row_num = i + 2
                col_num = headers.index(field) + 1
                sheet.update_cell(row_num, col_num, new_value)
                return True
        return False
    except Exception as e:
        print(f"❌ خطأ في التعديل: {e}")
        return False


def delete_student(code: str) -> bool:
    try:
        sheet = connect_to_sheet()
        all_data = sheet.get_all_records()
        for i, student in enumerate(all_data):
            if str(student.get("الكود", "")).strip() == str(code).strip():
                sheet.delete_rows(i + 2)
                return True
        return False
    except Exception as e:
        print(f"❌ خطأ في الحذف: {e}")
        return False


def get_statistics() -> dict:
    try:
        sheet = connect_to_sheet()
        all_data = sheet.get_all_records()
        stats = {
            "الإجمالي": len(all_data),
            "ث1": len([s for s in all_data if str(s.get("السنة الدراسية", "")).strip() == "ث1"]),
            "ث2": len([s for s in all_data if str(s.get("السنة الدراسية", "")).strip() == "ث2"]),
            "ث3": len([s for s in all_data if str(s.get("السنة الدراسية", "")).strip() == "ث3"]),
        }
        return stats
    except Exception as e:
        print(f"❌ خطأ في الإحصائيات: {e}")
        return {}


def search_by_name(name: str) -> list:
    try:
        sheet = connect_to_sheet()
        all_data = sheet.get_all_records()
        name_lower = name.strip().lower()
        return [s for s in all_data if name_lower in str(s.get("الاسم", "")).lower()]
    except Exception as e:
        print(f"❌ خطأ في البحث بالاسم: {e}")
        return []


def get_statistics_updated() -> dict:
    try:
        sheet = connect_to_sheet()
        all_data = sheet.get_all_records()

        def count(lst, year=None, spec=None):
            r = lst
            if year:
                r = [s for s in r if str(s.get("السنة الدراسية", "")).strip() == year]
            if spec == "بكالوريا":
                r = [s for s in r if "بكالوريا" in str(s.get("التخصص", ""))]
            elif spec:
                r = [s for s in r if str(s.get("التخصص", "")).strip() == spec]
            return len(r)

        with_teachers = [s for s in all_data if str(s.get("المدرسين", "")).strip()]

        return {
            "الإجمالي":    len(all_data),
            "مع_مدرسين":  len(with_teachers),
            "ث1":          count(all_data, year="ث1"),
            "ث2":          count(all_data, year="ث2"),
            "ث3":          count(all_data, year="ث3"),
            "عام":         count(all_data, spec="عام"),
            "عام_ث1":      count(all_data, year="ث1", spec="عام"),
            "عام_ث2":      count(all_data, year="ث2", spec="عام"),
            "عام_ث3":      count(all_data, year="ث3", spec="عام"),
            "أزهر":        count(all_data, spec="أزهر"),
            "أزهر_ث1":     count(all_data, year="ث1", spec="أزهر"),
            "أزهر_ث2":     count(all_data, year="ث2", spec="أزهر"),
            "أزهر_ث3":     count(all_data, year="ث3", spec="أزهر"),
            "بكالوريا":    count(all_data, spec="بكالوريا"),
            "بكالوريا_ث1": count(all_data, year="ث1", spec="بكالوريا"),
            "بكالوريا_ث2": count(all_data, year="ث2", spec="بكالوريا"),
            "بكالوريا_ث3": count(all_data, year="ث3", spec="بكالوريا"),
        }
    except Exception as e:
        print(f"❌ خطأ في الإحصائيات: {e}")
        return {}


def _parse_teacher_entry(entry: str):
    """
    بتحول entry زي "كيمياء/ا/ محمد صلاح" لـ (مادة, مدرس)
    الفورمات المدعوم: subject/teacher  (أول / بس هو الفاصل)
    """
    entry = entry.strip()
    if not entry:
        return "", ""
    if "::" in entry:
        parts = entry.split("::", 1)
        return parts[0].strip(), parts[1].strip()
    if "/" in entry:
        idx = entry.index("/")
        return entry[:idx].strip(), entry[idx+1:].strip()
    return "", entry


def get_teacher_stats(teacher_name: str = None) -> dict | list:
    try:
        sheet = connect_to_sheet()
        all_data = sheet.get_all_records()

        teachers = {}

        for student in all_data:
            teachers_str = str(student.get("المدرسين", "")).strip()
            if not teachers_str:
                continue

            # نفصل المدرسين — الفاصل الرئيسي هو |
            entries = [e.strip() for e in teachers_str.split("|") if e.strip()]

            for entry in entries:
                subject, teacher = _parse_teacher_entry(entry)
                if not teacher:
                    continue
                if teacher not in teachers:
                    teachers[teacher] = []
                teachers[teacher].append({
                    "اسم":    student.get("الاسم", ""),
                    "كود":    student.get("الكود", ""),
                    "السنة":  str(student.get("السنة الدراسية", "")).strip(),
                    "المادة": subject,
                })

        if teacher_name:
            teacher_name_lower = teacher_name.strip().lower()
            results = {}
            for t, students in teachers.items():
                if teacher_name_lower in t.lower():
                    breakdown = {"ث1": 0, "ث2": 0, "ث3": 0}
                    for s in students:
                        yr = s.get("السنة", "")
                        if yr in breakdown:
                            breakdown[yr] += 1
                    results[t] = {"طلاب": students, "بالسنة": breakdown}
            return results

        return dict(sorted(teachers.items(), key=lambda x: len(x[1]), reverse=True))

    except Exception as e:
        print(f"❌ خطأ في إحصائيات المدرسين: {e}")
        return {}


def get_teacher_stats_all() -> dict:
    return get_teacher_stats()
