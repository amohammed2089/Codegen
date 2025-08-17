import json
import os
from typing import Dict, Tuple

from prompts import FILE_PLAN_SYSTEM, FILE_WRITE_SYSTEM
import streamlit as st
import requests

# OpenAI client (Responses API)
def _openai_call(model: str, messages, temperature: float) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY"))
    if not client.api_key:
        raise RuntimeError("Missing OpenAI API key. Set OPENAI_API_KEY in Streamlit secrets.")
    # Use Responses API for structured output
    resp = client.responses.create(
        model=model,
        input=messages,
        temperature=temperature,
        # Encourage valid JSON
        response_format={"type": "json_object"},
    )
    # The SDK returns content in a uniform structure
    return resp.output_text

# Simple Hugging Face Inference API fallback (text-generation)
def _hf_call(model: str, prompt: str, temperature: float) -> str:
    hf_token = st.secrets.get("HF_TOKEN") or os.getenv("HF_TOKEN")
    if not hf_token:
        raise RuntimeError("Missing HF_TOKEN. Put a token in Streamlit secrets to use Hugging Face.")

    url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {"Authorization": f"Bearer {hf_token}"}
    payload = {
        "inputs": prompt,
        "parameters": {"temperature": temperature, "max_new_tokens": 3000, "return_full_text": False}
    }
    r = requests.post(url, headers=headers, json=payload, timeout=180)
    r.raise_for_status()
    data = r.json()
    # Many providers return a list of dicts with "generated_text"
    if isinstance(data, list) and data and "generated_text" in data[0]:
        return data[0]["generated_text"]
    # Some endpoints use "choices"
    if isinstance(data, dict) and "choices" in data and data["choices"]:
        return data["choices"][0].get("text", "")
    return str(data)

def _parse_json(text: str):
    try:
        return json.loads(text)
    except Exception as e:
        # Try to extract JSON substring
        import re
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise

def generate_file_bundle(provider: str, model_name: str, user_prompt: str, target_lang: str, license_name: str, temperature: float) -> Tuple[bool, Dict]:
    try:
        # 1) Ask for a high-level file plan (JSON)
        if provider == "openai":
            plan_json = _openai_call(
                model_name,
                [
                    {"role": "system", "content": FILE_PLAN_SYSTEM},
                    {"role": "user", "content": json.dumps({
                        "prompt": user_prompt, "primary_language": target_lang, "license": license_name
                    })}
                ],
                temperature
            )
        else:
            plan_json = _hf_call(
                model_name,
                f"{FILE_PLAN_SYSTEM}\n\nUSER:\n{json.dumps({'prompt': user_prompt,'primary_language': target_lang,'license': license_name})}",
                temperature
            )
        plan = _parse_json(plan_json)

        # 2) Ask the model to write each file (batched in one JSON for simplicity)
        if provider == "openai":
            files_json = _openai_call(
                model_name,
                [
                    {"role": "system", "content": FILE_WRITE_SYSTEM},
                    {"role": "user", "content": json.dumps({"plan": plan, "prompt": user_prompt})}
                ],
                temperature
            )
        else:
            files_json = _hf_call(
                model_name,
                f"{FILE_WRITE_SYSTEM}\n\nUSER:\n{json.dumps({'plan': plan, 'prompt': user_prompt})}",
                temperature
            )
        files = _parse_json(files_json)

        if not isinstance(files, dict) or "files" not in files:
            raise RuntimeError("Model did not return the expected {\"files\": {path: content}} JSON.")

        return True, {"plan": plan, "files": files["files"]}
    except Exception as e:
        return False, f"Generation failed: {e}"
