import html
import re
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer


CAPABILITIES_MARKDOWN = """# 천둥감자가 할 수 있는 일

로컬 PC에서 실행되는 천둥감자의 현재 기능을 간략히 정리했습니다.

## 대화와 글쓰기
- 한국어로 질문에 답하고, 글의 초안 작성·요약·문장 다듬기를 돕습니다.
- 서버에 저장된 사용자 기본 지침과 현재 대화의 최근 내용을 참고합니다.

## 웹 검색과 이미지
- 웹 검색을 켠 텍스트 질문은 Tavily 검색 결과를 참고해 답합니다. 검색이 실패하면 최신 정보는 확인되지 않았다고 알립니다.
- 사진과 문제 이미지를 읽고 설명하거나 답을 제시합니다. 작은 로컬 모델이라 OCR과 추론 결과는 틀릴 수 있습니다.

## PC 파일 만들기
- 로컬 모델이 파일 도구를 선택해 바탕화면 또는 문서 폴더에 HTML, CSS, JS, TXT 등 새 텍스트 파일을 만듭니다.
- PDF, Word(DOCX), Markdown, TXT 문서를 바탕화면에 새 파일로 저장할 수 있습니다.
- 지정된 폴더의 텍스트 파일을 읽고 파일 목록을 확인할 수 있습니다.
- 이 PC에서 요청하면 현재 Windows 사용자 권한으로 명령을 실행하거나 GUI 앱을 열 수 있습니다. 관리자 권한을 자동으로 얻지는 않습니다.
- 현재 열린 앱 화면을 로컬 비전 모델로 확인하고, 마우스 클릭·스크롤·키보드 단축키·한글 입력을 할 수 있습니다.
- 파일 생성 전용 도구는 기존 파일을 덮어쓰지 않습니다. 프로그램 실행 도구의 동작은 실행한 프로그램에 따라 달라집니다.

## 사용 방법
이 PC의 천둥감자 웹페이지에서 작업과 저장 위치·파일 형식을 구체적으로 적어 주세요. 예: “바탕화면에 한 페이지짜리 PDF로 요약해줘.”
"""


def requested_format(message: str) -> str | None:
    if "바탕화면" not in message or not re.search(r"만들|생성|작성|저장|파일로", message):
        return None
    if re.search(r"\.pdf\b|\bPDF\b|피디에프", message, re.I):
        return "pdf"
    if re.search(r"\.docx\b|\bDOCX\b|워드", message, re.I):
        return "docx"
    if re.search(r"\.md\b|\bMD\b|마크다운", message, re.I):
        return "md"
    if re.search(r"\.txt\b|\bTXT\b|텍스트\s*파일", message, re.I):
        return "txt"
    if "문서" in message:
        return "docx"
    return None


def asks_about_capabilities(message: str) -> bool:
    return bool(re.search(r"할\s*수\s*있는\s*일|가능한\s*기능|무슨\s*일을\s*할\s*수", message))


def _document_lines(markdown: str):
    for raw_line in markdown.replace("\r\n", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            yield "space", ""
        elif line.startswith("# "):
            yield "title", line[2:].strip()
        elif line.startswith("## "):
            yield "heading", line[3:].strip()
        elif line.startswith("- "):
            yield "bullet", line[2:].strip()
        else:
            yield "body", re.sub(r"^\d+[.)]\s*", "", line)


def _plain(text: str) -> str:
    return re.sub(r"\*\*(.*?)\*\*", r"\1", text)


def _pdf_text(text: str) -> str:
    return re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", html.escape(text))


def _pdf_styles():
    font_path = Path(r"C:\Windows\Fonts\malgun.ttf")
    bold_path = Path(r"C:\Windows\Fonts\malgunbd.ttf")
    if not font_path.exists():
        raise ValueError("PDF용 한글 글꼴을 찾지 못했습니다.")
    if "Malgun" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("Malgun", str(font_path)))
        pdfmetrics.registerFont(TTFont("MalgunBold", str(bold_path if bold_path.exists() else font_path)))
        pdfmetrics.registerFontFamily("Malgun", normal="Malgun", bold="MalgunBold")
    return {
        "title": ParagraphStyle("PotatoTitle", fontName="MalgunBold", fontSize=22, leading=30, textColor=colors.HexColor("#183A27"), spaceAfter=9 * mm),
        "heading": ParagraphStyle("PotatoHeading", fontName="MalgunBold", fontSize=12.5, leading=18, textColor=colors.HexColor("#276745"), spaceBefore=5 * mm, spaceAfter=2 * mm),
        "body": ParagraphStyle("PotatoBody", fontName="Malgun", fontSize=9.5, leading=16, textColor=colors.HexColor("#263A2C"), alignment=TA_LEFT, spaceAfter=2 * mm),
        "bullet": ParagraphStyle("PotatoBullet", fontName="Malgun", fontSize=9.2, leading=15, textColor=colors.HexColor("#263A2C"), leftIndent=6 * mm, firstLineIndent=-3 * mm, spaceAfter=1.7 * mm),
    }


