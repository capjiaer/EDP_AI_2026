#!/bin/bash
# Source this file to add edp CLI to your PATH
# Usage: source edp.sh

EDP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export EDP_ROOT

# PATH: only add if not already there
[[ ":$PATH:" != *":${EDP_ROOT}/bin:"* ]] \
    && export PATH="${EDP_ROOT}/bin:${PATH}"

# PYTHONPATH: only add if not already there
[[ ":$PYTHONPATH:" != *":${EDP_ROOT}/packages:"* ]] \
    && export PYTHONPATH="${EDP_ROOT}/packages${PYTHONPATH:+:$PYTHONPATH}"

# Generate wrapper only if missing
if [[ ! -x "${EDP_ROOT}/bin/edp" ]]; then
    mkdir -p "${EDP_ROOT}/bin"
    cat > "${EDP_ROOT}/bin/edp" <<'WRAPPER'
#!/bin/bash
EDP_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export EDP_ROOT
export PYTHONPATH="${EDP_ROOT}/packages${PYTHONPATH:+:$PYTHONPATH}"
exec "${PYTHON:-python}" -m edp "$@"
WRAPPER
    chmod +x "${EDP_ROOT}/bin/edp"
fi

# Generate completion cache (runs Python once, then pure bash for tab)
"${PYTHON:-python}" "${EDP_ROOT}/bin/_gen_completion_cache.py" 2>/dev/null

# Tab completion (pure bash, reads from cache file)
complete -r edp 2>/dev/null
source "${EDP_ROOT}/completions/edp.bash" 2>/dev/null
