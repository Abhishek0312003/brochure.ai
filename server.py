from flask import Flask, Response, request, jsonify
from flask_cors import CORS
import subprocess
import sys
import os
import requests as req

app = Flask(__name__)
CORS(app)


# ── Health check helpers ──────────────────────────────────────────────────────

def check_ollama():
    """Check if Ollama is running and return available models."""
    try:
        r = req.get("http://localhost:11434/api/tags", timeout=3)
        if r.status_code == 200:
            models = [m["name"] for m in r.json().get("models", [])]
            return True, models
        return False, []
    except Exception as e:
        return False, []

def check_playwright():
    """Check if Playwright + Chromium is installed."""
    try:
        result = subprocess.run(
            [sys.executable, "-c", "from playwright.sync_api import sync_playwright; print('ok')"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() == "ok"
    except Exception:
        return False

def check_scraper_file():
    """Check if brochureai.py exists next to server.py."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brochureai.py")
    return os.path.exists(path)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    """Full system health check — called by the UI on load."""
    ollama_ok, models = check_ollama()
    playwright_ok     = check_playwright()
    scraper_ok        = check_scraper_file()

    all_ok = ollama_ok and playwright_ok and scraper_ok

    status = {
        "ok": all_ok,
        "checks": {
            "ollama":     {"ok": ollama_ok,    "models": models,
                           "hint": "Run: ollama serve" if not ollama_ok else ""},
            "playwright": {"ok": playwright_ok,
                           "hint": "Run: playwright install chromium" if not playwright_ok else ""},
            "scraper":    {"ok": scraper_ok,
                           "hint": "brochureai.py not found next to server.py" if not scraper_ok else ""},
            "server":     {"ok": True, "hint": ""},
        }
    }

    print("\n[HEALTH CHECK]")
    for name, info in status["checks"].items():
        icon = "✓" if info["ok"] else "✗"
        hint = f"  ← {info['hint']}" if info.get("hint") else ""
        print(f"  {icon} {name:<12}{hint}")
    if ollama_ok:
        print(f"    models: {', '.join(models) if models else 'none loaded'}")
    print()

    return jsonify(status)


@app.route("/run", methods=["POST"])
def run_scraper():
    data = request.json
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    def generate():
        process = subprocess.Popen(
            [sys.executable, "-u", "brochureai.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        process.stdin.write(url + "\n")
        process.stdin.flush()
        process.stdin.close()

        for line in iter(process.stdout.readline, ""):
            yield f"data: {line.rstrip()}\n\n"

        process.wait()
        yield "data: __DONE__\n\n"

    return Response(generate(), mimetype="text/event-stream")


@app.route("/file")
def get_file():
    path = request.args.get("path", "")
    if not path or ".." in path:
        return "Forbidden", 403
    full = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
    if not os.path.exists(full):
        return "Not found", 404
    with open(full, "rb") as f:
        data = f.read()
    mime = "application/octet-stream"
    if path.endswith(".json"):  mime = "application/json"
    elif path.endswith(".txt"): mime = "text/plain"
    elif path.endswith(".html"):mime = "text/html"
    return Response(data, mimetype=mime, headers={
        "Content-Disposition": f"attachment; filename={os.path.basename(path)}"
    })


if __name__ == "__main__":
    print("=" * 52)
    print("  Brochure.AI Server  —  http://localhost:5050")
    print("=" * 52)

    # run health check on startup
    ollama_ok, models = check_ollama()
    playwright_ok     = check_playwright()
    scraper_ok        = check_scraper_file()

    checks = [
        ("Flask server",  True,          ""),
        ("Ollama",        ollama_ok,      "ollama serve"),
        ("Playwright",    playwright_ok,  "playwright install chromium"),
        ("brochureai.py", scraper_ok,     "file missing — check directory"),
    ]

    print("\n[STARTUP CHECK]")
    all_ok = True
    for name, ok, fix in checks:
        icon = "✓" if ok else "✗"
        hint = f"  ← fix: {fix}" if not ok and fix else ""
        print(f"  {icon} {name:<16}{hint}")
        if not ok: all_ok = False

    if ollama_ok and models:
        print(f"\n  Ollama models loaded: {', '.join(models)}")
    elif ollama_ok:
        print("\n  ⚠ Ollama running but no models loaded — run: ollama pull llama3.2")

    print(f"\n  {'✓ All systems ready!' if all_ok else '⚠ Some checks failed — see above'}")
    print("=" * 52 + "\n")

    app.run(port=5050, debug=False)