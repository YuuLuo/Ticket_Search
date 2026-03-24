# Ticket Search — 多段机票路线可行性搜索工具

自动化搜索多段航线的舱位可用性，通过浏览器拦截 [ExpertFlyer](https://www.expertflyer.com) 的 API 响应，提取指定舱位的可用航班，并使用剪枝算法从海量组合中找出所有满足转机时间限制的可行行程方案。

## 功能特点

- **浏览器自动捕获** — 启动 Chromium 浏览器，用户手动登录 ExpertFlyer 搜索航班，脚本自动拦截网络响应并提取数据
- **多舱位筛选** — 支持同时筛选多个舱位（如 `YEV`），所有指定舱位均有余票才会被选入
- **智能剪枝** — 使用弧一致性（Arc Consistency）算法 + DFS 搜索，从万亿级组合中高效筛选可行方案
- **转机时间限制** — 可配置最短（默认 45 分钟）和最长（默认 24 小时）转机时间
- **正序/倒序搜索** — 支持从第一段开始或从最后一段开始录入航班数据
- **经停详情** — 显示中转航班的经停机场、等待时间等详细信息
- **结果保存** — 可行方案自动保存到 `results/` 目录

## 项目结构

```
Ticket_Search/
  main.py                    # 入口
  requirements.txt           # 依赖
  ticket_search/
    __init__.py
    config.py                # 路线、舱位、转机限制等常量配置
    models.py                # 工具函数
    parser.py                # ExpertFlyer API JSON 解析
    solver.py                # 弧一致性剪枝 + DFS 搜索
    display.py               # 表格与行程格式化输出
    browser.py               # Playwright 浏览器管理 + 响应拦截
    cli.py                   # 主交互流程
```

## 安装

```bash
# 克隆仓库
git clone https://github.com/YuuLuo/Ticket_Search.git
cd Ticket_Search

# 安装依赖
pip install -r requirements.txt

# 安装 Chromium 浏览器（Playwright 需要）
python -m playwright install chromium
```

## 配置

编辑 `ticket_search/config.py`：

```python
DEFAULT_YEAR = 2026
TARGET_CLASSES = "V"          # 筛选舱位，如 "V" 或 "YEV"
MAX_RESULTS = 5000

ROUTE = [                     # 多段路线，按顺序列出所有经停城市
    "LAX", "SEA", "ANC", "MSP", "GRR",
    "DTW", "CVG", "DCA", "LGA", "SYR", "JFK", "BOS",
    "DXB"
]

MIN_LAYOVER = timedelta(minutes=45)   # 最短转机时间
MAX_LAYOVER = timedelta(hours=24)     # 最长转机时间
```

## 使用

```bash
python main.py
```

启动后流程：

1. 选择搜索顺序（正序 `f` / 倒序 `r`）
2. 浏览器自动打开，手动登录 ExpertFlyer
3. 按提示依次在浏览器中搜索每段航线，脚本自动捕获结果
4. 选择要添加的航班（全部 / 指定编号 / 不添加）
5. 所有段录入完成后，自动剪枝搜索可行方案
6. 结果输出到终端并保存至 `results/` 目录

## 输出示例

```
  段    航段       出发           到达          转机     航班               V
  ---- ---------- -------------- -------------- -------- -------------------- -
   1    LAX→SEA   06-07 07:10    06-07 10:03             DL2980              V9
   2    SEA→ANC   06-07 17:30    06-07 20:07    7h27m    DL931               V9
   3    ANC→MSP   06-08 06:00    06-08 14:24    9h53m    DL447               V9
  ...

  总转机等待: 48h30m
  总行程时长: 120h15m
  行程日期:   06-07 → 06-12
  最低余票:   V3
```

## 依赖

- Python 3.12+
- [Playwright](https://playwright.dev/python/) — 浏览器自动化

## 注意事项

- 需要有效的 ExpertFlyer 账号
- 浏览器登录状态保存在 `.browser_data/` 目录中，下次启动无需重新登录

## License

MIT
