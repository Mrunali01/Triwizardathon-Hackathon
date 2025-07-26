from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin

def find_uncaptioned_images(url):
    try:
        headers = { "User-Agent": "Mozilla/5.0" }
        html = requests.get(url, headers=headers, timeout=10).text
    except Exception as e:
        raise RuntimeError(f"Failed to fetch URL: {e}")
    
    soup = BeautifulSoup(html, "html.parser")
    img_tags = soup.find_all("img")

    print(f"Found {len(img_tags)} image(s) on the page.")
    
    excluded_extensions = ['.svg', '.webp', '.gif', '.ico', 'xml', 'svg+xml']
    uncaptioned = []

    for tag in img_tags:
        src = tag.get("src")
        alt = tag.attrs.get("alt", None)

        if not src:
            continue

        # 🔽 Skip if extension is in excluded list
        if any(src.lower().endswith(ext) for ext in excluded_extensions):
            print(f"⚪ Skipping excluded image: {src}")
            continue

        if alt is None or alt.strip() == "":
            full_src = urljoin(url, src)
            print(f"🟥 Uncaptioned image detected: {full_src}")
            uncaptioned.append(full_src)

    return uncaptioned