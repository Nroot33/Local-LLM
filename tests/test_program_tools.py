import unittest
from pathlib import Path
from unittest.mock import patch

from local_agent import open_putty_session, resolve_program, run_program, search_in_browser, tool_definitions


class ProgramToolTests(unittest.TestCase):
    def test_hidden_command_returns_output(self):
        result = run_program({"program": "cmd.exe", "arguments": ["/c", "echo", "LOCAL_TOOL_OK"]})
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("LOCAL_TOOL_OK", result["stdout"])

    def test_remote_client_has_no_program_tool(self):
        names = {tool["function"]["name"] for tool in tool_definitions(False, False)}
        self.assertNotIn("run_program", names)
        self.assertNotIn("launch_application", names)
        self.assertNotIn("open_putty_session", names)
        self.assertNotIn("search_in_browser", names)

    def test_registered_apps_are_resolved(self):
        self.assertTrue(resolve_program("chrome.exe").lower().endswith("chrome.exe"))
        self.assertTrue(resolve_program("putty.exe").lower().endswith("putty.exe"))
        self.assertTrue(Path(resolve_program("카카오톡")).is_file())

    @patch("local_agent.launch_application", return_value={"ok": True, "pid": 123})
    @patch("local_agent._putty_sessions", return_value=["네이버클라우드서버", "다른서버"])
    def test_putty_session_uses_saved_name(self, _sessions, launch):
        result = open_putty_session({"session": "네이버클라우드"})
        self.assertEqual(result["session"], "네이버클라우드서버")
        launch.assert_called_once_with({"program": "putty.exe", "arguments": ["-load", "네이버클라우드서버"]})

    @patch("local_agent.launch_application", return_value={"ok": True, "pid": 123})
    def test_browser_search_opens_query_url(self, launch):
        result = search_in_browser({"query": "가을"})
        self.assertEqual(result["query"], "가을")
        self.assertIn("%EA%B0%80%EC%9D%84", launch.call_args.args[0]["arguments"][0])


if __name__ == "__main__":
    unittest.main()
