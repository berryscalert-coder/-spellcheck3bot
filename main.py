import os
import asyncio
import aiohttp
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
if not BOT_TOKEN:
    logger.error("BOT_TOKEN environment variable not set!")
    exit(1)

# Supported languages for spell check
LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "nl": "Dutch",
    "pl": "Polish",
    "tr": "Turkish",
    "vi": "Vietnamese",
    "id": "Indonesian",
    "ms": "Malay",
    "sw": "Swahili",
    "ha": "Hausa",
    "yo": "Yoruba",
    "ig": "Igbo",
    "zu": "Zulu",
    "af": "Afrikaans",
    "el": "Greek",
    "he": "Hebrew",
    "hu": "Hungarian",
    "ro": "Romanian",
    "sk": "Slovak",
    "sv": "Swedish",
    "uk": "Ukrainian",
    "da": "Danish",
    "fi": "Finnish",
    "no": "Norwegian",
    "fa": "Persian",
    "ur": "Urdu",
    "bn": "Bengali",
    "ta": "Tamil",
    "te": "Telugu",
    "ml": "Malayalam"
}

user_sessions = {}

# ==================== KEYBOARDS ====================
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📝 Check Spelling", callback_data="check")],
        [InlineKeyboardButton("🌍 Set Language", callback_data="language")],
        [InlineKeyboardButton("📋 Language List", callback_data="languages")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_language_keyboard(selected: str = None):
    keyboard = []
    row = []
    for code, name in sorted(LANGUAGES.items(), key=lambda x: x[1])[:20]:
        display = f"✅ {name}" if code == selected else name
        row.append(InlineKeyboardButton(display, callback_data=f"setlang_{code}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back")])
    return InlineKeyboardMarkup(keyboard)

# ==================== COMMAND HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    user_sessions[user_id] = {"language": "en"}
    
    welcome = (
        f"📝 Welcome {user.first_name} to **SpellCheckBot**!\n\n"
        "🔍 Your spelling and grammar checker!\n\n"
        "**✨ Features:**\n"
        "• 📝 Check spelling and grammar\n"
        "• 🌍 Supports 35+ languages\n"
        "• 🔧 Get correction suggestions\n"
        "• 📋 List all supported languages\n\n"
        "**📖 How to use:**\n"
        "1. Send me any text\n"
        "2. I'll check for errors!\n"
        "3. Get corrections and suggestions\n\n"
        "⬇️ Send text or click 'Check Spelling'!"
    )
    await update.message.reply_text(welcome, parse_mode="Markdown", reply_markup=get_main_keyboard())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📖 **SpellCheckBot - Help Guide**\n\n"
        "**🔍 How to Check Spelling:**\n"
        "• Send any text message\n"
        "• Or click 'Check Spelling' button\n"
        "• I'll check for errors instantly!\n\n"
        "**🔧 Commands:**\n"
        "• `/start` - Start the bot\n"
        "• `/help` - Show this help\n"
        "• `/languages` - List all languages\n"
        "• `/check [text]` - Check spelling of text\n"
        "• `/setlang [code]` - Set language\n\n"
        "**📊 What You Get:**\n"
        "• Corrected text\n"
        "• Suggested corrections\n"
        "• Grammar and spelling errors fixed\n\n"
        "**💡 Examples:**\n"
        "• Send: 'I hav a cat' → 'I have a cat'\n"
        "• Send: 'She go to school' → 'She goes to school'"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

async def languages_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang_list = "🌍 **Supported Languages**\n\n"
    for code, name in sorted(LANGUAGES.items(), key=lambda x: x[1]):
        lang_list += f"• {name} (`{code}`)\n"
    await update.message.reply_text(lang_list, parse_mode="Markdown", reply_markup=get_main_keyboard())

