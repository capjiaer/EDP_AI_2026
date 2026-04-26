# edp tcsh/csh completion — dynamic data via $var, flag completion via n/<flag>/
#
# Prerequisites (handled by edp.csh before sourcing this file):
#   1. $_edp_projects, $_edp_nodes, $_edp_steps are set from cache
#   2. EDP_ROOT is set
#
# Design notes:
#   - All rules use 2-part n/<prev>/(list)/ format to avoid tcsh's
#     "Invalid completion" conflict (which triggers when the same word
#     appears as both a completion value and a 3-part pattern trigger).
#   - Dynamic values use $var list type (populated from cache at source
#     time; steps/nodes/projects rarely change within a session).

if (! $?EDP_ROOT) then
    exit
endif

uncomplete edp >& /dev/null

complete edp \
  'p/1/(init run status retry graph doctor flowcreate tutor)/' \
  \
  'n/init/(-prj --project -w --work-path -n --node -ver --version -blk --block -br --branch --link --no-link -h --help)/' \
  'n/-prj/$_edp_projects/' \
  'n/--project/$_edp_projects/' \
  'n/-n/$_edp_nodes/' \
  'n/--node/$_edp_nodes/' \
  'n/-ver/(P85 P95 P100)/' \
  'n/--version/(P85 P95 P100)/' \
  'n/-w/d/' \
  'n/--work-path/d/' \
  'n/-blk/d/' \
  'n/--block/d/' \
  \
  'n/run/(-fr --from -to --to -skip --skip -dr --dry-run --force -debug --debug -info --info -h --help)/' \
  'n/-fr/$_edp_steps/' \
  'n/--from/$_edp_steps/' \
  'n/-to/$_edp_steps/' \
  'n/--to/$_edp_steps/' \
  'n/-skip/$_edp_steps/' \
  'n/--skip/$_edp_steps/' \
  \
  'n/status/(-h --help)/' \
  \
  'n/retry/$_edp_steps/' \
  'n/retry/(-dr --dry-run -debug --debug -info --info -h --help)/' \
  \
  'n/graph/(-f --format -o --output -select --select -h --help)/' \
  'n/-f/(ascii dot table)/' \
  'n/--format/(ascii dot table)/' \
  'n/-o/f/' \
  'n/--output/f/' \
  \
  'n/doctor/(--strict --json -h --help)/' \
  \
  'n/flowcreate/(--tool --step --sub-steps --invoke -h --help)/' \
  'n/--tool/(pnr_innovus pv_calibre sta_pt)/' \
  'n/--step/$_edp_steps/' \
  'n/--sub-steps/$_edp_steps/' \
  'n/--invoke/(innovus calibre pt_shell)/' \
  \
  'n/tutor/(quickstart model diagnose -h --help)/'
