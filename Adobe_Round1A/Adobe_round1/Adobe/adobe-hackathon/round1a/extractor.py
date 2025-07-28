import concurrent.futures as cf
import fitz  
import os, json, re, time
from collections import Counter
SKIP_RE = re.compile(
    r'''^(
        \d+|
        page\s+\d+|p\.\s*\d+|
        step\s+\d+|
        note\s*:|
        \d+\.\s*(open|click|select)|
        \([a-z]\)|
        \.{3,}|
        (optional|required)\s*:|
        \w+\.pdf$|
        (revision\s+history|table\s+of\s+contents|acknowledgements?|
        references?|trademarks?|documents?\s+and\s+web\s+sites?|
        appendix|index|bibliography|abstract|summary|
        copyright|legal|disclaimer|confidential|version|date|
        contact\s+us|about\s+us|terms\s+and\s+conditions)
    )$''', re.IGNORECASE | re.VERBOSE)
INDIC_RE = re.compile(r'[\u0900-\u097F\u0A00-\u0CFF]')

def clean_text(text):
    if not text or len(text.strip()) < 2:
        return None
    cleaned = ' '.join(text.strip().split())
    if SKIP_RE.match(cleaned.lower()):
        return None
    if len(cleaned) > 120 or len(cleaned.split()) > 20:
        return None
    if re.fullmatch(r'[0-9\W]+', cleaned) and not re.search(r'[a-zA-Z]', cleaned):
        return None
    return cleaned

def safe_text_dict(page):
    try:
        return page.get_text("dict")
    except Exception:
        return {"blocks": []}

def get_confidence(text, size, is_bold, y0, avg_size, span_count, line_height, avg_line_height, page_height):
    conf = 0
    if size >= avg_size * 1.5:
        conf += 3
    elif size >= avg_size * 1.2:
        conf += 2
    elif size >= avg_size * 1.05:
        conf += 1
    if is_bold:
        conf += 1.5
    if y0 < page_height / 5:
        conf += 1
    elif y0 < page_height / 3:
        conf += 0.5
    if INDIC_RE.search(text):
        conf += 1
    if span_count == 1:
        conf += 1
    if line_height > avg_line_height * 1.5:
        conf += 0.5
    if text.isupper() and len(text.split()) < 10:
        conf += 1
    if text[0].isupper() and 1 < len(text.split()) < 15:
        conf += 0.5
    return conf

def determine_level(size, top_sizes, conf, is_bold):
    if conf >= 6: return "H1"
    if top_sizes and size >= top_sizes[0] * 0.98:
        return "H1"
    elif len(top_sizes) > 1 and size >= top_sizes[1] * 0.95:
        return "H2"
    elif is_bold and size >= top_sizes[-1] * 0.9:
        return "H3"
    return "H3"

