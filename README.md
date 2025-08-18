# 🤖 Code Writer Bot (Streamlit)

A Streamlit app that turns natural language prompts into a project plan and a ZIP of generated code files.

## Quickstart

```bash
git clone <your-repo-url>
cd code-writer-bot
pip install -r requirements.txt

# Secrets
# Create .streamlit/secrets.toml and set:
# OPENAI_API_KEY="sk-..."
# (Optional) HF_TOKEN="hf_..."

streamlit run app.py
