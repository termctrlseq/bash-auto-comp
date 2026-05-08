bash_menu_comp() {
    local mode="\[\e[1;38;5;8m\][i]\[\e[0m\]"
    local cmd_file result
    cmd_file="$(mktemp)"

    bash_completion.py \
        "$READLINE_LINE" \
        "$READLINE_POINT" \
        "$cmd_file" \
        "${mode@P}${PS1@P}"

    if [[ -r "$cmd_file" ]]; then
        mapfile -t result <"$cmd_file"
        rm -f "$cmd_file"
        if ((${#result[@]} == 2)); then
            READLINE_POINT="${result[0]}"
            READLINE_LINE="${result[1]}"
        fi
    fi
}
bind -m vi-insert -x '"\em": bash_menu_comp'

