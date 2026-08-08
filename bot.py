# ====================================================
# bot.py - النسخة الكاملة v10
# ====================================================

import logging
import json
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import BOT_TOKEN, ADMIN_ID, SUBJECTS, TEACHERS
from sheets import (
    setup_sheet, add_student, search_by_code, search_by_name,
    get_students_by_year, update_student, delete_student,
    get_statistics_updated, get_last_code_per_year, get_teacher_stats
)
from keyboards import (
    main_menu_keyboard, year_keyboard, subjects_keyboard,
    specialization_keyboard, baccalaureate_keyboard,
    student_actions_keyboard, smart_edit_keyboard,
    edit_fields_keyboard, image_actions_keyboard,
    report_type_keyboard, report_content_keyboard,
    confirm_delete_keyboard, back_keyboard, teachers_keyboard,
    attendance_menu_keyboard, att_subjects_keyboard, att_sessions_keyboard,
    att_present_absent_keyboard, att_exam_keyboard, att_done_keyboard
)
from pdf_report import generate_pdf
from config import GEMINI_API_KEY
from google import genai
from google.genai import types
import attendance

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ====================================================
# مراحل المحادثة
# ====================================================
GET_NAME           = "GET_NAME"
GET_CODE           = "GET_CODE"
GET_AREA           = "GET_AREA"
GET_PHONE          = "GET_PHONE"
GET_PARENT_PHONE   = "GET_PARENT_PHONE"
GET_SPECIALIZATION = "GET_SPECIALIZATION"
GET_YEAR           = "GET_YEAR"
GET_SUBJECTS       = "GET_SUBJECTS"
GET_TEACHER        = "GET_TEACHER"         # طلب اسم المدرس لكل مادة
SEARCH_CODE        = "SEARCH_CODE"
SEARCH_NAME        = "SEARCH_NAME"
SMART_EDIT         = "SMART_EDIT"          # تعديل بضغطة زر
EDIT_FIELD_VALUE   = "EDIT_FIELD_VALUE"
EDIT_ONE_FIELD     = "EDIT_ONE_FIELD"      # تعديل حقل واحد من شاشة التعديل الذكي
EDIT_ALL_VALUE     = "EDIT_ALL_VALUE"
IMG_EDIT_FIELD     = "IMG_EDIT_FIELD"
DELETE_CODE        = "DELETE_CODE"
BULK_INPUT         = "BULK_INPUT"
MULTI_PHOTO        = "MULTI_PHOTO"
SEARCH_TEACHER     = "SEARCH_TEACHER"      # البحث عن مدرس بالاسم
ATT_SEARCH         = "ATT_SEARCH"          # بحث عن طالب لتسجيل حضور/درجة/تقرير
ATT_TEACHER_NAME   = "ATT_TEACHER_NAME"    # طلب اسم المدرس لو المادة لسه فاضية
ATT_GRADE_SCORE    = "ATT_GRADE_SCORE"     # الطالب جاب كام
ATT_GRADE_MAX      = "ATT_GRADE_MAX"       # الدرجة من كام

temp_data  = {}
user_state = {}
user_action = {}


def is_admin(update: Update) -> bool:
    if ADMIN_ID is None:
        return True
    return update.effective_user.id == int(ADMIN_ID)


# ====================================================
# /start
# ====================================================
async def start(update: Update, context) -> None:
    if not is_admin(update):
        await update.message.reply_text("❌ مش مصرح لك.")
        return
    try:
        setup_sheet()
    except Exception as e:
        logger.error(f"setup_sheet: {e}")

    uid = update.effective_user.id
    user_state.pop(uid, None)
    temp_data.pop(uid, None)

    # بنجيب آخر كود لكل سنة
    try:
        last_codes = get_last_code_per_year()
        codes_text = (
            f"\n━━━━━━━━━━━━━━━━\n"
            f"🔢 آخر كود مسجل:\n"
            f"1️⃣ ث1: {last_codes.get('ث1', 'لا يوجد')}\n"
            f"2️⃣ ث2: {last_codes.get('ث2', 'لا يوجد')}\n"
            f"3️⃣ ث3: {last_codes.get('ث3', 'لا يوجد')}\n"
            f"━━━━━━━━━━━━━━━━"
        )
    except:
        codes_text = ""

    await update.message.reply_text(
        f"👋 أهلاً م. وفاء!\n"
        f"📚 نظام تسجيل طلاب مركز الارائج"
        f"{codes_text}\n\n"
        f"إيه اللي عايزاه تعمليه؟",
        reply_markup=main_menu_keyboard()
    )


# ====================================================
# تحليل الصورة بـ Gemini
# ====================================================
async def analyze_image(image_bytes: bytes) -> dict:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                """استخرج بيانات الطالب من الصورة وارجع JSON فقط:
{
  "اسم": "اسم الطالب الكامل",
  "كود": "كود الطالب",
  "المنطقة": "المنطقة أو المدينة",
  "تليفون": "رقم التليفون",
  "ولي الأمر": "رقم ولي الأمر",
  "السنة": "ث1 أو ث2 أو ث3",
  "التخصص": "عام أو أزهر أو بكالوريا - طب...",
  "المواد": "المواد مفصولة بفاصلة"
}
لو مش قادر تقرأ حاجة حطها "". ارجع JSON فقط.""",
            ],
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        text = (response.text or "").strip().replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        logger.error(f"analyze_image: {e}")
        return {}


def build_student_preview(data: dict) -> str:
    """رسالة ملخص البيانات"""
    return (
        f"📋 البيانات:\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"👤 الاسم: {data.get('اسم', '❓')}\n"
        f"🔑 الكود: {data.get('كود', '❓')}\n"
        f"📍 المنطقة: {data.get('المنطقة', '❓')}\n"
        f"📱 التليفون: {data.get('تليفون', '❓')}\n"
        f"👨‍👧 ولي الأمر: {data.get('ولي الأمر', '❓')}\n"
        f"📚 السنة: {data.get('السنة', '❓')}\n"
        f"🎓 التخصص: {data.get('التخصص', '❓')}\n"
        f"📖 المواد: {data.get('المواد', '❓')}\n"
        f"👨‍🏫 المدرسين: {data.get('المدرسين', '❓')}\n"
        f"━━━━━━━━━━━━━━━━\n"
    )


def format_student_info(student: dict) -> str:
    return (
        f"📋 بيانات الطالب\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"👤 الاسم: {student.get('الاسم', '')}\n"
        f"🔑 الكود: {student.get('الكود', '')}\n"
        f"📍 المنطقة: {student.get('المنطقة', '')}\n"
        f"📱 التليفون: {student.get('التليفون', '')}\n"
        f"👨‍👧 ولي الأمر: {student.get('ولي الأمر', '')}\n"
        f"📚 السنة: {student.get('السنة الدراسية', '')}\n"
        f"🎓 التخصص: {student.get('التخصص', '')}\n"
        f"📖 المواد: {student.get('المواد', '')}\n"
        f"👨‍🏫 المدرسين: {student.get('المدرسين', '')}\n"
        f"📅 التسجيل: {student.get('تاريخ التسجيل', '')}\n"
        f"━━━━━━━━━━━━━━━━"
    )


def build_teachers_text(teachers: dict) -> str:
    """بتحول dict المدرسين لنص: عربي/الأستاذ أحمد | كيمياء/الأستاذة سارة"""
    if not teachers:
        return ""
    return " | ".join([f"{subj}/{teacher}" for subj, teacher in teachers.items() if teacher])


def _att_report_text(student: dict, year: str, report: dict) -> str:
    text = (
        f"📄 تقرير حضور ودرجات\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"👤 {student.get('الاسم','')} | 🔑 {student.get('الكود','')} | 📚 {year}\n"
        f"✅ إجمالي مرات الحضور: {report['total_present']}\n"
        f"❌ إجمالي مرات الغياب: {report['total_absent']}\n"
    )
    if report["overall_percentage"] is not None:
        text += (
            f"🎯 نسبة الدرجات: {report['overall_percentage']:.1f}% "
            f"({report['overall_taqdeer']})\n"
        )
    text += "━━━━━━━━━━━━━━━━\n"

    if not report["subjects"]:
        text += "مفيش أي بيانات حضور أو درجات مسجلة للطالب ده لسه.\n"
        return text

    for s in report["subjects"]:
        text += f"\n📖 {s['subject']}"
        if s["teacher"]:
            text += f" — المدرس: {s['teacher']}"
        text += f"\n   ✅ حضر: {s['present']} | ❌ غاب: {s['absent']}\n"
        if s["grades"]:
            grades_str = "، ".join([f"حصة {sess}: {sc:g}/{mx:g}" for sess, sc, mx in s["grades"]])
            text += f"   📝 الدرجات: {grades_str}\n"
    return text


async def _att_after_student_found(update, context, uid, student: dict, from_callback: bool):
    """بعد ما نلاقي الطالب (بالكود أو بالاسم)، بنحدد سنته وبنكمل حسب الوضع (حضور/درجة/تقرير)"""
    year = student.get("السنة الدراسية", "")
    code = student.get("الكود", "")
    name = student.get("الاسم", "")

    if year not in attendance.YEAR_SHEET_IDS:
        text = f"❌ سنة الطالب ({year}) مش معروفة، مقدرش أفتح شيت الحضور بتاعها."
        if from_callback:
            await update.callback_query.edit_message_text(text, reply_markup=back_keyboard())
        else:
            await update.message.reply_text(text, reply_markup=back_keyboard())
        return

    row = attendance.find_row_by_code(year, code)
    if row is None:
        text = f"❌ الطالب {name} (كود {code}) مش مسجل في شيت حضور {year}."
        if from_callback:
            await update.callback_query.edit_message_text(text, reply_markup=back_keyboard())
        else:
            await update.message.reply_text(text, reply_markup=back_keyboard())
        return

    context.user_data["att_student"] = {"code": code, "name": name, "year": year, "row": row}
    mode = context.user_data.get("att_mode")
    user_state.pop(uid, None)

    if mode == "report":
        if from_callback:
            send_func = update.callback_query.edit_message_text
        else:
            send_func = update.message.reply_text
        await _att_send_student_report(send_func, student, year)
        return

    subjects = attendance.get_subjects_for_year(year)
    if not subjects:
        text = "❌ حصل خطأ في قراءة المواد من الشيت"
        if from_callback:
            await update.callback_query.edit_message_text(text, reply_markup=back_keyboard())
        else:
            await update.message.reply_text(text, reply_markup=back_keyboard())
        return

    text = f"👤 {name} ({year})\n\nاختاري المادة:"
    kb = att_subjects_keyboard(subjects)
    if from_callback:
        await update.callback_query.edit_message_text(text, reply_markup=kb)
    else:
        await update.message.reply_text(text, reply_markup=kb)


