# Telegram Bot - @lightfins_bot

## Goal
Run the Sanlam funeral policy application flow via Telegram, mirroring the web app wizard.

## Bot Handle
`@lightfins_bot`

## Prerequisites
- Python 3.8+
- `python-telegram-bot` installed (`pip install python-telegram-bot`)
- `TELEGRAM_BOT_TOKEN` set in `.env`

## Setup

### 1. Get Bot Token (already done for @lightfins_bot)
- Message @BotFather on Telegram
- Token stored in `.env` as `TELEGRAM_BOT_TOKEN`

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Bot
```bash
python execution/telegram_bot.py
```

**Expected output:**
```
Sanlam Telegram Bot starting...
Press Ctrl+C to stop.
```

## Conversation Flow

The bot guides users through these steps:

1. **POPIA Consent** - User must agree before proceeding
2. **ID Number** - 13-digit SA ID, validated (extracts age automatically)
3. **Plan Selection** - Value Funeral Plan or All-in-One
4. **Cover Amount** - Choose from available options for their age band
5. **Family Members** - Optional loop: add spouse, children, parents, extended family
6. **Quote** - Shows itemized premium breakdown using `pricing_engine.py`
7. **Address** - Residential address
8. **Bank Details** - Bank name + account number for debit order
9. **Phone Number** - Validated 10-digit SA number
10. **Confirm & Submit** - Shows full summary, user confirms

## Tools Used
- `execution/pricing_engine.py` - Premium calculation (rate tables, eligibility)
- `execution/validate_application_data.py` - ID and phone validation

## Output
- Application JSON saved to `.tmp/telegram_app_<user_id>_<timestamp>.json`
- Same data structure as web app submissions

## Commands
| Command | Action |
|---------|--------|
| `/start` | Begin new application |
| `/cancel` | Cancel current application |
| `/help` | Show help message |

## Edge Cases
- User enters invalid ID → re-prompt with error message
- Age outside eligibility range → polite rejection with referral to Sanlam
- User cancels mid-flow → data discarded, can restart with /start
- User sends /start during flow → restarts from beginning

## Learnings

### 2026-02-13
- Created initial bot with ConversationHandler pattern from python-telegram-bot
- Uses ReplyKeyboardMarkup for guided option selection
- Reuses existing pricing_engine.py and validate_application_data.py
- Bot handle: @lightfins_bot
