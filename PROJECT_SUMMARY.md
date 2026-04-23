# EDP_AI Rewrite 项目概览

> Last updated: 2026-04-23

## 目标

在保留 EDP 流程编排核心能力的前提下，完成可维护、可测试、可扩展的新版本实现，覆盖从 `init` 到 `run` 的主流程。

## 当前状态（可对外使用）

- CLI：`init` / `status` / `graph` / `run` 已可用
- Debug 执行链：
  - `edp run <step> -debug/--debug`
  - LSF 交互模式支持 `bsub -Ip`
  - `-info/--info` 可输出完整失败诊断
- Shell 一致性：
  - 自动按当前 shell 生成启动脚本（`.sh` 或 `.csh`）
  - 本地执行与 LSF 提交都会按脚本后缀选择解释器
- 补全：
  - bash：`completions/edp.bash`
  - csh/tcsh：`completions/edp.csh`

## 模块状态

- `configkit`：YAML/Tcl 配置桥接与覆盖链处理（完成）
- `cmdkit`：step/config/debug 脚本生成（完成）
- `flowkit`：依赖图、执行器、runner（完成）
- `dirkit`：工程与工作区初始化（完成）
- `edp`：命令编排与上下文解析（完成）

## 关键改进

- 保留配置覆盖链语义：base -> overlay -> user
- 引入可读的失败诊断上下文（launcher/script/workdir/LSF command）
- 增加 debug 场景可观测性（执行前调试提示 + `-info` 细节模式）
- 统一文档和补全入口，降低团队上手成本

## 剩余建议工作

- 对 `edp run` 增加端到端 CLI 集成测试
- 清理 `script_builder` 中可合并的重复 source 逻辑
- 持续优化 `try_new_edp` 产物的跟踪与忽略策略
