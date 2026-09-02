# -*- coding: utf-8 -*-
"""codex 草稿 → 盒子 JSON → 过关 → 给她过舌头的表。

用法：
  venv/bin/python tools/draft_to_box.py drafts/tin_codex.json --box 3_tin --name "铁盒" --kind tin \
      --look "方铁盒……" [--note "便签"] [--out data/chocolate/3_tin.json] [--table drafts/tin_review.md]

输入：codex 输出的 JSON 数组（每项 = 一颗，字段照清单），或 {"pieces": [...]} 。
不写 --out 时只出表和过关报告，不落盘。落盘前先跑 gate（起草模式：【待舌头】只提醒不拦）。
"""
import argparse, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import gate

COLS = ["id", "name", "form", "cocoa", "count", "tray", "wrap", "look", "smell",
        "first_seconds", "melt", "aftertaste", "aftertaste_minutes"]


def _cell(v):
    if isinstance(v, list):
        return "<br>".join("%s′ %s" % (s.get("at_min", "?"), s.get("text", "")) for s in v)
    return str(v if v is not None else "").replace("\n", " ").replace("|", "／")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("draft")
    ap.add_argument("--box", required=True, help="盒 id，如 3_tin")
    ap.add_argument("--name", required=True)
    ap.add_argument("--kind", required=True, choices=["bar", "ball", "tin"])
    ap.add_argument("--look", required=True, help="盒子外观一句")
    ap.add_argument("--note", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--table", default="")
    a = ap.parse_args()

    raw = json.load(open(a.draft, encoding="utf-8"))
    pieces = raw["pieces"] if isinstance(raw, dict) else raw
    # 补默认：铁盒每种一颗；weight 是排序用的草稿字段，不进盒
    clean = []
    for p in pieces:
        q = {k: v for k, v in p.items() if k in gate.PIECE_FIELDS}
        q.setdefault("count", 1)
        if "cocoa" in q and isinstance(q["cocoa"], str):
            try:
                q["cocoa"] = float(q["cocoa"].rstrip("%"))
            except ValueError:
                pass
        clean.append(q)
    box = {"id": a.box, "name": a.name, "kind": a.kind, "look": a.look, "pieces": clean}
    if a.note:
        box["note"] = a.note

    bp, pp = gate.check_box(box, serving=False)
    unfinished = sum(json.dumps(p, ensure_ascii=False).count(gate.UNFINISHED) for p in clean)
    print("盒级:", "过" if not bp else "不过 → " + "; ".join(bp))
    for p in clean:
        probs = pp.get(p.get("id"))
        print("  %s %s%s" % ("✗" if probs else "✓", p.get("id"), (" → " + "; ".join(probs)) if probs else ""))
    print("【待舌头】共 %d 处（上架时拒载）" % unfinished)

    lines = ["| " + " | ".join(COLS) + " |", "|" + "---|" * len(COLS)]
    for p in clean:
        lines.append("| " + " | ".join(_cell(p.get(c)) for c in COLS) + " |")
    table = "\n".join(lines)
    if a.table:
        open(a.table, "w", encoding="utf-8").write("# %s · 过舌头表\n\n" % a.name + table + "\n")
        print("表 →", a.table)
    else:
        print(table)

    if a.out:
        if bp:
            print("盒级不过，不落盘。")
            return 1
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        json.dump(box, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("盒 →", a.out, "（%d 颗；不过关的颗上架时会被拒载）" % len(clean))
    return 0


if __name__ == "__main__":
    sys.exit(main())
