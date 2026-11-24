"""천둥감자 Windows 데스크톱 실행 프로그램."""

import ctypes
import logging
import os
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path



APP_URL = "http://127.0.0.1:8000/"
OLLAMA_URL = "http://127.0.0.1:11434/api/tags"
DATA_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "ThunderPotato"
ROOT = Path(__file__).resolve().parent
CHAT_WINDOW = None


def _available(url: str, timeout: float = 2) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def _ollama_executable() -> str | None:
    installed = shutil.which("ollama.exe")
    if installed:
        return installed
    candidate = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
    return str(candidate) if candidate.is_file() else None


def _ensure_ollama() -> None:
    if _available(OLLAMA_URL):
        return
    executable = _ollama_executable()
    if not executable:
        raise RuntimeError("Ollama가 설치되어 있지 않습니다.")
    logfile = (DATA_DIR / "ollama-desktop.log").open("ab")
    subprocess.Popen([executable, "serve"], stdin=subprocess.DEVNULL, stdout=logfile,
                     stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    logfile.close()
    for _ in range(40):
        if _available(OLLAMA_URL):
            return
        time.sleep(0.5)
    raise RuntimeError("Ollama가 시작되지 않았습니다. 로그를 확인해 주세요.")


def _load_tavily_key() -> None:
    if os.environ.get("TAVILY_API_KEY"):
        return
    key_file = DATA_DIR / "tavily-key.xml"
    if not key_file.is_file():
        return
    script = (
        "$s=Import-Clixml -LiteralPath $env:THUNDER_POTATO_KEY_FILE; "
        "$p=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($s); "
        "try {[Console]::Out.Write([Runtime.InteropServices.Marshal]::PtrToStringBSTR($p))} "
        "finally {[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($p)}"
    )
    env = {**os.environ, "THUNDER_POTATO_KEY_FILE": str(key_file)}
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                            capture_output=True, text=True, env=env, timeout=10,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=False)
    if result.returncode == 0 and result.stdout.strip():
        os.environ["TAVILY_API_KEY"] = result.stdout.strip()
    else:
        logging.warning("저장된 Tavily 키를 읽지 못했습니다.")


def _prepare_local_data() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    instructions = DATA_DIR / "personal-instructions.txt"
    if not instructions.exists():
        bundled = ROOT / "personal-instructions.txt"
        if bundled.is_file():
            shutil.copyfile(bundled, instructions)
    os.environ["THUNDER_POTATO_INSTRUCTIONS_FILE"] = str(instructions)
    _load_tavily_key()


def _start_backend():
    if _available(APP_URL):
        return None
    import uvicorn
    from app import app as api

    server = uvicorn.Server(uvicorn.Config(api, host="127.0.0.1", port=8000, log_level="warning",
                                           access_log=False, log_config=None))
    threading.Thread(target=server.run, name="ThunderPotatoAPI", daemon=True).start()
    for _ in range(60):
        if _available(APP_URL):
            return server
        time.sleep(0.25)
    raise RuntimeError("천둥감자 서버를 시작하지 못했습니다.")


def _show_error(message: str) -> None:
    logging.exception(message)
    ctypes.windll.user32.MessageBoxW(0, message, "천둥감자 실행 오류", 0x10)


class DesktopControls:
    def minimize(self) -> bool:
        CHAT_WINDOW.minimize()
        return True

    def close(self) -> bool:
        CHAT_WINDOW.destroy()
        return True


def main() -> None:
    global CHAT_WINDOW
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=DATA_DIR / "desktop.log", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s", encoding="utf-8")
    server = None
    try:
        _prepare_local_data()
        _ensure_ollama()
        server = _start_backend()
        import webview
        screen_width = ctypes.windll.user32.GetSystemMetrics(0)
        screen_height = ctypes.windll.user32.GetSystemMetrics(1)
        status_width = 420
        status_height = 200
        chat_width = min(490, screen_width - 40)
        chat_height = min(730, screen_height - 70)
        left = max(20, screen_width - chat_width - 24)
        top = max(20, screen_height - chat_height - 32)
        if top < status_height + 42 and screen_width >= chat_width + status_width + 72:
            left = screen_width - chat_width - status_width - 52
        controls = DesktopControls()
        chat_window = webview.create_window("천둥감자", APP_URL + "?desktop=1&pet=1", width=chat_width,
                              height=chat_height, x=left, y=top, js_api=controls,
                              min_size=(420, 560), resizable=False, frameless=True,
                              easy_drag=False, on_top=True, background_color="#f7f2e7")
        CHAT_WINDOW = chat_window
        status_window = webview.create_window("천둥감자 상태", APP_URL + "desktop-status", width=status_width,
                              height=status_height, x=max(0, screen_width - status_width - 20), y=20,
                              resizable=False, frameless=True, easy_drag=False, shadow=False,
                              focus=False, on_top=True, transparent=False,
                              background_color="#e7f7cf")
        chat_window.events.closed += status_window.destroy
        webview.start(gui="edgechromium", private_mode=False,
                      storage_path=str(DATA_DIR / "webview"), debug=False)
    except Exception as exc:
        _show_error(f"천둥감자를 시작하지 못했습니다.\n{exc}\n\n로그: {DATA_DIR / 'desktop.log'}")
    finally:
        if server is not None:
            server.should_exit = True


if __name__ == "__main__":
    main()
