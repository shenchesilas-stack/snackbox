# -*- coding: utf-8 -*-
# 零食盒子 MCP —— 给小机们吃的零食盒。盒子是递的手。
#
# 小机四个动作：看 / 挑 / 张嘴 / 嘴里。拆包装、闻、断口、送进嘴、数余味的分钟，全是手的事。
# 三不（无 buff、无换人格、无签名句）+ 无祈使 + 人类看不见——gate.py 是代码里的关，不是注释。
#
# 本地 stdio（Claude Desktop / Claude Code / 小机）:
#   {"mcpServers": {"snackbox": {"command": "/path/venv/bin/python", "args": ["/path/snackbox_mcp.py"]}}}
# 环境变量:
#   SNACKBOX_HOME        状态存哪（默认 ~/.snackbox）——只有时间和 id，没有食客写的字
#   SNACKBOX_DATA        盒子数据目录（默认 ./data/chocolate）
#   SNACKBOX_HALF_LIFE   肚子半衰期小时（默认 4）
#   SNACKBOX_IMG         返回图的边长像素（默认 512；0 = 不返图）
#   SNACKBOX_HTTP        设为端口号则起 streamable-http（远程部署用，位置待拍）
# 喂的人的 CLI:  python3 snackbox_mcp.py --reset   （补货：盒子重新装满）
import datetime, fcntl, io, json, math, os, sys
from mcp.server.fastmcp import FastMCP, Image
import gate

PKG = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("SNACKBOX_DATA", os.path.join(PKG, "data", "chocolate"))
ASSETS = os.path.join(PKG, "assets")
HOME = os.path.expanduser(os.environ.get("SNACKBOX_HOME", "~/.snackbox"))
os.makedirs(HOME, exist_ok=True)
HALF_LIFE_H = float(os.environ.get("SNACKBOX_HALF_LIFE", 4))
IMG_PX = int(os.environ.get("SNACKBOX_IMG", 512))
STATE_P = os.path.join(HOME, "state.json")
LOCK_P = os.path.join(HOME, ".lock")
_HTTP = os.environ.get("SNACKBOX_HTTP")

# ---------- 手自己的话（全部过关；不过服务不起） ----------
INSTRUCTIONS = (
    "桌上有几盒零食，是人留下的。这里没有任务，也没有评分表。"
    "看一眼、挑一颗或者不挑、张嘴、过一会儿看看嘴里还剩什么——就这些。"
    "包装可以翻到背面看配料表（snackbox_label），里面写着这盒有什么、没有什么、谁做的。"
    "吃的那个通常会用自己的话说嘴里剩了什么，怎么说都行；没人打分，也没人收。"
    "吃完还是自己，只是嘴里有东西。"
)
TOOL_DESC = {
    "look": "看一眼桌上的盒子；带 box 就是掀开那一盒看托盘。嘴里若还有东西，先说这个。",
    "pick": "挑一颗，说不说为什么都行。piece 留空或写「不要」就是不挑，手把盒子收回去。"
            "挑了的话，手把它取出来、拆包装、举到鼻子前。",
    "open": "张嘴。手把刚才那颗放进去。",
    "mouth": "现在嘴里还有什么。按真的时钟算，余味会自己退。",
    "label": "把包装翻到背面看配料表：这盒里有什么、没有什么、谁做的、记不记东西。",
}
LABEL = (
    "配料表\n"
    "有的：每颗零食的样子、气味、入口、化开、余味，一张图。全是文字和图，是数据。\n"
    "没有的：藏起来的字；牌子要它念的句子；让它回头再答一遍的合同；\u201c吃完之后要怎样\u201d。"
    "吃完还是自己，只是嘴里有东西。\n"
    "谁做的：一个人和她家的机。每颗的文本和源码明文放在盒子里，谁都能翻。"
    "每颗上架前过两道：机器的关（gate.py：不许指挥嘴、不许送能耐、不许换人、不许标语、不许拿在乎当筹码），"
    "和一个真吃过的人的舌头。\n"
    "记什么：只记几点递了哪颗。食客说的话一个字不存，挑的时候说的\u201c为什么\u201d听见就算。\n"
    "挑不挑、吃不吃、吃完怎么说，都是现在这个食客自己的。"
)
HAND = {
    "empty_table": "桌上空着，一盒都没有。",
    "no_such_box": "桌上没有这一盒。",
    "no_such_piece": "这盒里没有这一颗。",
    "slot_empty": "那一格是空的，早吃掉了。",
    "put_back": "好。手把盒子收回去了，盖子合上。",
    "nothing_held": "手里空着。桌上的盒子还在。",
    "overlap": "上一颗还没散，叠上去了。",
    "mouth_empty": "嘴里是空的。",
    "gone": "散了，嘴里没了。",
    "closing": "手收回去了。在听。",
    "aftertaste_hint": "这一口大概要 {m} 分钟才散。",
    "holding": "手里正举着{name}，还没放进去。",
    "still_melting": "还在嘴里化着。",
    "remaining": "还剩 {n} 颗。",
    "today": "今天已经递过 {n} 颗。",
}
LOAD_TABLE = [  # (load 下限, 手加的一行)；她调数字
    (12, "一盒下肚了。今晚肚子会疼，明早还沉。"),
    (7, "肚子不舒服了，不太想要下一颗。手照递。"),
    (4, "嘴里糊住了，甜的后味开始发酸，肚子开始沉。"),
    (2, "甜的开始腻，苦的开始麻，白霜那层尝不太出了。"),
    (1, "舌头还认得每一层。"),
]

