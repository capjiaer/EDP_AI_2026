# EDP Rewrite - Current Status

> Last updated: 2026-04-26

## Recently Completed

### edp run / debug chain
- Added `-debug/--debug` in CLI (`edp run`)
- Debug flag is propagated through `Executor` and `Runner`
- LSF debug mode now uses `bsub -Ip`
- Debug run generates and executes `*_debug.sh` or `*_debug.csh` based on current shell
- Added `-info/--info` to print full failure diagnostics

### Shell consistency
- Script generation now auto-detects shell and writes one launcher only:
  - bash -> `*.sh`
  - csh/tcsh -> `*.csh`
- Local and LSF runners choose launcher (`bash`/`csh`) from script suffix

### Completion support
- Bash completion updated with `-debug/--debug` and `-info/--info`
- Added csh/tcsh completion file: `completions/edp.csh`
- `edp.csh` now loads completion cache and sources csh completion
- Added Python-driven backtick completion for dynamic step/project/node data

### Flow tutor
- Added `edp flow create` interactive scaffold command
- Supports minimal skeleton generation (`step.yaml`, `config.yaml`, `steps/*.tcl`, `hooks/*`)
- Added command tests and prompt examples for new flow owners

### Script builder cleanup
- Unified `tcl_packages` source logic (base/overlay) into `_source_block()` calls
- Removed duplicate manual loop paths for tcl_packages sourcing

## Remaining

### edp run 端到端测试
- 等 LSF 环境就绪后再补 CLI 集成测试

## Completed Core Modules

- configkit: `files2tcl` + override/new tracking
- cmdkit: `script_builder` + debug script generation
- dirkit: `init` + hook template generation
- flowkit: runner / executor / graph integration
- edp CLI: `init` / `status` / `graph` / `run` / `retry` / `doctor` / `flow`
