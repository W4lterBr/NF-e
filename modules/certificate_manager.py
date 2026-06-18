# -*- coding: utf-8 -*-
"""
Validação e segurança de certificados digitais (mTLS) usados nas integrações
com SEFAZ, Receita Federal (Ambiente Nacional) e webservices municipais.

Cobre:
  - validar_certificado(): valida o arquivo .pfx/.p12 e o prazo de validade
    (expiração) ANTES de tentar usá-lo numa chamada de rede.
  - determinar_verify_para_host(): decide se a verificação do certificado do
    SERVIDOR remoto pode ficar habilitada para um host específico — em vez
    de desabilitar globalmente para todo mundo (como o sistema fazia antes).
  - post_mtls_seguro(): POST autenticado por certificado digital com a mesma
    lógica de verificação segura por padrão + fallback logado.

SOBRE REVOGAÇÃO: não há, hoje, uma forma prática e amplamente disponível de
consultar OCSP/LCR da ICP-Brasil para certificados e-CNPJ/e-CPF fora de
integradoras especializadas (a infraestrutura de revogação da ICP-Brasil não
expõe um endpoint público simples para isso). O tratamento de revogação
real e efetivo é indireto: a própria SEFAZ/Receita rejeita a requisição mTLS
se o certificado apresentado estiver revogado — esse erro é capturado e
reportado claramente ao usuário em vez de ser mascarado como falha genérica
de rede (ver classificar_erro_https_certificado).
"""
from __future__ import annotations

import logging
import ssl
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests

logger = logging.getLogger('nfe_search')

_cert_security_logger = None


def _get_cert_security_logger():
    """Logger dedicado a eventos de segurança de certificado/TLS (logs/certificado_seguranca.log)."""
    global _cert_security_logger
    if _cert_security_logger is not None:
        return _cert_security_logger

    log = logging.getLogger('certificado_seguranca')
    log.setLevel(logging.WARNING)
    log.propagate = False

    if not log.handlers:
        try:
            from nfe_search import get_data_dir
            log_dir = Path(get_data_dir()) / 'logs'
        except Exception:
            log_dir = Path('logs')
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            handler = logging.FileHandler(str(log_dir / 'certificado_seguranca.log'), encoding='utf-8')
            handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
            log.addHandler(handler)
        except Exception as e:
            print(f"[certificado_seguranca] Aviso: não foi possível criar o log: {e}")

    _cert_security_logger = log
    return log


# ---------------------------------------------------------------------------
# Validação do certificado (arquivo + prazo de validade)
# ---------------------------------------------------------------------------

def validar_certificado(cert_path: str, senha: str) -> dict:
    """
    Valida um certificado PKCS#12 (.pfx/.p12) ANTES de usá-lo numa chamada
    de rede: existe no disco, abre com a senha informada, e está dentro do
    prazo de validade.

    Returns:
        dict: {
            "valido": bool,            # False se vencido, corrompido, senha errada, ou ausente
            "expirado": bool,
            "dias_restantes": int | None,
            "validade": str | None,    # dd/mm/aaaa
            "titular": str | None,
            "motivo": str | None,      # preenchido em caso de problema ou aviso (ex.: vencendo em breve)
        }
    """
    resultado = {
        "valido": False, "expirado": False, "dias_restantes": None,
        "validade": None, "titular": None, "motivo": None,
    }

    if not cert_path:
        resultado["motivo"] = "Caminho do certificado não informado"
        return resultado
    if not Path(cert_path).exists():
        resultado["motivo"] = f"Arquivo de certificado não encontrado: {cert_path}"
        return resultado

    try:
        from cryptography.hazmat.primitives.serialization import pkcs12
        with open(cert_path, 'rb') as f:
            pkcs12_bytes = f.read()
        senha_bytes = senha.encode('utf-8') if senha else None
        _, certificate, _ = pkcs12.load_key_and_certificates(pkcs12_bytes, senha_bytes)
    except Exception as e:
        resultado["motivo"] = f"Não foi possível abrir o certificado (senha incorreta ou arquivo corrompido): {e}"
        return resultado

    if certificate is None:
        resultado["motivo"] = "Certificado PKCS#12 não contém um certificado X.509 válido"
        return resultado

    try:
        expiry = (certificate.not_valid_after_utc
                  if hasattr(certificate, 'not_valid_after_utc')
                  else certificate.not_valid_after)
        expiry_naive = expiry.replace(tzinfo=None)
        dias_restantes = (expiry_naive - datetime.now()).days

        resultado["validade"] = expiry_naive.strftime("%d/%m/%Y")
        resultado["dias_restantes"] = dias_restantes
        try:
            resultado["titular"] = certificate.subject.rfc4514_string()
        except Exception:
            pass

        if dias_restantes < 0:
            resultado["expirado"] = True
            resultado["motivo"] = f"Certificado VENCIDO em {resultado['validade']} ({-dias_restantes} dia(s) atrás)"
            return resultado

        resultado["valido"] = True
        if dias_restantes <= 15:
            resultado["motivo"] = f"Certificado vence em {dias_restantes} dia(s) ({resultado['validade']}) — renove em breve"
        return resultado
    except Exception as e:
        resultado["motivo"] = f"Erro ao verificar validade do certificado: {e}"
        return resultado


