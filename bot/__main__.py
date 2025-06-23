# ruff: noqa: E402

from .core.config_manager import Config

Config.load()

from datetime import datetime
from logging import Formatter
from pytz import timezone

from . import LOGGER, bot_loop
from .core.tg_client import TgClient

import asyncio
import psutil

# Example config flags. Replace with your actual config management.
ENABLE_JDOWNLOADER = getattr(Config, "ENABLE_JDOWNLOADER", False)
ENABLE_RCLONE = getattr(Config, "ENABLE_RCLONE", True)
ENABLE_TELEGRAPH = getattr(Config, "ENABLE_TELEGRAPH", True)
ENABLE_HELPER_BOTS = getattr(Config, "ENABLE_HELPER_BOTS", True)

MAX_RAM_USAGE = 400 * 1024 * 1024  # 400 MB
CHECK_INTERVAL = 60  # check every 60 seconds
EXCLUDE_PROCESSES = ['python', 'python3', 'aria2c', 'qbittorrent-nox', 'rclone']  # Add your known essential processes here


async def kill_high_ram_processes():
    while True:
        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                if proc.info['name'] in EXCLUDE_PROCESSES:
                    continue
                mem_usage = proc.info['memory_info'].rss
                if mem_usage >= MAX_RAM_USAGE:
                    LOGGER.warning(f"Killing {proc.info['name']} (PID: {proc.info['pid']}) - RAM: {mem_usage / (1024 * 1024):.2f} MB")
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        await asyncio.sleep(CHECK_INTERVAL)


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

    def changetz(*args):
        return datetime.now(timezone(Config.TIMEZONE)).timetuple()

    Formatter.converter = changetz

    # Lazy start helper bots only if enabled.
    tg_start_tasks = [TgClient.start_bot(), TgClient.start_user()]
    if ENABLE_HELPER_BOTS:
        tg_start_tasks.append(TgClient.start_helper_bots())
    await gather(*tg_start_tasks)

    await gather(load_configurations(), update_variables())

    from .core.torrent_manager import TorrentManager

    await TorrentManager.initiate()

    await gather(
        update_qb_options(),
        update_aria2_options(),
        update_nzb_options(),
    )

    # Lazy imports and conditional starts for heavy services.
    tasks = [save_settings()]

    if ENABLE_JDOWNLOADER:
        from .core.jdownloader_booter import jdownloader
        tasks.append(jdownloader.boot())

    # Clean files only if needed (you may want to make this conditional/configurable)
    from .helper.ext_utils.files_utils import clean_all
    tasks.append(clean_all())

    from .modules import (
        get_packages_version,
        initiate_search_tools,
        restart_notification,
    )
    tasks.extend([
        initiate_search_tools(),
        get_packages_version(),
        restart_notification(),
        kill_high_ram_processes(),  # ✅ RAM monitor task added here
    ])

    if ENABLE_TELEGRAPH:
        from .helper.ext_utils.telegraph_helper import telegraph
        tasks.append(telegraph.create_account())

    if ENABLE_RCLONE:
        from .helper.mirror_leech_utils.rclone_utils.serve import rclone_serve_booter
        tasks.append(rclone_serve_booter())

    await gather(*tasks)


bot_loop.run_until_complete(main())


# Lazy import handlers and UI setup
def setup_handlers():
    from .core.handlers import add_handlers
    from .helper.ext_utils.bot_utils import create_help_buttons
    from .helper.listeners.aria2_listener import add_aria2_callbacks

    add_aria2_callbacks()
    create_help_buttons()
    add_handlers()


setup_handlers()

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
