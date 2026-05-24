"""
Project 1: Resume Optimizer
Uses Groq (free llama3) to tailor your resume to a job description.
Free stack: groq + markdown + weasyprint (or pdfkit)
"""

import os
import re
import argparse
from groq import Groq

# ── helpers ──────────────────────────────────────────────────────────────────

def load_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def save_text(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def optimize_resume(client: Groq, resume_md: str, job_desc: str, model: str) -> str:
    system_prompt = """You are an expert resume writer and career coach.
Your task is to tailor the given resume to match the job description as closely as possible.
Rules:
- Keep all information truthful — never invent experience or skills.
- Reorder bullet points to highlight the most relevant achievements first.
- Mirror keywords and phrases from the job description naturally.
- Strengthen weak action verbs (use: led, built, reduced, improved, shipped, etc.).
- Output the full optimized resume in clean Markdown format.
- Add a short (3-4 bullet) "Why I'm a great fit" section at the top under the name."""

    user_prompt = f"""## Job Description
{job_desc}

## Current Resume (Markdown)
{resume_md}

Please output the fully optimized resume in Markdown."""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=4096,
    )
    return response.choices[0].message.content

def markdown_to_pdf(md_text: str, output_path: str) -> bool:
    """Try weasyprint first, fall back to pdfkit, skip if neither available."""
    try:
        import markdown
        from weasyprint import HTML
        html = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
        styled = f"""<html><head><style>
            body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.5; }}
            h1 {{ color: #2c3e50; }} h2 {{ color: #34495e; border-bottom: 1px solid #ccc; }}
            ul {{ margin: 4px 0; }} li {{ margin: 2px 0; }}
        </style></head><body>{html}</body></html>"""
        HTML(string=styled).write_pdf(output_path)
        return True
    except ImportError:
        pass
    try:
        import pdfkit
        import markdown
        html = markdown.markdown(md_text, extensions=["tables"])
        pdfkit.from_string(html, output_path)
        return True
    except Exception:
        pass
    return False

# ── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AI Resume Optimizer (free via Groq)")
    parser.add_argument("--resume", default="resume.md", help="Path to your resume (Markdown)")
    parser.add_argument("--job", default="job_description.txt", help="Path to job description")
    parser.add_argument("--output", default="optimized_resume.md", help="Output markdown path")
    parser.add_argument("--pdf", default="optimized_resume.pdf", help="Output PDF path")
    parser.add_argument("--model", default="llama3-8b-8192", help="Groq model name")
    args = parser.parse_args()

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("Set GROQ_API_KEY environment variable. Get a free key at https://console.groq.com")

    client = Groq(api_key=api_key)

    print(f"Loading resume from: {args.resume}")
    resume_md = load_text(args.resume)

    print(f"Loading job description from: {args.job}")
    job_desc = load_text(args.job)

    print(f"Optimizing resume with {args.model}...")
    optimized = optimize_resume(client, resume_md, job_desc, args.model)

    save_text(args.output, optimized)
    print(f"Saved optimized resume → {args.output}")

    print("Attempting PDF export...")
    if markdown_to_pdf(optimized, args.pdf):
        print(f"Saved PDF → {args.pdf}")
    else:
        print("PDF export skipped (install weasyprint or pdfkit for PDF output).")

    print("\n--- Preview (first 800 chars) ---")
    print(optimized[:800])

if __name__ == "__main__":
    main()
