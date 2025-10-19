# app/config.py
from __future__ import annotations
from dataclasses import dataclass
from environs import Env
import json


@dataclass(frozen=True)
class Config:
    bot_token: str
    general_chat_ids: list[int]
    threads_by_worktype: dict[str, int]
    admins: set[int]
    users: set[int] | None
    db_dsn: str
    remind_every_min: int


def load_config() -> Config:
    env = Env();
    env.read_env()

    def _int_list(s: str | None) -> list[int]:
        return [int(x) for x in s.split(",") if x.strip()] if s else []

    def _int_set(s: str | None) -> set[int]:
        return set(_int_list(s))

    threads = json.loads(env.str("THREADS_JSON", "{}"))

    return Config(
        bot_token=env.str("BOT_TOKEN"),
        general_chat_ids=_int_list(env.str("GENERAL_CHAT_IDS", "")),
        threads_by_worktype={str(k): int(v) for k, v in threads.items()},
        admins=_int_set(env.str("ADMINS", "")),
        users=_int_set(env.str("USERS", "")) or None,
        db_dsn=env.str("DB_DSN"),
        remind_every_min=env.int("REMIND_EVERY_MIN", 2),
    )
