#!/bin/csh
# Source this file to add edp CLI to your PATH
# Usage: source edp.csh

set edp_root = `dirname $0`
set edp_root = `cd "$edp_root" && pwd`

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
