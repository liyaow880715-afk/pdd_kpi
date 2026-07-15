# 多平台电商 BI 看板

拼多多 / 抖音 / 天猫（占位） 的推广与订单数据 BI 分析工具。

后端使用 **Python + FastAPI + pandas**，前端使用 **Vite + React + TypeScript + Tailwind CSS**，通过浏览器访问；支持多店铺、多账号权限、AI 分析结论与企业微信日报推送。

---

## 功能特性

- 📊 **多平台切换**：拼多多、抖音、天猫（占位）独立数据与菜单
- 🏪 **多店铺隔离**：每个平台下可创建多个店铺，数据分开存储、分开筛选
- 📤 **数据导入**：拖拽上传推广 Excel / 订单 CSV，支持单日文件与全数据文件自动按日期拆分
- 📈 **核心 KPI 看板**：
  - 拼多多：推广花费、GMV、真实 ROI、退款率、点击率、商家实收、自然流量占比等
  - 抖音：消耗、成交金额、净成交金额、**实际收入**（订单应付金额 + 平台实际承担优惠金额）、ROI、点击率、转化率等
- 🛒 **商品级 / 规格级明细**：排行、对比、趋势图、导出 CSV
- 💰 **成本管理**：按「商家编码」维护商品成本/物流成本，支持刷新编码、未映射商品绑定、导入导出、待维护导出
- 🤖 **AI 智能洞察**：支持 Kimi / OpenAI / 任意兼容 API，自动生成平台专属分析结论
- 📲 **企业微信日报**：按店铺汇总后推送到指定机器人
- 👥 **账号权限**：主账号 + 子账号，支持按页面与店铺授权
- 🚀 **自动部署**：GitHub Actions 推送 `main`/`master` 后自动构建前端并部署到服务器

---

## 技术栈

| 层级 | 技术 |
|---|---|
| 后端 | Python 3.12、FastAPI、Pydantic、pandas、numpy、PyJWT、bcrypt |
| 前端 | Vite、React 19、TypeScript、Tailwind CSS 3、shadcn-style 组件 |
| 数据存储 | Parquet + JSON（本地文件），按平台与店铺隔离 |
| 部署 | uvicorn + systemd + Nginx + GitHub Actions |

---

## 快速启动（本地开发）

### 1. 安装后端依赖

```bash
cd pdd_bi_dashboard
python -m venv venv
venv\Scripts\pip install -r requirements.txt
```

### 2. 启动后端

```bash
venv\Scripts\python -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

浏览器访问 `http://localhost:5173`，默认账号 `admin` / `admin123`。

---

## 线上部署

项目已配置 GitHub Actions（`.github/workflows/deploy.yml`），推送 `main`/`master` 分支后自动：

1. 使用 Node.js 构建前端
2. 将 `frontend/dist/` 上传到服务器
3. 服务器执行 `git pull`、安装依赖、清理 `__pycache__`、重启 `pdd_kpi.service`、重载 Nginx

依赖 Secrets：`SERVER_HOST`、`SERVER_USER`、`SERVER_SSH_KEY`。

---

## 使用步骤

1. 登录后，顶部导航切换平台（拼多多 / 抖音）
2. 进入「导入」页面，选择店铺、上传推广 Excel 与订单 CSV
3. 日期留空时，程序会自动拆分文件内的所有日期
4. 进入「总览」查看汇总 KPI 与趋势
5. 进入「指标」查看单店详情、商品明细、规格分析
6. 进入「成本」维护商家编码对应的商品成本 / 物流成本
7. 进入「AI」配置 API Key 并生成分析结论
8. 进入「企微」配置机器人并发送日报

---

## 文件格式说明

### 拼多多推广数据

支持 `.xls` / `.xlsx`，关键列：

| 关键列 | 说明 |
|---|---|
| 商品ID / 商品id | 商品唯一标识 |
| 成交花费(元) / 总花费(元) | 推广花费 |
| 交易额(元) / 成交金额(元) | 推广 GMV |
| 成交笔数 | 推广成交订单数 |
| 曝光量 | 曝光次数 |
| 点击量 | 点击次数 |

### 拼多多订单数据

支持 `.csv`，关键列：

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

### 抖音推广数据

支持乘方推广 / 全域推广 Excel，关键列包括：

- 商品ID、商品名称、日期
- 整体消耗 / 综合成本
- 整体成交金额 / 净成交金额
- 整体成交订单数 / 净成交订单数
- 整体展示次数、整体点击次数
- 1小时内退款订单数 / 1小时内退款金额（可选）

### 抖音订单数据

支持 `.csv`，关键列：

