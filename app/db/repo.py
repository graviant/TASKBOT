from __future__ import annotations
from decimal import Decimal
from typing import Any
import logging
from typing import List, Dict, Optional

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


async def disable_assignment(assignment_id: int) -> bool:
    sql = "UPDATE assignments SET is_active = FALSE WHERE id = %s AND is_active = TRUE"
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute(sql, (assignment_id,))
                return cur.rowcount > 0


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


async def admin_delete_assignment(assignment_id: int) -> bool:
    sql = "DELETE FROM assignments WHERE id = %s AND is_active = TRUE"
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute(sql, (assignment_id,))
                return cur.rowcount > 0


# 1) Список разрешённых пользователей (кэш на старте)
async def list_member_user_ids() -> List[int]:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id FROM users WHERE is_member = true")
            rows = await cur.fetchall()
            return [int(r[0]) for r in rows]


# 2) Обновить флаг членства
async def set_user_membership(user_id: int, is_member: bool) -> None:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO users (id, is_member)
                VALUES (%s, %s)
                ON CONFLICT (id) DO UPDATE SET is_member = EXCLUDED.is_member
                """,
                (user_id, is_member),
            )


# 3) Апсертом сохраняем пользователя
async def upsert_user_full(
        user_id: int,
        username: Optional[str],
        full_name: Optional[str],
        is_admin: bool,
        is_member: bool,
) -> None:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO users (id, username, full_name, is_admin, is_member)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET username = EXCLUDED.username,
                    full_name = EXCLUDED.full_name,
                    is_admin = EXCLUDED.is_admin,
                    is_member = EXCLUDED.is_member
                """,
                (user_id, username, full_name, is_admin, is_member),
            )


# 4) Справочник заказчиков
async def list_customers(active_only: bool = True) -> List[Dict]:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            if active_only:
                await cur.execute("SELECT id, name FROM customers WHERE is_active = true ORDER BY name")
            else:
                await cur.execute("SELECT id, name, is_active FROM customers ORDER BY name")
            rows = await cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in rows]


async def get_customer_name(customer_id: int) -> Optional[str]:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT name FROM customers WHERE id = %s", (customer_id,))
            row = await cur.fetchone()
            return row[0] if row else None


# 5) Создание задания (customer_id + snapshot)
async def create_assignment(
        author_id: int,
        work_type: str,
        deadline_at,  # datetime | None
        project: Optional[str],
        customer_id: Optional[int],
        total_volume: Decimal,
        comment: Optional[str],
) -> int:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO assignments
                    (author_id, work_type, deadline_at, project, customer_id, customer_name_snapshot, total_volume, comment)
                VALUES
                    (%s, %s, %s, %s, %s, (SELECT name FROM customers WHERE id = %s), %s, %s)
                RETURNING id
                """,
                (author_id, work_type, deadline_at, project, customer_id, customer_id, total_volume, comment),
            )
            aid = await cur.fetchone()
            return int(aid[0])


# 6) Помечаем опубликованным (чат/сообщение)
async def mark_assignment_published(assignment_id: int, chat_id: int, message_id: int) -> None:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE assignments
                SET published_chat_id=%s, published_message_id=%s
                WHERE id=%s
                """,
                (chat_id, message_id, assignment_id),
            )


# 7) «Мои выданные задания» — имя заказчика стабильно
async def my_assignments(author_id: int) -> List[Dict]:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT a.*,
                       COALESCE(a.customer_name_snapshot, c.name) AS customer_name
                FROM assignments a
                LEFT JOIN customers c ON c.id = a.customer_id
                WHERE a.author_id = %s
                ORDER BY a.created_at DESC
                LIMIT 50
                """,
                (author_id,),
            )
            rows = await cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in rows]


# 8) (если используете) открытые задачи исполнителя
async def my_open_claims(user_id: int) -> List[Dict]:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, assignment_id, volume
                FROM task_claims
                WHERE executor_id=%s AND done=false
                ORDER BY created_at DESC
                """,
                (user_id,),
            )
            rows = await cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in rows]


# 9) (если используете) удалить мою незакрытую задачу
async def delete_my_open_claim(claim_id: int, user_id: int) -> bool:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                DELETE FROM task_claims
                WHERE id=%s AND executor_id=%s AND done=false
                """,
                (claim_id, user_id),
            )
            return cur.rowcount > 0


# 10) (если используете) список свободных заданий для напоминаний
async def list_free_assignments() -> List[Dict]:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT a.id, a.work_type, a.published_chat_id
                FROM assignments a
                WHERE a.is_active = true
                ORDER BY a.created_at DESC
                LIMIT 100
                """
            )
            rows = await cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in rows]


# 11) (если используете) расчёт свободного объёма
async def assignment_free_volume(assignment_id: int) -> Decimal:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            # всего
            await cur.execute("SELECT total_volume FROM assignments WHERE id=%s", (assignment_id,))
            row = await cur.fetchone()
            total = Decimal(row[0]) if row else Decimal("0")

            # занято
            await cur.execute(
                "SELECT COALESCE(SUM(volume), 0) FROM task_claims WHERE assignment_id=%s AND done=false",
                (assignment_id,),
            )
            row2 = await cur.fetchone()
            taken = Decimal(row2[0]) if row2 and row2[0] is not None else Decimal("0")

            return total - taken
