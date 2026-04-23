# Packages 说明

本目录包含 EDP 框架的四个核心库，均为 Python v2.0 重写版本。

## cmdkit — 脚本生成

根据 flow 目录结构和覆盖链，为每个 step 生成可执行的 Tcl 脚本。

- `ScriptBuilder` — 脚本生成引擎，自动从 flow 目录加载 step.yaml/config.yaml，结合 workdir hooks 生成最终脚本

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
- `StepRegistry` — 工具步骤注册表（支持覆盖链加载）
- `WorkflowBuilder` — 从配置构建可执行工作流
- `DependencyLoader` — 依赖关系加载与解析
