from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from service import compute_diff

app = FastAPI(title="PDF Diff API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class DiffRequest(BaseModel):
    old_text: str
    new_text: str


@app.post("/diff")
def diff_texts(body: DiffRequest):
    """
    Accepts the extracted text of two PDFs and returns character-level diff ops.
    Text extraction is performed client-side by pdf.js to ensure highlight alignment.
    """
    diffs = compute_diff(body.old_text, body.new_text)
    return {"diffs": diffs}
