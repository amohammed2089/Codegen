import io
import json
import shutil
import tempfile
from pathlib import Path
import streamlit as st

from llm_backend import generate_file_bundle
from utils import safe_write_files, zip_dir_to_bytes

st.set_page_config(page_title="Code Writer Bot", page_icon="🤖")

st.title("🤖 Code Writer Bot")
st.caption("Give me a prompt. I’ll plan the files and write the code.")

with st.sidebar:
    st.header("Settings")
    provider = st.selectbox(
        "Model provider",
        ["openai (Responses API)", "huggingface (Inference API)"],
        index=0,
    )
    model_name = st.text_input(
        "Model name",
        value="gpt-4.1-mini" if provider.startswith("openai") else "Qwen2.5-Coder-7B-Instruct",
        help="Use an available model for your account/provider."
    )
    temperature = st.slider("Temperature", 0.0, 1.0, 0.2, 0.05)

st.write("### Prompt")
user_prompt = st.text_area(
    "Describe the project or the file(s) you want me to generate:",
    height=180,
    placeholder="Example: Build a FastAPI service with /health and /summarize endpoints, Dockerfile, tests, and CI.",
)

colA, colB = st.columns(2)
with colA:
    target_lang = st.text_input("Primary language (optional)", value="python")
with colB:
    license_name = st.text_input("License (optional)", value="MIT")

if st.button("Generate Code", type="primary", disabled=not user_prompt.strip()):
    with st.spinner("Thinking, planning files, and generating code..."):
        ok, result = generate_file_bundle(
            provider=provider.split()[0],
            model_name=model_name.strip(),
            user_prompt=user_prompt.strip(),
            target_lang=target_lang.strip(),
            license_name=license_name.strip(),
            temperature=temperature,
        )

    if not ok:
        st.error(result)
    else:
        st.success("Code generated!")
        st.write("### Planned Files")
        st.json(result["plan"], expanded=False)

        st.write("### Preview (first few files)")
        preview_count = 0
        for path, content in result["files"].items():
            if preview_count >= 6:
                st.info("Showing first 6 files only.")
                break
            with st.expander(path, expanded=preview_count < 3):
                st.code(content, language="python" if path.endswith(".py") else None)
            preview_count += 1

        # Offer ZIP download
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            safe_write_files(tmpdir, result["files"])
            zip_bytes = zip_dir_to_bytes(tmpdir)
        st.download_button(
            label="⬇️ Download ZIP",
            data=zip_bytes,
            file_name="generated_project.zip",
            mime="application/zip",
        )

st.divider()
st.caption("Tip: Store your API keys with Streamlit secrets. See README for setup.")
