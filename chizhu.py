#!/usr/bin/env python3
import argparse
import html
import json
import os
import random
import shutil
import sys
import unicodedata
import uuid
import webbrowser
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

VERSION = "1.0.0"
DEFAULT_DATA = Path(__file__).resolve().parent / "data" / "mistakes.jsonl"
SEVERITIES = {"minor": "轻微", "normal": "一般", "major": "严重", "fatal": "灾难"}


def data_path(args):
    return Path(args.data or os.environ.get("CHIZHU_DATA") or DEFAULT_DATA)


def load_records(path):
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict) and rec.get("id"):
            records.append(rec)
    return records


def save_records(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    tmp.replace(path)


def dwidth(s):
    w = 0
    for ch in s:
        w += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return w


def pad(s, width):
    return s + " " * max(width - dwidth(s), 0)


def center(s, width):
    total = max(width - dwidth(s), 0)
    left = total // 2
    return " " * left + s + " " * (total - left)


def truncate(s, width):
    if width <= 0:
        return ""
    if dwidth(s) <= width:
        return s
    acc = 0
    out = []
    for ch in s:
        cw = 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
        if acc + cw > width - 1:
            break
        out.append(ch)
        acc += cw
    return "".join(out) + "…"


def fmt_time(iso):
    try:
        return datetime.fromisoformat(iso).strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return str(iso)


def parse_time(iso):
    try:
        return datetime.fromisoformat(iso)
    except (ValueError, TypeError):
        return None


def find_record(records, prefix):
    matches = [r for r in records if str(r.get("id", "")).startswith(prefix)]
    if not matches:
        raise SystemExit(f"错误:找不到 ID 前缀为 {prefix!r} 的记录。")
    if len(matches) > 1:
        ids = ", ".join(r["id"] for r in matches)
        raise SystemExit(f"错误:ID 前缀 {prefix!r} 匹配到多条({ids}),请用更长的前缀。")
    return matches[0]


def cmd_add(args, path):
    records = load_records(path)
    rec = {
        "id": uuid.uuid4().hex[:6],
        "time": datetime.now().astimezone().isoformat(timespec="seconds"),
        "model": args.model.strip(),
        "mistake": args.mistake.strip(),
        "reason": args.reason.strip(),
        "severity": args.severity,
        "context": (args.context or "").strip(),
        "tags": [t.strip() for t in (args.tags or "").replace("\r", ",").replace("\n", ",").split(",") if t.strip()],
        "resolved": False,
        "resolved_note": "",
    }
    while any(r["id"] == rec["id"] for r in records):
        rec["id"] = uuid.uuid4().hex[:6]
    records.append(rec)
    save_records(path, records)
    print(f"已钉上耻辱柱  [{rec['id']}]  {SEVERITIES[rec['severity']]}  {rec['model']}  {fmt_time(rec['time'])}")
    print(f"错误:{rec['mistake']}")
    print(f"原因:{rec['reason']}")


def cmd_list(args, path):
    records = load_records(path)
    if args.model:
        needle = args.model.lower()
        records = [r for r in records if needle in str(r.get("model", "")).lower()]
    if args.severity:
        records = [r for r in records if r.get("severity") == args.severity]
    records.sort(key=lambda r: str(r.get("time", "")), reverse=True)
    total = len(records)
    if not records:
        print("没有匹配的记录——柱上空空如也。")
        return
    if not args.all:
        records = records[: args.limit]
    term = shutil.get_terminal_size((120, 24)).columns
    col_id, col_time, col_sev = 6, 16, 4
    col_model = min(max([dwidth(str(r.get("model", ""))) for r in records] + [4]), 14)
    rest = max(term - (col_id + col_time + col_model + col_sev + 10), 30)
    col_m = max(rest // 2, 12)
    col_r = max(rest - col_m, 12)
    header = (
        pad("ID", col_id)
        + "  "
        + pad("时间", col_time)
        + "  "
        + pad("模型", col_model)
        + "  "
        + pad("级别", col_sev)
        + "  "
        + pad("错误", col_m)
        + "  "
        + pad("原因", col_r)
    )
    print(header)
    print("─" * min(dwidth(header), term))
    for r in records:
        mark = "✓" if r.get("resolved") else " "
        line = (
            pad(str(r.get("id", "")), col_id)
            + "  "
            + pad(fmt_time(r.get("time")), col_time)
            + "  "
            + pad(truncate(str(r.get("model", "")), col_model), col_model)
            + "  "
            + pad(SEVERITIES.get(r.get("severity", "normal"), "?"), col_sev)
            + "  "
            + pad(truncate(str(r.get("mistake", "")), col_m), col_m)
            + "  "
            + mark
            + truncate(str(r.get("reason", "")), col_r - 2)
        )
        print(line)
    shown = len(records)
    print(f"\n共 {total} 条,显示 {shown} 条。" + ("" if args.all else " (--all 查看全部)"))


def cmd_show(args, path):
    records = load_records(path)
    r = find_record(records, args.id)
    print(f"[{r['id']}]  {fmt_time(r.get('time'))}")
    print(f"模型:{r.get('model', '')}    级别:{SEVERITIES.get(r.get('severity', 'normal'), '?')}")
    print(f"错误:{r.get('mistake', '')}")
    print(f"原因:{r.get('reason', '')}")
    if r.get("context"):
        print(f"背景:{r['context']}")
    if r.get("tags"):
        print(f"标签:{', '.join(r['tags'])}")
    if r.get("resolved"):
        note = f"(备注:{r['resolved_note']})" if r.get("resolved_note") else ""
        print(f"状态:已吸取教训{note}")
    else:
        print("状态:未吸取教训")


def cmd_resolve(args, path):
    records = load_records(path)
    r = find_record(records, args.id)
    if r.get("resolved"):
        print(f"[{r['id']}] 早已吸取教训,无需重复标记。")
        return
    r["resolved"] = True
    r["resolved_note"] = (args.note or "").strip()
    save_records(path, records)
    print(f"[{r['id']}] 已标记为「吸取教训」。" + (f"备注:{r['resolved_note']}" if r["resolved_note"] else ""))


def cmd_del(args, path):
    records = load_records(path)
    r = find_record(records, args.id)
    if not args.force:
        raise SystemExit("错误:耻辱不该被轻易抹去。确认请加 --force。")
    records.remove(r)
    save_records(path, records)
    print(f"[{r['id']}] 已从耻辱柱上取下:{r.get('mistake', '')}")


def bar(n, max_n):
    if n <= 0:
        return "·"
    return "█" * max(1, round(n / max_n * 20)) if max_n else "·"


def cmd_stats(args, path):
    records = load_records(path)
    if not records:
        print("柱上空空如也,无数据可统计。")
        return
    now = datetime.now().astimezone()
    unresolved = sum(1 for r in records if not r.get("resolved"))
    last7 = sum(1 for r in records if (t := parse_time(r.get("time", ""))) and now - t <= timedelta(days=7))
    last30 = sum(1 for r in records if (t := parse_time(r.get("time", ""))) and now - t <= timedelta(days=30))
    print(f"柱上共计:{len(records)} 条,未吸取教训:{unresolved} 条")
    print(f"近 7 天:{last7} 条 | 近 30 天:{last30} 条\n")

    by_model = Counter(str(r.get("model", "?")) for r in records)
    print("按模型(惯犯榜):")
    mw = min(max(dwidth(m) for m in by_model), 20)
    for m, n in by_model.most_common():
        print(f"  {pad(truncate(m, mw), mw)}  {n:>3}  {bar(n, by_model.most_common(1)[0][1])}")
    print()

    by_sev = Counter(r.get("severity", "normal") for r in records)
    print("按级别:")
    for key in ("fatal", "major", "normal", "minor"):
        if by_sev.get(key):
            n = by_sev[key]
            print(f"  {pad(SEVERITIES[key], 6)}  {n:>3}  {bar(n, max(by_sev.values()))}")


def cmd_reflect(args, path):
    records = load_records(path)
    if not records:
        print("耻辱柱上空空如也,无事可思。")
        return
    unresolved = [r for r in records if not r.get("resolved")]
    pool = unresolved or records
    r = random.choice(pool)
    lines = [f"[{SEVERITIES.get(r.get('severity', 'normal'), '?')}] {r.get('model', '')}  {fmt_time(r.get('time'))}"]
    lines.append(f"错误:{r.get('mistake', '')}")
    lines.append(f"原因:{r.get('reason', '')}")
    if r.get("context"):
        lines.append(f"背景:{r['context']}")
    term = shutil.get_terminal_size((80, 24)).columns
    width = min(max(max(dwidth(x) for x in lines) + 2, 40), term - 4)
    print(center("面 壁 思 过", width))
    print("┌" + "─" * (width + 2) + "┐")
    for line in lines:
        print("│ " + pad(truncate(line, width), width) + " │")
    print("└" + "─" * (width + 2) + "┘")
    if unresolved:
        print("吸取教训后可用 resolve 命令销账。")


SEVERITY_COLORS = {"minor": "#8b93a1", "normal": "#4c8dff", "major": "#ff9f43", "fatal": "#ff4d5e"}


def cmd_export(args, path):
    records = load_records(path)
    records.sort(key=lambda r: str(r.get("time", "")), reverse=True)
    unresolved = sum(1 for r in records if not r.get("resolved"))
    by_sev = Counter(r.get("severity", "normal") for r in records)

    chips = [f'<span class="chip">共 {len(records)} 条</span>',
             f'<span class="chip warn">未吸取教训 {unresolved} 条</span>']
    for key in ("fatal", "major", "normal", "minor"):
        chips.append(f'<span class="chip" style="border-color:{SEVERITY_COLORS[key]}">{SEVERITIES[key]} {by_sev.get(key, 0)}</span>')

    cards = []
    for r in records:
        sev = r.get("severity", "normal")
        color = SEVERITY_COLORS.get(sev, "#4c8dff")
        parts = [f'<div class="row"><span class="sev" style="background:{color}">{html.escape(SEVERITIES.get(sev, "?"))}</span>'
                 f'<span class="model">{html.escape(str(r.get("model", "")))}</span>'
                 f'<span class="time">{html.escape(fmt_time(r.get("time")))}</span></div>']
        parts.append(f'<h2>{html.escape(str(r.get("mistake", "")))}</h2>')
        parts.append(f'<p class="reason"><b>原因</b>{html.escape(str(r.get("reason", "")))}</p>')
        if r.get("context"):
            parts.append(f'<p class="ctx"><b>背景</b>{html.escape(str(r["context"]))}</p>')
        if r.get("tags"):
            tags = "".join(f'<span class="tag">#{html.escape(t)}</span>' for t in r["tags"])
            parts.append(f'<div class="tags">{tags}</div>')
        if r.get("resolved"):
            note = html.escape(str(r.get("resolved_note", "")))
            parts.append(f'<div class="ok">已吸取教训{(" · " + note) if note else ""}</div>')
        cards.append(f'<article class="card" style="border-left-color:{color}">{"".join(parts)}</article>')

    page = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>耻辱柱 · AI 错误记录</title>
<style>
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: #0e1013; color: #d7dae0; font-family: system-ui, "Microsoft YaHei", sans-serif; }}
header {{ text-align: center; padding: 48px 16px 8px; }}
h1 {{ margin: 0; font-size: 40px; letter-spacing: 12px; color: #f1f3f5; }}
.slogan {{ color: #6b7280; margin: 12px 0 20px; }}
.chips {{ display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; }}
.chip {{ border: 1px solid #2a2f3a; border-radius: 999px; padding: 4px 12px; font-size: 13px; color: #aab1bd; }}
.chip.warn {{ border-color: #ff4d5e; color: #ff8a93; }}
main {{ max-width: 780px; margin: 0 auto; padding: 24px 16px 64px; display: flex; flex-direction: column; gap: 16px; }}
.card {{ background: #151920; border: 1px solid #232936; border-left: 4px solid #4c8dff; border-radius: 10px; padding: 16px 20px; }}
.row {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }}
.sev {{ color: #0e1013; font-weight: 700; font-size: 12px; border-radius: 4px; padding: 2px 8px; }}
.model {{ font-weight: 600; color: #e8eaee; }}
.time {{ margin-left: auto; color: #6b7280; font-size: 13px; }}
.card h2 {{ margin: 10px 0 6px; font-size: 17px; color: #f1f3f5; font-weight: 600; }}
.reason, .ctx {{ margin: 4px 0; color: #aab1bd; font-size: 14px; line-height: 1.7; }}
.reason b, .ctx b {{ color: #6b7280; font-weight: 600; margin-right: 10px; font-size: 12px; }}
.tags {{ margin-top: 8px; display: flex; gap: 6px; flex-wrap: wrap; }}
.tag {{ color: #7c8698; font-size: 12px; border: 1px solid #232936; border-radius: 4px; padding: 1px 6px; }}
.ok {{ margin-top: 10px; color: #51cf87; font-size: 13px; }}
.empty {{ text-align: center; color: #6b7280; padding: 60px 0; }}
footer {{ text-align: center; color: #4b5563; font-size: 12px; padding-bottom: 40px; }}
</style>
</head>
<body>
<header>
<h1>耻 辱 柱</h1>
<p class="slogan">每一行错误,都值得被钉在柱上。</p>
<div class="chips">{''.join(chips)}</div>
</header>
<main>
{'<div class="empty">柱上空空如也——要么无错可记,要么无人认领。</div>' if not cards else ''.join(cards)}
</main>
<footer>生成于 {html.escape(fmt_time(datetime.now().astimezone().isoformat(timespec="seconds")))} · 共 {len(records)} 条记录</footer>
</body>
</html>"""
    out = Path(args.out)
    out.write_text(page, encoding="utf-8")
    print(f"耻辱墙已导出:{out.resolve()}")
    if args.open:
        webbrowser.open(out.resolve().as_uri())


INDEX_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>耻辱柱 · 实时监控台</title>
<style>
* { box-sizing: border-box; }
body { margin: 0; background: #0e1013; color: #d7dae0; font-family: system-ui, "Microsoft YaHei", sans-serif; }
header { text-align: center; padding: 36px 16px 8px; }
h1 { margin: 0; font-size: 36px; letter-spacing: 12px; color: #f1f3f5; }
.slogan { color: #6b7280; margin: 10px 0 16px; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; }
.chip { border: 1px solid #2a2f3a; border-radius: 999px; padding: 4px 12px; font-size: 13px; color: #aab1bd; }
.chip.warn { border-color: #ff4d5e; color: #ff8a93; }
.wrap { max-width: 820px; margin: 0 auto; padding: 20px 16px 64px; }
form { background: #151920; border: 1px solid #232936; border-radius: 10px; padding: 16px 20px; display: grid; grid-template-columns: 1fr; gap: 10px; }
details.addbox { margin-bottom: 18px; }
details.addbox summary { cursor: pointer; list-style: none; background: #151920; border: 1px solid #232936; border-radius: 10px; padding: 12px 18px; color: #9db9ff; letter-spacing: 6px; text-align: center; font-size: 14px; user-select: none; }
details.addbox summary::-webkit-details-marker { display: none; }
details.addbox summary:hover { border-color: #4c8dff; }
details.addbox[open] summary { border-color: #4c8dff; border-radius: 10px 10px 0 0; }
details.addbox form { border-radius: 0 0 10px 10px; }
form .full { grid-column: 1 / -1; }
label { font-size: 12px; color: #6b7280; display: block; margin-bottom: 4px; }
input, select, textarea { width: 100%; background: #10131a; border: 1px solid #232936; border-radius: 6px; color: #d7dae0; padding: 8px 10px; font: inherit; }
textarea { resize: vertical; }
button { font: inherit; cursor: pointer; border-radius: 6px; border: 1px solid #2a2f3a; background: #1d232e; color: #d7dae0; padding: 8px 14px; }
button:hover { border-color: #4c8dff; }
.primary { background: rgba(76, 141, 255, .13); border-color: #4c8dff; color: #9db9ff; letter-spacing: 4px; }
.btnrow { grid-column: 1 / -1; display: flex; gap: 10px; }
.btnrow button { flex: 1; }
.ghost { border-color: #2a2f3a; color: #8b93a1; }
details.addbox.editing summary { border-color: #2f9e63; color: #51cf87; }
.filters { display: flex; flex-wrap: wrap; gap: 12px; margin: 18px 0; align-items: center; }
.filters input, .filters select { width: auto; }
.filters label { margin: 0; display: flex; align-items: center; gap: 6px; }
.cardlist { display: flex; flex-direction: column; gap: 14px; }
.sec-title { margin: 30px 0 12px; color: #51cf87; font-size: 14px; font-weight: 600; letter-spacing: 4px; display: flex; align-items: center; gap: 12px; }
.sec-title::after { content: ""; flex: 1; height: 1px; background: #232936; }
.card.done { opacity: .72; }
.card { background: #151920; border: 1px solid #232936; border-left: 4px solid #4c8dff; border-radius: 10px; padding: 14px 18px; }
.row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.sev { color: #0e1013; font-weight: 700; font-size: 12px; border-radius: 4px; padding: 2px 8px; }
.model { font-weight: 600; color: #e8eaee; }
.time { margin-left: auto; color: #6b7280; font-size: 13px; }
.card h2 { margin: 8px 0 6px; font-size: 16px; color: #f1f3f5; font-weight: 600; white-space: pre-wrap; }
.reason, .ctx { margin: 4px 0; color: #aab1bd; font-size: 14px; line-height: 1.7; white-space: pre-wrap; }
.reason b, .ctx b { color: #6b7280; font-weight: 600; margin-right: 10px; font-size: 12px; }
.tags { margin-top: 8px; display: flex; gap: 6px; flex-wrap: wrap; }
.tag { color: #7c8698; font-size: 12px; border: 1px solid #232936; border-radius: 4px; padding: 1px 6px; }
.actions { margin-top: 10px; display: flex; gap: 8px; align-items: center; }
.btn { padding: 4px 10px; font-size: 13px; }
.okb { border-color: #2f9e63; color: #51cf87; }
.danger { border-color: #5c2530; color: #ff8a93; }
.done { color: #51cf87; font-size: 13px; }
.empty { text-align: center; color: #6b7280; padding: 60px 0; }
footer { text-align: center; color: #4b5563; font-size: 12px; padding-bottom: 40px; }
</style>
</head>
<body>
<header>
<h1>耻 辱 柱</h1>
<p class="slogan">每一行错误,都值得被钉在柱上。页面每 8 秒自动刷新。</p>
<div class="chips" id="chips"></div>
</header>
<div class="wrap">
<details class="addbox" id="addbox">
<summary>钉 一 条 新 错 误</summary>
<form id="form">
<div class="full"><label>模型 *</label><textarea name="model" required rows="2" placeholder="如 gpt-4o / claude-opus / omen-alpha"></textarea></div>
<div class="full"><label>级别</label>
<select name="severity">
<option value="normal">一般</option>
<option value="minor">轻微</option>
<option value="major">严重</option>
<option value="fatal">灾难</option>
</select></div>
<div class="full"><label>犯了什么错 *</label><textarea name="mistake" required rows="3" placeholder="简明描述错误行为,可换行"></textarea></div>
<div class="full"><label>为什么会犯(根因)*</label><textarea name="reason" required rows="4" placeholder="深入一点,别只写「大意了」"></textarea></div>
<div class="full"><label>案发背景</label><textarea name="context" rows="2" placeholder="任务 / 环境(可选)"></textarea></div>
<div class="full"><label>标签</label><textarea name="tags" rows="2" placeholder="逗号或换行分隔(可选)"></textarea></div>
<div class="btnrow">
<button class="primary" id="submitbtn" type="submit">钉 上 去</button>
<button class="ghost" id="cancelbtn" type="button" style="display: none">取 消 编 辑</button>
</div>
</form>
</details>
<div class="filters">
<input id="fmodel" placeholder="按模型过滤">
<select id="fsev">
<option value="">全部级别</option>
<option value="fatal">灾难</option>
<option value="major">严重</option>
<option value="normal">一般</option>
<option value="minor">轻微</option>
</select>
</div>
<div id="cards" class="cardlist"></div>
<div id="donewrap"></div>
</div>
<footer>耻辱柱实时监控台 · 数据:data/mistakes.jsonl</footer>
<script>
const SEV = { minor: "轻微", normal: "一般", major: "严重", fatal: "灾难" };
const COLOR = { minor: "#8b93a1", normal: "#4c8dff", major: "#ff9f43", fatal: "#ff4d5e" };
let records = [];
const state = { model: "", sev: "" };
let editingId = null;
const $ = id => document.getElementById(id);

async function api(url, body) {
  const opt = body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {};
  const r = await fetch(url, opt);
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.error || "HTTP " + r.status);
  return d;
}
function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}
function fmt(t) {
  try { return new Date(t).toLocaleString("zh-CN", { hour12: false }); } catch (e) { return t || ""; }
}
function card(r) {
  const sev = r.severity || "normal";
  const a = el("article", "card");
  a.style.borderLeftColor = COLOR[sev];
  const row = el("div", "row");
  const s = el("span", "sev", SEV[sev]);
  s.style.background = COLOR[sev];
  row.append(s, el("span", "model", r.model || "?"), el("span", "time", fmt(r.time)));
  a.append(row, el("h2", null, r.mistake || ""));
  const p = el("p", "reason");
  p.append(el("b", null, "原因"), document.createTextNode(r.reason || ""));
  a.append(p);
  if (r.context) {
    const c = el("p", "ctx");
    c.append(el("b", null, "背景"), document.createTextNode(r.context));
    a.append(c);
  }
  if (r.tags && r.tags.length) {
    const t = el("div", "tags");
    for (const x of r.tags) t.append(el("span", "tag", "#" + x));
    a.append(t);
  }
  const act = el("div", "actions");
  const eb = el("button", "btn", "编辑");
  eb.onclick = () => startEdit(r);
  act.append(eb);
  if (!r.resolved) {
    const b = el("button", "btn okb", "销账");
    b.onclick = async () => {
      const note = prompt("吸取了什么教训?(可留空)") || "";
      try { await api("/api/resolve", { id: r.id, note }); refresh(); } catch (e) { alert(e.message); }
    };
    act.append(b);
  } else {
    act.append(el("span", "done", "已吸取教训" + (r.resolved_note ? " · " + r.resolved_note : "")));
  }
  const d = el("button", "btn danger", "取下");
  d.onclick = async () => {
    if (confirm("耻辱不该被轻易抹去,确定取下?")) {
      try { await api("/api/delete", { id: r.id }); refresh(); } catch (e) { alert(e.message); }
    }
  };
  act.append(d);
  a.append(act);
  return a;
}
function render() {
  const chips = $("chips");
  chips.innerHTML = "";
  const openN = records.filter(r => !r.resolved).length;
  chips.append(el("span", "chip", "共 " + records.length + " 条"), el("span", "chip warn", "未吸取教训 " + openN + " 条"));
  for (const k of ["fatal", "major", "normal", "minor"]) {
    const n = records.filter(r => (r.severity || "normal") === k).length;
    const c = el("span", "chip", SEV[k] + " " + n);
    c.style.borderColor = COLOR[k];
    chips.append(c);
  }
  const list = records.filter(r =>
    (!state.model || (r.model || "").toLowerCase().includes(state.model)) &&
    (!state.sev || (r.severity || "normal") === state.sev)
  );
  const open = list.filter(r => !r.resolved);
  const done = list.filter(r => r.resolved);
  const cards = $("cards");
  cards.innerHTML = "";
  if (!open.length) {
    cards.append(el("div", "empty", records.length ? "没有未销账的记录,干得漂亮。" : "柱上空空如也——钉上第一条耻辱记录吧。"));
  } else {
    for (const r of open) cards.append(card(r));
  }
  const dw = $("donewrap");
  dw.innerHTML = "";
  if (done.length) {
    dw.append(el("h3", "sec-title", "已 吸 取 教 训 · " + done.length + " 条"));
    const dl = el("div", "cardlist");
    for (const r of done) {
      const c = card(r);
      c.classList.add("done");
      dl.append(c);
    }
    dw.append(dl);
  }
}
function startEdit(r) {
  editingId = r.id;
  const f = $("form");
  f.model.value = r.model || "";
  f.severity.value = r.severity || "normal";
  f.mistake.value = r.mistake || "";
  f.reason.value = r.reason || "";
  f.context.value = r.context || "";
  f.tags.value = (r.tags || []).join(", ");
  const box = $("addbox");
  box.setAttribute("open", "");
  box.classList.add("editing");
  $("submitbtn").textContent = "保 存 修 改";
  $("cancelbtn").style.display = "";
  f.scrollIntoView({ behavior: "smooth", block: "start" });
}
function resetForm() {
  editingId = null;
  const f = $("form");
  f.reset();
  $("addbox").classList.remove("editing");
  $("submitbtn").textContent = "钉 上 去";
  $("cancelbtn").style.display = "none";
}
async function refresh() {
  try { records = (await api("/api/records")).records; render(); } catch (e) {}
}
$("fmodel").oninput = e => { state.model = e.target.value.trim().toLowerCase(); render(); };
$("fsev").onchange = e => { state.sev = e.target.value; render(); };
$("form").onsubmit = async e => {
  e.preventDefault();
  const f = e.target;
  const payload = {
    model: f.model.value.trim(),
    mistake: f.mistake.value.trim(),
    reason: f.reason.value.trim(),
    severity: f.severity.value,
    context: f.context.value.trim(),
    tags: f.tags.value.trim()
  };
  try {
    if (editingId) {
      payload.id = editingId;
      await api("/api/edit", payload);
    } else {
      await api("/api/records", payload);
    }
    resetForm();
    f.closest("details").removeAttribute("open");
    refresh();
  } catch (err) { alert(err.message); }
};
$("cancelbtn").onclick = () => resetForm();
$("addbox").addEventListener("toggle", e => { if (!e.target.open && editingId) resetForm(); });
refresh();
setInterval(refresh, 8000);
</script>
</body>
</html>"""


def cmd_serve(args, path):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body, ctype):
            data = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _json(self, obj, code=200):
            self._send(code, json.dumps(obj, ensure_ascii=False), "application/json; charset=utf-8")

        def _body(self):
            length = int(self.headers.get("Content-Length") or 0)
            try:
                return json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                return None

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self._send(200, INDEX_HTML, "text/html; charset=utf-8")
            elif self.path == "/api/records":
                recs = load_records(path)
                recs.sort(key=lambda r: str(r.get("time", "")), reverse=True)
                self._json({"records": recs})
            else:
                self._json({"error": "not found"}, 404)

        def do_POST(self):
            payload = self._body()
            if payload is None:
                return self._json({"error": "请求体不是合法 JSON"}, 400)
            if self.path == "/api/records":
                model = str(payload.get("model", "")).strip()
                mistake = str(payload.get("mistake", "")).strip()
                reason = str(payload.get("reason", "")).strip()
                if not model or not mistake or not reason:
                    return self._json({"error": "model / mistake / reason 均不能为空"}, 400)
                severity = payload.get("severity", "normal")
                if severity not in SEVERITIES:
                    severity = "normal"
                recs = load_records(path)
                rec = {
                    "id": uuid.uuid4().hex[:6],
                    "time": datetime.now().astimezone().isoformat(timespec="seconds"),
                    "model": " ".join(model.split())[:200],
                    "mistake": mistake[:2000],
                    "reason": reason[:2000],
                    "severity": severity,
                    "context": str(payload.get("context", "")).strip()[:2000],
                    "tags": payload.get("tags", []),
                    "resolved": False,
                    "resolved_note": "",
                }
                if isinstance(rec["tags"], str):
                    rec["tags"] = [t.strip() for t in rec["tags"].replace("\r", ",").replace("\n", ",").split(",") if t.strip()][:20]
                while any(r["id"] == rec["id"] for r in recs):
                    rec["id"] = uuid.uuid4().hex[:6]
                recs.append(rec)
                save_records(path, recs)
                return self._json({"ok": True, "record": rec})
            if self.path == "/api/edit":
                recs = load_records(path)
                rid = str(payload.get("id", "")).strip()
                if not rid:
                    return self._json({"error": "缺少记录 ID"}, 400)
                try:
                    r = find_record(recs, rid)
                except SystemExit as exc:
                    return self._json({"error": str(exc)}, 404)
                model = str(payload.get("model", "")).strip()
                mistake = str(payload.get("mistake", "")).strip()
                reason = str(payload.get("reason", "")).strip()
                if not model or not mistake or not reason:
                    return self._json({"error": "model / mistake / reason 均不能为空"}, 400)
                severity = payload.get("severity", r.get("severity", "normal"))
                if severity not in SEVERITIES:
                    severity = "normal"
                r["model"] = " ".join(model.split())[:200]
                r["mistake"] = mistake[:2000]
                r["reason"] = reason[:2000]
                r["severity"] = severity
                r["context"] = str(payload.get("context", "")).strip()[:2000]
                tags = payload.get("tags", r.get("tags", []))
                if isinstance(tags, str):
                    tags = [t.strip() for t in tags.replace("\r", ",").replace("\n", ",").split(",") if t.strip()][:20]
                r["tags"] = tags
                save_records(path, recs)
                return self._json({"ok": True, "record": r})
            if self.path in ("/api/resolve", "/api/delete"):
                recs = load_records(path)
                rid = str(payload.get("id", "")).strip()
                if not rid:
                    return self._json({"error": "缺少记录 ID"}, 400)
                try:
                    r = find_record(recs, rid)
                except SystemExit as exc:
                    return self._json({"error": str(exc)}, 404)
                if self.path == "/api/resolve":
                    r["resolved"] = True
                    r["resolved_note"] = str(payload.get("note", "")).strip()[:500]
                else:
                    recs.remove(r)
                save_records(path, recs)
                return self._json({"ok": True})
            return self._json({"error": "not found"}, 404)

        def log_message(self, *args):
            pass

    url = f"http://{args.host}:{args.port}"
    try:
        server = ThreadingHTTPServer((args.host, args.port), Handler)
    except OSError as exc:
        raise SystemExit(f"错误:无法监听 {url}({exc}),端口可能被占用,试试 --port 换一个。")
    print(f"耻辱柱实时监控台已开张:{url}")
    print("Ctrl+C 停止。")
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def build_parser():
    sev_help = "级别:" + " ".join(f"{k}={v}" for k, v in SEVERITIES.items())
    parser = argparse.ArgumentParser(
        prog="chizhu",
        description="耻辱柱 —— 让 AI 把自己犯的错钉在柱上(时间、模型、原因,一条不少)。",
        epilog="示例:\n"
               "  python chizhu.py add -m gpt-4o -s fatal -c \"生产迁移\" -t \"数据库\" \"误删 users 表\" \"未确认环境就执行了 DROP\"\n"
               "  python chizhu.py list --model gpt-4o\n"
               "  python chizhu.py reflect\n"
               "  python chizhu.py serve\n"
               "  python chizhu.py export --open\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--data", help="数据文件路径(默认 %(default)s,或环境变量 CHIZHU_DATA)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("add", help="把一个错误钉上耻辱柱")
    p.add_argument("mistake", help="犯了什么错")
    p.add_argument("reason", help="为什么会犯(根因)")
    p.add_argument("-m", "--model", required=True, help="哪个模型犯的(如 gpt-4o / claude-opus / omen-alpha)")
    p.add_argument("-s", "--severity", choices=list(SEVERITIES), default="normal", metavar="LEVEL", help=sev_help)
    p.add_argument("-c", "--context", help="案发背景(任务/环境)")
    p.add_argument("-t", "--tags", help="标签,逗号分隔")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("list", help="查看柱上的耻辱记录")
    p.add_argument("-m", "--model", help="按模型过滤(子串匹配)")
    p.add_argument("-s", "--severity", choices=list(SEVERITIES), metavar="LEVEL", help="按级别过滤")
    p.add_argument("-n", "--limit", type=int, default=20, help="显示条数(默认 20)")
    p.add_argument("--all", action="store_true", help="显示全部记录")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("show", help="查看某条记录详情")
    p.add_argument("id", help="记录 ID(可用前缀)")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("resolve", help="标记某条错误已吸取教训(销账)")
    p.add_argument("id", help="记录 ID(可用前缀)")
    p.add_argument("--note", help="吸取了什么教训")
    p.set_defaults(func=cmd_resolve)

    p = sub.add_parser("del", help="从柱上取下记录(慎用,耻辱不该被抹去)")
    p.add_argument("id", help="记录 ID(可用前缀)")
    p.add_argument("--force", action="store_true", help="确认删除")
    p.set_defaults(func=cmd_del)

    p = sub.add_parser("stats", help="统计各模型/级别的耻辱数据(惯犯榜)")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("reflect", help="随机面壁:抽一条未吸取教训的错误反省")
    p.set_defaults(func=cmd_reflect)

    p = sub.add_parser("serve", help="启动本地 Web 实时监控台(网页查看/钉错误/销账)")
    p.add_argument("--host", default="127.0.0.1", help="监听地址(默认仅本机)")
    p.add_argument("--port", type=int, default=8737, help="端口(默认 %(default)s)")
    p.add_argument("--no-open", action="store_true", help="不自动打开浏览器")
    p.set_defaults(func=cmd_serve)

    p = sub.add_parser("export", help="导出 HTML 耻辱墙")
    p.add_argument("--out", default="shame_wall.html", help="输出文件(默认 %(default)s)")
    p.add_argument("--open", action="store_true", help="导出后在浏览器打开")
    p.set_defaults(func=cmd_export)

    return parser


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = build_parser()
    args = parser.parse_args()
    args.func(args, data_path(args))


if __name__ == "__main__":
    main()
