#!/bin/tcsh
# Source this file to add edp CLI to your PATH
# Usage: From EDP_ROOT directory: source edp.csh

# Set EDP_ROOT to script's directory (assuming script is in EDP_ROOT)
setenv EDP_ROOT "/home/zero/EDP_AI_2026"

# PATH: add EDP bin to PATH
setenv PATH "${EDP_ROOT}/bin:${PATH}"

# PYTHONPATH: add EDP packages to PYTHONPATH
set py_path = "${EDP_ROOT}/packages"
if ( $?PYTHONPATH ) then
    setenv PYTHONPATH "${py_path}:${PYTHONPATH}"
else
    setenv PYTHONPATH "${py_path}"
endif

# Generate wrapper only if missing
if ( ! -x "${EDP_ROOT}/bin/edp" ) then
    if ( ! -d "${EDP_ROOT}/bin" ) mkdir -p "${EDP_ROOT}/bin"
    # Write wrapper script safely
    cat >! "${EDP_ROOT}/bin/edp" << 'WRAPPER_EOF'
#!/bin/bash
EDP_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export EDP_ROOT
export PYTHONPATH="${EDP_ROOT}/packages${PYTHONPATH:+:$PYTHONPATH}"
exec "${PYTHON:-python3}" -m edp "$@"
WRAPPER_EOF
    chmod +x "${EDP_ROOT}/bin/edp"
endif

# Generate completion cache (for bash and Python helper)
if ( $?PYTHON ) then
    set _edp_python = "$PYTHON"
else
    set _edp_python = "python3"
endif
"$_edp_python" "${EDP_ROOT}/bin/_gen_completion_cache.py" >& /dev/null
unset _edp_python
	# ── tcsh tab completion ──────────────────────────────────────────
	#
	# Architecture notes (2026-04-26):
	#
	# tcsh's `complete` builtin uses declarative pattern rules — no
	# callback functions like bash's `complete -F`.  Key limitations:
	#
	#   1. No list display: custom `complete` rules cycle through
	#      matches one at a time per Tab press. `autolist` only
	#      works for file/variable completions, not custom rules.
	#      Bash-style "Tab shows all candidates" is not attainable.
	#
	#   2. "Invalid completion" conflict: a word that appears both
	#      as a completion value AND as a 3-part pattern trigger
	#      (e.g. `n/init/-prj/(projects)/`) causes tcsh to reject
	#      the completion.  Fix: use 2-part `n/-prj/(…)` rules
	#      without subcommand context.  Safe because EDP flag names
	#      are globally unique across subcommands.
	#
	#   3. Backtick commands (`...`) are evaluated at Tab-press
	#      time in 2-part `n` rules, but silently ignored in 3-part
	#      `n` rules.  Use `$var` list type for dynamic data
	#      (populated from cache at source time).
	#
	#   4. Variables in `$var` list type are frozen at `complete`
	#      definition time.  Acceptable since projects/nodes/steps
	#      rarely change within a shell session.
	#
	# Future ideas if tcsh gets better completion support:
	#   - Replace `$var` with backtick commands for true dynamism
	#   - Use `$COMMAND_LINE` env var (if tcsh sets it) for context
	#   - Explore `complete=enhance` or `listchoices` variants
	#
	# See also: completions/edp.csh (rules), bin/edp_complete_helper.py
	#
	# ────────────────────────────────────────────────────────────────

	set autolist
	set listmaxrows=20

	# Load tcsh completion (cache -> completion rules)
	if ( -f "${EDP_ROOT}/.edp_completion_cache.csh" ) then
	    source "${EDP_ROOT}/.edp_completion_cache.csh"
	endif
	if ( -f "${EDP_ROOT}/completions/edp.csh" ) then
	    source "${EDP_ROOT}/completions/edp.csh"
	endif

# ls color support and useful aliases
alias ls 'ls --color=auto'
alias ll 'ls -l --color=auto'
alias la 'ls -a --color=auto'
alias lla 'ls -la --color=auto'
alias lt 'ls -lt --color=auto'
alias ltr 'ls -ltr --color=auto'
alias l  'ls -CF --color=auto'
