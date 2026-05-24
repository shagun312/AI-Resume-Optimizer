# AI Resume Optimizer

Tailors your resume to any job description in seconds using free AI models.

- **CLI** — powered by [Groq](https://console.groq.com) (Llama 3, free tier)
- **Web UI** — powered by [GitHub Models](https://github.com/marketplace/models) (GPT-4o / GPT-5, free tier)

## Setup

```bash
pip install -r requirements.txt
```

For PDF export (optional):

```bash
pip install weasyprint markdown
```

For PDF resume upload (optional):

```bash
pip install pymupdf
```

## Run — Web UI

```bash
# Option A: set token in .env
echo GITHUB_TOKEN=your_token_here > .env

# Option B: paste it in the UI token box at runtime

python app.py
# open http://localhost:7860
```

Get a free GitHub token at: GitHub → Settings → Developer settings → Personal access tokens

## Run — CLI

```bash
export GROQ_API_KEY=your_key_here   # Windows: $env:GROQ_API_KEY="..."

python main.py --resume resume.md --job job_description.txt
```

Get a free Groq API key at: [console.groq.com](https://console.groq.com)

### CLI options

| Flag | Default | Description |
|---|---|---|
| `--resume` | `resume.md` | Path to your resume (Markdown or plain text) |
| `--job` | `job_description.txt` | Path to the job description |
| `--output` | `optimized_resume.md` | Output Markdown path |
| `--pdf` | `optimized_resume.pdf` | Output PDF path |
| `--model` | `llama3-8b-8192` | Groq model name |

## How it works

1. Sends your resume + job description to an LLM
2. LLM rewrites the resume — mirrors keywords, reorders bullets, adds a "Why I'm a great fit" section
3. Runs a second LLM call to analyze what changed and give a fit score
4. Outputs Markdown and PDF

## Files

```
app.py                  Web UI (Gradio)
main.py                 CLI tool
resume.md               Sample resume
job_description.txt     Sample job description
requirements.txt        Dependencies
```
