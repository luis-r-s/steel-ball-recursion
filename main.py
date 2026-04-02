import sys
import os
import requests
import img2pdf
import subprocess
import time
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

path = "out/"


def download_file(filename, url, max_retries=3):
    for attempt in range(max_retries):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(url, timeout=30, headers=headers, stream=True)
            response.raise_for_status()

            with open(filename, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return True
        except (
            requests.exceptions.ChunkedEncodingError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        ) as e:
            print(f"attempt {attempt + 1} failed for {filename}: {type(e).__name__}")
            if attempt < max_retries - 1:
                wait_time = 2**attempt
                print(f"retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"failed to download {filename} after {max_retries} attempts")
                return False
        except Exception as e:
            print(f"unexpected error downloading {filename}: {e}")
            return False


def main():
    os.makedirs(path, exist_ok=True)

    url = sys.argv[1]
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    pictures = soup.find_all("picture")

    img_urls = [pic.img["src"] for pic in pictures]

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}
        for i, img_url in enumerate(img_urls):
            ext = os.path.splitext(img_url)[-1] or ".png"
            filename = os.path.join(path, f"image_{i}{ext}")
            future = executor.submit(download_file, filename, img_url)
            futures[future] = i
            print(f"queued page {i}")

        completed = 0
        for future in as_completed(futures):
            i = futures[future]
            try:
                success = future.result()
                if success:
                    print(f"downloaded page {i}")
                    completed += 1
            except Exception as e:
                print(f"error on page {i}: {e}")

    image_files = sorted(
        [os.path.join(path, fn) for fn in os.listdir(path) if fn.endswith(".png")],
        key=lambda x: int(os.path.splitext(os.path.basename(x))[0].split("_")[1]),
    )

    if not image_files:
        print("no images were downloaded successfully")
        return

    print(f"converting {len(image_files)} images to pdf")
    pdf_data = img2pdf.convert(image_files)
    with open(os.path.join(path, "output.pdf"), "wb") as f:
        f.write(pdf_data)

    subprocess.run("rm -f out/*.png", shell=True, check=True)


if __name__ == "__main__":
    main()
