import sys
import os
import requests
import traceback
import traceback

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web_monitoring_pdf_diff import pdf_text_diff

def fetch_cdx_pdfs(limit=20):
    cdx_url = "http://web.archive.org/cdx/search/cdx"

def fetch_cdx_pdfs(limit=30):
    # Search Internet Archive for items with format=Text PDF
    # The collection-search page uses their advanced search API
    search_url = "https://archive.org/advancedsearch.php"
    params = {
        "q": 'format:("Text PDF") AND mediatype:("texts")',
        "fl[]": "identifier",
        "rows": limit * 5, # Fetch more to account for 404s
        "output": "json"
    }
    
    print("Fetching PDF list from archive.org...")
    resp = requests.get(search_url, params=params)
    resp.raise_for_status()
    data = resp.json()
    
    docs = data.get("response", {}).get("docs", [])
    if not docs:
        print("No documents found!")
        return []
        
    results = []
    # For each item, the PDF is usually available at https://archive.org/download/{identifier}/{identifier}.pdf
    for doc in docs:
        identifier = doc.get("identifier")
        if identifier:
             # Often the PDF has the same name as the identifier
             pdf_url = f"https://archive.org/download/{identifier}/{identifier}.pdf"
             results.append(pdf_url)
             
    return results

def main():
    urls = fetch_cdx_pdfs(limit=20)
    if not urls:
        print("No URLs found from CDX.")
        return

    pdfs = []
    print(f"Found {len(urls)} PDF URLs. Downloading up to 20...")
    for url in urls:
        if len(pdfs) >= 20:
            break
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                pdfs.append((url, r.content))
                print(f"Downloaded [{len(pdfs)}/20]: {url}")
            else:
                pass
        except Exception as e:
            pass
            
    print(f"\nSuccessfully downloaded {len(pdfs)} PDFs. Testing...")
    if not pdfs:
        return

    success_count = 0
    error_count = 0
    
    for i, (url1, bytes1) in enumerate(pdfs):
        try:
            print(f"[{i+1}/{len(pdfs)}] Testing: {url1}")
            
            # 1. Byte identical test
            res_id = pdf_text_diff(bytes1, bytes1)
            assert res_id["identical"] is True, "Byte identical test failed!"
            
            # 2. Diff against another PDF (wrap around)
            next_url, next_bytes = pdfs[(i + 1) % len(pdfs)]
            res_diff = pdf_text_diff(bytes1, next_bytes)
            
            success_count += 1
            print(f"   -> Success. Identical={res_diff.get('identical')}, Changes={res_diff.get('change_count')}")
            
        except Exception as e:
            error_count += 1
            print(f"   -> ERROR!")
            traceback.print_exc()

    print(f"\nSummary: {success_count} succeeded, {error_count} failed out of {len(pdfs)} PDFs tested.")

if __name__ == "__main__":
    main()
