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
        [InlineKeyboardButton("📈 إحصائيات", callback_data="stats"),
         InlineKeyboardButton("🔢 آخر الأكواد", callback_data="last_codes")],
        [InlineKeyboardButton("👨‍🏫 إحصائيات المدرسين", callback_data="teacher_stats")],
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
