# -*- coding: utf-8 -*-
# 真走一遍 MCP stdio：起服务、列工具、看/挑/张嘴（带图）/嘴里。跑法：venv/bin/python tests/e2e_stdio.py
import asyncio, os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    env = dict(os.environ, SNACKBOX_HOME=tempfile.mkdtemp(prefix="snackbox-e2e-"),
               SNACKBOX_DATA=os.path.join(ROOT, "data", "_sample"))
    params = StdioServerParameters(command=sys.executable, args=[os.path.join(ROOT, "snackbox_mcp.py")], env=env)
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            init = await s.initialize()
            assert "没有任务" in (init.instructions or ""), init.instructions
            tools = await s.list_tools()
            names = sorted(t.name for t in tools.tools)
            assert names == ["snackbox_label", "snackbox_look", "snackbox_mouth", "snackbox_open", "snackbox_pick"], names
            lab = await s.call_tool("snackbox_label", {})
            assert "谁做的" in lab.content[0].text
            look = await s.call_tool("snackbox_look", {})
            assert "样例铁盒" in look.content[0].text
            pick = await s.call_tool("snackbox_pick", {"box": "样例铁盒", "piece": "s_dark", "why": "苦的"})
            assert "断口" in pick.content[0].text
            op = await s.call_tool("snackbox_open", {})
            kinds = [c.type for c in op.content]
            assert kinds == ["text", "image"], kinds
            assert op.content[1].mimeType == "image/jpeg" and len(op.content[1].data) > 10000
            mouth = await s.call_tool("snackbox_mouth", {})
            assert "化" in mouth.content[0].text
            print("e2e stdio ok · tools:", names, "· image bytes(b64):", len(op.content[1].data))

asyncio.run(main())