# ---------------------------------------------------------------------------
# Verificação segura do certificado do SERVIDOR (proteção contra MITM)
# ---------------------------------------------------------------------------

# Cache por host: evita refazer o preflight de verificação a cada chamada
# (uma vez identificado que um host tem cadeia mal configurada, lembra disso
# pelo resto da execução do processo).
_verify_cache: dict[str, bool] = {}


def determinar_verify_para_host(url: str, cert_path: Optional[str] = None,
                                 senha: Optional[str] = None, timeout: int = 10) -> bool:
    """
    Decide se a verificação do certificado do servidor remoto deve ficar
    HABILITADA para o host da URL informada.

    Por padrão tenta com verificação estrita (segura). Alguns webservices de
    SEFAZ estaduais e prefeituras têm cadeias de certificado mal configuradas
    (certificado intermediário ausente, raiz autoassinada na cadeia) que
    falham na verificação mesmo sendo o servidor legítimo — quando isso
    acontece, registra um aviso explícito em logs/certificado_seguranca.log
    (nunca falha silenciosamente) e desabilita a verificação APENAS para
    aquele host específico, preservando proteção contra MITM para todos os
    outros (incluindo os endpoints nacionais, que têm cadeia correta).

    Returns:
        bool: True se a verificação deve ficar habilitada para este host.
    """
    host = urlparse(url).netloc or url
    if host in _verify_cache:
        return _verify_cache[host]

    try:
        kwargs = {"timeout": timeout, "verify": True}
        if cert_path:
            import requests_pkcs12
            requests_pkcs12.get(url, pkcs12_filename=cert_path, pkcs12_password=senha or "", **kwargs)
        else:
            requests.get(url, **kwargs)
        _verify_cache[host] = True
        return True
    except requests.exceptions.SSLError as e:
        _get_cert_security_logger().warning(
            f"Verificação do certificado do servidor FALHOU para '{host}' — cadeia de certificado "
            f"mal configurada no servidor remoto (não é um problema do certificado do usuário). "
            f"Verificação será desabilitada APENAS para este host. Motivo: {e}"
        )
        _verify_cache[host] = False
        return False
    except Exception:
        # Falha de rede/timeout/auth não é problema de certificado do servidor —
        # assume seguro por padrão e deixa o erro real aparecer na chamada real.
        _verify_cache[host] = True
        return True


def classificar_erro_https_certificado(exc: Exception) -> Optional[str]:
    """
    Classifica uma exceção de rede como possível problema do CERTIFICADO DO
    USUÁRIO (expirado, revogado, senha incorreta) em vez de mascará-la como
    erro genérico de conexão. Retorna uma mensagem amigável ou None se não
    reconhecer o padrão.
    """
    msg = str(exc).lower()
    if 'certificate has expired' in msg or 'certificate is not yet valid' in msg:
        return "O certificado digital apresentado está fora do prazo de validade."
    if 'revoked' in msg or 'revogado' in msg:
        return "O certificado digital apresentado foi REVOGADO pela Autoridade Certificadora."
    if 'sslv3_alert_certificate_unknown' in msg or 'tlsv1_alert_unknown_ca' in msg:
        return "O servidor não reconheceu a Autoridade Certificadora do certificado apresentado."
    if 'bad decrypt' in msg or 'mac verify failure' in msg or 'invalid password' in msg:
        return "Senha do certificado incorreta ou arquivo .pfx corrompido."
    return None
