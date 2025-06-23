from .bot_settings import send_bot_settings, edit_bot_settings
from .cancel_task import cancel, cancel_multi, cancel_all_buttons, cancel_all_update
from .chat_permission import authorize, unauthorize, add_sudo, remove_sudo
from .clone import clone_node
from .exec import aioexecute, execute, clear
from .file_selector import select, confirm_selection
from .force_start import remove_from_queue
from .gd_count import count_node
from .gd_delete import delete_file
from .gd_search import gdrive_search, select_type
from .help import arg_usage, bot_help
from .mediainfo import mediainfo
from .speedtest import speedtest
from .broadcast import broadcast
# HEAVY RAM USAGE: LAZY IMPORTS BELOW
def mirror(*args, **kwargs):
    from .mirror_leech import mirror as _mirror
    return _mirror(*args, **kwargs)
def leech(*args, **kwargs):
    from .mirror_leech import leech as _leech
    return _leech(*args, **kwargs)
def qb_leech(*args, **kwargs):
    from .mirror_leech import qb_leech as _qb_leech
    return _qb_leech(*args, **kwargs)
def qb_mirror(*args, **kwargs):
    from .mirror_leech import qb_mirror as _qb_mirror
    return _qb_mirror(*args, **kwargs)
def jd_leech(*args, **kwargs):
    from .mirror_leech import jd_leech as _jd_leech
    return _jd_leech(*args, **kwargs)
def jd_mirror(*args, **kwargs):
    from .mirror_leech import jd_mirror as _jd_mirror
    return _jd_mirror(*args, **kwargs)
def nzb_leech(*args, **kwargs):
    from .mirror_leech import nzb_leech as _nzb_leech
    return _nzb_leech(*args, **kwargs)
def nzb_mirror(*args, **kwargs):
    from .mirror_leech import nzb_mirror as _nzb_mirror
    return _nzb_mirror(*args, **kwargs)
from .restart import (
    restart_bot,
    restart_notification,
    confirm_restart,
    restart_sessions,
)
from .imdb import imdb_search, imdb_callback
# from .rss import get_rss_menu, rss_listener   # Disabled to save RAM
from .search import torrent_search, torrent_search_update, initiate_search_tools
from .nzb_search import hydra_search
from .services import start, start_cb, login, ping, log, log_cb
from .shell import run_shell
from .stats import bot_stats, stats_pages, get_packages_version
from .status import task_status, status_pages
from .users_settings import get_users_settings, edit_user_settings, send_user_settings
from .ytdlp import ytdl, ytdl_leech

__all__ = [
    "send_bot_settings",
    "edit_bot_settings",
    "cancel",
    "cancel_multi",
    "cancel_all_buttons",
    "cancel_all_update",
    "authorize",
    "unauthorize",
    "add_sudo",
    "remove_sudo",
    "clone_node",
    "aioexecute",
    "execute",
    #"hydra_search",
    "clear",
    "select",
    "confirm_selection",
    "remove_from_queue",
    "count_node",
    "delete_file",
    "gdrive_search",
    "select_type",
    "arg_usage",
    # HEAVY (LAZY) IMPORTS
    "mirror",
    "leech",
    "qb_leech",
    "qb_mirror",
    #"jd_leech",
    #"jd_mirror",
    #"nzb_leech",
    #"nzb_mirror",
    "restart_bot",
    "restart_notification",
    "confirm_restart",
    "restart_sessions",
    #"imdb_search",
    #"imdb_callback",
    # "get_rss_menu",      # Disabled to save RAM
    # "rss_listener",      # Disabled to save RAM
    #"torrent_search",
    #"torrent_search_update",
    #"initiate_search_tools",
    "start",
    "start_cb",
    #"login",
    "bot_help",
    "mediainfo",
    "speedtest",
    "broadcast",
    "ping",
    "log",
    "log_cb",
    "run_shell",
    "bot_stats",
    "stats_pages",
    "get_packages_version",
    "task_status",
    "status_pages",
    "get_users_settings",
    "edit_user_settings",
    "send_user_settings",
    "ytdl",
    "ytdl_leech",
]
