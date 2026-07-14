from telegram.ext import Application

from .rep import REP


def init(app: Application):
    app.add_handler(REP)