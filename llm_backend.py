import json
import os
from typing import Dict, Tuple

import requests
import streamlit as st

from prompts import FILE_PLAN_SYSTEM, FILE_WRITE_SYSTEM

# ---------- OpenAI (Responses API) ----------
def _openai_call(model: str, messages, temperature: float) -> str:
    """
    Calls the OpenAI Responses API with JSON mode enabled.
    Returns the raw text output (which we expect to be JSON).
    """
    from openai import OpenAI

    client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY"))
    if not (client.api_key):
        raise RuntimeError("Missing OpenAI API key. Set OPENAI_API_KEY in Streamlit secrets or env.")

    resp = client.responses.create(
        model=model,
        input=messages,
        temperature=temperature,
        # JSON mode for Responses API
        text={"format": {"type": "json_object"}},
    )
    return resp.output_text  # SDK helper to read text from the response


# ---------- Hugging Face (Inference API) ----------
def _hf_call(model: str, prompt: str, temperature: float) -> str:
    """
    Calls Hugging Face Inference API for a simple text-generation fallback.
    """
    hf_token = st.secrets.get("HF_TOKEN") or os.getenv("HF_TOKEN")
    if not hf_token:
        raise RuntimeError("Missing HF_TOKEN. Put a token in Streamlit secrets to use Hugging Face.")

    url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {"Authorization": f"Bearer {hf_token}"}
    payload = {
        "inputs": prompt,
        "parameters": {"temperature": temperature, "max_new_tokens": 3000, "return_full_text": False},
    }
    r = requests.post(url, headers=headers, json=payload, timeout=180)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, list) and data and "generated_text" in data[0]:
        return data[0]["generated_text"]
    if isinstance(data, dict) and "choices" in data and data["choices"]:
        return data["choices"][0].get("text", "")
    return str(data)


def _parse_json(text: str):
    """
    Best-effort JSON extraction. Tries a full parse, then a { ... } substring.
    """
    try:
        return json.loads(text)
    except Exception:
        import re
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise


def generate_file_bundle(
    provider: str,
    model_name: str,
    user_prompt: str,
    target_lang: str,
    license_name: str,
    temperature: float,
) -> Tuple[bool, Dict]:
    """
    Orchestrates two model calls:
      1) FILE PLAN  -> JSON describing files/stack/commands
      2) FILE WRITE -> JSON {"files": {"path": "content", ...}}
    """
    try:
        # ---- 1) PLAN ----
        if provider == "openai":
            plan_json_text = _openai_call(
                model=model_name,
                messages=[
                    {"role": "system", "content": FILE_PLAN_SYSTEM},
                    {"role": "user", "content": json.dumps(
                        {"prompt": user_prompt, "primary_language": target_lang, "license": license_name}
                    )},
                ],
                temperature=temperature,
            )
        else:
            plan_json_text = _hf_call(
                model=model_name,
                prompt=f"{FILE_PLAN_SYSTEM}\n\nUSER:\n{json.dumps({'prompt': user_prompt, 'primary_language': target_lang, 'license': license_name})}",
                temperature=temperature,
            )

        plan = _parse_json(plan_json_text)

        # ---- 2) WRITE ----
        if provider == "openai":
            files_json_text = _openai_call(
                model=model_name,
                messages=[
                    {"role": "system", "content": FILE_WRITE_SYSTEM},
                    {"role": "user", "content": json.dumps({"plan": plan, "prompt": user_prompt})},
                ],
                temperature=temperature,
            )
        else:
            files_json_text = _hf_call(
                model=model_name,
                prompt=f"{FILE_WRITE_SYSTEM}\n\nUSER:\n{json.dumps({'plan': plan, 'prompt': user_prompt})}",
                temperature=temperature,
            )

        files_obj = _parse_json(files_json_text)

        if not isinstance(files_obj, dict) or "files" not in files_obj:
            raise RuntimeError('Model did not return expected JSON: {"files": {path: content}}.')

        return True, {"plan": plan, "files": files_obj["files"]}

    except Exception as e:
        return False, f"Generation failed: {e}"
