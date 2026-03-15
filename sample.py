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