def extract_pdf(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        title = os.path.splitext(os.path.basename(pdf_path))[0]
        if len(doc) == 0:
            return title, []
        sizes, lines = [], []
        page_height = doc[0].rect.height if len(doc) > 0 else 0
        for page_num in range(min(50, len(doc))):
            page = doc[page_num]
            current_page_height = page.rect.height
            for block in safe_text_dict(page).get("blocks", []):
                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    if not spans: continue
                    text = " ".join(span.get("text", "") for span in spans).strip()
                    cleaned = clean_text(text)
                    if not cleaned: continue
                    max_span = max(spans, key=lambda s: s.get("size", 0), default={})
                    size = max_span.get("size", 0)
                    fontname = max_span.get("font", "")
                    y0, y1 = line.get("bbox", [0, 0, 0, 0])[1:3]
                    line_height = y1 - y0
                    flags = max_span.get("flags", 0)
                    is_bold = bool(flags & 16) or ("bold" in fontname.lower())
                    sizes.append(size)
                    lines.append({
                        "text": cleaned,
                        "size": size,
                        "flags": flags,
                        "is_bold": is_bold,
                        "y0": y0,
                        "line_height": line_height,
                        "page": page_num,
                        "span_count": len(spans)
                    })
        if not lines:
            return title, []
        avg_size = sum(sizes) / len(sizes) if sizes else 0
        avg_line_height = sum(l["line_height"] for l in lines) / len(lines) if lines else 0
        size_counts = Counter(sizes)
        filtered_size_counts = {s: c for s, c in size_counts.items() if s > avg_size * 0.9}
        top_sizes = sorted([s for s, _ in Counter(filtered_size_counts).most_common(3)], reverse=True)
        seen_heading_text = set()
        headings = []
        for line in lines:
            conf = get_confidence(
                line["text"], line["size"], line["is_bold"], line["y0"],
                avg_size, line["span_count"], line["line_height"], avg_line_height, page_height
            )
            if conf >= 2.0 or (len(lines) < 100 and conf >= 1.0):
                normalized_text = line["text"].lower()
                if normalized_text not in seen_heading_text:
                    seen_heading_text.add(normalized_text)
                    level = determine_level(line["size"], top_sizes, conf, line["is_bold"])
                    headings.append({
                        "level": level,
                        "text": line["text"],
                        "page": line["page"],
                        "conf": conf,
                        "y0": line["y0"]
                    })
        if len(headings) < 5:
            fallback_candidates = []
            for fl in lines:
                if fl["y0"] < page_height * 0.6 and len(fl["text"]) <= 80 and \
                   fl["size"] >= avg_size * 1.0 and (fl["is_bold"] or fl["size"] >= avg_size * 1.2):
                    normalized_text = fl["text"].lower()
                    if normalized_text not in seen_heading_text:
                        fallback_candidates.append(fl)
                        seen_heading_text.add(normalized_text)
            sorted_fallback = sorted(fallback_candidates, key=lambda x: (-x["size"], x["y0"], x["page"]))
            for fl in sorted_fallback[:min(5, len(sorted_fallback))]:
                headings.append({
                    "level": "H3",
                    "text": fl["text"],
                    "page": fl["page"],
                    "conf": 0.5,
                    "y0": fl["y0"]
                })
        title_cands = [h for h in headings if h["page"] == 0 and h["level"] == "H1"]
        if title_cands:
            title = sorted(title_cands, key=lambda h: (-h["conf"], h["y0"]))[0]["text"]
        elif headings:
            title = sorted(headings, key=lambda h: (-h["conf"], h["y0"]))[0]["text"]
        return title, headings
    except Exception as e:
        print(f" Error processing {pdf_path}: {e}")
        return os.path.splitext(os.path.basename(pdf_path))[0], []

def filter_outline(outline, max_items=20):
    page_index_mode = 0 
    sorted_candidates = sorted(outline, key=lambda x: (-x["conf"], x["y0"], x["page"]))
    seen_normalized_text = set()
    result = []
    for item in sorted_candidates:
        normalized_text = re.sub(r'\W+', '', item["text"]).lower()
        if normalized_text in seen_normalized_text:
            continue
        seen_normalized_text.add(normalized_text)
        page_field = item["page"] + page_index_mode
        result.append({
            "level": item["level"],
            "text": item["text"],
            "page": page_field
        })
        if len(result) >= max_items:
            break
    level_order = {"H1": 0, "H2": 1, "H3": 2}
    return sorted(result, key=lambda x: (x["page"], level_order.get(x["level"], 99)))

def worker(task):
    pdf_path, out_path = task
    start_time = time.time()
    title, outline = extract_pdf(pdf_path)
    processing_time = time.time() - start_time
    if not title and outline:
        title = outline[0]["text"]
    elif not title:
        title = os.path.splitext(os.path.basename(pdf_path))[0]
    filtered_outline = filter_outline(outline)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"title": title, "outline": filtered_outline}, f, ensure_ascii=False, indent=2)
    print(f"Processed {os.path.basename(pdf_path)} in {processing_time:.2f} sec")

def main():
    input_dir = "/app/input"
    output_dir = "/app/output"
    if not os.path.exists(input_dir):
        print(f" Input folder not found at: {input_dir}")
        return
    os.makedirs(output_dir, exist_ok=True)
    pdfs = [f for f in os.listdir(input_dir) if f.lower().endswith(".pdf")]
    if not pdfs:
        print(f" No PDF files found in input folder: {input_dir}")
        return
    tasks = [(os.path.join(input_dir, f), os.path.join(output_dir, os.path.splitext(f)[0] + ".json")) for f in pdfs]
    print(f" Starting extraction from {len(tasks)} PDF(s)...")
    total_start_time = time.time()
    with cf.ProcessPoolExecutor(max_workers=min(8, len(tasks))) as executor:
        executor.map(worker, tasks)
    total_processing_time = time.time() - total_start_time
    print(f" All PDFs processed in {total_processing_time:.2f} sec")

if __name__ == "__main__":
    main()
