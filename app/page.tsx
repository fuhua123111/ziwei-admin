"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { MAJOR_STAR_LIST, TIME_OPTIONS, type Chart, type Stats } from "@/lib/types";
import ChartDetail from "@/components/ChartDetail";

export default function HomePage() {
  const [items, setItems] = useState<Chart[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  // 筛选
  const [q, setQ] = useState("");
  const [gender, setGender] = useState("");
  const [star, setStar] = useState("");
  const [sort, setSort] = useState("id_desc");

  const [stats, setStats] = useState<Stats | null>(null);
  const [engineVer, setEngineVer] = useState("");

  // 弹窗
  const [showCreate, setShowCreate] = useState(false);
  const [detailId, setDetailId] = useState<number | null>(null);
  const [editRow, setEditRow] = useState<Chart | null>(null);

  const size = 12;

  async function load(p = page) {
    setLoading(true);
    setErr("");
    try {
      const res = await api.list({ q, gender, star, sort, page: p, size });
      setItems(res.items);
      setTotal(res.total);
      setPages(res.pages);
      setPage(res.page);
    } catch (e: any) {
      setErr(e.message || "加载失败");
    } finally {
      setLoading(false);
    }
  }

  async function loadStats() {
    try {
      const s = await api.stats();
      setStats(s.stats);
    } catch {
      /* 忽略 */
    }
  }

  useEffect(() => {
    api.engine().then((e) => setEngineVer(e.iztro || "")).catch(() => {});
  }, []);

  useEffect(() => {
    load(1);
    loadStats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gender, star, sort]);

  function flash(m: string) {
    setMsg(m);
    setTimeout(() => setMsg(""), 3000);
  }

  async function doDelete(c: Chart) {
    if (!confirm(`确认删除「${c.name}」？删除后可在数据库中恢复。`)) return;
    try {
      await api.remove(c.id);
      flash(`已删除 ${c.name}`);
      load();
      loadStats();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  return (
    <>
      <header className="app-header">
        <div className="brand">
          <span className="dot" />
          紫微斗数 · 本地管理后台
          <small>iztro {engineVer || "…"} · SQLite</small>
        </div>
        <div className="header-spacer" />
        <button className="primary" onClick={() => setShowCreate(true)}>
          + 新建星盘
        </button>
      </header>

      <main className="container">
        {err && <div className="alert error">{err}</div>}
        {msg && <div className="alert ok">{msg}</div>}

        <div className="stats-row">
          <div className="stat-box">
            <div className="label">星盘总数</div>
            <div className="value accent">{stats?.total ?? "—"}</div>
          </div>
          <div className="stat-box">
            <div className="label">男 / 女</div>
            <div className="value">
              {stats ? `${stats.male} / ${stats.female}` : "—"}
            </div>
          </div>
          <div className="stat-box">
            <div className="label">最常见主星组合</div>
            <div className="value gold" style={{ fontSize: 15, paddingTop: 8 }}>
              {stats?.top_stars?.[0]?.stars || "—"}
            </div>
          </div>
          <div className="stat-box">
            <div className="label">当前筛选结果</div>
            <div className="value">{total}</div>
          </div>
        </div>

        <div className="toolbar">
          <input
            className="grow"
            placeholder="搜索 姓名 / 生日 / 农历 / 干支 / 备注"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && load(1)}
          />
          <select value={gender} onChange={(e) => setGender(e.target.value)}>
            <option value="">全部性别</option>
            <option value="男">男</option>
            <option value="女">女</option>
          </select>
          <select value={star} onChange={(e) => setStar(e.target.value)}>
            <option value="">全部主星</option>
            {MAJOR_STAR_LIST.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <select value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="id_desc">最新创建</option>
            <option value="id_asc">最早创建</option>
            <option value="name">按姓名</option>
            <option value="solar_asc">生日升序</option>
            <option value="solar_desc">生日降序</option>
            <option value="rating">按评分</option>
          </select>
          <button onClick={() => load(1)}>查询</button>
          {(q || gender || star) && (
            <button
              className="ghost"
              onClick={() => {
                setQ("");
                setGender("");
                setStar("");
                setTimeout(() => load(1), 0);
              }}
            >
              清空
            </button>
          )}
        </div>

        <div className="table-wrap">
          {loading ? (
            <div className="loading">
              <span className="spinner" />
              加载中…
            </div>
          ) : items.length === 0 ? (
            <div className="empty">
              还没有数据。
              <br />
              <br />
              <button className="primary" onClick={() => setShowCreate(true)}>
                + 新建第一个星盘
              </button>
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th style={{ width: 50 }}>ID</th>
                  <th>姓名</th>
                  <th>阳历</th>
                  <th>农历 / 干支</th>
                  <th>命宫主星</th>
                  <th>五行局</th>
                  <th>命主/身主</th>
                  <th>标签</th>
                  <th>评分</th>
                  <th style={{ width: 150 }}>操作</th>
                </tr>
              </thead>
              <tbody>
                {items.map((c) => (
                  <tr key={c.id}>
                    <td className="muted mono">{c.id}</td>
                    <td>
                      <b>{c.name}</b>
                      <span className="muted" style={{ fontSize: 11, marginLeft: 6 }}>
                        {c.gender}
                      </span>
                    </td>
                    <td className="mono">{c.solar_date}</td>
                    <td>
                      <div style={{ fontSize: 12.5 }}>{c.lunar_date}</div>
                      <div className="muted" style={{ fontSize: 11 }}>
                        {c.chinese_date}
                      </div>
                    </td>
                    <td>
                      {renderStars(c.all_major)}
                    </td>
                    <td>
                      <span className="five-el">{c.five_elements}</span>
                    </td>
                    <td className="muted" style={{ fontSize: 12.5 }}>
                      {c.soul} / {c.body}
                    </td>
                    <td>
                      {(c.tags || "")
                        .split(",")
                        .filter(Boolean)
                        .slice(0, 2)
                        .map((t) => (
                          <span className="pill tag" key={t}>
                            {t}
                          </span>
                        ))}
                    </td>
                    <td>
                      <span className="stars-rating">
                        {"★".repeat(c.star_rating)}
                        <span className="off">
                          {"★".repeat(5 - c.star_rating)}
                        </span>
                      </span>
                    </td>
                    <td>
                      <button
                        style={{ padding: "5px 9px", fontSize: 12 }}
                        onClick={() => setDetailId(c.id)}
                      >
                        查看
                      </button>{" "}
                      <button
                        style={{ padding: "5px 9px", fontSize: 12 }}
                        onClick={() => setEditRow(c)}
                      >
                        编辑
                      </button>{" "}
                      <button
                        className="danger"
                        style={{ padding: "5px 9px", fontSize: 12 }}
                        onClick={() => doDelete(c)}
                      >
                        删除
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {pages > 1 && (
          <div className="pager">
            <button disabled={page <= 1} onClick={() => load(page - 1)}>
              上一页
            </button>
            <span className="page-info">
              第 {page} / {pages} 页 · 共 {total} 条
            </span>
            <button disabled={page >= pages} onClick={() => load(page + 1)}>
              下一页
            </button>
          </div>
        )}

        <div className="muted" style={{ marginTop: 22, fontSize: 12, lineHeight: 1.9 }}>
          数据源：<b>iztro</b>（SylarLong，MIT 协议）真实排盘 · 存储：本地 SQLite ·
          后端：FastAPI · 前端：Next.js
        </div>
      </main>

      {showCreate && (
        <CreateModal
          onClose={() => setShowCreate(false)}
          onDone={(m) => {
            setShowCreate(false);
            flash(m);
            load(1);
            loadStats();
          }}
        />
      )}

      {editRow && (
        <EditModal
          row={editRow}
          onClose={() => setEditRow(null)}
          onDone={(m) => {
            setEditRow(null);
            flash(m);
            load();
          }}
        />
      )}

      {detailId !== null && (
        <ChartDetail id={detailId} onClose={() => setDetailId(null)} />
      )}
    </>
  );
}

function renderStars(all?: string) {
  if (!all) return <span className="muted">—</span>;
  const names = Array.from(new Set(all.split("|").join(",").split(",").filter(Boolean)));
  const majors = names.filter((n) => MAJOR_STAR_LIST.includes(n));
  if (majors.length === 0) return <span className="muted">{names.slice(0, 2).join("、")}</span>;
  return majors.map((n) => (
    <span className="pill major" key={n}>
      {n}
    </span>
  ));
}

function CreateModal({
  onClose,
  onDone,
}: {
  onClose: () => void;
  onDone: (msg: string) => void;
}) {
  const [name, setName] = useState("");
  const [gender, setGender] = useState("男");
  const [year, setYear] = useState(1990);
  const [month, setMonth] = useState(1);
  const [day, setDay] = useState(1);
  const [timeIndex, setTimeIndex] = useState(6);
  const [note, setNote] = useState("");
  const [tags, setTags] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function submit() {
    if (!name.trim()) {
      setErr("请填写姓名");
      return;
    }
    setBusy(true);
    setErr("");
    try {
      await api.create({
        name: name.trim(),
        gender,
        year,
        month,
        day,
        time_index: timeIndex,
        note,
        tags,
      });
      onDone(`已创建「${name}」`);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-mask" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>新建星盘</h3>
        {err && <div className="alert error">{err}</div>}
        <div className="form-row">
          <label>姓名 *</label>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="如：张三" autoFocus />
        </div>
        <div className="form-row">
          <label>性别</label>
          <select value={gender} onChange={(e) => setGender(e.target.value)}>
            <option value="男">男</option>
            <option value="女">女</option>
          </select>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
          <div className="form-row">
            <label>年</label>
            <input type="number" value={year} onChange={(e) => setYear(+e.target.value)} />
          </div>
          <div className="form-row">
            <label>月</label>
            <input type="number" min={1} max={12} value={month} onChange={(e) => setMonth(+e.target.value)} />
          </div>
          <div className="form-row">
            <label>日</label>
            <input type="number" min={1} max={31} value={day} onChange={(e) => setDay(+e.target.value)} />
          </div>
        </div>
        <div className="form-row">
          <label>出生时辰</label>
          <select value={timeIndex} onChange={(e) => setTimeIndex(+e.target.value)}>
            {TIME_OPTIONS.map((t, i) => (
              <option key={i} value={i}>
                {t}
              </option>
            ))}
          </select>
        </div>
        <div className="form-row">
          <label>标签（逗号分隔）</label>
          <input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="如：客户,VIP" />
        </div>
        <div className="form-row">
          <label>备注</label>
          <textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} />
        </div>
        <div className="form-actions">
          <button onClick={onClose} disabled={busy}>
            取消
          </button>
          <button className="primary" onClick={submit} disabled={busy}>
            {busy ? "排盘中…" : "创建并排盘"}
          </button>
        </div>
      </div>
    </div>
  );
}

function EditModal({
  row,
  onClose,
  onDone,
}: {
  row: Chart;
  onClose: () => void;
  onDone: (msg: string) => void;
}) {
  const [name, setName] = useState(row.name);
  const [note, setNote] = useState(row.note || "");
  const [tags, setTags] = useState(row.tags || "");
  const [rating, setRating] = useState(row.star_rating || 0);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function submit() {
    setBusy(true);
    setErr("");
    try {
      await api.update(row.id, {
        name: name.trim(),
        note,
        tags,
        star_rating: rating,
      });
      onDone(`已保存「${name}」`);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-mask" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>编辑 · {row.name}</h3>
        {err && <div className="alert error">{err}</div>}
        <div className="form-row">
          <label>姓名</label>
          <input value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="form-row">
          <label>标签</label>
          <input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="如：客户,VIP" />
        </div>
        <div className="form-row">
          <label>评分（0-5）</label>
          <select value={rating} onChange={(e) => setRating(+e.target.value)}>
            {[0, 1, 2, 3, 4, 5].map((n) => (
              <option key={n} value={n}>
                {"★".repeat(n) || "无"}
              </option>
            ))}
          </select>
        </div>
        <div className="form-row">
          <label>备注</label>
          <textarea rows={3} value={note} onChange={(e) => setNote(e.target.value)} />
        </div>
        <div className="form-actions">
          <button onClick={onClose} disabled={busy}>
            取消
          </button>
          <button className="primary" onClick={submit} disabled={busy}>
            {busy ? "保存中…" : "保存"}
          </button>
        </div>
      </div>
    </div>
  );
}
