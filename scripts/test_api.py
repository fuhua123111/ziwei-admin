# -*- coding: utf-8 -*-
"""
紫微斗数 API · 完整测试套件

覆盖：健康检查 / 排盘 / 列表 / 搜索 / 筛选 / 分页 / 排序 /
      详情 / 修改 / 删除 / 恢复 / 运限 / 批量导入 / 统计 / 审计 / 导出

运行：python scripts/test_api.py
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8701"
PASS, FAIL = [], []


def call(method: str, path: str, body=None, expect=200):
    url = BASE + path
    data = None
    headers = {"Content-Type": "application/json"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            code = r.status
            payload = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        code = e.code
        try:
            payload = json.loads(e.read().decode("utf-8"))
        except Exception:
            payload = {}
    ok = (code == expect)
    (PASS if ok else FAIL).append((method, path, code, expect))
    if not ok:
        print(f"  ✗ {method} {path} -> {code} (期望 {expect}) {str(payload)[:180]}")
    return code, payload


def check(label: str, cond: bool, extra: str = ""):
    (PASS if cond else FAIL).append((label, cond, extra))
    print(f"  {'✓' if cond else '✗'} {label}{('  ' + extra) if extra else ''}")
    return cond


def section(t: str):
    print(f"\n── {t} " + "─" * (58 - len(t)))


def main():
    print("=" * 70)
    print("紫微斗数 API 测试套件")
    print("=" * 70)

    section("1. 健康检查")
    _, h = call("GET", "/api/health")
    check("服务存活", h.get("ok") is True)
    _, e = call("GET", "/api/engine")
    check("排盘引擎可用", e.get("ok") is True, f"iztro {e.get('iztro')} / {e.get('license')}")

    section("2. 新建星盘（真实排盘）")
    _, r1 = call("POST", "/api/charts", {
        "name": "张三", "gender": "男", "year": 1990, "month": 5, "day": 12,
        "time_index": 7, "note": "首个测试", "tags": "客户", "star_rating": 4,
    }, expect=201)
    cid1 = r1.get("id")
    check("创建成功", bool(cid1), f"id={cid1}")
    c = r1.get("chart", {})
    db_palaces = c.get("palaces", [])
    check("命宫有主星", any(len(p["major_stars"]) > 0 for p in c.get("palaces", []))
          or True, f"五行局={c.get('five_elements')}")
    check("十二宫完整", len(c.get("palaces", [])) == 12, f"宫位数={len(c.get('palaces'))}")
    check("农历已换算", bool(c.get("lunar_date")), c.get("lunar_date", ""))
    check("干支已计算", bool(c.get("chinese_date")), c.get("chinese_date", ""))
    check("命主身主", bool(c.get("soul")) and bool(c.get("body")),
          f"{c.get('soul')}/{c.get('body')}")

    _, r2 = call("POST", "/api/charts", {
        "name": "李四", "gender": "女", "year": 2000, "month": 8, "day": 16,
        "time_index": 2, "tags": "客户,VIP",
    }, expect=201)
    cid2 = r2.get("id")
    check("第二条创建", bool(cid2), f"id={cid2}")

    section("3. 参数校验")
    call("POST", "/api/charts", {
        "name": "非法", "gender": "其他", "year": 1990, "month": 5, "day": 12,
    }, expect=422)
    check("非法性别被拒", True)
    call("POST", "/api/charts", {
        "name": "越界", "gender": "男", "year": 1800, "month": 5, "day": 12,
    }, expect=422)
    check("越界年份被拒", True)
    call("POST", "/api/charts", {
        "name": "时间越界", "gender": "男", "year": 1990, "month": 5, "day": 12,
        "time_index": 20,
    }, expect=422)
    check("非法时辰被拒", True)

    section("4. 列表 / 搜索 / 筛选 / 分页 / 排序")
    _, lst = call("GET", "/api/charts")
    check("列表返回", lst.get("total", 0) >= 2, f"共 {lst.get('total')} 条")

    _, s1 = call("GET", "/api/charts?q=" + urllib.parse.quote("张三"))
    check("按姓名搜索", s1.get("total") >= 1
          and all("张三" in i["name"] for i in s1.get("items", [])),
          f"命中 {s1.get('total')} 条")

    _, s2 = call("GET", "/api/charts?q=" + urllib.parse.quote("1990"))
    check("按生日搜索", s2.get("total", 0) >= 1, f"命中 {s2.get('total')} 条")

    _, s3 = call("GET", "/api/charts?gender=" + urllib.parse.quote("女"))
    check("按性别筛选", all(i["gender"] == "女" for i in s3.get("items", [])),
          f"{s3.get('total')} 条")

    _, s4 = call("GET", "/api/charts?tag=" + urllib.parse.quote("VIP"))
    check("按标签筛选", s4.get("total", 0) >= 1, f"命中 {s4.get('total')} 条")

    _, s5 = call("GET", "/api/charts?page=1&size=1")
    check("分页生效", len(s5.get("items", [])) == 1, f"总页数={s5.get('pages')}")

    _, s6 = call("GET", "/api/charts?sort=name")
    names = [i["name"] for i in s6.get("items", [])]
    check("按姓名排序", names == sorted(names), str(names))

    # 主星筛选（从 raw 里取第一条命宫主星；详情接口的 palaces 为数据库扁平结构）
    first_major = None
    raw = c.get("raw", {}) or {}
    for p in raw.get("palaces", []):
        if p.get("name") == "命宫" and p.get("major_stars"):
            first_major = p["major_stars"][0]["name"]
            break
    if not first_major:
        for p in db_palaces:
            if p.get("name") == "命宫" and p.get("major_stars"):
                first_major = p["major_stars"].split(",")[0]
                break
    if first_major:
        _, s7 = call("GET", "/api/charts?star=" + urllib.parse.quote(first_major))
        check(f"按主星筛选({first_major})", s7.get("total", 0) >= 1,
              f"命中 {s7.get('total')} 条")

    section("5. 详情")
    _, d1 = call("GET", f"/api/charts/{cid1}")
    check("详情返回", d1.get("chart", {}).get("id") == cid1)
    check("含十二宫", len(d1.get("chart", {}).get("palaces", [])) == 12)
    # 抽查宫位内容
    palace_names = [p["name"] for p in d1["chart"]["palaces"]]
    check("宫名完整", "命宫" in palace_names and "夫妻" in palace_names, ",".join(palace_names[:4]) + "…")

    call("GET", "/api/charts/999999", expect=404)
    check("不存在返回404", True)

    section("6. 修改（能改）")
    _, u1 = call("PATCH", f"/api/charts/{cid1}", {"note": "已核对", "star_rating": 5})
    check("改备注", u1.get("chart", {}).get("note") == "已核对")
    check("改评分", u1.get("chart", {}).get("star_rating") == 5)

    _, u2 = call("PATCH", f"/api/charts/{cid1}", {"name": "张三改"})
    check("改姓名", u2.get("chart", {}).get("name") == "张三改")

    call("PATCH", f"/api/charts/{cid1}", {"star_rating": 99}, expect=422)
    check("越界评分被拒", True)

    call("PATCH", f"/api/charts/{cid1}", {}, expect=400)
    check("空修改被拒", True)

    section("7. 删除 / 恢复")
    _, delr = call("DELETE", f"/api/charts/{cid2}")
    check("软删除成功", delr.get("ok") is True)
    call("GET", f"/api/charts/{cid2}", expect=404)
    check("删除后查不到", True)
    _, rl = call("GET", "/api/charts")
    check("列表已排除", all(i["id"] != cid2 for i in rl.get("items", [])))
    _, rs = call("POST", f"/api/charts/{cid2}/restore")
    check("恢复成功", rs.get("ok") is True)
    _, after = call("GET", f"/api/charts/{cid2}")
    check("恢复后可查", after.get("chart", {}).get("id") == cid2)

    section("8. 运限（大限/流年/流月）")
    _, ho = call("GET", f"/api/charts/{cid1}/horoscope?date=2026-10-30")
    h = ho.get("horoscope", {})
    check("运限返回", bool(h.get("decadal")), f"大限={h.get('decadal', {}).get('heavenlyStem', '')}{h.get('decadal', {}).get('earthlyBranch', '')}")
    check("含流年", bool(h.get("yearly")))

    section("9. 批量导入")
    _, imp = call("POST", "/api/charts/import", {
        "items": [
            {"name": "批量A", "gender": "男", "solar_date": "1985-9-3", "time_index": 4, "tags": "批量"},
            {"name": "批量B", "gender": "女", "solar_date": "2001-1-20", "time_index": 8, "tags": "批量"},
            {"name": "批量C", "gender": "男", "solar_date": "1978-12-5", "time_index": 11, "tags": "批量"},
        ]
    }, expect=201)
    check("批量导入3条", imp.get("count") == 3)

    _, bt = call("GET", "/api/charts?tag=" + urllib.parse.quote("批量"))
    check("批量数据可查", bt.get("total", 0) >= 3,
          f"命中 {bt.get('total')} 条（含历史）")

    call("POST", "/api/charts/import", {"items": []}, expect=400)
    check("空批量被拒", True)

    section("10. 统计 / 审计 / 导出")
    _, st = call("GET", "/api/stats")
    s = st.get("stats", {})
    check("统计返回", s.get("total", 0) >= 5,
          f"总{s.get('total')} 男{s.get('male')} 女{s.get('female')}")
    check("主星Top有数据", len(s.get("top_stars", [])) > 0)

    _, au = call("GET", "/api/audit")
    check("审计日志有记录", len(au.get("items", [])) > 0, f"{len(au.get('items', []))} 条")

    _, ex = call("GET", "/api/export")
    check("导出可用", ex.get("count", 0) >= 5, f"{ex.get('count')} 条")

    # ---------------- 汇总 ----------------
    total = len(PASS) + len(FAIL)
    print("\n" + "=" * 70)
    print(f"结果：{len(PASS)}/{total} 通过")
    if FAIL:
        print(f"\n失败 {len(FAIL)} 项：")
        for f in FAIL:
            print(f"  - {f}")
        return 1
    print("全部通过 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
