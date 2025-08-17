from pathlib import Path
import io
import zipfile

def safe_write_files(root: Path, files: dict):
    for rel, content in files.items():
        path = (root / rel).resolve()
        if not str(path).startswith(str(root.resolve())):
            raise RuntimeError(f"Unsafe path: {rel}")
        path.parent.mkdir(parents=True, exist_ok=True)
        # Normalize newlines
        if isinstance(content, bytes):
            data = content
        else:
            data = content.replace("\r\n", "\n").encode("utf-8")
        path.write_bytes(data)

def zip_dir_to_bytes(root: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in root.rglob("*"):
            if p.is_file():
                zf.write(p, arcname=p.relative_to(root))
    buf.seek(0)
    return buf.read()
