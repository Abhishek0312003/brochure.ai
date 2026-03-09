from openai import OpenAI
import os
import time
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright

OLLAMA_BASE_URL = "http://localhost:11434/v1"
ollama = OpenAI(base_url=OLLAMA_BASE_URL, api_key='ollama')

# force UTF-8 output so Windows terminal does not crash on special chars
import sys
sys.stdout.reconfigure(encoding='utf-8')

# ── Edge case helpers ─────────────────────────────────────────────────────────

def safe_ext(url_str, fallback=".jpg"):
    try:
        path = urlparse(url_str).path
        ext = os.path.splitext(path)[-1].lower()
        return ext if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico"} else fallback
    except Exception:
        return fallback

def safe_slug(url_str, max_len=60):
    try:
        slug = url_str.replace("https://", "").replace("http://", "")
        for ch in ["/", ".", "?", "=", "&", "#", ":", "%"]:
            slug = slug.replace(ch, "_")
        return slug[:max_len]
    except Exception:
        return f"page_{int(time.time())}"

def normalize_url(href, base):
    try:
        if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
            return None
        return urljoin(base, href)
    except Exception:
        return None

def is_same_domain(link_url, base_url):
    try:
        return urlparse(link_url).netloc == urlparse(base_url).netloc
    except Exception:
        return False

def fetch_with_playwright(target_url, timeout=30000):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            pg = browser.new_page()
            pg.set_extra_http_headers({"User-Agent": "Mozilla/5.0"})
            pg.goto(target_url, wait_until="networkidle", timeout=timeout)
            content = pg.content()
            browser.close()
            return content
    except Exception as e:
        print(f"[ERROR] Playwright failed for {target_url}: {e}")
        return None

def download_image(img_url, save_path, headers):
    try:
        r = requests.get(img_url, headers=headers, timeout=10)
        r.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(r.content)
        return True
    except Exception as e:
        print(f"[ERROR] Image download failed {img_url}: {e}")
        return False