async def _att_send_student_report(send_func, student: dict, year: str):
    row = attendance.find_row_by_code(year, student.get("الكود", ""))
    if row is None:
        await send_func(
            f"❌ الطالب {student.get('الاسم','')} مش مسجل في شيت حضور {year} لسه.",
            reply_markup=back_keyboard()
        )
        return
    report = attendance.build_report(year, row)
    text = _att_report_text(student, year, report)
    if len(text) > 4000:
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for i, chunk in enumerate(chunks):
            kb = back_keyboard() if i == len(chunks) - 1 else None
            await send_func(chunk, reply_markup=kb)
    else:
        await send_func(text, reply_markup=back_keyboard())


# ====================================================
# التعامل مع الصور
# ====================================================
async def handle_photo(update: Update, context) -> None:
    if not is_admin(update):
        return
    uid = update.effective_user.id

    # وضع الصور المتعددة
    if user_state.get(uid) == MULTI_PHOTO:
        if uid not in temp_data:
            temp_data[uid] = {"pending_photos": []}
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()
        temp_data[uid]["pending_photos"].append(bytes(image_bytes))
        count = len(temp_data[uid]["pending_photos"])
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"✅ حلل الـ {count} صورة", callback_data="process_multi_photos")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="back_main")],
        ])
        await update.message.reply_text(
            f"✅ استلمت صورة رقم {count}\nابعتي أكتر أو اضغطي تحليل 👇",
            reply_markup=keyboard
        )
        return

    # صورة واحدة
    wait_msg = await update.message.reply_text("📸 جاري تحليل الصورة بـ Gemini...\n⏳ ثواني بس...")
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()
        data = await analyze_image(bytes(image_bytes))

        if not data:
            await wait_msg.edit_text("❌ مقدرتش أقرأ البيانات", reply_markup=main_menu_keyboard())
            return

        temp_data[uid] = data
        temp_data[uid]["from_image"] = True
        preview = build_student_preview(data)
        await wait_msg.edit_text(
            preview + "البيانات صح؟ لو في غلط اضغطي على الحقل 👇",
            reply_markup=image_actions_keyboard()
        )
    except Exception as e:
        logger.error(f"handle_photo: {e}")
        await wait_msg.edit_text("❌ حصل خطأ", reply_markup=main_menu_keyboard())


# ====================================================
# تحليل نص المجموعة
# ====================================================
async def parse_bulk_students(text: str) -> list:
    students = []
    blocks = re.split(r'\n---\n|\n\n', text.strip())
    for block in blocks:
        if not block.strip():
            continue
        student = {}
        for line in block.strip().split('\n'):
            if ':' not in line:
                continue
            parts = line.split(':', 1)
            key = parts[0].strip()
            val = parts[1].strip()
            if any(k in key for k in ['اسم', 'الاسم']):
                student['اسم'] = val
            elif any(k in key for k in ['كود', 'الكود']):
                student['كود'] = val
            elif any(k in key for k in ['منطقة', 'المنطقة']):
                student['المنطقة'] = val
            elif any(k in key for k in ['تليفون', 'موبايل']) and 'ولي' not in key:
                student['تليفون'] = val
            elif any(k in key for k in ['ولي', 'الوالد']):
                student['ولي الأمر'] = val
            elif any(k in key for k in ['سنة', 'الصف']):
                student['السنة'] = val
            elif any(k in key for k in ['تخصص']):
                student['التخصص'] = val
            elif any(k in key for k in ['مواد']):
                student['المواد'] = val
            elif any(k in key for k in ['مدرس', 'المدرس']):
                student['المدرسين'] = val
        if student.get('اسم') and student.get('كود'):
            students.append(student)
    return students


