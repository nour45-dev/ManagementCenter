# ====================================================
# attendance.py - حضور وغياب ودرجات الطلاب
# 3 ملفات Google Sheets منفصلة (واحد لكل سنة دراسية: ث1/ث2/ث3)
# نفس تصميم الملفات: اسم الطالب|الكود|تليفون|ولي الأمر ثم بلوك لكل مادة
# (اسم المدرس + 8 أعمدة حصص). كل عمود حصة ممكن يكون:
#   فاضي  -> لسه معملوش حاجة
#   "✓"   -> حضر من غير امتحان
#   "غ"   -> غايب
#   "8/10" -> درجة امتحان (ومعناها إنه حضر)
# ====================================================

import os
import json
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# روابط الملفات اللي بعتها - ممكن تتغير عن طريق environment variables برضو
YEAR_SHEET_IDS = {
    "ث1": os.environ.get("YEAR1_SHEET_ID", "1q_iyNGryFIT5uItAO3m9ta6v-I244CHMzckVwGEKQ-0"),
    "ث2": os.environ.get("YEAR2_SHEET_ID", "1yjExvLdYC42zEHSOf36hfIDLvwIANjbtSFh0h8RXOyA"),
    "ث3": os.environ.get("YEAR3_SHEET_ID", "1FW45EvI_gmEbQkzM1w6gwNGm04jWWxGQjQyPPqf3Ci8"),
}

STUDENT_CODE_COL = 2   # عمود B
MAX_SESSIONS = 8

_ws_cache = {}
_layout_cache = {}


def _connect():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=SCOPES)
    else:
        cred_file = os.environ.get("CREDENTIALS_FILE", "credentials.json")
        creds = Credentials.from_service_account_file(cred_file, scopes=SCOPES)
    return gspread.authorize(creds)


def _get_worksheet(year: str):
    if year not in YEAR_SHEET_IDS:
        raise ValueError(f"سنة غير معروفة: {year}")
    if year in _ws_cache:
        return _ws_cache[year]
    client = _connect()
    sh = client.open_by_key(YEAR_SHEET_IDS[year])
    ws = sh.sheet1
    _ws_cache[year] = ws
    return ws


def _get_layout(year: str, force: bool = False):
    """
    بتقرأ رأس الشيت وترجع بنية المواد ديناميكيًا (من غير ما نحدد أعمدة يدويًا):
    [{"subject": "عربي", "teacher_col": 6, "session_cols": [7,8,...,14]}, ...]
    الأعمدة 1-indexed زي ما gspread بيستخدم.
    """
    if not force and year in _layout_cache:
        return _layout_cache[year]

    ws = _get_worksheet(year)
    row1 = ws.row_values(1)
    row2 = ws.row_values(2)

    blocks = []
    n = max(len(row1), len(row2)) + 1
    col = 1
    while col <= n:
        val2 = row2[col - 1].strip() if col - 1 < len(row2) else ""
        if val2 == "اسم المدرس":
            subject = row1[col - 1].strip() if col - 1 < len(row1) else ""
            teacher_col = col
            session_cols = []
            c = col + 1
            while len(session_cols) < MAX_SESSIONS and c <= n:
                v2 = row2[c - 1].strip() if c - 1 < len(row2) else ""
                if v2 == "اسم المدرس":
                    break
                session_cols.append(c)
                c += 1
            blocks.append({"subject": subject, "teacher_col": teacher_col, "session_cols": session_cols})
            col = c
        else:
            col += 1

    _layout_cache[year] = blocks
    return blocks


def get_subjects_for_year(year: str):
    return [b["subject"] for b in _get_layout(year) if b["subject"]]


def _find_subject_block(year: str, subject: str):
    for b in _get_layout(year):
        if b["subject"].strip() == subject.strip():
            return b
    return None


