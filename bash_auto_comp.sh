#!/usr/bin/env bash
#
# Derived from the bash-completion function _comp_command_offset()
# with modifications for use as an auto-completion source.
# Last Change:  2026-01-26
# License:      GNU General Public License version 2 or later
#
# #######################################################################
#
# bash_completion - programmable completion functions for bash 4.2+
#
# Copyright © 2006-2008, Ian Macdonald <ian@caliban.org>
#           © 2009-2020, Bash Completion Maintainers
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# The latest version of this software can be obtained here:
#
# https://github.com/scop/bash-completion
#
# #######################################################################
#
# Return completion candidates for typed line
#
#   Arguments:
#              typed line
#   Returns:
#            line  #1:   word being completed
#            lines #2+:  completion candidates (one per line)
#
# shellcheck disable=SC2155

auto_complete() {
    (($# == 1)) || return
    if ! command -v _comp_compgen; then
        source /usr/share/bash-completion/bash_completion || return
    fi

    COMP_LINE="$1"
    COMP_POINT="${#1}"
    read -ra COMP_WORDS <<<"$COMP_LINE"
    ((COMP_CWORD = ${#COMP_WORDS[@]} - 1))

    # Start of a copied part of _comp_command_offset() function
    COMPREPLY=()
    local cur
    _comp_get_words cur || return # MODIFIED: return on failure

    if ((COMP_CWORD == 0)); then
        _comp_compgen_commands 2>/dev/null # MODIFIED: ignore errors
    else
        _comp_dequote "${COMP_WORDS[0]}"
        local cmd=${REPLY-} compcmd=${REPLY-}
        local cspec=$(complete -p -- "$cmd" 2>/dev/null)

        # If we have no completion for $cmd yet, see if we have for basename
        if [[ ! $cspec && $cmd == */* ]]; then
            cspec=$(complete -p -- "${cmd##*/}" 2>/dev/null)
            [[ $cspec ]] && compcmd=${cmd##*/}
        fi
        # If still nothing, just load it for the basename
        if [[ ! $cspec ]]; then
            compcmd=${cmd##*/}
            _comp_load -D -- "$compcmd"
            cspec=$(complete -p -- "$compcmd" 2>/dev/null)
        fi

        local retry_count=0
        while true; do # loop for the retry request by status 124
            local args original_cur=${comp_args[1]-$cur}
            if ((${#COMP_WORDS[@]} >= 2)); then
                args=("$cmd" "$original_cur" "${COMP_WORDS[-2]}")
            else
                args=("$cmd" "$original_cur")
            fi

            if [[ ! $cspec ]]; then
                if ((${#COMPREPLY[@]} == 0)); then
                    # XXX will probably never happen as long as completion loader loads
                    #     *something* for every command thrown at it ($cspec != empty)
                    _comp_complete_minimal "${args[@]}"
                fi
            elif [[ $cspec == *\ -[CF]\ * ]]; then
                if [[ $cspec == *' -F '* ]]; then
                    # complete -F <function>

                    # get function name
                    local func=${cspec#* -F }
                    func=${func%% *}
                    $func "${args[@]}" 2>/dev/null # MODIFIED: ignore errors

                    # restart completion (once) if function exited with 124
                    if (($? == 124 && retry_count++ == 0)); then
                        # Note: When the completion function returns 124, the
                        # state of COMPREPLY is discarded.
                        COMPREPLY=()

                        cspec=$(complete -p -- "$compcmd" 2>/dev/null)

                        # Note: When completion spec is removed after 124, we
                        # do not generate any completions including the default
                        # ones. This is the behavior of the original Bash
                        # progcomp.
                        [[ $cspec ]] || break

                        continue
                    fi
                else
                    # complete -C <command>

                    # get command name
                    local completer=${cspec#* -C \'}

                    # completer commands are always single-quoted
                    if ! _comp_dequote "'$completer"; then
                        _minimal "${args[@]}" 2>/dev/null # MODIFIED: ignore errors
                        break
                    fi
                    completer=${REPLY[0]}

                    local -a suggestions

                    local IFS=$' \t\n'
                    local reset_monitor=$(shopt -po monitor) reset_lastpipe=$(shopt -p lastpipe) reset_noglob=$(shopt -po noglob)
                    set +o monitor
                    shopt -s lastpipe
                    set -o noglob

                    COMP_KEY="$COMP_KEY" COMP_LINE="$COMP_LINE" \
                        COMP_POINT="$COMP_POINT" COMP_TYPE="$COMP_TYPE" \
                        $completer "${args[@]}" | mapfile -t suggestions

                    $reset_monitor
                    $reset_lastpipe
                    $reset_noglob
                    _comp_unlocal IFS

                    local suggestion
                    local i=0
                    COMPREPLY=()
                    for suggestion in "${suggestions[@]}"; do
                        COMPREPLY[i]+=${COMPREPLY[i]+$'\n'}$suggestion

                        if [[ $suggestion != *\\ ]]; then
                            ((i++))
                        fi
                    done
                fi

                # MODIFIED: no need to restore compopts
                # restore initial compopts
                # local opt
                # while [[ $cspec == *" -o "* ]]; do
                #     # FIXME: should we take "+o opt" into account?
                #     cspec=${cspec#*-o }
                #     opt=${cspec%% *}
                #     compopt -o "$opt"
                #     cspec=${cspec#"$opt"}
                # done
            else
                cspec=${cspec#complete}
                cspec=${cspec%%@("$compcmd"|"'${compcmd//\'/\'\\\'\'}'")}
                eval "_comp_compgen -- $cspec"
            fi
            break
        done
    fi
    # End of a copied part

    if ((${#COMPREPLY[@]} == 0)); then
        mapfile -t COMPREPLY < <(compgen -f "$cur")
    fi

    printf '%s\n' "$cur" "${COMPREPLY[@]}"
}
auto_complete "$1"

