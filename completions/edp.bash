# edp bash completion (reads from Python-generated cache, pure bash for tab)

_edp_cache_file="${EDP_ROOT:-}/.edp_completion_cache"

_edp_read_cache() {
    local key="$1"
    [[ -f "$_edp_cache_file" ]] || return
    local line
    while IFS= read -r line; do
        case "$line" in
            "${key}="*) echo "${line#*=}"; return ;;
        esac
    done < "$_edp_cache_file"
}

_edp_completions() {
    local cur prev subcmd
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # Detect subcommand
    subcmd=""
    for ((i=1; i<COMP_CWORD; i++)); do
        case "${COMP_WORDS[i]}" in
            -*) continue ;;
            init|run|status|retry|graph)
                subcmd="${COMP_WORDS[i]}"
                break
                ;;
        esac
    done

    # No subcommand yet
    if [[ -z "$subcmd" ]]; then
        COMPREPLY=($(compgen -W "init run status retry graph -h --help" -- "$cur"))
        return
    fi

    case "$subcmd" in
        init)
            case "$prev" in
                -prj|--project)
                    COMPREPLY=($(compgen -W "$(_edp_read_cache PROJECTS)" -- "$cur"))
                    return ;;
                -n|--node)
                    COMPREPLY=($(compgen -W "$(_edp_read_cache NODES)" -- "$cur"))
                    return ;;
                -ver|--version)
                    COMPREPLY=($(compgen -W "P85 P95 P100" -- "$cur"))
                    return ;;
                -w|--work-path)  compopt -o nospace -o default; COMPREPLY=(); return ;;
                -blk|--block)    compopt -o nospace; COMPREPLY=(); return ;;
                -br|--branch)    compopt -o nospace; COMPREPLY=(); return ;;
            esac
            COMPREPLY=($(compgen -W "-prj --project -w --work-path -n --node -ver --version -blk --block -br --branch --link --no-link -h --help" -- "$cur"))
            ;;
        run)
            case "$prev" in
                -fr|--from|-to)
                    COMPREPLY=($(compgen -W "$(_edp_read_cache STEPS)" -- "$cur"))
                    return ;;
                -skip)
                    COMPREPLY=($(compgen -W "$(_edp_read_cache STEPS)" -- "$cur"))
                    return ;;
                run)
                    # step 名补全（位置参数）
                    COMPREPLY=($(compgen -W "$(_edp_read_cache STEPS)" -- "$cur"))
                    return ;;
            esac
            COMPREPLY=($(compgen -W "-fr --from -to --to -skip --skip -dr --dry-run --force -debug --debug -info --info -h --help" -- "$cur"))
            ;;
        status)
            COMPREPLY=($(compgen -W "-h --help" -- "$cur"))
            ;;
        retry)
            case "$prev" in
                retry)
                    COMPREPLY=($(compgen -W "$(_edp_read_cache STEPS)" -- "$cur"))
                    return ;;
            esac
            COMPREPLY=($(compgen -W "-dr --dry-run -debug --debug -info --info -h --help" -- "$cur"))
            ;;
        graph)
            case "$prev" in
                -f|--format)    COMPREPLY=($(compgen -W "ascii dot table" -- "$cur")); return ;;
                -o|--output)    compopt -o nospace -o default; COMPREPLY=(); return ;;
            esac
            COMPREPLY=($(compgen -W "-f --format -o --output -select --select -h --help" -- "$cur"))
            ;;
    esac
}

complete -F _edp_completions edp
