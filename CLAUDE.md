# CLAUDE.md — EDP AI 2026 项目上下文

> Claude Code 每次对话开始时自动读取此文件

## 用户背景

- EDA 工程师，负责 EDP 流程编排框架开发
- Python 为主，前端/Web 在积极学习中
- 喜欢边做边学，希望每步有简要教学（做了什么、改了哪些文件、为什么）
- 偏好先做到大体可用，再迭代优化
- 沟通风格轻松，中英混用
- git: name=capjiaer, email=capjiaer@163.com

## 项目结构

```
packages/          — Python 核心库
  configkit/       — YAML/Tcl 配置桥接与覆盖链
  cmdkit/          — step/config/debug 脚本生成
  flowkit/         — 依赖图、执行器、runner
  dirkit/          — 工程与工作区初始化
  edp/             — CLI 命令编排（init/status/graph/run/retry/doctor/flow）
resources/         — 多 foundry/node/project 配置数据
web/
  backend/         — Flask REST API + WebSocket (SocketIO)
  frontend/        — Vue 3 + Vite + Vue Flow + Element Plus
```

## CLI 命令（已完成）

`init` / `status` / `graph` / `run` / `retry` / `doctor` / `flow create`

## Web UI

### 启动方式
```bash
cd web && source venv/bin/activate && python3 -m backend.app   # 生产模式 (port 5000)
cd web/frontend && npm run dev                                   # 开发模式 (Vite 5173 + proxy)
cd web/frontend && npm run build                                 # 构建前端
```

### 架构要点
- Backend: Flask App Factory (`create_app()`)，**必须用 `socketio.run()` 启动**（不能用 `app.run()`，否则 gevent-websocket 失败）
- Frontend: Vue 3 Composition API，WebSocket 用 socket.io-client
- Vue Flow 自定义节点只通过 `data` prop 传数据，不要用顶层 prop
- 部署：Docker multi-stage build，Vue build → Flask serve 静态文件
- npm 镜像：`npm config set registry https://registry.npmmirror.com`

### Phase 1 已完成 (2026-04-26)
- DAG 可视化（Vue Flow，从上到下布局，smoothstep 边）
- 点击节点触发运行 + 实时状态推送（WebSocket 五色：idle/running/success/failed/skipped）
- 顶部三级联动 foundry/node/project 选择
- 右侧 Step 详情面板 + 底部状态栏

### Phase 2 待做
- 数据库（当前读文件系统）
- 配置在线编辑
- Check list 功能
- 初始化向导

## 已知坑

| 坑 | 解法 |
|----|------|
| Flask-SocketIO + gevent 用 `app.run()` 启动会 WebSocket 500 | 必须用 `socketio.run(app)` |
| Vue Flow 自定义节点的额外 prop 不会被传入 | 所有业务字段放 `data` 里，组件读 `props.data.xxx` |
| `npm run build` 从项目根目录执行会 ENOENT | 必须从 `web/frontend/` 执行 |
| 系统没有 `python` 命令 | 始终用 `python3` |
| npm 国内网络慢 | 配 npmmirror 镜像 |

## 剩余工作

- 等 LSF 环境就绪后补 `edp run` 端到端 CLI 集成测试
- Web UI Phase 2 功能
