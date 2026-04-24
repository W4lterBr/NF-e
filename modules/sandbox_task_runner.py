"""
Sandbox task runner - Executes isolated tasks (PDF generation, SEFAZ fetching).
This script is called by sandbox_worker.py as a subprocess.
"""
import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent


def generate_pdf(payload):
    """Generate PDF from XML."""
    try:
        sys.path.insert(0, str(BASE_DIR))
        from modules.pdf_simple import generate_danfe_pdf
        
        xml_text = payload.get("xml", "")
        out_path = payload.get("out_path", "")
        tipo = payload.get("tipo", "NFe")
        
        if not xml_text or not out_path:
            return {"ok": False, "error": "Missing xml or out_path"}
        
        # Call PDF generator — suporta retorno dict {ok, pdf_tipo} (NFS-e) e bool legado
        raw = generate_danfe_pdf(xml_text, out_path, tipo)
        if isinstance(raw, dict):
            ok = raw.get("ok", False)
            pdf_tipo = raw.get("pdf_tipo")
        else:
            ok = bool(raw)
            pdf_tipo = None
        return {"ok": ok, "path": out_path if ok else None, "pdf_tipo": pdf_tipo}
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}


def fetch_by_chave(payload):
    """Fetch XML from SEFAZ by chave."""
    try:
        sys.path.insert(0, str(BASE_DIR))
        from nfe_search import NFeService
        
        cert_data = payload.get("cert", {})
        chave = payload.get("chave", "")
        prefer = payload.get("prefer", ["nfeProc", "NFe"])
        
        if not chave or not cert_data.get("path"):
            return {"ok": False, "error": "Missing cert or chave"}
        
        # Create service
        svc = NFeService(
            cert_data.get("path"),
            cert_data.get("senha", ""),
            cert_data.get("cnpj", ""),
            cert_data.get("cuf", "")
        )
        
        # Fetch by chave
        xml = svc.fetch_by_chave(chave, prefer=prefer)
        if xml:
            return {"ok": True, "data": {"xml": xml}}
        else:
            return {"ok": False, "error": "XML not found"}
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}


if __name__ == "__main__":
    try:
        input_data = sys.stdin.read()
        data = json.loads(input_data)
        task = data.get("task")
        payload = data.get("payload", {})

        # Redirect stdout → stderr while running the task so that library
        # messages (e.g. WeasyPrint startup warnings) do not pollute the
        # JSON line that the parent process reads from stdout.
        _real_stdout = sys.stdout
        sys.stdout = sys.stderr

        if task == "generate_pdf":
            result = generate_pdf(payload)
        elif task == "fetch_by_chave":
            result = fetch_by_chave(payload)
        else:
            result = {"ok": False, "error": f"Unknown task: {task}"}

        sys.stdout = _real_stdout
        print(json.dumps(result))
        sys.exit(0)
    except Exception as e:
        import traceback
        try:
            sys.stdout = _real_stdout  # type: ignore[name-defined]
        except Exception:
            pass
        print(json.dumps({"ok": False, "error": str(e), "traceback": traceback.format_exc()}))
        sys.exit(1)