def scrape_and_save(target_url, pages_dir, images_dir, headers, label="page"):
    print(f"[LOG] Fetching: {target_url}")
    t = time.time()
    html = fetch_with_playwright(target_url)
    if not html:
        print(f"[SKIP] Could not fetch: {target_url}")
        return ""
    print(f"[LOG] Fetched in {time.time() - t:.2f}s")

    html_path = os.path.join(pages_dir, f"{label}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[LOG] HTML saved -> {html_path}")

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n", strip=True)
    txt_path = os.path.join(pages_dir, f"{label}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"[LOG] Text saved -> {txt_path}")

    return text, soup

# ── Main ──────────────────────────────────────────────────────────────────────

url = input("The website URL: ").strip()
if not url.startswith("http"):
    url = "https://" + url
print(f"[LOG] Target: {url}")

headers = {"User-Agent": "Mozilla/5.0"}

domain = urlparse(url).netloc.replace("www.", "")
pages_dir = f"pages/{domain}"
images_dir = f"images/{domain}"
os.makedirs(pages_dir, exist_ok=True)
os.makedirs(images_dir, exist_ok=True)
print(f"[LOG] Output dirs: {pages_dir} | {images_dir}")

# Step 1: scrape main page
result = scrape_and_save(url, pages_dir, images_dir, headers, label="page")
if not result:
    print("[FATAL] Could not scrape the main page. Exiting.")
    exit(1)
page_text, soup = result

print("[LOG] Downloading main page images...")
for i, img in enumerate(soup.find_all("img", src=True)):
    img_url = urljoin(url, img["src"])
    ext = safe_ext(img_url)
    img_path = os.path.join(images_dir, f"main_image_{i}{ext}")
    if download_image(img_url, img_path, headers):
        print(f"[LOG] Image saved: {img_path}")

# Step 2: extract links
raw_links = []
for tag in soup.find_all("a", href=True):
    full = normalize_url(tag["href"], url)
    if full and is_same_domain(full, url) and full not in raw_links:
        raw_links.append(full)

print(f"[LOG] Found {len(raw_links)} same-domain links")

# Step 3: filter useful links via Ollama
print("[LOG] Filtering useful links via Ollama...")
useful_links = []

for link in raw_links:
    try:
        prompt = f"""You are building a company brochure for investors, clients, and users.
Analyze this URL path and decide if it likely contains valuable content such as:
- About the company, mission, vision, team
- Services, products, features, pricing
- Contact information, support
- Blog posts, case studies, testimonials

Reply with ONLY "YES" or "NO". No explanation.
URL: {link}"""

        resp = ollama.chat.completions.create(
            model="llama3.2",
            messages=[{"role": "user", "content": prompt}]
        )
        answer = resp.choices[0].message.content.strip().upper()
        is_yes = answer.startswith("YES") or "YES" in answer[:10]
        # use ASCII symbols only to avoid Windows encoding crash
        print(f"[LOG] {'YES' if is_yes else 'NO '} -> {link}")
        if is_yes:
            useful_links.append(link)
    except Exception as e:
        print(f"[ERROR] Ollama filter failed for {link}: {e}")

# always force-include contact page if found — Ollama often filters it out
contact_keywords = ["contact", "contact-us", "contactus", "reach-us", "get-in-touch"]
for link in raw_links:
    path = urlparse(link).path.lower().strip("/")
    if any(kw in path for kw in contact_keywords) and link not in useful_links:
        print(f"[LOG] Force-adding contact page -> {link}")
        useful_links.append(link)

print(f"[LOG] Useful links: {len(useful_links)}")

# Step 4: scrape each useful link
all_pages_text = [page_text]

for i, link in enumerate(useful_links):
    print(f"[LOG] Scraping {i+1}/{len(useful_links)}: {link}")
    slug = safe_slug(link)
    result = scrape_and_save(link, pages_dir, images_dir, headers, label=slug)
    if not result:
        continue
    sub_text, sub_soup = result
    all_pages_text.append(sub_text)

    for j, img in enumerate(sub_soup.find_all("img", src=True)):
        img_url = urljoin(link, img["src"])
        ext = safe_ext(img_url)
        img_path = os.path.join(images_dir, f"{slug}_img_{j}{ext}")
        if download_image(img_url, img_path, headers):
            print(f"[LOG] Image saved: {img_path}")

print(f"[LOG] Total pages scraped: {len(all_pages_text)}")

# Step 5: build brochure JSON via Ollama — batched processing
print("[LOG] Building brochure JSON via Ollama (batched)...")

BATCH_SIZE = 1500  # chars per batch — safe for llama3.2 context window

def clean_json(raw):
    """Strip markdown fences and return clean JSON string."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return raw.strip()

def parse_json_safe(raw):
    """Try to parse JSON, repair by trimming trailing garbage if needed."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        for end_idx in range(len(raw), 0, -1):
            if raw[end_idx-1] == '}':
                try:
                    return json.loads(raw[:end_idx])
                except Exception:
                    continue
    return None

def extract_batch(text_chunk, batch_num, total_batches):
    """Send one batch to Ollama, extract partial brochure fields."""
    prompt = f"""You are extracting information for a company brochure. This is batch {batch_num} of {total_batches}.
Extract whatever is relevant from this content and return ONLY a JSON object with any of these keys that are present:
company_name, tagline, about, mission, services (list), key_features (list), pricing (list),
target_audience, contact_info (object with email/phone/address/website), testimonials (list), key_highlights (list).

Return ONLY valid JSON. No markdown. No explanation. If a field is not found, omit it.

CONTENT:
{text_chunk}"""

    resp = ollama.chat.completions.create(
        model="llama3.2",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = clean_json(resp.choices[0].message.content)
    return parse_json_safe(raw)

def merge_brochures(batches):
    """Merge multiple partial brochure dicts into one complete brochure."""
    merged = {
        "company_name": "",
        "tagline": "",
        "about": "",
        "mission": "",
        "services": [],
        "key_features": [],
        "pricing": [],
        "target_audience": "",
        "contact_info": {"email": "", "phone": "", "address": "", "website": ""},
        "testimonials": [],
        "key_highlights": []
    }
    list_fields = {"services", "key_features", "pricing", "testimonials", "key_highlights"}

    for b in batches:
        if not b:
            continue
        for key, val in b.items():
            if key not in merged:
                continue
            if key == "contact_info" and isinstance(val, dict):
                for k, v in val.items():
                    if v and not merged["contact_info"].get(k):
                        merged["contact_info"][k] = v
            elif key in list_fields and isinstance(val, list):
                # add unique items only
                for item in val:
                    if item and item not in merged[key]:
                        merged[key].append(item)
            elif isinstance(val, str) and val.strip():
                # string fields: take first non-empty value, append later ones
                if not merged[key]:
                    merged[key] = val.strip()
                elif key in {"about", "mission", "target_audience"} and len(merged[key]) < 400:
                    merged[key] += " " + val.strip()
    return merged

# split all page texts into BATCH_SIZE chunks
all_text = "\n\n".join(t for t in all_pages_text if t.strip())
chunks = [all_text[i:i+BATCH_SIZE] for i in range(0, len(all_text), BATCH_SIZE)]
total = len(chunks)
print(f"[LOG] Processing {total} batch(es) of ~{BATCH_SIZE} chars each...")

batch_results = []
for idx, chunk in enumerate(chunks):
    print(f"[LOG] Batch {idx+1}/{total}...")
    t = time.time()
    try:
        result = extract_batch(chunk, idx+1, total)
        elapsed = time.time() - t
        if result:
            print(f"[LOG] Batch {idx+1} done in {elapsed:.2f}s — fields: {list(result.keys())}")
            batch_results.append(result)
        else:
            print(f"[LOG] Batch {idx+1} returned no usable JSON, skipping")
    except Exception as e:
        print(f"[ERROR] Batch {idx+1} failed: {e}")

print(f"[LOG] Merging {len(batch_results)} batch result(s)...")
brochure = merge_brochures(batch_results)

# dedicated contact info extraction pass — scan full text for email/phone/address
print("[LOG] Extracting contact info...")
import re
full_text = all_text

# email
if not brochure["contact_info"]["email"]:
    emails = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', full_text)
    if emails:
        brochure["contact_info"]["email"] = emails[0]
        print(f"[LOG] Email found: {emails[0]}")

# phone
if not brochure["contact_info"]["phone"]:
    phones = re.findall(r'[+]?[\d][\d\s\-().]{8,}[\d]', full_text)
    clean_phones = [p.strip() for p in phones if len(re.sub(r'\D','',p)) >= 8]
    if clean_phones:
        brochure["contact_info"]["phone"] = clean_phones[0]
        print(f"[LOG] Phone found: {clean_phones[0]}")

# address — look for lines near "Address" keyword
if not brochure["contact_info"]["address"]:
    addr_match = re.search(r'Address[:\s\n]+([^\n]{10,80})', full_text, re.IGNORECASE)
    if addr_match:
        brochure["contact_info"]["address"] = addr_match.group(1).strip()
        print(f"[LOG] Address found: {brochure['contact_info']['address']}")

# website
if not brochure["contact_info"]["website"]:
    brochure["contact_info"]["website"] = url

if not any([brochure["company_name"], brochure["about"], brochure["services"]]):
    print("[ERROR] Merge produced empty brochure")
    brochure = {"error": "All batches failed", "raw": all_text[:500]}
else:
    print("[LOG] Brochure merge complete")
    print(f"[LOG] Contact -> email:{brochure['contact_info']['email']} phone:{brochure['contact_info']['phone']} address:{brochure['contact_info']['address']}")

# Step 6: save brochure JSON
brochure_path = f"{pages_dir}/brochure.json"
with open(brochure_path, "w", encoding="utf-8") as f:
    json.dump(brochure, f, indent=2, ensure_ascii=False)
print(f"[LOG] Brochure saved -> {brochure_path}")
print("\n[DONE] Brochure JSON:")
print(json.dumps(brochure, indent=2, ensure_ascii=False))