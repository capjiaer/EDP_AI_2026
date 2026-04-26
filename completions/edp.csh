# edp tcsh/csh completion -- Python-driven dynamic + hybrid static
#
# Prerequisites (handled by edp.csh before sourcing this file):
#   1. EDP_ROOT/bin is in PATH (so edp_complete_helper.py is findable)
#   2. EDP_ROOT is set (for the helper to find the cache)
#
# Static lists use (...) for speed.  Dynamic values (steps, projects,
# nodes) use backtick commands -- tcsh evaluates these at Tab-press time,
# so the completion list is always fresh.

if (! $?EDP_ROOT) then
    exit
endif

# Clear old completion
uncomplete edp >& /dev/null

# ── Rules ordered: specific value patterns first, general flag patterns last.
# ── Backtick commands contain NO slashes (avoids delimiter parsing bugs).

complete edp \
  'p/1/(init run status retry graph doctor flowcreate tutor)/' \
  \
  'n/init/-prj/`edp_complete_helper.py projects`/' \
  'n/init/--project/`edp_complete_helper.py projects`/' \
  'n/init/-n/`edp_complete_helper.py nodes`/' \
  'n/init/--node/`edp_complete_helper.py nodes`/' \
  'n/init/-ver/(P85 P95 P100)/' \
  'n/init/--version/(P85 P95 P100)/' \
  'n/init/-w/d/' \
  'n/init/--work-path/d/' \
  'n/init/-blk/d/' \
  'n/init/--block/d/' \
  'n/init/(-prj --project -w --work-path -n --node -ver --version -blk --block -br --branch --link --no-link -h --help)/' \
  \
  'n/run/-fr/`edp_complete_helper.py steps`/' \
  'n/run/--from/`edp_complete_helper.py steps`/' \
  'n/run/-to/`edp_complete_helper.py steps`/' \
  'n/run/--to/`edp_complete_helper.py steps`/' \
  'n/run/-skip/`edp_complete_helper.py steps`/' \
  'n/run/--skip/`edp_complete_helper.py steps`/' \
  'n/run/`edp_complete_helper.py run_steps_and_flags`/' \
  \
  'n/status/(-h --help)/' \
  \
  'n/retry/-dr/(-h --help)/' \
  'n/retry/--dry-run/(-h --help)/' \
  'n/retry/retry/`edp_complete_helper.py steps`/' \
  'n/retry/(-dr --dry-run -debug --debug -info --info -h --help)/' \
  \
  'n/graph/-f/(ascii dot table)/' \
  'n/graph/--format/(ascii dot table)/' \
  'n/graph/-o/f/' \
  'n/graph/--output/f/' \
  'n/graph/(-f --format -o --output -select --select -h --help)/' \
  \
  'n/doctor/(--strict --json -h --help)/' \
  \
  'n/flowcreate/--tool/(pnr_innovus pv_calibre sta_pt)/' \
  'n/flowcreate/--step/`edp_complete_helper.py steps`/' \
  'n/flowcreate/--sub-steps/`edp_complete_helper.py steps`/' \
  'n/flowcreate/--invoke/(innovus calibre pt_shell)/' \
  'n/flowcreate/(--tool --step --sub-steps --invoke -h --help)/' \
  \
  'n/tutor/(quickstart model diagnose -h --help)/' \
  \
  'c/-*/(-fr --from -to --to -skip --skip -dr --dry-run --force -debug --debug -info --info --strict --json -prj --project -w --work-path -n --node -ver --version -blk --block -br --branch --link --no-link -f --format -o --output -select --select --tool --step --sub-steps --invoke -h --help)/'
