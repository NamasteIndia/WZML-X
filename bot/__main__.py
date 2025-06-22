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


def log_ram_usage() -> float:
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()  # in bytes
    rss_mb = mem_info.rss / (1024 ** 2)  # Resident Set Size in MB
    vms_mb = mem_info.vms / (1024 ** 2)  # Virtual Memory Size in MB
    LOGGER.info(f"RAM Usage: RSS={rss_mb:.2f} MB, VMS={vms_mb:.2f} MB")
    return rss_mb


async def try_hibernate_or_shutdown(service, name):
    """
    Try to hibernate the service if possible to save RAM,
    otherwise shutdown it. Return True if any action succeeded.
    """
    mem_before = log_ram_usage()
    freed = False

    if hasattr(service, "hibernate") and callable(service.hibernate):
        try:
            await service.hibernate()
            LOGGER.info(f"Hibernated {name} successfully.")
            freed = True
        except Exception as e:
            LOGGER.warning(f"Failed to hibernate {name}: {e}")

    if not freed and hasattr(service, "shutdown") and callable(service.shutdown):
        try:
            await service.shutdown()
            LOGGER.info(f"Shutdown {name} successfully.")
            freed = True
        except Exception as e:
            LOGGER.warning(f"Failed to shutdown {name}: {e}")

    mem_after = log_ram_usage()
    LOGGER.info(f"{name}: RAM usage before {mem_before:.2f} MB, after {mem_after:.2f} MB")
    return freed


async def manage_idle_services():
    """
    Instead of restarting idle services, hibernate or shutdown them
    whichever frees more RAM, for improved memory management.
    """
    LOGGER.info("Managing idle services for RAM optimization...")

    from .core.jdownloader_booter import jdownloader
    from .helper.ext_utils.telegraph_helper import telegraph
    from .helper.mirror_leech_utils.rclone_utils.serve import rclone_serve_booter
    from .modules import (
        initiate_search_tools,
        get_packages_version,
        restart_notification,
    )
    from .helper.ext_utils.files_utils import clean_all

    # Try hibernate or shutdown on each service
    await try_hibernate_or_shutdown(jdownloader, "JDownloader")
    await try_hibernate_or_shutdown(telegraph, "Telegraph")
    await try_hibernate_or_shutdown(rclone_serve_booter, "Rclone Serve")

    # These modules may not have hibernate/shutdown - run as usual to refresh/free memory
    try:
        await initiate_search_tools()
        LOGGER.info("Initiated search tools to free resources.")
    except Exception as e:
        LOGGER.warning(f"Failed to initiate_search_tools: {e}")

    try:
        await get_packages_version()
        LOGGER.info("Checked packages versions.")
    except Exception as e:
        LOGGER.warning(f"Failed to get_packages_version: {e}")

    try:
        await restart_notification()
        LOGGER.info("Restarted notification module.")
    except Exception as e:
        LOGGER.warning(f"Failed to restart_notification: {e}")

    try:
        await clean_all()
        LOGGER.info("Cleaned temporary files and cache.")
    except Exception as e:
        LOGGER.warning(f"Failed to clean_all: {e}")

    LOGGER.info("Idle services managed successfully for RAM optimization.")


async def periodic_ram_logger(interval: int = 300):
    """
    Periodically log RAM usage and manage idle services if memory usage exceeds threshold.
    Runs every `interval` seconds (default 5 minutes).
    """
    while True:
        rss = log_ram_usage()

        threshold_mb = getattr(Config, "MEMORY_RESTART_THRESHOLD_MB", None)
        if threshold_mb is None:
            LOGGER.error(
                "Config missing MEMORY_RESTART_THRESHOLD_MB, skipping idle service management."
            )
        else:
            if rss >= threshold_mb:
                LOGGER.warning(
                    f"High RAM usage detected: {rss:.2f} MB >= {threshold_mb} MB. Managing idle services."
                )
                try:
                    await manage_idle_services()
                except Exception as e:
                    LOGGER.error(f"Exception managing idle services: {e}")
        await asyncio.sleep(interval)


# --- Cache improvements for memory management ---

chat_cache = weakref.WeakValueDictionary()
message_cache = weakref.WeakValueDictionary()


def cache_chat(chat):
    try:
        if chat is not None and hasattr(chat, "id"):
            chat_cache[chat.id] = chat
    except Exception as e:
        LOGGER.warning(f"Failed to cache chat with id {getattr(chat, 'id', None)}: {e}")


def cache_message(message):
    try:
        if message is not None and hasattr(message, "message_id"):
            message_cache[message.message_id] = message
    except Exception as e:
        LOGGER.warning(
            f"Failed to cache message with id {getattr(message, 'message_id', None)}: {e}"
        )


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
        try:
            return datetime.now(timezone(Config.TIMEZONE)).timetuple()
        except Exception as e:
            LOGGER.error(f"Failed to convert timezone: {e}")
            return datetime.utcnow().timetuple()

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

    # Start periodic RAM logger with idle service hibernate/shutdown on high memory usage every 5 minutes
    asyncio.create_task(periodic_ram_logger(interval=300))


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

from pyrogram import Client


@Client.on_message()
async def message_handler(client, message):
    cache_message(message)
    if message.chat:
        cache_chat(message.chat)
    # existing message processing logic


@new_task
async def restart_sessions_confirm(_, query):
    data = query.data.split()
    message = query.message
    if len(data) > 1 and data[1] == "confirm":
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
