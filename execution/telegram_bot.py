#!/usr/bin/env python3
"""
Sanlam Funeral Policy - Telegram Bot

Conversational bot that mirrors the web app's application flow:
  Consent -> ID -> Plan -> Cover -> Family -> Quote -> Address -> Bank -> Confirm

Uses the existing pricing_engine.py for premium calculations
and validate_application_data.py for input validation.

Layer 3: Execution script (deterministic, testable).

Setup:
    1. Set TELEGRAM_BOT_TOKEN in .env
    2. pip install python-telegram-bot
    3. python execution/telegram_bot.py
"""

import os
import sys
import json
import logging
from datetime import datetime

# Add project root to path so we can import sibling modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

from execution.pricing_engine import (
    calculate_premium,
    calculate_total_premium,
    validate_eligibility,
    get_available_covers,
    COVER_LIMITS,
    AGE_LIMITS,
)
from execution.validate_application_data import validate_id_number, validate_phone

# ── Logging ───────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Conversation States ───────────────────────────────────
(
    CONSENT,
    ID_NUMBER,
    PLAN_SELECT,
    COVER_AMOUNT,
    ADD_FAMILY,
    FAMILY_TYPE,
    FAMILY_AGE,
    FAMILY_COVER,
    QUOTE_CONFIRM,
    ADDRESS,
    BANK_NAME,
    ACCOUNT_NUMBER,
    PHONE,
    CONFIRM_SUBMIT,
) = range(14)

# ── Helpers ───────────────────────────────────────────────

def age_from_id(id_number: str) -> int:
    """Extract age from SA ID number (YYMMDD...)."""
    year_part = int(id_number[0:2])
    current_year = datetime.now().year % 100
    birth_year = 1900 + year_part if year_part > current_year else 2000 + year_part
    today = datetime.now()
    month = int(id_number[2:4])
    day = int(id_number[4:6])
    age = today.year - birth_year
    if (today.month, today.day) < (month, day):
        age -= 1
    return age


def format_rand(amount: int) -> str:
    return f"R{amount:,}"


def application_summary(data: dict) -> str:
    """Build a readable summary of the application."""
    lines = []
    lines.append("── Application Summary ──")
    lines.append(f"Plan: {data.get('plan', 'value').replace('_', ' ').title()}")
    lines.append(f"ID Number: {data['id_number']}")
    lines.append(f"Age: {data['age']}")
    lines.append(f"Phone: {data.get('phone', 'N/A')}")
    lines.append(f"\nPrincipal cover: {format_rand(data['cover_amount'])}")

    if data.get('family'):
        lines.append("\nFamily members:")
        for i, m in enumerate(data['family'], 1):
            lines.append(f"  {i}. {m['type'].title()} - age {m['age']}, cover {format_rand(m['cover_amount'])}")

    lines.append(f"\nTotal premium: {format_rand(data['total_premium'])}/month")
    lines.append(f"Address: {data.get('address', 'N/A')}")
    lines.append(f"Bank: {data.get('bank_name', 'N/A')}")
    lines.append(f"Account: {data.get('account_number', 'N/A')}")
    return "\n".join(lines)


