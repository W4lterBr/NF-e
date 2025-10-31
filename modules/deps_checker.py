"""
Verificador e instalador automático de dependências para geração de PDF (DANFE/DACTE).

Uso:
    from modules.deps_checker import ensure_pdf_deps
    ensure_pdf_deps(auto_install=True)

Critério de sucesso: pelo menos um backend disponível:
- Preferido: brazil-fiscal-report (cross-platform) + qrcode[pil] para CT-e
- Alternativas: PyNFe (NF-e), erpbrasil.edoc.pdf (pode ter limitações no Windows)
- Fallback mínimo: reportlab
"""
from __future__ import annotations

import sys
import subprocess
from typing import Iterable, Tuple


PREFERRED_PKGS = [
    # Preferido: brazil-fiscal-report
    "brazil-fiscal-report",
    # CT-e QRCode
    "qrcode[pil]",
]
ALT_PYNFE = ["PyNFe"]
ALT_ERPBRASIL = [
    "erpbrasil.edoc.pdf",
    "weasyprint",
    "cairosvg",
    "tinycss2",
    "cssselect2",
]
FALLBACK_MINIMAL = ["reportlab"]


def _import_ok(mod: str) -> bool:
    try:
        __import__(mod)
        return True
    except Exception:
        return False


def _run_pip_install(pkgs: Iterable[str]) -> Tuple[bool, str]:
    """Instala os pacotes informados usando o pip do ambiente atual.
    Retorna (ok, output). Não lança exceção.
    """
    cmd = [sys.executable, "-m", "pip", "install", *pkgs]
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        ok = proc.returncode == 0
        return ok, proc.stdout
    except Exception as e:
        return False, f"pip install failed: {e}"


def has_any_pdf_backend() -> bool:
    """Retorna True se já existir um backend de PDF disponível."""
    # Preferido: brazil-fiscal-report
    if _import_ok("brazilfiscalreport"):
        return True
    # Alternativa: PyNFe
    if _import_ok("pynfe"):
        return True
    # Alternativa: erpbrasil.edoc.pdf e seus requisitos principais
    if _import_ok("erpbrasil.edoc.pdf") and all(_import_ok(m) for m in ["weasyprint", "cairosvg", "tinycss2", "cssselect2"]):
        return True
    # Fallback mínimo: reportlab
    if _import_ok("reportlab"):
        return True
    return False


def ensure_pdf_deps(auto_install: bool = True) -> bool:
    """Garante que pelo menos um backend de PDF esteja disponível.

    - Se já existir, retorna True imediatamente.
    - Se não existir e auto_install for True, tenta instalar o conjunto preferido;
      caso falhe, tenta instalar o fallback.
    - Retorna True se, ao final, algum backend estiver disponível.
    """
    if has_any_pdf_backend():
        return True

    if not auto_install:
        return False

    # Tenta instalar o conjunto preferido (brazil-fiscal-report + qrcode)
    ok, _ = _run_pip_install(PREFERRED_PKGS)
    if ok and has_any_pdf_backend():
        return True

    # Tenta PyNFe explicitamente
    okp, _ = _run_pip_install(ALT_PYNFE)
    if okp and has_any_pdf_backend():
        return True

    # Tenta erpbrasil.edoc.pdf (pode ter limitações no Windows)
    okb, _ = _run_pip_install(ALT_ERPBRASIL)
    if okb and has_any_pdf_backend():
        return True

    # Tenta fallback mínimo (reportlab)
    ok3, _ = _run_pip_install(FALLBACK_MINIMAL)
    if ok3 and has_any_pdf_backend():
        return True

    return False
