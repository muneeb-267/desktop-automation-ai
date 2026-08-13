"""PyAutoGUI wrappers — real OS mouse/keyboard/browser automation."""

from __future__ import annotations

import platform
import shutil
import subprocess
import time
import webbrowser
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus


class AutomationEngine:
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        auto = (config or {}).get("automation", {})
        self.dry_run = bool(auto.get("dry_run", False))
        self.pause_seconds = float(auto.get("pause_seconds", 0.12))
        self.type_interval = float(auto.get("type_interval", 0.02))
        self.move_duration = float(auto.get("move_duration", 0.12))
        self.post_action_delay = float(auto.get("post_action_delay", 0.25))
        self.app_launch_wait = float(auto.get("app_launch_wait", 1.4))
        self.failsafe = bool(auto.get("failsafe", True))
        self._history: List[Dict[str, Any]] = []
        self._pyautogui = None
        try:
            import pyautogui

            pyautogui.FAILSAFE = self.failsafe
            pyautogui.PAUSE = self.pause_seconds
            self._pyautogui = pyautogui
        except (Exception, SystemExit):
            self._pyautogui = None

    def set_dry_run(self, enabled: bool) -> None:
        self.dry_run = enabled
        if self._pyautogui is not None:
            self._pyautogui.PAUSE = self.pause_seconds

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
        time.sleep(self.post_action_delay if seconds is None else max(0.0, seconds))

    def move_to(self, x: int, y: int) -> Dict[str, Any]:
        entry = self._record("move_to", x=x, y=y)
        if not self.dry_run and self._pyautogui:
            self._pyautogui.moveTo(x, y, duration=self.move_duration)
        return entry

    def click(
        self, x: Optional[int] = None, y: Optional[int] = None, button: str = "left", clicks: int = 1
    ) -> Dict[str, Any]:
        entry = self._record("click", x=x, y=y, button=button, clicks=clicks)
        if not self.dry_run and self._pyautogui:
            if x is not None and y is not None:
                self._pyautogui.click(x, y, clicks=clicks, button=button, interval=0.08)
            else:
                self._pyautogui.click(clicks=clicks, button=button)
            self._sleep()
        return entry

    def double_click(self, x: Optional[int] = None, y: Optional[int] = None) -> Dict[str, Any]:
        return self.click(x=x, y=y, clicks=2)

    def type_text(self, text: str, *, paste: bool = True) -> Dict[str, Any]:
        """Type text. Uses clipboard paste for speed/unicode when possible."""
        entry = self._record("type_text", text=text, paste=paste)
        if self.dry_run or not self._pyautogui:
            return entry
        if paste and text:
            try:
                import pyperclip

                old = None
                try:
                    old = pyperclip.paste()
                except Exception:
                    old = None
                pyperclip.copy(text)
                system = platform.system().lower()
                if system == "darwin":
                    self._pyautogui.hotkey("command", "v")
                else:
                    self._pyautogui.hotkey("ctrl", "v")
                self._sleep(0.15)
                if old is not None:
                    try:
                        pyperclip.copy(old)
                    except Exception:
                        pass
                return entry
            except Exception:
                pass
        # Fallback character typing
        self._pyautogui.write(text, interval=self.type_interval)
        self._sleep()
        return entry

    def press(self, key: str) -> Dict[str, Any]:
        entry = self._record("press", key=key)
        if not self.dry_run and self._pyautogui:
            if "+" in key:
                parts = [p.strip() for p in key.split("+")]
                # Normalize common aliases
                parts = ["command" if p == "cmd" else p for p in parts]
                self._pyautogui.hotkey(*parts)
            else:
                self._pyautogui.press(key)
            self._sleep()
        return entry

    def scroll(self, direction: str = "down", amount: int = 3) -> Dict[str, Any]:
        clicks = amount * 120 if direction in ("up", "left") else -amount * 120
        # pyautogui.scroll uses "clicks" units; keep moderate values
        units = amount * 3 if direction in ("up", "left") else -amount * 3
        if direction in ("left", "right"):
            entry = self._record("hscroll", direction=direction, amount=amount)
            if not self.dry_run and self._pyautogui:
                try:
                    self._pyautogui.hscroll(units)
                except Exception:
                    self._pyautogui.scroll(units)
                self._sleep()
            return entry
        entry = self._record("scroll", direction=direction, amount=amount)
        if not self.dry_run and self._pyautogui:
            self._pyautogui.scroll(units)
            self._sleep()
        return entry

    def wait(self, seconds: float = 1.0) -> Dict[str, Any]:
        entry = self._record("wait", seconds=seconds)
        # Always wait a little even in dry-run for sequencing realism; shorter if dry
        delay = float(seconds)
        if self.dry_run:
            delay = min(delay, 0.15)
        time.sleep(max(0.0, delay))
        return entry

    def open_url(self, url: str) -> Dict[str, Any]:
        """Open a URL in the default/Chrome browser (real navigation)."""
        entry = self._record("open_url", url=url)
        if self.dry_run:
            return entry
        system = platform.system().lower()
        launched = False
        # Prefer Chrome when available for Google/search tasks
        chrome = (
            shutil.which("google-chrome")
            or shutil.which("google-chrome-stable")
            or shutil.which("chromium")
            or shutil.which("chromium-browser")
        )
        try:
            if chrome:
                subprocess.Popen([chrome, "--new-tab", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                launched = True
                entry["launched_with"] = chrome
            elif system == "windows":
                subprocess.Popen(["cmd", "/c", "start", "", url], shell=False)
                launched = True
            elif system == "darwin":
                subprocess.Popen(["open", url])
                launched = True
            else:
                subprocess.Popen(["xdg-open", url])
                launched = True
        except Exception as exc:
            entry["error"] = str(exc)
        if not launched:
            webbrowser.open(url)
            entry["launched_with"] = "webbrowser"
        self._sleep(self.app_launch_wait)
        return entry

    def search_google(self, query: str) -> Dict[str, Any]:
        """Open Google and run a search query directly."""
        q = (query or "").strip()
        url = f"https://www.google.com/search?q={quote_plus(q)}" if q else "https://www.google.com"
        entry = self._record("search_google", query=q, url=url)
        open_res = self.open_url(url)
        entry["open"] = open_res
        return entry

    def open_app(self, app: str) -> Dict[str, Any]:
        """Launch a common desktop application by friendly name."""
        app_l = (app or "").strip().lower()
        # Treat google as browser+google.com
        if app_l in ("google", "google.com"):
            return self.open_url("https://www.google.com")
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
                    if isinstance(cmd, str):
                        subprocess.Popen(cmd, shell=True)
                    else:
                        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self._sleep(self.app_launch_wait)
                entry["launched_with"] = cmd
                return entry
            except Exception as exc:
                last_error = exc
        if last_error:
            entry["error"] = str(last_error)
            raise RuntimeError(f"Could not open app '{app}': {last_error}") from last_error
        raise RuntimeError(f"Could not open app '{app}'")

    def focus_address_bar_and_search(self, query: str) -> Dict[str, Any]:
        """Focus browser address bar and search (fallback path)."""
        entry = self._record("address_bar_search", query=query)
        self.press("ctrl+l")
        self.wait(0.25)
        self.type_text(query, paste=True)
        self.press("enter")
        self.wait(0.8)
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
            "gmail": ["start https://mail.google.com"],
            "youtube": ["start https://www.youtube.com"],
        }
        chrome_bin = (
            shutil.which("google-chrome")
            or shutil.which("google-chrome-stable")
            or shutil.which("chromium")
            or shutil.which("chromium-browser")
        )
        mapping_linux = {
            "chrome": [[chrome_bin] if chrome_bin else ["google-chrome"], ["chromium"], ["firefox"]],
            "firefox": [["firefox"]],
            "notepad": [["gedit"], ["xed"], ["mousepad"], ["xed"]],
            "calculator": [["gnome-calculator"], ["kcalc"], ["galculator"]],
            "explorer": [["thunar"], ["nautilus"], ["xdg-open", os_path_home()]],
            "terminal": [["x-terminal-emulator"], ["gnome-terminal"], ["xterm"]],
            "code": [["code"]],
            "cmd": [["x-terminal-emulator"]],
            "msedge": [["microsoft-edge"], ["microsoft-edge-stable"]],
            "gmail": [[chrome_bin, "https://mail.google.com"] if chrome_bin else ["xdg-open", "https://mail.google.com"]],
            "youtube": [[chrome_bin, "https://www.youtube.com"] if chrome_bin else ["xdg-open", "https://www.youtube.com"]],
        }
        mapping_mac = {
            "chrome": [["open", "-a", "Google Chrome"]],
            "firefox": [["open", "-a", "Firefox"]],
            "notepad": [["open", "-a", "TextEdit"]],
            "calculator": [["open", "-a", "Calculator"]],
            "explorer": [["open", "."]],
            "terminal": [["open", "-a", "Terminal"]],
            "code": [["open", "-a", "Visual Studio Code"], ["code"]],
            "gmail": [["open", "https://mail.google.com"]],
            "youtube": [["open", "https://www.youtube.com"]],
        }
        if system == "windows":
            return mapping_win.get(app, [f"start {app}"])
        if system == "darwin":
            return mapping_mac.get(app, [["open", "-a", app]])
        cmds = mapping_linux.get(app)
        if not cmds:
            return [[app]]
        # Filter out None chrome paths
        cleaned = []
        for c in cmds:
            if c and c[0]:
                cleaned.append(c)
        return cleaned or [[app]]


def os_path_home() -> str:
    from pathlib import Path

    return str(Path.home())
