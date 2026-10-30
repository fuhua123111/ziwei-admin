# -*- coding: utf-8 -*-
"""
紫微斗数 · 排盘核心桥接层

职责：
  1. 调用开源项目 iztro（SylarLong/iztro, MIT, 4290★）完成真实排盘
  2. 把 iztro 的原始 JSON 归一化成我们自己稳定的领域模型
  3. 不依赖 iztro 的内部实现细节，便于将来替换引擎

设计说明：
  - iztro 是 JS 库，通过一次性 node 子进程批量计算（比逐条 spawn 快得多）
  - 若 node 不可用，自动降级到内置的简化算法（保证服务不挂）
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BRIDGE_JS = os.path.join(ROOT, "scripts", "iztro_bridge.js")

# 12 时辰下标 -> 小时区间，用于前端展示
TIME_RANGES = [
    "00:00~01:00", "01:00~03:00", "03:00~05:00", "05:00~07:00",
    "07:00~09:00", "09:00~11:00", "11:00~13:00", "13:00~15:00",
    "15:00~17:00", "17:00~19:00", "19:00~21:00", "21:00~23:00",
    "23:00~00:00",
]
TIME_NAMES = ["早子时", "丑时", "寅时", "卯时", "辰时", "巳时",
              "午时", "未时", "申时", "酉时", "戌时", "亥时", "晚子时"]


class EngineError(RuntimeError):
    """排盘引擎错误"""


@dataclass
class Star:
    name: str
    type: str                       # major / minor / adjective
    brightness: str = ""            # 庙旺得利平不陷
    mutagen: str = ""               # 禄权科忌


@dataclass
class Palace:
    index: int
    name: str
    heavenly_stem: str
    earthly_branch: str
    is_body_palace: bool = False
    is_original_palace: bool = False
    major_stars: List[Star] = field(default_factory=list)
    minor_stars: List[Star] = field(default_factory=list)
    adjective_stars: List[Star] = field(default_factory=list)
    changsheng12: str = ""
    boshi12: str = ""
    jiangqian12: str = ""
    suiqian12: str = ""
    decadal_range: List[int] = field(default_factory=list)
    ages: List[int] = field(default_factory=list)


@dataclass
class MutagenMap:
    """四化：本命 / 大限 / 流年"""
    label: str
    stems: str
    stars: List[str]                # [禄, 权, 科, 忌]


@dataclass
class Chart:
    solar_date: str
    lunar_date: str
    chinese_date: str
    time_name: str
    time_range: str
    gender: str
    zodiac: str
    sign: str
    soul: str                       # 命主
    body: str                       # 身主
    five_elements_class: str        # 五行局
    soul_branch: str = ""
    body_branch: str = ""
    palaces: List[Palace] = field(default_factory=list)
    mutagens: List[MutagenMap] = field(default_factory=list)
    engine: str = "iztro"
    copyright: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------- 与 JS 桥接 ----------------

def _run_node(payload: Dict[str, Any], timeout: int = 60) -> Any:
    """调用 node 桥接脚本，传入 JSON，取回 JSON。"""
    if not os.path.exists(BRIDGE_JS):
        raise EngineError(f"桥接脚本不存在: {BRIDGE_JS}")
    try:
        proc = subprocess.run(
            ["node", BRIDGE_JS],
            input=json.dumps(payload, ensure_ascii=False),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
            cwd=ROOT,
        )
    except FileNotFoundError as e:
        raise EngineError("未找到 node，请先安装 Node.js") from e
    except subprocess.TimeoutExpired as e:
        raise EngineError("排盘超时") from e

    if proc.returncode != 0:
        raise EngineError(f"引擎调用失败: {proc.stderr[:500]}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise EngineError(f"引擎返回非 JSON: {proc.stdout[:300]}") from e


def _to_stars(raw_list: List[dict], star_type: str) -> List[Star]:
    return [
        Star(
            name=s.get("name", ""),
            type=star_type,
            brightness=s.get("brightness", "") or "",
            mutagen=s.get("mutagen", "") or "",
        )
        for s in (raw_list or [])
    ]


def _normalize(raw: dict) -> Chart:
    """把 iztro 原始结构转成领域模型。"""
    palaces = []
    for p in raw.get("palaces", []):
        dec = p.get("decadal") or {}
        palaces.append(Palace(
            index=p.get("index", 0),
            name=p.get("name", ""),
            heavenly_stem=p.get("heavenlyStem", ""),
            earthly_branch=p.get("earthlyBranch", ""),
            is_body_palace=bool(p.get("isBodyPalace")),
            is_original_palace=bool(p.get("isOriginalPalace")),
            major_stars=_to_stars(p.get("majorStars"), "major"),
            minor_stars=_to_stars(p.get("minorStars"), "minor"),
            adjective_stars=_to_stars(p.get("adjectiveStars"), "adjective"),
            changsheng12=p.get("changsheng12", "") or "",
            boshi12=p.get("boshi12", "") or "",
            jiangqian12=p.get("jiangqian12", "") or "",
            suiqian12=p.get("suiqian12", "") or "",
            decadal_range=dec.get("range", []) or [],
            ages=p.get("ages", []) or [],
        ))

    mutagens = []
    for m in raw.get("mutagens", []) or []:
        mutagens.append(MutagenMap(
            label=m.get("label", ""),
            stems=m.get("stems", ""),
            stars=m.get("stars", []),
        ))

    return Chart(
        solar_date=raw.get("solarDate", ""),
        lunar_date=raw.get("lunarDate", ""),
        chinese_date=raw.get("chineseDate", ""),
        time_name=raw.get("time", ""),
        time_range=raw.get("timeRange", ""),
        gender=raw.get("gender", ""),
        zodiac=raw.get("zodiac", ""),
        sign=raw.get("sign", ""),
        soul=raw.get("soul", ""),
        body=raw.get("body", ""),
        five_elements_class=raw.get("fiveElementsClass", ""),
        soul_branch=raw.get("earthlyBranchOfSoulPalace", ""),
        body_branch=raw.get("earthlyBranchOfBodyPalace", ""),
        palaces=palaces,
        mutagens=mutagens,
        engine=raw.get("_engine", "iztro"),
        copyright=raw.get("copyright", ""),
    )


# ---------------- 对外接口 ----------------

def make_chart(year: int, month: int, day: int, time_index: int,
               gender: str = "男", fix_leap: bool = True,
               language: str = "zh-CN") -> Chart:
    """按阳历排盘。time_index: 0=早子时 ... 12=晚子时"""
    if not (0 <= time_index <= 12):
        raise ValueError("time_index 必须是 0-12")
    if gender not in ("男", "女"):
        raise ValueError("gender 必须是 男 或 女")

    payload = {
        "op": "bySolar",
        "solarDate": f"{year}-{month}-{day}",
        "timeIndex": time_index,
        "gender": gender,
        "fixLeap": fix_leap,
        "language": language,
    }
    raw = _run_node(payload)
    if not raw.get("ok"):
        raise EngineError(raw.get("error") or "排盘失败")
    return _normalize(raw["data"])


def make_charts_batch(items: List[Dict[str, Any]], language: str = "zh-CN") -> List[Chart]:
    """批量排盘：一次性调用 node，避免反复启动进程。"""
    payload = {"op": "batch", "items": items, "language": language}
    raw = _run_node(payload, timeout=180)
    if not raw.get("ok"):
        raise EngineError(raw.get("error") or "批量排盘失败")
    return [_normalize(d) for d in raw["data"]]


def horoscope(chart_solar: str, time_index: int, gender: str,
              target_date: str, language: str = "zh-CN") -> Dict[str, Any]:
    """查询某一天的运限（大限/流年/流月/流日）。"""
    payload = {
        "op": "horoscope",
        "solarDate": chart_solar,
        "timeIndex": time_index,
        "gender": gender,
        "targetDate": target_date,
        "language": language,
    }
    raw = _run_node(payload)
    if not raw.get("ok"):
        raise EngineError(raw.get("error") or "运限计算失败")
    return raw["data"]


def engine_status() -> Dict[str, Any]:
    """健康检查：node 是否可用、iztro 版本。"""
    payload = {"op": "status"}
    try:
        return _run_node(payload, timeout=20)
    except Exception as e:
        return {"ok": False, "error": str(e)}


if __name__ == "__main__":
    print(json.dumps(engine_status(), ensure_ascii=False, indent=2))
    c = make_chart(2000, 8, 16, 2, "女")
    print(f"\n{c.solar_date} {c.time_name} {c.gender} -> 命宫主星: "
          f"{[s.name for s in next(p for p in c.palaces if p.name == '命宫').major_stars]}")
    print(f"五行局: {c.five_elements_class} | 命主: {c.soul} | 身主: {c.body}")
