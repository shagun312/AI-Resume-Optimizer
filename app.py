"""
Project 1: AI Resume Optimizer — Gradio UI
Provider: GitHub Models (free — openai/gpt-4o, gpt-5, llama, mistral)

Run:
    pip install -r requirements.txt
    # Add your token to ../.env  OR  paste it in the UI
    python app.py
Then open http://localhost:7860
"""

import os
import sys
import tempfile
from pathlib import Path

import gradio as gr

# Allow importing shared llm.py from parent folder
sys.path.insert(0, str(Path(__file__).parent.parent))
from llm import get_client, chat, MODELS

# ── optional deps ─────────────────────────────────────────────────────────────
try:
    import fitz         # PyMuPDF — read PDF resumes
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    import markdown as md_lib
    from xhtml2pdf import pisa
    HAS_PDF_EXPORT = True
except (ImportError, OSError):
    HAS_PDF_EXPORT = False

# ── prompts ───────────────────────────────────────────────────────────────────

SYSTEM_OPTIMIZE = """You are an expert resume writer and an experienced career coach at top tech companies.
Your job is to tailor the given resume to match a specific job description.

STRICT RULES:
1. NEVER invent experience, skills, or achievements — only reframe what exists.
2. Mirror exact keywords and phrases from the job description naturally throughout.
3. Reorder bullet points within each role so the most relevant achievements come first.
4. Upgrade weak action verbs → use: led, built, designed, reduced, shipped, owned, scaled, drove, architected.
5. Add a "Why I'm a Great Fit" section (3-4 bullets) right below the name/contact header.
6. Do NOT add new jobs, new education, or skills that weren't in the original.
7. Output the complete optimized resume in clean Markdown — nothing else."""

SYSTEM_ANALYZE = """You are a resume coach reviewing what changed between an original and an optimized resume.
Be specific and concise. Format your response exactly as:

### What Was Improved
- [specific change 1]
- [specific change 2]
...

### Keywords Injected from Job Description
- [keyword/phrase 1]
- [keyword/phrase 2]
...

### Fit Score
**X / 10** — [one sentence reason]

Keep the whole analysis under 250 words."""

# ── helpers ───────────────────────────────────────────────────────────────────

def read_uploaded_file(file_path: str) -> str:
    if not file_path:
        return ""
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        if not HAS_PYMUPDF:
            return "Install pymupdf to upload PDFs:  pip install pymupdf"
        doc = fitz.open(file_path)
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return text.strip()
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read().strip()

def save_as_markdown(text: str) -> str:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".md", mode="w", encoding="utf-8")
    tmp.write(text)
    tmp.close()
    return tmp.name

