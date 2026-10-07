#!/usr/bin/env bash

warn() {
    printf '\033[1;33mWarnig:\033[0m %s\n' "$*"
}

die() {
    printf '\033[1;31mError:\033[0m %s\n' "$*"
    exit 1
}

install_bash_auto_comp() {
    declare install_path="${HOME}/.local/bin/" bash_auto_comp_py='./bash_auto_comp.py' bash_auto_comp_sh='./auto-bash-completion/bash_auto_comp.sh'
    [[ -n $1 ]] && install_path="$1"

    [[ -r $bash_auto_comp_py ]] || die "'${bash_auto_comp_py}' not found"
    [[ -r $bash_auto_comp_sh ]] || die "'${bash_auto_comp_sh}' not found"
    [[ -d $install_path ]] || die "'${install_path} does not exist"
    [[ ":${PATH}:" != *:"$install_path":* ]] && warn "'${install_path}' not in PATH"

    cp --target-directory="$install_path" "$bash_auto_comp_py" "$bash_auto_comp_sh"

}

install_bash_auto_comp "$@"

