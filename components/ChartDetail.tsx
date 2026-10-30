"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Chart, PalaceRaw } from "@/lib/types";

/**
 * 星盘详情：以传统十二宫布局展示 iztro 排出的完整盘面
 *
 * 传统方位（4x4 网格，中间 2x2 为信息区）：
 *   巳 午 未 申
 *   辰  中  中 酉
 *   卯  中  中 戌
 *   寅 丑 子 亥
 *
 * 注意：后端经 Python dataclass 序列化，字段为 snake_case。
 */

const BRANCH_POS: Record<string, [number, number]> = {
  巳: [0, 0], 午: [0, 1], 未: [0, 2], 申: [0, 3],
  辰: [1, 0], 酉: [1, 3],
  卯: [2, 0], 戌: [2, 3],
  寅: [3, 0], 丑: [3, 1], 子: [3, 2], 亥: [3, 3],
};

export default function ChartDetail({
  id,
  onClose,
}: {
  id: number;
  onClose: () => void;
}) {
  const [chart, setChart] = useState<Chart | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const res = await api.get(id);
        if (alive) setChart(res.chart);
      } catch (e: any) {
        if (alive) setErr(e.message);
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [id]);

  const raw: any = chart?.raw;
  const palaces: PalaceRaw[] = raw?.palaces || [];

  return (
    <div className="modal-mask" onClick={onClose}>
      <div
        className="modal"
        style={{ maxWidth: 1120, width: "96vw" }}
        onClick={(e) => e.stopPropagation()}
      >
        {loading ? (
          <div className="loading">
            <span className="spinner" />
            加载星盘…
          </div>
        ) : err ? (
          <div className="alert error">{err}</div>
        ) : chart && raw ? (
          <>
            <div style={{ display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
              <h3 style={{ margin: 0, fontSize: 19 }}>
                {chart.name}
                <span className="muted" style={{ fontSize: 13, marginLeft: 8, fontWeight: 400 }}>
                  {chart.gender} · {raw.solar_date} {raw.time_name}
                </span>
              </h3>
              <span className="five-el">{raw.five_elements_class}</span>
              <div style={{ flex: 1 }} />
              <button onClick={onClose}>关闭</button>
            </div>

            <div className="info-grid">
              <Info k="阳历" v={raw.solar_date} />
              <Info k="农历" v={raw.lunar_date} />
              <Info k="干支" v={raw.chinese_date} />
              <Info k="时辰" v={`${raw.time_name} ${raw.time_range}`} />
              <Info k="生肖 / 星座" v={`${raw.zodiac} / ${raw.sign}`} />
              <Info k="命主 / 身主" v={`${raw.soul} / ${raw.body}`} />
              <Info k="命宫地支" v={raw.soul_branch} />
              <Info k="身宫地支" v={raw.body_branch} />
            </div>

            {raw.mutagens && raw.mutagens.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>
                  四化（禄 / 权 / 科 / 忌）
                </div>
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                  {raw.mutagens.map((m: any) => (
                    <div
                      key={m.label + m.stems}
                      style={{
                        background: "var(--bg-3)",
                        borderRadius: 8,
                        padding: "7px 12px",
                        fontSize: 12.5,
                      }}
                    >
                      <b>{m.stems}</b>
                      <span className="muted"> {m.label}：</span>
                      {m.stars && m.stars.length > 0 ? (
                        m.stars.map((s: string, i: number) => (
                          <span className={`pill mutagen-${["禄", "权", "科", "忌"][i]}`} key={s + i}>
                            {s}
                            {["禄", "权", "科", "忌"][i]}
                          </span>
                        ))
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div style={{ marginTop: 20 }}>
              <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>
                十二宫盘面（传统方位 · 金色边框为命宫，绿色为身宫）
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(4, 1fr)",
                  gap: 8,
                }}
              >
                {Array.from({ length: 16 }).map((_, idx) => {
                  const row = Math.floor(idx / 4);
                  const col = idx % 4;
                  const isCenter = row >= 1 && row <= 2 && col >= 1 && col <= 2;

                  if (isCenter) {
                    if (row === 1 && col === 1) {
                      return (
                        <div
                          key="center"
                          style={{
                            gridColumn: "2 / span 2",
                            gridRow: "2 / span 2",
                            background: "linear-gradient(160deg,#16203a,#101728)",
                            border: "1px solid var(--line-2)",
                            borderRadius: 10,
                            display: "flex",
                            flexDirection: "column",
                            alignItems: "center",
                            justifyContent: "center",
                            padding: 14,
                            gap: 5,
                          }}
                        >
                          <div style={{ fontSize: 16, fontWeight: 700 }}>{chart.name}</div>
                          <div className="muted" style={{ fontSize: 12 }}>
                            {raw.gender} · {raw.zodiac} · {raw.sign}
                          </div>
                          <div style={{ fontSize: 13, color: "var(--accent-2)", fontWeight: 600 }}>
                            {raw.five_elements_class}
                          </div>
                          <div className="muted" style={{ fontSize: 11.5, textAlign: "center", lineHeight: 1.7 }}>
                            命主 {raw.soul} · 身主 {raw.body}
                            <br />
                            {raw.chinese_date}
                          </div>
                        </div>
                      );
                    }
                    return null;
                  }

                  const branch = Object.keys(BRANCH_POS).find(
                    (b) => BRANCH_POS[b][0] === row && BRANCH_POS[b][1] === col
                  );
                  if (!branch) return <div key={idx} />;
                  const p = palaces.find((x) => x.earthly_branch === branch);
                  if (!p) {
                    return (
                      <div className="palace" key={idx}>
                        <div className="palace-head">
                          <span className="palace-name">{branch}宫</span>
                        </div>
                        <span className="muted" style={{ fontSize: 11 }}>
                          无数据
                        </span>
                      </div>
                    );
                  }
                  return <PalaceCard key={idx} p={p} />;
                })}
              </div>
            </div>

            <div className="muted" style={{ marginTop: 16, fontSize: 11.5, lineHeight: 1.8 }}>
              排盘引擎：{raw.copyright || "iztro (MIT License)"}
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}

function Info({ k, v }: { k: string; v: string }) {
  return (
    <div className="info-item">
      <div className="k">{k}</div>
      <div className="v">{v || "—"}</div>
    </div>
  );
}

function PalaceCard({ p }: { p: PalaceRaw }) {
  const isMing = p.name === "命宫";
  const isBody = p.is_body_palace;
  return (
    <div
      className={`palace${isMing ? " is-ming" : ""}${isBody ? " is-body" : ""}`}
      title={`${p.name}（${p.heavenly_stem}${p.earthly_branch}）${
        p.decadal_range && p.decadal_range.length
          ? ` 大限 ${p.decadal_range[0]}-${p.decadal_range[1]} 岁`
          : ""
      }`}
    >
      <div className="palace-head">
        <span className="palace-name">
          {p.name}
          {isBody && (
            <span style={{ color: "var(--accent-2)", fontSize: 10, marginLeft: 4 }}>身</span>
          )}
        </span>
        <span className="palace-gz">
          {p.heavenly_stem}
          {p.earthly_branch}
        </span>
      </div>

      <div className="palace-major">
        {p.major_stars.length === 0 ? (
          <span className="muted" style={{ fontSize: 11 }}>
            无主星
          </span>
        ) : (
          p.major_stars.map((s) => (
            <span className="pill major" key={s.name}>
              {s.name}
              {s.brightness && (
                <span style={{ opacity: 0.75, fontSize: 10 }}> {s.brightness}</span>
              )}
              {s.mutagen && <span style={{ color: "#ff9ba3", fontSize: 10 }}> {s.mutagen}</span>}
            </span>
          ))
        )}
      </div>

      {p.minor_stars && p.minor_stars.length > 0 && (
        <div className="palace-minor">
          {p.minor_stars.map((s) => (
            <span className="pill minor" key={s.name}>
              {s.name}
              {s.mutagen && <span style={{ color: "#ff9ba3", fontSize: 10 }}> {s.mutagen}</span>}
            </span>
          ))}
        </div>
      )}

      {p.adjective_stars && p.adjective_stars.length > 0 && (
        <div className="palace-adj">{p.adjective_stars.map((s) => s.name).join(" · ")}</div>
      )}

      {p.decadal_range && p.decadal_range.length > 0 && (
        <div className="muted" style={{ position: "absolute", right: 9, bottom: 6, fontSize: 10 }}>
          {p.decadal_range[0]}-{p.decadal_range[1]}
        </div>
      )}
    </div>
  );
}