# ====================================================
# handle_callback - كل ضغطات الأزرار
# ====================================================
async def handle_callback(update: Update, context) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    uid = query.from_user.id

    # ====== رجوع ======
    if data == "back_main":
        user_state.pop(uid, None)
        temp_data.pop(uid, None)
        user_action.pop(uid, None)
        context.user_data.clear()
        await query.edit_message_text(
            "📚 القائمة الرئيسية\n\nإيه اللي عايزاه تعمليه؟",
            reply_markup=main_menu_keyboard()
        )

    # ====== آخر كود لكل سنة ======
    elif data == "last_codes":
        codes = get_last_code_per_year()
        await query.edit_message_text(
            f"🔢 آخر كود مسجل لكل سنة:\n\n"
            f"1️⃣ ث1: {codes.get('ث1', 'لا يوجد')}\n"
            f"2️⃣ ث2: {codes.get('ث2', 'لا يوجد')}\n"
            f"3️⃣ ث3: {codes.get('ث3', 'لا يوجد')}",
            reply_markup=back_keyboard()
        )

    # ====== تسجيل طالب واحد ======
    elif data == "new_student":
        temp_data[uid] = {}
        user_state[uid] = GET_NAME
        await query.edit_message_text(
            "➕ تسجيل طالب جديد\n\n1️⃣ اكتبي اسم الطالب كامل:",
            reply_markup=back_keyboard()
        )

    # ====== تسجيل من صورة ======
    elif data == "new_from_image":
        await query.edit_message_text(
            "📸 تسجيل من صورة\n\nابعتي صورة واحدة أو اختاري أكتر من صورة:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📸 صورة واحدة - ابعتيها علطول", callback_data="back_main")],
                [InlineKeyboardButton("📸📸 أكتر من صورة معاً", callback_data="start_multi_photo")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
            ])
        )

    # ====== صور متعددة ======
    elif data == "start_multi_photo":
        user_state[uid] = MULTI_PHOTO
        temp_data[uid] = {"pending_photos": []}
        await query.edit_message_text(
            "📸 وضع الصور المتعددة\n\nابعتي الصور واحدة واحدة\nوبعدين اضغطي تحليل ✅",
            reply_markup=back_keyboard()
        )

    elif data == "process_multi_photos":
        photos = temp_data.get(uid, {}).get("pending_photos", [])
        if not photos:
            await query.answer("❌ مفيش صور!", show_alert=True)
            return
        user_state.pop(uid, None)
        await query.edit_message_text(f"⏳ جاري تحليل {len(photos)} صورة...")
        success_count = 0
        results_text = ""
        fail_list = []
        for i, img_bytes in enumerate(photos, 1):
            d = await analyze_image(img_bytes)
            if d and d.get("اسم"):
                s = {
                    "اسم": d.get("اسم", ""), "كود": d.get("كود", ""),
                    "المنطقة": d.get("المنطقة", ""), "تليفون": d.get("تليفون", ""),
                    "ولي الأمر": d.get("ولي الأمر", ""), "السنة": d.get("السنة", ""),
                    "التخصص": d.get("التخصص", ""), "المواد": d.get("المواد", ""),
                    "المدرسين": d.get("المدرسين", ""),
                }
                if add_student(s):
                    success_count += 1
                    name = d.get('اسم', '')
                    code_val = d.get('كود', '')
                    results_text += f"✅ {i}. {name} - {code_val}\n"
                else:
                    fail_list.append(f"صورة {i}")
            else:
                fail_list.append(f"صورة {i} (مش قادر يقرأها)")
        result = f"📊 نتيجة تحليل {len(photos)} صورة:\n\n{results_text}"
        if fail_list:
            result += f"\n❌ فشل: {', '.join(fail_list)}"
        result += f"\n\n✅ تم تسجيل {success_count} طالب!"
        temp_data.pop(uid, None)
        await query.edit_message_text(result, reply_markup=main_menu_keyboard())

    # ====== تسجيل مجموعة ======
    elif data == "new_bulk":
        user_state[uid] = BULK_INPUT
        await query.edit_message_text(
            "👥 تسجيل مجموعة طلاب\n\n"
            "اكتبي بيانات كل طالب:\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "اسم: أحمد محمد علي\n"
            "كود: 2025001\n"
            "منطقة: المنصورة\n"
            "تليفون: 01012345678\n"
            "ولي الأمر: 01098765432\n"
            "سنة: ث2\n"
            "تخصص: عام\n"
            "مواد: عربي, كيمياء, رياضة\n"
            "مدرسين: عربي/أ.محمد | كيمياء/أ.سارة\n"
            "---\n"
            "اسم: محمد علي\n"
            "كود: 2025002\n"
            "━━━━━━━━━━━━━━━━",
            reply_markup=back_keyboard()
        )

    # ====== تأكيد حفظ بيانات الصورة ======
    elif data == "confirm_image_save":
        student_data = temp_data.get(uid, {})
        student_data.pop("from_image", None)
        # بنضيف المدرسين من temp لو موجودين
        teachers = student_data.pop("teachers_dict", {})
        if teachers:
            student_data["المدرسين"] = build_teachers_text(teachers)
        success = add_student(student_data)
        if success:
            await query.edit_message_text(
                "✅ تم تسجيل الطالب من الصورة!\n\n" + build_student_preview(student_data),
                reply_markup=main_menu_keyboard()
            )
        else:
            await query.edit_message_text("❌ حصل خطأ في الحفظ", reply_markup=main_menu_keyboard())
        temp_data.pop(uid, None)

    # ====== تعديل حقل من الصورة ======
    elif data.startswith("imgedit_"):
        field = data.replace("imgedit_", "")
        if field == "الكل":
            user_state[uid] = EDIT_ALL_VALUE
            context.user_data["edit_source"] = "image"
            await query.edit_message_text(
                "📝 اكتبي البيانات الجديدة:\n\n"
                "اسم: ...\nكود: ...\nمنطقة: ...\nتليفون: ...\nولي الأمر: ...\n"
                "سنة: ...\nتخصص: ...\nمواد: ...\nمدرسين: عربي/أ.محمد | كيمياء/أ.سارة",
                reply_markup=back_keyboard()
            )
        elif field == "السنة":
            user_state[uid] = GET_YEAR
            context.user_data["edit_source"] = "image"
            await query.edit_message_text("📚 اختاري السنة الصح:", reply_markup=year_keyboard("year"))
        elif field == "التخصص":
            user_state[uid] = GET_SPECIALIZATION
            context.user_data["edit_source"] = "image"
            await query.edit_message_text("🎓 اختاري التخصص:", reply_markup=specialization_keyboard())
        elif field == "المواد":
            year = temp_data.get(uid, {}).get("السنة", "ث1")
            temp_data[uid]["المواد_مختارة"] = []
            temp_data[uid]["teachers_dict"] = {}
            user_state[uid] = GET_SUBJECTS
            context.user_data["edit_source"] = "image"
            await query.edit_message_text("📖 اختاري المواد:", reply_markup=subjects_keyboard(year, []))
        else:
            field_labels = {"اسم": "الاسم", "كود": "الكود", "المنطقة": "المنطقة",
                          "تليفون": "التليفون", "ولي الأمر": "ولي الأمر"}
            user_state[uid] = IMG_EDIT_FIELD
            context.user_data["img_edit_field"] = field
            await query.edit_message_text(
                f"✏️ اكتبي {field_labels.get(field, field)} الجديد:",
                reply_markup=back_keyboard()
            )

    # ====== البحث بالكود ======
    elif data == "search_student":
        user_state[uid] = SEARCH_CODE
        user_action[uid] = "search"
        await query.edit_message_text("🔎 بحث بالكود\n\n✍️ اكتبي كود الطالب:", reply_markup=back_keyboard())

    # ====== بحث بالاسم ======
    elif data == "search_by_name":
        user_state[uid] = SEARCH_NAME
        await query.edit_message_text("🔍 بحث بالاسم\n\n✍️ اكتبي اسم الطالب أو جزء منه:", reply_markup=back_keyboard())

    # ====== اختيار طالب من نتائج البحث ======
    elif data.startswith("select_student_"):
        code = data.replace("select_student_", "")
        student = search_by_code(code)
        if student:
            await query.edit_message_text(format_student_info(student), reply_markup=student_actions_keyboard(code))

    # ====== تعديل ذكي بضغطة زر ======
    elif data.startswith("smartedit_"):
        code = data.replace("smartedit_", "")
        student = search_by_code(code)
        if student:
            context.user_data["smartedit_student"] = student
            await query.edit_message_text(
                "✏️ اضغطي على الحقل اللي عايزاه تعدليه:\n"
                "(كل زر فيه القيمة الحالية)\n"
                "تقدري تعدلي كذا حقل ورا بعض، وفي الآخر دوسي «✅ خلاص، حفظ»",
                reply_markup=smart_edit_keyboard(student)
            )

    # ====== ضغط على حقل في التعديل الذكي ======
    elif data.startswith("sefield_"):
        # sefield_{code}_{fieldname}
        parts = data.split("_", 2)
        code = parts[1]
        field = parts[2]
        student = context.user_data.get("smartedit_student", {})

        if field == "السنة الدراسية":
            context.user_data["se_code"] = code
            context.user_data["se_field"] = field
            user_state[uid] = GET_YEAR
            context.user_data["edit_source"] = "smartedit"
            await query.edit_message_text("📚 اختاري السنة الجديدة:", reply_markup=year_keyboard("year"))

        elif field == "التخصص":
            context.user_data["se_code"] = code
            context.user_data["se_field"] = field
            user_state[uid] = GET_SPECIALIZATION
            context.user_data["edit_source"] = "smartedit"
            await query.edit_message_text("🎓 اختاري التخصص الجديد:", reply_markup=specialization_keyboard(edit_mode=True))

        elif field == "المواد":
            context.user_data["se_code"] = code
            year = student.get("السنة الدراسية", "ث1")
            temp_data[uid] = {"كود": code, "السنة": year, "المواد_مختارة": [], "teachers_dict": {}, "edit_mode": True}
            user_state[uid] = GET_SUBJECTS
            context.user_data["edit_source"] = "smartedit"
            await query.edit_message_text("📖 اختاري المواد الجديدة:", reply_markup=subjects_keyboard(year, []))

        elif field == "المدرسين":
            # تعديل المدرسين نصياً
            context.user_data["se_code"] = code
            context.user_data["se_field"] = field
            user_state[uid] = EDIT_FIELD_VALUE
            context.user_data["edit_code"] = code
            context.user_data["edit_field"] = field
            context.user_data["edit_source"] = "smartedit"
            await query.edit_message_text(
                f"👨‍🏫 اكتبي المدرسين بالشكل ده:\n"
                f"عربي/أ.محمد | كيمياء/أ.سارة | رياضة/أ.علي\n\n"
                f"القيمة الحالية:\n{student.get('المدرسين', 'لا يوجد')}",
                reply_markup=back_keyboard()
            )

        else:
            # حقل نصي عادي - بنعرض القيمة الحالية ونطلب الجديدة
            current_val = student.get(field, "")
            context.user_data["edit_code"] = code
            context.user_data["edit_field"] = field
            context.user_data["smartedit_student"] = student
            context.user_data["edit_source"] = "smartedit"
            user_state[uid] = EDIT_FIELD_VALUE
            await query.edit_message_text(
                f"✏️ تعديل {field}\n\n"
                f"القيمة الحالية: {current_val}\n\n"
                f"اكتبي القيمة الجديدة:",
                reply_markup=back_keyboard()
            )

    # ====== خلاص التعديل الذكي ======
    elif data.startswith("done_edit_"):
        code = data.replace("done_edit_", "")
        student = search_by_code(code)
        if student:
            await query.edit_message_text(
                "✅ تم حفظ التعديلات!\n\n" + format_student_info(student),
                reply_markup=main_menu_keyboard()
            )
        context.user_data.clear()

    # ====== تعديل عادي ======
    elif data == "edit_student":
        user_state[uid] = SEARCH_CODE
        user_action[uid] = "edit"
        await query.edit_message_text("✏️ تعديل\n\n✍️ اكتبي كود الطالب:", reply_markup=back_keyboard())

    elif data.startswith("edit_") and not data.startswith("editfield_"):
        code = data.replace("edit_", "")
        await query.edit_message_reply_markup(reply_markup=edit_fields_keyboard(code))

    elif data.startswith("editfield_"):
        parts = data.split("_", 2)
        code = parts[1]
        field = parts[2]
        if field == "المواد":
            student = search_by_code(code)
            year = student.get("السنة الدراسية", "ث1") if student else "ث1"
            temp_data[uid] = {"كود": code, "السنة": year, "المواد_مختارة": [], "teachers_dict": {}, "edit_mode": True}
            user_state[uid] = GET_SUBJECTS
            await query.edit_message_text("📖 اختاري المواد الجديدة:", reply_markup=subjects_keyboard(year, []))
        elif field == "التخصص":
            context.user_data["edit_code"] = code
            context.user_data["edit_field"] = field
            await query.edit_message_text("🎓 اختاري التخصص:", reply_markup=specialization_keyboard(edit_mode=True))
        elif field == "السنة الدراسية":
            context.user_data["edit_code"] = code
            context.user_data["edit_field"] = field
            context.user_data["edit_source"] = "field"
            user_state[uid] = GET_YEAR
            await query.edit_message_text("📚 اختاري السنة:", reply_markup=year_keyboard("year"))
        else:
            user_state[uid] = EDIT_FIELD_VALUE
            context.user_data["edit_code"] = code
            context.user_data["edit_field"] = field
            await query.edit_message_text(f"✏️ تعديل {field}\n\n✍️ اكتبي القيمة الجديدة:", reply_markup=back_keyboard())

    # ====== حذف ======
    elif data == "delete_student":
        user_state[uid] = DELETE_CODE
        await query.edit_message_text("🗑️ حذف\n\n✍️ اكتبي كود الطالب:", reply_markup=back_keyboard())

    elif data.startswith("delete_") and not data.startswith("delete_student"):
        code = data.replace("delete_", "")
        student = search_by_code(code)
        name = student.get("الاسم", "") if student else ""
        await query.edit_message_text(
            f"⚠️ متأكدة تحذفي:\n👤 {name} - كود {code}؟",
            reply_markup=confirm_delete_keyboard(code)
        )

    elif data.startswith("confirm_delete_"):
        code = data.replace("confirm_delete_", "")
        success = delete_student(code)
        msg = f"✅ تم حذف الطالب {code}" if success else "❌ حصل خطأ"
        await query.edit_message_text(msg, reply_markup=main_menu_keyboard())

    # ====== إحصائيات ======
    elif data == "stats":
        stats = get_statistics_updated()
        await query.edit_message_text(
            f"📈 إحصائيات مركز الارائج\n\n"
            f"👥 الإجمالي: {stats.get('الإجمالي', 0)}\n"
            f"1️⃣ ث1: {stats.get('ث1', 0)}\n"
            f"2️⃣ ث2: {stats.get('ث2', 0)}\n"
            f"3️⃣ ث3: {stats.get('ث3', 0)}\n\n"
            f"🏫 عام: {stats.get('عام', 0)}\n"
            f"🕌 أزهر: {stats.get('أزهر', 0)}\n"
            f"🎓 بكالوريا: {stats.get('بكالوريا', 0)}",
            reply_markup=back_keyboard()
        )

    # ====== آخر كود لكل سنة ======
    elif data == "last_codes":
        try:
            last = get_last_code_per_year()
            await query.edit_message_text(
                f"🔢 آخر كود مسجل لكل سنة:\n\n"
                f"1️⃣ ث1: {last.get('ث1', 'لا يوجد')}\n"
                f"2️⃣ ث2: {last.get('ث2', 'لا يوجد')}\n"
                f"3️⃣ ث3: {last.get('ث3', 'لا يوجد')}",
                reply_markup=back_keyboard()
            )
        except Exception as e:
            await query.edit_message_text("❌ حصل خطأ", reply_markup=back_keyboard())

    # ====== إحصائيات المدرسين - عرض كل المدرسين ======
    elif data == "teacher_stats":
        await query.edit_message_text(
            "👨‍🏫 إحصائيات المدرسين\n\n"
            "إيه اللي عايزاه؟",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 كل المدرسين وعدد طلابهم", callback_data="all_teachers")],
                [InlineKeyboardButton("🔍 بحث عن مدرس معين", callback_data="search_teacher")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
            ])
        )

    # ====== كل المدرسين ======
    elif data == "all_teachers":
        await query.edit_message_text("⏳ جاري جلب البيانات...")
        teachers = get_teacher_stats()
        if not teachers:
            await query.edit_message_text(
                "📭 مفيش بيانات مدرسين مسجلة",
                reply_markup=back_keyboard()
            )
            return

        text = "👨‍🏫 كل المدرسين وعدد طلابهم:\n━━━━━━━━━━━━━━━━\n"
        for i, (teacher, students) in enumerate(teachers.items(), 1):
            text += f"{i}. {teacher}: {len(students)} طالب\n"

        # لو الرسالة طويلة نقسمها
        if len(text) > 4000:
            chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
            await query.edit_message_text(chunks[0])
            for chunk in chunks[1:]:
                await context.bot.send_message(chat_id=query.message.chat_id, text=chunk)
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="✅ انتهى",
                reply_markup=back_keyboard()
            )
        else:
            await query.edit_message_text(text, reply_markup=back_keyboard())

    # ====== بحث عن مدرس معين ======
    elif data == "search_teacher":
        user_state[uid] = SEARCH_TEACHER
        await query.edit_message_text(
            "🔍 بحث عن مدرس\n\n✍️ اكتبي اسم المدرس أو جزء منه:",
            reply_markup=back_keyboard()
        )

    # ====== قائمة الحضور والغياب والدرجات ======
    elif data == "att_menu":
        context.user_data.pop("att_mode", None)
        context.user_data.pop("att_student", None)
        context.user_data.pop("att_subject", None)
        context.user_data.pop("att_session", None)
        await query.edit_message_text(
            "📅 الحضور والغياب والدرجات\n\nإيه اللي عايزاه؟",
            reply_markup=attendance_menu_keyboard()
        )

    elif data in ("att_start_attendance", "att_start_grade", "att_start_report"):
        mode = {"att_start_attendance": "attendance", "att_start_grade": "grade", "att_start_report": "report"}[data]
        context.user_data["att_mode"] = mode
        user_state[uid] = ATT_SEARCH
        await query.edit_message_text(
            "🔍 اكتبي اسم الطالب أو الكود بتاعه:",
            reply_markup=back_keyboard()
        )

    # ====== اختيار طالب من نتائج بحث الحضور ======
    elif data.startswith("att_pick_"):
        code = data.replace("att_pick_", "")
        student = search_by_code(code)
        if not student:
            await query.edit_message_text("❌ الطالب مش موجود", reply_markup=back_keyboard())
            return
        await _att_after_student_found(update, context, uid, student, from_callback=True)

    # ====== اختيار المادة ======
    elif data.startswith("att_subj_"):
        subject = data[len("att_subj_"):]
        student = context.user_data.get("att_student", {})
        year = student.get("year")
        row = student.get("row")
        context.user_data["att_subject"] = subject

        teacher = attendance.get_teacher(year, row, subject)
        if not teacher:
            user_state[uid] = ATT_TEACHER_NAME
            await query.edit_message_text(
                f"المادة دي ({subject}) لسه مفيهاش مدرس مسجل لـ {student.get('name','')}.\n"
                f"✍️ اكتبي اسم المدرس:",
                reply_markup=back_keyboard()
            )
            return

        mode = context.user_data.get("att_mode")
        if mode == "grade":
            user_state[uid] = ATT_GRADE_SCORE
            await query.edit_message_text(
                f"📖 {subject} — أي حصة؟ اختاري رقمها الأول 👇\nهبعتلك تسأل عن الدرجة بعد اختيار الحصة.",
                reply_markup=att_sessions_keyboard()
            )
        else:
            await query.edit_message_text(
                f"📖 {subject} — اختاري رقم الحصة:",
                reply_markup=att_sessions_keyboard()
            )

    # ====== اختيار الحصة ======
    elif data.startswith("att_sess_"):
        session = int(data.replace("att_sess_", ""))
        context.user_data["att_session"] = session
        mode = context.user_data.get("att_mode")
        subject = context.user_data.get("att_subject")
        if mode == "grade":
            user_state[uid] = ATT_GRADE_SCORE
            await query.edit_message_text(f"📝 {subject} - حصة {session}\n\n✍️ الطالب جاب كام؟")
        else:
            await query.edit_message_text(
                f"📖 {subject} - حصة {session}\n\nحاضر ولا غايب؟",
                reply_markup=att_present_absent_keyboard()
            )

    elif data == "att_absent":
        student = context.user_data.get("att_student", {})
        subject = context.user_data.get("att_subject")
        session = context.user_data.get("att_session")
        attendance.mark_session(student.get("year"), student.get("row"), subject, session, "غ")
        await query.edit_message_text(
            f"✅ اتسجل: {student.get('name','')} غايب في {subject} - حصة {session}",
            reply_markup=att_done_keyboard()
        )

    elif data == "att_present":
        await query.edit_message_text(
            "فيه امتحان الحصة دي؟",
            reply_markup=att_exam_keyboard()
        )

    elif data == "att_exam_no":
        student = context.user_data.get("att_student", {})
        subject = context.user_data.get("att_subject")
        session = context.user_data.get("att_session")
        attendance.mark_session(student.get("year"), student.get("row"), subject, session, "✓")
        await query.edit_message_text(
            f"✅ اتسجل: {student.get('name','')} حاضر في {subject} - حصة {session}",
            reply_markup=att_done_keyboard()
        )

    elif data == "att_exam_yes":
        user_state[uid] = ATT_GRADE_SCORE
        await query.edit_message_text("✍️ الطالب جاب كام؟")

    elif data == "att_again":
        student = context.user_data.get("att_student", {})
        year = student.get("year")
        subjects = attendance.get_subjects_for_year(year) if year else []
        if not subjects:
            await query.edit_message_text("❌ حصل خطأ في قراءة المواد", reply_markup=back_keyboard())
            return
        await query.edit_message_text(
            f"👤 {student.get('name','')}\n\nاختاري المادة:",
            reply_markup=att_subjects_keyboard(subjects)
        )

    # ====== تعديل كل البيانات بعرض الحالية والضغط ======
    elif data.startswith("editall_"):
        code = data.replace("editall_", "")
        student = search_by_code(code)
        if not student:
            await query.edit_message_text("❌ مش موجود", reply_markup=back_keyboard())
            return
        context.user_data["editall_code"] = code
        # بنعرض البيانات الحالية وأزرار لكل حقل
        keyboard = [
            [InlineKeyboardButton(
                f"👤 الاسم: {student.get('الاسم','')[:20]}",
                callback_data=f"editone_{code}_الاسم"
            )],
            [InlineKeyboardButton(
                f"📍 المنطقة: {student.get('المنطقة','')[:20]}",
                callback_data=f"editone_{code}_المنطقة"
            )],
            [InlineKeyboardButton(
                f"📱 التليفون: {student.get('التليفون','')}",
                callback_data=f"editone_{code}_التليفون"
            )],
            [InlineKeyboardButton(
                f"👨‍👧 ولي الأمر: {student.get('ولي الأمر','')}",
                callback_data=f"editone_{code}_ولي الأمر"
            )],
            [InlineKeyboardButton(
                f"📚 السنة: {student.get('السنة الدراسية','')}",
                callback_data=f"editone_{code}_السنة الدراسية"
            )],
            [InlineKeyboardButton(
                f"🎓 التخصص: {student.get('التخصص','')[:15]}",
                callback_data=f"editone_{code}_التخصص"
            )],
            [InlineKeyboardButton(
                f"📖 المواد: {student.get('المواد','')[:20]}...",
                callback_data=f"editone_{code}_المواد"
            )],
            [InlineKeyboardButton(
                f"👨‍🏫 المدرسين: {student.get('المدرسين','')[:20]}",
                callback_data=f"editone_{code}_المدرسين"
            )],
            [InlineKeyboardButton("✅ خلاص، حفظ", callback_data="back_main")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
        ]
        await query.edit_message_text(
            f"📝 تعديل بيانات الطالب\n"
            f"🔑 الكود: {code}\n\n"
            f"اضغطي على الحقل اللي عايزاه تعدليه:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ====== تعديل حقل واحد بالضغط ======
    elif data.startswith("editone_"):
        parts = data.split("_", 2)
        code = parts[1]
        field = parts[2]
        context.user_data["editone_code"] = code
        context.user_data["editone_field"] = field

        if field == "المواد":
            student = search_by_code(code)
            year = student.get("السنة الدراسية", "ث1") if student else "ث1"
            temp_data[uid] = {"كود": code, "السنة": year, "المواد_مختارة": [], "edit_mode": True}
            user_state[uid] = GET_SUBJECTS
            await query.edit_message_text(
                "📖 اختاري المواد الجديدة:",
                reply_markup=subjects_keyboard(year, [])
            )
        elif field == "السنة الدراسية":
            user_state[uid] = EDIT_ONE_FIELD
            await query.edit_message_text(
                "📚 اختاري السنة الجديدة:",
                reply_markup=year_keyboard("editoneyear")
            )
        elif field == "التخصص":
            user_state[uid] = EDIT_ONE_FIELD
            await query.edit_message_text(
                "🎓 اختاري التخصص الجديد:",
                reply_markup=specialization_keyboard(edit_mode=True)
            )
        else:
            # حقل نصي - بنطلب القيمة الجديدة مع عرض القديمة
            student = search_by_code(code)
            current_val = student.get(field, '') if student else ''
            user_state[uid] = EDIT_ONE_FIELD
            await query.edit_message_text(
                f"✏️ تعديل {field}\n\n"
                f"القيمة الحالية: {current_val}\n\n"
                f"✍️ اكتبي القيمة الجديدة:",
                reply_markup=back_keyboard()
            )

    # ====== year callback لـ editone ======
    elif data.startswith("editoneyear_"):
        year = data.replace("editoneyear_", "")
        code = context.user_data.get("editone_code")
        success = update_student(code, "السنة الدراسية", year)
        user_state.pop(uid, None)
        msg = f"✅ تم تعديل السنة: {year}" if success else "❌ حصل خطأ"
        # نرجع لشاشة التعديل الكامل
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 تعديل حقل تاني", callback_data=f"editall_{code}")],
            [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_main")],
        ]))

    # ====== التقارير ======
    elif data == "reports":
        await query.edit_message_text("📊 التقارير\n\nإيه نوع التقرير؟", reply_markup=report_type_keyboard())

    # ====== اختيار السنة ======
    elif data.startswith("year_"):
        year = data.replace("year_", "")
        edit_source = context.user_data.get("edit_source")

        if uid not in temp_data:
            temp_data[uid] = {}
        temp_data[uid]["السنة"] = year
        temp_data[uid]["المواد_مختارة"] = []
        temp_data[uid]["teachers_dict"] = {}

        if edit_source in ["image", "smartedit"]:
            # من الصورة أو التعديل الذكي
            user_state[uid] = GET_SUBJECTS
            await query.edit_message_text(
                f"✅ السنة: {year}\n\n📖 اختاري المواد:",
                reply_markup=subjects_keyboard(year, [])
            )
        elif edit_source == "field":
            # تعديل السنة فقط
            code = context.user_data.get("edit_code")
            success = update_student(code, "السنة الدراسية", year)
            msg = f"✅ تم تعديل السنة: {year}" if success else "❌ حصل خطأ"
            # نعرض الطالب المحدث
            student = search_by_code(code)
            if student and success:
                context.user_data["smartedit_student"] = student
                await query.edit_message_text(
                    f"✅ تم تعديل السنة: {year}\n\nإيه اللي عايزاه تعدله كمان؟",
                    reply_markup=smart_edit_keyboard(student)
                )
            else:
                await query.edit_message_text(msg, reply_markup=main_menu_keyboard())
            context.user_data.pop("edit_source", None)
        else:
            user_state[uid] = GET_SUBJECTS
            await query.edit_message_text(
                f"✅ السنة: {year}\n\n7️⃣ اختاري المواد ✅:",
                reply_markup=subjects_keyboard(year, [])
            )

    # ====== اختيار/إلغاء مادة ======
    elif data.startswith("subj_"):
        subject = data.replace("subj_", "")
        if uid not in temp_data:
            temp_data[uid] = {}
        selected = temp_data[uid].get("المواد_مختارة", [])
        teachers = temp_data[uid].get("teachers_dict", {})

        if subject in selected:
            selected.remove(subject)
            teachers.pop(subject, None)
        else:
            selected.append(subject)

        temp_data[uid]["المواد_مختارة"] = selected
        temp_data[uid]["teachers_dict"] = teachers
        year = temp_data[uid].get("السنة", "ث1")
        await query.edit_message_reply_markup(reply_markup=subjects_keyboard(year, selected, teachers))

    # ====== تأكيد المواد - يطلب المدرسين ======
    elif data == "confirm_subjects":
        uid_data = temp_data.get(uid, {})
        selected = uid_data.get("المواد_مختارة", [])

        if not selected:
            await query.answer("⚠️ لازم تختاري مادة واحدة على الأقل!", show_alert=True)
            return

        # بنحفظ المواد ونبدأ طلب المدرسين
        uid_data["المواد"] = ", ".join(selected)
        uid_data["pending_teachers"] = list(selected)  # قائمة المواد اللي لسه محتاجة مدرس
        uid_data["teachers_dict"] = uid_data.get("teachers_dict", {})

        await _process_next_teacher(update, context, uid, uid_data, from_callback=True)

    # ====== تخطي مدرس مادة ======
    elif data.startswith("skip_teacher_"):
        subject = data.replace("skip_teacher_", "")
        uid_data = temp_data.get(uid, {})
        if subject in uid_data.get("pending_teachers", []):
            uid_data["pending_teachers"].remove(subject)
        await _process_next_teacher(update, context, uid, uid_data, from_callback=True)

    # ====== اختيار مدرس من الأزرار ======
    elif data.startswith("pick_teacher_"):
        uid_data = temp_data.get(uid, {})
        pending  = uid_data.get("pending_teachers", [])
        subject  = pending[0] if pending else ""
        # اسم المدرس = ما بعد "pick_teacher_{subject}_"
        prefix  = f"pick_teacher_{subject}_"
        teacher = data[len(prefix):] if data.startswith(prefix) else data.replace("pick_teacher_", "")
        if subject:
            uid_data.setdefault("teachers_dict", {})[subject] = teacher
            if subject in pending:
                pending.remove(subject)
        await _process_next_teacher(update, context, uid, uid_data, from_callback=True)

    # ====== كتابة اسم مدرس يدوياً ======
    elif data.startswith("write_teacher_"):
        subject = data[len("write_teacher_"):]
        context.user_data["writing_teacher_for"] = subject
        user_state[uid] = GET_TEACHER
        await query.edit_message_text(
            f"✍️ اكتبي اسم مدرس مادة: {subject}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⏭️ تخطي", callback_data=f"skip_teacher_{subject}")
            ]])
        )

    # ====== spec_ و bacc_ ======
    elif data.startswith("spec_") or data.startswith("editspec_"):
        is_edit = data.startswith("editspec_")
        spec = data.replace("editspec_", "").replace("spec_", "")
        edit_source = context.user_data.get("edit_source")

        if spec == "بكالوريا":
            await query.edit_message_text(
                "🎓 اختاري نوع البكالوريا:",
                reply_markup=baccalaureate_keyboard(edit_mode=is_edit)
            )
        else:
            if edit_source == "smartedit":
                code = context.user_data.get("se_code", context.user_data.get("edit_code"))
                success = update_student(code, "التخصص", spec)
                student = search_by_code(code)
                if student:
                    context.user_data["smartedit_student"] = student
                    await query.edit_message_text(
                        f"✅ تم تعديل التخصص: {spec}\n\nإيه اللي عايزاه تعدله كمان؟",
                        reply_markup=smart_edit_keyboard(student)
                    )
                context.user_data.pop("edit_source", None)
            elif edit_source == "image":
                temp_data[uid]["التخصص"] = spec
                context.user_data.pop("edit_source", None)
                preview = build_student_preview(temp_data[uid])
                await query.edit_message_text(preview + "البيانات صح؟", reply_markup=image_actions_keyboard())
            else:
                if uid not in temp_data:
                    temp_data[uid] = {}
                temp_data[uid]["التخصص"] = spec
                user_state[uid] = GET_YEAR
                await query.edit_message_text(
                    f"✅ التخصص: {spec}\n\n6️⃣ إيه السنة الدراسية؟",
                    reply_markup=year_keyboard("year")
                )

    elif data.startswith("bacc_") or data.startswith("editbacc_"):
        is_edit = data.startswith("editbacc_")
        bacc_type = data.replace("editbacc_", "").replace("bacc_", "")
        full_spec = f"بكالوريا - {bacc_type}"
        edit_source = context.user_data.get("edit_source")

        if edit_source == "smartedit":
            code = context.user_data.get("se_code", context.user_data.get("edit_code"))
            success = update_student(code, "التخصص", full_spec)
            student = search_by_code(code)
            if student:
                context.user_data["smartedit_student"] = student
                await query.edit_message_text(
                    f"✅ تم تعديل التخصص: {full_spec}\n\nإيه اللي عايزاه تعدله كمان؟",
                    reply_markup=smart_edit_keyboard(student)
                )
            context.user_data.pop("edit_source", None)
        elif edit_source == "image":
            temp_data[uid]["التخصص"] = full_spec
            context.user_data.pop("edit_source", None)
            preview = build_student_preview(temp_data[uid])
            await query.edit_message_text(preview + "البيانات صح؟", reply_markup=image_actions_keyboard())
        else:
            if uid not in temp_data:
                temp_data[uid] = {}
            temp_data[uid]["التخصص"] = full_spec
            user_state[uid] = GET_YEAR
            await query.edit_message_text(
                f"✅ التخصص: {full_spec}\n\n6️⃣ إيه السنة الدراسية؟",
                reply_markup=year_keyboard("year")
            )

    # ====== التقارير ======
    elif data.startswith("report_"):
        year_filter = data.replace("report_", "")
        label = "كل الطلاب" if year_filter == "all" else year_filter
        await query.edit_message_text(
            f"📊 تقرير {label}\n\nإيه اللي عايزاه يظهر؟",
            reply_markup=report_content_keyboard(year_filter)
        )

    elif data.startswith("rpt_"):
        parts = data.split("_", 2)
        year = parts[1]
        content_type = parts[2]
        year_param = None if year == "all" else year
        students = get_students_by_year(year_param)
        label = "كل الطلاب" if year == "all" else year

        if not students:
            await query.edit_message_text("📭 مفيش طلاب", reply_markup=back_keyboard())
            return

        if content_type == "pdf":
            await query.edit_message_text(f"⏳ جاري إنشاء PDF لـ {label}...")
            pdf_path = generate_pdf(students, label)
            with open(pdf_path, 'rb') as f:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=f,
                    filename=f"تقرير_{label}.pdf",
                    caption=f"📄 تقرير {label} - {len(students)} طالب"
                )
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="✅ تم إرسال PDF",
                reply_markup=main_menu_keyboard()
            )
            return

        report = f"📊 تقرير {label}\nالعدد: {len(students)} طالب\n━━━━━━━━━━━━━━━━\n"
        for i, s in enumerate(students, 1):
            if content_type == "names":
                report += f"{i}. {s.get('الاسم', '')}\n"
            elif content_type == "phones":
                report += f"{i}. {s.get('الاسم', '')}\n   📱 {s.get('التليفون', '')} | 👨‍👧 {s.get('ولي الأمر', '')}\n"
            elif content_type == "subjects":
                report += (
                    f"{i}. {s.get('الاسم', '')} ({s.get('السنة الدراسية', '')} - {s.get('التخصص', '')})\n"
                    f"   📖 {s.get('المواد', '')}\n"
                    f"   👨‍🏫 {s.get('المدرسين', '')}\n"
                )
            elif content_type == "all":
                report += (
                    f"{i}. 👤 {s.get('الاسم', '')} | 🔑 {s.get('الكود', '')}\n"
                    f"   📍 {s.get('المنطقة', '')} | 📱 {s.get('التليفون', '')}\n"
                    f"   📚 {s.get('السنة الدراسية', '')} | 🎓 {s.get('التخصص', '')}\n"
                    f"   📖 {s.get('المواد', '')}\n"
                    f"   👨‍🏫 {s.get('المدرسين', '')}\n"
                )
            if i % 5 == 0:
                report += "━━━━━━━━━━━━━━━━\n"

        if len(report) > 4000:
            chunks = [report[i:i+4000] for i in range(0, len(report), 4000)]
            await query.edit_message_text(chunks[0])
            for chunk in chunks[1:]:
                await context.bot.send_message(chat_id=query.message.chat_id, text=chunk)
            await context.bot.send_message(
                chat_id=query.message.chat_id, text="✅ انتهى التقرير",
                reply_markup=main_menu_keyboard()
            )
        else:
            await query.edit_message_text(report, reply_markup=main_menu_keyboard())


    # ====== PDF تقرير مدرس مرتب بالسنة ======
    elif data == "teacher_pdf":
        results = context.user_data.get("teacher_search_results", {})
        query_text = context.user_data.get("teacher_search_query", "مدرس")
        if not results:
            await query.answer("مفيش بيانات، ابحثي عن المدرس أول", show_alert=True)
            return
        await query.edit_message_text("⏳ جاري إنشاء PDF...")
        import os, tempfile
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
            from reportlab.lib.styles import ParagraphStyle
            from reportlab.lib import colors
            from reportlab.lib.units import cm
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            import arabic_reshaper
            from bidi.algorithm import get_display

            def ar(t): return get_display(arabic_reshaper.reshape(str(t)))
            font_path = "Amiri-Regular.ttf"
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont("Amiri", font_path))
                fn = "Amiri"
            else:
                fn = "Helvetica"

            pdf_path = tempfile.mktemp(suffix=".pdf")
            doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                                    rightMargin=1.5*cm, leftMargin=1.5*cm,
                                    topMargin=2*cm, bottomMargin=2*cm)
            story = []
            t1 = ParagraphStyle("t1", fontName=fn, fontSize=16, alignment=1, spaceAfter=8)
            t2 = ParagraphStyle("t2", fontName=fn, fontSize=13, alignment=1, spaceAfter=6)
            t3 = ParagraphStyle("t3", fontName=fn, fontSize=11, alignment=1, spaceAfter=4)
            t4 = ParagraphStyle("t4", fontName=fn, fontSize=10, alignment=1, spaceAfter=3)

            def make_table(rows_data, col_w):
                t = Table(rows_data, colWidths=col_w, repeatRows=1)
                t.setStyle(TableStyle([
                    ("BACKGROUND",     (0,0),(-1,0),  colors.HexColor("#2c3e50")),
                    ("TEXTCOLOR",      (0,0),(-1,0),  colors.white),
                    ("FONTNAME",       (0,0),(-1,-1), fn),
                    ("FONTSIZE",       (0,0),(-1,0),  9),
                    ("FONTSIZE",       (0,1),(-1,-1), 8),
                    ("ALIGN",          (0,0),(-1,-1), "CENTER"),
                    ("VALIGN",         (0,0),(-1,-1), "MIDDLE"),
                    ("ROWBACKGROUNDS", (0,1),(-1,-1), [colors.white, colors.HexColor("#f2f2f2")]),
                    ("GRID",           (0,0),(-1,-1), 0.4, colors.grey),
                    ("TOPPADDING",     (0,0),(-1,-1), 3),
                    ("BOTTOMPADDING",  (0,0),(-1,-1), 3),
                ]))
                return t

            col_w = [0.7*cm, 3.2*cm, 1.6*cm, 2.3*cm, 2.3*cm, 1.8*cm, 2*cm, 1.8*cm]
            hdrs  = [ar(h) for h in ["#","الاسم","الكود","التليفون","ولي الامر","المنطقة","التخصص","المادة"]]
            first_teacher = True

            for teacher, data_val in results.items():
                if not first_teacher:
                    story.append(PageBreak())
                first_teacher = False
                if isinstance(data_val, dict) and "طلاب" in data_val:
                    students = data_val["طلاب"]
                    by_year  = data_val.get("بالسنة", {})
                    by_spec  = data_val.get("بالتخصص", {})
                else:
                    students = data_val
                    by_year  = {}
                    by_spec  = {}

                story.append(Paragraph(ar(f"تقرير طلاب: {teacher}"), t1))
                story.append(Paragraph(ar(f"اجمالي الطلاب: {len(students)}"), t2))
                if by_year:
                    story.append(Paragraph(ar(
                        f"ث1: {by_year.get('ث1',0)}  |  ث2: {by_year.get('ث2',0)}  |  ث3: {by_year.get('ث3',0)}"
                    ), t3))
                if by_spec:
                    story.append(Paragraph(ar(
                        f"عام: {by_spec.get('عام',0)}  |  ازهر: {by_spec.get('أزهر',0)}  |  بكالوريا: {by_spec.get('بكالوريا',0)}"
                    ), t3))
                story.append(Spacer(1, 0.4*cm))

                for year_label in ["ث1", "ث2", "ث3"]:
                    yr_students = [s for s in students if s.get("السنة","") == year_label]
                    if not yr_students:
                        continue
                    sp_count = {"عام": 0, "أزهر": 0, "بكالوريا": 0}
                    for s in yr_students:
                        sp = s.get("التخصص","")
                        if "بكالوريا" in sp: sp_count["بكالوريا"] += 1
                        elif sp == "أزهر":   sp_count["أزهر"] += 1
                        elif sp == "عام":    sp_count["عام"] += 1

                    story.append(Paragraph(ar(f"سنة {year_label}"), t2))
                    story.append(Paragraph(ar(
                        f"عدد الطلاب: {len(yr_students)}  |  "
                        f"عام: {sp_count['عام']}  |  "
                        f"ازهر: {sp_count['أزهر']}  |  "
                        f"بكالوريا: {sp_count['بكالوريا']}"
                    ), t4))
                    story.append(Spacer(1, 0.2*cm))
                    rows = [hdrs]
                    for i, s in enumerate(yr_students, 1):
                        rows.append([ar(i), ar(s.get("اسم","")), ar(s.get("كود","")),
                                     ar(s.get("التليفون","")), ar(s.get("ولي_الامر","")),
                                     ar(s.get("المنطقة","")), ar(s.get("التخصص","")), ar(s.get("المادة",""))])
                    story.append(make_table(rows, col_w))
                    story.append(Spacer(1, 0.5*cm))

            doc.build(story)
            with open(pdf_path, "rb") as fp:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=fp,
                    filename=f"تقرير_{query_text}.pdf",
                    caption=f"تقرير طلاب: {query_text}"
                )
            os.remove(pdf_path)
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="تم ارسال PDF",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("بحث عن مدرس تاني", callback_data="search_teacher")],
                    [InlineKeyboardButton("القائمة الرئيسية", callback_data="back_main")],
                ])
            )
        except Exception as e:
            print(f"خطا في PDF: {e}")
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"حصل خطا في انشاء PDF: {e}",
                reply_markup=back_keyboard()
            )



