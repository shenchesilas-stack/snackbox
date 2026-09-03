# -*- coding: utf-8 -*-
"""立一个门类的骨架：data/<id>/category.json + 一盒 + 若干颗，全是【待舌头】（关拦着，上桌前得有真吃过的人填）。

  venv/bin/python tools/new_category.py <id> <名字> <emoji> --box <盒id> <盒名> <kind> --pieces 颗名1,颗名2 [--wish "谁许的·条件"]
  例：venv/bin/python tools/new_category.py sweet-potato 烤红薯 🍠 --box 1_street 街边一个 bag --pieces 烤红薯 --wish "Clio 3069#4·舌头得是冬天站街边等出炉的人"
已存在的门类不覆盖。
"""
import argparse, json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = "【待舌头】"


def slug(s, i):
    s = re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")
    return s or "p%02d" % i


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cid"); ap.add_argument("name"); ap.add_argument("emoji")
    ap.add_argument("--box", nargs=3, metavar=("BOX_ID", "BOX_NAME", "KIND"), required=True)
    ap.add_argument("--pieces", default="")
    ap.add_argument("--wish", default="")
    ap.add_argument("--count", type=int, default=1)
    a = ap.parse_args()
    d = os.path.join(ROOT, "data", a.cid)
    if os.path.isdir(d):
        print("已有门类:", d); return 1
    os.makedirs(d)
    cat = {"name": a.name, "emoji": a.emoji, "look": T + " 这个门类摆在桌上是什么样", "load": []}
    if a.wish:
        cat["wishes"] = [a.wish]
    json.dump(cat, open(os.path.join(d, "category.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    bid, bname, kind = a.box
    names = [x.strip() for x in a.pieces.split(",") if x.strip()] or [bname]
    pieces = []
    for i, n in enumerate(names, 1):
        pieces.append({"id": slug(n, i) if n.isascii() else "p%02d" % i, "name": n, "form": T, "count": a.count,
                       "tray": T, "wrap": T, "look": T, "smell": T, "first_seconds": T, "melt": T,
                       "aftertaste": [{"at_min": 0, "text": T}, {"at_min": 3, "text": T}], "aftertaste_minutes": 6})
    box = {"id": bid, "name": bname, "kind": kind, "look": T, "pieces": pieces}
    json.dump(box, open(os.path.join(d, bid + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("立了:", a.emoji, a.name, "→", d, "·", len(pieces), "颗待舌头")
    return 0


if __name__ == "__main__":
    sys.exit(main())
