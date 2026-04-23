#!/bin/csh
# Source this file to add edp CLI to your PATH
# Usage: source edp.csh

set edp_root = `dirname $0`
set edp_root = `cd "$edp_root" && pwd`
setenv EDP_ROOT "$edp_root"

# PATH
echo $PATH | grep -q "${edp_root}/bin" || setenv PATH "${edp_root}/bin:$PATH"

# PYTHONPATH
setenv PYTHONPATH "${edp_root}/packages${PYTHONPATH:+:$PYTHONPATH}"

# Generate wrapper only if missing
if ( ! -x "${edp_root}/bin/edp" ) then
    if ( ! -d "${edp_root}/bin" ) mkdir -p "${edp_root}/bin"
    cat >! "${edp_root}/bin/edp" <<'WRAPPER'
#!/bin/bash
EDP_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="${EDP_ROOT}/packages${PYTHONPATH:+:$PYTHONPATH}"
exec "${PYTHON:-python}" -m edp "$@"
WRAPPER
    chmod +x "${edp_root}/bin/edp"
endif

# Generate completion cache (same source as bash completion)
if ( $?PYTHON ) then
    set _edp_python = "$PYTHON"
else
    set _edp_python = "python"
endif
"$_edp_python" "${edp_root}/bin/_gen_completion_cache.py" >& /dev/null
unset _edp_python

# tcsh/csh completion
if ( -f "${edp_root}/completions/edp.csh" ) then
    source "${edp_root}/completions/edp.csh"
endif
