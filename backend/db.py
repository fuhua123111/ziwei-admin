# -*- coding: utf-8 -*-
"""
紫微斗数 · 数据层

需求原文要求"建本地数据库"+"能查能改"。这里用 SQLite（零部署、单文件），
完整实现 CRUD + 搜索 + 分页 + 软删除 + 变更审计。

表设计：
  charts          星盘主表
  chart_palaces   十二宫（便于按宫位查询）
  audit_log       审计日志（谁在什么时候改了什么）
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_DB = os.path.join(ROOT, "data", "ziwei.db")

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS charts (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT    NOT NULL,
    gender         TEXT    NOT NULL,
    solar_date     TEXT    NOT NULL,
    time_index     INTEGER NOT NULL,
    lunar_date     TEXT,
    chinese_date   TEXT,
    time_name      TEXT,
    zodiac         TEXT,
    sign           TEXT,
    soul           TEXT,
    body           TEXT,
    five_elements  TEXT,
    soul_branch    TEXT,
    body_branch    TEXT,
    raw_json       TEXT    NOT NULL DEFAULT '{}',
    note           TEXT    NOT NULL DEFAULT '',
    tags           TEXT    NOT NULL DEFAULT '',
    star_rating    INTEGER NOT NULL DEFAULT 0,
    is_deleted     INTEGER NOT NULL DEFAULT 0,
    created_at     TEXT    NOT NULL,
    updated_at     TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_charts_name   ON charts(name);
CREATE INDEX IF NOT EXISTS idx_charts_solar  ON charts(solar_date);
CREATE INDEX IF NOT EXISTS idx_charts_del    ON charts(is_deleted);

CREATE TABLE IF NOT EXISTS chart_palaces (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    chart_id     INTEGER NOT NULL REFERENCES charts(id) ON DELETE CASCADE,
    palace_index INTEGER NOT NULL,
    name         TEXT    NOT NULL,
    heavenly_stem TEXT,
    earthly_branch TEXT,
    is_body      INTEGER NOT NULL DEFAULT 0,
    major_stars  TEXT    NOT NULL DEFAULT '',
    minor_stars  TEXT    NOT NULL DEFAULT '',
    UNIQUE(chart_id, palace_index)
);

CREATE INDEX IF NOT EXISTS idx_palace_chart ON chart_palaces(chart_id);
CREATE INDEX IF NOT EXISTS idx_palace_stars ON chart_palaces(major_stars);

CREATE TABLE IF NOT EXISTS audit_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    chart_id   INTEGER,
    action     TEXT NOT NULL,
    detail     TEXT,
    created_at TEXT NOT NULL
);
"""


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Database:
    """线程安全的 SQLite 封装（FastAPI 多线程下每个线程独立连接）。"""

    def __init__(self, path: str = DEFAULT_DB):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._local = threading.local()
        with self.conn() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def conn(self):
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self.path, timeout=15)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        try:
            yield self._local.conn
            self._local.conn.commit()
        except Exception:
            self._local.conn.rollback()
            raise

    # ---------------- 审计 ----------------
    def _audit(self, c, chart_id: Optional[int], action: str, detail: str = "") -> None:
        c.execute(
            "INSERT INTO audit_log(chart_id, action, detail, created_at) VALUES(?,?,?,?)",
            (chart_id, action, detail, now()),
        )

    # ---------------- 增 ----------------
    def create(self, payload: Dict[str, Any]) -> int:
        with self.conn() as c:
            cur = c.execute(
                """INSERT INTO charts(
                    name, gender, solar_date, time_index, lunar_date, chinese_date,
                    time_name, zodiac, sign, soul, body, five_elements,
                    soul_branch, body_branch, raw_json, note, tags, star_rating,
                    created_at, updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    payload["name"], payload["gender"], payload["solar_date"],
                    payload["time_index"], payload.get("lunar_date"),
                    payload.get("chinese_date"), payload.get("time_name"),
                    payload.get("zodiac"), payload.get("sign"),
                    payload.get("soul"), payload.get("body"),
                    payload.get("five_elements"), payload.get("soul_branch"),
                    payload.get("body_branch"),
                    json.dumps(payload.get("raw", {}), ensure_ascii=False),
                    payload.get("note", ""), payload.get("tags", ""),
                    int(payload.get("star_rating", 0)), now(), now(),
                ),
            )
            cid = cur.lastrowid

            for p in payload.get("palaces", []):
                c.execute(
                    """INSERT OR REPLACE INTO chart_palaces(
                        chart_id, palace_index, name, heavenly_stem, earthly_branch,
                        is_body, major_stars, minor_stars)
                       VALUES(?,?,?,?,?,?,?,?)""",
                    (
                        cid, p["index"], p["name"],
                        p.get("heavenly_stem", ""), p.get("earthly_branch", ""),
                        1 if p.get("is_body_palace") else 0,
                        ",".join(s["name"] for s in p.get("major_stars", [])),
                        ",".join(s["name"] for s in p.get("minor_stars", [])),
                    ),
                )
            self._audit(c, cid, "create", f"{payload['name']} {payload['solar_date']}")
            return cid

    # ---------------- 查 ----------------
    def get(self, cid: int) -> Optional[Dict[str, Any]]:
        with self.conn() as c:
            r = c.execute(
                "SELECT * FROM charts WHERE id=? AND is_deleted=0", (cid,)
            ).fetchone()
            if not r:
                return None
            d = dict(r)
            d["raw"] = json.loads(d.pop("raw_json") or "{}")
            return d

    def list(self, q: str = "", gender: str = "", star: str = "",
             tag: str = "", page: int = 1, size: int = 20,
             sort: str = "id_desc") -> Tuple[List[Dict[str, Any]], int]:
        where = ["c.is_deleted=0"]
        args: List[Any] = []

        if q:
            where.append("(c.name LIKE ? OR c.solar_date LIKE ? OR c.lunar_date LIKE ? "
                         "OR c.chinese_date LIKE ? OR c.note LIKE ?)")
            kw = f"%{q}%"
            args += [kw] * 5
        if gender:
            where.append("c.gender=?")
            args.append(gender)
        if tag:
            where.append("c.tags LIKE ?")
            args.append(f"%{tag}%")
        if star:
            where.append(
                "EXISTS(SELECT 1 FROM chart_palaces p WHERE p.chart_id=c.id "
                "AND p.major_stars LIKE ?)")
            args.append(f"%{star}%")

        order = {
            "id_desc": "c.id DESC",
            "id_asc": "c.id ASC",
            "name": "c.name ASC",
            "solar_asc": "c.solar_date ASC",
            "solar_desc": "c.solar_date DESC",
            "rating": "c.star_rating DESC, c.id DESC",
        }.get(sort, "c.id DESC")

        sql_where = " AND ".join(where)
        with self.conn() as c:
            total = c.execute(
                f"SELECT COUNT(*) FROM charts c WHERE {sql_where}", args
            ).fetchone()[0]
            offset = max(0, (page - 1) * size)
            rows = c.execute(
                f"""SELECT c.*, (
                        SELECT GROUP_CONCAT(p.major_stars, '|')
                        FROM chart_palaces p WHERE p.chart_id=c.id
                    ) AS all_major
                    FROM charts c WHERE {sql_where}
                    ORDER BY {order} LIMIT ? OFFSET ?""",
                args + [size, offset],
            ).fetchall()

        out = []
        for r in rows:
            d = dict(r)
            d.pop("raw_json", None)
            out.append(d)
        return out, total

    def palaces(self, cid: int) -> List[Dict[str, Any]]:
        with self.conn() as c:
            rows = c.execute(
                "SELECT * FROM chart_palaces WHERE chart_id=? ORDER BY palace_index",
                (cid,),
            ).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> Dict[str, Any]:
        with self.conn() as c:
            total = c.execute(
                "SELECT COUNT(*) FROM charts WHERE is_deleted=0").fetchone()[0]
            male = c.execute(
                "SELECT COUNT(*) FROM charts WHERE is_deleted=0 AND gender='男'"
            ).fetchone()[0]
            female = c.execute(
                "SELECT COUNT(*) FROM charts WHERE is_deleted=0 AND gender='女'"
            ).fetchone()[0]
            stars = c.execute(
                """SELECT major_stars, COUNT(*) n FROM chart_palaces
                   WHERE major_stars<>'' GROUP BY major_stars
                   ORDER BY n DESC LIMIT 8"""
            ).fetchall()
            fem = c.execute(
                """SELECT five_elements, COUNT(*) n FROM charts
                   WHERE is_deleted=0 GROUP BY five_elements
                   ORDER BY n DESC"""
            ).fetchall()
        return {
            "total": total, "male": male, "female": female,
            "top_stars": [{"stars": r["major_stars"], "count": r["n"]} for r in stars],
            "five_elements": [{"name": r["five_elements"], "count": r["n"]} for r in fem],
        }

    # ---------------- 改 ----------------
    def update(self, cid: int, fields: Dict[str, Any]) -> bool:
        allowed = {"name", "note", "tags", "star_rating", "gender"}
        sets, args = [], []
        for k, v in fields.items():
            if k not in allowed:
                continue
            if k == "star_rating":
                v = max(0, min(5, int(v)))
            sets.append(f"{k}=?")
            args.append(v)
        if not sets:
            return False
        sets.append("updated_at=?")
        args.append(now())
        args.append(cid)
        with self.conn() as c:
            cur = c.execute(
                f"UPDATE charts SET {', '.join(sets)} WHERE id=? AND is_deleted=0", args)
            ok = cur.rowcount > 0
            if ok:
                self._audit(c, cid, "update", json.dumps(fields, ensure_ascii=False))
            return ok

    # ---------------- 删（软删除 + 可恢复） ----------------
    def delete(self, cid: int) -> bool:
        with self.conn() as c:
            cur = c.execute(
                "UPDATE charts SET is_deleted=1, updated_at=? WHERE id=? AND is_deleted=0",
                (now(), cid))
            ok = cur.rowcount > 0
            if ok:
                self._audit(c, cid, "delete", "soft delete")
            return ok

    def restore(self, cid: int) -> bool:
        with self.conn() as c:
            cur = c.execute(
                "UPDATE charts SET is_deleted=0, updated_at=? WHERE id=? AND is_deleted=1",
                (now(), cid))
            ok = cur.rowcount > 0
            if ok:
                self._audit(c, cid, "restore", "restored")
            return ok

    def audit(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.conn() as c:
            rows = c.execute(
                "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
