# EDP AI 2026 — EDA Flow Framework Rewrite

> Last updated: 2026-04-28

## Overview

EDP (EDA Design Platform) 是一套 EDA 流程管理框架，用于管理 IC 设计中从综合到签核的完整流程。本项目是 2026 年的全面重写版本，采用 Python 3 + Tcl 双语言架构。

## Architecture

```
edp run drc
     │
     ▼
┌──────────┐     ┌──────────────┐     ┌──────────────┐
│  edp CLI │────▶│   flowkit    │────▶│   cmdkit     │
│  (click) │     │  executor    │     │ script_builder│
│          │     │  runner      │     │              │
│  init    │     │  graph       │     │ ┌──────────┐ │
│  run     │     │  state_store │     │ │config.tcl│ │
│  status  │     └──────────────┘     │ │step.tcl  │ │
│  graph   │          │               │ │debug.tcl │ │
└──────────┘          │               │ │step.sh   │ │
                      ▼               │ └──────────┘ │
               ┌──────────────┐     └──────┬───────┘
               │   configkit  │            │
               │  yaml ↔ tcl  │            ▼
               │  files2tcl   │     ┌──────────────┐
               │  override    │     │   dirkit     │
               │  tracking    │     │  init -prj   │
               └──────────────┘     │  init -blk   │
                                    │  hook 模板    │
                                    └──────────────┘
```

## Directory Structure

```
new_edp/
├── packages/
│   ├── edp/          # CLI 入口（init/run/status/graph）
│   ├── configkit/    # 配置转换（YAML ↔ Tcl, files2tcl）
│   ├── cmdkit/       # 脚本生成（ScriptBuilder）
│   ├── dirkit/       # 目录管理（init, project finder）
│   └── flowkit/      # 工作流引擎（graph, executor, runner）
├── resources/
│   └── flow/
│       ├── common_packages/        # 全局共享 tcl 包（default/<tool>）
│       │   └── tcl_packages/default/
│       │       └── edp_debug.tcl   # 交互式 debug CLI
│       └── initialize/{foundry}/{node}/
│           ├── common_prj/         # base flow（通用）
│           └── {project}/          # overlay flow（项目级覆盖）
├── web/                             # Web UI（Flask + Vue 3）
│   ├── backend/                     #   Flask API & WebSocket 服务
│   │   ├── api/                     #     REST 端点（graph/status/run/projects）
│   │   └── services/                #     业务逻辑（graph_service/run_service）
│   ├── frontend/                    #   Vue 3 前端（Vite + Vue Flow + Element Plus）
│   │   └── src/components/          #     FlowGraph / StepNode / TopNav / SidePanel / StatusBar
│   ├── cmds/                        #   命令模板（pnr_innovus / pv_calibre）
│   ├── Dockerfile                   #   多阶段构建（Node.js 前端 + Python 后端）
│   └── docker-compose.yml           #   单容器部署
├── docs/                            # 设计文档与规划
│   └── superpowers/
│       ├── plans/                   #   实施计划
│       └── specs/                   #   技术规格
├── bin/edp                          # CLI 入口脚本
├── edp.sh / edp.csh                 # 环境设置脚本
└── completions/                     # Tab 补全
```

## Core Concepts

### Config Overlay Chain

```
base config.yaml → overlay config.yaml → user_config.yaml
```

后面覆盖前面，`files2tcl` 生成单一 config.tcl，标注每个变量的来源、`[override]` 和 `[new]`。

### Step Supply vs Activation

- `cmds/{tool}/step.yaml`（供给层）：定义工具“可提供”的 step（`supported_steps`、`invoke`、`sub_steps`）。
- `step_config.yaml`（应用层）：定义当前 flow “实际启用”的 step（`steps` 列表）。
- 结论：`step.yaml` 的能力声明不会自动进入执行面，是否执行以 `step_config.yaml` 为准。

### Invoke vs LSF

- `invoke`（命令层）：只负责工具命令拼接与变量展开（`{var}`、`$var`、`$edp(var)`）。
- `lsf`（调度层）：只负责 bsub 资源参数（`lsf_mode`、`queue`、`cpu_num`、`mem_limit`、`wall_time`）。
- 映射关系：`queue -> bsub -q`，`cpu_num -> bsub -n`（仅 `>1` 生效），`hosts -> bsub -m`，`mem_limit -> bsub -R`，`wall_time -> bsub -W`，`job_name -> bsub -J`，`extra_opts` 透传。
- 运行模式：默认 `bsub -K`，`edp run --debug` 使用 `bsub -Ip`（当前不从 `config.yaml` 读取 mode）。

### Generated Scripts (per step)

| 文件 | 用途 |
|------|------|
| `cmds/{tool}/{step}_config.tcl` | 配置变量（configkit 生成） |
| `cmds/{tool}/{step}.tcl` | 正常执行脚本 |
| `cmds/{tool}/{step}_debug.tcl` | debug 交互脚本 |
| `runs/{tool}/{step}/{step}.sh` or `.csh` | 启动包装（按当前 shell 自动选择） |

### Hook System

