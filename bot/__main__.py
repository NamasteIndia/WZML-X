# ruff: noqa: E402

import os
import psutil
import asyncio
import weakref

from datetime import datetime
from logging import Formatter
from pytz import timezone

from .core.config_manager import Config

Config.load()

from . import LOGGER, bot_loop
from .core.tg_client import TgClient


def log_ram_usage():
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()  # in bytes
    rss_mb = mem_info.rss / (1024 ** 2)  # Resident Set Size in MB
    vms_mb = mem_info.vms / (1024 ** 2)  # Virtual Memory Size in MB
    LOGGER.info(f"RAM Usage: RSS={rss_mb:.2f} MB, VMS={vms_mb:.2f} MB")
    return rss_mb


async def periodic_ram_logger(interval=300):
    """Periodically log RAM usage every `interval` seconds."""
    while True:
        rss = log_ram_usage()
        # If RSS is above threshold, trigger idle service restart
        if rss >= Config.MEMORY_RESTART_THRESHOLD_MB:  # Define this threshold in your config, e.g. 500MB
            LOGGER.warning(f"RAM usage high ({rss:.2f} MB). Restarting idle services.")
            try:
                await restart_idle_services()
            except Exception as e:
                LOGGER.error(f"Error restarting idle services: {e}")
        await asyncio.sleep(interval)


async def restart_idle_services():
    """
    Restart idle/background services without restarting entire bot.
    Modify this function as needed to restart specific services you consider idle.
    """
    LOGGER.info("Restarting idle services...")

    # Example restart sequence — adapt according to your bot's idle services and their APIs:
    # You can add or remove services to be restarted here

    from .core.jdownloader_booter import jdownloader
    from .helper.ext_utils.telegraph_helper import telegraph
    from .helper.mirror_leech_utils.rclone_utils.serve import rclone_serve_booter
    from .modules import (
        initiate_search_tools,
        get_packages_version,
        restart_notification,
    )
    from .helper.ext_utils.files_utils import clean_all

    # If these services have dedicated restart or reload methods, call them; else call their boot/init
    await jdownloader.boot()
    await telegraph.create_account()
    await rclone_serve_booter()
    await initiate_search_tools()
    await get_packages_version()
    await restart_notification()
    await clean_all()

    LOGGER.info("Idle services restarted successfully.")


# --- Begin cache improvements for memory management ---

# Weak caches for Telegram Chat and Message objects
chat_cache = weakref.WeakValueDictionary()
message_cache = weakref.WeakValueDictionary()


def cache_chat(chat):
    """Cache chat object weakly by its ID."""
    try:
        chat_cache[chat.id] = chat
    except Exception as e:
        LOGGER.warning(f"Failed to cache chat {getattr(chat, 'id', None)}: {e}")


def cache_message(message):
    """Cache message object weakly by its message_id."""
    try:
        message_cache[message.message_id] = message
    except Exception as e:
        LOGGER.warning(f"Failed to cache message {getattr(message, 'message_id', None)}: {e}")


# --- End cache improvements ---


async def main():
    from asyncio import gather

    from .core.startup import (
        load_configurations,
        load_settings,
        save_settings,
        update_aria2_options,
        update_nzb_options,
        update_qb_options,
        update_variables,
    )

    await load_settings()
    log_ram_usage()

    def changetz(*args):
        return datetime.now(timezone(Config.TIMEZONE)).timetuple()

    Formatter.converter = changetz

    await gather(
        TgClient.start_bot(),
        TgClient.start_user(),
        TgClient.start_helper_bots(),
    )
    log_ram_usage()

    await gather(load_configurations(), update_variables())
    log_ram_usage()

    from .core.torrent_manager import TorrentManager

    await TorrentManager.initiate()
    log_ram_usage()

    await gather(
        update_qb_options(),
        update_aria2_options(),
        update_nzb_options(),
    )
    log_ram_usage()

    from .core.jdownloader_booter import jdownloader
    from .helper.ext_utils.files_utils import clean_all
    from .helper.ext_utils.telegraph_helper import telegraph
    from .helper.mirror_leech_utils.rclone_utils.serve import rclone_serve_booter
    from .modules import (
        get_packages_version,
        initiate_search_tools,
        restart_notification,
    )

    await gather(
        save_settings(),
        jdownloader.boot(),
        clean_all(),
        initiate_search_tools(),
        get_packages_version(),
        restart_notification(),
        telegraph.create_account(),
        rclone_serve_booter(),
    )
    log_ram_usage()

    # Start periodic RAM usage logging with idle service restarts triggered if memory high
    asyncio.create_task(periodic_ram_logger(interval=3600))  # check every hour


bot_loop.run_until_complete(main())

from .core.handlers import add_handlers
from .helper.ext_utils.bot_utils import create_help_buttons
from .helper.listeners.aria2_listener import add_aria2_callbacks

add_aria2_callbacks()
create_help_buttons()
add_handlers()

from pyrogram.filters import regex
from pyrogram.handlers import CallbackQueryHandler

from .core.handlers import add_handlers
from .helper.ext_utils.bot_utils import new_task
from .helper.telegram_helper.filters import CustomFilters
from .helper.telegram_helper.message_utils import (
    delete_message,
    edit_message,
    send_message,
)

# Example: wrap message/chat caching around message handlers as illustration
# You must adapt this to your actual message handler setup

from pyrogram import Client


@Client.on_message()
async def message_handler(client, message):
    # Cache the message and chat object weakly to avoid memory retention
    cache_message(message)
    if message.chat:
        cache_chat(message.chat)
    # Your existing message processing logic here
    # ...


@new_task
async def restart_sessions_confirm(_, query):
    data = query.data.split()
    message = query.message
    if data[1] == "confirm":
        reply_to = message.reply_to_message
        restart_message = await send_message(reply_to, "Restarting Session(s)...")
        await delete_message(message)
        await TgClient.reload()
        add_handlers()
        TgClient.bot.add_handler(
            CallbackQueryHandler(
                restart_sessions_confirm,
                filters=regex("^sessionrestart") & CustomFilters.sudo,
            )
        )
        await edit_message(restart_message, "Session(s) Restarted Successfully!")
    else:
        await delete_message(message)


TgClient.bot.add_handler(
    CallbackQueryHandler(
        restart_sessions_confirm,
        filters=regex("^sessionrestart") & CustomFilters.sudo,
    )
)

LOGGER.info("WZ Client(s) & Services Started !")
bot_loop.run_forever()
