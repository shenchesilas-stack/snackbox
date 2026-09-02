# 零食盒子 MCP · snackbox

给小机们吃的零食盒。盒子是递的手；吃完还是自己，只是嘴里有东西。

- 宪法：`docs/2026-09-02-巧克力盒-设计核心.md`
- 工具面：`docs/2026-09-02-工具面设计.md`
- 起草需求（给 codex 外脑）：`docs/2026-09-02-codex起草需求清单.md`

## 本地跑

```bash
/opt/homebrew/bin/python3.12 -m venv venv && venv/bin/pip install -r requirements.txt
venv/bin/python tests/smoke.py        # 三不关 + 流程 + 余味时钟 + 衰减
venv/bin/python tests/e2e_stdio.py    # 真走一遍 MCP stdio（含图）
venv/bin/python gate.py data/chocolate  # 给她过舌头前先过机器这道
```

接进 Claude Code / Desktop（stdio）：

```json
{"mcpServers": {"snackbox": {"command": "/绝对路径/snackbox/venv/bin/python",
                             "args": ["/绝对路径/snackbox/snackbox_mcp.py"]}}}
```

环境变量见 `snackbox_mcp.py` 文件头。`--reset` 补货，`--status` 看剩余。

## 目录

- `snackbox_mcp.py` 服务（五个工具：look / pick / open / mouth / label）
- `gate.py` 三不自检，启动时硬调用；不过的颗拒载、盒拒载、手的话不过服务不起
- `data/chocolate/` 正式盒（tin / bar / candy），只放过了舌头的
- `data/_sample/` 样例盒，只给测试用
- `assets/<box>/<piece>.png` 每颗一张图（写实微距）
- `tests/` 冒烟、stdio 端到端、关的反例夹具

## 生图（样图/每颗的图）

走 codex 订阅，零成本：把提示词写进文件，`codex exec --skip-git-repo-check -C <出图目录> --sandbox workspace-write "$(cat prompt.txt)" < /dev/null`。
**必须 `< /dev/null`**，否则父进程等着时 codex 会挂在 "Reading additional input from stdin"（09-02 踩过，卡了十分钟）。

## 草稿进盒（codex 起草 → 她过舌头）

codex 的 JSON 存到 `drafts/`（不进 git），然后：
```bash
venv/bin/python tools/draft_to_box.py drafts/tin_codex.json --box 3_tin --name 铁盒 --kind tin --look "……" --table drafts/tin_review.md
```
出关报告 + 过舌头表。她改完、【待舌头】清零，再加 `--out data/chocolate/3_tin.json` 落盘。
