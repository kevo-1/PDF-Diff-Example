# PDF-Diff Example

This is a sample project to demonstrate the PDF-Diff functionality.

**Note:** This project is a prototype and is not intended for production use.

## How to Run

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the server:
   ```bash
   uvicorn main:app --reload
   ```

3. Host the index.html file:
    ```bash
    python -m http.server 8000
    ```

4. Open the application in your browser:
    ```
    http://localhost:8000
    ```

5. Upload the two PDF files to compare.

