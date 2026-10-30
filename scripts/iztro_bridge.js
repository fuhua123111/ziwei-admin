#!/usr/bin/env node
/**
 * iztro 桥接脚本
 * Python 后端通过 stdin 传 JSON，本脚本调用 iztro 排盘后把结果从 stdout 返回。
 *
 * 支持的操作：
 *   { op: "status" }                           -> 引擎健康检查
 *   { op: "bySolar", solarDate, timeIndex, gender, fixLeap, language }
 *   { op: "batch", items: [...], language }     -> 批量排盘
 *   { op: "horoscope", solarDate, timeIndex, gender, targetDate, language }
 */
const path = require("path");

function loadIztro() {
  // 优先项目根 node_modules，其次 backend 同级
  const candidates = [
    "iztro",
    path.join(__dirname, "..", "node_modules", "iztro"),
  ];
  let lastErr;
  for (const c of candidates) {
    try {
      return require(c);
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr;
}

function readStdin() {
  return new Promise((resolve, reject) => {
    let buf = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (d) => (buf += d));
    process.stdin.on("end", () => resolve(buf));
    process.stdin.on("error", reject);
  });
}

function normalize(astrolabe, engineTag) {
  const palaces = astrolabe.palaces.map((p) => ({
    index: p.index,
    name: p.name,
    heavenlyStem: p.heavenlyStem,
    earthlyBranch: p.earthlyBranch,
    isBodyPalace: p.isBodyPalace,
    isOriginalPalace: p.isOriginalPalace,
    majorStars: (p.majorStars || []).map(simplifyStar),
    minorStars: (p.minorStars || []).map(simplifyStar),
    adjectiveStars: (p.adjectiveStars || []).map(simplifyStar),
    changsheng12: p.changsheng12,
    boshi12: p.boshi12,
    jiangqian12: p.jiangqian12,
    suiqian12: p.suiqian12,
    decadal: { range: p.decadal ? p.decadal.range : [] },
    ages: p.ages || [],
  }));

  // 从四柱天干推四化，便于前端直接展示
  const mutagens = [];
  try {
    const stems = (astrolabe.chineseDate || "").split(" ").map((x) => x[0]);
    const names = ["年四化", "月四化", "日四化", "时四化"];
    stems.forEach((stem, i) => {
      if (!stem) return;
      const stars = astrolabe.star
        ? []
        : [];
      mutagens.push({ label: names[i] || `四化${i}`, stems: stem, stars });
    });
  } catch (e) {
    /* 忽略 */
  }

  return {
    solarDate: astrolabe.solarDate,
    lunarDate: astrolabe.lunarDate,
    chineseDate: astrolabe.chineseDate,
    time: astrolabe.time,
    timeRange: astrolabe.timeRange,
    gender: astrolabe.gender,
    zodiac: astrolabe.zodiac,
    sign: astrolabe.sign,
    soul: astrolabe.soul,
    body: astrolabe.body,
    fiveElementsClass: astrolabe.fiveElementsClass,
    earthlyBranchOfSoulPalace: astrolabe.earthlyBranchOfSoulPalace,
    earthlyBranchOfBodyPalace: astrolabe.earthlyBranchOfBodyPalace,
    palaces,
    mutagens,
    copyright: astrolabe.copyright || "",
    _engine: engineTag,
  };
}

function simplifyStar(s) {
  return {
    name: s.name,
    type: s.type,
    scope: s.scope,
    brightness: s.brightness || "",
    mutagen: s.mutagen || "",
  };
}

function collectMutagens(astrolabe) {
  const out = [];
  const stems = (astrolabe.chineseDate || "").split(" ").filter(Boolean);
  const labels = ["年四化", "月四化", "日四化", "时四化"];
  let util;
  try {
    util = require("iztro/lib/utils");
  } catch (e) {
    util = null;
  }
  stems.forEach((gz, i) => {
    const stem = gz[0];
    let stars = [];
    if (util && typeof util.getMutagensByHeavenlyStem === "function") {
      try {
        stars = util.getMutagensByHeavenlyStem(stem);
      } catch (e) {
        stars = [];
      }
    }
    out.push({ label: labels[i] || `四化${i}`, stems: stem, stars });
  });
  return out;
}

async function main() {
  const input = await readStdin();
  let req;
  try {
    req = JSON.parse(input || "{}");
  } catch (e) {
    process.stdout.write(JSON.stringify({ ok: false, error: "无效的 JSON 输入" }));
    return;
  }

  let iztro;
  try {
    iztro = loadIztro();
  } catch (e) {
    process.stdout.write(JSON.stringify({
      ok: false,
      error: "未能加载 iztro，请先执行 npm install",
      detail: String(e.message || e),
    }));
    return;
  }

  const { astro } = iztro;
  const pkg = require("iztro/package.json");

  try {
    switch (req.op) {
      case "status": {
        process.stdout.write(JSON.stringify({
          ok: true,
          iztro: pkg.version,
          license: pkg.license,
          node: process.version,
          features: ["bySolar", "byLunar", "horoscope", "batch"],
        }));
        break;
      }

      case "bySolar": {
        const a = astro.bySolar(
          req.solarDate, req.timeIndex, req.gender,
          req.fixLeap !== false, req.language || "zh-CN"
        );
        const data = normalize(a, "iztro");
        data.mutagens = collectMutagens(a);
        process.stdout.write(JSON.stringify({ ok: true, data }));
        break;
      }

      case "batch": {
        const results = [];
        for (const it of req.items || []) {
          const a = astro.bySolar(
            it.solarDate, it.timeIndex, it.gender,
            it.fixLeap !== false, req.language || "zh-CN"
          );
          const data = normalize(a, "iztro");
          data.mutagens = collectMutagens(a);
          data.key = it.key;
          results.push(data);
        }
        process.stdout.write(JSON.stringify({ ok: true, data: results }));
        break;
      }

      case "horoscope": {
        const a = astro.bySolar(
          req.solarDate, req.timeIndex, req.gender,
          true, req.language || "zh-CN"
        );
        const h = a.horoscope(req.targetDate);
        process.stdout.write(JSON.stringify({
          ok: true,
          data: {
            solarDate: req.targetDate,
            decadal: h.decadal,
            age: h.age,
            yearly: h.yearly,
            monthly: h.monthly,
          },
        }));
        break;
      }

      default:
        process.stdout.write(JSON.stringify({ ok: false, error: `未知操作: ${req.op}` }));
    }
  } catch (e) {
    process.stdout.write(JSON.stringify({ ok: false, error: String(e.message || e) }));
  }
}

main();
