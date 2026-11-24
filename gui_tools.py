import base64
import ctypes
import io

import httpx
import pyautogui


pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.12


def screen_size() -> dict:
    size = pyautogui.size()
    return {"width": size.width, "height": size.height}


async def inspect_screen(question: str, vision_model: str, ollama_url: str) -> dict:
    # 화면은 로컬 비전 모델에만 전달한다.
    image = pyautogui.screenshot()
    width, height = image.size
    image.thumbnail((1600, 1000))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    prompt = (
        f"이 이미지는 PC 화면이다. 원본 화면 크기는 {width}x{height}px, 전달한 이미지 크기는 {image.width}x{image.height}px이다. "
        "사용자의 질문에 한국어로 답하라. 보이는 앱과 주요 요소를 설명하고, 클릭할 대상을 물었다면 원본 화면 좌표 (x,y)를 제시하라. "
        "이미지에 보이지 않는 것은 추측하지 마라. 질문: " + (question or "현재 화면을 설명해줘")[:500]
    )
    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(
            f"{ollama_url}/api/chat",
            json={"model": vision_model, "stream": False, "think": False, "options": {"num_predict": 700},
                  "messages": [{"role": "user", "content": prompt, "images": [encoded]}]},
        )
        response.raise_for_status()
    return {"ok": True, "width": width, "height": height,
            "description": response.json()["message"].get("content", "").strip()[:5000]}


def _coordinates(x: int, y: int) -> tuple[int, int]:
    size = pyautogui.size()
    if type(x) is not int or type(y) is not int or not 0 <= x < size.width or not 0 <= y < size.height:
        raise ValueError("화면 좌표가 올바르지 않습니다.")
    return x, y


def mouse_click(arguments: dict) -> dict:
    x, y = _coordinates(arguments.get("x"), arguments.get("y"))
    button = arguments.get("button", "left")
    clicks = arguments.get("clicks", 1)
    if button not in ("left", "right", "middle") or type(clicks) is not int or clicks not in (1, 2):
        raise ValueError("마우스 클릭 옵션이 올바르지 않습니다.")
    pyautogui.click(x, y, clicks=clicks, interval=0.15, button=button)
    return {"ok": True, "x": x, "y": y, "button": button, "clicks": clicks}


def mouse_scroll(arguments: dict) -> dict:
    amount = arguments.get("amount")
    if type(amount) is not int or not -20 <= amount <= 20:
        raise ValueError("스크롤 양은 -20~20이어야 합니다.")
    pyautogui.scroll(amount)
    return {"ok": True, "amount": amount}


def keyboard_press(arguments: dict) -> dict:
    keys = arguments.get("keys")
    if not isinstance(keys, list) or not 1 <= len(keys) <= 4 or any(not isinstance(key, str) or key.lower() not in pyautogui.KEYBOARD_KEYS for key in keys):
        raise ValueError("키 이름이 올바르지 않습니다.")
    pyautogui.hotkey(*(key.lower() for key in keys))
    return {"ok": True, "keys": keys}


class _KeyInput(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.c_size_t)]


class _InputUnion(ctypes.Union):
    _fields_ = [("ki", _KeyInput), ("padding", ctypes.c_byte * 32)]


class _Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("data", _InputUnion)]


def keyboard_type(arguments: dict) -> dict:
    value = arguments.get("text")
    if not isinstance(value, str) or not value or len(value) > 4000:
        raise ValueError("입력할 글자는 1~4000자여야 합니다.")
    user32 = ctypes.windll.user32
    user32.SendInput.argtypes = (ctypes.c_uint, ctypes.POINTER(_Input), ctypes.c_int)
    user32.SendInput.restype = ctypes.c_uint
    encoded = value.encode("utf-16-le")
    for offset in range(0, len(encoded), 2):
        unit = int.from_bytes(encoded[offset:offset + 2], "little")
        events = (_Input * 2)()
        events[0].type = events[1].type = 1
        events[0].data.ki = _KeyInput(0, unit, 0x0004, 0, 0)
        events[1].data.ki = _KeyInput(0, unit, 0x0004 | 0x0002, 0, 0)
        if user32.SendInput(2, events, ctypes.sizeof(_Input)) != 2:
            raise OSError("키보드 입력을 전달하지 못했습니다.")
    return {"ok": True, "characters": len(value)}
