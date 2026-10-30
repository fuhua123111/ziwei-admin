# -*- coding: utf-8 -*-
"""
最终交付验收：模拟"拿到项目 → 一键跑起来"的完整流程
检查：文件完整性 / 依赖声明 / 服务可用 / 核心链路
"""
import json
import os
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ok_list, fail_list = [], []


def check(label, cond, extra=""):
    (ok_list if cond else fail_list).append(label)
    print(f"  {'✓' if cond else '✗'} {label}{('  ' + extra) if extra else ''}")


def get(url, timeout=30):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def post(url, body, timeout=120):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


print("=" * 66)
print("最终交付验收")
print("=" * 66)

print("\n── 1. 文件完整性 " + "─" * 46)
required = [
    "README.md", "LICENSE", ".gitignore", "package.json", "next.config.js",
    "tsconfig.json", "start.bat",
    "backend/engine.py", "backend/db.py", "backend/main.py",
    "components/ChartDetail.tsx",
    "lib/api.ts", "lib/types.ts",
    "app/page.tsx", "app/layout.tsx", "app/globals.css",
    "scripts/iztro_bridge.js", "scripts/test_api.py",
    "scripts/test_frontend.py", "scripts/final_acceptance.py", "scripts/backup.py",
]
missing = [f for f in required if not os.path.exists(os.path.join(ROOT, f))]
check(f"核心文件齐全 ({len(required)} 个)", not missing,
      f"缺失: {missing}" if missing else "")

shots = os.path.join(ROOT, "screenshots")
shots_ok = os.path.isdir(shots) and len([f for f in os.listdir(shots) if f.endswith(".png")]) >= 4
check("验收截图存在", shots_ok,
      f"{len(os.listdir(shots)) if os.path.isdir(shots) else 0} 张")

print("\n── 2. 依赖声明 " + "─" * 48)
pkg = json.load(open(os.path.join(ROOT, "package.json"), encoding="utf-8"))
deps = pkg.get("dependencies", {})
check("声明 iztro", "iztro" in deps, deps.get("iztro", ""))
check("声明 next", "next" in deps, deps.get("next", ""))
check("声明 react", "react" in deps, deps.get("react", ""))
check("node_modules 已安装", os.path.isdir(os.path.join(ROOT, "node_modules")))

print("\n── 3. 后端服务 " + "─" * 48)
try:
    h = get("http://127.0.0.1:8701/api/health")
    check("后端存活", h.get("ok") is True)
except Exception as e:
    check("后端存活", False, str(e)[:60])

try:
    e = get("http://127.0.0.1:8701/api/engine")
    check("排盘引擎", e.get("ok") is True, f"iztro {e.get('iztro')} / {e.get('license')}")
except Exception as ex:
    check("排盘引擎", False, str(ex)[:60])

print("\n── 4. 核心链路（真实排盘） " + "─" * 38)
try:
    created = post("http://127.0.0.1:8701/api/charts", {
        "name": "最终验收", "gender": "女", "year": 1995, "month": 6, "day": 18,
        "time_index": 9, "note": "交付验收自动创建", "tags": "验收",
    })
    cid = created.get("id")
    check("创建星盘", bool(cid), f"id={cid}")
    chart = created.get("chart", {})
    raw = chart.get("raw", {})
    palaces = raw.get("palaces", [])
    check("十二宫完整", len(palaces) == 12, f"{len(palaces)} 宫")
    stars = sum(len(p.get("major_stars", [])) + len(p.get("minor_stars", []))
                for p in palaces)
    check("星曜数据", stars > 10, f"{stars} 颗星")
    check("农历换算", bool(raw.get("lunar_date")), raw.get("lunar_date", ""))
    check("干支", bool(raw.get("chinese_date")), raw.get("chinese_date", ""))
    check("四化", len(raw.get("mutagens", [])) > 0,
          f"{len(raw.get('mutagens', []))} 组")

    # 查
    lst = get(f"http://127.0.0.1:8701/api/charts?q=" + urllib.parse.quote("最终验收"))
    check("能查", lst.get("total", 0) >= 1, f"命中 {lst.get('total')}")

    # 改
    req = urllib.request.Request(
        f"http://127.0.0.1:8701/api/charts/{cid}",
        data=json.dumps({"note": "验收已修改"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="PATCH")
    urllib.request.urlopen(req, timeout=30)
    after = get(f"http://127.0.0.1:8701/api/charts/{cid}")
    check("能改", after["chart"]["note"] == "验收已修改")

    # 删
    req = urllib.request.Request(f"http://127.0.0.1:8701/api/charts/{cid}", method="DELETE")
    urllib.request.urlopen(req, timeout=30)
    try:
        get(f"http://127.0.0.1:8701/api/charts/{cid}")
        check("能删", False, "删除后仍可访问")
    except urllib.error.HTTPError as he:
        check("能删", he.code == 404, "删除后返回 404")
except Exception as ex:
    check("核心链路", False, str(ex)[:100])

print("\n── 5. 前端服务 " + "─" * 48)
import urllib.parse  # noqa
try:
    with urllib.request.urlopen("http://127.0.0.1:8700", timeout=30) as r:
        html = r.read().decode("utf-8", errors="ignore")
    check("前端可访问", r.status == 200)
    check("页面含标题", "紫微斗数" in html or "__next" in html)
except Exception as ex:
    check("前端可访问", False, str(ex)[:60])

print("\n" + "=" * 66)
total = len(ok_list) + len(fail_list)
print(f"验收结果：{len(ok_list)}/{total} 通过")
if fail_list:
    print("失败项：", fail_list)
    sys.exit(1)
print("交付验收通过 ✓")