# ====================================================
# دالة مساعدة لمعالجة المدرسين
# ====================================================
async def _process_next_teacher(update, context, uid, uid_data, from_callback=False):
    """بتعالج طلب المدرس التالي أو تحفظ الطالب لو خلصنا"""
    pending = uid_data.get("pending_teachers", [])

    if pending:
        next_subject = pending[0]
        user_state[uid] = GET_TEACHER
        text = f"👨‍🏫 اختاري مدرس مادة:\n📖 {next_subject}"
        kb = teachers_keyboard(next_subject)
        if from_callback:
            await update.callback_query.edit_message_text(text, reply_markup=kb)
        else:
            await update.message.reply_text(text, reply_markup=kb)
    else:
        # خلصنا كل المواد - نحفظ الطالب
        user_state.pop(uid, None)
        teachers = uid_data.get("teachers_dict", {})
        uid_data["المدرسين"] = build_teachers_text(teachers)

        edit_source = context.user_data.get("edit_source")
        edit_mode = uid_data.get("edit_mode")

        if edit_mode:
            # تعديل مواد ومدرسين طالب موجود
            code = uid_data.get("كود")
            update_student(code, "المواد", uid_data["المواد"])
            update_student(code, "المدرسين", uid_data["المدرسين"])
            student = search_by_code(code)
            msg = f"✅ تم تعديل المواد والمدرسين!\n\n📖 {uid_data['المواد']}\n👨‍🏫 {uid_data['المدرسين']}"
            if from_callback:
                if student and context.user_data.get("edit_source") == "smartedit":
                    context.user_data["smartedit_student"] = student
                    await update.callback_query.edit_message_text(
                        msg + "\n\nإيه اللي عايزاه تعدله كمان؟",
                        reply_markup=smart_edit_keyboard(student)
                    )
                else:
                    await update.callback_query.edit_message_text(msg, reply_markup=main_menu_keyboard())
            else:
                await update.message.reply_text(msg, reply_markup=main_menu_keyboard())
            temp_data.pop(uid, None)

        elif edit_source == "image":
            # تعديل مواد من الصورة
            temp_data[uid]["المواد"] = uid_data["المواد"]
            temp_data[uid]["المدرسين"] = uid_data["المدرسين"]
            context.user_data.pop("edit_source", None)
            preview = build_student_preview(temp_data[uid])
            if from_callback:
                await update.callback_query.edit_message_text(
                    "✅ تم تحديث المواد والمدرسين!\n\n" + preview + "البيانات صح؟",
                    reply_markup=image_actions_keyboard()
                )
            else:
                await update.message.reply_text(
                    "✅ تم تحديث المواد والمدرسين!\n\n" + preview + "البيانات صح؟",
                    reply_markup=image_actions_keyboard()
                )

        else:
            # تسجيل جديد
            student_to_save = {
                "اسم":       uid_data.get("اسم", ""),
                "كود":       uid_data.get("كود", ""),
                "المنطقة":  uid_data.get("المنطقة", ""),
                "تليفون":    uid_data.get("تليفون", ""),
                "ولي الأمر": uid_data.get("ولي الأمر", ""),
                "السنة":     uid_data.get("السنة", ""),
                "التخصص":    uid_data.get("التخصص", ""),
                "المواد":    uid_data.get("المواد", ""),
                "المدرسين":  uid_data.get("المدرسين", ""),
            }
            success = add_student(student_to_save)
            if success:
                msg = (
                    f"✅ تم تسجيل الطالب بنجاح!\n\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"👤 {student_to_save['اسم']} | 🔑 {student_to_save['كود']}\n"
                    f"📍 {student_to_save['المنطقة']} | 📱 {student_to_save['تليفون']}\n"
                    f"📚 {student_to_save['السنة']} | 🎓 {student_to_save['التخصص']}\n"
                    f"📖 {student_to_save['المواد']}\n"
                    f"👨‍🏫 {student_to_save['المدرسين']}\n"
                    f"━━━━━━━━━━━━━━━━\n✅ تم الحفظ"
                )
            else:
                msg = "❌ حصل خطأ في الحفظ"

            if from_callback:
                await update.callback_query.edit_message_text(msg, reply_markup=main_menu_keyboard())
            else:
                await update.message.reply_text(msg, reply_markup=main_menu_keyboard())
            temp_data.pop(uid, None)


