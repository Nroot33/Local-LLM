import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from local_agent import run_local_agent, run_program, should_think, verify_saved_file


class VerificationTests(unittest.TestCase):
    def test_thinking_depends_on_request(self):
        self.assertFalse(should_think("안녕"))
        self.assertFalse(should_think("메모장 열어줘"))
        self.assertTrue(should_think("이 수학 문제를 계산해서 검증해줘"))
        self.assertTrue(should_think("바탕화면에 게임 로그인 HTML 파일 만들어줘"))

    def test_failed_command_is_not_reported_as_success(self):
        result = run_program({"program": "cmd.exe", "arguments": ["/c", "exit", "7"]})
        self.assertFalse(result["ok"])
        self.assertEqual(result["exit_code"], 7)

    def test_saved_file_is_read_back(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "answer.txt"
            path.write_text("정답", encoding="utf-8")
            self.assertTrue(verify_saved_file(str(path), "정답")["ok"])
            self.assertFalse(verify_saved_file(str(path), "오답")["ok"])
            self.assertFalse(verify_saved_file(str(path.with_name("missing.txt")))["ok"])


class ThinkingRequestTests(unittest.IsolatedAsyncioTestCase):
    async def test_ollama_receives_selected_thinking_mode(self):
        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"message": {"content": "확인했습니다."}}

        class FakeClient:
            def __init__(self, *args, **kwargs):
                self.requests = []

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def post(self, url, json):
                modes.append(json["think"])
                return FakeResponse()

        modes = []
        with patch("local_agent.httpx.AsyncClient", FakeClient):
            await run_local_agent("안녕", [], "", False, False, "qwen3:8b", "http://localhost", "")
            await run_local_agent("이 문제의 원인을 분석해줘", [], "", False, False, "qwen3:8b", "http://localhost", "")
        self.assertEqual(modes, [False, True])

    async def test_screen_is_checked_after_mouse_action(self):
        responses = iter([
            {"message": {"content": "", "tool_calls": [{"function": {"name": "inspect_screen", "arguments": {"question": "버튼 위치"}}}]}},
            {"message": {"content": "", "tool_calls": [{"function": {"name": "mouse_click", "arguments": {"x": 100, "y": 100}}}]}},
            {"message": {"content": "완료"}},
        ])

        class FakeResponse:
            def __init__(self, data):
                self.data = data

            def raise_for_status(self):
                pass

            def json(self):
                return self.data

        class FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def post(self, url, json):
                return FakeResponse(next(responses))

        tool_results = iter([({"ok": True, "description": "버튼이 보임"}, None), ({"ok": True, "x": 100, "y": 100}, None)])
        async def fake_tool(*args, **kwargs):
            return next(tool_results)

        with patch("local_agent.httpx.AsyncClient", FakeClient), patch("local_agent.execute_tool", side_effect=fake_tool), patch("local_agent.inspect_screen", new_callable=AsyncMock, return_value={"ok": True, "description": "버튼을 누른 뒤 새 화면이 보임"}) as check:
            result = await run_local_agent("화면의 버튼을 클릭해", [], "", False, True, "qwen3:8b", "http://localhost", "")
        self.assertTrue(result["screen_rechecked"])
        self.assertIn("새 화면", result["answer"])
        check.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
