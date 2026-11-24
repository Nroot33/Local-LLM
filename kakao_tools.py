import time
import os
import subprocess
from pathlib import Path

import pyautogui
import pygetwindow
import win32con
import win32gui
from pywinauto import Desktop

from gui_tools import keyboard_type

KAKAO_RECIPIENT_ALIASES = {"혭": "💡✨❤️", "와이프": "💡✨❤️"}


def resolve_kakao_recipient(recipient: str) -> str:
    name = recipient.strip()
    return KAKAO_RECIPIENT_ALIASES.get(name, name)


def _chat_window(recipient: str):
    for window in pygetwindow.getAllWindows():
        if window.title == recipient and window.width > 200 and window.height > 200:
            return window
    return None


def _main_window():
    return next((window for window in pygetwindow.getAllWindows() if window.title == "카카오톡"), None)


def _show_kakao_from_tray():
    main = _main_window()
    if main:
        return main
    candidates = [Path(base) / "Kakao" / "KakaoTalk" / "KakaoTalk.exe"
                  for base in (os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)"), os.environ.get("LOCALAPPDATA")) if base]
    executable = next((path for path in candidates if path.is_file()), None)
    if executable is None:
        raise ValueError("카카오톡 실행 파일을 찾지 못했습니다.")
    # 트레이에만 남은 단일 인스턴스를 다시 표시한다.
    subprocess.Popen([str(executable)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(30):
        main = _main_window()
        if main:
            return main
        time.sleep(0.2)
    raise ValueError("카카오톡이 트레이에서 기본 창을 다시 표시하지 않았습니다.")


def _focus_window(window):
    if win32gui.GetForegroundWindow() == window._hWnd:
        return
    try:
        window.activate()
    except Exception:
        pass
    if win32gui.GetForegroundWindow() == window._hWnd:
        return
    was_topmost = bool(win32gui.GetWindowLong(window._hWnd, win32con.GWL_EXSTYLE) & win32con.WS_EX_TOPMOST)
    try:
        win32gui.SetWindowPos(window._hWnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        pyautogui.click(window.left + min(130, window.width // 2), window.top + 40)
        time.sleep(0.15)
    finally:
        if not was_topmost:
            win32gui.SetWindowPos(window._hWnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
    if win32gui.GetForegroundWindow() != window._hWnd:
        raise ValueError("다른 앱이 화면 입력을 점유하여 카카오톡을 활성화하지 못했습니다.")


def _open_matching_chat(recipient: str):
    existing = _chat_window(recipient)
    if existing:
        return existing
    main = _show_kakao_from_tray()
    if any("LockModeView" in item.window_text() for item in Desktop(backend="uia").window(handle=main._hWnd).descendants()):
        raise ValueError("카카오톡이 잠금 모드입니다. 잠금 해제 후 다시 요청해 주세요. 메시지는 보내지 않았습니다.")
    _focus_window(main)
    time.sleep(0.25)
    # 채팅 목록 상단의 검색 버튼을 누르고 검색어를 확정한다.
    pyautogui.click(main.left + main.width - 110, main.top + 56)
    search = Desktop(backend="win32").window(handle=main._hWnd)
    fields = [item for item in search.descendants() if item.friendly_class_name() == "Edit" and 75 <= item.rectangle().top - main.top <= 125]
    if not fields:
        raise ValueError("카카오톡 검색 입력칸을 찾지 못했습니다.")
    fields[0].set_edit_text(recipient)
    fields[0].set_focus()
    pyautogui.press("enter")
    time.sleep(0.5)
    # 후보가 여러 개여도 제목이 완전히 같은 대화창만 사용한다.
    for row in range(5):
        pyautogui.doubleClick(main.left + min(main.width - 100, 170), main.top + 165 + row * 72, interval=0.12)
        time.sleep(0.3)
        matched = _chat_window(recipient)
        if matched:
            return matched
    raise ValueError("검색 결과에서 이름이 정확히 일치하는 대화방을 찾지 못했습니다. 메시지는 보내지 않았습니다.")


def send_kakao_message(arguments: dict) -> dict:
    recipient = arguments.get("recipient")
    message = arguments.get("message")
    if not isinstance(recipient, str) or not recipient.strip() or len(recipient) > 100:
        raise ValueError("받는 사람의 대화방 이름이 올바르지 않습니다.")
    if not isinstance(message, str) or not message.strip() or len(message) > 1000:
        raise ValueError("보낼 메시지가 비어 있거나 너무 깁니다.")
    recipient = resolve_kakao_recipient(recipient)
    window = _open_matching_chat(recipient)
    if window.title != recipient:
        raise ValueError("대화방 이름이 일치하지 않아 전송하지 않았습니다.")
    _focus_window(window)
    chat = Desktop(backend="win32").window(handle=window._hWnd)
    editors = [item for item in chat.descendants() if "RICHEDIT" in item.class_name().upper()]
    if len(editors) != 1:
        raise ValueError("카카오톡 메시지 입력칸을 특정하지 못했습니다.")
    editor = editors[0]
    current = editor.window_text()
    if current.strip() not in ("", "메시지 입력") and current != message:
        raise ValueError("대화방에 작성 중인 문구가 있어 덮어쓰지 않았습니다.")
    editor.set_focus()
    if current != message:
        keyboard_type({"text": message})
    for _ in range(10):
        if editor.window_text() == message:
            break
        time.sleep(0.1)
    if editor.window_text() != message:
        raise ValueError("메시지가 입력칸에 정확히 입력되지 않아 전송하지 않았습니다.")
    pyautogui.press("enter")
    time.sleep(0.45)
    if editor.window_text().strip() not in ("", "메시지 입력"):
        raise ValueError("전송 뒤 입력칸이 비워지지 않아 전송 성공을 확인하지 못했습니다.")
    return {"ok": True, "recipient": recipient, "message": message, "confirmation": "대화방 제목 일치 및 전송 뒤 입력칸 비움"}
