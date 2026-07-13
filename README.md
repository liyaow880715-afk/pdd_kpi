# 拼多多推广数据 BI 看板

一个本地浏览器版 BI 工具，支持每日导入拼多多「推广数据 `.xls/.xlsx`」和「订单数据 `.csv`」，自动按 **商品ID** 与 **样式ID** 匹配，计算真实 ROI、退款率、自然流量占比等核心指标，并接入 Kimi / OpenAI API 生成 AI 分析结论。

## 功能特性

- 📤 拖拽上传推广 Excel 与订单 CSV
- 🏪 **多店铺支持**：按店铺名称分别导入、存储、筛选和对比
- 🔗 自动按 `商品ID` + `样式ID` 匹配推广与订单数据
- 📊 核心 KPI 看板：花费、GMV、**有效 ROI**、退款率、点击率等
- 🛒 商品级明细排行与对比
- 🎨 样式/规格级分析（哪个 SKU 最赚钱/最亏钱）
- 🤖 AI 智能洞察（支持 Kimi / OpenAI / 任意兼容 API）
- 📥 一键导出处理后的 CSV
- 📈 多日数据持久化，支持历史趋势对比

## 快速启动

### 方式一：双击启动（推荐）

直接双击项目目录下的 `start.bat`，首次会自动创建虚拟环境并安装依赖。

> 首次运行 Streamlit 可能会在终端询问邮箱，直接按回车跳过即可，之后不会再出现。

### 方式二：命令行启动

```bash
cd pdd_bi_dashboard
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\streamlit run app.py
```

### 方式三：PowerShell 启动

若 `start.bat` 在你的系统上有乱码问题，可右键 `start.ps1` 选择「使用 PowerShell 运行」，或在 PowerShell 中执行：

```powershell
powershell -ExecutionPolicy Bypass -File start.ps1
```

启动后，浏览器会自动打开 `http://localhost:8501`。

## 使用步骤

1. 填写「店铺名称」（多店铺时用于区分数据）
2. 上传「推广数据」Excel 文件
3. 上传「订单数据」CSV 文件
4. 确认或修改数据日期（程序会尝试从文件名自动识别）
5. 可选：填写 Kimi / OpenAI API Key 以启用 AI 深度分析
6. 点击「🚀 开始分析」
7. 在标签页中查看核心指标、商品分析、样式分析、AI 洞察、导出数据

## 文件格式说明

### 推广数据

支持 `.xls` 或 `.xlsx`，需包含以下关键列：

| 关键列 | 说明 |
|---|---|
| 商品ID / 商品id | 商品唯一标识 |
| 成交花费(元) / 总花费(元) | 推广花费 |
| 交易额(元) / 成交金额(元) | 推广带来的 GMV |
| 成交笔数 | 推广成交订单数 |
| 曝光量 | 曝光次数 |
| 点击量 | 点击次数 |

若推广数据中也包含 `样式ID` / `商品规格` 列，则会按样式维度匹配。

### 订单数据

支持 `.csv`，需包含以下关键列：

| 关键列 | 说明 |
|---|---|
| 商品id | 商品唯一标识 |
| 样式ID | SKU/规格标识 |
| 商品规格 | 规格名称 |
| 订单状态 | 如：已收货、已取消、已发货退款成功等 |
| 售后状态 | 如：退款成功、无售后等 |
| 商品总价(元) | 订单商品总价 |
| 商家实收金额(元) | 商家实际收入 |
| 商品数量(件) | 购买数量 |

## AI 配置

在左侧侧边栏配置：

- **API Key**：你的 Kimi / OpenAI / 兼容 API Key
- **Base URL**：
  - Kimi coding（默认）: `https://api.kimi.com/coding/v1`
  - Moonshot: `https://api.moonshot.cn/v1`
  - OpenAI: `https://api.openai.com/v1`
- **模型名称**：
  - Kimi coding: `kimi-coding`
  - Moonshot: `moonshot-v1-8k`
  - OpenAI: `gpt-4o-mini` 或 `gpt-4o`
- **Temperature**：文本生成温度，默认 `1.0`
- **Reasoning Effort**：推理深度，默认 `low`（仅对 kimi-coding / o1 / o3 / o4 等推理模型生效）

配置好后点击「💾 保存 AI 配置」，下次启动会自动读取。然后点击「🧪 测试连接」验证 API 是否可用。

> ⚠️ API Key 以明文保存在本机 `data/config.json`，不会上传，仅供本机使用。

如果未填写 API Key，系统会自动使用内置规则生成洞察结论。

## 数据存储

处理后的数据会保存在项目目录下的 `data/processed/` 中：

- `product_YYYY-MM-DD.parquet`：商品级指标
- `style_YYYY-MM-DD.parquet`：样式级指标
- `orders_YYYY-MM-DD.parquet`：处理后的订单明细
- `data/meta.json`：导入记录元数据

## 项目结构

```
pdd_bi_dashboard/
├── app.py                 # Streamlit 主入口
├── data_loader.py         # 文件读取与列名标准化
├── data_processor.py      # 推广与订单数据匹配
├── metrics.py             # KPI 计算
├── ai_analyzer.py         # AI 提示词与规则化洞察
├── api_client.py          # LLM API 调用客户端
├── config_manager.py      # 本地配置管理（API Key 等）
├── storage.py             # 本地数据持久化（支持多店铺）
├── dashboard.py           # 看板 UI 组件
├── .streamlit/
│   └── config.toml        # Streamlit 配置（主题、禁用统计）
├── requirements.txt
├── start.bat
├── start.ps1
├── .gitignore
└── README.md
```

## 注意事项

- 首次运行会在项目目录下创建 `venv/` 虚拟环境和 `data/` 数据目录
- 推广数据中的「总计」行会自动过滤
- **真实 ROI = 有效商家实收 / 推广花费**，其中「有效」指剔除退款和取消订单
- 退款判定基于订单状态或售后状态包含「退款成功」
- 取消判定基于订单状态包含「已取消」「取消」「交易关闭」
- 若推广数据无样式维度，则样式分析页仅展示订单侧的规格汇总
- AI 分析需自行提供 API Key，工具不会上传或保存你的 Key
- 多店铺数据按「店铺名称」分别存储，文件名会被安全化