def find_row_by_code(year: str, code: str):
    """بترجع رقم الصف (1-indexed) لطالب بالكود في شيت السنة دي، أو None لو مش لاقياه"""
    try:
        ws = _get_worksheet(year)
        codes = ws.col_values(STUDENT_CODE_COL)
        code_str = str(code).strip()
        for i, c in enumerate(codes, 1):
            if str(c).strip() == code_str:
                return i
        return None
    except Exception as e:
        print(f"❌ خطأ في البحث عن الطالب في شيت {year}: {e}")
        return None


def get_teacher(year: str, row: int, subject: str) -> str:
    block = _find_subject_block(year, subject)
    if not block:
        return ""
    ws = _get_worksheet(year)
    return (ws.cell(row, block["teacher_col"]).value or "").strip()


def set_teacher_if_empty(year: str, row: int, subject: str, teacher_name: str) -> bool:
    block = _find_subject_block(year, subject)
    if not block:
        return False
    ws = _get_worksheet(year)
    current = (ws.cell(row, block["teacher_col"]).value or "").strip()
    if not current:
        ws.update_cell(row, block["teacher_col"], teacher_name)
    return True


def mark_session(year: str, row: int, subject: str, session: int, value: str) -> bool:
    """بتكتب قيمة (✓ / غ / 8/10) في عمود الحصة المطلوبة"""
    block = _find_subject_block(year, subject)
    if not block or session < 1 or session > len(block["session_cols"]):
        return False
    ws = _get_worksheet(year)
    col = block["session_cols"][session - 1]
    ws.update_cell(row, col, value)
    return True


def get_student_full_record(year: str, row: int) -> list:
    """
    بترجع بيانات كل المواد اللي فيها بيانات فعلية للطالب ده:
    [{"subject":.., "teacher":.., "sessions": {1:"✓", 2:"غ", 5:"8/10", ...}}, ...]
    """
    ws = _get_worksheet(year)
    layout = _get_layout(year)
    row_values = ws.row_values(row)

    def cell(col):
        return row_values[col - 1].strip() if col - 1 < len(row_values) else ""

    result = []
    for block in layout:
        teacher = cell(block["teacher_col"])
        sessions = {}
        for idx, col in enumerate(block["session_cols"], 1):
            v = cell(col)
            if v:
                sessions[idx] = v
        if teacher or sessions:
            result.append({"subject": block["subject"], "teacher": teacher, "sessions": sessions})
    return result


def get_taqdeer(percentage: float) -> str:
    if percentage >= 85:
        return "ممتاز"
    if percentage >= 75:
        return "جيد جدًا"
    if percentage >= 65:
        return "جيد"
    if percentage >= 50:
        return "مقبول"
    return "ضعيف"


def build_report(year: str, row: int) -> dict:
    """
    بتبني تقرير شامل: لكل مادة (عدد الحضور / عدد الغياب / الدرجات)، وتقدير عام
    """
    record = get_student_full_record(year, row)
    subjects_report = []
    total_score = 0
    total_max = 0
    total_present = 0
    total_absent = 0

    for entry in record:
        present = 0
        absent = 0
        grades = []  # (session, score, max)
        for session, val in sorted(entry["sessions"].items()):
            v = val.strip()
            if v == "غ":
                absent += 1
            elif v == "✓":
                present += 1
            elif "/" in v:
                present += 1
                try:
                    score_str, max_str = v.split("/", 1)
                    score = float(score_str.strip())
                    mx = float(max_str.strip())
                    grades.append((session, score, mx))
                    total_score += score
                    total_max += mx
                except ValueError:
                    pass
            else:
                # أي قيمة تانية (زي "0" لوحدها) بنعتبرها حضور بدون تفصيل درجة واضح
                present += 1

        total_present += present
        total_absent += absent

        subjects_report.append({
            "subject": entry["subject"],
            "teacher": entry["teacher"],
            "present": present,
            "absent": absent,
            "grades": grades,
        })

    overall_percentage = (total_score / total_max * 100) if total_max > 0 else None
    overall_taqdeer = get_taqdeer(overall_percentage) if overall_percentage is not None else None

    return {
        "subjects": subjects_report,
        "total_present": total_present,
        "total_absent": total_absent,
        "overall_percentage": overall_percentage,
        "overall_taqdeer": overall_taqdeer,
    }
