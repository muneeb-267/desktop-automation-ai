"""PyAutoGUI wrappers with dry-run safety and cross-platform app launch."""

from __future__ import annotations

import platform
import subprocess
import time
from typing import Any, Dict, List, Optional


class AutomationEngine:
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        auto = (config or {}).get("automation", {})
        self.dry_run = bool(auto.get("dry_run", True))
        self.pause_seconds = float(auto.get("pause_seconds", 0.35))
        self.type_interval = float(auto.get("type_interval", 0.04))
        self.move_duration = float(auto.get("move_duration", 0.25))
        self.post_action_delay = float(auto.get("post_action_delay", 0.4))
        self.failsafe = bool(auto.get("failsafe", True))
        self._history: List[Dict[str, Any]] = []
        self._pyautogui = None
        try:
            import pyautogui

            pyautogui.FAILSAFE = self.failsafe
            pyautogui.PAUSE = self.pause_seconds
            self._pyautogui = pyautogui
        except (Exception, SystemExit):
            # Missing tkinter/scrot on some Linux images — dry-run still works.
            self._pyautogui = None

    def set_dry_run(self, enabled: bool) -> None:
        self.dry_run = enabled

    @property
    def history(self) -> List[Dict[str, Any]]:
        return list(self._history)

    def clear_history(self) -> None:
        self._history.clear()

    def _record(self, action: str, **kwargs: Any) -> Dict[str, Any]:
        entry = {"action": action, "dry_run": self.dry_run, **kwargs}
        self._history.append(entry)
        return entry

    def _sleep(self, seconds: Optional[float] = None) -> None:
        time.sleep(self.post_action_delay if seconds is None else seconds)

    def move_to(self, x: int, y: int) -> Dict[str, Any]:
        entry = self._record("move_to", x=x, y=y)
        if not self.dry_run and self._pyautogui:
            self._pyautogui.moveTo(x, y, duration=self.move_duration)
        return entry

    def click(self, x: Optional[int] = None, y: Optional[int] = None, button: str = "left") -> Dict[str, Any]:
        entry = self._record("click", x=x, y=y, button=button)
        if not self.dry_run and self._pyautogui:
            if x is not None and y is not None:
                self._pyautogui.click(x, y, button=button)
            else:
                self._pyautogui.click(button=button)
            self._sleep()
        return entry

    def type_text(self, text: str) -> Dict[str, Any]:
        entry = self._record("type_text", text=text)
        if not self.dry_run and self._pyautogui:
            self._pyautogui.write(text, interval=self.type_interval)
            self._sleep()
        return entry

    def press(self, key: str) -> Dict[str, Any]:
        entry = self._record("press", key=key)
        if not self.dry_run and self._pyautogui:
            if "+" in key:
                parts = [p.strip() for p in key.split("+")]
                self._pyautogui.hotkey(*parts)
            else:
                self._pyautogui.press(key)
            self._sleep()
        return entry

    def scroll(self, direction: str = "down", amount: int = 3) -> Dict[str, Any]:
        clicks = amount if direction in ("up", "left") else -amount
        if direction in ("left", "right"):
            entry = self._record("hscroll", direction=direction, amount=amount)
            if not self.dry_run and self._pyautogui:
                try:
                    self._pyautogui.hscroll(clicks)
                except Exception:
                    self._pyautogui.scroll(clicks)
                self._sleep()
            return entry
        entry = self._record("scroll", direction=direction, amount=amount)
        if not self.dry_run and self._pyautogui:
            self._pyautogui.scroll(clicks)
            self._sleep()
        return entry

    def wait(self, seconds: float = 1.0) -> Dict[str, Any]:
        entry = self._record("wait", seconds=seconds)
        if not self.dry_run:
            time.sleep(max(0.0, float(seconds)))
        return entry

    def open_app(self, app: str) -> Dict[str, Any]:
        """Launch a common desktop application by friendly name."""
        app_l = (app or "").strip().lower()
        system = platform.system().lower()
        commands = self._resolve_launch_command(app_l, system)
        entry = self._record("open_app", app=app_l, commands=commands, system=system)
        if self.dry_run:
            return entry
        last_error: Optional[Exception] = None
        for cmd in commands:
            try:
                if system == "windows":
                    subprocess.Popen(cmd, shell=True)
                else:
                    subprocess.Popen(cmd, shell=False)
                self._sleep(0.8)
                entry["launched_with"] = cmd
                return entry
            except Exception as exc:  # try next candidate
                last_error = exc
        if last_error:
            entry["error"] = str(last_error)
            raise RuntimeError(f"Could not open app '{app}': {last_error}") from last_error
        return entry

    def _resolve_launch_command(self, app: str, system: str) -> List[Any]:
        mapping_win = {
            "chrome": ["start chrome", "start msedge"],
            "msedge": ["start msedge"],
            "firefox": ["start firefox"],
            "notepad": ["notepad"],
            "calculator": ["calc"],
            "explorer": ["explorer"],
            "cmd": ["start cmd"],
            "code": ["code"],
            "terminal": ["start wt", "start cmd"],
        }
        mapping_linux = {
            "chrome": [["google-chrome"], ["chromium-browser"], ["chromium"], ["google-chrome-stable"]],
            "firefox": [["firefox"]],
            "notepad": [["gedit"], ["xed"], ["mousepad"], ["nano"]],
            "calculator": [["gnome-calculator"], ["kcalc"], ["galculator"]],
            "explorer": [["nautilus"], ["thunar"], ["xdg-open", "."]],
            "terminal": [["x-terminal-emulator"], ["gnome-terminal"], ["xterm"]],
            "code": [["code"]],
            "cmd": [["x-terminal-emulator"]],
            "msedge": [["microsoft-edge"], ["microsoft-edge-stable"]],
        }
        mapping_mac = {
            "chrome": [['open', '-a', 'Google Chrome']],
            "firefox": [['open', '-a', 'Firefox']],
            "notepad": [['open', '-a', 'TextEdit']],
            "calculator": [['open', '-a', 'Calculator']],
            "explorer": [['open', '.']],
            "terminal": [['open', '-a', 'Terminal']],
            "code": [['open', '-a', 'Visual Studio Code'], ["code"]],
        }
        if system == "windows":
            cmds = mapping_win.get(app, [f"start {app}"])
            return cmds
        if system == "darwin":
            return mapping_mac.get(app, [["open", "-a", app]])
        # linux / other
        return mapping_linux.get(app, [[app]])
