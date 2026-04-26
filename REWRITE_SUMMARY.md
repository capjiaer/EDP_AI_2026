# EDP Rewrite 里程碑总结

> Last updated: 2026-04-23

## 本轮完成内容

### 0) `edp flow create` Flow Tutor（MVP）

- 新增命令组：`edp flow`
- 新增子命令：`edp flow create`
- 通过交互式提问生成最小骨架（`step.yaml` / `config.yaml` / `steps/*.tcl` / `hooks/*`）
- 明确覆盖链语义：同名 step 覆盖，新 step 追加

### 1) `edp run` debug 能力补齐

- 新增参数：`-debug/--debug`
- 新增参数：`-info/--info`（失败时显示完整诊断）
- Debug 模式支持 LSF 交互提交：`bsub -Ip`

### 2) Shell 一致性修复

- 启动器生成由“固定 `.sh`”升级为“按当前 shell 自动选择”
  - bash -> `.sh`
  - csh/tcsh -> `.csh`
- 本地和 LSF 执行均按脚本后缀选择解释器

### 3) 可观测性与排障体验

- debug 模式打印启动信息（runner + script path）
- 执行失败时输出摘要
- `-info` 下输出完整细节（含 launcher/script/workdir/LSF command）

### 4) 补全体系完善

- bash 补全增加 `-debug/--debug`、`-info/--info`
- 新增 csh/tcsh 补全文件 `completions/edp.csh`
- `edp.csh` 增加 completion cache 生成与自动加载

### 5) 文档同步

- `README.md`：补充 debug/info 用法、shell/completion 说明、产物策略
- `TODO.md`：从历史遗留清单更新为当前状态 + 真实剩余待办

## 回归验证（最小集合）

- `python -m edp run --help`：确认参数可见
- `packages.cmdkit.tests.test_cmdkit.TestShellGeneration`
- `packages.cmdkit.tests.test_cmdkit.TestWriteStepScript`
- `packages.flowkit.tests.test_executor.TestLSFRunner`

上述定向回归已通过。

## 下一步

- 等 LSF 环境就绪后补 `edp run` 的 CLI 端到端测试
- `try_new_edp` 产物不做特殊跟踪，gitignore 已覆盖
