# ====================================================
# keyboards.py - النسخة الكاملة مع تعديل بضغطة زر
# ====================================================

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import SUBJECTS


def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ تسجيل طالب واحد", callback_data="new_student")],
        [InlineKeyboardButton("👥 تسجيل مجموعة", callback_data="new_bulk")],
        [InlineKeyboardButton("📸 تسجيل من صورة", callback_data="new_from_image")],
        [InlineKeyboardButton("🔍 بحث بالاسم", callback_data="search_by_name")],
        [InlineKeyboardButton("🔎 بحث بالكود", callback_data="search_student")],
        [InlineKeyboardButton("✏️ تعديل بيانات", callback_data="edit_student")],
        [InlineKeyboardButton("🗑️ حذف طالب", callback_data="delete_student")],
        [InlineKeyboardButton("📊 تقارير", callback_data="reports")],
        [InlineKeyboardButton("📈 إحصائيات", callback_data="stats"), InlineKeyboardButton("🔢 آخر الأكواد", callback_data="last_codes")],
    ]
    return InlineKeyboardMarkup(keyboard)


def student_actions_keyboard(code: str):
    """أزرار الأكشن على الطالب بعد البحث"""
    keyboard = [
        [InlineKeyboardButton("✏️ تعديل بيانات", callback_data=f"smartedit_{code}")],
        [InlineKeyboardButton("🗑️ حذف الطالب", callback_data=f"delete_{code}")],
        [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def smart_edit_keyboard(student: dict) -> InlineKeyboardMarkup:
    """
    بيعرض البيانات الحالية للطالب وكل زر فيه القيمة الحالية
    م. وفاء تضغط على اللي عايزاه تعدله مباشرة
    """
    code = student.get("الكود", "")
    keyboard = [
        [InlineKeyboardButton(
            f"👤 الاسم: {student.get('الاسم', '')}",
            callback_data=f"sefield_{code}_الاسم"
        )],
        [InlineKeyboardButton(
            f"📍 المنطقة: {student.get('المنطقة', '')}",
            callback_data=f"sefield_{code}_المنطقة"
        )],
        [InlineKeyboardButton(
            f"📱 التليفون: {student.get('التليفون', '')}",
            callback_data=f"sefield_{code}_التليفون"
        )],
        [InlineKeyboardButton(
            f"👨‍👧 ولي الأمر: {student.get('ولي الأمر', '')}",
            callback_data=f"sefield_{code}_ولي الأمر"
        )],
        [InlineKeyboardButton(
            f"📚 السنة: {student.get('السنة الدراسية', '')}",
            callback_data=f"sefield_{code}_السنة الدراسية"
        )],
        [InlineKeyboardButton(
            f"🎓 التخصص: {student.get('التخصص', '')}",
            callback_data=f"sefield_{code}_التخصص"
        )],
        [InlineKeyboardButton(
            f"📖 المواد: {student.get('المواد', '')[:25]}{'...' if len(student.get('المواد',''))>25 else ''}",
            callback_data=f"sefield_{code}_المواد"
        )],
        [InlineKeyboardButton(
            f"👨‍🏫 المدرسين: {student.get('المدرسين', '')[:20]}{'...' if len(student.get('المدرسين',''))>20 else ''}",
            callback_data=f"sefield_{code}_المدرسين"
        )],
        [InlineKeyboardButton("✅ خلاص، حفظ", callback_data=f"done_edit_{code}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def image_actions_keyboard():
    """أزرار ما بعد تحليل الصورة"""
    keyboard = [
        [InlineKeyboardButton("✅ صح، احفظ", callback_data="confirm_image_save")],
        [InlineKeyboardButton("👤 تعديل الاسم", callback_data="imgedit_اسم"),
         InlineKeyboardButton("🔑 تعديل الكود", callback_data="imgedit_كود")],
        [InlineKeyboardButton("📍 تعديل المنطقة", callback_data="imgedit_المنطقة"),
         InlineKeyboardButton("📱 تعديل التليفون", callback_data="imgedit_تليفون")],
        [InlineKeyboardButton("👨‍👧 تعديل ولي الأمر", callback_data="imgedit_ولي الأمر")],
        [InlineKeyboardButton("📚 تعديل السنة", callback_data="imgedit_السنة"),
         InlineKeyboardButton("🎓 تعديل التخصص", callback_data="imgedit_التخصص")],
        [InlineKeyboardButton("📖 تعديل المواد", callback_data="imgedit_المواد")],
        [InlineKeyboardButton("📝 تعديل كل البيانات", callback_data="imgedit_الكل")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def subjects_keyboard(year: str, selected: list = [], teachers: dict = {}):
    """
    أزرار المواد - لو مادة اتختارت بيبين ✅ واسم المدرس لو موجود
    """
    subjects = SUBJECTS.get(year, [])
    keyboard = []
    for i in range(0, len(subjects), 2):
        row = []
        for j in [i, i+1]:
            if j >= len(subjects):
                break
            s = subjects[j]
            if s in selected:
                teacher = teachers.get(s, "")
                label = f"✅ {s}" + (f" ({teacher})" if teacher else "")
            else:
                label = s
            row.append(InlineKeyboardButton(label, callback_data=f"subj_{s}"))
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton(
        f"✅ تأكيد ({len(selected)} مادة)", callback_data="confirm_subjects"
    )])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)


def year_keyboard(callback_prefix="year"):
    keyboard = [
        [
            InlineKeyboardButton("1️⃣ ث1", callback_data=f"{callback_prefix}_ث1"),
            InlineKeyboardButton("2️⃣ ث2", callback_data=f"{callback_prefix}_ث2"),
            InlineKeyboardButton("3️⃣ ث3", callback_data=f"{callback_prefix}_ث3"),
        ],
        [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


def specialization_keyboard(edit_mode=False):
    prefix = "editspec_" if edit_mode else "spec_"
    keyboard = [
        [InlineKeyboardButton("🏫 عام", callback_data=f"{prefix}عام")],
        [InlineKeyboardButton("🕌 أزهر", callback_data=f"{prefix}أزهر")],
        [InlineKeyboardButton("🎓 بكالوريا", callback_data=f"{prefix}بكالوريا")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def baccalaureate_keyboard(edit_mode=False):
    prefix = "editbacc_" if edit_mode else "bacc_"
    keyboard = [
        [InlineKeyboardButton("🏥 طب", callback_data=f"{prefix}طب"),
         InlineKeyboardButton("🏗️ هندسة", callback_data=f"{prefix}هندسة")],
        [InlineKeyboardButton("📚 الاداب", callback_data=f"{prefix}الاداب"),
         InlineKeyboardButton("💼 الاعمال", callback_data=f"{prefix}الاعمال")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def edit_fields_keyboard(code: str):
    keyboard = [
        [InlineKeyboardButton("👤 الاسم", callback_data=f"editfield_{code}_الاسم")],
        [InlineKeyboardButton("📍 المنطقة", callback_data=f"editfield_{code}_المنطقة")],
        [InlineKeyboardButton("📱 التليفون", callback_data=f"editfield_{code}_التليفون")],
        [InlineKeyboardButton("👨‍👧 ولي الأمر", callback_data=f"editfield_{code}_ولي الأمر")],
        [InlineKeyboardButton("📚 السنة الدراسية", callback_data=f"editfield_{code}_السنة الدراسية")],
        [InlineKeyboardButton("🎓 التخصص", callback_data=f"editfield_{code}_التخصص")],
        [InlineKeyboardButton("📖 المواد", callback_data=f"editfield_{code}_المواد")],
        [InlineKeyboardButton("👨‍🏫 المدرسين", callback_data=f"editfield_{code}_المدرسين")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def report_type_keyboard():
    keyboard = [
        [InlineKeyboardButton("👥 كل الطلاب", callback_data="report_all")],
        [InlineKeyboardButton("1️⃣ طلاب ث1", callback_data="report_ث1")],
        [InlineKeyboardButton("2️⃣ طلاب ث2", callback_data="report_ث2")],
        [InlineKeyboardButton("3️⃣ طلاب ث3", callback_data="report_ث3")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def report_content_keyboard(year: str):
    keyboard = [
        [InlineKeyboardButton("👥 الأسماء فقط", callback_data=f"rpt_{year}_names")],
        [InlineKeyboardButton("📱 الأسماء والتليفونات", callback_data=f"rpt_{year}_phones")],
        [InlineKeyboardButton("📖 المواد والمدرسين", callback_data=f"rpt_{year}_subjects")],
        [InlineKeyboardButton("📋 كل البيانات", callback_data=f"rpt_{year}_all")],
        [InlineKeyboardButton("📄 تحميل PDF", callback_data=f"rpt_{year}_pdf")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="reports")],
    ]
    return InlineKeyboardMarkup(keyboard)


def confirm_delete_keyboard(code: str):
    keyboard = [[
        InlineKeyboardButton("✅ آيوه، امسح", callback_data=f"confirm_delete_{code}"),
        InlineKeyboardButton("❌ لا، رجوع", callback_data="back_main"),
    ]]
    return InlineKeyboardMarkup(keyboard)


def back_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back_main")
    ]])