| 关键列 | 说明 |
|---|---|
| 商品ID | 商品唯一标识 |
| 选购商品 | 商品名称 |
| 商品规格 | 规格名称 |
| 商品数量 | 购买数量 |
| 商品单价 | 单价 |
| 订单应付金额 | 买家应付金额 |
| 平台实际承担优惠金额 | 平台补贴（用于计算实际收入）|
| 商家编码 | 成本管理用（可选）|
| 订单状态 / 售后状态 | 用于退款/取消判定 |
| 订单提交时间 / 下单时间 | 用于拆分日期 |

> 抖音实际收入 = 订单应付金额 + 平台实际承担优惠金额

---

## AI 配置

在「AI」页面配置：

- **API Key**：Kimi / OpenAI / 兼容 API Key
- **Base URL**：
  - Kimi coding: `https://api.kimi.com/coding/v1`
  - Moonshot: `https://api.moonshot.cn/v1`
  - OpenAI: `https://api.openai.com/v1`
- **模型名称**：如 `kimi-coding`、`moonshot-v1-8k`、`gpt-4o-mini`
- **Temperature**：默认 `1.0`

配置好后点击「测试连接」验证。未配置 API Key 时，系统会使用内置规则生成简要结论。

> API Key 保存在本机 `data/config.json`，不会上传。

---

## 成本管理

成本按「商家编码」维护，全店铺通用：

1. 点击「刷新编码」从订单中自动提取商家编码
2. 在「待维护商家编码」中填写商品成本 / 物流成本，点击「保存」
3. 若订单中没有商家编码，可在「未映射商家编码的商品」中把 `product_id` / 规格绑定到商家编码
4. 支持导入导出 CSV，也可单独导出「待维护商家编码」清单

成本会按 `有效订单数` 计算总成本，并结合 `有效 GMV` 计算毛利、毛利率、盈亏、盈亏率。

---

## 数据存储

数据按平台隔离保存在项目目录下：

- `data/processed/{店铺}/`：拼多多商品指标、样式指标、订单明细
- `data/processed_douyin/{店铺}/`：抖音商品指标、订单明细
- `data/costs.json`：拼多多成本配置
- `data/douyin_costs.json`：抖音成本配置
- `data/config.json`：AI 配置、用户认证等
- `data/stores.json`：店铺注册信息（含 platform 字段）

---

## 项目结构

```
pdd_bi_dashboard/
├── api.py                      # FastAPI 主入口
├── api_client.py               # LLM API 调用客户端
├── app.py / dashboard.py       # 旧版 Streamlit 入口（保留兼容）
├── data_loader.py              # 拼多多文件读取
├── data_processor.py           # 拼多多推广与订单匹配
├── metrics.py                  # 拼多多 KPI 计算
├── cost_manager.py             # 拼多多成本管理
├── storage.py                  # 拼多多数据持久化
├── ai_analyzer.py              # 拼多多 AI 提示词
├── report_builder.py / wecom.py # 拼多多企微日报
├── store_manager.py            # 店铺注册与权限
├── auth.py                     # JWT 认证与权限中间件
├── routers/                    # FastAPI 路由
│   ├── auth.py / users.py / stores.py
│   ├── imports.py / orders.py / metrics.py / costs.py
│   ├── ai.py / wecom.py / exports.py / dashboard.py
│   └── douyin.py / douyin_costs.py / douyin_ai.py / douyin_wecom.py
├── douyin_loader.py            # 抖音文件读取
├── douyin_metrics.py           # 抖音 KPI 计算
├── douyin_cost_manager.py      # 抖音成本管理
├── douyin_services.py          # 抖音业务服务层
├── douyin_storage.py           # 抖音数据持久化
├── douyin_ai_analyzer.py       # 抖音 AI 提示词
├── douyin_report_builder.py    # 抖音企微日报
├── frontend/                   # React 前端
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/              # 拼多多 / 抖音各页面
│   │   ├── components/
│   │   └── api/client.ts
│   └── package.json
├── requirements.txt
├── start.bat / start.ps1       # 本地旧版 Streamlit 启动脚本
├── .github/workflows/deploy.yml # 自动部署
└── README.md
```

---

## 注意事项

- 首次运行会创建 `venv/` 和 `data/` 目录
- 拼多多真实 ROI = 有效商家实收 / 推广花费，「有效」指剔除退款和取消订单
- 抖音实际收入 = 订单应付金额 + 平台实际承担优惠金额
- 推广数据中的「总计/汇总/全部」行会自动过滤
- 多店铺数据按「店铺名称」分别存储；店铺注册时选择所属平台
- 子账号权限在「用户管理」中配置，需勾选对应平台页面与允许店铺
- 天猫板块当前为占位状态，未接入实际数据功能
