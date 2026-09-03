# -*- coding: utf-8 -*-
"""每颗一张图：从 data/chocolate/*.json 生成提示词，交给 codex 订阅生图（零成本）。

用法：venv/bin/python tools/gen_images.py 3_tin [--only t01,t02] [--dry]
  → assets/<box>/<id>.png   （已存在的跳过；--force 重生）
画风锁定见 docs/2026-09-02-codex起草需求清单.md 附录（她 09-02 过的第三轮）。
"""
import argparse, json, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STYLE = ("mouth-watering editorial food photography, rich, warm, slightly moody. Golden late-afternoon "
         "window light raking from the side, strong specular highlights on glossy tempered chocolate, deep soft "
         "shadows, high micro-contrast. Surface: dark walnut wood table, a little worn. Camera pulled back so the "
         "subject occupies roughly a third of the frame, 50mm feel, shallow depth of field with creamy bokeh. "
         "Warm chocolate browns glowing, never grey or dull. No hands, no text, no letters, no logos, no brand "
         "marks, no props like cups, leaves or flowers. The chocolate must NOT ooze or run: fillings are soft "
         "and glossy but hold their shape; a bar square only just softens at one corner.")

SCENE = {
    "bag": "First-person point of view, eyes looking DOWN into a bag held just below the chin. The bag is the cheap thin FLAT "
           "kraft paper bag used by Chinese street chestnut stalls: very lightweight 70-gram brown kraft, a flat two-layer sack "
           "with NO side gussets and NO flat base, a pointed V-shaped bottom, floppy and limp, only bulging where the chestnuts "
           "sit at the bottom, slightly translucent with faint grease spots, plain, no printing; the top edge folded over once "
           "and pinched shut, the mouth a narrow slit pushed open just enough to look in. A hand in a knitted wool glove pinches "
           "that folded top edge between thumb and forefinger because the bag is hot. Down inside: glossy dark mahogany roasted "
           "chestnuts, several split open along a cut, a pale fuzzy patch at each base, a few sugar-glazed shiny spots; NO peeled "
           "nut. White steam drifting up out of the slit toward the viewer. Around the bag: an evening street blurred beyond "
           "recognition, only soft warm bokeh and vague shapes, no readable objects. Details: ",    "chips": "A foil chip bag torn open across the top, the tear ragged and off to one side, the bag slumped and half-deflated, "
             "lying on the wood with a small heap of potato chips spilled out of the mouth; a few chips scattered closer to the camera, "
             "one broken. The bag is plain and unprinted (a solid color, no logo, no text). Salt crystals and oil sheen visible on the "
             "chips; a few crumbs on the wood. Details: ",
    "bar": "An 85% dark chocolate bar, thin and wide, divided into small rectangles, its paper sleeve (printed with a "
           "simple illustration of cocoa beans and a cocoa plant, NO letters or numbers) pulled halfway off the short end and the thin SILVER foil (not gold) folded back with crinkles catching the light. One rectangle has "
           "been snapped off and lies beside the bar, snap edge toward the camera showing a fine dense grain, "
           "near-black brown with a restrained sheen and a faint grey fat bloom on the broken edge. A few crumbs.",
    "ball": "A small open paper bag of milk chocolate soft-centre balls, each in plain unprinted red foil twisted at "
            "both ends, a few spilled onto the wood. In front, one red foil twisted open and unfurled with the "
            "unwrapped glossy ball on it, and beside it one ball broken in half showing a thin crisp shell and a "
            "slightly paler, soft, glossy centre that holds its shape.",
    "tin": "An open square tin of assorted chocolates, lid off, translucent tissue paper lifted back, a twelve-cell "
           "tray in which every piece is different: {tray_list}. Exactly ONE cell is empty: the cell of THIS piece. "
           "In front of the tin on the wood: THIS piece, taken out and broken in half, break edge toward the camera: "
           "{this}. The piece is broken into TWO halves of ONE piece: the two cut faces are the two sides of the same break and would fit back together (complementary, not mirrored copies); one half may show the cut face and the other its outside. If the piece is described as dark chocolate, its shell must be dark near-black brown, not milk; if salt crystals are described, coarse white salt grains must be visible on top.",
}


def build(box, piece, all_pieces):
    kind = box["kind"]
    if box.get("category") == "chips":
        kind = "chips"
    if kind == "bag":
        style = STYLE.replace("No hands, ", "").replace("Surface: dark walnut wood table, a little worn. ", "").replace(
            "Camera pulled back so the subject occupies roughly a third of the frame, ", "Close shot from above, the bag mouth fills most of the frame, ")
        return "%s\n\nSubject: %s%s" % (style, SCENE["bag"], piece["look"])
    if kind == "tin":
        others = [p["tray"] for p in all_pieces if p["id"] != piece["id"]]
        scene = SCENE["tin"].format(
            tray_list="; ".join(others),
            this="%s. Shape and surface: %s. Inside after breaking: %s" % (piece["name"], piece["tray"], piece["look"]))
    else:
        scene = SCENE.get(kind, SCENE["bar"]) + (" Details: " if kind != "bag" else "") + piece["look"]
    return "%s\n\nSubject: %s" % (STYLE, scene)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("box")
    ap.add_argument("--only", default="")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    cat, _, bid = a.box.partition("/") if "/" in a.box else ("chocolate", "/", a.box)   # 用法：gen_images.py chestnut/1_bag
    box = json.load(open(os.path.join(ROOT, "data", cat, bid + ".json"), encoding="utf-8"))
    box["category"] = cat
    out_dir = os.path.join(ROOT, "assets", cat, box["id"])
    os.makedirs(out_dir, exist_ok=True)
    only = set(x for x in a.only.split(",") if x)
    jobs = []
    for p in box["pieces"]:
        if only and p["id"] not in only:
            continue
        dst = os.path.join(out_dir, p["id"] + ".png")
        if os.path.exists(dst) and not a.force:
            continue
        jobs.append((p, dst))
    if not jobs:
        print("nothing to do"); return 0
    parts = ["Use your built-in image_gen tool (subscription path, do NOT use the CLI/API fallback, do NOT ask for "
             "OPENAI_API_KEY). Generate %d separate 1024x1024 images, one per numbered item below, and copy each "
             "final PNG to the exact absolute path given. Do not write any other files. Generate them one at a time; "
             "for items 2 onward, keep the same tin, wood, light and tray so the set looks like one box. Some piece "
             "descriptions below are in Chinese: translate them into precise English inside the image prompt you send." % len(jobs)]
    for i, (p, dst) in enumerate(jobs, 1):
        parts.append("\n### Item %d → save as: %s\n%s" % (i, dst, build(box, p, box["pieces"])))
    parts.append("\nWhen done, print the absolute paths of all saved files.")
    prompt = "\n".join(parts)
    work = os.path.join(ROOT, "drafts", "imggen_" + cat + "_" + box["id"])
    os.makedirs(work, exist_ok=True)
    open(os.path.join(work, "prompt.txt"), "w", encoding="utf-8").write(prompt)
    print("%d jobs · prompt → %s/prompt.txt" % (len(jobs), work))
    if a.dry:
        return 0
    log = open(os.path.join(work, "run.log"), "w")
    rc = subprocess.call(["codex", "exec", "--skip-git-repo-check", "-C", ROOT, "--sandbox", "workspace-write", prompt],
                         stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
    log.write("\nEXIT %d\n" % rc); log.close()
    done = [p["id"] for p, dst in jobs if os.path.exists(dst)]
    print("exit", rc, "· got", len(done), "/", len(jobs), done)
    return rc


if __name__ == "__main__":
    sys.exit(main())
