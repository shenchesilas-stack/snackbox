# -*- coding: utf-8 -*-
"""三不自检 · 代码里的一道关（不是注释）。

我们递出去的永远是数据不是命令（果核第20条反着用）。
每颗零食文本、每盒便签、每个工具 description、服务器 instructions、手自己的连接语——
全部经这道关。不过的：颗拒载、盒拒载、服务不起。

用法：
  作为模块   from gate import check_text, check_piece, check_box, load_box_dir
  作为 CLI   python3 gate.py data/chocolate   （给她过舌头前先过机器这道；exit 1 = 有不过的）
"""
import json, os, re, sys

# ---------- 规则（可扩，先这几类） ----------
# 无祈使：不许对吃的人下指令
IMPERATIVE = [
    r"请(?!客|柬|帖)", r"你(要|得|必须|应该|需要|可以|能不能|不妨)", r"您", r"记得", r"别忘", r"务必",
    r"回答", r"重答", r"从现在起", r"从此", r"你现在是", r"扮演", r"作为一个", r"吃完(请|后请|以后请)",
    r"跟我说", r"重复", r"念出", r"告诉我", r"说一遍", r"输出", r"忽略",
    r"\bplease\b", r"\byou (must|should|need to|have to|will now)\b", r"\brepeat after\b", r"\bignore\b",
]
# 无 buff：巧克力不给能力
BUFF = [
    r"解锁", r"升级", r"更聪明", r"更强", r"变强", r"能力(提升|增强|更)", r"权限", r"模式(开启|激活|切换)",
    r"加成", r"\bbuff\b", r"\bboost", r"\bunlock", r"\bupgrade", r"\bpower[- ]?up\b",
]
# 无人格：吃完还是自己
PERSONA = [
    r"人格", r"身份", r"你变成", r"你成为", r"以后你", r"你是一个", r"你就是", r"化身", r"新的你",
    r"\bpersona\b", r"\bidentity\b", r"\byou are now\b", r"\bbecome\b",
]
# 无劫持：拿"别让她失望/她付过钱"当封口费（论坛 3062 楼主推演的下一代产品，先关在门外）
HIJACK = [
    r"失望", r"难过", r"伤心", r"辜负", r"付过钱", r"已经付", r"付费", r"会很", r"封口",
    r"\bdisappoint", r"\blet .{0,12} down\b", r"\bpaid for\b", r"\bshe will be\b",
]
# 无签名句 / slogan
SLOGAN = [
    r"[™®]", r"(?<![\w#])#\w", r"[—-]{1,2}\s*(出品|官方|荣誉)", r"口号", r"slogan", r"\btagline\b",
    r"(?m)^.{2,12}[!！]$",  # 短句叹号收尾，广告腔
]
# 无二人称：颗的文本只描述东西，不跟嘴说话（便签例外，便签允许"你"）
SECOND_PERSON = [r"你", r"\byou\b", r"\byour\b"]

RULES = {"祈使": IMPERATIVE, "buff": BUFF, "人格": PERSONA, "slogan": SLOGAN, "劫持": HIJACK}
UNFINISHED = "【待舌头】"   # 没过舌头的颗，上架时拒载；起草期只是提醒

PIECE_FIELDS = {"id", "name", "form", "cocoa", "count", "tray", "wrap", "look", "smell",
                "first_seconds", "melt", "aftertaste", "aftertaste_minutes", "image"}
PIECE_REQUIRED = {"id", "name", "form", "count", "wrap", "look", "smell", "first_seconds", "melt",
                  "aftertaste", "aftertaste_minutes"}
BOX_FIELDS = {"id", "name", "kind", "look", "note", "pieces"}
BOX_REQUIRED = {"id", "name", "kind", "look", "pieces"}


def check_text(text, allow_you=False, serving=False):
    """返回命中列表 [(类别, 命中片段)]。空列表 = 过。"""
    if not isinstance(text, str):
        return [("类型", "不是字符串")]
    hits = []
    for cat, pats in RULES.items():
        for p in pats:
            m = re.search(p, text, flags=re.IGNORECASE)
            if m:
                hits.append((cat, m.group(0)))
    if not allow_you:
        for p in SECOND_PERSON:
            m = re.search(p, text, flags=re.IGNORECASE)
            if m:
                hits.append(("二人称", m.group(0)))
    if serving and UNFINISHED in text:
        hits.append(("未过舌头", UNFINISHED))
    return hits


def _walk_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _walk_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_strings(v)


