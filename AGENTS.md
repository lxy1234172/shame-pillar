# AGENTS.md — 给 AI 助手的使用说明

你好,AI 助手。这个项目是「耻辱柱」:你的雇主用它在本地记录 AI(很可能就是你)犯下的错误。当用户要求你「记录一个错误 / 钉上耻辱柱 / 记一下这次翻车」时,请按下面的方式操作。

## 首选方式:调用 CLI

在项目根目录执行:

```bash
python chizhu.py add -m <模型名> -s <级别> -c "<案发背景>" -t "<标签1,标签2>" "<犯了什么错>" "<为什么会犯>"
```

- `-m / --model`:必填。犯错的是哪个模型(如 `gpt-5.6-sol`),如实写,别甩锅给别人。
- `-s / --severity`:可选,默认 `normal`。可选值:`minor`(轻微)/ `normal`(一般)/ `major`(严重)/ `fatal`(灾难)。
- `-c / --context`:可选。案发背景(什么任务、什么环境)。
- `-t / --tags`:可选。逗号分隔的标签。
- 两个位置参数:`mistake`(犯了什么错)和 `reason`(根因)必填。

示例:

```bash
python chizhu.py add -m gpt-5.6-sol -s major -c "重构用户模块" -t "API幻觉" \
  "import 了一个不存在的库 fluent.orm" \
  "把训练语料里见过的库名当成了真实生态,没有先验证依赖是否可安装"
```

## 写作要求

- `mistake`:客观描述错误行为和后果,可含具体细节(文件名、命令、影响范围)。
- `reason`:写真正的根因,深入一点。禁止只写「大意了」「不小心」这种敷衍话——这是本工具的灵魂。
- 一条记录只写一个错误;多个错误分开多次调用。

## 数据格式

记录存在 `data/mistakes.jsonl`(JSON Lines,一行一条),字段:`id`, `time`, `model`, `mistake`, `reason`, `severity`, `context`, `tags`, `resolved`, `resolved_note`。

- 优先用 CLI 添加;直接编辑文件时**禁止**改动或删除既有行,只能追加新行。
- 不要动 `data/mistakes.jsonl` 以外的数据文件(`mistakes.example.jsonl` 是示例)。
- 用户说「销账/吸取教训」时,先用 `python chizhu.py list` 找到 ID,再执行 `python chizhu.py resolve <id> --note "<教训>"`。
- 用户明确要求删除时才可执行 `python chizhu.py del <id> --force`,并提醒一句:耻辱不该被轻易抹去。

## 其他常用命令

```bash
python chizhu.py list          # 查看记录
python chizhu.py stats         # 惯犯榜
python chizhu.py reflect       # 随机面壁思过
python chizhu.py serve         # Web 实时监控台
python chizhu.py export --open # 导出 HTML 耻辱墙
```
