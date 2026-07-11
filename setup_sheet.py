# ====================================================
# ملف setup_sheet.py
# شغّله مرة واحدة بس عشان تجهز الشيت
# ====================================================

import gspread
from google.oauth2.service_account import Credentials
from config import SHEET_ID, SHEET_NAME, CREDENTIALS_FILE, COLUMNS

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def setup():
    print("🔄 بنتصل بـ Google Sheets...")
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SHEET_ID)

    # بنشوف لو الورقة موجودة
    existing_sheets = [ws.title for ws in spreadsheet.worksheets()]

    if SHEET_NAME not in existing_sheets:
        # بنعمل ورقة جديدة
        sheet = spreadsheet.add_worksheet(title=SHEET_NAME, rows=1000, cols=10)
        print(f"✅ تم إنشاء ورقة '{SHEET_NAME}'")
    else:
        sheet = spreadsheet.worksheet(SHEET_NAME)
        print(f"✅ الورقة '{SHEET_NAME}' موجودة بالفعل")

    # بنحط الأعمدة لو الشيت فاضي
    existing = sheet.get_all_values()
    if not existing:
        sheet.append_row(COLUMNS)
        # تنسيق الصف الأول (header) بخلفية زرقا وخط أبيض عريض
        sheet.format("A1:H1", {
            "backgroundColor": {"red": 0.2, "green": 0.4, "blue": 0.8},
            "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
            "horizontalAlignment": "CENTER"
        })
        print("✅ تم إضافة الأعمدة وتنسيقها")
    else:
        print("✅ الأعمدة موجودة بالفعل")

    print("\n🎉 الشيت جاهز للاستخدام!")
    print(f"🔗 رابط الشيت: https://docs.google.com/spreadsheets/d/{SHEET_ID}")

if __name__ == "__main__":
    setup()
