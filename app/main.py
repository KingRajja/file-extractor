from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from typing import Optional
from pathlib import Path
import io
import chardet
import subprocess, tempfile, os, shutil  # ДОБАВИЛИ shutil для which()
from striprtf.striprtf import rtf_to_text  # для RTF-пути

# PDF
from pdfminer.high_level import extract_text as pdf_extract_text
# DOCX
from docx import Document

app = FastAPI(title="File Text Extractor", version="1.0.0")

# Разрешим CORS (удобно для фронта/тестов)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

def _looks_like_rtf(data: bytes) -> bool:
    # RTF начинается с "{\rtf" в ASCII
    head = data[:20].lstrip()
    return head.startswith(b"{\\rtf") or head.upper().startswith(b"{\\RTF")

def _decode_bytes_guess(data: bytes) -> str:
    # Пробуем угадать кодировку и декодировать
    guess = chardet.detect(data or b"")
    enc = guess.get("encoding") or "utf-8"
    try:
        return data.decode(enc, errors="strict")
    except Exception:
        return data.decode("utf-8", errors="ignore")

def _extract_text_from_docx(data: bytes) -> str:
    with io.BytesIO(data) as bio:
        doc = Document(bio)
        return "\n".join(p.text for p in doc.paragraphs)

def _extract_text_from_pdf(data: bytes) -> str:
    with io.BytesIO(data) as bio:
        return pdf_extract_text(bio) or ""

def _extract_text_from_doc_soft(data: bytes) -> str:
    """
    Мягкая поддержка .doc:
      1) Если это RTF — распарсим rtf_to_text (без системных пакетов).
      2) Если бинарный .doc — попытаемся использовать antiword, но только если он стоит.
    """
    # 1) .doc, который на самом деле RTF
    if _looks_like_rtf(data):
        try:
            return rtf_to_text(data.decode("latin1", errors="ignore"))
        except Exception:
            # запасной путь — просто вернуть «как есть» (не упадём)
            return data.decode("utf-8", errors="ignore")

    # 2) Настоящий бинарный .doc — мягко пробуем antiword, если он есть в системе
    antiword_path = shutil.which("antiword")
    if antiword_path:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".doc")
        try:
            tmp.write(data)
            tmp.flush()
            tmp.close()
            result = subprocess.run(
                [antiword_path, "-m", "UTF-8.txt", tmp.name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=20
            )
            if result.returncode == 0:
                return result.stdout.decode("utf-8", errors="ignore")
            # antiword не справился — отдаём «как есть», чтобы не падать
            return data.decode("utf-8", errors="ignore")
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    # 3) antiword не установлен — мягко деградируем: попытаемся угадать текст
    # (чаще всего получится нечитаемо, но сервис не упадёт)
    return data.decode("utf-8", errors="ignore")

def extract_text(data: bytes, filename: str, content_type: Optional[str]) -> str:
    ext = Path(filename).suffix.lower().lstrip(".")
    # Текстовые форматы
    if ext in {"txt", "csv", "md", "log"}:
        return _decode_bytes_guess(data)
    # DOCX
    if ext == "docx":
        return _extract_text_from_docx(data)
    # PDF
    if ext == "pdf":
        return _extract_text_from_pdf(data)
    
    if ext == "doc":                                
        return _extract_text_from_doc_soft(data)
    # Если пришёл любой text/* — тоже попробуем
    if (content_type or "").startswith("text/"):
        return _decode_bytes_guess(data)
    # Фолбэк: пытаемся декодировать как UTF-8 (игнорируя ошибки)
    return data.decode("utf-8", errors="ignore")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/extract")
async def extract(file: UploadFile = File(...)):
    # Базовые проверки
    name = file.filename or "uploaded_file"
    ext = Path(name).suffix.lower().lstrip(".")
    content_type = file.content_type

    # Читаем байты с ограничением размера
    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large (> {MAX_FILE_SIZE//1024//1024}MB)")

    try:
        text = extract_text(data, name, content_type)
    except Exception as e:
        # Возвращаем понятную ошибку, но без лишних внутренностей
        raise HTTPException(status_code=422, detail=f"Failed to extract text: {type(e).__name__}")

    return JSONResponse(
        {
            "filename": name,
            "extension": ext,
            "content_type": content_type,
            "text": text,
            "size_bytes": len(data),
        }
    )
