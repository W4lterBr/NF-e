# -*- coding: utf-8 -*-
"""
Diagnostico de integridade do banco (notas.db) e do armazenamento de XML/PDF.

Rotina SOMENTE LEITURA (nao grava nada). Verifica:
  1. Chaves duplicadas em notas_detalhadas
  2. Notas COMPLETO sem caminho conhecido (nem xmls_baixados nem xmls_caminhos)
     -> dependem do fallback lento de busca em disco (rglob)
  3. Caminhos invalidos em xmls_baixados (registrado mas arquivo nao existe)
  4. Caminhos invalidos em xmls_caminhos (registrado mas arquivo nao existe)
  5. PDFs orfaos (pdf_path registrado em notas_detalhadas mas arquivo nao existe)
  6. XMLs orfaos em disco (arquivo .xml encontrado nas pastas conhecidas mas
     nenhuma chave correspondente existe em notas_detalhadas)

Uso:
    python scripts/diagnostico_integridade.py
    python scripts/diagnostico_integridade.py --tipo NFS-e
    python scripts/diagnostico_integridade.py --json relatorio.json
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from pathlib import Path
from datetime import datetime

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


def get_db_path() -> Path:
    return get_data_dir() / "notas.db"


def chaves_de_xml(xml_path: Path):
    """Extrai a(s) chave(s) de um arquivo XML usando os parsers existentes.
    Retorna lista de chaves (pode ter mais de uma para arquivos multi-nota ABRASF)."""
    chaves = []
    try:
        from modules.xml_indexer import parse_nfe, parse_cte, parse_nfse, parse_nfse_abrasf, parse_nfce
    except Exception:
        return chaves

    try:
        header = xml_path.read_bytes()[:600].decode("utf-8", errors="ignore")
    except Exception:
        return chaves

    try:
        if "portalfiscal.inf.br/nfe" in header and ('"55"' in header or ">55<" in header or "infNFe" in header) and "infCte" not in header:
            if "<mod>65</mod>" in header or "NFCe" in header:
                d = parse_nfce(str(xml_path))
            else:
                d = parse_nfe(str(xml_path))
            if d.get("chave"):
                chaves.append(d["chave"])
        elif "portalfiscal.inf.br/cte" in header:
            d = parse_cte(str(xml_path))
            if d.get("chave"):
                chaves.append(d["chave"])
        elif "abrasf.org.br" in header or "ListaNotaFiscal" in header:
            for d in parse_nfse_abrasf(str(xml_path)):
                if d.get("chave"):
                    chaves.append(d["chave"])
        elif "sped.fazenda.gov.br/nfse" in header:
            d = parse_nfse(str(xml_path))
            if d.get("chave"):
                chaves.append(d["chave"])
    except Exception:
        pass
    return chaves


def listar_pastas_xml(data_dir: Path, db) -> list:
    roots = [
        data_dir / "xmls", data_dir / "xmls_chave", data_dir / "xmls_nfce",
        data_dir / "xml_NFs", data_dir / "xml_envio", data_dir / "xml_extraidos",
    ]
    try:
        for (pasta,) in db.execute("SELECT pasta_base FROM perfis_armazenamento WHERE ativo=1").fetchall():
            if pasta:
                roots.append(Path(pasta))
    except Exception:
        pass
    return [r for r in roots if r.exists()]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tipo", help="Filtra por tipo (NFe, CTe, NFS-e, NFC-e)")
    ap.add_argument("--json", help="Salva relatorio completo em arquivo JSON")
    ap.add_argument("--scan-disco", action="store_true",
                     help="Tambem varre as pastas de XML em disco p/ achar XML orfao (mais lento)")
    args = ap.parse_args()

    import sqlite3
    db_path = get_db_path()
    print("=" * 78)
    print(f"DIAGNOSTICO DE INTEGRIDADE — {db_path}")
    print(f"Executado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 78)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    filtro_tipo = ""
    params: list = []
    if args.tipo:
        filtro_tipo = " AND tipo = ?"
        params.append(args.tipo)

    relatorio: dict = {"gerado_em": datetime.now().isoformat(), "db_path": str(db_path)}

    # 1) Chaves duplicadas -----------------------------------------------------
    dups = conn.execute(
        f"SELECT chave, COUNT(*) c FROM notas_detalhadas WHERE 1=1{filtro_tipo} "
        f"GROUP BY chave HAVING c > 1", params
    ).fetchall()
    relatorio["chaves_duplicadas"] = [dict(r) for r in dups]
    print(f"\n[1] Chaves duplicadas: {len(dups)}")
    for r in dups[:10]:
        print(f"     {r['chave']} ({r['c']}x)")

    # 2) COMPLETO sem caminho conhecido ----------------------------------------
    sem_caminho = conn.execute(
        f"""SELECT n.chave, n.tipo, n.numero, n.informante, n.atualizado_em
            FROM notas_detalhadas n
            LEFT JOIN xmls_baixados b ON b.chave = n.chave
            LEFT JOIN xmls_caminhos c ON c.chave = n.chave
            WHERE n.xml_status = 'COMPLETO'{filtro_tipo}
              AND (b.chave IS NULL OR (b.caminho_arquivo IS NULL AND b.xml_completo IS NULL))
              AND c.chave IS NULL
        """, params
    ).fetchall()
    relatorio["completo_sem_caminho"] = [dict(r) for r in sem_caminho]
    print(f"\n[2] COMPLETO sem caminho conhecido (xmls_baixados/xmls_caminhos): {len(sem_caminho)}")
    print("     -> essas notas só são encontradas via busca lenta em disco (rglob)")
    for r in sem_caminho[:10]:
        print(f"     {r['tipo']:8s} {r['numero'] or '':10s} chave={r['chave'][:25]}…")

    # 3) Caminhos invalidos em xmls_baixados -----------------------------------
    rows_b = conn.execute(
        "SELECT chave, caminho_arquivo FROM xmls_baixados WHERE caminho_arquivo IS NOT NULL"
    ).fetchall()
    invalidos_b = [dict(r) for r in rows_b if not os.path.exists(r["caminho_arquivo"])]
    relatorio["xmls_baixados_caminho_invalido"] = invalidos_b
    print(f"\n[3] xmls_baixados com caminho registrado mas arquivo ausente: {len(invalidos_b)} / {len(rows_b)}")
    for r in invalidos_b[:10]:
        print(f"     {r['chave'][:25]}… -> {r['caminho_arquivo']}")

    # 4) Caminhos invalidos em xmls_caminhos -----------------------------------
    rows_c = conn.execute("SELECT chave, caminho FROM xmls_caminhos").fetchall()
    invalidos_c = [dict(r) for r in rows_c if not os.path.exists(r["caminho"])]
    relatorio["xmls_caminhos_caminho_invalido"] = invalidos_c
    print(f"\n[4] xmls_caminhos com caminho registrado mas arquivo ausente: {len(invalidos_c)} / {len(rows_c)}")
    for r in invalidos_c[:10]:
        print(f"     {r['chave'][:25]}… -> {r['caminho']}")

    # 5) PDFs orfaos (pdf_path no notas_detalhadas) ----------------------------
    rows_p = conn.execute(
        f"SELECT chave, pdf_path FROM notas_detalhadas WHERE pdf_path IS NOT NULL AND pdf_path != ''{filtro_tipo}",
        params
    ).fetchall()
    pdf_orfaos = [dict(r) for r in rows_p if not os.path.exists(r["pdf_path"])]
    relatorio["pdf_path_invalido"] = pdf_orfaos
    print(f"\n[5] notas_detalhadas.pdf_path registrado mas arquivo ausente: {len(pdf_orfaos)} / {len(rows_p)}")
    for r in pdf_orfaos[:10]:
        print(f"     {r['chave'][:25]}… -> {r['pdf_path']}")

    # 6) XML orfao em disco (opcional, mais lento) -----------------------------
    if args.scan_disco:
        data_dir = get_data_dir()
        roots = listar_pastas_xml(data_dir, conn)
        print(f"\n[6] Varrendo {len(roots)} pasta(s) raiz em busca de XML órfão em disco...")
        chaves_conhecidas = {r[0] for r in conn.execute("SELECT chave FROM notas_detalhadas").fetchall()}
        orfaos_disco = []
        total_arquivos = 0
        for root in roots:
            for f in root.rglob("*.xml"):
                total_arquivos += 1
                chs = chaves_de_xml(f)
                if not chs:
                    continue  # não foi possível extrair chave (não é erro de órfão, é falha de parse)
                if not any(ch in chaves_conhecidas for ch in chs):
                    orfaos_disco.append({"arquivo": str(f), "chaves_extraidas": chs})
        relatorio["xml_orfao_disco"] = orfaos_disco
        relatorio["total_arquivos_xml_varridos"] = total_arquivos
        print(f"     Arquivos .xml varridos: {total_arquivos}")
        print(f"     XML órfãos (sem registro em notas_detalhadas): {len(orfaos_disco)}")
        for o in orfaos_disco[:10]:
            print(f"     {o['arquivo']}")
    else:
        print("\n[6] XML órfão em disco: pulado (use --scan-disco para incluir; é mais lento)")

    # Resumo --------------------------------------------------------------------
    total_notas = conn.execute(f"SELECT COUNT(*) FROM notas_detalhadas WHERE 1=1{filtro_tipo}", params).fetchone()[0]
    print("\n" + "=" * 78)
    print("RESUMO")
    print("=" * 78)
    print(f"Total de notas analisadas : {total_notas}")
    print(f"Chaves duplicadas         : {len(dups)}")
    print(f"COMPLETO sem caminho      : {len(sem_caminho)}")
    print(f"xmls_baixados inválido    : {len(invalidos_b)}")
    print(f"xmls_caminhos inválido    : {len(invalidos_c)}")
    print(f"pdf_path inválido         : {len(pdf_orfaos)}")
    if args.scan_disco:
        print(f"XML órfão em disco        : {len(relatorio.get('xml_orfao_disco', []))}")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(relatorio, fh, ensure_ascii=False, indent=2)
        print(f"\nRelatório completo salvo em: {args.json}")

    conn.close()


if __name__ == "__main__":
    main()
