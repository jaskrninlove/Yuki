from telegram.ext import Application

from .balance import BALANCE
from .daily import DAILY
from .pay import PAY
from .crime import CRIME
from .leaderboard import LEADERBOARD




def init(app: Application):
    app.add_handler(BALANCE)
    app.add_handler(DAILY)
    app.add_handler(PAY)
    app.add_handler(CRIME)
    app.add_handler(LEADERBOARD)