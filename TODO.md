# EDP Rewrite - Pending Issues

## edp run 遗留问题

### 1. --debug 支持
- CLI 没有加 `--debug` 选项
- Executor 没有传递 debug 标志
- 需要 `edp run place --debug` → 生成并执行 `place_debug.sh`（带 `bsub -Ip`）

### 2. Runner 用 bash 执行 csh 脚本
- `LocalRunner`: `subprocess.run(["bash", script.sh])`
- `LSFRunner`: `cmd.append("bash")` + `cmd.append(script.sh)`
- 但 .sh 的 shebang 是 `#!/bin/csh`
- 需要统一：要么改成 bash，要么用 csh 执行

### 3. LSFRunner 没有 -Ip 支持
- debug 模式需要 `bsub -Ip`（interactive + pseudo-terminal）
- 当前只有 `-K`（阻塞等待）

### 4. Debug 模式执行方式
- 正常模式：`.sh` 脚本包含完整命令（`bsub ... innovus place.tcl`）
- Debug 模式：需要 `bsub -Ip ... innovus`，然后在 innovus shell 里 source `place_debug.tcl`
- 方案：生成 `place_debug.sh`（带 `-Ip` + innovus -init debug.tcl），runner 照样跑 .sh

### 5. tcl_packages source 逻辑重复
- base/overlay 的 tcl_packages 是手写循环，和 `_source_block()` 重复
- 可以统一用 `_source_block()` 加额外注释参数

## 已完成模块

- configkit: files2tcl 完成，override/new 标记完成
- cmdkit: script_builder.py 完成，36 tests 通过
- dirkit: init + hook 模板生成完成
- edp_debug.tcl: debug CLI 完成，catch/skip 已修
- CLI: init/status/graph 完成
