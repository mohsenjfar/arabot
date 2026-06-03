from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, filters
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_URL = os.getenv("BOT_URL")

# ========== هندلر دکمه ==========
async def button_handler(update: Update, context):
    query = update.callback_query
    await query.answer()  # حتماً باید باشه تا لودینگ دکمه تموم بشه
    
    data = query.data  # دریافت دیتای دکمه
    
    if data == "btn1":
        await query.edit_message_text("✅ دکمه اول رو زدی!")
    elif data == "btn2":
        await query.edit_message_text("✅ دکمه دوم رو زدی!")
    elif data == "close":
        await query.delete_message()  # حذف پیام

# ========== هندلر /start با دکمه اینلاین ==========
async def start(update: Update, context):
    keyboard = [
        [
            InlineKeyboardButton("🔘 دکمه اول", callback_data="btn1"),
            InlineKeyboardButton("🔘 دکمه دوم", callback_data="btn2"),
        ],
        [
            InlineKeyboardButton("❌ بستن", callback_data="close"),
        ],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "روی دکمه‌ها کلیک کن:",
        reply_markup=reply_markup
    )

# ========== راه‌اندازی ==========
app = (
    Application.builder()
    .token(BOT_TOKEN)
    .base_url(BOT_URL)
    .build()
)

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))  # هندلر دکمه

print("Bot started! Send /start")
app.run_polling()