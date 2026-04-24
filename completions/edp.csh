# edp tcsh/csh completion
# Usage: source edp.csh (it will source this file automatically)

if (! $?EDP_ROOT) then
    exit
endif

set _edp_cache_file = "${EDP_ROOT}/.edp_completion_cache"

set _edp_projects = ""
set _edp_nodes = ""
set _edp_steps = ""

if ( -f "$_edp_cache_file" ) then
    set _edp_projects = `awk -F= '/^PROJECTS=/{print $2}' "$_edp_cache_file"`
    set _edp_nodes = `awk -F= '/^NODES=/{print $2}' "$_edp_cache_file"`
    set _edp_steps = `awk -F= '/^STEPS=/{print $2}' "$_edp_cache_file"`
endif

if ("$_edp_projects" == "") set _edp_projects = ( )
if ("$_edp_nodes" == "") set _edp_nodes = ( )
if ("$_edp_steps" == "") set _edp_steps = ( )

set _edp_subcmds = (init run status retry graph doctor flowcreate tutor -h --help)
set _edp_init_opts = (-prj --project -w --work-path -n --node -ver --version -blk --block -br --branch --link --no-link -h --help)
set _edp_run_opts = (-fr --from -to --to -skip --skip -dr --dry-run --force -debug --debug -info --info -h --help)
set _edp_status_opts = (-h --help)
set _edp_retry_opts = (-dr --dry-run -debug --debug -info --info -h --help)
set _edp_graph_opts = (-f --format -o --output -select --select -h --help)

uncomplete edp >& /dev/null

# 第一段：子命令
complete edp 'p/1/($_edp_subcmds)/'

# init: 常规选项 + 参数值
complete edp 'n/init/($_edp_init_opts)/'
complete edp 'N/-prj --project/($_edp_projects)/'
complete edp 'N/-n --node/($_edp_nodes)/'
complete edp 'N/-ver --version/(P85 P95 P100)/'
complete edp 'N/-w --work-path/d/'

# run: 位置参数(step) + 选项 + 选项值
complete edp 'n/run/($_edp_run_opts $_edp_steps)/'
complete edp 'N/-fr --from/($_edp_steps)/'
complete edp 'N/-to --to/($_edp_steps)/'
complete edp 'N/-skip --skip/($_edp_steps)/'

# retry: step + options
complete edp 'n/retry/($_edp_steps $_edp_retry_opts)/'

# status: help only
complete edp 'n/status/($_edp_status_opts)/'

# graph: 选项 + 枚举 + 路径
complete edp 'n/graph/($_edp_graph_opts)/'
complete edp 'N/-f --format/(ascii dot table)/'
complete edp 'N/-o --output/f/'

# doctor: help only
complete edp 'n/doctor/(--strict --json -h --help)/'

# single-token alias: flowcreate
complete edp 'n/flowcreate/(--tool --step --sub-steps --invoke -h --help)/'
complete edp 'N/--tool/(pnr_innovus pv_calibre sta_pt)/'
complete edp "N/--step/($_edp_steps)/"
complete edp "N/--sub-steps/($_edp_steps)/"
complete edp 'N/--invoke/(innovus\ -init\ \$edp\(script\) calibre\ -drc\ \$edp\(script\) pt_shell\ -file\ \$edp\(script\))/'

# tutor subcommands
complete edp 'n/tutor/(quickstart model diagnose -h --help)/'

