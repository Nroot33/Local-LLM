import base64
import copy
import unittest
from unittest.mock import patch

from starlette.requests import Request

import app as backend


class ImageThinkingTests(unittest.IsolatedAsyncioTestCase):
    async def test_math_retries_without_thinking_after_length_limit(self):
        calls = []

        class FakeResponse:
            def __init__(self, payload):
                self.payload = payload

            def raise_for_status(self):
                pass

            def json(self):
                return self.payload

        class FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def post(self, url, json):
                calls.append(copy.deepcopy(json))
                if len(calls) == 1:
                    return FakeResponse({"message": {"content": "x+1=2. x의 값을 구하시오."}})
                if len(calls) == 2:
                    return FakeResponse({"done_reason": "length", "message": {"content": ""}})
                return FakeResponse({"done_reason": "stop", "message": {"content": "1"}})

        image = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"test").decode("ascii")
        request = backend.ChatRequest(message="정답만 알려줘", image=image)
        http_request = Request({"type": "http", "client": ("127.0.0.1", 12345), "headers": []})
        with patch("app.httpx.AsyncClient", FakeClient), patch("app.load_personal_instructions", return_value=""):
            result = await backend.chat(request, http_request)
        self.assertEqual(result["answer"], "1")
        self.assertEqual([call["think"] for call in calls], [False, True, False])
        self.assertEqual([call.get("options", {}).get("num_predict") for call in calls], [None, 1536, 256])


if __name__ == "__main__":
    unittest.main()
