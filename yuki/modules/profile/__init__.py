from telegram.ext import Application

from .profile import PROFILE
from .xp_listener import XP_HANDLER


def init(app: Application):
    app.add_handler(PROFILE)
    app.add_handler(XP_HANDLER, group=10)