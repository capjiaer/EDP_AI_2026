# EDP Web UI Design Spec

> 2026-04-26 | Phase 1

## Goal

为 EDP 流程管理框架添加 Web 前端，将 CLI 核心能力（依赖图可视化、步骤执行、状态监控）以交互式图形界面呈现，降低使用门槛。

## Tech Stack

| Layer | Choice | Reason |
|-------|--------|--------|
| Frontend | Vue 3 + Vite | 团队有基础，生态够用 |
| Graph | Vue Flow | Vue 原生 DAG 组件，支持自定义节点/事件/动画 |
| UI Library | Element Plus | 管理后台组件完善，中文文档 |
| Backend | Flask + Flask-SocketIO | 直接 import 现有 Python kit |
| Realtime | WebSocket (SocketIO) | step 状态实时推送 |
| Deployment | Docker (single container) | 内网 Firefox，一键部署 |
| Auth | None | 内网信任环境 |

## Architecture

```
浏览器 (Firefox)
    │
    ▼
┌─────────────────────────────────┐
│  Flask 后端 (单容器)              │
│  ┌──────────┐  ┌──────────────┐ │
│  │ REST API │  │ WebSocket    │ │
│  │ 图数据   │  │ 实时状态推送  │ │
│  │ 触发运行 │  │              │ │
│  └────┬─────┘  └──────┬───────┘ │
│       │               │         │
│       ▼               ▼         │
│  ┌──────────────────────────┐   │
│  │ 复用现有 Python kit       │   │
│  │ flowkit / configkit /    │   │
│  │ cmdkit / dirkit          │   │
│  └──────────────────────────┘   │
│                                 │
│  /static → Vue 构建产物          │
└─────────────────────────────────┘
```

- 开发时：Vue dev server (5173) + Flask (5000)，前后端分离
- 部署时：Vue build 成静态文件由 Flask serve，单容器

## Directory Structure

```
EDP_AI_2026/
├── packages/           # 现有 Python kit（后端直接 import）
├── web/
│   ├── backend/
│   │   ├── app.py          # Flask 入口 + SocketIO 初始化
│   │   ├── api/
│   │   │   ├── graph.py    # GET /api/graph
│   │   │   ├── run.py      # POST /api/run/<step>
│   │   │   ├── status.py   # GET /api/status
│   │   │   └── projects.py # GET /api/projects
│   │   └── ws.py           # WebSocket 事件处理
│   ├── frontend/
│   │   ├── src/
│   │   │   ├── components/
│   │   │   │   ├── FlowGraph.vue    # Vue Flow DAG 主组件
│   │   │   │   ├── StepNode.vue     # 自定义节点（颜色/状态）
│   │   │   │   ├── SidePanel.vue    # 右侧 step 详情/配置/日志
│   │   │   │   ├── TopNav.vue       # 顶部导航（项目切换/doctor）
│   │   │   │   └── StatusBar.vue    # 底部连接/运行状态
│   │   │   ├── composables/
│   │   │   │   └── useSocket.js     # WebSocket 封装
│   │   │   ├── App.vue
│   │   │   └── main.js
│   │   ├── index.html
│   │   ├── package.json
│   │   └── vite.config.js
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── requirements.txt
```

## API Endpoints

### REST

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/graph` | GET | 返回 step 依赖图（nodes + edges） |
| `/api/status` | GET | 返回所有 step 当前状态 |
| `/api/run/<step>` | POST | 触发运行指定 step |
| `/api/projects` | GET | 返回 foundry/node/project 层级数据 |

### WebSocket

| Event | Direction | Payload |
|-------|-----------|---------|
| `step_status` | Server → Client | `{ step, status, message }` |

status 枚举：`idle | running | success | failed | skipped`

## Frontend Layout

```
┌─────────────────────────────────────────┐
│  TopNav（项目选择 / doctor / 设置）       │
├──────────────────────┬──────────────────┤
│                      │                  │
│   FlowGraph          │  SidePanel       │
│   Vue Flow DAG       │  - step 详情     │
│   点击节点触发运行    │  - 配置预览       │
│   颜色表示状态        │  - 运行日志       │
│                      │                  │
├──────────────────────┴──────────────────┤
│  StatusBar（WebSocket 连接 / 运行中数）   │
└─────────────────────────────────────────┘
```

## Node Color Scheme

| Status | Color | Animation |
|--------|-------|-----------|
| idle | 灰色 `#909399` | 无 |
| running | 蓝色 `#409EFF` | 脉冲 |
| success | 绿色 `#67C23A` | 无 |
| failed | 红色 `#F56C6C` | 无 |
| skipped | 黄色 `#E6A23C` | 无 |

## Run Flow (Click to Execute)

```
1. 用户点击 DAG 节点
2. 前端 POST /api/run/<step>
3. Flask 后台线程调用 flowkit 执行
4. 每次状态变化通过 WebSocket push step_status
5. 前端收到事件 → 更新节点颜色 + SidePanel
```

## Phase 1 Scope

### In Scope
- 交互式 DAG 图（Vue Flow）
- 点击节点触发运行
- 实时状态更新（WebSocket）
- 项目层级数据展示
- Docker 部署

### Out of Scope (Phase 2)
- 用户登录/权限
- 数据库（当前读文件系统）
- 配置在线编辑
- Check list 功能
- 初始化向导

## Data Source

一期直接读取文件系统：
- 依赖图：从 `step_config.yaml` + `step.yaml` 解析（复用 flowkit）
- 状态：从 flowkit state_store 读取
- 项目层级：从 `resources/flow/initialize/` 目录结构扫描

## Docker

Multi-stage build:
1. Node.js stage: build Vue frontend
2. Python stage: Flask + built frontend static files
3. Expose port 5000
