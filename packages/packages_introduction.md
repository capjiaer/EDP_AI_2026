# Packages 说明

本目录包含 EDP 框架核心库与 CLI 入口模块（Python v2.0 重写）。

## cmdkit — 脚本生成

根据 flow 目录结构和覆盖链，为每个 step 生成可执行的 Tcl 脚本。

- `ScriptBuilder` — 脚本生成引擎，自动从 flow 目录加载 `step.yaml`/`config.yaml`，结合 workdir hooks 生成最终脚本
- `_script_utils` — 路径与 source 片段等通用脚本工具
- `_proc_conflict` — Tcl `proc` 重名冲突检查（构建期 fail-fast）
- `_invoke_resolver` — `invoke` 解析与 step shell 脚本生成
- `_script_sections` — config/header/debug 片段生成

## configkit — 配置转换

负责配置文件的加载、转换和合并。

- YAML/Tcl 双向转换（Python dict ↔ Tcl interp）
- 变量引用展开（`$var`, `${var}`）
- 多文件配置合并
- 支持混合格式加载（YAML + Tcl）

## dirkit — 目录管理

负责项目环境初始化和工作路径管理。

- `ProjectInitializer` — 项目初始化
- `WorkPathInitializer` — 工作路径初始化
- `ProjectFinder` — 项目查找
- `BranchLinker` — 分支管理与链接

## flowkit — 工作流执行

负责步骤依赖管理和工作流执行。

- `Graph` / `Dependency` — 依赖图构建与拓扑排序
- `Step` / `StepStatus` — 步骤状态管理
- `StepRegistry` — 工具步骤注册表（`common_prj -> project` 覆盖链：同名 step 覆盖，新 step 追加）
- `WorkflowBuilder` — 从配置构建可执行工作流
- `DependencyLoader` — 依赖关系加载与解析

## edp — CLI 编排入口

面向 flow owner 的命令行入口，负责把上下文解析、图配置选择、脚本生成与执行串起来。

- `cli.py` — 顶层命令注册（`init/run/status/retry/graph/doctor/flow`）
- `context.py` — 分支上下文自动解析与 `graph_config` 选择
- `commands/flow_cmd.py` — `edp flow create` 交互式骨架生成 tutor

## 新同学最短上手路径

目标：从 0 到可 dry-run 的新 step，先跑通主链路，再细化脚本逻辑。

1. 进入分支工作目录后执行 `edp flow create`
2. 根据提示输入 `tool/step/sub_steps/invoke`（可直接回车使用默认值）
3. 查看生成的 `cmds/<tool>/step.yaml` 与 `cmds/<tool>/steps/<step>/*.tcl`
4. 按需编辑 `hooks/<tool>/<step>/*`（不用可删）
5. 在 `step_config.yaml` 中确认已选择 `tool.step`
6. 执行 `edp run <step> --dry-run` 验证结构完整

常见规则：

- 覆盖链按 `common_prj -> project` 加载
- 同名 `step` 在 project 层整体覆盖 common 层
- 新 `step` 在 project 层增量追加，不影响 common 其他 step

最小示例（以 `pv_calibre.dfm` 为例）：

- 交互输入示例：
  - `Tool name`: `pv_calibre`
  - `Step name`: `dfm`
  - `Sub steps`: `dfm`
  - `Invoke`: `calibre -drc -hier -turbo`
  - `Create hooks`: `yes`
- 典型生成结果：
  - `cmds/pv_calibre/step.yaml` 中新增：
    - `supported_steps.dfm.invoke = ["calibre -drc -hier -turbo"]`
    - `supported_steps.dfm.sub_steps = [dfm]`
  - `cmds/pv_calibre/steps/dfm/dfm.tcl`
  - `hooks/pv_calibre/dfm/step.pre`、`step.post`、`dfm.pre`、`dfm.post`、`dfm.replace`
- 验证命令：
  - `edp run dfm --dry-run`
