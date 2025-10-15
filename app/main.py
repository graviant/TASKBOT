import asyncio
import sys
import logging
from decimal import Decimal
from pathlib import Path
import re

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiohttp import ClientConnectorError
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .config import load_config
from .db.pool import init_pool, get_pool, close_pool
from .db import repo

from .routers import start as r_start
from .routers import user_tasks as r_user
from .routers import admin as r_admin
from .routers import group as r_group

from .middlewares.admin import AdminMiddleware
from .middlewares.members import AllMiddleware
from .services.allowed import AllowedUsers

CUSTOMERS_SEED = [
    "Администрация Главы Чувашии",
    "Глава Чувашии",
    "Госпаблики",
    "Госпаблики детских садов",
    "Госпаблики ОМСУ",
    "Госпаблики школ",
    "Кабмин Чувашии",
    "Медиацентр Чувашии",
    "Минздрав Чувашии",
    "Минкультуры Чувашии",
    "Минобразования Чувашии",
    "Минсельхоз Чувашии",
    "Минспорт Чувашии",
    "Минстрой Чувашии",
    "Минтруд Чувашии",
    "Минцифры Чувашии",
    "Минэкономразвития Чувашии",
    "Молодежная политика",
    "Фонд защитников отечества",
    "ЦУР Чувашии",
    "Военкомат Чувашии",
    "Госветслужба",
    "Госпаблик Чебоксары",
    "Госпаблики спортивных школ",
    "Минтранс Чувашии",
]

# аккуратный сплит по ';' с учётом кавычек и $$...$$
_SQL_SPLIT_RE = re.compile(r";\s*(?=(?:[^'\"$]|'[^']*'|\"[^\"]*\"|\$\$.*?\$\$)*$)", re.DOTALL)


async def apply_schema():
    """
    1) Применяем schema.sql: бьём на стейтменты и выполняем по одному.
    2) Проверяем, что таблица customers создана.
    3) Если customers пуста — засеваем начальными значениями.
    """
    pool = get_pool()

    # 1) читаем schema.sql
    schema_path = Path(__file__).resolve().parent / "db" / "schema.sql"
    if not schema_path.exists():
        raise FileNotFoundError(f"schema.sql not found at: {schema_path}")
    schema_sql = schema_path.read_text(encoding="utf-8")

    # 2) разбиваем на отдельные запросы
    statements = [s.strip() for s in _SQL_SPLIT_RE.split(schema_sql) if s.strip()]

    async with pool.connection() as conn:
        async with conn.transaction():
            for i, stmt in enumerate(statements, 1):
                try:
                    await conn.execute(stmt)
                except Exception as e:
                    preview = (stmt.replace("\n", " ")[:220] + "…") if len(stmt) > 220 else stmt
                    raise RuntimeError(f"Schema statement #{i} failed: {preview}") from e

    # 3) sanity-check: существует ли таблица customers
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute("select to_regclass('public.customers')")
                exists = (await cur.fetchone())[0]
                if not exists:
                    raise RuntimeError("Table 'customers' was not created. Check schema.sql content.")

    # 4) seed customers (если пусто)
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute("select count(*) from customers")
                count = (await cur.fetchone())[0]
                if count == 0:
                    for name in CUSTOMERS_SEED:
                        await cur.execute(
                            "insert into customers(name) values (%s) on conflict (name) do nothing",
                            (name,),
                        )


async def _probe_db() -> None:
    pool = get_pool()
    async with pool.connection() as conn:
        await conn.execute("select 1")


async def remind_job(bot: Bot):
    from .services.publisher import assignment_markup
    cfg = load_config()
    ass = await repo.list_free_assignments()
    me = await bot.me()
    for a in ass:
        free = await repo.assignment_free_volume(a["id"])
        if free <= Decimal("0") or not a["published_chat_id"]:
            continue
        # было:
        # thread_id = cfg.threads_by_worktype.get(a["work_type"])
        # стало:
        thread_id = await repo.thread_id_for_worktype(a["work_type"])

        text = f"🔔 Напоминание по заданию #{a['id']}: свободно {free}"
        await bot.send_message(
            a["published_chat_id"],
            text,
            message_thread_id=thread_id,
            reply_markup=assignment_markup(a["id"], me.username),
        )


async def main():
    logging.info("Loading config…")
    cfg = load_config()
    tmask = (cfg.bot_token[:8] + "…") if getattr(cfg, "bot_token", None) else "<EMPTY>"
    logging.info("BOT_TOKEN looks like: %s", tmask)

    logging.info("Init DB pool…")
    await init_pool(cfg.db_dsn)

    logging.info("Probing DB connectivity…")
    await _probe_db()

    logging.info("Applying schema…")
    await apply_schema()

    # --- Allowed cache ---
    logging.info("Loading allowed members cache…")
    allowed = AllowedUsers()
    try:
        member_ids = await repo.list_member_user_ids()  # SELECT id FROM users WHERE is_member = true
        await allowed.load(member_ids)
        logging.info("Allowed cache loaded: %d members", len(member_ids))
    except Exception:
        logging.exception("Failed to load allowed members; continue with empty cache")
        await allowed.load([])

    # --- Bot / Dispatcher ---
    logging.info("Creating Bot/Dispatcher…")
    session = AiohttpSession()
    bot = Bot(
        cfg.bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),  # aiogram 3.7+ так
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp["allowed"] = allowed

    # --- Middlewares ---
    try:
        logging.info("Attaching middlewares…")
        dp.message.middleware(AllMiddleware(cfg.admins, allowed))
        r_admin.router.message.middleware(AdminMiddleware(cfg.admins))
        logging.info("Middlewares attached")
    except Exception:
        logging.exception("Middlewares setup failed")
        return

    # --- Routers ---
    for name, router in [
        ("start", r_start.router),
        ("user_tasks", r_user.router),
        ("admin", r_admin.router),
        ("group", r_group.router),
    ]:
        try:
            logging.info("Including router: %s…", name)
            dp.include_router(router)
            logging.info("Included router: %s", name)
        except Exception:
            logging.exception("Router include failed: %s", name)
            return

    # --- Проверка токена / сети ---
    try:
        logging.info("Authorizing bot via getMe()…")
        me = await bot.me()
        logging.info("Bot authorized: @%s (id=%s)", me.username, me.id)
    except ClientConnectorError:
        logging.exception("Cannot connect to api.telegram.org:443 (network/proxy/SSL)")
        return
    except Exception:
        logging.exception("Bot authorization failed (check BOT_TOKEN / network)")
        return

    # --- Scheduler ---
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(remind_job, "interval", minutes=cfg.remind_every_min, args=[bot])
    scheduler.start()
    logging.info("Scheduler started. Starting polling…")

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        logging.info("Shutting down…")
        try:
            if scheduler.running:
                scheduler.shutdown(wait=False)
        except Exception as e:
            logging.exception("Scheduler shutdown error: %s", e)
        try:
            await bot.session.close()
        except Exception as e:
            logging.exception("Bot session close error: %s", e)
        try:
            await close_pool()
        except Exception as e:
            logging.exception("DB pool close error: %s", e)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("aiohttp").setLevel(logging.INFO)

    # Windows: psycopg async → нужен SelectorEventLoop
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    else:
        try:
            import uvloop

            uvloop.install()
        except Exception:
            pass

    try:
        asyncio.run(main())
    except Exception:
        logging.exception("Fatal error in main()")
        raise
