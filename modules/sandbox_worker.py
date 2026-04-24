"""Sandbox worker for isolated task execution (PDF generation, SEFAZ fetching)."""
from __future__ import annotations

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

# Import BrazilFiscalReport at top level for PyInstaller detection
BRAZILFISCALREPORT_AVAILABLE = False
Danfe = None
Dacte = None

try:
    from brazilfiscalreport.danfe import Danfe
    from brazilfiscalreport.dacte import Dacte
    BRAZILFISCALREPORT_AVAILABLE = True
    print("✅ brazilfiscalreport loaded successfully")
except ImportError as e:
    print(f"⚠️ First attempt failed: {e}")
    # Try alternative import for frozen mode
    try:
        import sys
        if getattr(sys, 'frozen', False):
            # In frozen mode, try to import from _internal
            base_path = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(sys.executable).parent / '_internal'
            sys.path.insert(0, str(base_path))
            print(f"🔍 Trying from: {base_path}")
        
        from brazilfiscalreport.danfe import Danfe
        from brazilfiscalreport.dacte import Dacte
        BRAZILFISCALREPORT_AVAILABLE = True
        print("✅ brazilfiscalreport loaded successfully (second attempt)")
    except Exception as e2:
        print(f"❌ brazilfiscalreport not available - {e2}")
        import traceback
        traceback.print_exc()

BASE_DIR = Path(__file__).parent.parent


