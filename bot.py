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
    confirm_delete_keyboard, back_keyboard, teachers_keyboard
)
from pdf_report import generate_pdf
from config import GEMINI_API_KEY
from google import genai
from google.genai import types

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
                "(كل زر فيه القيمة الحالية)",
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
        uid_data["pending_teachers"] = list(selected)
        uid_data["teachers_dict"] = uid_data.get("teachers_dict", {})

        # نطلب مدرس أول مادة عن طريق الدالة المركزية (بتعرض الأزرار)
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
        # pick_teacher_{subject}_{teacher_name}
        rest = data.replace("pick_teacher_", "", 1)
        uid_data = temp_data.get(uid, {})
        pending = uid_data.get("pending_teachers", [])

        # نعرف المادة من أول عنصر في pending (لأن اسم المدرس ممكن يحتوي _)
        subject = pending[0] if pending else ""
        teacher = rest[len(subject)+1:]  # نشيل subject_ من الأول

        if subject:
            uid_data.setdefault("teachers_dict", {})[subject] = teacher
            if subject in pending:
                pending.remove(subject)

        await _process_next_teacher(update, context, uid, uid_data, from_callback=True)

    # ====== كتابة اسم مدرس يدوياً ======
    elif data.startswith("write_teacher_"):
        subject = data.replace("write_teacher_", "", 1)
        uid_data = temp_data.get(uid, {})
        user_state[uid] = GET_TEACHER
        context.user_data["writing_teacher_for"] = subject
        await query.edit_message_text(
            f"✍️ اكتبي اسم مدرس مادة:\n📖 {subject}",
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


# ====================================================
# دالة مساعدة لمعالجة المدرسين
# ====================================================
async def _process_next_teacher(update, context, uid, uid_data, from_callback=False):
    """بتعالج طلب المدرس التالي أو تحفظ الطالب لو خلصنا"""
    pending = uid_data.get("pending_teachers", [])

    if pending:
        # لسه في مواد
        next_subject = pending[0]
        user_state[uid] = GET_TEACHER
        has_teachers = bool(TEACHERS.get(next_subject))
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

    # ====== اسم المدرس ======
    elif state == GET_TEACHER:
        uid_data = temp_data.get(uid, {})
        pending = uid_data.get("pending_teachers", [])

        # لو كان بيكتب مدرس لمادة محددة من write_teacher_
        writing_for = context.user_data.pop("writing_teacher_for", None)
        if writing_for:
            current_subject = writing_for
        elif pending:
            current_subject = pending[0]
        else:
            current_subject = None

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
            await update.message.reply_text(info + "\n\nإيه اللي عايزاه تعدليه؟", reply_markup=edit_fields_keyboard(code))
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

        # بنبني الرد لكل مدرس في النتيجة
        response = f"🔍 نتيجة البحث عن: '{text}'\n━━━━━━━━━━━━━━━━\n"
        for teacher, students in results.items():
            response += f"\n👨‍🏫 {teacher}\n"
            response += f"📊 عدد الطلاب: {len(students)}\n"

            # تفاصيل الطلاب
            for i, s in enumerate(students, 1):
                response += (
                    f"  {i}. {s.get('اسم', '')} "
                    f"({s.get('السنة', '')}) "
                    f"- {s.get('المادة', '')}\n"
                )
            response += "━━━━━━━━━━━━━━━━\n"

        if len(response) > 4000:
            chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
            await wait_msg.edit_text(chunks[0])
            for chunk in chunks[1:]:
                await context.bot.send_message(chat_id=update.message.chat_id, text=chunk)
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text="✅ انتهى",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔍 بحث عن مدرس تاني", callback_data="search_teacher")],
                    [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_main")],
                ])
            )
        else:
            await wait_msg.edit_text(
                response,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔍 بحث عن مدرس تاني", callback_data="search_teacher")],
                    [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_main")],
                ])
            )

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
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
