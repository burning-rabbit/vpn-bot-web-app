"""Main Telegram bot file."""
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from config import TELEGRAM_BOT_TOKEN
from handlers.commands import (
    start_command,
    help_command,
    get_vpn_command,
    devices_command,
    button_callback,
    handle_text_message
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # Changed to DEBUG for detailed error information
)
logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors that occur during updates."""
    logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)
    
    # Try to send error message to user if update is available
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже."
            )
        except Exception:
            pass  # Ignore errors when sending error message


def main():
    """Start the bot."""
    try:
        # Create application
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Register command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("get_vpn", get_vpn_command))
        application.add_handler(CommandHandler("devices", devices_command))
        
        # Register callback query handler for buttons
        application.add_handler(CallbackQueryHandler(button_callback))
        
        # Register message handler for text input (device names)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
        
        # Register error handler
        application.add_error_handler(error_handler)
        
        # Start the bot
        logger.info("Bot is starting...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}")
        raise


if __name__ == "__main__":
    main()

