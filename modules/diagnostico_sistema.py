# -*- coding: utf-8 -*-
"""
Diagnóstico do Sistema (Problema crítico 8).

Executa um conjunto de checagens de saúde do sistema e retorna o resultado
em um semáforo por item: OK (🟢), ATENCAO (🟡), ERRO (🔴).

Sem dependência de Qt — pode ser chamado de um diálogo, de um script de
linha de comando, ou de testes automatizados.

Uso:
    from modules.diagnostico_sistema import executar_diagnostico
    resultados = executar_diagnostico()
    for r in resultados:
        print(r["status"], r["nome"], "-", r["detalhe"])
"""
from __future__ import annotations

import socket
import sqlite3
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

OK = "OK"
ATENCAO = "ATENCAO"
ERRO = "ERRO"

ICONE = {OK: "🟢", ATENCAO: "🟡", ERRO: "🔴"}


def _item(nome: str, status: str, detalhe: str, categoria: str = "geral") -> Dict[str, Any]:
    return {"nome": nome, "status": status, "detalhe": detalhe, "categoria": categoria, "icone": ICONE[status]}


def _get_data_dir() -> Path:
    try:
        from nfe_search import get_data_dir
        return Path(get_data_dir())
    except Exception:
        return Path(".")


def _db_path() -> Path:
    return _get_data_dir() / "notas.db"


# ---------------------------------------------------------------------------
# Checagens individuais — cada uma protegida por try/except própria, para
# que a falha de UMA checagem nunca impeça as demais de rodar.
# ---------------------------------------------------------------------------

def checar_banco_integro() -> Dict[str, Any]:
    try:
        conn = sqlite3.connect(str(_db_path()), timeout=5)
        resultado = conn.execute("PRAGMA integrity_check").fetchone()[0]
        total_notas = conn.execute("SELECT COUNT(*) FROM notas_detalhadas").fetchone()[0]
        conn.close()
        if resultado == "ok":
            return _item("Banco de dados íntegro", OK, f"PRAGMA integrity_check: ok ({total_notas} notas)", "database")
        return _item("Banco de dados íntegro", ERRO, f"PRAGMA integrity_check reportou problemas: {resultado}", "database")
    except sqlite3.OperationalError as e:
        if "locked" in str(e).lower():
            return _item("Banco de dados íntegro", ATENCAO, f"Banco ocupado por outro processo agora: {e}", "database")
        return _item("Banco de dados íntegro", ERRO, f"Erro ao acessar o banco: {e}", "database")
    except Exception as e:
        return _item("Banco de dados íntegro", ERRO, f"Erro ao verificar o banco: {e}", "database")


def checar_certificados() -> Dict[str, Any]:
    try:
        from modules.certificate_manager import validar_certificado
        conn = sqlite3.connect(str(_db_path()), timeout=5)
        certs = conn.execute("SELECT cnpj_cpf, caminho, senha, informante FROM certificados").fetchall()
        conn.close()
    except Exception as e:
        return _item("Certificados digitais", ERRO, f"Não foi possível ler certificados do banco: {e}", "certificado")

    if not certs:
        return _item("Certificados digitais", ATENCAO, "Nenhum certificado cadastrado", "certificado")

    try:
        from modules.crypto_portable import get_portable_crypto
        crypto = get_portable_crypto()
    except Exception:
        crypto = None

    vencidos, vencendo, invalidos, ok_count = [], [], [], 0
    for cnpj, caminho, senha_armazenada, informante in certs:
        senha = senha_armazenada
        if crypto and senha_armazenada:
            try:
                if crypto.is_encrypted(senha_armazenada):
                    senha = crypto.decrypt(senha_armazenada)
            except Exception:
                pass
        info = validar_certificado(caminho, senha or "")
        if info["expirado"]:
            vencidos.append(cnpj)
        elif not info["valido"]:
            invalidos.append(cnpj)
        elif info["motivo"]:  # válido mas vencendo em breve
            vencendo.append(cnpj)
            ok_count += 1
        else:
            ok_count += 1

    if vencidos or invalidos:
        partes = []
        if vencidos:
            partes.append(f"{len(vencidos)} vencido(s): {', '.join(vencidos)}")
        if invalidos:
            partes.append(f"{len(invalidos)} inválido(s): {', '.join(invalidos)}")
        return _item("Certificados digitais", ERRO, "; ".join(partes), "certificado")
    if vencendo:
        return _item("Certificados digitais", ATENCAO,
                      f"{ok_count} certificado(s) válido(s), {len(vencendo)} vencendo em breve: {', '.join(vencendo)}",
                      "certificado")
    return _item("Certificados digitais", OK, f"{ok_count} certificado(s) válido(s)", "certificado")


