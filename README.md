#  Brochure.AI

> Scrape any website → extract content → generate a professional brochure (JSON + PDF) using a local or cloud AI model.

---

## 📁 Project Structure

```
Brochure.ai/
├── brochureai.py        # Main scraper + AI pipeline
├── server.py            # Local Flask server (bridges UI ↔ scraper)
├── terminal_ui.html     # Browser-based terminal UI
├── requirements.txt     # Python dependencies
├── README.md
├── pages/               # Saved HTML + text per domain
│   └── example.com/
│       ├── page.html
│       ├── page.txt
│       └── brochure.json
└── images/              # Downloaded images per domain
    └── example.com/
```

---

## ⚙️ Requirements

- Python 3.9+
- Node.js (optional, only if you extend the project)
- A running AI model — local (Ollama) **or** cloud API (OpenAI, Groq, etc.)

---

## 🚀 Setup & Installation

### 1. Clone / Download the project

```powershell
cd "D:\AI Course Resource\Pratice"
# place all files in Brochure.ai folder
```

### 2. Create and activate virtual environment

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install Python dependencies

```powershell
pip install -r requirements.txt
```

### 4. Install Playwright browser (one time only)

```powershell
playwright install chromium
```

---

## 🤖 AI Model Configuration

The project supports **local Ollama** or any **cloud API** (OpenAI, Groq, Anthropic, etc.).
Edit the top of `brochureai.py` to switch between them.

---

### Option A — Ollama (Local, Free, Default)

**Install Ollama:** https://ollama.com/download

```powershell
# Pull the model (one time)
ollama pull llama3.2

# Start Ollama server (keep this terminal open)
ollama serve
```

`brochureai.py` config (already set by default):

```python
from openai import OpenAI

OLLAMA_BASE_URL = "http://localhost:11434/v1"
ollama = OpenAI(base_url=OLLAMA_BASE_URL, api_key='ollama')

# In chat calls:
model="llama3.2"
```

Other models you can pull and use:
```powershell
ollama pull mistral        # faster, lighter
ollama pull llama3.1:8b    # better quality
ollama pull gemma2         # Google's model
ollama pull phi3           # Microsoft, very fast
```

---

### Option B — OpenAI API (GPT-4o, GPT-4, GPT-3.5)

**Get API key:** https://platform.openai.com/api-keys

```powershell
pip install openai
```

Edit `brochureai.py`:

```python
from openai import OpenAI

ollama = OpenAI(api_key="sk-YOUR_OPENAI_API_KEY_HERE")

# In chat calls change model to:
model="gpt-4o"           # best quality
# or
model="gpt-3.5-turbo"    # cheaper, faster
```

Remove or comment out `OLLAMA_BASE_URL` — not needed for OpenAI.

---

### Option C — Groq API (Fast, Free tier available)

**Get API key:** https://console.groq.com

```powershell
pip install groq
```

Edit `brochureai.py`:

```python
from groq import Groq

ollama = Groq(api_key="gsk_YOUR_GROQ_API_KEY_HERE")

# In chat calls change model to:
model="llama3-8b-8192"       # fast + free tier
# or
model="mixtral-8x7b-32768"   # longer context
# or
model="llama-3.1-70b-versatile"  # best quality on Groq
```

---

### Option D — Anthropic Claude API

**Get API key:** https://console.anthropic.com

```powershell
pip install anthropic
```

Edit `brochureai.py`:

```python
import anthropic

client = anthropic.Anthropic(api_key="sk-ant-YOUR_KEY_HERE")

# Replace ollama.chat.completions.create(...) calls with:
resp = client.messages.create(
    model="claude-3-5-haiku-20241022",   # fast + affordable
    # or "claude-opus-4-6"              # best quality
    max_tokens=1200,
    messages=[{"role": "user", "content": prompt}]
)
answer = resp.content[0].text
```

---

### Option E — Google Gemini API

**Get API key:** https://aistudio.google.com/app/apikey

```powershell
pip install google-generativeai
```

Edit `brochureai.py`:

```python
import google.generativeai as genai

genai.configure(api_key="YOUR_GEMINI_API_KEY")
model_obj = genai.GenerativeModel("gemini-1.5-flash")  # or gemini-1.5-pro

# Replace ollama calls with:
resp = model_obj.generate_content(prompt)
answer = resp.text
```

---

### Option F — xAI Grok API

**Get API key:** https://console.x.ai

```powershell
pip install openai   # Grok uses OpenAI-compatible API
```

Edit `brochureai.py`:

```python
from openai import OpenAI

ollama = OpenAI(
    api_key="xai-YOUR_GROK_API_KEY_HERE",
    base_url="https://api.x.ai/v1"
)

# In chat calls:
model="grok-beta"
```

---

## ▶️ Running the Project

You need **two terminals** open at the same time.

### Terminal 1 — Start Ollama (skip if using cloud API)

```powershell
ollama serve
```

### Terminal 2 — Start Flask server

```powershell
cd "D:\AI Course Resource\Pratice\Brochure.ai"
.venv\Scripts\activate
python server.py
```

You should see:

```
====================================================
  Brochure.AI Server  —  http://localhost:5050
====================================================
[STARTUP CHECK]
  ✓ Flask server
  ✓ Ollama
  ✓ Playwright
  ✓ brochureai.py
  ✓ All systems ready!
====================================================
```

### Open the UI

Double-click `terminal_ui.html` or run:

```powershell
start terminal_ui.html
```

Enter any URL and press **RUN**.

---

## 📤 Outputs

After a successful run, files are saved under `pages/<domain>/` and `images/<domain>/`:

| File | Description |
|------|-------------|
| `page.html` | Full rendered HTML of main page |
| `page.txt` | Plain text extracted from main page |
| `brochure.json` | Structured brochure data (all fields) |
| `brochure_raw.txt` | Raw LLM output (only if JSON parse failed) |
| `<slug>.html` | HTML of each useful subpage |
| `<slug>.txt` | Text of each useful subpage |

Images saved under `images/<domain>/`:
- `main_image_0.jpg` — images from landing page
- `<slug>_img_0.jpg` — images from subpages

Download any of these directly from the terminal UI after the run.

---

## 🛠️ Troubleshooting

| Problem | Fix |
|---------|-----|
| `UnicodeEncodeError` on Windows | Already fixed — `sys.stdout.reconfigure(encoding='utf-8')` is set |
| `playwright install` not found | Run: `playwright install chromium` |
| Ollama not responding | Run: `ollama serve` in a separate terminal |
| JSON parse failed | Batching handles this automatically — check `brochure_raw.txt` if it still fails |
| Server offline in UI | Make sure `python server.py` is running before opening the HTML |
| 0 links found | Site may block scrapers — try a different URL |
| PDF is empty | Run the scraper first — PDF reads from `brochure.json` |

---

## 📦 requirements.txt

```
openai
requests
beautifulsoup4
playwright
flask
flask-cors
```

Install with:
```powershell
pip install -r requirements.txt
```

---

## 📝 Notes

- **llama3.2** has a small context window (~4k tokens). The pipeline uses batching to handle large sites.
- Cloud APIs (GPT-4o, Claude, Groq) have much larger context windows and will give richer brochure content.
- Playwright launches a headless Chromium browser — this handles React/Vue/Next.js sites that `requests` cannot scrape.
- All scraped data stays **100% local** when using Ollama.

---

*Built with Python · Playwright · Ollama · Flask · jsPDF*