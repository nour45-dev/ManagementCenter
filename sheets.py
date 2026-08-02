import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from config import SHEET_ID, SHEET_NAME, CREDENTIALS_FILE, COLUMNS, TEACHER_ALIASES

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
        if all_data:
            print(f"🔍 أعمدة الشيت: {list(all_data[0].keys())}")
        for year in ["ث1", "ث2", "ث3"]:
            year_students = [
                s for s in all_data
                if str(s.get("السنة الدراسية", "") or s.get("السنة", "")).strip() == year
            ]
            if year_students:
                last_code = year_students[-1].get("الكود", "")
                result[year] = str(last_code) if str(last_code).strip() else "لا يوجد"
        return result
    except Exception as e:
        print(f"❌ خطأ في جلب آخر الأكواد: {e}")
        return {"ث1": "خطأ", "ث2": "خطأ", "ث3": "خطأ"}


def search_by_code(code: str) -> dict | None:
    try:
        sheet = connect_to_sheet()
        all_data = sheet.get_all_records()
        code_str = str(code).strip()
        for student in all_data:
            if str(student.get("الكود", "") or "").strip() == code_str:
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
        return [
            s for s in all_data
            if str(s.get("السنة الدراسية", "") or s.get("السنة", "")).strip() == str(year).strip()
        ]
    except Exception as e:
        print(f"❌ خطأ في جلب الطلاب: {e}")
        return []


def update_student(code: str, field: str, new_value: str) -> bool:
    try:
        sheet = connect_to_sheet()
        all_data = sheet.get_all_records()
        headers = sheet.row_values(1)
        code_str = str(code).strip()
        for i, student in enumerate(all_data):
            if str(student.get("الكود", "") or "").strip() == code_str:
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
        code_str = str(code).strip()
        for i, student in enumerate(all_data):
            if str(student.get("الكود", "") or "").strip() == code_str:
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
        def yr(s): return str(s.get("السنة الدراسية", "") or s.get("السنة", "")).strip()
        return {
            "الإجمالي": len(all_data),
            "ث1": len([s for s in all_data if yr(s) == "ث1"]),
            "ث2": len([s for s in all_data if yr(s) == "ث2"]),
            "ث3": len([s for s in all_data if yr(s) == "ث3"]),
        }
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

        def yr(s): return str(s.get("السنة الدراسية", "") or s.get("السنة", "")).strip()
        def sp(s): return str(s.get("التخصص", "")).strip()

        def count(lst, year=None, spec=None):
            r = lst
            if year:   r = [s for s in r if yr(s) == year]
            if spec == "بكالوريا": r = [s for s in r if "بكالوريا" in sp(s)]
            elif spec: r = [s for s in r if sp(s) == spec]
            return len(r)

        active = [s for s in all_data if str(s.get("المدرسين", "")).strip() and str(s.get("المواد", "")).strip()]

        return {
            "الإجمالي":      len(all_data),
            "مع_مدرسين":    len(active),
            "ث1":            count(all_data, year="ث1"),
            "ث2":            count(all_data, year="ث2"),
            "ث3":            count(all_data, year="ث3"),
            "نشط_ث1":       count(active, year="ث1"),
            "نشط_ث2":       count(active, year="ث2"),
            "نشط_ث3":       count(active, year="ث3"),
            "عام":           count(all_data, spec="عام"),
            "عام_ث1":        count(all_data, year="ث1", spec="عام"),
            "عام_ث2":        count(all_data, year="ث2", spec="عام"),
            "عام_ث3":        count(all_data, year="ث3", spec="عام"),
            "أزهر":          count(all_data, spec="أزهر"),
            "أزهر_ث1":       count(all_data, year="ث1", spec="أزهر"),
            "أزهر_ث2":       count(all_data, year="ث2", spec="أزهر"),
            "أزهر_ث3":       count(all_data, year="ث3", spec="أزهر"),
            "بكالوريا":      count(all_data, spec="بكالوريا"),
            "بكالوريا_ث1":   count(all_data, year="ث1", spec="بكالوريا"),
            "بكالوريا_ث2":   count(all_data, year="ث2", spec="بكالوريا"),
            "بكالوريا_ث3":   count(all_data, year="ث3", spec="بكالوريا"),
        }
    except Exception as e:
        print(f"❌ خطأ في الإحصائيات: {e}")
        return {}


def _parse_entries(teachers_str: str) -> list:
    results = []
    entries = [e.strip() for e in teachers_str.split("|") if e.strip()]
    if len(entries) == 1:
        for sep in ["،", ","]:
            if sep in teachers_str:
                entries = [e.strip() for e in teachers_str.split(sep) if e.strip()]
                break
    for entry in entries:
        if not entry:
            continue
        if "::" in entry:
            parts = entry.split("::", 1)
            subject, teacher = parts[0].strip(), parts[1].strip()
        elif "/" in entry:
            idx = entry.index("/")
            subject, teacher = entry[:idx].strip(), entry[idx+1:].strip()
        elif ":" in entry:
            parts = entry.split(":", 1)
            subject, teacher = parts[0].strip(), parts[1].strip()
        else:
            subject, teacher = "", entry.strip()
        if teacher:
            results.append((subject, teacher))
    return results


def get_teacher_stats(teacher_name: str = None) -> dict | list:
    try:
        sheet = connect_to_sheet()
        all_data = sheet.get_all_records()
        teachers = {}

        for student in all_data:
            teachers_str = str(student.get("المدرسين", "")).strip()
            if not teachers_str:
                continue
            s_yr   = str(student.get("السنة الدراسية", "") or student.get("السنة", "")).strip()
            s_spec = str(student.get("التخصص", "")).strip()

            for subject, teacher in _parse_entries(teachers_str):
                teacher = teacher.strip()
                if teacher in ["كلهم", "الكل", "all"]:
                    continue
                # بنوحد اسم المدرس - أي صيغة مختلفة (بمسافات/بدون "ا/"/اسم مختصر) بترجع للاسم الرسمي
                teacher = TEACHER_ALIASES.get(teacher, teacher)
                if teacher not in teachers:
                    teachers[teacher] = []
                teachers[teacher].append({
                    "اسم":       student.get("الاسم", ""),
                    "كود":       str(student.get("الكود", "") or ""),
                    "السنة":     s_yr,
                    "التخصص":   s_spec,
                    "المادة":    subject,
                    "التليفون":  str(student.get("التليفون", "") or ""),
                    "ولي_الامر": str(student.get("ولي الأمر", "") or ""),
                    "المنطقة":   str(student.get("المنطقة", "") or ""),
                })

        if teacher_name:
            teacher_name_lower = teacher_name.strip().lower()
            results = {}
            for t, students in teachers.items():
                if teacher_name_lower in t.lower():
                    by_year = {"ث1": 0, "ث2": 0, "ث3": 0}
                    by_spec = {"عام": 0, "أزهر": 0, "بكالوريا": 0}
                    for s in students:
                        if s.get("السنة") in by_year:
                            by_year[s["السنة"]] += 1
                        sp = s.get("التخصص", "")
                        if "بكالوريا" in sp: by_spec["بكالوريا"] += 1
                        elif sp == "أزهر":   by_spec["أزهر"] += 1
                        elif sp == "عام":    by_spec["عام"] += 1
                    results[t] = {"طلاب": students, "بالسنة": by_year, "بالتخصص": by_spec}
            return results

        return dict(sorted(teachers.items(), key=lambda x: len(x[1]), reverse=True))

    except Exception as e:
        print(f"❌ خطأ في إحصائيات المدرسين: {e}")
        return {}


def get_teacher_stats_all() -> dict:
    return get_teacher_stats()
