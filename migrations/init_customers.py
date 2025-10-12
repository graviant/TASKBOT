# -*- coding: utf-8 -*-
"""
Синхронное создание таблицы customers — просто и надежно (без async/pool).
Запускать из корня проекта:
    python -m migrations.init_customers
или настройте в PyCharm "Module name": migrations.init_customers
"""
from TASKBOT.app.config import load_config
import psycopg  # pip install psycopg[binary]

CUSTOMERS = [
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

if __name__ == "__main__":
    cfg = load_config()
    with psycopg.connect(cfg.db_dsn) as conn, conn.cursor() as cur:
        for name in CUSTOMERS:
            cur.execute(
                "INSERT INTO customers (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
                (name,)
            )
        conn.commit()
    print("✅ Таблица customers заполнена начальными данными.")