def checar_storage() -> Dict[str, Any]:
    data_dir = _get_data_dir()
    pastas_invalidas = []
    pastas_testadas = 0

    locais = [data_dir / "xmls"]
    try:
        conn = sqlite3.connect(str(_db_path()), timeout=5)
        perfis = conn.execute("SELECT nome, pasta_base FROM perfis_armazenamento WHERE ativo=1").fetchall()
        conn.close()
    except Exception:
        perfis = []

    for nome_perfil, pasta in perfis:
        locais.append(Path(pasta))

    for pasta in locais:
        pastas_testadas += 1
        try:
            pasta.mkdir(parents=True, exist_ok=True)
            teste = pasta / ".diagnostico_teste_escrita.tmp"
            teste.write_text("teste", encoding="utf-8")
            teste.unlink()
        except Exception as e:
            pastas_invalidas.append(f"{pasta} ({e})")

    if pastas_invalidas:
        return _item("Armazenamento (pastas)", ERRO,
                      f"{len(pastas_invalidas)}/{pastas_testadas} pasta(s) inacessível(eis): {'; '.join(pastas_invalidas)}",
                      "storage")
    return _item("Armazenamento (pastas)", OK, f"{pastas_testadas} pasta(s) acessível(eis) para leitura/escrita", "storage")


def checar_caminhos_xml(amostra: int = 50) -> Dict[str, Any]:
    try:
        conn = sqlite3.connect(str(_db_path()), timeout=5)
        rows = conn.execute(
            "SELECT caminho_arquivo FROM xmls_baixados WHERE caminho_arquivo IS NOT NULL "
            "ORDER BY baixado_em DESC LIMIT ?", (amostra,)
        ).fetchall()
        conn.close()
    except Exception as e:
        return _item("Caminhos de XML (amostra recente)", ERRO, f"Erro ao consultar banco: {e}", "storage")

    if not rows:
        return _item("Caminhos de XML (amostra recente)", ATENCAO, "Nenhum XML registrado no banco ainda", "storage")

    invalidos = sum(1 for (caminho,) in rows if not Path(caminho).exists())
    total = len(rows)
    if invalidos == 0:
        return _item("Caminhos de XML (amostra recente)", OK, f"{total}/{total} encontrados em disco", "storage")
    proporcao = invalidos / total
    status = ERRO if proporcao > 0.3 else ATENCAO
    return _item("Caminhos de XML (amostra recente)", status,
                  f"{invalidos}/{total} caminhos registrados não encontrados em disco — "
                  f"considere rodar scripts/reindexar_xmls.py", "storage")


def checar_pdfs(amostra: int = 50) -> Dict[str, Any]:
    try:
        conn = sqlite3.connect(str(_db_path()), timeout=5)
        rows = conn.execute(
            "SELECT pdf_path FROM notas_detalhadas WHERE pdf_path IS NOT NULL AND pdf_path != '' "
            "ORDER BY atualizado_em DESC LIMIT ?", (amostra,)
        ).fetchall()
        conn.close()
    except Exception as e:
        return _item("PDFs (amostra recente)", ERRO, f"Erro ao consultar banco: {e}", "pdf")

    if not rows:
        return _item("PDFs (amostra recente)", ATENCAO, "Nenhum PDF registrado no banco ainda", "pdf")

    invalidos = 0
    for (caminho,) in rows:
        p = Path(caminho)
        if not p.exists():
            invalidos += 1
            continue
        try:
            if p.stat().st_size < 100 or p.read_bytes()[:4] != b"%PDF":
                invalidos += 1
        except Exception:
            invalidos += 1

    total = len(rows)
    if invalidos == 0:
        return _item("PDFs (amostra recente)", OK, f"{total}/{total} válidos (existem e começam com %PDF)", "pdf")
    proporcao = invalidos / total
    status = ERRO if proporcao > 0.3 else ATENCAO
    return _item("PDFs (amostra recente)", status, f"{invalidos}/{total} ausentes ou inválidos", "pdf")


def _testar_conexao(host: str, porta: int = 443, timeout: float = 5.0) -> Optional[str]:
    """Tenta abrir um socket TCP. Retorna None se OK, ou a mensagem de erro."""
    try:
        with socket.create_connection((host, porta), timeout=timeout):
            return None
    except Exception as e:
        return str(e)


def checar_internet() -> Dict[str, Any]:
    # Testa contra dois resolvedores DNS públicos conhecidos — não depende da
    # disponibilidade de um site específico, só de conectividade básica.
    for host in ("1.1.1.1", "8.8.8.8"):
        erro = _testar_conexao(host, 443, timeout=4)
        if erro is None:
            return _item("Conexão com a internet", OK, f"Conectividade confirmada ({host}:443)", "rede")
    return _item("Conexão com a internet", ERRO, f"Sem conectividade (falhou para 1.1.1.1 e 8.8.8.8): {erro}", "rede")


