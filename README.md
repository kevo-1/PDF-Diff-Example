# web-monitoring-pdf-diff-example

Tools for diffing PDF documents, producing output compatible with
[web-monitoring-diff](https://github.com/edgi-govdata-archiving/web-monitoring-diff).

## Installation

```bash
pip install web-monitoring-pdf-diff
```

For development:

```bash
pip install -e ".[dev]"
```

## Usage

### Library

```python
from web_monitoring_pdf_diff import pdf_text_diff

with open("old.pdf", "rb") as f:
    old_pdf = f.read()
with open("new.pdf", "rb") as f:
    new_pdf = f.read()

result = pdf_text_diff(old_pdf, new_pdf)
```

The result is a dictionary matching the web-monitoring-diff output format:

```json
{
	"diff": [
		[-1, "removed text"],
		[0, "unchanged text"],
		[1, "added text"]
	],
	"change_count": 2
}
```

Where each entry in `diff` is a `[change_type, text]` pair:

- `-1` = removed (text present in old PDF only)
- `0` = unchanged
- `1` = added (text present in new PDF only)

### Example with included sample PDFs

Two sample PDFs are included in the repository for quick testing:

```python
from web_monitoring_pdf_diff import pdf_text_diff

with open("pdf_sample.pdf", "rb") as f:
    original = f.read()
with open("pdf_sample changed.pdf", "rb") as f:
    modified = f.read()

result = pdf_text_diff(original, modified)
print(f"Found {result['change_count']} change(s)")
for change_type, text in result["diff"]:
    if change_type == -1:
        print(f"  REMOVED: {text[:80]}")
    elif change_type == 1:
        print(f"  ADDED:   {text[:80]}")
```

### Example Output

```
Found 3 change(s)
  REMOVED: fun fun.
  ADDED:   Fun Fun Fun.
  REMOVED: pellentesque elit,
  ADDED:   pellentesque. Elit,
  ADDED:   Extra text
 Extra text Sample PDF This is a simple PDF file. Fun Fun Fun Fun. L
```

## Web Service

The package includes a FastAPI web service that exposes `pdf_text_diff` as an HTTP endpoint.

### Install with server dependencies

```bash
pip install -e ".[server]"
```

### Run locally

**Windows / all platforms** (using uvicorn directly):

```bash
uvicorn web_monitoring_pdf_diff.web:app --host 127.0.0.1 --port 8000 --reload
```

### Example request

```bash
curl -X POST http://127.0.0.1:8000/pdf_text_diff \
  -F "old_pdf=@old.pdf" \
  -F "new_pdf=@new.pdf"
```

## Target Python Version

Python >= 3.10
