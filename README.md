中文 | [English](README_EN.md)

# 耻辱柱 · chiruzhu

> 每一行错误,都值得被钉在柱上。

AI 编程助手越用越多,它们犯的错也越来越多:幻觉出压根不存在的库、把 `.*` 「优化」成 `.*?` 搞挂生产日志、把你说的「随便改改」理解成推翻重写……

**耻辱柱**是一个零依赖的单文件 Python CLI,专门用来记录这些黑历史:哪个模型、什么时间、犯了什么错、根因是什么,一条不少。支持终端表格、惯犯榜统计、随机面壁思过,还自带一个实时 Web 监控台和可分享的 HTML 耻辱墙。

## 演示

实时监控台(`python chiruzhu.py serve`):

![实时监控台](docs/web_demo.png)

## 功能

- 📌 **钉错误** —— 记录模型、错误、根因、级别(轻微/一般/严重/灾难)、背景、标签
- 📋 **查看记录** —— 终端宽表自适应,支持按模型/级别过滤
- ✅ **销账** —— 吸取教训后标记 resolved,可附教训备注
- 📊 **惯犯榜** —— 按模型和级别统计,ASCII 条形图直观看谁最惯犯
- 🧘 **面壁思过** —— 从未销账记录中随机抽一条出来反省
- 🖥️ **实时监控台** —— 内置 Web 服务,网页上钉错误/编辑/销账,8 秒自动刷新
- 🧱 **耻辱墙** —— 导出单文件 HTML,可以直接发给朋友或挂到静态托管上
- 🚫 **防手贱** —— 删除记录必须加 `--force`,毕竟「耻辱不该被轻易抹去」

零第三方依赖,Python 3.9+ 即可运行,Windows / macOS / Linux 通吃。

## 快速开始

```bash
# 钉一条错误
python chiruzhu.py add -m gpt-5.6-sol -s fatal -t "正则,生产事故" \
  "把 .* 改成 .*? 导致日志解析漏了一半数据" \
  "只看了匹配结果没看边界条件,非贪婪匹配在多行日志上行为完全不同"

# 查看柱上记录
python chiruzhu.py list

# 惯犯榜
python chiruzhu.py stats

# 随机抽一条面壁思过
python chiruzhu.py reflect

# 吸取教训,销账
python chiruzhu.py resolve <id> --note "先查再说,不知道就承认不知道"

# 打开 Web 实时监控台
python chiruzhu.py serve

# 导出 HTML 耻辱墙
python chiruzhu.py export --open
```

Windows 下可以直接用包装脚本:

```bat
chiruzhu add -m gemini-3.5-pro -s minor "import 了三个不存在的库" "幻觉出一整套不存在的开源生态"
```

> 💡 **让 AI 自己记账**:把 [`AGENTS.md`](AGENTS.md) 丢给你的 AI 编程助手(或直接放在项目根目录,多数工具会自动读取),它就知道怎么规范地往柱上钉错误了——你说一句「记一下这次翻车」即可。

## 数据

记录存在 `data/mistakes.jsonl`(JSON Lines,每行一条),默认不入库,你的黑历史只属于你自己。想换位置可以用 `--data` 参数或环境变量 `CHIZHU_DATA`。

虚构示例数据见 [`data/mistakes.example.jsonl`](data/mistakes.example.jsonl)。

## License

MIT