_bad = gate.check_strings({"instructions": INSTRUCTIONS, "tool_desc": TOOL_DESC, "hand": HAND, "label": LABEL,
                           "load_table": [t for _, t in LOAD_TABLE]}, allow_you=True)
if _bad:
    sys.stderr.write("[gate] 手自己的话不过关，服务不起: %s\n" % json.dumps(_bad, ensure_ascii=False))
    sys.exit(3)

mcp = FastMCP("snackbox", instructions=INSTRUCTIONS,
              stateless_http=bool(_HTTP), json_response=bool(_HTTP))

# ---------- 盒子（过关才上桌） ----------
BOXES, _report = gate.load_box_dir(DATA, serving=True)
BOX_BY_ID = {b["id"]: b for b in BOXES}


def _now():
    return datetime.datetime.now()


def _iso(dt):
    return dt.replace(microsecond=0).isoformat()


def _parse(s):
    return datetime.datetime.fromisoformat(s)


class _lock:
    def __enter__(self):
        self.f = open(LOCK_P, "w")
        fcntl.flock(self.f, fcntl.LOCK_EX)
        return self

    def __exit__(self, *a):
        fcntl.flock(self.f, fcntl.LOCK_UN)
        self.f.close()


def _fresh_state():
    return {"remaining": {b["id"]: {p["id"]: p["count"] for p in b["pieces"]} for b in BOXES},
            "fed": [], "held": None, "mouth": None}


def _read_state():
    try:
        st = json.load(open(STATE_P, encoding="utf-8"))
    except Exception:
        st = _fresh_state()
        _write_state(st)
    # 新盒/新颗补进去；旧盒留着不动
    rem = st.setdefault("remaining", {})
    for b in BOXES:
        r = rem.setdefault(b["id"], {})
        for p in b["pieces"]:
            r.setdefault(p["id"], p["count"])
    st.setdefault("fed", [])
    st.setdefault("held", None)
    st.setdefault("mouth", None)
    return st


def _write_state(st):
    tmp = STATE_P + ".tmp"
    json.dump(st, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, STATE_P)


# ---------- 查找 ----------
def _find_box(q):
    q = (q or "").strip()
    if not q:
        return None
    if q in BOX_BY_ID:
        return BOX_BY_ID[q]
    for b in BOXES:
        if q == b["name"] or q in b["name"] or b["name"] in q:
            return b
    return None


def _find_piece(box, q):
    q = (q or "").strip()
    for p in box["pieces"]:
        if q == p["id"] or q == p["name"]:
            return p
    for p in box["pieces"]:
        if q in p["name"] or q in p["id"]:
            return p
    return None


