# 🏫 بوت مركز الارائج - النسخة الكاملة

## 📁 ملفات المشروع
```
araij_bot/
├── bot.py              ← الكود الرئيسي
├── sheets.py           ← Google Sheets
├── keyboards.py        ← أزرار التليجرام
├── config.py           ← الإعدادات (افتحه وحط البيانات)
├── pdf_report.py       ← توليد تقارير PDF
├── setup_sheet.py      ← إعداد الشيت (مرة واحدة)
├── credentials.json    ← ملف Google (حطه هنا)
└── requirements.txt    ← المكتبات
```

## ⚙️ الإعداد

### 1. افتح config.py وحط:
```python
BOT_TOKEN = "التوكن من BotFather"
GEMINI_API_KEY = "مفتاح Gemini للصور"
ADMIN_ID = 123456789  # الـ ID بتاعك
```

### 2. ثبّت المكتبات:
```bash
py -3.11 -m pip install -r requirements.txt
```

### 3. شغّل:
```bash
py -3.11 bot.py
```

## 🤖 مميزات البوت
| الميزة | الوصف |
|--------|-------|
| ➕ تسجيل طالب | خطوة بخطوة |
| 👥 تسجيل مجموعة | أكتر من طالب مرة واحدة |
| 📸 تسجيل من صورة | استمارة مكتوبة بالإيد |
| 🔍 بحث بالاسم | جزئي - مش لازم اسم كامل |
| 🔎 بحث بالكود | مباشر |
| ✏️ تعديل | أي بيانات |
| 🗑️ حذف | مع تأكيد |
| 📊 تقارير | نص أو PDF |
| 📈 إحصائيات | عدد الطلاب |

## 📸 للصور - محتاج Gemini API Key
روح: https://aistudio.google.com/apikey
اعمل account واعمل API Key مجاني