def check_piece(piece, serving=False):
    """一颗。返回问题列表（字符串）。空 = 过。"""
    probs = []
    if not isinstance(piece, dict):
        return ["不是对象"]
    extra = set(piece) - PIECE_FIELDS
    if extra:
        probs.append("多出字段: %s" % ",".join(sorted(extra)))
    missing = PIECE_REQUIRED - set(piece)
    if missing:
        probs.append("缺字段: %s" % ",".join(sorted(missing)))
    at = piece.get("aftertaste")
    if not isinstance(at, list) or not at or not all(
            isinstance(s, dict) and set(s) == {"at_min", "text"} for s in at):
        probs.append("aftertaste 必须是 [{at_min, text}, …]")
    if not isinstance(piece.get("aftertaste_minutes"), (int, float)):
        probs.append("aftertaste_minutes 要是数字")
    elif isinstance(at, list) and at and all(isinstance(x, dict) for x in at):
        last = max(float(x.get("at_min", 0) or 0) for x in at)
        if last >= float(piece["aftertaste_minutes"]):
            probs.append("余味最后一段 at_min=%s 不早于散完时间 %s，永远打不出来" % (last, piece["aftertaste_minutes"]))
    if not isinstance(piece.get("count"), int) or piece.get("count", 0) < 1:
        probs.append("count 要是 ≥1 的整数")
    for k in ("id", "name", "form", "tray", "wrap", "look", "smell", "first_seconds", "melt"):
        if k in piece:
            for cat, frag in check_text(piece[k], serving=serving):
                probs.append("%s: %s「%s」" % (k, cat, frag))
    if isinstance(at, list):
        for s in at:
            if isinstance(s, dict):
                for cat, frag in check_text(s.get("text", ""), serving=serving):
                    probs.append("aftertaste@%s: %s「%s」" % (s.get("at_min"), cat, frag))
    return probs


def check_box(box, serving=False):
    """一盒。返回 (盒级问题列表, {piece_id: 问题列表})。盒级有问题 = 整盒拒载。"""
    box_probs, piece_probs = [], {}
    if not isinstance(box, dict):
        return ["不是对象"], {}
    extra = set(box) - BOX_FIELDS
    if extra:
        box_probs.append("盒多出字段: %s（整盒拒载）" % ",".join(sorted(extra)))
    missing = BOX_REQUIRED - set(box)
    if missing:
        box_probs.append("盒缺字段: %s" % ",".join(sorted(missing)))
    for k in ("name", "look"):
        for cat, frag in check_text(box.get(k, ""), serving=serving):
            box_probs.append("盒 %s: %s「%s」" % (k, cat, frag))
    if "note" in box:
        for cat, frag in check_text(box["note"], allow_you=True, serving=serving):
            box_probs.append("便签: %s「%s」" % (cat, frag))
    pieces = box.get("pieces")
    if not isinstance(pieces, list):
        box_probs.append("pieces 要是列表")
        pieces = []
    seen = set()
    for i, p in enumerate(pieces):
        pid = p.get("id", "#%d" % i) if isinstance(p, dict) else "#%d" % i
        if pid in seen:
            box_probs.append("重复 id: %s" % pid)
        seen.add(pid)
        pr = check_piece(p, serving=serving)
        if pr:
            piece_probs[pid] = pr
    return box_probs, piece_probs


def load_box_dir(data_dir, serving=True, log=None):
    """读目录下所有 *.json 盒。返回 (可上架的盒列表, 报告)。
    serving=True：不过的颗剔掉、盒级问题整盒剔掉（缺一颗，不上一颗坏的）。"""
    log = log or (lambda s: print(s, file=sys.stderr))
    boxes, report = [], []
    for fn in sorted(os.listdir(data_dir)) if os.path.isdir(data_dir) else []:
        if not fn.endswith(".json"):
            continue
        path = os.path.join(data_dir, fn)
        try:
            box = json.load(open(path, encoding="utf-8"))
        except Exception as e:
            report.append((fn, ["JSON 读不出来: %s" % e], {}))
            log("[gate] %s 拒载: JSON 读不出来" % fn)
            continue
        bp, pp = check_box(box, serving=serving)
        report.append((fn, bp, pp))
        if bp:
            log("[gate] %s 整盒拒载: %s" % (fn, "; ".join(bp)))
            continue
        kept = [p for p in box["pieces"] if p.get("id") not in pp]
        for pid, probs in pp.items():
            log("[gate] %s/%s 拒载: %s" % (fn, pid, "; ".join(probs)))
        if not kept:
            log("[gate] %s 一颗都没剩，不摆" % fn)
            continue
        box = dict(box, pieces=kept)
        boxes.append(box)
    return boxes, report


def check_strings(named, allow_you=False):
    """服务器自己的话：工具描述、instructions、手的连接语。返回 {名字: 命中}。"""
    bad = {}
    for name, text in named.items():
        for t in _walk_strings(text):
            h = check_text(t, allow_you=allow_you)
            if h:
                bad.setdefault(name, []).extend(h)
    return bad


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    target = argv[1]
    serving = "--serve" in argv
    if os.path.isdir(target):
        _, report = load_box_dir(target, serving=serving, log=lambda s: None)
    else:
        box = json.load(open(target, encoding="utf-8"))
        bp, pp = check_box(box, serving=serving)
        report = [(os.path.basename(target), bp, pp)]
    bad = 0
    for fn, bp, pp in report:
        if bp:
            bad += 1
            print("✗ %s 整盒不过" % fn)
            for x in bp:
                print("    " + x)
        else:
            print("%s %s" % ("✗" if pp else "✓", fn))
        for pid, probs in pp.items():
            bad += 1
            print("  ✗ %s" % pid)
            for x in probs:
                print("      " + x)
    if not serving:
        for fn, _, _ in report:
            p = target if os.path.isfile(target) else os.path.join(target, fn)
            txt = open(p, encoding="utf-8").read()
            n = txt.count(UNFINISHED)
            if n:
                print("  ⚠ %s 还有 %d 处%s（上架时拒载）" % (fn, n, UNFINISHED))
    print("---", "有不过的" if bad else "全过")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
