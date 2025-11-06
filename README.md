````markdown
# 🧩 File Extractor API

Простой микросервис на **Python + FastAPI**, который принимает файл и возвращает:
- имя файла  
- расширение  
- MIME-тип  
- размер в байтах  
- извлечённый текст из содержимого  

Поддерживаются форматы: `.txt`, `.md`, `.csv`, `.log`, `.pdf`, `.docx`, `.doc`.

---

## 🚀 Быстрый старт

### 1. Сборка Docker-образа
```bash
docker build -t file-extractor:latest .
````

### 2. Запуск контейнера

```bash
docker run --rm -p 8080:8000 file-extractor:latest
```

Сервис будет доступен по адресу:
👉 [http://localhost:8080](http://localhost:8080)

Документация Swagger UI:
👉 [http://localhost:8080/docs](http://localhost:8080/docs)

---

## 📤 Примеры запросов

### cURL

```bash
# Текстовый файл
curl -s -X POST http://localhost:8080/extract \
  -F "file=@/path/to/file.txt"

# PDF
curl -s -X POST http://localhost:8080/extract \
  -F "file=@/path/to/file.pdf"

# DOCX
curl -s -X POST http://localhost:8080/extract \
  -F "file=@/path/to/file.docx"
```

---

## 🧠 Пример запроса из TypeScript

```ts
type ExtractResponse = {
  filename: string;
  extension: string;
  content_type: string | null;
  text: string;
  size_bytes: number;
};

async function uploadFile(file: File): Promise<ExtractResponse> {
  const form = new FormData();
  form.append("file", file, file.name);

  const res = await fetch("http://localhost:8080/extract", {
    method: "POST",
    body: form,
    // CORS уже разрешён в FastAPI, заголовки тут не нужны
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Upload failed: ${res.status} ${errText}`);
  }

  return (await res.json()) as ExtractResponse;
}
```

---

## 📦 Формат ответа

```json
{
  "filename": "report.pdf",
  "extension": "pdf",
  "content_type": "application/pdf",
  "text": "…извлечённый текст…",
  "size_bytes": 123456
}
```

---

## ⚙️ Поддерживаемые форматы

| Расширение                    | Описание           | Библиотека                                |
| ----------------------------- | ------------------ | ----------------------------------------- |
| `.txt`, `.md`, `.csv`, `.log` | Текстовые файлы    | `chardet`                                 |
| `.pdf`                        | PDF-файлы          | `pdfminer.six`                            |
| `.docx`                       | Word OpenXML       | `python-docx`                             |
| `.doc`                        | Старый формат Word | `striprtf` / `antiword` (если установлен) |

---

## 🧩 API Эндпоинты

| Метод  | Путь       | Описание                                   |
| ------ | ---------- | ------------------------------------------ |
| `GET`  | `/health`  | Проверка статуса                           |
| `POST` | `/extract` | Принимает файл и возвращает JSON с текстом |

---

## ⚙️ Технические детали

* Максимальный размер файла: **20 MB**
* CORS включён по умолчанию
* Запуск через `uvicorn`:

  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port 8000
  ```

---

## 🧑‍💻 Автор a.denisov.dev@yandex.ru
