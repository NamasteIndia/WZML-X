# ruff: noqa: E402

import os
import psutil
import logging
import asyncio
import tracemalloc

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


async def periodic_ram_logger(interval=300):
    while True:
        log_ram_usage()
        await asyncio.sleep(interval)


async def periodic_memory_snapshot(interval=600):
    """
    Periodically log top memory allocation differences using tracemalloc.
    """
    tracemalloc.start()
    snapshot1 = tracemalloc.take_snapshot()
    while True:
        await asyncio.sleep(interval)
        snapshot2 = tracemalloc.take_snapshot()
        top_stats = snapshot2.compare_to(snapshot1, 'lineno')
        LOGGER.info("Top 10 memory allocation differences since last snapshot:")
        for stat in top_stats[:10]:
            LOGGER.info(stat)
        snapshot1 = snapshot2


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
    log_ram_usage()  # RAM usage after loading settings

    def changetz(*args):
        return datetime.now(timezone(Config.TIMEZONE)).timetuple()

    Formatter.converter = changetz

    await gather(
        TgClient.start_bot(),
        TgClient.start_user(),
        TgClient.start_helper_bots(),
    )
    log_ram_usage()  # RAM usage after starting TgClients

    await gather(load_configurations(), update_variables())
    log_ram_usage()  # RAM usage after loading configurations and variables

    from .core.torrent_manager import TorrentManager

    await TorrentManager.initiate()
    log_ram_usage()  # RAM usage after TorrentManager initiation

    await gather(
        update_qb_options(),
        update_aria2_options(),
        update_nzb_options(),
    )
    log_ram_usage()  # RAM usage after updating download options

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
    log_ram_usage()  # Final RAM usage after startup completion

    # Schedule periodic RAM logging every 5 minutes (300s)
    asyncio.create_task(periodic_ram_logger())

    # Schedule periodic tracemalloc memory snapshot logging every 10 minutes (600s)
    asyncio.create_task(periodic_memory_snapshot())


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
