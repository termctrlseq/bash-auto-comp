# Bash Auto Completion

An interactive completion menu for Bash that appears directly on the command line.

Instead of repeatedly pressing `Tab` to cycle or list completions, this project lets you browse completion candidates in an interactive terminal interface while keeping your current command line visible.

The project uses Bash's existing programmable completion system as its completion source—it does **not** implement its own completion logic.

## Why?

Bash already provides excellent command-line editing through Readline, as well as the ability to edit the current command in a full-featured editor (`v` in vi mode or <kbd>Ctrl</kbd>+<kbd>X</kbd>, <kbd>Ctrl</kbd>+<kbd>E</kbd> in emacs mode).

This project explores a workflow that fits between those two approaches.

It is intended for situations where a command is becoming long enough that you need to browse completion candidates several times, but opening an external editor feels unnecessary. It can also be useful when your editor does not provide the same shell completion experience as Bash itself.

The goal is not to replace Readline or external-editor workflows, but to provide another tool for the cases in between.

## Experimental Status

This project is currently experimental.

Its primary purpose is to explore an alternative completion workflow using Bash's existing completion infrastructure. While it is usable, there are still limitations imposed by Readline that affect the user experience.

Feedback, ideas, and experimentation are welcome.

## Requirements

* Bash
* Perl
* Python **3.13+**
* **uv**
* **bash-completion**

`uv` is used to run `bash_auto_comp.py` and automatically install its Python dependencies declared in the script.

`bash-completion` is required because the project uses the standard Bash completion functions as the source of completion candidates.

## Installation

Copy the project files to a directory in your `PATH`, for example:

```bash
mkdir -p ~/.local/bin
cp bash_auto_comp.py bash_auto_comp.sh ~/.local/bin/
chmod +x ~/.local/bin/bash_auto_comp.py
```

Add the following to your `~/.bashrc`:

```bash
bash_auto_comp() {
    local mode="" prompt cmd_file
    local -a result
    # Optional: prepend a vi-mode indicator (for show-mode-in-prompt users).
    # See console_codes(4): ECMA-48 Select Graphic Rendition
    # and          bash(1): PROMPTING
    # mode="\[\e[1;38;5;8m\][i]\[\e[0m\]" # Uncomment and customize.
    prompt="${mode}$(perl -pe 's/\\\[\\e\].*?\\\]//g' <<<"${PS1}")"
    cmd_file="$(mktemp)" || return
    trap 'rm -f "$cmd_file"' RETURN

    bash_auto_comp.py     \
        "$READLINE_LINE"  \
        "$READLINE_POINT" \
        "$cmd_file"       \
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
```

Reload your shell:

```bash
source ~/.bashrc
```

## Usage

Press **Alt+M** to open the completion menu.

The default configuration enables the key binding in:

* vi command mode
* vi insert mode
* emacs mode

You can change the activation key by modifying the `bind` commands in your `.bashrc`.

## Optional Prompt Indicator

The wrapper includes an optional `mode` variable that can be used to display a custom prompt indicator while the completion menu is active.

By default it is disabled:

```bash
local mode=""
```

For example:

```bash
mode="\[\e[1;38;5;8m\][i]\[\e[0m\]"
```

Customize it however you like, or leave it empty.

## How It Works

When invoked, the Bash wrapper passes the following information to `bash_auto_comp.py`:

* the current command line (`READLINE_LINE`)
* the current cursor position (`READLINE_POINT`)
* a temporary output file
* the expanded shell prompt

The Python program queries Bash's programmable completion system, presents the available completion candidates in an interactive terminal interface, and writes the updated command line and cursor position back to the temporary file.

The wrapper then updates `READLINE_LINE` and `READLINE_POINT`, allowing editing to continue seamlessly from the selected completion.

## Known Limitations

* The completion interface is currently exited using **Esc**.
* **Enter cannot currently be used to accept a completion.** While the completion interface is active, Readline handles the Enter key in a way that makes this difficult to integrate cleanly.

## License

See the LICENSE file for licensing information.