def _draw_page(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setFillColor(colors.HexColor("#A9EC78"))
    canvas.rect(0, height - 7 * mm, width, 7 * mm, fill=1, stroke=0)
    canvas.setStrokeColor(colors.HexColor("#D6E6D7"))
    canvas.line(20 * mm, 18 * mm, width - 20 * mm, 18 * mm)
    canvas.setFont("Malgun", 8)
    canvas.setFillColor(colors.HexColor("#718475"))
    canvas.drawString(20 * mm, 12 * mm, "천둥감자  |  로컬 문서")
    canvas.drawRightString(width - 20 * mm, 12 * mm, str(doc.page))
    canvas.restoreState()


def _write_pdf(path: Path, markdown: str) -> None:
    styles = _pdf_styles()
    story = []
    for kind, text in _document_lines(markdown):
        if kind == "space":
            if story:
                story.append(Spacer(1, 1.4 * mm))
        elif kind == "bullet":
            story.append(Paragraph("•  " + _pdf_text(text), styles[kind]))
        else:
            story.append(Paragraph(_pdf_text(text), styles[kind]))
    document = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=22 * mm, bottomMargin=25 * mm)
    document.build(story, onFirstPage=_draw_page, onLaterPages=_draw_page)
    if not PdfReader(str(path)).pages:
        raise ValueError("PDF 페이지가 생성되지 않았습니다.")


def _write_docx(path: Path, markdown: str) -> None:
    document = Document()
    section = document.sections[0]
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(2.2)
    section.left_margin = Cm(2.3)
    section.right_margin = Cm(2.3)
    for style_name in ("Normal", "Title", "Heading 1", "List Bullet"):
        style = document.styles[style_name]
        style.font.name = "맑은 고딕"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "맑은 고딕")
    document.styles["Normal"].font.size = Pt(10.5)
    document.styles["Normal"].paragraph_format.space_after = Pt(7)
    document.styles["Title"].font.size = Pt(22)
    document.styles["Title"].font.color.rgb = RGBColor(24, 58, 39)
    document.styles["Heading 1"].font.size = Pt(13)
    document.styles["Heading 1"].font.color.rgb = RGBColor(39, 103, 69)
    for kind, text in _document_lines(markdown):
        if kind == "space":
            continue
        if kind == "title":
            document.add_paragraph(_plain(text), style="Title")
        elif kind == "heading":
            document.add_paragraph(_plain(text), style="Heading 1")
        elif kind == "bullet":
            document.add_paragraph(_plain(text), style="List Bullet")
        else:
            document.add_paragraph(_plain(text))
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    footer.add_run("천둥감자 | 로컬 문서")
    document.save(str(path))


def save_document(markdown: str, file_format: str, capabilities: bool = False) -> Path:
    if not markdown.strip() or len(markdown) > 60000:
        raise ValueError("문서 내용이 비어 있거나 너무 깁니다.")
    desktop = Path.home() / "Desktop"
    stem = "천둥감자-할-수-있는-일" if capabilities else f"천둥감자-문서-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    path = desktop / f"{stem}.{file_format}"
    suffix = 2
    while path.exists():
        path = desktop / f"{stem}-{suffix}.{file_format}"
        suffix += 1
    if file_format == "pdf":
        _write_pdf(path, markdown)
    elif file_format == "docx":
        _write_docx(path, markdown)
    elif file_format == "md":
        path.write_text(markdown, encoding="utf-8")
    elif file_format == "txt":
        path.write_text("\n".join(_plain(text) for _, text in _document_lines(markdown)), encoding="utf-8")
    else:
        raise ValueError("지원하지 않는 문서 형식입니다.")
    return path