# ====================================================
# handle_text - الرسائل النصية
# ====================================================
async def handle_text(update: Update, context) -> None:
    if not is_admin(update):
        return
    uid = update.effective_user.id
    text = update.message.text.strip()
    state = user_state.get(uid)

    # ====== خطوات التسجيل ======
    if state == GET_NAME:
        temp_data[uid]["اسم"] = text
        user_state[uid] = GET_CODE
        await update.message.reply_text(f"✅ الاسم: {text}\n\n2️⃣ اكتبي كود الطالب:", reply_markup=back_keyboard())

    elif state == GET_CODE:
        existing = search_by_code(text)
        if existing:
            await update.message.reply_text(
                f"⚠️ الكود {text} موجود!\nالطالب: {existing.get('الاسم', '')}\n\n✍️ اكتبي كود تاني:",
                reply_markup=back_keyboard()
            )
            return
        temp_data[uid]["كود"] = text
        user_state[uid] = GET_AREA
        await update.message.reply_text(f"✅ الكود: {text}\n\n3️⃣ اكتبي المنطقة:", reply_markup=back_keyboard())

    elif state == GET_AREA:
        temp_data[uid]["المنطقة"] = text
        user_state[uid] = GET_PHONE
        await update.message.reply_text(f"✅ المنطقة: {text}\n\n4️⃣ اكتبي رقم تليفون الطالب:", reply_markup=back_keyboard())

    elif state == GET_PHONE:
        temp_data[uid]["تليفون"] = text
        user_state[uid] = GET_PARENT_PHONE
        await update.message.reply_text(f"✅ التليفون: {text}\n\n5️⃣ اكتبي رقم تليفون ولي الأمر:", reply_markup=back_keyboard())

    elif state == GET_PARENT_PHONE:
        temp_data[uid]["ولي الأمر"] = text
        user_state[uid] = GET_SPECIALIZATION
        await update.message.reply_text(f"✅ ولي الأمر: {text}\n\n6️⃣ إيه تخصص الطالب؟", reply_markup=specialization_keyboard())

    # ====== اسم المدرس (كتابة يدوية) ======
    elif state == GET_TEACHER:
        uid_data = temp_data.get(uid, {})
        pending  = uid_data.get("pending_teachers", [])
        writing_for = context.user_data.pop("writing_teacher_for", None)
        current_subject = writing_for if writing_for else (pending[0] if pending else None)
        if current_subject:
            uid_data.setdefault("teachers_dict", {})[current_subject] = text
            if current_subject in pending:
                pending.remove(current_subject)
        await _process_next_teacher(update, context, uid, uid_data, from_callback=False)

    # ====== البحث بالكود ======
    elif state == SEARCH_CODE:
        action = user_action.get(uid, "search")
        student = search_by_code(text)
        if not student:
            await update.message.reply_text(f"❌ مفيش طالب بالكود {text}", reply_markup=back_keyboard())
            return
        info = format_student_info(student)
        code = student.get("الكود", "")
        user_state.pop(uid, None)
        if action == "edit":
            context.user_data["smartedit_student"] = student
            await update.message.reply_text(
                info + "\n\nاضغطي على الحقل اللي عايزاه تعدليه (تقدري تعدلي كذا حقل ورا بعض):",
                reply_markup=smart_edit_keyboard(student)
            )
        else:
            await update.message.reply_text(info, reply_markup=student_actions_keyboard(code))

    # ====== البحث بالاسم ======
    elif state == SEARCH_NAME:
        results = search_by_name(text)
        user_state.pop(uid, None)
        if not results:
            await update.message.reply_text(f"❌ مفيش طالب بالاسم '{text}'", reply_markup=back_keyboard())
            return
        if len(results) == 1:
            student = results[0]
            await update.message.reply_text(
                format_student_info(student),
                reply_markup=student_actions_keyboard(student.get("الكود", ""))
            )
        else:
            keyboard = []
            for s in results[:10]:
                keyboard.append([InlineKeyboardButton(
                    f"👤 {s.get('الاسم', '')} | {s.get('السنة الدراسية', '')} | كود: {s.get('الكود', '')}",
                    callback_data=f"select_student_{s.get('الكود', '')}"
                )])
            keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_main")])
            await update.message.reply_text(
                f"🔍 لقيت {len(results)} طالب بالاسم '{text}'\nاختاري:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    # ====== بحث عن مدرس ======
    elif state == SEARCH_TEACHER:
        user_state.pop(uid, None)
        wait_msg = await update.message.reply_text("⏳ جاري البحث...")
        results = get_teacher_stats(text)

        if not results:
            await wait_msg.edit_text(
                f"❌ مفيش مدرس بالاسم '{text}'",
                reply_markup=back_keyboard()
            )
            return

        # بنخزن النتايج عشان زرار PDF يقدر يستخدمها بعدين
        context.user_data["teacher_search_results"] = results
        context.user_data["teacher_search_query"]   = text

        # بنبني الرد لكل مدرس في النتيجة
        response = f"🔍 نتيجة البحث عن: '{text}'\n━━━━━━━━━━━━━━━━\n"
        for teacher, data_val in results.items():
            # get_teacher_stats(name) بترجع لكل مدرس: {"طلاب": [...], "بالسنة": {...}, "بالتخصص": {...}}
            if isinstance(data_val, dict) and "طلاب" in data_val:
                students = data_val["طلاب"]
                by_year  = data_val.get("بالسنة", {})
                by_spec  = data_val.get("بالتخصص", {})
            else:
                students = data_val
                by_year  = {}
                by_spec  = {}

            response += f"\n👨‍🏫 {teacher}\n"
            response += f"📊 عدد الطلاب: {len(students)}\n"
            if by_year:
                response += (
                    f"  1️⃣ ث1: {by_year.get('ث1',0)} | "
                    f"2️⃣ ث2: {by_year.get('ث2',0)} | "
                    f"3️⃣ ث3: {by_year.get('ث3',0)}\n"
                )
            if by_spec:
                response += (
                    f"  🏫 عام: {by_spec.get('عام',0)} | "
                    f"🕌 أزهر: {by_spec.get('أزهر',0)} | "
                    f"🎓 بكالوريا: {by_spec.get('بكالوريا',0)}\n"
                )

            # تفاصيل الطلاب
            for i, s in enumerate(students, 1):
                response += (
                    f"  {i}. {s.get('اسم', '')} "
                    f"({s.get('السنة', '')}) "
                    f"- {s.get('المادة', '')}\n"
                )
            response += "━━━━━━━━━━━━━━━━\n"

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📄 تحميل PDF بكل التفاصيل", callback_data="teacher_pdf")],
            [InlineKeyboardButton("🔍 بحث عن مدرس تاني", callback_data="search_teacher")],
            [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_main")],
        ])

        if len(response) > 4000:
            chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
            await wait_msg.edit_text(chunks[0])
            for chunk in chunks[1:]:
                await context.bot.send_message(chat_id=update.message.chat_id, text=chunk)
            await context.bot.send_message(chat_id=update.message.chat_id, text="📄 تقرير PDF:", reply_markup=kb)
        else:
            await wait_msg.edit_text(response, reply_markup=kb)

    # ====== بحث عن طالب لتسجيل حضور/درجة/تقرير ======
    elif state == ATT_SEARCH:
        student = search_by_code(text)
        if student:
            await _att_after_student_found(update, context, uid, student, from_callback=False)
            return

        results = search_by_name(text)
        if not results:
            await update.message.reply_text(f"❌ مفيش طالب بالاسم أو الكود '{text}'", reply_markup=back_keyboard())
            return
        if len(results) == 1:
            await _att_after_student_found(update, context, uid, results[0], from_callback=False)
            return

        keyboard = []
        for s in results[:10]:
            keyboard.append([InlineKeyboardButton(
                f"👤 {s.get('الاسم', '')} | {s.get('السنة الدراسية', '')} | كود: {s.get('الكود', '')}",
                callback_data=f"att_pick_{s.get('الكود', '')}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_main")])
        await update.message.reply_text(
            f"🔍 لقيت {len(results)} طالب بالاسم '{text}'\nاختاري:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ====== اسم مدرس مادة لسه مسجلش لها مدرس ======
    elif state == ATT_TEACHER_NAME:
        student = context.user_data.get("att_student", {})
        subject = context.user_data.get("att_subject")
        attendance.set_teacher_if_empty(student.get("year"), student.get("row"), subject, text)
        user_state.pop(uid, None)

        mode = context.user_data.get("att_mode")
        if mode == "grade":
            user_state[uid] = ATT_GRADE_SCORE
            await update.message.reply_text(
                f"✅ تسجل المدرس: {text}\n\n📖 {subject} - أي حصة؟ اختاري رقمها 👇",
                reply_markup=att_sessions_keyboard()
            )
        else:
            await update.message.reply_text(
                f"✅ تسجل المدرس: {text}\n\n📖 {subject} - اختاري رقم الحصة:",
                reply_markup=att_sessions_keyboard()
            )

    # ====== الطالب جاب كام في الامتحان ======
    elif state == ATT_GRADE_SCORE:
        if context.user_data.get("att_session") is None:
            # لسه محددناش رقم الحصة (جاي من مسار "تسجيل درجة" مباشرة) - المتوقع إن الرقم اتبعت كزرار قبل كده
            await update.message.reply_text("اختاري رقم الحصة الأول من الأزرار فوق.")
            return
        context.user_data["att_score"] = text.strip()
        user_state[uid] = ATT_GRADE_MAX
        await update.message.reply_text("✍️ الدرجة النهائية للامتحان (من كام)؟")

    elif state == ATT_GRADE_MAX:
        score = context.user_data.get("att_score", "")
        max_score = text.strip()
        student = context.user_data.get("att_student", {})
        subject = context.user_data.get("att_subject")
        session = context.user_data.get("att_session")
        user_state.pop(uid, None)

        ok = attendance.mark_session(student.get("year"), student.get("row"), subject, session, f"{score}/{max_score}")
        if ok:
            await update.message.reply_text(
                f"✅ اتسجلت الدرجة: {student.get('name','')} - {subject} - حصة {session}: {score}/{max_score}",
                reply_markup=att_done_keyboard()
            )
        else:
            await update.message.reply_text("❌ حصل خطأ في تسجيل الدرجة", reply_markup=back_keyboard())

    # ====== تسجيل مجموعة ======
    elif state == BULK_INPUT:
        user_state.pop(uid, None)
        wait_msg = await update.message.reply_text("⏳ جاري معالجة البيانات...")
        students = await parse_bulk_students(text)
        if not students:
            await wait_msg.edit_text("❌ مقدرتش أقرأ البيانات", reply_markup=back_keyboard())
            return
        success_count = 0
        fail_list = []
        for s in students:
            if add_student(s):
                success_count += 1
            else:
                fail_list.append(s.get("اسم", "مجهول"))
        result = f"✅ تم تسجيل {success_count} طالب!\n"
        if fail_list:
            result += f"❌ فشل: {', '.join(fail_list)}"
        await wait_msg.edit_text(result, reply_markup=main_menu_keyboard())

    # ====== حذف ======
    elif state == DELETE_CODE:
        student = search_by_code(text)
        if not student:
            await update.message.reply_text(f"❌ مفيش طالب بالكود {text}", reply_markup=back_keyboard())
            return
        user_state.pop(uid, None)
        await update.message.reply_text(
            f"⚠️ متأكدة تحذفي:\n👤 {student.get('الاسم', '')} - كود {text}؟",
            reply_markup=confirm_delete_keyboard(text)
        )

    # ====== تعديل قيمة واحدة ======
    elif state == EDIT_FIELD_VALUE:
        code = context.user_data.get("edit_code")
        field = context.user_data.get("edit_field")
        success = update_student(code, field, text)
        user_state.pop(uid, None)

        # لو التعديل جايلنا من شاشة "التعديل الذكي" - نرجع لنفس الشاشة عشان تكملي تعديل حقل تاني
        if success and context.user_data.get("edit_source") == "smartedit":
            student = search_by_code(code)
            if student:
                context.user_data["smartedit_student"] = student
                await update.message.reply_text(
                    f"✅ تم تعديل {field}!\nالجديد: {text}\n\nإيه اللي عايزاه تعدله كمان؟",
                    reply_markup=smart_edit_keyboard(student)
                )
                return

        msg = f"✅ تم تعديل {field}!\nالجديد: {text}" if success else "❌ حصل خطأ"
        await update.message.reply_text(msg, reply_markup=main_menu_keyboard())

    # ====== تعديل حقل واحد من شاشة التعديل الذكي ======
    elif state == EDIT_ONE_FIELD:
        code = context.user_data.get("editone_code")
        field = context.user_data.get("editone_field")
        success = update_student(code, field, text)
        user_state.pop(uid, None)

        # بعد التعديل نرجع لشاشة التعديل الكامل عشان يعدل حاجة تانية
        if success:
            await update.message.reply_text(
                f"✅ تم تعديل {field}: {text}\n\nعايزاه تعدلي حاجة تانية؟",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📝 تعديل حقل تاني", callback_data=f"editall_{code}")],
                    [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_main")],
                ])
            )
        else:
            await update.message.reply_text("❌ حصل خطأ", reply_markup=main_menu_keyboard())

    # ====== تعديل حقل من الصورة ======
    elif state == IMG_EDIT_FIELD:
        field = context.user_data.get("img_edit_field")
        if field and uid in temp_data:
            temp_data[uid][field] = text
            user_state.pop(uid, None)
            preview = build_student_preview(temp_data[uid])
            await update.message.reply_text(
                f"✅ تم تعديل {field}: {text}\n\n" + preview + "البيانات صح دلوقتي؟",
                reply_markup=image_actions_keyboard()
            )
        else:
            await update.message.reply_text("❌ حصل خطأ", reply_markup=main_menu_keyboard())

    # ====== تعديل كل البيانات ======
    elif state == EDIT_ALL_VALUE:
        user_state.pop(uid, None)
        edit_source = context.user_data.get("edit_source", "image")
        new_data = {}
        for line in text.strip().split('\n'):
            if ':' not in line:
                continue
            parts = line.split(':', 1)
            key = parts[0].strip()
            val = parts[1].strip()
            if any(k in key for k in ['اسم']): new_data['اسم'] = val
            elif any(k in key for k in ['كود']): new_data['كود'] = val
            elif any(k in key for k in ['منطقة']): new_data['المنطقة'] = val
            elif any(k in key for k in ['تليفون']) and 'ولي' not in key: new_data['تليفون'] = val
            elif any(k in key for k in ['ولي']): new_data['ولي الأمر'] = val
            elif any(k in key for k in ['سنة']): new_data['السنة'] = val
            elif any(k in key for k in ['تخصص']): new_data['التخصص'] = val
            elif any(k in key for k in ['مواد']): new_data['المواد'] = val
            elif any(k in key for k in ['مدرس']): new_data['المدرسين'] = val

        if edit_source == "image":
            if uid in temp_data:
                temp_data[uid].update(new_data)
            else:
                temp_data[uid] = new_data
            temp_data[uid]["from_image"] = True
            preview = build_student_preview(temp_data[uid])
            await update.message.reply_text(
                "✅ تم تحديث البيانات!\n\n" + preview + "دلوقتي صح؟",
                reply_markup=image_actions_keyboard()
            )
        else:
            old_code = context.user_data.get("editall_code")
            fields_map = {
                "اسم": "الاسم", "كود": "الكود", "المنطقة": "المنطقة",
                "تليفون": "التليفون", "ولي الأمر": "ولي الأمر",
                "السنة": "السنة الدراسية", "التخصص": "التخصص",
                "المواد": "المواد", "المدرسين": "المدرسين"
            }
            success_fields = []
            for k, v in new_data.items():
                sheet_field = fields_map.get(k, k)
                if update_student(old_code, sheet_field, v):
                    success_fields.append(sheet_field)
            if success_fields:
                student = search_by_code(old_code)
                if student:
                    await update.message.reply_text(
                        f"✅ تم تعديل {len(success_fields)} حقل!\n\n" + format_student_info(student),
                        reply_markup=main_menu_keyboard()
                    )
            else:
                await update.message.reply_text("❌ مفيش حاجة اتعدلت", reply_markup=main_menu_keyboard())

    else:
        await update.message.reply_text("📚 القائمة الرئيسية", reply_markup=main_menu_keyboard())


# ====================================================
# الدالة الرئيسية
# ====================================================
def main():
    print("🚀 بيتشغل البوت...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("✅ البوت شغال! ابعتي /start في التليجرام")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
