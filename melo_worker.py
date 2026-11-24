"""로컬 MeloTTS 음성 생성 서버."""

import tempfile
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


_model = None
_model_lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_error(404)
            return
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        if self.path != "/synthesize":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 < length <= 6000:
            self.send_error(400, "invalid text length")
            return
        text = self.rfile.read(length).decode("utf-8").strip()
        if not text:
            self.send_error(400, "empty text")
            return
        try:
            global _model
            with _model_lock:
                if _model is None:
                    from melo.api import TTS
                    _model = TTS(language="KR", device="cpu")
                speaker = _model.hps.data.spk2id["KR"]
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "speech.wav"
                    _model.tts_to_file(text, speaker, str(path), speed=1.0)
                    audio = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(audio)))
            self.end_headers()
            self.wfile.write(audio)
        except Exception as exc:
            traceback.print_exc()
            self.send_error(500, "speech synthesis failed")

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8766), Handler).serve_forever()
