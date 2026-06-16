#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
classifier.py — Lõi (engine) phân loại hợp đồng dùng chung cho cả
bản chạy theo folder (classify_contracts.py) và bản web upload (app.py).

Phân loại (xét theo thứ tự):
  1. Giống từ 70% trở lên   : độ giống template tốt nhất >= 70%
  2. Hợp đồng trọng yếu      : độ giống < 70% VÀ thuộc loại NDA / License
  3. Không theo template     : các trường hợp còn lại
"""

import os, re, subprocess, tempfile, difflib

# ---------- Cấu hình ----------
THRESHOLD = 70.0   # % ngưỡng "giống template"

CAT_SIM  = "Giống từ 70% trở lên"
CAT_KEY  = "Hợp đồng trọng yếu"
CAT_NONE = "Không theo template"
CATEGORIES = [CAT_SIM, CAT_KEY, CAT_NONE]

# Từ khóa nhận diện hợp đồng trọng yếu (xét ở tiêu đề + tên file)
KEYWORDS_MATERIAL = [
    "non-disclosure", "nondisclosure", "non disclosure", "nda",
    "confidentiality agreement", "thỏa thuận bảo mật", "thoả thuận bảo mật",
    "hợp đồng bảo mật", "license agreement", "licensing agreement",
    "hợp đồng cấp phép", "hợp đồng bản quyền", "hợp đồng license",
]

_VN = "àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"

# ---------- Đọc văn bản nhiều định dạng ----------
def read_docx(path):
    import docx
    d = docx.Document(path)
    parts = [p.text for p in d.paragraphs]
    for tb in d.tables:
        for row in tb.rows:
            parts.append(" ".join(c.text for c in row.cells))
    return "\n".join(parts)

def read_doc(path):
    """Chuyển .doc -> .docx bằng LibreOffice (nếu có) rồi đọc."""
    try:
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["soffice", "--headless", "--convert-to", "docx",
                            "--outdir", tmp, path], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            out = os.path.join(tmp, os.path.splitext(os.path.basename(path))[0] + ".docx")
            return read_docx(out) if os.path.exists(out) else ""
    except Exception:
        return ""   # môi trường không có LibreOffice -> bỏ qua file .doc

def read_pdf(path):
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            return "\n".join(pg.extract_text() or "" for pg in pdf.pages)
    except Exception:
        try:
            import PyPDF2
            r = PyPDF2.PdfReader(path)
            return "\n".join(pg.extract_text() or "" for pg in r.pages)
        except Exception:
            return ""

def extract_text(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx": return read_docx(path)
    if ext == ".doc":  return read_doc(path)
    if ext == ".pdf":  return read_pdf(path)
    if ext in (".txt", ".md"):
        try:
            return open(path, encoding="utf-8", errors="ignore").read()
        except Exception:
            return ""
    return ""

SUPPORTED_EXT = (".docx", ".doc", ".pdf", ".txt", ".md")

# ---------- Chuẩn hóa & so sánh ----------
def normalize(text):
    """Bỏ qua khác biệt về số/ngày tháng, viết hoa, dấu câu, khoảng trắng."""
    t = text.lower()
    t = re.sub(r"\d+", " ", t)
    t = re.sub(rf"[^\w\s{_VN}]", " ", t, flags=re.UNICODE)
    return t.split()

def similarity(tokens_a, tokens_b):
    if not tokens_a or not tokens_b:
        return 0.0
    return difflib.SequenceMatcher(None, tokens_a, tokens_b).ratio() * 100.0

def first_line(text):
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""

def is_material(title, name):
    blob = (title + " " + name).lower()
    return any(k in blob for k in KEYWORDS_MATERIAL)

# ---------- API cấp cao ----------
def build_templates(template_paths):
    """Nhận list đường dẫn file template -> list dict {name, tokens}."""
    templates = []
    for p in template_paths:
        txt = extract_text(p)
        if txt.strip():
            templates.append({"name": os.path.basename(p), "tokens": normalize(txt)})
    return templates

def classify_text(name, text, templates, threshold=THRESHOLD):
    """Phân loại 1 hợp đồng (đã có text) so với danh sách templates."""
    tokens = normalize(text)
    title = first_line(text)
    best_name, best_sim = "-", 0.0
    for tpl in templates:
        s = similarity(tokens, tpl["tokens"])
        if s > best_sim:
            best_sim, best_name = s, tpl["name"]
    material = is_material(title, name)
    if best_sim >= threshold:
        cat = CAT_SIM
    elif material:
        cat = CAT_KEY
    else:
        cat = CAT_NONE
    return {"name": name, "title": title[:90], "best_tpl": best_name,
            "sim": round(best_sim, 1), "material": material, "cat": cat}

def classify_file(path, templates, threshold=THRESHOLD, display_name=None):
    text = extract_text(path)
    return classify_text(display_name or os.path.basename(path), text, templates, threshold)
