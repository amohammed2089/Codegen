# 🤖 Code Writer Bot (Streamlit)

Turn a natural-language prompt into a file plan and a ZIP of generated code.

## Quickstart

```bash
# 1) Clone
git clone <your-repo-url>
cd code-writer-bot

# 2) Python env & deps
pip install -r requirements.txt

# 3) Secrets
# Create .streamlit/secrets.toml and set:
# OPENAI_API_KEY="sk-..."
# (Optionally) HF_TOKEN="hf_..."

# 4) Run
streamlit run app.py