def _run_task_direct(task_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute task directly in current process (for frozen mode).
    
    Args:
        task_name: Name of the task ('generate_pdf', 'fetch_by_chave')
        payload: Task-specific data
    
    Returns:
        Dict with 'ok' (bool) and task-specific results
    """
    try:
        if task_name == "generate_pdf":
            return _generate_pdf_direct(payload)
        elif task_name == "fetch_by_chave":
            return _fetch_by_chave_direct(payload)
        else:
            return {"ok": False, "error": f"Unknown task: {task_name}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _generate_pdf_direct(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Generate PDF directly without subprocess."""
    import sys
    from pathlib import Path
    from datetime import datetime
    
    # 🔍 DEBUG auxiliar no sandbox_worker
    def debug_sandbox(msg):
        """Log de debug do sandbox_worker"""
        try:
            import os
            appdata = os.getenv('APPDATA')
            if appdata:
                debug_dir = Path(appdata) / "Busca XML" / "logs"
            else:
                debug_dir = Path.home() / "AppData" / "Roaming" / "Busca XML" / "logs"
            
            debug_dir.mkdir(parents=True, exist_ok=True)
            debug_file = debug_dir / "nfse_pdf_debug.log"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(debug_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] [SANDBOX] {msg}\n")
            
            print(f"[SANDBOX] {msg}", file=sys.stderr)
        except:
            pass
    
    try:
        xml_text = payload.get("xml", "")
        out_path = payload.get("out_path", "")
        tipo = payload.get("tipo", "NFe")
        
        if not xml_text or not out_path:
            return {"ok": False, "error": "Missing xml or out_path"}
        
        # 🔥 NFC-e: BrazilFiscalReport não suporta - usa gerar_danfce
        if "NFC" in tipo.upper():
            print(f"[PDF] NFC-e detectada - gerando cupom térmico...", file=sys.stderr)
            try:
                from gerar_danfce import gerar_danfce
                success = gerar_danfce(xml_text, out_path)
                if success:
                    return {"ok": True, "path": out_path}
                else:
                    return {"ok": False, "error": "NFC-e PDF generation failed"}
            except Exception as e:
                return {"ok": False, "error": f"gerar_danfce error: {str(e)}"}

        # 🔥 NFS-e: BrazilFiscalReport não suporta - usa pdf_simple direto
        if "NFS" in tipo.upper():
            debug_sandbox(f"NFS-e detectada no sandbox_worker! Tipo: {tipo}")
            debug_sandbox(f"Chamando pdf_simple.generate_danfe_pdf()")
            debug_sandbox(f"Destino: {out_path}")

            print(f"[PDF] NFS-e detectada - usando pdf_simple...", file=sys.stderr)
            try:
                from modules.pdf_simple import generate_danfe_pdf
                debug_sandbox("✅ pdf_simple.generate_danfe_pdf importado com sucesso")
                
                result = generate_danfe_pdf(xml_text, out_path, tipo)
                
                # Suporta retorno dict {ok, pdf_tipo} (NFS-e) e bool legado (NF-e/CT-e)
                if isinstance(result, dict):
                    ok = result.get("ok", False)
                    pdf_tipo = result.get("pdf_tipo")
                else:
                    ok = bool(result)
                    pdf_tipo = None
                
                if ok:
                    debug_sandbox(f"✅ generate_danfe_pdf OK (pdf_tipo={pdf_tipo})")
                    if Path(out_path).exists():
                        size = Path(out_path).stat().st_size
                        debug_sandbox(f"✅ Arquivo PDF criado: {size:,} bytes")
                    else:
                        debug_sandbox(f"⚠️ generate_danfe_pdf retornou True mas arquivo não existe!")
                    return {"ok": True, "path": out_path, "pdf_tipo": pdf_tipo}
                else:
                    debug_sandbox("❌ generate_danfe_pdf retornou False/falha")
                    return {"ok": False, "error": "PDF generation failed"}
            except Exception as e:
                debug_sandbox(f"❌ EXCEÇÃO no pdf_simple: {type(e).__name__}: {str(e)}")
                import traceback
                debug_sandbox(f"Stack trace:\n{traceback.format_exc()}")
                return {"ok": False, "error": f"pdf_simple error: {str(e)}"}
        
        # NFe/CT-e: Usa BrazilFiscalReport se disponível
        if not BRAZILFISCALREPORT_AVAILABLE:
            # Fallback para pdf_simple
            print(f"[PDF] BrazilFiscalReport não disponível - usando pdf_simple...", file=sys.stderr)
            try:
                from modules.pdf_simple import generate_danfe_pdf
                success = generate_danfe_pdf(xml_text, out_path, tipo)
                if success:
                    return {"ok": True, "path": out_path}
                else:
                    return {"ok": False, "error": "PDF generation failed"}
            except Exception as e:
                return {"ok": False, "error": f"pdf_simple error: {str(e)}"}
        
        # Use BrazilFiscalReport para NFe/CT-e
        if isinstance(xml_text, str):
            xml_bytes = xml_text.encode('utf-8')
        else:
            xml_bytes = xml_text
        
        if tipo.upper() == "CTE":
            doc = Dacte(xml=xml_bytes)
            doc.output(str(out_path))
        else:  # NFe
            doc = Danfe(xml=xml_bytes)
            doc.output(str(out_path))
        
        return {"ok": True, "path": out_path}
    except Exception as e:
        # Se BrazilFiscalReport falhar, tenta pdf_simple como último recurso
        print(f"[PDF] BrazilFiscalReport falhou - tentando pdf_simple...", file=sys.stderr)
        try:
            from modules.pdf_simple import generate_danfe_pdf
            success = generate_danfe_pdf(xml_text, out_path, tipo)
            if success:
                return {"ok": True, "path": out_path}
            else:
                return {"ok": False, "error": f"Original error: {str(e)}"}
        except Exception as e2:
            return {"ok": False, "error": f"All methods failed. BrazilFiscalReport: {str(e)}, pdf_simple: {str(e2)}"}


def _fetch_by_chave_direct(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch XML from SEFAZ by chave directly without subprocess."""
    try:
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


def run_task(task_name: str, payload: Dict[str, Any], timeout: int = 240) -> Dict[str, Any]:
    """
    Execute a task in an isolated subprocess (or directly if frozen).
    
    Args:
        task_name: Name of the task ('generate_pdf', 'fetch_by_chave')
        payload: Task-specific data
        timeout: Timeout in seconds
    
    Returns:
        Dict with 'ok' (bool) and task-specific results
    """
    try:
        # Em modo frozen, executa diretamente (sem subprocess) para evitar problemas com python.exe
        if getattr(sys, 'frozen', False):
            return _run_task_direct(task_name, payload)
        
        # Modo desenvolvimento: usa subprocess
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
        
        proc = subprocess.Popen(
            [sys.executable, "-u", str(worker_script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',   # Evita UnicodeDecodeError se stderr tiver bytes não-UTF-8
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
