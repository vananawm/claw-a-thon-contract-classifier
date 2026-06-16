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

import os, re, json, subprocess, tempfile, difflib

# ---------- Cấu hình ----------
THRESHOLD = 70.0   # % ngưỡng "giống template"

CAT_SIM  = "Giống từ 70% trở lên"
CAT_KEY  = "Hợp đồng trọng yếu"
CAT_NONE = "Không theo template"
CATEGORIES = [CAT_SIM, CAT_KEY, CAT_NONE]

# --- Model GreenNode MaaS (OpenAI-compatible) để nhận diện hợp đồng trọng yếu ---
LLM_BASE_URL = os.environ.get("GREENNODE_BASE_URL", "https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1")
LLM_API_KEY  = os.environ.get("GREENNODE_API_KEY", "")
LLM_MODEL    = os.environ.get("GREENNODE_MODEL", "")  # để trống = tự dò model Qwen đang bật
_RESOLVED_MODEL = None

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

def _resolve_model():
    """Xác định mã model để gọi: ưu tiên biến môi trường, nếu trống thì tự dò model
    có chứa 'qwen' đang khả dụng qua /v1/models. Có cache để chỉ dò 1 lần."""
    global _RESOLVED_MODEL
    if LLM_MODEL:
        return LLM_MODEL
    if _RESOLVED_MODEL:
        return _RESOLVED_MODEL
    try:
        import requests
        r = requests.get(f"{LLM_BASE_URL}/models",
                         headers={"Authorization": f"Bearer {LLM_API_KEY}"}, timeout=15)
        r.raise_for_status()
        ids = [m.get("id", "") for m in r.json().get("data", [])]
        pick = next((i for i in ids if "qwen" in i.lower()), None) or (ids[0] if ids else None)
        _RESOLVED_MODEL = pick or "qwen/qwen3-5-27b"
    except Exception:
        _RESOLVED_MODEL = "qwen/qwen3-5-27b"
    return _RESOLVED_MODEL

def detect_material_llm(title, text):
    """Dùng model Qwen (GreenNode MaaS) xác định hợp đồng trọng yếu.
    Trả về dict {material, loai, ly_do} nếu gọi được; None nếu không (sẽ fallback dò từ khóa)."""
    if not LLM_API_KEY:
        return None
    try:
        import requests
        prompt = (
            "Bạn là trợ lý pháp chế. Đọc đoạn đầu hợp đồng và xác định đây có phải "
            "HỢP ĐỒNG TRỌNG YẾU không. Hợp đồng trọng yếu là loại quan trọng cần rà soát kỹ: "
            "NDA / thỏa thuận bảo mật, hợp đồng license / cấp phép / bản quyền, chuyển nhượng "
            "sở hữu trí tuệ, hoặc hợp đồng có cam kết bảo mật/độc quyền mạnh.\n"
            'Chỉ trả lời bằng JSON: {"material": true/false, "loai": "<loại ngắn gọn>", '
            '"ly_do": "<1 câu>"}.\n\n'
            f"Tiêu đề: {title}\nNội dung (rút gọn):\n{text[:3000]}"
        )
        r = requests.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {LLM_API_KEY}", "Content-Type": "application/json"},
            json={"model": _resolve_model(),
                  "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0},
            timeout=30,
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        m = re.search(r"\{.*\}", content, re.S)
        data = json.loads(m.group(0)) if m else {}
        return {"material": bool(data.get("material")),
                "loai": str(data.get("loai", "")),
                "ly_do": str(data.get("ly_do", ""))}
    except Exception:
        return None

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

    loai = ly_do = ""
    if best_sim >= threshold:
        cat, material = CAT_SIM, False
    else:
        # Chưa khớp template -> kiểm tra "trọng yếu": ưu tiên Qwen, fallback dò từ khóa
        llm = detect_material_llm(title, text)
        if llm is not None:
            material, loai, ly_do = llm["material"], llm["loai"], llm["ly_do"]
        else:
            material = is_material(title, name)
        cat = CAT_KEY if material else CAT_NONE

    return {"name": name, "title": title[:90], "best_tpl": best_name,
            "sim": round(best_sim, 1), "material": material,
            "loai": loai, "ly_do": ly_do, "cat": cat}

def classify_file(path, templates, threshold=THRESHOLD, display_name=None):
    text = extract_text(path)
    return classify_text(display_name or os.path.basename(path), text, templates, threshold)
