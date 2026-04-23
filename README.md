# EDP AI 2026 — EDA Flow Framework Rewrite

> Last updated: 2026-04-23

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
│   ├── flow/
│   │   └── initialize/{foundry}/{node}/
│   │       ├── common_prj/         # base flow（通用）
│   │       └── {project}/          # overlay flow（项目级覆盖）
│   └── common_packages/
│       └── tcl_packages/default/
│           └── edp_debug.tcl       # 交互式 debug CLI
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

### Generated Scripts (per step)

| 文件 | 用途 |
|------|------|
| `cmds/{tool}/{step}_config.tcl` | 配置变量（configkit 生成） |
| `cmds/{tool}/{step}.tcl` | 正常执行脚本 |
| `cmds/{tool}/{step}_debug.tcl` | debug 交互脚本 |
| `runs/{tool}/{step}/{step}.sh` | 启动包装（bsub/bash） |

### Hook System

```
hooks/{tool}/{step}/
  ├── step.pre          # step 级 pre hook
  ├── step.post         # step 级 post hook
  ├── {sub}.pre         # sub_step 级 pre hook
  ├── {sub}.post        # sub_step 级 post hook
  └── {sub}.replace     # sub_step 替换 hook
```

Hook 为 proc 定义，通过 `if {[info procs ...]}` 安全调用，空模板不生效。

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
```

## CLI Commands

```bash
edp init -prj dongting -ver P85          # 初始化项目
edp init -blk pcie                       # 初始化 block workspace
edp status                                # 查看执行状态
edp graph                                 # 查看/切换依赖图
edp run [step] [options]                  # 执行
```

## Tech Stack

- **Python 3.9+** (click, pyyaml, tkinter.Tcl)
- **Tcl 8.6+** (EDA tool scripting)
- **LSF** (job scheduling)

## Development Status

| Module | Status |
|--------|--------|
| configkit (files2tcl, override tracking) | Done |
| cmdkit (script_builder, debug script) | Done |
| dirkit (init, hook templates) | Done |
| flowkit (runner, executor, graph) | Done |
| edp CLI (init/status/graph) | Done |
| edp run --debug | Pending |

See [TODO.md](TODO.md) for remaining issues.
