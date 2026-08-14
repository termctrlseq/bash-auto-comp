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

from rich.console import Console
from rich.live import Live
from rich.text import Text

console = Console()


class LiveMenu:
    """Bash completion menu."""

    def __init__(
        self,
        cmd_line: str,
        cmd_point: int | None = None,
        prefix: str | None = None,
        menu_height: int = 7,
    ) -> None:
        self._cmd_line = cmd_line
        self._cmd_point = len(cmd_line) if cmd_point is None else cmd_point
        self._prefix = (
            Text.from_ansi("") if prefix is None else Text.from_ansi(prefix)
        )
        self._word = ""
        self._items = []
        self._completed = False

        self._cmd_style = "color(252)"
        self._menu_style = "color(66) on color(235)"
        self._menu_sel_style = "bold magenta on color(237)"

        self._bash_completion = Path(__file__).parent / "bash_auto_comp.sh"
        self._proc = None
        self._start_process()

        self._fd = sys.stdin.fileno()
        try:
            self._menu_height = min(
                menu_height, int(os.get_terminal_size(self._fd)[1]) - 1
            )
        except OSError:
            self._menu_height = menu_height

        self._start_idx = 0
        self._stop_idx = self._start_idx + self._menu_height
        self._selected = -1

    def _wrap_offset(self, text: Text) -> int | None:
        lines = text.wrap(console, console.width)
        if len(lines) > 1:
            return lines[0].cell_len

        return None

    def _prepare_menu(self) -> Text:
        self._get_proc_output()

        text = self._prefix.copy()
        indent = " " * (text.cell_len + self._cmd_point - len(self._word))
        length = (
            max(
                len(line)
                for line in self._items[self._start_idx : self._stop_idx]
            )
            if self._items
            else 0
        )
        head = self._cmd_line[: self._cmd_point]
        tail = self._cmd_line[self._cmd_point :] or "┊"
        if self._selected != -1:
            head = head.removesuffix(self._word) + self._items[self._selected]

        text.append(
            Text.from_markup(
                f"[{self._cmd_style}]{head}[reverse]{tail[:1]}[/]{tail[1:]}[/]"
            )
        )

        if offset := self._wrap_offset(text.copy()):
            indent = indent[offset:]

        if self._completed:
            self._completed = False
        else:
            for i, item in enumerate(
                self._items[self._start_idx : self._stop_idx],
                start=self._start_idx,
            ):
                if i == self._selected:
                    style = self._menu_sel_style
                else:
                    style = self._menu_style

                text.append(
                    Text.from_markup(
                        f"\n{indent}[{style}]{item:<{length}}[/]"
                    )
                )

        return text

    def _get_key(self) -> str | None:
        old = termios.tcgetattr(self._fd)
        try:
            tty.setcbreak(self._fd)
            rlist = select.select([self._fd], [], [], 0.2)[0]
            if rlist:
                return os.read(self._fd, 6).decode()
        finally:
            termios.tcsetattr(self._fd, termios.TCSADRAIN, old)

        return None

    def _parse_input(self) -> tuple[int, str] | None:
        key = self._get_key()

        # TAB, Down Arrow, Ctrl-n
        if key in ["\t", "\x1b[B", "\x0e"]:
            if self._selected < len(self._items) - 1:
                self._selected += 1
                if self._selected > self._stop_idx - 1:
                    self._stop_idx = self._selected + 1
                    self._start_idx = self._stop_idx - self._menu_height
            else:
                self._selected = -1
                self._start_idx = 0
                self._stop_idx = self._menu_height

        # Shift-TAB, Up Arrow, Ctrl-p
        elif key in ["\x1b[Z", "\x1b[A", "\x10"]:
            if self._selected > -1:
                self._selected -= 1
                if self._selected < self._start_idx:
                    self._start_idx = max(self._selected, 0)
                    self._stop_idx = self._start_idx + self._menu_height
            else:
                self._selected = len(self._items) - 1
                self._stop_idx = self._selected + 1
                self._start_idx = max(0, self._stop_idx - self._menu_height)

        # Enter, Escape, Ctrl-d
        elif key in ["\n", "\x1b", "\x04"]:
            if self._selected != -1:
                head = self._cmd_line[: self._cmd_point]
                tail = self._cmd_line[self._cmd_point :]
                if self._word and self._items[self._selected].startswith(
                    self._word
                ):
                    head = head.removesuffix(self._word)
                    self._cmd_point -= len(self._word)
                head += f"{self._items[self._selected]}"
                self._cmd_line = head + tail
                self._cmd_point += len(self._items[self._selected])

            return self._cmd_point, self._cmd_line

        # " " <= key <= "~":
        elif key and key.isprintable():
            head = self._cmd_line[: self._cmd_point]
            tail = self._cmd_line[self._cmd_point :]
            if self._selected != -1:
                head = (
                    head.removesuffix(self._word)
                    + self._items[self._selected]
                )
                self._cmd_point += len(self._items[self._selected]) - len(
                    self._word
                )
                self._word = ""
                self._selected = -1
                self._start_idx = 0
                self._stop_idx = self._start_idx + self._menu_height
            else:
                self._word = ""
            self._cmd_line = head + key + tail
            self._cmd_point += 1

            self._start_process()

        # Backspace
        elif key == "\x7f":
            if self._cmd_point <= 0:
                return self._cmd_point, self._cmd_line

            head = self._cmd_line[: self._cmd_point]
            tail = self._cmd_line[self._cmd_point :]

            if self._selected != -1:
                # Replace word with selected item, than backtrack
                head = (
                    head.removesuffix(self._word)
                    + self._items[self._selected]
                )
                self._cmd_point += len(self._items[self._selected]) - len(
                    self._word
                )
                self._word = self._items[self._selected]
                self._completed = True
                self._selected = -1

            if self._word:
                # Remove last character in word
                self._word = self._word[:-1]

            # Remove character before point
            self._cmd_line = head[:-1] + tail
            self._cmd_point -= 1

            self._start_process()

        return None

    def display_menu(self) -> tuple[int, str]:
        with Live(
            self._prepare_menu(), transient=True, auto_refresh=False
        ) as live:
            while True:
                if result := self._parse_input():
                    return result

                live.update(self._prepare_menu(), refresh=True)

    def _start_process(self) -> None:
        self._items.clear()

        if self._proc is not None:
            if self._proc.poll() is None:
                try:
                    self._proc.terminate()
                    self._proc.communicate(timeout=1)
                except TimeoutExpired:
                    self._proc.kill()
                    self._proc.communicate()
            else:
                self._proc.communicate()

        self._proc = Popen(
            [self._bash_completion, self._cmd_line[: self._cmd_point]],
            stdout=PIPE,
            stderr=PIPE,
            encoding="utf-8",
        )

    def _get_proc_output(self) -> None:
        if (
            not self._items
            and self._proc is not None
            and self._proc.poll() == 0
        ):
            with contextlib.suppress(TimeoutExpired):
                outs, _ = self._proc.communicate(timeout=1)
                out_lines = outs.splitlines()
                if len(out_lines) >= 2:
                    self._word = out_lines[0]
                    self._items = sorted(
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

    menu = LiveMenu(cmd_line=cmd_line, cmd_point=cmd_point, prefix=prefix)
    result = menu.display_menu()

    cmd_point, cmd_line = result
    with cmd_file.open("w") as fd:
        fd.write(f"{cmd_point}\n{cmd_line}\n")


if __name__ == "__main__":
    main()
