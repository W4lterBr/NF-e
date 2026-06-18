# -*- coding: utf-8 -*-
"""
Reindexar XMLs — percorre todas as pastas conhecidas de XML, localiza os
arquivos, e corrige no banco (notas.db):
  - xmls_caminhos  (registra/atualiza o caminho real de cada chave)
  - xmls_baixados  (mantido em sincronia para o caminho LOCAL principal)
  - notas_detalhadas.xml_status (promove para COMPLETO quando o XML completo
    é encontrado em disco e o status atual não reflete isso)

Por padrão roda em modo DRY-RUN (não grava nada — apenas relata o que faria).
Use --apply para gravar de fato. Em modo --apply, um backup timestampado do
notas.db é criado automaticamente antes de qualquer escrita.

Uso:
    python scripts/reindexar_xmls.py                  # dry-run (somente relatorio)
    python scripts/reindexar_xmls.py --apply           # aplica as correções
    python scripts/reindexar_xmls.py --apply --tipo NFS-e
"""
from __future__ import annotations

import argparse
import io
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Console do Windows usa cp1252 por padrão e não representa emojis — força UTF-8
# (mesmo padrão já usado em buscar_nfse_auto.py) quando executado como script direto.
if __name__ == "__main__" and sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


def get_data_dir() -> Path:
    try:
        from nfe_search import get_data_dir as _gdd
        return Path(_gdd())
    except Exception:
        return BASE_DIR


def detectar_tipo_e_extrair(xml_path: Path):
    """Detecta o tipo de documento pelo conteudo do XML e retorna
    (tipo_doc, lista_de_dicts_extraidos) usando os parsers de modules/xml_indexer.
    tipo_doc in {'NFe', 'CTe', 'NFSe', 'NFCe', None}.
    """
    from modules.xml_indexer import parse_nfe, parse_cte, parse_nfse, parse_nfse_abrasf, parse_nfce

    try:
        header = xml_path.read_bytes()[:800].decode("utf-8", errors="ignore")
    except Exception:
        return None, []

    try:
        if "portalfiscal.inf.br/cte" in header:
            d = parse_cte(str(xml_path))
            return ("CTe", [d]) if d.get("chave") else (None, [])

        if "portalfiscal.inf.br/nfe" in header:
            is_nfce = "<mod>65</mod>" in header
            d = parse_nfce(str(xml_path)) if is_nfce else parse_nfe(str(xml_path))
            tipo = "NFCe" if is_nfce else "NFe"
            return (tipo, [d]) if d.get("chave") else (None, [])

        if "abrasf.org.br" in header or "ListaNotaFiscal" in header:
            ds = [d for d in parse_nfse_abrasf(str(xml_path)) if d.get("chave")]
            return ("NFSe", ds) if ds else (None, [])

        if "sped.fazenda.gov.br/nfse" in header:
            d = parse_nfse(str(xml_path))
            return ("NFSe", [d]) if d.get("chave") else (None, [])
    except Exception:
        return None, []

    return None, []


