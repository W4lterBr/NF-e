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
        # Tenta encontrar o sandbox_task_runner.py em várias localizações
        possible_paths = [
            BASE_DIR / "modules" / "sandbox_task_runner.py",
            BASE_DIR / "sandbox_task_runner.py",
            Path(sys.executable).parent / "modules" / "sandbox_task_runner.py",
            Path(sys.executable).parent / "sandbox_task_runner.py",
        ]
        
        worker_script = None
        for path in possible_paths:
            if path.exists():
                worker_script = path
                break
        
        if not worker_script:
            # Fallback: create inline runner in temp folder
            import tempfile
            temp_dir = Path(tempfile.gettempdir()) / "BOT_Busca_NFE"
            temp_dir.mkdir(parents=True, exist_ok=True)
            worker_script = temp_dir / "_temp_runner.py"
            _create_temp_runner(worker_script)
        
        # Prepare JSON payload
        payload_json = json.dumps({"task": task_name, "payload": payload})
        
        # Run in subprocess with optimization flags
        env = {**os.environ.copy(), "PYTHONUNBUFFERED": "1", "PYTHONDONTWRITEBYTECODE": "1"}
        
        # CORREÇÃO: Se estamos rodando no PyInstaller, usar python.exe do sistema
        # ao invés do executável empacotado (que abrirá outra instância da interface)
        python_exe = sys.executable
        if getattr(sys, 'frozen', False):
            # Estamos rodando no PyInstaller - encontrar python.exe do sistema
            # Primeiro, tenta usar python do ambiente virtual se existir
            possible_pythons = [
                BASE_DIR / ".venv" / "Scripts" / "python.exe",  # venv local
                Path(sys.executable).parent / "python.exe",  # pasta do executável
                Path("C:/Python312/python.exe"),  # instalação padrão
                Path("C:/Python311/python.exe"),
                Path("C:/Python310/python.exe"),
            ]
            for py_path in possible_pythons:
                if py_path.exists():
                    python_exe = str(py_path)
                    break
            else:
                # Última tentativa: buscar python.exe no PATH usando shutil.which
                import shutil
                found_python = shutil.which("python.exe") or shutil.which("python3.exe")
                if found_python and Path(found_python).exists():
                    # Verifica se não é o próprio executável
                    if not found_python.lower().endswith(Path(sys.executable).name.lower()):
                        python_exe = found_python
                    else:
                        # Se o which encontrou o próprio exe, erro crítico
                        raise RuntimeError(
                            "ERRO: Python não encontrado no sistema. "
                            "Instale Python 3.10 ou superior para usar este recurso."
                        )
                else:
                    raise RuntimeError(
                        "ERRO: Python não encontrado no sistema. "
                        "Instale Python 3.10 ou superior para usar este recurso."
                    )
        
        proc = subprocess.Popen(
            [python_exe, "-u", str(worker_script)],
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
