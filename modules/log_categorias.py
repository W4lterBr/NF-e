# -*- coding: utf-8 -*-
"""
Logs separados por categoria (Problema crítico 7).

Categorias: nfe, cte, nfse, nfce, pdf, storage, database — cada uma grava em
seu próprio arquivo (logs/{categoria}.log), além de continuar passando pelo
logger geral ('nfe_search' → logs/busca_nfe_AAAA-MM-DD.log) como já acontecia.

Uso:
    from modules.log_categorias import log_falha

    try:
        ...
    except Exception as e:
        log_falha('nfe', documento=numero, chave=chave, cnpj=cnpj_emitente, erro=e)

Cada falha registrada inclui: data/hora (automático via logging), categoria,
documento, chave, CNPJ, mensagem de erro completa e traceback (quando uma
exceção está ativa no momento da chamada).
"""
from __future__ import annotations

import logging
import sys
import traceback as _traceback_module
from pathlib import Path
from typing import Optional

CATEGORIAS_VALIDAS = ("nfe", "cte", "nfse", "nfce", "pdf", "storage", "database")

_loggers_categoria: dict[str, logging.Logger] = {}


def _get_log_dir() -> Path:
    try:
        from nfe_search import get_data_dir
        return Path(get_data_dir()) / "logs"
    except Exception:
        return Path("logs")


def get_logger_categoria(categoria: str) -> logging.Logger:
    """Retorna (criando se necessário) o logger dedicado da categoria.
    Grava em logs/{categoria}.log, com nível WARNING (apenas problemas reais,
    não chatter informativo de toda a aplicação)."""
    if categoria not in CATEGORIAS_VALIDAS:
        raise ValueError(f"Categoria de log desconhecida: {categoria!r}. Use uma de {CATEGORIAS_VALIDAS}")

    if categoria in _loggers_categoria:
        return _loggers_categoria[categoria]

    log = logging.getLogger(f"categoria.{categoria}")
    log.setLevel(logging.WARNING)
    log.propagate = False  # não duplica no logger geral 'nfe_search'

    if not log.handlers:
        log_dir = _get_log_dir()
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            handler = logging.FileHandler(str(log_dir / f"{categoria}.log"), encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
            log.addHandler(handler)
        except Exception as e:
            print(f"[log_categorias] Aviso: não foi possível criar logs/{categoria}.log: {e}", file=sys.stderr)

    _loggers_categoria[categoria] = log
    return log


def log_falha(categoria: str, documento: Optional[str] = None, chave: Optional[str] = None,
              cnpj: Optional[str] = None, erro=None, nivel: str = "ERROR", **extra) -> None:
    """
    Registra uma falha estruturada em logs/{categoria}.log.

    Args:
        categoria: uma de CATEGORIAS_VALIDAS ('nfe', 'cte', 'nfse', 'nfce', 'pdf', 'storage', 'database')
        documento: identificador legível do documento (número, nome de arquivo, etc.)
        chave: chave de acesso (44/50 dígitos) quando disponível
        cnpj: CNPJ relevante (emitente/prestador/informante)
        erro: exceção ou mensagem de erro — vira "erro completo" no log;
              se chamado de dentro de um `except:`, o traceback é incluído automaticamente
        nivel: 'ERROR' (padrão) ou 'WARNING'
        **extra: campos adicionais livres (ex.: nsu=..., url=..., status_http=...)
    """
    log = get_logger_categoria(categoria)

    partes = [
        f"documento={documento or '-'}",
        f"chave={chave or '-'}",
        f"cnpj={cnpj or '-'}",
        f"erro={erro if erro is not None else '-'}",
    ]
    for k, v in extra.items():
        partes.append(f"{k}={v}")
    msg = " ".join(partes)

    tb = _traceback_module.format_exc()
    tem_traceback_ativo = bool(tb) and tb.strip() != "NoneType: None"

    log_fn = log.error if nivel.upper() == "ERROR" else log.warning
    if tem_traceback_ativo:
        log_fn(f"{msg}\n{tb}")
    else:
        log_fn(msg)