def listar_pastas_xml(data_dir: Path, conn: sqlite3.Connection) -> list:
    roots = [
        data_dir / "xmls", data_dir / "xmls_chave", data_dir / "xmls_nfce",
        data_dir / "xml_NFs", data_dir / "xml_envio", data_dir / "xml_extraidos",
    ]
    try:
        for (pasta,) in conn.execute("SELECT pasta_base FROM perfis_armazenamento WHERE ativo=1").fetchall():
            if pasta:
                roots.append(Path(pasta))
    except Exception:
        pass
    return [r for r in roots if r.exists()]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="Grava as correções no banco (sem isso, roda em dry-run)")
    ap.add_argument("--tipo", choices=["NFe", "CTe", "NFSe", "NFCe"], help="Restringe a um tipo de documento")
    ap.add_argument("--limite", type=int, default=0, help="Limita o número de arquivos processados (0 = sem limite)")
    args = ap.parse_args()

    data_dir = get_data_dir()
    db_path = data_dir / "notas.db"

    print("=" * 78)
    print(f"REINDEXAR XMLs — {'APLICANDO MUDANÇAS' if args.apply else 'DRY-RUN (nenhuma escrita)'}")
    print(f"Banco: {db_path}")
    print("=" * 78)

    if args.apply:
        backup_path = db_path.with_name(f"notas.db.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(db_path, backup_path)
        print(f"💾 Backup criado: {backup_path}")

    # timeout maior + commits periódicos (ver loop abaixo): sem isso, uma única
    # transação aberta por todo o scan (~10k arquivos) trava o banco para o app
    # principal durante toda a execução — causou "database is locked" reais e
    # perda de gravação no app rodando em paralelo.
    conn = sqlite3.connect(str(db_path), timeout=30)

    roots = listar_pastas_xml(data_dir, conn)
    print(f"\nPastas a varrer ({len(roots)}):")
    for r in roots:
        print(f"  - {r}")

    from nfe_search import _registrar_caminho_salvo

    stats = {
        "arquivos_varridos": 0,
        "sem_chave_extraida": 0,
        "caminhos_novos_ou_atualizados": 0,
        "caminho_via_nome_arquivo": 0,
        "status_corrigido": 0,
        "ja_correto": 0,
    }
    status_corrigidos = []
    sem_chave = []

    for root in roots:
        for xml_file in root.rglob("*.xml"):
            if args.limite and stats["arquivos_varridos"] >= args.limite:
                break
            stats["arquivos_varridos"] += 1

            tipo_doc, extraidos = detectar_tipo_e_extrair(xml_file)
            if args.tipo and tipo_doc != args.tipo:
                continue
            if not extraidos:
                # Fallback seguro: arquivos de protocolo SOAP (ex.: retConsSitNFe) não têm
                # estrutura reconhecida pelos parsers, mas muitas vezes o nome do arquivo
                # É a própria chave (44 dígitos). Registra o CAMINHO para que resolve_xml_text
                # consiga achar o arquivo, mas NUNCA promove xml_status a partir daqui —
                # não temos como validar o conteúdo, então não arriscamos criar uma nova
                # inconsistência "status diz COMPLETO mas dado é raso".
                nome = xml_file.stem
                if nome.isdigit() and len(nome) in (44,):
                    if args.tipo and args.tipo not in ("NFe", "CTe"):
                        stats["sem_chave_extraida"] += 1
                        sem_chave.append(str(xml_file))
                        continue
                    row = conn.execute(
                        "SELECT informante FROM notas_detalhadas WHERE chave = ?", (nome,)
                    ).fetchone()
                    if row is not None:
                        if args.apply:
                            _registrar_caminho_salvo(nome, row[0] or "", str(xml_file), tipo="LOCAL")
                        stats["caminhos_novos_ou_atualizados"] += 1
                        stats["caminho_via_nome_arquivo"] += 1
                        continue
                stats["sem_chave_extraida"] += 1
                sem_chave.append(str(xml_file))
                continue

            for dados in extraidos:
                chave = dados.get("chave")
                if not chave:
                    continue
                informante = dados.get("informante") or dados.get("prest_cnpj") or dados.get("emit_cnpj") or ""

                # --- xmls_caminhos / xmls_baixados ---
                if args.apply:
                    _registrar_caminho_salvo(chave, informante, str(xml_file), tipo="LOCAL")
                stats["caminhos_novos_ou_atualizados"] += 1

                # --- corrige xml_status quando o documento é COMPLETO ---
                if dados.get("xml_status") == "COMPLETO":
                    row = conn.execute(
                        "SELECT xml_status FROM notas_detalhadas WHERE chave = ?", (chave,)
                    ).fetchone()
                    if row is None:
                        continue  # não cria nota nova aqui — reindexação só corrige caminho/status de notas existentes
                    status_atual = row[0]
                    if status_atual != "COMPLETO":
                        status_corrigidos.append((chave, status_atual, str(xml_file)))
                        stats["status_corrigido"] += 1
                        if args.apply:
                            conn.execute(
                                "UPDATE notas_detalhadas SET xml_status = 'COMPLETO' WHERE chave = ?",
                                (chave,)
                            )
                    else:
                        stats["ja_correto"] += 1

            # 🔒 Commit periódico: mantém cada transação curta (poucos arquivos),
            # liberando o lock do banco rapidamente para o app principal poder
            # gravar em paralelo. Uma transação única para os ~10k arquivos
            # travaria o banco inteiro até o fim do scan.
            if args.apply and stats["arquivos_varridos"] % 50 == 0:
                conn.commit()

        if args.limite and stats["arquivos_varridos"] >= args.limite:
            break

    if args.apply:
        conn.commit()
        # garante o índice de performance em xml_status (idempotente, não destrutivo)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_notas_xml_status ON notas_detalhadas(xml_status, tipo)")
        conn.commit()

    print("\n" + "=" * 78)
    print("RESUMO")
    print("=" * 78)
    print(f"Arquivos .xml varridos          : {stats['arquivos_varridos']}")
    print(f"Sem chave extraída (parse falhou): {stats['sem_chave_extraida']}")
    print(f"Caminhos novos/atualizados       : {stats['caminhos_novos_ou_atualizados']}")
    print(f"  (via nome do arquivo = chave)  : {stats['caminho_via_nome_arquivo']}")
    print(f"xml_status corrigido p/ COMPLETO : {stats['status_corrigido']}")
    print(f"Já estavam corretos              : {stats['ja_correto']}")

    if status_corrigidos:
        print(f"\nExemplos de status corrigido (até 15):")
        for chave, status_antigo, arq in status_corrigidos[:15]:
            print(f"  {chave[:25]}… {status_antigo or 'NULL'} -> COMPLETO   ({arq})")

    if not args.apply:
        print("\n⚠️  DRY-RUN — nada foi gravado. Rode novamente com --apply para gravar as correções.")

    conn.close()


if __name__ == "__main__":
    main()