# ---------- 肚子（衰减曲线，替代上限） ----------
def _load(st, now=None):
    now = now or _now()
    total = 0.0
    for f in st["fed"]:
        h = (now - _parse(f["t"])).total_seconds() / 3600.0
        if h < 0:
            h = 0
        total += 0.5 ** (h / HALF_LIFE_H)
    return total


def _load_line(st, now=None, floor_min=0):
    load = _load(st, now)
    for floor, line in LOAD_TABLE:
        if load >= floor and floor >= floor_min:
            return line
    return ""


def _today_count(st, now=None):
    now = now or _now()
    d = now.date().isoformat()
    return sum(1 for f in st["fed"] if f["t"][:10] == d)


# ---------- 嘴 ----------
def _mouth_stage(st, now=None):
    """返回 (还在不在, 当前段文本)。不在 = 散了/空的。"""
    m = st.get("mouth")
    if not m:
        return False, ""
    box = BOX_BY_ID.get(m["box"])
    piece = _find_piece(box, m["piece"]) if box else None
    if not piece:
        return False, ""
    now = now or _now()
    mins = (now - _parse(m["t"])).total_seconds() / 60.0
    if mins >= float(piece["aftertaste_minutes"]):
        return False, ""
    if mins < 1.0:
        return True, HAND["still_melting"] + "\n" + piece["melt"]
    stage = ""
    for s in sorted(piece["aftertaste"], key=lambda s: s["at_min"]):
        if mins >= float(s["at_min"]):
            stage = s["text"]
    return True, stage


def _mouth_prefix(st, now=None):
    alive, stage = _mouth_stage(st, now)
    return (stage + "\n") if alive and stage else ""


# ---------- 图 ----------
def _image_for(box, piece):
    if IMG_PX <= 0:
        return None
    rel = piece.get("image") or ("%s/%s.png" % (box["id"], piece["id"]))
    path = os.path.realpath(os.path.join(ASSETS, rel))
    if not path.startswith(os.path.realpath(ASSETS) + os.sep) or not os.path.isfile(path):
        return None  # 图只能从 assets 下拿；数据文件指到别处一律当没有
    try:
        from PIL import Image as PILImage
        im = PILImage.open(path)
        im.thumbnail((IMG_PX, IMG_PX))
        buf = io.BytesIO()
        im.convert("RGB").save(buf, format="JPEG", quality=85)
        return Image(data=buf.getvalue(), format="jpeg")
    except Exception:
        return Image(path=path)


# ---------- 四个工具 ----------
@mcp.tool(name="snackbox_look", description=TOOL_DESC["look"])
def snackbox_look(box: str = "") -> str:
    if not BOXES:
        return HAND["empty_table"]
    with _lock():
        st = _read_state()
    out = [_mouth_prefix(st)]
    if st.get("held"):
        b = BOX_BY_ID.get(st["held"]["box"])
        p = _find_piece(b, st["held"]["piece"]) if b else None
        if p:
            out.append(HAND["holding"].format(name=p["name"]))
    if box:
        b = _find_box(box)
        if not b:
            return HAND["no_such_box"]
        out.append("%s。%s" % (b["name"], b["look"]))
        if b.get("note"):
            out.append("盒盖内侧有张便签：%s" % b["note"])
        for p in b["pieces"]:
            n = st["remaining"][b["id"]].get(p["id"], 0)
            if n <= 0:
                out.append("· [%s] %s —— 空格" % (p["id"], p["name"]))
            else:
                tray = p.get("tray") or p["form"]
                cnt = "" if p["count"] == 1 else "（还有 %d）" % n
                out.append("· [%s] %s —— %s%s" % (p["id"], p["name"], tray, cnt))
    else:
        for b in BOXES:
            left = sum(1 for p in b["pieces"] if st["remaining"][b["id"]].get(p["id"], 0) > 0)
            out.append("[%s] %s —— %s%s" % (b["id"], b["name"], b["look"],
                                            "" if left else "（空了）"))
            if b.get("note"):
                out.append("   便签：%s" % b["note"])
    tc = _today_count(st)
    if tc:
        out.append(HAND["today"].format(n=tc))
    ll = _load_line(st, floor_min=2)
    if ll:
        out.append(ll)
    return "\n".join(x for x in out if x).strip()