# ── Bot Handlers ──────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point - /start command."""
    context.user_data.clear()
    context.user_data['family'] = []

    await update.message.reply_text(
        "Welcome to the *Sanlam Funeral Plan* assistant.\n\n"
        "I'll help you apply for funeral cover in a few simple steps.\n\n"
        "Before we begin, do you consent to your information being used "
        "to process a funeral policy application in line with POPIA?",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(
            [["Yes, I consent"], ["No"]],
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )
    return CONSENT


async def consent_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    if "yes" not in text:
        await update.message.reply_text(
            "No problem. You can start again anytime with /start.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "Thank you. Please enter your *13-digit South African ID number*.",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ID_NUMBER


async def id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    id_num = update.message.text.strip().replace(" ", "")
    valid, msg = validate_id_number(id_num)

    if not valid:
        await update.message.reply_text(f"Invalid ID: {msg}\nPlease try again.")
        return ID_NUMBER

    age = age_from_id(id_num)
    context.user_data['id_number'] = id_num
    context.user_data['age'] = age

    # Check principal eligibility
    valid, msg = validate_eligibility(age, 'principal', 5000)
    if not valid:
        await update.message.reply_text(
            f"Unfortunately you are not eligible: {msg}\n"
            "Please contact Sanlam directly for assistance.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    await update.message.reply_text(
        f"Got it! You are *{age} years old*.\n\n"
        "Which plan would you like?",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(
            [["Value Funeral Plan"], ["All-in-One Plan"]],
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )
    return PLAN_SELECT


async def plan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    plan = 'all_in_one' if 'all' in text else 'value'
    context.user_data['plan'] = plan

    covers = get_available_covers('principal')
    cover_text = ", ".join(format_rand(c) for c in covers)
    plan_name = "All-in-One" if plan == 'all_in_one' else "Value Funeral"

    await update.message.reply_text(
        f"You chose the *{plan_name}* plan.\n\n"
        f"How much cover do you want for yourself (the principal)?\n"
        f"Available: {cover_text}",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(
            [[format_rand(c) for c in covers[i:i+3]] for i in range(0, len(covers), 3)],
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )
    return COVER_AMOUNT


async def cover_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().replace("R", "").replace(",", "").replace(" ", "")
    try:
        cover = int(text)
    except ValueError:
        await update.message.reply_text("Please enter a valid amount (e.g. R50,000 or 50000).")
        return COVER_AMOUNT

    age = context.user_data['age']
    valid, msg = validate_eligibility(age, 'principal', cover)
    if not valid:
        await update.message.reply_text(f"{msg}\nPlease choose a different amount.")
        return COVER_AMOUNT

    premium = calculate_premium(age, 'principal', cover)
    context.user_data['cover_amount'] = cover
    context.user_data['principal_premium'] = premium

    await update.message.reply_text(
        f"Your premium for {format_rand(cover)} cover: *{format_rand(premium)}/month*\n\n"
        "Would you like to add family members to this policy?",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(
            [["Yes, add family"], ["No, continue"]],
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )
    return ADD_FAMILY


async def add_family_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    if "no" in text:
        return await show_quote(update, context)

    await update.message.reply_text(
        "Who would you like to add?",
        reply_markup=ReplyKeyboardMarkup(
            [["Spouse", "Child"], ["Parent", "Extended Family"], ["Done adding"]],
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )
    return FAMILY_TYPE


async def family_type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()

    if "done" in text:
        return await show_quote(update, context)

    type_map = {
        'spouse': 'spouse',
        'child': 'child',
        'parent': 'parent',
        'extended': 'wider_family',
    }

    member_type = None
    for key, val in type_map.items():
        if key in text:
            member_type = val
            break

    if not member_type:
        await update.message.reply_text("Please choose: Spouse, Child, Parent, or Extended Family.")
        return FAMILY_TYPE

    context.user_data['adding_type'] = member_type
    min_age, max_age = AGE_LIMITS[member_type]

    await update.message.reply_text(
        f"What is the {member_type.replace('_', ' ')}'s age? (valid: {min_age}-{max_age})",
        reply_markup=ReplyKeyboardRemove(),
    )
    return FAMILY_AGE


async def family_age_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        age = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Please enter a number for the age.")
        return FAMILY_AGE

    member_type = context.user_data['adding_type']
    min_age, max_age = AGE_LIMITS[member_type]

    if age < min_age or age > max_age:
        await update.message.reply_text(
            f"Age must be between {min_age} and {max_age} for {member_type.replace('_', ' ')}. Try again."
        )
        return FAMILY_AGE

    context.user_data['adding_age'] = age

    covers = get_available_covers(member_type)
    cover_text = ", ".join(format_rand(c) for c in covers)

    await update.message.reply_text(
        f"Choose cover amount for this {member_type.replace('_', ' ')} (age {age}):\n"
        f"Available: {cover_text}",
        reply_markup=ReplyKeyboardMarkup(
            [[format_rand(c) for c in covers[i:i+3]] for i in range(0, len(covers), 3)],
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )
    return FAMILY_COVER


async def family_cover_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().replace("R", "").replace(",", "").replace(" ", "")
    try:
        cover = int(text)
    except ValueError:
        await update.message.reply_text("Please enter a valid amount.")
        return FAMILY_COVER

    member_type = context.user_data['adding_type']
    age = context.user_data['adding_age']

    valid, msg = validate_eligibility(age, member_type, cover)
    if not valid:
        await update.message.reply_text(f"{msg}\nPlease choose a different amount.")
        return FAMILY_COVER

    premium = calculate_premium(age, member_type, cover)

    context.user_data['family'].append({
        'type': member_type,
        'age': age,
        'cover_amount': cover,
        'premium': premium,
    })

    count = len(context.user_data['family'])
    await update.message.reply_text(
        f"Added {member_type.replace('_', ' ')} (age {age}, {format_rand(cover)} cover, "
        f"{format_rand(premium)}/month).\n\n"
        f"You have {count} family member(s) added.\n"
        "Add another or continue?",
        reply_markup=ReplyKeyboardMarkup(
            [["Spouse", "Child"], ["Parent", "Extended Family"], ["Done adding"]],
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )
    return FAMILY_TYPE


async def show_quote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Calculate and display the total quote."""
    lives = [
        {
            'age': context.user_data['age'],
            'category': 'principal',
            'cover_amount': context.user_data['cover_amount'],
        }
    ]
    for m in context.user_data.get('family', []):
        lives.append({
            'age': m['age'],
            'category': m['type'],
            'cover_amount': m['cover_amount'],
        })

    plan = context.user_data.get('plan', 'value')
    result = calculate_total_premium(lives, plan)
    context.user_data['total_premium'] = result['total']

    lines = ["*Your Quote*\n"]
    for p in result['premiums']:
        lines.append(
            f"  {p['category'].replace('_', ' ').title()} (age {p['age']}): "
            f"{format_rand(p['cover_amount'])} cover = {format_rand(p['premium'])}/mo"
        )
    lines.append(f"\nSubtotal: {format_rand(result['subtotal'])}/month")
    if result['min_applied']:
        lines.append(f"Minimum premium applied: {format_rand(result['total'])}/month")
    else:
        lines.append(f"*Total: {format_rand(result['total'])}/month*")

    await update.message.reply_text(
        "\n".join(lines) + "\n\nWould you like to proceed?",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(
            [["Yes, proceed"], ["No, start over"]],
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )
    return QUOTE_CONFIRM


async def quote_confirm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    if "no" in text or "start" in text:
        return await start(update, context)

    await update.message.reply_text(
        "Please enter your *residential address* (street, suburb, city, postal code).",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ADDRESS


async def address_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    address = update.message.text.strip()
    if len(address) < 10:
        await update.message.reply_text("Please provide a more complete address.")
        return ADDRESS

    context.user_data['address'] = address

    await update.message.reply_text(
        "Which bank do you use for the debit order?",
        reply_markup=ReplyKeyboardMarkup(
            [["ABSA", "FNB"], ["Standard Bank", "Nedbank"], ["Capitec", "Other"]],
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )
    return BANK_NAME


async def bank_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['bank_name'] = update.message.text.strip()

    await update.message.reply_text(
        "Please enter your bank *account number*.",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ACCOUNT_NUMBER


async def account_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    acc = update.message.text.strip().replace(" ", "")
    if not acc.isdigit() or len(acc) < 6:
        await update.message.reply_text("Please enter a valid account number (digits only, at least 6).")
        return ACCOUNT_NUMBER

    context.user_data['account_number'] = acc

    await update.message.reply_text(
        "Lastly, please enter your *cellphone number* (10 digits, e.g. 0821234567).",
        parse_mode="Markdown",
    )
    return PHONE


async def phone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    phone = update.message.text.strip().replace(" ", "").replace("-", "")
    valid, msg = validate_phone(phone)
    if not valid:
        await update.message.reply_text(f"Invalid phone: {msg}\nPlease try again.")
        return PHONE

    context.user_data['phone'] = phone

    summary = application_summary(context.user_data)
    await update.message.reply_text(
        f"{summary}\n\n"
        "Please confirm: is everything correct?",
        reply_markup=ReplyKeyboardMarkup(
            [["Confirm & Submit"], ["Cancel"]],
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )
    return CONFIRM_SUBMIT


async def confirm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    if "cancel" in text:
        await update.message.reply_text(
            "Application cancelled. Use /start to begin again.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    # Save application data to .tmp/
    data = dict(context.user_data)
    os.makedirs(".tmp", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    user_id = update.effective_user.id
    filepath = f".tmp/telegram_app_{user_id}_{timestamp}.json"

    # Convert to serializable format
    save_data = {
        "source": "telegram",
        "telegram_user_id": user_id,
        "timestamp": timestamp,
        "policyholder": {
            "id_number": data.get("id_number"),
            "age": data.get("age"),
            "cellphone": data.get("phone"),
        },
        "plan": data.get("plan", "value"),
        "lives_covered": {
            "principal": {
                "cover_amount": data.get("cover_amount"),
                "premium": data.get("principal_premium"),
            },
            "family": data.get("family", []),
        },
        "payment": {
            "monthly_premium": data.get("total_premium"),
            "bank_name": data.get("bank_name"),
            "account_number": data.get("account_number"),
        },
        "address": data.get("address"),
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=2)

    logger.info("Application saved: %s", filepath)

    await update.message.reply_text(
        "Your application has been submitted successfully!\n\n"
        f"Reference: TG-{user_id}-{timestamp}\n"
        f"Premium: {format_rand(data['total_premium'])}/month\n\n"
        "A Sanlam representative will contact you to finalize your policy.\n\n"
        "Thank you for choosing Sanlam!",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /cancel command."""
    await update.message.reply_text(
        "Application cancelled. Use /start to begin again.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    await update.message.reply_text(
        "*Sanlam Funeral Plan Bot*\n\n"
        "Commands:\n"
        "/start - Begin a new application\n"
        "/cancel - Cancel current application\n"
        "/help - Show this message\n\n"
        "This bot helps you apply for a Sanlam funeral policy. "
        "You'll be guided through each step.",
        parse_mode="Markdown",
    )


# ── Main ──────────────────────────────────────────────────

def main():
    """Start the bot."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("ERROR: TELEGRAM_BOT_TOKEN not set in environment.")
        print("Set it in .env or export it:")
        print("  export TELEGRAM_BOT_TOKEN='your-bot-token-here'")
        print("\nTo get a token:")
        print("  1. Message @BotFather on Telegram")
        print("  2. Send /newbot")
        print("  3. Follow the prompts to create your bot")
        print("  4. Copy the token and set it as TELEGRAM_BOT_TOKEN")
        sys.exit(1)

    app = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CONSENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, consent_handler)],
            ID_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, id_handler)],
            PLAN_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, plan_handler)],
            COVER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, cover_handler)],
            ADD_FAMILY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_family_handler)],
            FAMILY_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, family_type_handler)],
            FAMILY_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, family_age_handler)],
            FAMILY_COVER: [MessageHandler(filters.TEXT & ~filters.COMMAND, family_cover_handler)],
            QUOTE_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, quote_confirm_handler)],
            ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, address_handler)],
            BANK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, bank_handler)],
            ACCOUNT_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, account_handler)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone_handler)],
            CONFIRM_SUBMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))

    print("Sanlam Telegram Bot starting...")
    print("Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    # Load .env if present
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())

    main()
