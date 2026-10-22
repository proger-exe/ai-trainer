"""Smallest check that fails if wiring breaks: config parsing and every router module importing."""
import importlib
import os

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "1:test")
os.environ.setdefault("GEMINI_API_TOKEN", "test")
os.environ.setdefault("ADMIN_IDS", "1, 2")


def test_config_parses_env():
    from core.config import Config

    assert Config.validate()
    assert Config.ADMIN_IDS == [1, 2]


def test_modules_import():
    for name in ("bot.routers", "atlant.routers", "api_server", "bot.services.supabase_poller"):
        importlib.import_module(name)