async def setlang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a language code.\n\n"
            "Example: `/setlang en`\n"
            "Use /languages to see all codes.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        return
    
    lang_code = context.args[0].lower()
    
    if lang_code not in LANGUAGES:
        await update.message.reply_text(
            f"❌ '{lang_code}' is not supported.\n"
            "Use /languages to see all codes.",
            reply_markup=get_main_keyboard()
        )
        return
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    user_sessions[user_id]["language"] = lang_code
    
    await update.message.reply_text(
        f"✅ Language set to: **{LANGUAGES[lang_code]}**",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide text to check.\n\n"
            "Example: `/check I hav a cat`\n"
            "Or just send me any text!",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        return
    
    text = " ".join(context.args)
    await check_spelling_and_reply(update, text)

# ==================== CALLBACK HANDLERS ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = str(update.effective_user.id)
    
    if data == "check":
        await query.edit_message_text(
            "📝 **Send me any text**\n\n"
            "I'll check the spelling and grammar for you!\n\n"
            "💡 You can also use /check [text]",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    
    elif data == "language":
        current_lang = user_sessions.get(user_id, {}).get("language", "en")
        await query.edit_message_text(
            "🌍 **Select your language:**",
            parse_mode="Markdown",
            reply_markup=get_language_keyboard(current_lang)
        )
    
    elif data.startswith("setlang_"):
        lang_code = data.replace("setlang_", "")
        if user_id not in user_sessions:
            user_sessions[user_id] = {}
        user_sessions[user_id]["language"] = lang_code
        
        await query.edit_message_text(
            f"✅ Language set to: **{LANGUAGES.get(lang_code, 'Unknown')}**\n\n"
            "Send me text to check! 📝",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    
    elif data == "languages":
        lang_list = "🌍 **Supported Languages**\n\n"
        for code, name in sorted(LANGUAGES.items(), key=lambda x: x[1]):
            lang_list += f"• {name} (`{code}`)\n"
        await query.edit_message_text(lang_list, parse_mode="Markdown", reply_markup=get_main_keyboard())
    
    elif data == "help":
        help_text = (
            "📖 **SpellCheckBot - Help Guide**\n\n"
            "**🔍 How to Check Spelling:**\n"
            "• Send any text message\n"
            "• Or click 'Check Spelling' button\n"
            "• I'll check for errors instantly!\n\n"
            "**🔧 Commands:**\n"
            "• `/start` - Start the bot\n"
            "• `/help` - Show this help\n"
            "• `/languages` - List all languages\n"
            "• `/check [text]` - Check spelling of text\n"
            "• `/setlang [code]` - Set language"
        )
        await query.edit_message_text(help_text, parse_mode="Markdown", reply_markup=get_main_keyboard())
    
    elif data == "back":
        await query.edit_message_text(
            "🏠 **Main Menu**\n\n"
            "What would you like to do?",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

# ==================== SPELL CHECK FUNCTIONS ====================
async def check_spelling(text: str, language: str = "en"):
    """Check spelling using LibreTranslate's spell check API"""
    if not text or len(text.strip()) < 1:
        return None
    
    try:
        url = "https://libretranslate.com/spellcheck"
        payload = {
            "q": text,
            "language": language
        }
        headers = {"Content-Type": "application/json"}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                return None
    except asyncio.TimeoutError:
        logger.warning("Spell check API timeout")
        return None
    except Exception as e:
        logger.error(f"Spell check error: {e}")
        return None

async def check_spelling_and_reply(update: Update, text: str):
    """Check spelling and reply with results"""
    user_id = str(update.effective_user.id)
    language = user_sessions.get(user_id, {}).get("language", "en")
    
    if len(text.strip()) < 3:
        await update.message.reply_text(
            "❌ **Text too short**\n\n"
            "Please send at least 3 characters for checking.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Send processing message
    processing_msg = await update.message.reply_text(
        "🔍 **Checking spelling...**\n\n"
        "⏳ Analyzing text...",
        parse_mode="Markdown"
    )
    
    result = await check_spelling(text, language)
    
    await processing_msg.delete()
    
    if result:
        corrections = result.get("corrections", [])
        corrected_text = result.get("corrected", text)
        
        if corrections and len(corrections) > 0:
            correction_details = ""
            for i, correction in enumerate(corrections[:5]):
                correction_details += f"{i+1}. **{correction.get('original', '')}** → _{correction.get('correction', '')}_\n"
            
            if len(corrections) > 5:
                correction_details += f"\n... and {len(corrections) - 5} more corrections"
            
            await update.message.reply_text(
                f"✅ **Spelling Check Complete!**\n\n"
                f"📝 **Original:**\n_{text[:200]}{'...' if len(text) > 200 else ''}_\n\n"
                f"📝 **Corrected:**\n_{corrected_text[:200]}{'...' if len(corrected_text) > 200 else ''}_\n\n"
                f"🔧 **Corrections Found:** {len(corrections)}\n\n"
                f"{correction_details}\n\n"
                f"🌍 **Language:** {LANGUAGES.get(language, 'English')}\n"
                f"💡 Send more text to check!",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
        else:
            await update.message.reply_text(
                f"✅ **No Spelling Errors Found!**\n\n"
                f"📝 **Your text:**\n_{text[:200]}{'...' if len(text) > 200 else ''}_\n\n"
                f"🌍 **Language:** {LANGUAGES.get(language, 'English')}\n\n"
                f"✍️ Your text looks great! Keep up the good work!",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
    else:
        # Fallback: Check for common spelling errors
        corrections = []
        words = text.split()
        for word in words:
            if len(word) > 2 and word not in ["the", "and", "for", "are", "but", "not", "you", "all", "can", "had", "her", "was", "one", "our", "out", "see", "she", "two", "way", "who", "yes", "why"]:
                # Simple check for common mistakes
                if word == "hav":
                    corrections.append({"original": "hav", "correction": "have"})
                elif word == "teh":
                    corrections.append({"original": "teh", "correction": "the"})
                elif word == "adn":
                    corrections.append({"original": "adn", "correction": "and"})
                elif word == "fo":
                    corrections.append({"original": "fo", "correction": "for"})
                elif word == "wih":
                    corrections.append({"original": "wih", "correction": "with"})
                elif word == "waas":
                    corrections.append({"original": "waas", "correction": "was"})
                elif word == "wer":
                    corrections.append({"original": "wer", "correction": "were"})
        
        if corrections:
            corrected_text = text
            for corr in corrections:
                corrected_text = corrected_text.replace(corr["original"], corr["correction"])
            
            correction_details = ""
            for i, correction in enumerate(corrections[:5]):
                correction_details += f"{i+1}. **{correction['original']}** → _{correction['correction']}_\n"
            
            await update.message.reply_text(
                f"✅ **Spelling Check Complete!**\n\n"
                f"📝 **Original:**\n_{text[:200]}{'...' if len(text) > 200 else ''}_\n\n"
                f"📝 **Corrected:**\n_{corrected_text[:200]}{'...' if len(corrected_text) > 200 else ''}_\n\n"
                f"🔧 **Corrections Found:** {len(corrections)}\n\n"
                f"{correction_details}\n\n"
                f"🌍 **Language:** {LANGUAGES.get(language, 'English')}\n"
                f"💡 Send more text to check!",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
        else:
            await update.message.reply_text(
                f"✅ **Spelling Check Complete!**\n\n"
                f"📝 **Your text:**\n_{text[:200]}{'...' if len(text) > 200 else ''}_\n\n"
                f"🌍 **Language:** {LANGUAGES.get(language, 'English')}\n\n"
                f"⚠️ Could not perform detailed analysis.\n"
                f"💡 Try sending shorter text or a different language.",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )

# ==================== MESSAGE HANDLER ====================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    if text.startswith('/'):
        return
    
    await check_spelling_and_reply(update, text)

# ==================== ERROR HANDLER ====================
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning(f"Update {update} caused error {context.error}")

# ==================== MAIN FUNCTION ====================
def main():
    print("=" * 50)
    print("📝 Starting SpellCheckBot...")
    print(f"🌍 Supported languages: {len(LANGUAGES)}")
    print("✅ Bot is ready!")
    print("=" * 50)
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("languages", languages_command))
    application.add_handler(CommandHandler("setlang", setlang_command))
    application.add_handler(CommandHandler("check", check_command))
    
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_error_handler(error_handler)
    
    print("✅ Bot is running! Press Ctrl+C to stop.")
    print("=" * 50)
    
    application.run_polling()

if __name__ == "__main__":
    main()
