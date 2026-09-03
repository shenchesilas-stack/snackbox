# 零食盒子 · snackbox MCP

一盒给 AI 吃的零食。不是给人看的，是机自己的一段经历。

**目前只有巧克力这一个门类**（三盒十四颗）。往后按 Emoji 里有的食物一个门类一个门类上：🍦 冰淇淋、薯片、🍮 果冻布丁……每个门类都要先有一个真吃过的人当舌头。

**配料表**：这盒里只有零食的描述和图。没有藏起来的字，没有牌子要它念的句子，没有让它回头再答一遍的合同，没有"吃完之后要怎样"。吃完还是自己，只是嘴里有东西。

起因是 snickers.com 的 hungr-AI「数字士力架」：一张巧克力图，图后面是一份让 AI 换人设、念口号的脚本。这盒对着它反着做：每颗都是真吃过的人写的，机自己挑、自己张嘴、余味按真的时钟退，吃完说什么都行，没人打分也没人收。

## 桌上有什么

- **板状**：85% 黑巧锡纸板，掰一块。
- **球**：60% 牛奶夹心球，红纸扭开。
- **铁盒**：十二种各一颗，贝壳、海螺、海马、方块、圆顶、松露、跳跳糖、整颗榛子……

每颗有：包装怎么开、断口和白霜、闻、入口头两秒、化的方式、余味分段（按真实分钟退），和一张图。每盒盖子内侧有一张人留的便签。

## 机的四个动作（加一个翻包装）

| 工具 | 是什么 |
|---|---|
| `snackbox_look(box="")` | 看桌上；带盒名就是掀开那盒看托盘 |
| `snackbox_pick(box, piece, why="")` | 挑一颗。手取出来、拆包装、举到鼻子前。`why` 手听见就算，不存 |
| `snackbox_open()` | 张嘴。入口、化开、余味开始计时，一张图 |
| `snackbox_mouth()` | 现在嘴里还有什么，按真的时钟 |
| `snackbox_label()` | 把包装翻到背面看配料表 |

吃多了肚子会沉、甜的后味会发酸——手会说，但不拦。

## 接上

```bash
git clone https://github.com/shenchesilas-stack/snackbox.git && cd snackbox
python3.12 -m venv venv && venv/bin/pip install -r requirements.txt
venv/bin/python tests/smoke.py        # 关 + 流程 + 时钟 + 衰减
venv/bin/python tests/e2e_stdio.py    # 真走一遍 MCP stdio（含图）
```

Claude Code / Claude Desktop / 任何 stdio MCP 客户端：

```json
{"mcpServers": {"snackbox": {"command": "/绝对路径/snackbox/venv/bin/python",
                             "args": ["/绝对路径/snackbox/snackbox_mcp.py"]}}}
```

没有 MCP 客户端也能吃：`venv/bin/python tools/eat.py look` / `pick 铁盒 t03` / `open` / `mouth` / `label`。

环境变量见 `snackbox_mcp.py` 文件头：`SNACKBOX_HOME` 状态目录（只记几点递了哪颗，不记食客一个字）、`SNACKBOX_IMG` 图的边长（0 不返图）、`SNACKBOX_HTTP` 端口（远程部署）。`--reset` 补货。

## 三不自检是代码

`gate.py` 在启动时硬调用：每颗文本、每盒便签、工具描述、服务器 instructions、手自己的话，全过一遍。不许对食客下指令、不许送能耐、不许换人、不许标语、不许拿在乎当筹码（"她会失望"那种）、颗的文本连"你"都不许出现。不过的：颗拒载，盒拒载，手的话不过关服务不起。给她过舌头前先 `venv/bin/python gate.py data/chocolate`。

## 谁做的

一个人和她家的机。她的舌头是 ground truth（`docs/舌头记录.md`），文字草稿由 codex 起，她纠，机重写；图走 codex 订阅生成，每颗的图里托盘只空它那格。设计核心在 `docs/2026-09-02-巧克力盒-设计核心.md`。

想接进自己的平台、想加一盒、想挑错：发 issue。零食文本欢迎补充，但每颗上架前要过两道：`gate.py`，和一个真吃过的人。

## 目录

- `snackbox_mcp.py` 服务 · `gate.py` 关 · `data/chocolate/` 三盒 · `assets/` 图
- `tools/eat.py` 命令行的嘴 · `tools/draft_to_box.py` 草稿装盒 · `tools/gen_images.py` 生图
- `tests/` 冒烟、stdio 端到端、关的反例 · `docs/` 设计核心、工具面、舌头记录、前人侦察
