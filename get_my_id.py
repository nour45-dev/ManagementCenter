# ====================================================
# ملف get_my_id.py
# شغّله مرة واحدة بس عشان تعرفي الـ ID بتاعك
# وبعدين حطيه في config.py في ADMIN_ID
# ====================================================

from telegram import Update
from telegram.ext import Application, CommandHandler

# حطي التوكن هنا مؤقتاً
TOKEN = "8884828886:AAGWzT1RCzd9Qs46fEnZJBbj5Y3tA2x_OpY"

async def get_id(update: Update, context):
    user = update.effective_user
    await update.message.reply_text(
        f"✅ الـ ID بتاعك:\n"
        f"🔢 {user.id}\n\n"
        f"👤 الاسم: {user.full_name}\n\n"
        f"حطي الرقم ده في config.py في ADMIN_ID"
    )

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", get_id))
print("شغّل البوت وابعتيله /start عشان تعرفي الـ ID...")
app.run_polling()
