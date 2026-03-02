from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from service import compute_text_diff

app = FastAPI(title="PDF Diff API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/text-diff")
async def text_diff(
    old_pdf: UploadFile = File(...),
    new_pdf: UploadFile = File(...),
):
    """Word-level text diff with highlighted page images and changes list."""
    old_bytes = await old_pdf.read()
    new_bytes = await new_pdf.read()
    return compute_text_diff(old_bytes, new_bytes)
