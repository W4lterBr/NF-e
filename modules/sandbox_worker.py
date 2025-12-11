"""Sandbox worker for isolated task execution (PDF generation, SEFAZ fetching)."""
from __future__ import annotations

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional


BASE_DIR = Path(__file__).parent.parent


def run_task(task_name: str, payload: Dict[str, Any], timeout: int = 240) -> Dict[str, Any]:
    """
    Execute a task in an isolated subprocess.
    
    Args:
        task_name: Name of the task ('generate_pdf', 'fetch_by_chave')
        payload: Task-specific data
        timeout: Timeout in seconds
    
    Returns:
        Dict with 'ok' (bool) and task-specific results
    """
    try:
        worker_script = BASE_DIR / "modules" / "sandbox_task_runner.py"
        if not worker_script.exists():
            # Fallback: create inline runner
            worker_script = BASE_DIR / "modules" / "_temp_runner.py"
            _create_temp_runner(worker_script)
        
        # Prepare JSON payload
        payload_json = json.dumps({"task": task_name, "payload": payload})
        
        # Run in subprocess with optimization flags
        env = {**os.environ.copy(), "PYTHONUNBUFFERED": "1", "PYTHONDONTWRITEBYTECODE": "1"}
        
        proc = subprocess.Popen(
            [sys.executable, "-u", str(worker_script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(BASE_DIR),
            env=env
        )
        
        stdout, stderr = proc.communicate(input=payload_json, timeout=timeout)
        
        if proc.returncode == 0:
            try:
                result = json.loads(stdout)
                return result
            except json.JSONDecodeError:
                return {"ok": False, "error": f"Invalid JSON response: {stdout[:200]}"}
        else:
            return {"ok": False, "error": stderr or stdout}
    
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except Exception:
            pass
        return {"ok": False, "error": f"Task timeout ({timeout}s)"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _create_temp_runner(path: Path):
    """Create a temporary task runner script."""
    runner_code = '''
import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

def generate_pdf(payload):
    """Generate PDF from XML."""
    try:
        import sys
        sys.path.insert(0, str(BASE_DIR))
        from modules.pdf_simple import generate_danfe_pdf
        xml_text = payload.get("xml", "")
        out_path = payload.get("out_path", "")
        tipo = payload.get("tipo", "NFe")
        
        if not xml_text or not out_path:
            return {"ok": False, "error": "Missing xml or out_path"}
        
        # Call PDF generator
        success = generate_danfe_pdf(xml_text, out_path, tipo)
        return {"ok": success, "path": out_path if success else None}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def fetch_by_chave(payload):
    """Fetch XML from SEFAZ by chave."""
    try:
        import sys
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
        return {"ok": False, "error": str(e)}

if __name__ == "__main__":
    try:
        input_data = sys.stdin.read()
        data = json.loads(input_data)
        task = data.get("task")
        payload = data.get("payload", {})
        
        if task == "generate_pdf":
            result = generate_pdf(payload)
        elif task == "fetch_by_chave":
            result = fetch_by_chave(payload)
        else:
            result = {"ok": False, "error": f"Unknown task: {task}"}
        
        print(json.dumps(result))
        sys.exit(0)
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        sys.exit(1)
'''
    path.write_text(runner_code, encoding='utf-8')
