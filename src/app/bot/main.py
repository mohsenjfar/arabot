from telegram.ext import Application, CommandHandler, MessageHandler, filters
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_URL = os.getenv("BOT_URL")

async def ping(update, context):
    await update.message.reply_text("pong")

async def echo(update, context):
    await update.message.reply_text(f"گرفتم: {update.message.text}")

app = (
    Application.builder()
    .token(BOT_TOKEN)
    .base_url(BOT_URL)
    .build()
)
app.add_handler(CommandHandler("ping", ping))
app.add_handler(MessageHandler(filters.TEXT, echo))

print("Bot started!")
app.run_polling()