def save_as_pdf(text: str) -> str | None:
    if not HAS_PDF_EXPORT:
        return None
    html_body = md_lib.markdown(text, extensions=["tables", "fenced_code"])
    styled_html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
  body  {{ font-family: Arial, sans-serif; margin: 48px;
           line-height: 1.6; color: #1a1a1a; font-size: 11pt; }}
  h1   {{ color: #0d1117; font-size: 20pt; margin-bottom: 4px; }}
  h2   {{ color: #24292f; font-size: 13pt; border-bottom: 1.5px solid #d0d7de;
          padding-bottom: 4px; margin-top: 20px; }}
  h3   {{ color: #24292f; font-size: 11pt; margin-bottom: 4px; }}
  ul   {{ margin: 4px 0 10px 0; padding-left: 22px; }}
  li   {{ margin: 3px 0; }}
  a    {{ color: #0969da; }}
</style></head><body>{html_body}</body></html>"""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.close()
    with open(tmp.name, "wb") as f:
        pisa.CreatePDF(styled_html, dest=f)
    return tmp.name

# ── core handler (streaming generator) ───────────────────────────────────────

def run_optimizer(resume_text: str, job_text: str, model_label: str, token: str):
    """
    Yields: (optimized_md, analysis_md, dl_md_path, dl_pdf_path, status_msg)
    Using yield makes this a generator → Gradio streams updates live to the UI.
    """
    # ── validation ────────────────────────────────────────────────────────────
    resume_text = resume_text.strip()
    job_text    = job_text.strip()

    if not resume_text:
        yield "", "", None, None, "⚠️ Paste your resume or upload a file first."
        return
    if not job_text:
        yield "", "", None, None, "⚠️ Paste the job description first."
        return

    try:
        client = get_client(token)
    except EnvironmentError as e:
        yield "", "", None, None, f"⚠️ {e}"
        return

    model = MODELS.get(model_label, "openai/gpt-4o-mini")

    # ── step 1: optimize ──────────────────────────────────────────────────────
    yield "", "", None, None, f"⏳ Optimizing your resume with **{model}**…"
    try:
        optimized = chat(
            client,
            messages=[
                {"role": "system", "content": SYSTEM_OPTIMIZE},
                {"role": "user",   "content": f"## Job Description\n{job_text}\n\n## Current Resume\n{resume_text}"},
            ],
            model=model,
            temperature=0.3,
            max_tokens=4096,
        )
    except Exception as e:
        yield "", "", None, None, f"❌ API error during optimization: {e}"
        return

    yield optimized, "", None, None, "⏳ Analyzing what changed…"

    # ── step 2: analyze ───────────────────────────────────────────────────────
    try:
        analysis = chat(
            client,
            messages=[
                {"role": "system", "content": SYSTEM_ANALYZE},
                {"role": "user",   "content": (
                    f"## Job Description\n{job_text}\n\n"
                    f"## Original Resume\n{resume_text}\n\n"
                    f"## Optimized Resume\n{optimized}"
                )},
            ],
            model=model,
            temperature=0.2,
            max_tokens=600,
        )
    except Exception as e:
        analysis = f"_Analysis failed: {e}_"

    # ── step 3: save files ────────────────────────────────────────────────────
    md_path  = save_as_markdown(optimized)
    pdf_path = save_as_pdf(optimized)

    pdf_note = (
        "" if pdf_path
        else "\n\n---\n_PDF export: `pip install xhtml2pdf markdown`_"
    )

    yield optimized, analysis + pdf_note, md_path, pdf_path, "Resume is optimized and ready to download!"

# ── Gradio UI ─────────────────────────────────────────────────────────────────

CSS = """
#title       { text-align: center; }
#footer-note { text-align: center; font-size: 0.82em; color: #666; }
#status-bar  { min-height: 30px; font-size: 0.9em; }
footer       { display: none !important; }
"""

def build_ui():
    with gr.Blocks(title="AI Resume Optimizer") as demo:

        # ── header ────────────────────────────────────────────────────────────
        gr.Markdown("# 🎯 AI Resume Optimizer", elem_id="title")
        gr.Markdown(
            "Tailors your resume to any job description in seconds.  \n"
            "Powered by **GitHub Models** (GPT-4o / GPT-5 / Llama — free tier).",
            elem_id="title",
        )

        # ── settings bar (token + model) ─────────────────────────────────────
        with gr.Row():
            token_box = gr.Textbox(
                label="GitHub Token  (or set GITHUB_TOKEN in .env)",
                placeholder="github_pat_… or ghp_…",
                type="password",
                scale=4,
            )
            model_dd = gr.Dropdown(
                choices=list(MODELS.keys()),
                value="gpt-4o-mini  (fast & cheap)",
                label="Model",
                scale=2,
            )

        # ── input row ─────────────────────────────────────────────────────────
        with gr.Row(equal_height=False):
            with gr.Column(scale=1):
                gr.Markdown("### 📄 Your Resume")
                upload_btn = gr.File(
                    label="Upload  (.md / .txt / .pdf)",
                    file_types=[".md", ".txt", ".pdf"],
                    type="filepath",
                )
                resume_box = gr.Textbox(
                    label="Or paste resume text / Markdown",
                    placeholder="Paste your resume here…",
                    lines=16,
                    max_lines=40,
                )

            with gr.Column(scale=1):
                gr.Markdown("### 💼 Job Description")
                job_box = gr.Textbox(
                    label="Paste the full job posting",
                    placeholder="Copy-paste the entire job description here…",
                    lines=20,
                    max_lines=40,
                )

        # ── action + status ───────────────────────────────────────────────────
        with gr.Row():
            run_btn = gr.Button("Optimize My Resume", variant="primary", scale=1)

        status_md = gr.Markdown("", elem_id="status-bar")

        # ── output row ────────────────────────────────────────────────────────
        with gr.Row(equal_height=False):
            with gr.Column(scale=3):
                gr.Markdown("### Optimized Resume")
                output_md = gr.Markdown(value="_Your optimized resume will appear here…_", height=540)

            with gr.Column(scale=2):
                gr.Markdown("### What Changed")
                analysis_md = gr.Markdown(value="_Analysis will appear here…_", height=540)

        # ── download row ──────────────────────────────────────────────────────
        with gr.Row():
            dl_md  = gr.File(label="⬇️  Download .md",  scale=1)
            dl_pdf = gr.File(label="⬇️  Download .pdf", scale=1)

        # ── footer ────────────────────────────────────────────────────────────
        gr.Markdown(
            "**Get a free GitHub token:** "
            "[github.com → Settings → Developer settings → PAT](https://github.com/settings/tokens)",
            elem_id="footer-note",
        )

        # ── wire up events ────────────────────────────────────────────────────
        upload_btn.change(
            fn=read_uploaded_file,
            inputs=[upload_btn],
            outputs=[resume_box],
        )

        run_btn.click(
            fn=run_optimizer,
            inputs=[resume_box, job_box, model_dd, token_box],
            outputs=[output_md, analysis_md, dl_md, dl_pdf, status_md],
        )

    return demo

# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AI Resume Optimizer")
    parser.add_argument("--port",  type=int, default=7860)
    parser.add_argument("--share", action="store_true", help="Public Gradio share link")
    args = parser.parse_args()

    demo = build_ui()
    demo.launch(
        server_port=args.port,
        share=args.share,
        inbrowser=True,
        theme=gr.themes.Soft(),
        css=CSS,
    )
