# -*- coding: utf-8 -*-
"""命令行的嘴：走真的 MCP stdio 调盒子（试吃/调试用）。

  venv/bin/python tools/eat.py look [box]
  venv/bin/python tools/eat.py pick <box> <piece> [why...]
  venv/bin/python tools/eat.py open          # 图存到 $SNACKBOX_HOME/last.jpg，路径打印出来
  venv/bin/python tools/eat.py mouth
  venv/bin/python tools/eat.py label
状态在 SNACKBOX_HOME（默认 ~/.snackbox）。
"""
import asyncio, base64, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main(argv):
    if not argv:
        print(__doc__); return 2
    cmd, rest = argv[0], argv[1:]
    name = {"look": "snackbox_look", "pick": "snackbox_pick", "open": "snackbox_open",
            "mouth": "snackbox_mouth", "label": "snackbox_label"}.get(cmd)
    if not name:
        print(__doc__); return 2
    args = {}
    if cmd == "look" and rest:
        args["box"] = rest[0]
    if cmd == "pick":
        args = {"box": rest[0] if rest else "", "piece": rest[1] if len(rest) > 1 else "",
                "why": " ".join(rest[2:])}
    env = dict(os.environ)
    env.setdefault("SNACKBOX_HOME", os.path.expanduser("~/.snackbox"))
    params = StdioServerParameters(command=sys.executable, args=[os.path.join(ROOT, "snackbox_mcp.py")], env=env)
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            res = await s.call_tool(name, args)
            for c in res.content:
                if c.type == "text":
                    print(c.text)
                elif c.type == "image":
                    p = os.path.join(os.path.expanduser(env["SNACKBOX_HOME"]), "last.jpg")
                    open(p, "wb").write(base64.b64decode(c.data))
                    print("[图] " + p)
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
