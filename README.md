# 천둥감자 🥔⚡

내 PC에서 쓰려고 만든 Qwen 데스크톱 앱입니다. 대화는 Ollama로 돌리고, 필요할 때 사진을 읽거나 웹을 검색합니다. 파일 작성과 PC 조작도 대화창에서 요청할 수 있습니다.

화면은 Vue, 서버는 FastAPI로 만들었습니다. Tavily 키를 설정하면 웹 검색에 사용하고, 음성 답변은 별도로 설치한 MeloTTS로 생성합니다.

## Windows에서 실행하기

먼저 [Ollama](https://ollama.com/)를 설치하고 사용할 모델을 받습니다.

```powershell
ollama pull qwen3:8b
ollama pull qwen3-vl:4b-instruct
```

이 폴더에서 의존성을 설치하고 실행 파일을 만듭니다. Python과 Node.js가 필요합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-desktop.txt
New-Item personal-instructions.txt -ItemType File -ErrorAction SilentlyContinue
cd web
npm ci
npm run build
cd ..
.\build-desktop.ps1
.\dist\천둥감자.exe
```

`personal-instructions.txt`에는 원하는 답변 방식을 적으면 됩니다. 개인 설정과 API 키는 GitHub에 올리지 않습니다. MeloTTS 음성을 쓰려면 별도 Python 환경에 MeloTTS를 설치해야 합니다.

이 앱은 개인 PC에서 사용하도록 만들었습니다. PC 조작 기능은 현재 로그인한 Windows 사용자 권한으로 실행됩니다.