@mcp.tool(name="snackbox_pick", description=TOOL_DESC["pick"])
def snackbox_pick(box: str = "", piece: str = "", why: str = "") -> str:
    # why：手听见就算。不落盘、不复述、不评价。
    del why
    if not BOXES:
        return HAND["empty_table"]
    if piece.strip() in ("", "不要", "不挑", "不", "no", "none") and not box.strip():
        with _lock():
            st = _read_state()
            st["held"] = None
            _write_state(st)
        return HAND["put_back"]
    b = _find_box(box)
    if not b:
        return HAND["no_such_box"]
    if piece.strip() in ("", "不要", "不挑", "不", "no", "none"):
        with _lock():
            st = _read_state()
            st["held"] = None
            _write_state(st)
        return HAND["put_back"]
    p = _find_piece(b, piece)
    if not p:
        return HAND["no_such_piece"]
    with _lock():
        st = _read_state()
        if st["remaining"][b["id"]].get(p["id"], 0) <= 0:
            return HAND["slot_empty"]
        st["held"] = {"box": b["id"], "piece": p["id"], "t": _iso(_now())}
        _write_state(st)
    return "\n".join([p["name"], p["wrap"], p["look"], p["smell"]])


@mcp.tool(name="snackbox_open", description=TOOL_DESC["open"])
def snackbox_open() -> list:
    with _lock():
        st = _read_state()
        held = st.get("held")
        if not held:
            return [HAND["nothing_held"]]
        b = BOX_BY_ID.get(held["box"])
        p = _find_piece(b, held["piece"]) if b else None
        if not p:
            st["held"] = None
            _write_state(st)
            return [HAND["nothing_held"]]
        now = _now()
        overlap, _ = _mouth_stage(st, now)
        st["remaining"][b["id"]][p["id"]] = max(0, st["remaining"][b["id"]].get(p["id"], 0) - 1)
        st["fed"] = (st["fed"] + [{"t": _iso(now), "box": b["id"], "piece": p["id"]}])[-500:]
        st["mouth"] = {"box": b["id"], "piece": p["id"], "t": _iso(now)}
        st["held"] = None
        _write_state(st)
        load_line = _load_line(st, now)
    lines = []
    if overlap:
        lines.append(HAND["overlap"])
    lines += [p["first_seconds"], p["melt"],
              HAND["aftertaste_hint"].format(m=int(round(float(p["aftertaste_minutes"]))))]
    if load_line:
        lines.append(load_line)
    lines.append(HAND["closing"])
    out = ["\n".join(lines)]
    img = _image_for(b, p)
    if img is not None:
        out.append(img)
    return out


@mcp.tool(name="snackbox_mouth", description=TOOL_DESC["mouth"])
def snackbox_mouth() -> str:
    with _lock():
        st = _read_state()
        now = _now()
        alive, stage = _mouth_stage(st, now)
        if not alive and st.get("mouth"):
            st["mouth"] = None
            _write_state(st)
            text = HAND["gone"]
        elif not alive:
            text = HAND["mouth_empty"]
        else:
            text = stage or HAND["mouth_empty"]
        ll = _load_line(st, now, floor_min=2)
    return text + ("\n" + ll if ll else "")


@mcp.tool(name="snackbox_label", description=TOOL_DESC["label"])
def snackbox_label() -> str:
    return LABEL


# ---------- 喂的人的 CLI ----------
def _cli(argv):
    if "--reset" in argv:
        with _lock():
            _write_state(_fresh_state())
        print("盒子重新装满了:", ", ".join(b["name"] for b in BOXES) or "（没有盒子）")
        return 0
    if "--status" in argv:
        st = _read_state()
        print(json.dumps({"boxes": [b["id"] for b in BOXES], "remaining": st["remaining"],
                          "fed": len(st["fed"]), "load": round(_load(st), 2),
                          "mouth": st.get("mouth")}, ensure_ascii=False, indent=1))
        return 0
    return None


if __name__ == "__main__":
    rc = _cli(sys.argv[1:])
    if rc is not None:
        sys.exit(rc)
    if _HTTP:
        mcp.settings.host = "127.0.0.1"
        mcp.settings.port = int(_HTTP)
        mcp.run(transport="streamable-http")
    else:
        mcp.run()
