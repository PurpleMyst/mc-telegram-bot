import gzip
import logging
import os
import subprocess
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

import colorama
import platformdirs
import pretty_errors as _
from colorama import Fore, Style
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, PicklePersistence


class ColorFormatter(logging.Formatter):
    """
    A custom logging formatter to add colors to log messages.
    """

    # Map log levels to colors
    LEVEL_COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.MAGENTA + Style.BRIGHT,
    }

    def format(self, record):
        # Add color to the log level
        level_color = self.LEVEL_COLORS.get(record.levelno, "")
        record.levelname = f"{level_color}{record.levelname}{Style.RESET_ALL}"

        # Add color to the logger name
        record.name = f"{Fore.BLUE}{record.name}{Style.RESET_ALL}"

        # Add color to the timestamp
        timestamp = self.formatTime(record, self.datefmt)

        record.message = record.getMessage()  # Populate the message field
        formatted_message = f"{Fore.MAGENTA}{timestamp}{Style.RESET_ALL} - {record.name} - {record.levelname} - {record.message}"
        return formatted_message


def compress_log_file(log_file_path):
    """
    Compress a log file using gzip.

    Args:
        log_file_path (str): The path to the log file to compress.
    """
    if os.path.exists(log_file_path):
        with open(log_file_path, "rb") as f_in:
            with gzip.open(f"{log_file_path}.gz", "wb") as f_out:
                f_out.writelines(f_in)
        os.remove(log_file_path)  # Remove the uncompressed log file


def setup_global_logging():
    """
    Set up global logging configuration for all loggers.

    Args:
        log_file (str): File path for persistent logs.
        level (int): Logging level (e.g., logging.DEBUG, logging.INFO).
    """

    log_file = (
        Path(platformdirs.user_log_dir("mc_telegram_bot", "PurpleMyst", ensure_exists=True))
        / "bot.log"
    )
    level = logging.INFO

    # Create a console handler with color formatting
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(ColorFormatter(datefmt="%Y-%m-%d %H:%M:%S"))

    # Create a timed rotating file handler with compression
    file_handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        backupCount=7,  # Rotate logs daily, keep 7 days
    )
    file_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
    )
    file_handler.namer = lambda name: name + ".gz"
    file_handler.rotator = lambda source, _: compress_log_file(source)

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers (avoid duplicate logs if called multiple times)
    root_logger.handlers.clear()

    # Add the handlers to the root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Silence the overly verbose loggers from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)


colorama.init()
setup_global_logging()
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert context.bot_data is not None
    assert update.message is not None
    assert update.effective_user is not None

    user_id = update.effective_user.id

    if user_id in context.bot_data.get("users", set()):
        await update.message.reply_text("👋 Ciao! Sei già sbloccato.")
        return

    match context.args:
        case [key]:
            if key != os.getenv("SECRET_KEY"):
                logger.warning(f"Invalid secret key {key} from user {user_id}")
                await update.message.reply_text("🔒 Chiave segreta errata. Riprova.")
                return

            if update.effective_user is not None:
                logger.info(f"User {user_id} has unlocked the bot")
                await update.message.reply_text("🔓 Benvenuto! Ora puoi usare il bot.")
                context.bot_data.setdefault("users", set()).add(user_id)

        case _:
            logger.info(f"User {user_id} tried to access the bot without a secret key")
            await update.message.reply_text(
                "Ciao! Per usare questo bot, devi conoscere la chiave segreta. "
                "Scrivila dopo il comando /start 🤫🔑"
            )


async def start_server(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert context.bot_data is not None
    assert update.message is not None
    assert update.effective_user is not None

    user_id = update.effective_user.id

    if user_id not in context.bot_data.get("users", set()):
        logger.warning(f"User {user_id} tried to start the server without unlocking the bot")
        await update.message.reply_text(
            "🔒 Devi sbloccare il bot prima di poter avviare il server."
        )
        return

    try:
        subprocess.Popen(["bash", Path(__file__).parent / "start_server.sh"])
    except Exception as e:
        logger.error(f"Error starting the server: {e}")
        await update.message.reply_text("❌ Errore nell'avvio del server.")
        return
    else:
        logger.info(f"User {user_id} has started the server")
        await update.message.reply_text("🚀 Server avviato con successo!")


async def stop_server(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert context.bot_data is not None
    assert update.message is not None
    assert update.effective_user is not None

    user_id = update.effective_user.id

    if user_id not in context.bot_data.get("users", set()):
        logger.warning(f"User {user_id} tried to stop the server without unlocking the bot")
        await update.message.reply_text(
            "🔒 Devi sbloccare il bot prima di poter arrestare il server."
        )
        return

    try:
        subprocess.Popen(["bash", Path(__file__).parent / "stop_server.sh"])
    except Exception as e:
        logger.error(f"Error stopping the server: {e}")
        await update.message.reply_text("❌ Errore nell'arresto del server.")
        return
    else:
        logger.info(f"User {user_id} has stopped the server")
        await update.message.reply_text("🛑 Server arrestato con successo!")


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert context.bot_data is not None
    assert update.message is not None
    assert update.effective_user is not None

    user_id = update.effective_user.id

    if user_id not in context.bot_data.get("users", set()):
        logger.warning(f"User {user_id} tried to access the help command without unlocking the bot")
        await update.message.reply_text("🔒 Devi sbloccare il bot per poter usare questo comando.")
        return

    await update.message.reply_text(
        "ℹ️ Questo bot ti permette di avviare e arrestare un server Minecraft. "
        "Per iniziare, scrivi /start per sbloccare il bot. "
        "Dopo averlo sbloccato, puoi avviare il server con /start_server e arrestarlo con /stop_server."
    )


def main():
    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if token is None:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in .env file")

    application = (
        ApplicationBuilder()
        .token(token)
        .persistence(
            PicklePersistence(
                Path(
                    platformdirs.user_data_dir("mc_telegram_bot", "PurpleMyst", ensure_exists=True)
                )
                / "data.pkl"
            )
        )
        .build()
    )

    start_handler = CommandHandler("start", start)
    application.add_handler(start_handler)

    start_server_handler = CommandHandler("start_server", start_server)
    application.add_handler(start_server_handler)

    stop_server_handler = CommandHandler("stop_server", stop_server)
    application.add_handler(stop_server_handler)

    help_handler = CommandHandler("help", help)
    application.add_handler(help_handler)

    application.run_polling()


if __name__ == "__main__":
    main()
