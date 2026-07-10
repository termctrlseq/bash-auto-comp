#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "rich>=15.0.0",
# ]
# ///

import contextlib
import os
import select
import sys
import termios
import tty
from pathlib import Path
from subprocess import PIPE, Popen, TimeoutExpired

from rich.live import Live
from rich.text import Text


class LiveMenu:
    """Bash completion menu."""

    def __init__(
        self,
        cmd_line: str,
        cmd_point: int | None = None,
        prefix: str | None = None,
        menu_height: int = 7,
    ) -> None:
        self.cmd_line = cmd_line
        self.cmd_point = len(cmd_line) if cmd_point is None else cmd_point
        self.prefix = (
            Text.from_ansi("") if prefix is None else Text.from_ansi(prefix)
        )
        self.word = ""
        self.items = []
        self.completed = False

        self.cmd_style = "color(252)"
        self.menu_style = "color(66) on color(235)"
        self.menu_sel_style = "bold magenta on color(237)"

        self.bash_completion = Path(__file__).parent / "bash_auto_comp.sh"
        self.proc = None
        self.start_process()

        self.fd = sys.stdin.fileno()
        try:
            self.menu_height = min(
                menu_height, int(os.get_terminal_size(self.fd)[1]) - 1
            )
        except OSError:
            self.menu_height = menu_height

        self.start_idx = 0
        self.stop_idx = self.start_idx + self.menu_height
        self.selected = -1

    def prepare_menu(self) -> Text:
        self.get_proc_output()

        text = self.prefix.copy()
        indent = " " * (text.cell_len + self.cmd_point - len(self.word))
        length = (
            max(
                len(line)
                for line in self.items[self.start_idx : self.stop_idx]
            )
            if self.items
            else 0
        )
        head = self.cmd_line[: self.cmd_point]
        tail = self.cmd_line[self.cmd_point :] or " "
        if self.selected != -1:
            head = head.removesuffix(self.word) + self.items[self.selected]

        text.append(
            Text.from_markup(
                f"[{self.cmd_style}]{head}[reverse]{tail[:1]}[/]{tail[1:]}[/]"
            )
        )

        if self.completed:
            self.completed = False
        else:
            for i, item in enumerate(
                self.items[self.start_idx : self.stop_idx],
                start=self.start_idx,
            ):
                if i == self.selected:
                    style = self.menu_sel_style
                else:
                    style = self.menu_style

                text.append(
                    Text.from_markup(
                        f"\n{indent}[{style}]{item:<{length}}[/]"
                    )
                )

        return text

    def get_key(self) -> str | None:
        old = termios.tcgetattr(self.fd)
        try:
            tty.setcbreak(self.fd)
            rlist = select.select([self.fd], [], [], 0.2)[0]
            if rlist:
                return os.read(self.fd, 6).decode()
        finally:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, old)

        return None

    def parse_input(self) -> tuple[int, str] | None:
        with Live(
            self.prepare_menu(), transient=True, auto_refresh=False
        ) as live:
            while True:
                key = self.get_key()

                # TAB, Down Arrow, Ctrl-n
                if key in ["\t", "\x1b[B", "\x0e"]:
                    if self.selected < len(self.items) - 1:
                        self.selected += 1
                        if self.selected > self.stop_idx - 1:
                            self.stop_idx = self.selected + 1
                            self.start_idx = self.stop_idx - self.menu_height
                    else:
                        self.selected = -1
                        self.start_idx = 0
                        self.stop_idx = self.menu_height

                # Shift-TAB, Up Arrow, Ctrl-p
                elif key in ["\x1b[Z", "\x1b[A", "\x10"]:
                    if self.selected > -1:
                        self.selected -= 1
                        if self.selected < self.start_idx:
                            self.start_idx = max(self.selected, 0)
                            self.stop_idx = self.start_idx + self.menu_height
                    else:
                        self.selected = len(self.items) - 1
                        self.stop_idx = self.selected + 1
                        self.start_idx = max(
                            0, self.stop_idx - self.menu_height
                        )

                # Enter, Escape
                elif key in ["\n", "\x1b"]:
                    if self.selected != -1:
                        head = self.cmd_line[: self.cmd_point]
                        tail = self.cmd_line[self.cmd_point :]
                        if self.word and self.items[self.selected].startswith(
                            self.word
                        ):
                            head = head.removesuffix(self.word)
                            self.cmd_point -= len(self.word)
                        head += f"{self.items[self.selected]}"
                        self.cmd_line = head + tail
                        self.cmd_point += len(self.items[self.selected])

                    return self.cmd_point, self.cmd_line

                # " " <= key <= "~":
                elif key and key.isprintable():
                    head = self.cmd_line[: self.cmd_point]
                    tail = self.cmd_line[self.cmd_point :]
                    if self.selected != -1:
                        head = (
                            head.removesuffix(self.word)
                            + self.items[self.selected]
                        )
                        self.cmd_point += len(
                            self.items[self.selected]
                        ) - len(self.word)
                        self.word = ""
                        self.selected = -1
                        self.start_idx = 0
                        self.stop_idx = self.start_idx + self.menu_height
                    else:
                        self.word = ""
                    self.cmd_line = head + key + tail
                    self.cmd_point += 1

                    self.start_process()

                # Backspace
                elif key == "\x7f":
                    if self.cmd_point <= 0:
                        return self.cmd_point, self.cmd_line

                    head = self.cmd_line[: self.cmd_point]
                    tail = self.cmd_line[self.cmd_point :]

                    if self.selected != -1:
                        # Replace word with selected item, than backtrack
                        head = (
                            head.removesuffix(self.word)
                            + self.items[self.selected]
                        )
                        self.cmd_point += len(
                            self.items[self.selected]
                        ) - len(self.word)
                        self.word = self.items[self.selected][:-1]
                        self.completed = True
                        self.selected = -1

                    elif self.word:
                        # Remove last character in word
                        self.word = self.word[:-1]

                    # Remove character before point
                    self.cmd_line = head[:-1] + tail
                    self.cmd_point -= 1

                    self.start_process()

                live.update(self.prepare_menu(), refresh=True)

    def start_process(self) -> None:
        self.items.clear()

        if self.proc is not None:
            if self.proc.poll() is None:
                try:
                    self.proc.terminate()
                    self.proc.communicate(timeout=1)
                except TimeoutExpired:
                    self.proc.kill()
                    self.proc.communicate()
            else:
                self.proc.communicate()

        self.proc = Popen(
            [self.bash_completion, self.cmd_line[: self.cmd_point]],
            stdout=PIPE,
            stderr=PIPE,
            encoding="utf-8",
        )

    def get_proc_output(self) -> None:
        if not self.items and self.proc is not None and self.proc.poll() == 0:
            with contextlib.suppress(TimeoutExpired):
                outs, _ = self.proc.communicate(timeout=1)
                out_lines = outs.splitlines()
                if len(out_lines) >= 2:
                    self.word = out_lines[0]
                    self.items = sorted(
                        set(out_lines[1:]), key=lambda x: len(x)
                    )


def main() -> None:
    if len(sys.argv) != 5:
        return

    cmd_line = sys.argv[1]
    try:
        cmd_point = int(sys.argv[2])
    except ValueError:
        return
    cmd_file = Path(sys.argv[3])
    prefix = sys.argv[4]
    result = None

    menu = LiveMenu(cmd_line=cmd_line, cmd_point=cmd_point, prefix=prefix)
    while result is None:
        menu.prepare_menu()
        result = menu.parse_input()

    cmd_point, cmd_line = result
    with cmd_file.open("w") as fd:
        fd.write(f"{cmd_point}\n{cmd_line}\n")


if __name__ == "__main__":
    main()