def checar_sefaz() -> Dict[str, Any]:
    erro = _testar_conexao("www1.nfe.fazenda.gov.br", 443, timeout=6)
    if erro is None:
        return _item("Serviço SEFAZ (Receita Federal)", OK, "www1.nfe.fazenda.gov.br acessível", "rede")
    return _item("Serviço SEFAZ (Receita Federal)", ERRO, f"www1.nfe.fazenda.gov.br inacessível: {erro}", "rede")


def checar_adn_nfse() -> Dict[str, Any]:
    erro = _testar_conexao("adn.nfse.gov.br", 443, timeout=6)
    if erro is None:
        return _item("Ambiente Nacional NFS-e (ADN)", OK, "adn.nfse.gov.br acessível", "rede")
    return _item("Ambiente Nacional NFS-e (ADN)", ERRO, f"adn.nfse.gov.br inacessível: {erro}", "rede")


def checar_servico_municipal() -> Dict[str, Any]:
    try:
        conn = sqlite3.connect(str(_db_path()), timeout=5)
        configs = conn.execute(
            "SELECT DISTINCT provedor, url_customizada FROM nfse_config "
            "WHERE ativo=1 AND provedor NOT IN ('ADN', 'NACIONAL', 'AMBIENTE_NACIONAL')"
        ).fetchall()
        conn.close()
    except Exception as e:
        return _item("Serviços municipais de NFS-e", ATENCAO, f"Não foi possível ler configuração: {e}", "rede")

    if not configs:
        return _item("Serviços municipais de NFS-e", ATENCAO, "Nenhum provedor municipal configurado (usando apenas ADN)", "rede")

    from urllib.parse import urlparse
    falhas = []
    testados = 0
    for provedor, url in configs:
        if not url:
            continue
        host = urlparse(url).netloc or url
        testados += 1
        if _testar_conexao(host, 443, timeout=6) is not None:
            falhas.append(provedor)

    if testados == 0:
        return _item("Serviços municipais de NFS-e", ATENCAO, f"{len(configs)} provedor(es) configurado(s), sem URL para testar", "rede")
    if falhas:
        return _item("Serviços municipais de NFS-e", ATENCAO if len(falhas) < testados else ERRO,
                      f"{len(falhas)}/{testados} provedor(es) inacessível(eis): {', '.join(falhas)}", "rede")
    return _item("Serviços municipais de NFS-e", OK, f"{testados} provedor(es) acessível(eis)", "rede")


# Lista de checagens executadas por executar_diagnostico(), em ordem de exibição.
_CHECAGENS: List[Callable[[], Dict[str, Any]]] = [
    checar_banco_integro,
    checar_certificados,
    checar_storage,
    checar_caminhos_xml,
    checar_pdfs,
    checar_internet,
    checar_sefaz,
    checar_adn_nfse,
    checar_servico_municipal,
]


def executar_diagnostico(progresso: Optional[Callable[[int, int, str], None]] = None) -> List[Dict[str, Any]]:
    """
    Executa todas as checagens e retorna a lista de resultados, na ordem.

    Args:
        progresso: callback opcional `(indice, total, nome_da_checagem)` chamado
                   antes de cada checagem — útil para atualizar uma barra de progresso.
    """
    resultados = []
    total = len(_CHECAGENS)
    for i, checagem in enumerate(_CHECAGENS, 1):
        if progresso:
            try:
                progresso(i, total, checagem.__name__)
            except Exception:
                pass
        try:
            resultados.append(checagem())
        except Exception as e:
            resultados.append(_item(checagem.__name__, ERRO, f"Falha inesperada ao executar checagem: {e}", "geral"))
    return resultados


def status_geral(resultados: List[Dict[str, Any]]) -> str:
    """Resume a lista de resultados num único status: ERRO se algum item for ERRO,
    ATENCAO se algum for ATENCAO (e nenhum ERRO), OK se todos OK."""
    if any(r["status"] == ERRO for r in resultados):
        return ERRO
    if any(r["status"] == ATENCAO for r in resultados):
        return ATENCAO
    return OK


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    print("=" * 70)
    print("DIAGNÓSTICO DO SISTEMA")
    print("=" * 70)
    resultados = executar_diagnostico(progresso=lambda i, t, n: print(f"[{i}/{t}] {n}..."))
    print()
    for r in resultados:
        print(f"{r['icone']} {r['nome']}: {r['detalhe']}")
    print()
    geral = status_geral(resultados)
    print(f"STATUS GERAL: {ICONE[geral]} {geral}")
