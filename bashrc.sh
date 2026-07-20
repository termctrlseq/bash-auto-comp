bash_auto_comp() {
    local mode="" prompt cmd_file
    local -a result
    # Optional: prepend a vi-mode indicator (for show-mode-in-prompt users).
    # See console_codes(4) § ECMA-48 Select Graphic Rendition
    # and          bash(1) § PROMPTING
    # mode="\[\e[1;38;5;8m\][i]\[\e[0m\]" # Uncomment and customize.
    prompt="${mode}$(perl -pe 's/\\\[\\e\].*?\\\]//g' <<<"${PS1}")"
    cmd_file="$(mktemp)" || return
    trap 'rm -f "$cmd_file"' RETURN

    bash_auto_comp.py \
        "$READLINE_LINE" \
        "$READLINE_POINT" \
        "$cmd_file" \
        "${prompt@P}"

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
bind -m emacs -x '"\em": bash_auto_comp'

