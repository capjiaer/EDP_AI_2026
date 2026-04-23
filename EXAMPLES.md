# EDP 常用示例

> Last updated: 2026-04-23

## 1) 环境加载

### bash

```bash
source edp.sh
```

### csh/tcsh

```csh
source edp.csh
```

---

## 2) 初始化工作区

```bash
# 初始化项目（示例）
edp init -prj dongting -ver P85

# 进入 block 工作区
edp init -blk pcie
```

---

## 3) 创建新 flow step（Flow Tutor）

```bash
# 交互式创建（推荐）
edp flow create

# 半自动：减少提问
edp flow create --tool pnr_innovus --step place
```

示例输入（交互）：
- Tool name: `pv_calibre`
- Step name: `dfm`
- Sub steps: `dfm`
- Invoke: `calibre -drc -hier -turbo`
- Create hooks: `yes`

---

## 4) 常见执行方式

```bash
# 全图执行
edp run

# 单步执行
edp run drc

# 子图执行
edp run -fr syn -to drc

# 仅预览
edp run --dry-run

# 忽略历史状态强制重跑
edp run --force
```

---

## 5) Debug 执行（推荐流程）

```bash
# Debug 执行（会生成并使用 *_debug 启动脚本）
edp run place -debug

# Debug + 完整错误细节
edp run place -debug -info
```

说明：
- LSF debug 使用 `bsub -Ip`
- 启动脚本按当前 shell 自动生成 `.sh` 或 `.csh`

---

## 6) 交互式 Tcl Debug

```tcl
source cmds/pnr_innovus/place_debug.tcl
edp_steplist
edp_next
edp_run_to opt_design
edp_skip detail_place
edp_reset
edp_vars pnr*
```

---

## 7) ConfigKit 快速示例

```python
from configkit import yamlfiles2dict, merge_dict

# 加载并可选展开变量
cfg = yamlfiles2dict("config.yaml", expand_variables=True)

# 合并字典
base = {"a": 1, "b": {"c": 2}}
overlay = {"b": {"d": 3}}
merged = merge_dict(base, overlay)
```

```python
from configkit import dict2tclinterp, tclinterp2dict

data = {"server": {"host": "localhost", "port": 8080}}
interp = dict2tclinterp(data)
back = tclinterp2dict(interp)
```

---

## 8) 补全验证

```bash
# bash
edp run -<Tab>
edp run --<Tab>
```

```csh
# csh/tcsh
edp run -<Tab>
edp init -prj <Tab>
edp graph -f <Tab>
```
