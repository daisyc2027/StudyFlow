from zoneinfo import ZoneInfo

from flask import current_app


def now():
    return current_app.config['CLOCK']()


def today(user):
    return now().astimezone(ZoneInfo(user.timezone)).date()