```
hooks/{tool}/{step}/
  ├── step.pre          # step 级 pre hook
  ├── step.post         # step 级 post hook
  ├── {sub}.pre         # sub_step 级 pre hook
  ├── {sub}.post        # sub_step 级 post hook
  └── {sub}.replace     # sub_step 替换 hook
```

Hook 为 proc 定义；生成脚本只会 source 有效 hook 文件并直接调用对应 proc（默认模板文件不会参与执行）。

### Debug Mode

在 EDA 工具 Tcl shell 中交互式调试：

```tcl
source cmds/pnr_innovus/place_debug.tcl
edp_steplist          # 查看计划
edp_next              # 执行下一个 sub_step
edp_run_to opt_design # 执行到指定 sub_step
edp_skip detail_place # 跳过
edp_reset             # 重置
edp_vars pnr*         # 查看变量
```

## Execution Modes

```bash
edp run                # 全图执行
edp run drc            # 单步执行
edp run -fr syn -to drc  # 子图执行
edp run --dry-run      # 预览模式
edp run --force        # 强制重跑
edp run place -debug   # debug 启动（LSF 下走 -Ip）
edp run place -debug -info  # 失败时打印完整诊断信息
```

## CLI Commands

```bash
source edp.sh / source edp.csh                # 载入环境与补全
edp init -prj dongting -ver P85          # 初始化项目
edp init -blk pcie                       # 初始化 block workspace
edp status                                # 查看执行状态
edp graph                                 # 查看/切换依赖图
edp retry [step] [options]                # 从失败步骤重试
edp doctor [--strict] [--json]            # 环境与结构诊断
edp flowcreate                           # 交互式创建新 flow step 骨架
edp run [step] [options]                  # 执行
```

## Tech Stack

- **Python 3.9+** (click, pyyaml, tkinter.Tcl)
- **Tcl 8.6+** (EDA tool scripting)
- **LSF** (job scheduling)

## Shell & Completion

- Bash: `source edp.sh`，加载 `completions/edp.bash`
- Csh/Tcsh: `source edp.csh`，加载 `completions/edp.csh`
- 两套补全都支持 `run` 关键参数（`-debug/--debug`, `-info/--info`, `-fr/-to/-skip`）

## Web UI

基于 Flask + Vue 3 的可视化界面，支持实时状态推送与交互式操作。

### 架构

```text
浏览器 ←── WebSocket ──→ Flask-SocketIO
   │                        │
   ├─ FlowGraph.vue         ├─ api/graph.py      # 依赖图数据
   ├─ StepNode.vue          ├─ api/status.py     # 步骤状态查询
   ├─ SidePanel.vue         ├─ api/run.py        # 触发执行
   ├─ TopNav.vue            ├─ api/projects.py   # 项目层级
   └─ StatusBar.vue         └─ services/         # flowkit 封装
```

### 功能

| 功能 | 说明 |
| ---- | ---- |
| DAG 可视化 | Vue Flow 绘制步骤依赖图，5 色状态标识 |
| 点击执行 | 点击节点触发 `edp run <step>` |
| 实时状态 | WebSocket 推送步骤执行进度 |
| 项目选择 | TopNav 下拉选择 foundry/node/project |
| 详情面板 | SidePanel 展示步骤配置与日志 |

### 部署

```bash
# 开发模式
cd web/frontend && npm install && npm run dev   # 前端 :5173
cd web/backend && pip install -r requirements.txt && python app.py  # 后端 :5000

# Docker 一键部署
cd web && docker-compose up --build
```

## Development Validation

建议在改动 `edp run` 相关逻辑后执行以下最小回归：

```bash
PYTHONPATH=packages python -m unittest \
  packages.edp.tests.test_run_cli_e2e \
  packages.cmdkit.tests.test_cmdkit.TestShellGeneration \
  packages.cmdkit.tests.test_cmdkit.TestWriteStepScript \
  packages.flowkit.tests.test_executor.TestLSFRunner
```

## Workspace Artifact Policy

- `try_new_edp/` 是测试与演示工作区，允许保留可复现流程所需的关键产物
- 建议优先跟踪：
  - `cmds/{tool}/{step}.tcl`
  - `cmds/{tool}/{step}_debug.tcl`
  - shell launcher 示例（`.sh` 或 `.csh`，按当前 shell）
- 建议避免提交临时日志、工具输出数据库等一次性文件
- 如需清理噪音文件，优先在 `try_new_edp/` 下补充局部 `.gitignore`

## Development Status

| Module | Status |
| ------ | ------ |
| configkit (files2tcl, override tracking) | Done |
| cmdkit (script_builder, debug script) | Done |
| dirkit (init, hook templates) | Done |
| flowkit (runner, executor, graph) | Done |
| edp CLI (init/run/status/retry/graph/doctor/flowcreate) | Done |
| edp run -debug/--debug | Done |
| edp run -info/--info | Done |
| bash/csh completion | Done |
| web ui phase 1 (DAG / WebSocket / 点击执行 / Docker 部署) | Done |

See [TODO.md](TODO.md) for remaining issues.
