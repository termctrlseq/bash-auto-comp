bash_auto_comp() {
    local mode="\[\e[1;38;5;8m\][i]\[\e[0m\]"
    local cmd_file
    local -a result
    cmd_file="$(mktemp)" || return
    trap 'rm -f "$cmd_file"' RETURN

    bash_auto_comp.py \
        "$READLINE_LINE" \
        "$READLINE_POINT" \
        "$cmd_file" \
        "${mode@P}${PS1@P}"

    if [[ -r "$cmd_file" ]]; then
        mapfile -t result <"$cmd_file"
        if ((${#result[@]} == 2)); then
            READLINE_POINT="${result[0]}"
            READLINE_LINE="${result[1]}"
        fi
    fi
}
bind -m vi-command -x '"\em": bash_auto_comp'
bind -m vi-insert -x '"\em": bash_auto_comp'

