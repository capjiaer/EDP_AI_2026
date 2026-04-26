# EDP_AI Rewrite 项目概览

> Last updated: 2026-04-26

## 目标

在保留 EDP 流程编排核心能力的前提下，完成可维护、可测试、可扩展的新版本实现，覆盖从 `init` 到 `run` 的主流程，并提供 Web 前端降低使用门槛。

## 当前状态（可对外使用）

### CLI
- `init` / `status` / `graph` / `run` / `retry` / `doctor` / `flow create` 已可用
- `edp run <step> -debug/--debug` 支持调试执行
- LSF 交互模式支持 `bsub -Ip`
- `-info/--info` 可输出完整失败诊断
- 自动按当前 shell 生成启动脚本（`.sh` 或 `.csh`）
- bash / csh / tcsh 补全

### Web UI（Phase 1 已完成）
- Vue 3 + Flask 前后端，单容器部署
- Vue Flow 交互式 DAG 图（从上到下布局）
- 点击节点触发 step 运行
- WebSocket 实时状态推送（idle/running/success/failed/skipped 五色）
- 顶部三级联动选择 foundry / node / project
- 右侧面板显示 step 详情与状态
- 底部状态栏显示 WebSocket 连接与运行计数

## 模块状态

| 模块 | 职责 | 状态 |
|------|------|------|
| `configkit` | YAML/Tcl 配置桥接与覆盖链处理 | 完成 |
| `cmdkit` | step/config/debug 脚本生成 | 完成 |
| `flowkit` | 依赖图、执行器、runner | 完成 |
| `dirkit` | 工程与工作区初始化 | 完成 |
| `edp` | CLI 命令编排与上下文解析 | 完成 |
| `web/backend` | Flask REST API + WebSocket | 完成 |
| `web/frontend` | Vue 3 DAG 可视化 | 完成 |

## 剩余工作

- 等 LSF 环境就绪后补 `edp run` 端到端 CLI 集成测试
- Web UI Phase 2：数据库、配置在线编辑、Check list 功能、初始化向导
