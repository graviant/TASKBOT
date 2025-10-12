from __future__ import annotations
from decimal import Decimal
from typing import Any
import logging

from psycopg.rows import dict_row
from .pool import get_pool


# ---------- users ----------

async def upsert_user(user_id: int, username: str | None, full_name: str | None,
                      is_admin: bool, is_member: bool) -> None:
    sql = """
    INSERT INTO users (id, username, full_name, is_admin, is_member)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (id) DO UPDATE
      SET username = EXCLUDED.username,
          full_name = EXCLUDED.full_name,
          is_admin = EXCLUDED.is_admin,
          is_member = EXCLUDED.is_member
    """
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute(sql, (user_id, username, full_name, is_admin, is_member))


async def is_admin(user_id: int) -> bool:
    sql = "SELECT is_admin FROM users WHERE id = %s"
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (user_id,))
            row = await cur.fetchone()
            return bool(row[0]) if row else False


# ---------- assignments ----------

async def create_assignment(author_id: int, work_type: str, deadline_at,
                            project: str | None, customer: str | None,
                            total_volume: Decimal, comment: str | None) -> int:
    sql = """
    INSERT INTO assignments (author_id, work_type, deadline_at, project, customer, total_volume, comment)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    RETURNING id
    """
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute(sql, (author_id, work_type, deadline_at, project, customer, total_volume, comment))
                row = await cur.fetchone()
                return int(row[0])


async def mark_assignment_published(assignment_id: int, chat_id: int, msg_id: int) -> None:
    sql = "UPDATE assignments SET published_chat_id = %s, published_message_id = %s WHERE id = %s"
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute(sql, (chat_id, msg_id, assignment_id))


async def assignment_free_volume(assignment_id: int) -> Decimal:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT total_volume FROM assignments WHERE id = %s", (assignment_id,))
            row = await cur.fetchone()
            total: Decimal = row[0] if row and row[0] is not None else Decimal("0")

            await cur.execute("SELECT COALESCE(SUM(volume), 0) FROM task_claims WHERE assignment_id = %s",
                              (assignment_id,))
            row = await cur.fetchone()
            taken: Decimal = row[0] if row and row[0] is not None else Decimal("0")

            return total - taken


async def disable_assignment(assignment_id: int) -> bool:
    sql = "UPDATE assignments SET is_active = FALSE WHERE id = %s AND is_active = TRUE"
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute(sql, (assignment_id,))
                return cur.rowcount > 0


async def my_assignments(author_id: int) -> list[dict[str, Any]]:
    sql = "SELECT * FROM assignments WHERE author_id = %s ORDER BY created_at DESC LIMIT 50"
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(sql, (author_id,))
            rows = await cur.fetchall()
            return list(rows)  # уже dict-и благодаря row_factory


# ---------- claims ----------

async def take_claim(assignment_id: int, executor_id: int, volume: Decimal) -> int | None:
    free = await assignment_free_volume(assignment_id)
    if volume <= 0 or volume > free:
        return None

    sql = "INSERT INTO task_claims (assignment_id, executor_id, volume) VALUES (%s, %s, %s) RETURNING id"
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute(sql, (assignment_id, executor_id, volume))
                row = await cur.fetchone()
                return int(row[0])


async def my_open_claims(executor_id: int) -> list[dict[str, Any]]:
    sql = """
    SELECT * FROM task_claims
    WHERE executor_id = %s AND done = FALSE
    ORDER BY created_at DESC
    """
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(sql, (executor_id,))
            rows = await cur.fetchall()
            return list(rows)


async def delete_my_open_claim(claim_id: int, executor_id: int) -> bool:
    sql = "DELETE FROM task_claims WHERE id = %s AND executor_id = %s AND done = FALSE"
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute(sql, (claim_id, executor_id))
                return cur.rowcount > 0


async def admin_delete_assignment(assignment_id: int) -> bool:
    sql = "DELETE FROM assignments WHERE id = %s AND is_active = TRUE"
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute(sql, (assignment_id,))
                return cur.rowcount > 0


async def list_free_assignments() -> list[dict[str, Any]]:
    sql = "SELECT * FROM assignments WHERE is_active = TRUE ORDER BY created_at DESC LIMIT 100"
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(sql)
            rows = await cur.fetchall()
            return list(rows)


async def list_member_user_ids() -> list[int]:
    sql = "SELECT id FROM users WHERE is_member = TRUE"
    pool = get_pool()
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql)
                rows = await cur.fetchall()
                return [r[0] for r in rows]
    except Exception:
        logging.exception("list_member_user_ids() failed; returning empty list")
        return []


async def set_user_membership(user_id: int, is_member: bool) -> None:
    sql = """
    INSERT INTO users (id, is_member)
    VALUES (%s, %s)
    ON CONFLICT (id) DO UPDATE SET is_member = EXCLUDED.is_member
    """
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute(sql, (user_id, is_member))


async def upsert_user_full(user_id: int, username: str | None, full_name: str | None,
                           is_admin: bool, is_member: bool) -> None:
    sql = """
    INSERT INTO users (id, username, full_name, is_admin, is_member)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (id) DO UPDATE
      SET username = EXCLUDED.username,
          full_name = EXCLUDED.full_name,
          is_admin = EXCLUDED.is_admin,
          is_member = EXCLUDED.is_member
    """
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute(sql, (user_id, username, full_name, is_admin, is_member))


# app/db/repo.py (добавлено для работы с кнопками - список заказчиков)
async def list_customers() -> list[dict]:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.transaction():
            rows = await conn.fetch("select id, name from customers order by name")
            return [dict(r) for r in rows]

async def get_customer_name(customer_id: int) -> str | None:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.transaction():
            return await conn.fetchval("select name from customers where id=$1", customer_id)
