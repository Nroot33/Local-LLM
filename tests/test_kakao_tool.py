import unittest
from unittest.mock import patch

from local_agent import execute_tool, parse_kakao_send_request, tool_definitions
from kakao_tools import _show_kakao_from_tray, resolve_kakao_recipient, send_kakao_message


class KakaoToolTests(unittest.IsolatedAsyncioTestCase):
    def test_tray_app_is_reopened(self):
        with patch("kakao_tools._main_window", side_effect=[None, object()]) as main, patch("kakao_tools.subprocess.Popen") as launch:
            self.assertIsNotNone(_show_kakao_from_tray())
            launch.assert_called_once()

    def test_room_name_request_parses(self):
        self.assertEqual(parse_kakao_send_request('월평 방에 "AI 자동화 테스트중입니다." 라고 카톡보내'), {"recipient": "월평", "message": "AI 자동화 테스트중입니다."})

    def test_aliases_resolve_to_exact_room(self):
        for alias in ("혭", "와이프"):
            self.assertEqual(resolve_kakao_recipient(alias), "💡✨❤️")
            self.assertEqual(parse_kakao_send_request(f'{alias}에게 카톡으로 "안녕" 보내'), {"recipient": "💡✨❤️", "message": "안녕"})

    def test_alias_is_resolved_before_room_lookup(self):
        room = type("Room", (), {"title": "💡✨❤️", "_hWnd": 1})()
        with patch("kakao_tools._open_matching_chat", return_value=room) as lookup, patch("kakao_tools._focus_window"), patch("kakao_tools.Desktop") as desktop, patch("kakao_tools.keyboard_type"), patch("kakao_tools.pyautogui.press"), patch("kakao_tools.time.sleep"):
            editor = desktop.return_value.window.return_value
            editor.class_name.return_value = "RICHEDIT"
            editor.window_text.side_effect = ["", "안녕", "안녕", ""]
            editor.descendants.return_value = [editor]
            send_kakao_message({"recipient": "와이프", "message": "안녕"})
            lookup.assert_called_once_with("💡✨❤️")

    async def test_user_words_override_model_arguments(self):
        request = '💡✨❤️ 에게 카톡으로 "이것은 AI가 보내는 자동 메시지 입니다. " 라고 보내'
        with patch("local_agent.send_kakao_message", return_value={"ok": True}) as sender:
            result, _ = await execute_tool("send_kakao_message", {"recipient": "다른방", "message": "변경된 문구"}, request, "", False, True, False)
            self.assertTrue(result["ok"])
            sender.assert_called_once_with({"recipient": "💡✨❤️", "message": "이것은 AI가 보내는 자동 메시지 입니다. "})

    async def test_remote_client_cannot_send(self):
        names = {tool["function"]["name"] for tool in tool_definitions(False, False)}
        self.assertNotIn("send_kakao_message", names)
        result, _ = await execute_tool("send_kakao_message", {"recipient": "누군가", "message": "안녕"}, "보내줘", "", False, False, False)
        self.assertFalse(result["ok"])
