# -*- coding: utf-8 -*-
"""
紫微斗数 · REST API

对应需求："建本地数据库、做一个能查能改的网页后台"

接口：
  GET    /api/health              健康检查
  GET    /api/engine              排盘引擎状态
  POST   /api/charts              新建星盘（自动排盘并入库）
  GET    /api/charts              列表（搜索/筛选/分页/排序）
  GET    /api/charts/{id}         详情（含十二宫）
  PATCH  /api/charts/{id}         修改（姓名/备注/标签/评分）
  DELETE /api/charts/{id}         删除（软删除）
  POST   /api/charts/{id}/restore 恢复
  GET    /api/charts/{id}/horoscope 运限（大限/流年/流月）
  GET    /api/stats               统计
  GET    /api/audit               审计日志
  POST   /api/charts/import       批量导入
  GET    /api/export              导出全部 JSON
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import engine
from db import Database, DEFAULT_DB

app = FastAPI(
    title="紫微斗数 API",
    description="基于开源库 iztro（MIT）的排盘服务 + 本地 SQLite 数据库",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.environ.get("ZIWEI_DB", DEFAULT_DB)
db = Database(DB_PATH)


# ---------------- 请求模型 ----------------

class ChartCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=40)
    gender: str = Field("男")
    year: int = Field(..., ge=1900, le=2100)
    month: int = Field(..., ge=1, le=12)
    day: int = Field(..., ge=1, le=31)
    time_index: int = Field(0, ge=0, le=12, description="0=早子时,1=丑时,...,12=晚子时")
    note: str = ""
    tags: str = ""
    star_rating: int = Field(0, ge=0, le=5)

    @field_validator("gender")
    @classmethod
    def check_gender(cls, v: str) -> str:
        if v not in ("男", "女"):
            raise ValueError("性别必须是 男 或 女")
        return v


class ChartUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=40)
    note: Optional[str] = None
    tags: Optional[str] = None
    star_rating: Optional[int] = Field(None, ge=0, le=5)
    gender: Optional[str] = None


class BatchItem(BaseModel):
    name: str
    gender: str = "男"
    solar_date: str          # YYYY-M-D
    time_index: int = 0
    note: str = ""
    tags: str = ""


class BatchImport(BaseModel):
    items: List[BatchItem]


# ---------------- 基础 ----------------

@app.get("/api/health")
def health() -> Dict[str, Any]:
    return {"ok": True, "db": DB_PATH, "version": app.version}


@app.get("/api/engine")
def engine_info() -> Dict[str, Any]:
    return engine.engine_status()


# ---------------- 星盘 ----------------

@app.post("/api/charts", status_code=201)
def create_chart(body: ChartCreate) -> Dict[str, Any]:
    try:
        chart = engine.make_chart(
            body.year, body.month, body.day, body.time_index, body.gender
        )
    except engine.EngineError as e:
        raise HTTPException(502, f"排盘失败: {e}")
    except ValueError as e:
        raise HTTPException(400, str(e))

    c = chart.to_dict()
    payload = {
        "name": body.name,
        "gender": c["gender"],
        "solar_date": c["solar_date"],
        "time_index": body.time_index,
        "lunar_date": c["lunar_date"],
        "chinese_date": c["chinese_date"],
        "time_name": c["time_name"],
        "zodiac": c["zodiac"],
        "sign": c["sign"],
        "soul": c["soul"],
        "body": c["body"],
        "five_elements": c["five_elements_class"],
        "soul_branch": c["soul_branch"],
        "body_branch": c["body_branch"],
        "raw": c,
        "note": body.note,
        "tags": body.tags,
        "star_rating": body.star_rating,
        "palaces": c["palaces"],
    }
    cid = db.create(payload)
    return {"ok": True, "id": cid, "chart": _detail(cid)}


@app.get("/api/charts")
def list_charts(
    q: str = Query("", description="关键词：姓名/生日/农历/干支/备注"),
    gender: str = Query("", description="男/女"),
    star: str = Query("", description="按主星筛选，如 紫微"),
    tag: str = Query("", description="按标签筛选"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    sort: str = Query("id_desc"),
) -> Dict[str, Any]:
    rows, total = db.list(q=q, gender=gender, star=star, tag=tag,
                          page=page, size=size, sort=sort)
    return {
        "ok": True, "total": total, "page": page, "size": size,
        "pages": (total + size - 1) // size if size else 0,
        "items": rows,
    }


def _detail(cid: int) -> Dict[str, Any]:
    row = db.get(cid)
    if not row:
        raise HTTPException(404, "星盘不存在")
    row["palaces"] = db.palaces(cid)
    return row


@app.get("/api/charts/{cid}")
def get_chart(cid: int) -> Dict[str, Any]:
    return {"ok": True, "chart": _detail(cid)}


@app.patch("/api/charts/{cid}")
def update_chart(cid: int, body: ChartUpdate) -> Dict[str, Any]:
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(400, "没有要修改的字段")
    if not db.get(cid):
        raise HTTPException(404, "星盘不存在")
    ok = db.update(cid, fields)
    if not ok:
        raise HTTPException(400, "修改失败")
    return {"ok": True, "chart": _detail(cid)}


@app.delete("/api/charts/{cid}")
def delete_chart(cid: int) -> Dict[str, Any]:
    if not db.delete(cid):
        raise HTTPException(404, "星盘不存在或已删除")
    return {"ok": True, "deleted": cid}


@app.post("/api/charts/{cid}/restore")
def restore_chart(cid: int) -> Dict[str, Any]:
    if not db.restore(cid):
        raise HTTPException(404, "星盘不存在或未被删除")
    return {"ok": True, "restored": cid}


@app.get("/api/charts/{cid}/horoscope")
def get_horoscope(cid: int,
                  date: str = Query(..., description="目标日期 YYYY-MM-DD")) -> Dict[str, Any]:
    row = db.get(cid)
    if not row:
        raise HTTPException(404, "星盘不存在")
    try:
        data = engine.horoscope(row["solar_date"], row["time_index"],
                                row["gender"], date)
    except engine.EngineError as e:
        raise HTTPException(502, f"运限计算失败: {e}")
    return {"ok": True, "chart_id": cid, "horoscope": data}


# ---------------- 批量导入 ----------------

@app.post("/api/charts/import", status_code=201)
def import_charts(body: BatchImport) -> Dict[str, Any]:
    if not body.items:
        raise HTTPException(400, "items 不能为空")
    if len(body.items) > 500:
        raise HTTPException(400, "单次最多导入 500 条")

    items = []
    for it in body.items:
        try:
            y, m, d = [int(x) for x in it.solar_date.replace("/", "-").split("-")]
        except Exception:
            raise HTTPException(400, f"日期格式错误: {it.solar_date}")
        items.append({
            "key": it.name + "|" + it.solar_date,
            "solarDate": f"{y}-{m}-{d}",
            "timeIndex": it.time_index,
            "gender": it.gender,
            "fixLeap": True,
        })

    try:
        charts = engine.make_charts_batch(items)
    except engine.EngineError as e:
        raise HTTPException(502, f"批量排盘失败: {e}")

    created = []
    for it, chart in zip(body.items, charts):
        c = chart.to_dict()
        cid = db.create({
            "name": it.name, "gender": c["gender"], "solar_date": c["solar_date"],
            "time_index": it.time_index, "lunar_date": c["lunar_date"],
            "chinese_date": c["chinese_date"], "time_name": c["time_name"],
            "zodiac": c["zodiac"], "sign": c["sign"], "soul": c["soul"],
            "body": c["body"], "five_elements": c["five_elements_class"],
            "soul_branch": c["soul_branch"], "body_branch": c["body_branch"],
            "raw": c, "note": it.note, "tags": it.tags,
            "palaces": c["palaces"],
        })
        created.append({"id": cid, "name": it.name, "solar_date": c["solar_date"]})
    return {"ok": True, "count": len(created), "created": created}


# ---------------- 统计 / 审计 / 导出 ----------------

@app.get("/api/stats")
def stats() -> Dict[str, Any]:
    return {"ok": True, "stats": db.stats()}


@app.get("/api/audit")
def audit(limit: int = Query(50, ge=1, le=500)) -> Dict[str, Any]:
    return {"ok": True, "items": db.audit(limit)}


@app.get("/api/export")
def export_all() -> JSONResponse:
    rows, total = db.list(page=1, size=10000)
    for r in rows:
        r["palaces"] = db.palaces(r["id"])
    return JSONResponse(
        {"ok": True, "count": total, "charts": rows},
        headers={"Content-Disposition": 'attachment; filename="ziwei_export.json"'},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8701)
