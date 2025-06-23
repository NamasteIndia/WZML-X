# ruff: noqa: E402

import os
import psutil
from logging import Formatter
from datetime import datetime
from pytz import timezone

from .core.config_manager import Config

Config.load()

from . import LOGGER, bot_loop
from .core.tg_client import TgClient


def get_total_rss_mb() -> float:
    """
    Calculate total RSS memory in MB for current process and all its children.
    This provides a more accurate measure of actual RAM used by the entire process tree,
    closer to what Heroku reports as dyno memory usage.
    """
    try:
        rss = 0
        proc = psutil.Process(os.getpid())
        rss += proc.memory_info().rss
        # Safely sum memory of all child processes recursively
        for child in proc.children(recursive=True):
            try:
                rss += child.memory_info().rss
            except Exception:
                pass
        return rss / (1024 ** 2)
    except Exception as e:
        LOGGER.error(f"Failed to get total RSS memory: {e}")
        return 0.0


def log_process_tree_memory():
    proc = psutil.Process(os.getpid())
    LOGGER.info(
        f"Main PID: {proc.pid}, RSS: {proc.memory_info().rss / (1024**2):.2f} MB, CMD: {' '.join(proc.cmdline())}"
    )
    for child in proc.children(recursive=True):
        try:
            mem = child.memory_info().rss / (1024 ** 2)
            cmdline = " ".join(child.cmdline())
            LOGGER.info(f"Child PID: {child.pid}, RSS: {mem:.2f} MB, CMD: {cmdline}")
        except Exception:
            continue


def log_ram_usage() -> float:
    total_rss_mb = get_total_rss_mb()
    process = psutil.Process(os.getpid())
    vms_mb = process.memory_info().vms / (1024 ** 2)  # Virtual Memory Size in MB
    LOGGER.info(f"RAM Usage: Total RSS={total_rss_mb:.2f} MB, Main Process VMS={vms_mb:.2f} MB")
    log_process_tree_memory()
    return total_rss_mb


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

    await gather(
        TgClient.start_bot(), TgClient.start_user(), TgClient.start_helper_bots()
    )

    await gather(load_configurations(), update_variables())

    from .core.torrent_manager import TorrentManager

    await TorrentManager.initiate()
    await gather(
        update_qb_options(),
        update_aria2_options(),
        update_nzb_options(),
    )

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

    # Log memory usage at startup and after initializations to help track usage
    log_ram_usage()


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
