import sys
import os
import requests

def download_sample_pdfs():
    fixtures_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
    os.makedirs(fixtures_dir, exist_ok=True)
    
    # 14 reliable, statically hosted PDFs for testing
    pdf_urls = {
        "dummy.pdf": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
        "sample-3pp.pdf": "https://pdfobject.com/pdf/sample-3pp.pdf",
        "sample-link.pdf": "https://www.antennahouse.com/XSLsample/pdf/sample-link_1.pdf",
        "iso-sample.pdf": "https://www.iso.org/files/live/sites/isoorg/files/store/en/PUB100080.pdf",
        "a_file.pdf": "https://tcpdf.org/files/examples/example_001.pdf",
        "sample-2.pdf": "https://unec.edu.az/application/uploads/2014/12/pdf-sample.pdf",
        "sample-3.pdf": "https://research.nhm.org/pdfs/10840/10840-001.pdf",
        "sample-5.pdf": "https://s29.q4cdn.com/175625835/files/doc_downloads/test.pdf",
        "color-test.pdf": "https://www.color.org/srgb.pdf",
        "mit-sample.pdf": "https://ocw.mit.edu/courses/aeronautics-and-astronautics/16-01-unified-engineering-i-ii-iii-iv-fall-2005-spring-2006/systems-labs-06/spl8.pdf",
        "pdf-reference.pdf": "https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf",
        "irs-form.pdf": "https://www.irs.gov/pub/irs-pdf/fw4.pdf",
        "arxiv-paper.pdf": "https://arxiv.org/pdf/1706.03762.pdf",
        "git-cheat.pdf": "https://education.github.com/git-cheat-sheet-education.pdf"
    }

    print(f"Downloading {len(pdf_urls)} reliable PDF fixtures...")
    downloaded = 0
    
    for filename, url in pdf_urls.items():
        file_path = os.path.join(fixtures_dir, filename)
        if os.path.exists(file_path):
            print(f"  Skipping {filename} (already exists)")
            downloaded += 1
            continue
            
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                with open(file_path, 'wb') as f:
                    f.write(r.content)
                print(f"  Downloaded {filename}")
                downloaded += 1
            else:
                print(f"  Failed {filename} - HTTP HTTP {r.status_code}")
        except Exception as e:
            print(f"  Failed {filename} - {e}")

    print(f"\nSuccessfully downloaded {downloaded}/{len(pdf_urls)} PDFs to {fixtures_dir}")

if __name__ == "__main__":
    download_sample_pdfs()
