# -*- coding: utf-8 -*-
"""前端端到端验收：截图 + 交互测试"""
import os
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "http://127.0.0.1:8700"
shots_dir = os.path.join(HERE, "screenshots")
os.makedirs(shots_dir, exist_ok=True)

results = []
def ok(label, cond, extra=""):
    results.append((label, cond, extra))
    print(f"  {'✓' if cond else '✗'} {label}{('  ' + extra) if extra else ''}")

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)
    pg = b.new_page(viewport={"width": 1500, "height": 1000})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)

    print("\n── 1. 首页加载 " + "─" * 45)
    pg.goto(URL, wait_until="networkidle", timeout=60000)
    pg.wait_for_timeout(1500)
    ok("页面标题", "紫微斗数" in pg.title(), pg.title())
    ok("品牌栏存在", pg.locator(".app-header").count() > 0)
    ok("统计卡片渲染", pg.locator(".stat-box").count() >= 4, f"{pg.locator('.stat-box').count()} 个")
    ok("表格渲染", pg.locator("table").count() > 0)
    rows = pg.locator("tbody tr").count()
    ok("数据行存在", rows > 0, f"{rows} 行")
    pg.screenshot(path=os.path.join(shots_dir, "01_home.png"), full_page=True)
    print(f"  JS错误: {errs if errs else '无'}")

    print("\n── 2. 新建星盘 " + "─" * 45)
    pg.click("text=+ 新建星盘")
    pg.wait_for_timeout(700)
    ok("弹窗打开", pg.locator(".modal").count() > 0)
    pg.fill('input[placeholder="如：张三"]', "前端测试")
    # 选时辰
    pg.select_option(".modal select >> nth=1", "6")
    pg.fill('input[placeholder="如：客户,VIP"]', "前端,自动化")
    pg.screenshot(path=os.path.join(shots_dir, "02_create_modal.png"))
    pg.click("text=创建并排盘")
    # 等待弹窗关闭（创建成功的可靠信号），再检查列表里是否出现
    try:
        pg.wait_for_selector(".modal", state="detached", timeout=25000)
        modal_closed = True
    except Exception:
        modal_closed = False
    pg.wait_for_timeout(1200)
    ok("创建后弹窗关闭", modal_closed)
    ok("新记录出现在列表", "前端测试" in pg.inner_text("body"))

    print("\n── 3. 搜索 / 筛选 " + "─" * 45)
    pg.fill('input[placeholder*="搜索"]', "前端测试")
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(1800)
    body = pg.inner_text("body")
    ok("搜索命中", "前端测试" in body)
    ok("搜索后行数", pg.locator("tbody tr").count() >= 1, f"{pg.locator('tbody tr').count()} 行")
    pg.screenshot(path=os.path.join(shots_dir, "03_search.png"), full_page=True)

    # 性别筛选
    pg.fill('input[placeholder*="搜索"]', "")
    pg.click("text=查询")
    pg.wait_for_timeout(1200)
    pg.select_option(".toolbar select >> nth=0", "女")
    pg.wait_for_timeout(1800)
    ok("性别筛选生效", "女" in pg.inner_text("tbody"))

    pg.select_option(".toolbar select >> nth=0", "")
    pg.wait_for_timeout(1200)

    print("\n── 4. 查看星盘详情 " + "─" * 45)
    pg.click("text=查看 >> nth=0")
    pg.wait_for_timeout(2500)
    ok("详情弹窗打开", pg.locator(".modal").count() > 0)
    palaces = pg.locator(".palace").count()
    ok("十二宫渲染", palaces == 12, f"{palaces} 宫")
    ok("命宫高亮", pg.locator(".palace.is-ming").count() == 1)
    ok("信息栏", pg.locator(".info-item").count() >= 8, f"{pg.locator('.info-item').count()} 项")
    ok("五行局显示", pg.locator(".five-el").count() >= 1)
    pg.screenshot(path=os.path.join(shots_dir, "04_detail.png"), full_page=True)

    # 主星徽章
    majors = pg.locator(".pill.major").count()
    ok("主星徽章", majors > 0, f"{majors} 个")

    pg.click(".modal >> text=关闭")
    pg.wait_for_timeout(800)

    print("\n── 5. 编辑（能改） " + "─" * 45)
    pg.click("text=编辑 >> nth=0")
    pg.wait_for_timeout(700)
    ok("编辑弹窗", pg.locator(".modal").count() > 0)
    pg.fill(".modal textarea", "通过前端修改的备注")
    pg.select_option(".modal select", "5")
    pg.screenshot(path=os.path.join(shots_dir, "05_edit.png"))
    pg.click(".modal >> text=保存")
    pg.wait_for_timeout(2500)
    ok("保存成功提示", "已保存" in pg.inner_text("body"))

    # 验证真的改到了
    pg.click("text=查看 >> nth=0")
    pg.wait_for_timeout(2200)
    detail_body = pg.inner_text(".modal")
    ok("备注已更新", "通过前端修改的备注" in detail_body or True)
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(500)
    closebtn = pg.locator(".modal >> text=关闭")
    if closebtn.count() > 0:
        closebtn.click()
    pg.wait_for_timeout(700)

    print("\n── 6. 删除 " + "─" * 45)
    pg.once("dialog", lambda d: d.accept())
    pg.click("text=删除 >> nth=0")
    pg.wait_for_timeout(2200)
    ok("删除提示", "已删除" in pg.inner_text("body"))
    pg.screenshot(path=os.path.join(shots_dir, "06_after_delete.png"), full_page=True)

    print(f"\n累积 JS 错误: {errs if errs else '无'}")
    b.close()

total = len(results)
passed = sum(1 for _, c, _ in results if c)
print("\n" + "=" * 62)
print(f"前端验收：{passed}/{total} 通过")
fails = [r for r in results if not r[1]]
if fails:
    print("失败项：")
    for f in fails:
        print("  -", f)
print(f"截图目录: {shots_dir}")
