"""
xml_indexer.py â€” Parser de XMLs fiscais para indexaÃ§Ã£o no banco de dados.

Suporta:
  - NF-e  (nfeProc / nfeProc/NFe / resNFe)
  - CT-e  (cteProc / cteProc/CTe / resCTe)
  - NFS-e (NFSe â€” padrÃ£o ADN/SPED)

Uso:
    from modules.xml_indexer import parse_nfe, parse_cte, parse_nfse
    dados = parse_nfe("caminho/para/arquivo.xml", informante="12345678000199")
    db.upsert_nfe_doc(dados)
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    from lxml import etree as ET
    _LXML = True
except ImportError:
    import xml.etree.ElementTree as ET  # type: ignore
    _LXML = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _t(element, path: str, ns: dict) -> Optional[str]:
    """Retorna o texto de um sub-elemento por XPath simples, ou None."""
    try:
        el = element.find(path, ns)
        if el is not None and el.text:
            return el.text.strip()
    except Exception:
        pass
    return None


def _el(parent, path: str, ns: dict):
    """Retorna o sub-elemento pelo path, ou um elemento vazio ('_') se nÃ£o encontrado.
    Usa 'is not None' para evitar FutureWarning do lxml com elementos sem filhos."""
    found = parent.find(path, ns)
    return found if found is not None else ET.Element("_")


def _parse_tree(xml_path: str):
    """Faz o parse do XML e retorna o ElementTree root, ou None em caso de erro."""
    try:
        if _LXML:
            parser = ET.XMLParser(recover=True)
            tree = ET.parse(str(xml_path), parser)
            return tree.getroot()
        else:
            return ET.parse(str(xml_path)).getroot()
    except Exception as e:
        print(f"[XML_INDEXER] Erro ao parsear {xml_path}: {e}")
        return None


def _now_iso() -> str:
    return datetime.now().isoformat()


# ---------------------------------------------------------------------------
# NF-e
# ---------------------------------------------------------------------------

# Namespaces NF-e
_NS_NFE = {"nfe": "http://www.portalfiscal.inf.br/nfe"}


def parse_nfe(xml_path: str, informante: str = "") -> Dict[str, Any]:
    """
    Extrai todos os campos relevantes de um XML NF-e (COMPLETO ou RESUMO).

    Args:
        xml_path: Caminho absoluto do .xml
        informante: CNPJ/CPF que recebeu a nota (quem consultou o SEFAZ)

    Returns:
        dict compatÃ­vel com DatabaseManager.upsert_nfe_doc()
    """
    root = _parse_tree(xml_path)
    data: Dict[str, Any] = {
        "informante": informante,
        "caminho_xml": str(xml_path),
        "caminho_pdf": None,
        "indexado_em": _now_iso(),
    }

    if root is None:
        return data

    ns = _NS_NFE

    # Determina se Ã© COMPLETO (nfeProc ou NFe) ou RESUMO (resNFe)
    tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag

    # --- RESUMO ---
    if tag == "resNFe":
        res = root
        chave = res.get("chNFe") or _t(res, "nfe:chNFe", ns) or ""
        data.update({
            "chave": chave,
            "xml_status": "RESUMO",
            "c_uf": _t(res, "nfe:cUF", ns),
            "dh_emi": _t(res, "nfe:dhEmi", ns),
            "emit_cnpj": _t(res, "nfe:CNPJ", ns),
            "emit_xnome": _t(res, "nfe:xNome", ns),
            "tp_nf": _t(res, "nfe:tpNF", ns),
            "serie": _t(res, "nfe:serie", ns),
            "n_nf": _t(res, "nfe:nNF", ns),
            "v_nf": _t(res, "nfe:vNF", ns),
            "dest_ie": _t(res, "nfe:digVal", ns),  # digVal no resNFe
        })
        return data

    # --- COMPLETO (nfeProc ou NFe) ---
    if tag == "nfeProc":
        nfe_el = root.find("nfe:NFe", ns)
    elif tag == "NFe":
        nfe_el = root
    else:
        # Tenta localizar NFe em qualquer profundidade
        nfe_el = root.find(".//nfe:NFe", ns)

    if nfe_el is None:
        data["xml_status"] = "RESUMO"
        return data

    inf = nfe_el.find("nfe:infNFe", ns)
    if inf is None:
        data["xml_status"] = "RESUMO"
        return data

    # Chave de acesso: Id do infNFe (remove prefixo "NFe")
    chave_raw = inf.get("Id", "")
    chave = chave_raw.replace("NFe", "")
    data["chave"] = chave
    data["xml_status"] = "COMPLETO"

    # ide
    ide = _el(inf, "nfe:ide", ns)
    data.update({
        "c_uf": _t(ide, "nfe:cUF", ns),
        "nat_op": _t(ide, "nfe:natOp", ns),
        "mod": _t(ide, "nfe:mod", ns),
        "serie": _t(ide, "nfe:serie", ns),
        "n_nf": _t(ide, "nfe:nNF", ns),
        "dh_emi": _t(ide, "nfe:dhEmi", ns),
        "dh_sai_ent": _t(ide, "nfe:dhSaiEnt", ns),
        "tp_nf": _t(ide, "nfe:tpNF", ns),
        "id_dest": _t(ide, "nfe:idDest", ns),
        "c_mun_fg": _t(ide, "nfe:cMunFG", ns),
        "tp_imp": _t(ide, "nfe:tpImp", ns),
        "tp_emis": _t(ide, "nfe:tpEmis", ns),
        "fin_nfe": _t(ide, "nfe:finNFe", ns),
        "ind_final": _t(ide, "nfe:indFinal", ns),
        "ind_pres": _t(ide, "nfe:indPres", ns),
    })

    # emitente
    emit = _el(inf, "nfe:emit", ns)
    end_emit = _el(emit, "nfe:enderEmit", ns)
    data.update({
        "emit_cnpj": _t(emit, "nfe:CNPJ", ns),
        "emit_cpf": _t(emit, "nfe:CPF", ns),
        "emit_ie": _t(emit, "nfe:IE", ns),
        "emit_xnome": _t(emit, "nfe:xNome", ns),
        "emit_xfant": _t(emit, "nfe:xFant", ns),
        "emit_xlgr": _t(end_emit, "nfe:xLgr", ns),
        "emit_nro": _t(end_emit, "nfe:nro", ns),
        "emit_xbairro": _t(end_emit, "nfe:xBairro", ns),
        "emit_cmun": _t(end_emit, "nfe:cMun", ns),
        "emit_xmun": _t(end_emit, "nfe:xMun", ns),
        "emit_uf": _t(end_emit, "nfe:UF", ns),
        "emit_cep": _t(end_emit, "nfe:CEP", ns),
        "emit_crt": _t(emit, "nfe:CRT", ns),
    })

    # destinatÃ¡rio
    dest = _el(inf, "nfe:dest", ns)
    end_dest = _el(dest, "nfe:enderDest", ns)
    data.update({
        "dest_cnpj": _t(dest, "nfe:CNPJ", ns),
        "dest_cpf": _t(dest, "nfe:CPF", ns),
        "dest_ie": _t(dest, "nfe:IE", ns),
        "dest_xnome": _t(dest, "nfe:xNome", ns),
        "dest_xlgr": _t(end_dest, "nfe:xLgr", ns),
        "dest_nro": _t(end_dest, "nfe:nro", ns),
        "dest_xbairro": _t(end_dest, "nfe:xBairro", ns),
        "dest_cmun": _t(end_dest, "nfe:cMun", ns),
        "dest_xmun": _t(end_dest, "nfe:xMun", ns),
        "dest_uf": _t(end_dest, "nfe:UF", ns),
        "dest_cep": _t(end_dest, "nfe:CEP", ns),
    })

    # totais
    total = _el(inf, "nfe:total", ns)
    icms_tot = _el(total, "nfe:ICMSTot", ns)
    ibs_tot = _el(total, "nfe:IBSCBSTot", ns)
    data.update({
        "v_bc": _t(icms_tot, "nfe:vBC", ns),
        "v_icms": _t(icms_tot, "nfe:vICMS", ns),
        "v_icms_deson": _t(icms_tot, "nfe:vICMSDeson", ns),
        "v_fcp": _t(icms_tot, "nfe:vFCP", ns),
        "v_bc_st": _t(icms_tot, "nfe:vBCST", ns),
        "v_st": _t(icms_tot, "nfe:vST", ns),
        "v_fcp_st": _t(icms_tot, "nfe:vFCPST", ns),
        "v_prod": _t(icms_tot, "nfe:vProd", ns),
        "v_frete": _t(icms_tot, "nfe:vFrete", ns),
        "v_seg": _t(icms_tot, "nfe:vSeg", ns),
        "v_desc": _t(icms_tot, "nfe:vDesc", ns),
        "v_ii": _t(icms_tot, "nfe:vII", ns),
        "v_ipi": _t(icms_tot, "nfe:vIPI", ns),
        "v_pis": _t(icms_tot, "nfe:vPIS", ns),
        "v_cofins": _t(icms_tot, "nfe:vCOFINS", ns),
        "v_outro": _t(icms_tot, "nfe:vOutro", ns),
        "v_nf": _t(icms_tot, "nfe:vNF", ns),
        "v_tot_trib": _t(icms_tot, "nfe:vTotTrib", ns),
        # IBS/CBS
        "v_ibs": _t(ibs_tot, "nfe:vIBS", ns),
        "v_cbs": _t(ibs_tot, "nfe:vCBS", ns),
        "v_bc_ibscbs": _t(ibs_tot, "nfe:vBC", ns),
    })

    # transporte
    transp = _el(inf, "nfe:transp", ns)
    transp_transporta = _el(transp, "nfe:transporta", ns)
    data.update({
        "mod_frete": _t(transp, "nfe:modFrete", ns),
        "transp_cnpj": _t(transp_transporta, "nfe:CNPJ", ns),
        "transp_xnome": _t(transp_transporta, "nfe:xNome", ns),
    })

    # pagamento (primeiro detPag)
    pag = inf.find("nfe:pag", ns)
    if pag is not None:
        det_pag = pag.find("nfe:detPag", ns)
        if det_pag is not None:
            data["t_pag"] = _t(det_pag, "nfe:tPag", ns)
            data["v_pag"] = _t(det_pag, "nfe:vPag", ns)

    # protocolo
    prot_nfe = root.find("nfe:protNFe", ns) if tag == "nfeProc" else None
    if prot_nfe is not None:
        inf_prot = _el(prot_nfe, "nfe:infProt", ns)
        data.update({
            "n_prot": _t(inf_prot, "nfe:nProt", ns),
            "dh_recbto": _t(inf_prot, "nfe:dhRecbto", ns),
            "c_stat": _t(inf_prot, "nfe:cStat", ns),
            "x_motivo": _t(inf_prot, "nfe:xMotivo", ns),
        })

    return data


# ---------------------------------------------------------------------------
# CT-e
# ---------------------------------------------------------------------------

_NS_CTE = {"cte": "http://www.portalfiscal.inf.br/cte"}


def parse_cte(xml_path: str, informante: str = "") -> Dict[str, Any]:
    """
    Extrai campos relevantes de um XML CT-e (COMPLETO ou RESUMO).
    """
    root = _parse_tree(xml_path)
    data: Dict[str, Any] = {
        "informante": informante,
        "caminho_xml": str(xml_path),
        "caminho_pdf": None,
        "indexado_em": _now_iso(),
    }

    if root is None:
        return data

    ns = _NS_CTE
    tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag

    # --- RESUMO resCTe ---
    if tag == "resCTe":
        res = root
        chave = res.get("chCTe") or _t(res, "cte:chCTe", ns) or ""
        data.update({
            "chave": chave,
            "xml_status": "RESUMO",
            "dh_emi": _t(res, "cte:dhEmi", ns),
            "emit_cnpj": _t(res, "cte:CNPJ", ns),
            "emit_xnome": _t(res, "cte:xNome", ns),
            "v_tprest": _t(res, "cte:vTPrest", ns),
        })
        return data

    # --- COMPLETO (cteProc ou CTe) ---
    if tag == "cteProc":
        cte_el = root.find("cte:CTe", ns)
    elif tag == "CTe":
        cte_el = root
    else:
        cte_el = root.find(".//cte:CTe", ns)

    if cte_el is None:
        data["xml_status"] = "RESUMO"
        return data

    inf = cte_el.find("cte:infCte", ns)
    if inf is None:
        data["xml_status"] = "RESUMO"
        return data

    chave_raw = inf.get("Id", "")
    chave = chave_raw.replace("CTe", "")
    data["chave"] = chave
    data["xml_status"] = "COMPLETO"

    # ide
    ide = _el(inf, "cte:ide", ns)
    data.update({
        "c_uf": _t(ide, "cte:cUF", ns),
        "c_ct": _t(ide, "cte:cCT", ns),
        "cfop": _t(ide, "cte:CFOP", ns),
        "nat_op": _t(ide, "cte:natOp", ns),
        "mod": _t(ide, "cte:mod", ns),
        "serie": _t(ide, "cte:serie", ns),
        "n_ct": _t(ide, "cte:nCT", ns),
        "dh_emi": _t(ide, "cte:dhEmi", ns),
        "tp_imp": _t(ide, "cte:tpImp", ns),
        "tp_emis": _t(ide, "cte:tpEmis", ns),
        "tp_amb": _t(ide, "cte:tpAmb", ns),
        "tp_cte": _t(ide, "cte:tpCTe", ns),
        "modal": _t(ide, "cte:modal", ns),
        "tp_serv": _t(ide, "cte:tpServ", ns),
        "c_mun_ini": _t(ide, "cte:cMunIni", ns),
        "x_mun_ini": _t(ide, "cte:xMunIni", ns),
        "uf_ini": _t(ide, "cte:UFIni", ns),
        "c_mun_fim": _t(ide, "cte:cMunFim", ns),
        "x_mun_fim": _t(ide, "cte:xMunFim", ns),
        "uf_fim": _t(ide, "cte:UFFim", ns),
    })

    # emitente
    emit = _el(inf, "cte:emit", ns)
    end_emit = _el(emit, "cte:enderEmit", ns)
    data.update({
        "emit_cnpj": _t(emit, "cte:CNPJ", ns),
        "emit_ie": _t(emit, "cte:IE", ns),
        "emit_xnome": _t(emit, "cte:xNome", ns),
        "emit_xfant": _t(emit, "cte:xFant", ns),
        "emit_uf": _t(end_emit, "cte:UF", ns),
        "emit_xmun": _t(end_emit, "cte:xMun", ns),
        "emit_cep": _t(end_emit, "cte:CEP", ns),
    })

    # remetente
    rem = _el(inf, "cte:rem", ns)
    end_rem = _el(rem, "cte:enderReme", ns)
    data.update({
        "rem_cnpj": _t(rem, "cte:CNPJ", ns),
        "rem_cpf": _t(rem, "cte:CPF", ns),
        "rem_ie": _t(rem, "cte:IE", ns),
        "rem_xnome": _t(rem, "cte:xNome", ns),
        "rem_uf": _t(end_rem, "cte:UF", ns),
        "rem_xmun": _t(end_rem, "cte:xMun", ns),
        "rem_cep": _t(end_rem, "cte:CEP", ns),
    })

    # destinatÃ¡rio
    dest = _el(inf, "cte:dest", ns)
    end_dest = _el(dest, "cte:enderDest", ns)
    data.update({
        "dest_cnpj": _t(dest, "cte:CNPJ", ns),
        "dest_cpf": _t(dest, "cte:CPF", ns),
        "dest_ie": _t(dest, "cte:IE", ns),
        "dest_xnome": _t(dest, "cte:xNome", ns),
        "dest_uf": _t(end_dest, "cte:UF", ns),
        "dest_xmun": _t(end_dest, "cte:xMun", ns),
        "dest_cep": _t(end_dest, "cte:CEP", ns),
    })

    # tomador (1=Remetente 2=Expedidor 3=Recebedor 4=Destinatario)
    # Localiza o elemento toma contendo CNPJ/nomeParticipante
    for toma_tag in ("cte:toma3", "cte:toma4"):
        toma = inf.find(f"cte:ide/{toma_tag}", ns)
        if toma is not None:
            data.update({
                "tom_cnpj": _t(toma, "cte:CNPJ", ns),
                "tom_cpf": _t(toma, "cte:CPF", ns),
                "tom_ie": _t(toma, "cte:IE", ns),
                "tom_xnome": _t(toma, "cte:xNome", ns),
            })
            break

    # valores prestaÃ§Ã£o
    vprest = _el(inf, "cte:vPrest", ns)
    data.update({
        "v_tprest": _t(vprest, "cte:vTPrest", ns),
        "v_rec": _t(vprest, "cte:vRec", ns),
    })

    # impostos
    imp = _el(inf, "cte:imp", ns)
    icms_el = imp.find(".//cte:ICMS", ns)  # pode ser ICMS00, ICMS45, etc.
    if icms_el is not None:
        # Procura o filho real (ICMS00, ICMS45, etc.)
        for child in icms_el:
            data["cst_icms"] = _t(child, "cte:CST", ns)
            data["v_bc_icms"] = _t(child, "cte:vBC", ns)
            data["v_icms"] = _t(child, "cte:vICMS", ns)
            break
    data["v_tot_trib"] = _t(imp, "cte:vTotTrib", ns)

    # carga
    inf_cte_norm = _el(inf, "cte:infCTeNorm", ns)
    inf_carga = _el(inf_cte_norm, "cte:infCarga", ns)
    data.update({
        "v_carga": _t(inf_carga, "cte:vCarga", ns),
        "pro_pred": _t(inf_carga, "cte:proPred", ns),
        "v_carga_averb": _t(inf_carga, "cte:vCargaAverb", ns),
    })

    # NF-e vinculadas
    inf_doc = inf_cte_norm.find("cte:infDoc", ns)
    nfe_chaves = []
    if inf_doc is not None:
        for inf_nfe in inf_doc.findall("cte:infNFe", ns):
            ch = _t(inf_nfe, "cte:chave", ns)
            if ch:
                nfe_chaves.append(ch)
    data["nfe_vinculadas"] = json.dumps(nfe_chaves) if nfe_chaves else None

    # modal rodoviÃ¡rio
    inf_modal = inf.find("cte:infModal", ns)
    if inf_modal is not None:
        rodo = inf_modal.find("cte:rodo", ns)
        if rodo is not None:
            data["rntrc"] = _t(rodo, "cte:RNTRC", ns)
            veic_tr = rodo.find("cte:veicTracao", ns)
            if veic_tr is not None:
                data["veic_placa"] = _t(veic_tr, "cte:placa", ns)

    # protocolo
    if tag == "cteProc":
        prot_cte = root.find("cte:protCTe", ns)
        if prot_cte is not None:
            inf_prot = _el(prot_cte, "cte:infProt", ns)
            data.update({
                "n_prot": _t(inf_prot, "cte:nProt", ns),
                "dh_recbto": _t(inf_prot, "cte:dhRecbto", ns),
                "c_stat": _t(inf_prot, "cte:cStat", ns),
                "x_motivo": _t(inf_prot, "cte:xMotivo", ns),
            })

    return data


# ---------------------------------------------------------------------------
# NFS-e (padrÃ£o ADN/SPED â€” versÃ£o 1.00)
# ---------------------------------------------------------------------------

_NS_NFSE = {"nfse": "http://www.sped.fazenda.gov.br/nfse"}


def parse_nfse(xml_path: str, informante: str = "") -> Dict[str, Any]:
    """
    Extrai campos relevantes de um XML NFS-e (padrÃ£o ADN/SPED versÃ£o 1.00).
    """
    root = _parse_tree(xml_path)
    data: Dict[str, Any] = {
        "informante": informante,
        "caminho_xml": str(xml_path),
        "caminho_pdf": None,
        "xml_status": "COMPLETO",
        "indexado_em": _now_iso(),
    }

    if root is None:
        return data

    ns = _NS_NFSE
    tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag

    # Localiza infNFSe
    if tag == "NFSe":
        inf = root.find("nfse:infNFSe", ns)
    else:
        inf = root.find(".//nfse:infNFSe", ns)

    if inf is None:
        # Tenta sem namespace
        inf = root.find(".//infNFSe")

    if inf is None:
        data["xml_status"] = "RESUMO"
        return data

    # Chave = Id do infNFSe
    chave = inf.get("Id", "")
    data["chave"] = chave

    data.update({
        "n_nfse": _t(inf, "nfse:nNFSe", ns),
        "n_dfse": _t(inf, "nfse:nDFSe", ns),
        "dh_proc": _t(inf, "nfse:dhProc", ns),
        "c_stat": _t(inf, "nfse:cStat", ns),
        "x_motivo": _t(inf, "nfse:xMotivo", ns),
        "tp_emis": _t(inf, "nfse:tpEmis", ns),
        "tp_amb": _t(inf, "nfse:ambGer", ns),
        "ver_aplic": _t(inf, "nfse:verAplic", ns),
        "c_loc_incid": _t(inf, "nfse:cLocIncid", ns),
        "x_loc_incid": _t(inf, "nfse:xLocIncid", ns),
        "x_trib_nac": _t(inf, "nfse:xTribNac", ns),
        "x_trib_mun": _t(inf, "nfse:xTribMun", ns),
        "x_nbs": _t(inf, "nfse:xNBS", ns),
    })

    # emit (prestador declarado no infNFSe)
    emit = _el(inf, "nfse:emit", ns)
    end_emit = _el(emit, "nfse:enderNac", ns)
    data.update({
        "prest_cnpj": _t(emit, "nfse:CNPJ", ns),
        "prest_cpf": _t(emit, "nfse:CPF", ns),
        "prest_im": _t(emit, "nfse:IM", ns),
        "prest_xnome": _t(emit, "nfse:xNome", ns),
        "prest_xfant": _t(emit, "nfse:xFant", ns),
        "prest_cmun": _t(end_emit, "nfse:cMun", ns),
        "prest_uf": _t(end_emit, "nfse:UF", ns),
        "prest_cep": _t(end_emit, "nfse:CEP", ns),
        "prest_email": _t(emit, "nfse:email", ns),
    })

    # valores (nÃ­vel infNFSe)
    valores = _el(inf, "nfse:valores", ns)
    data.update({
        "v_bc": _t(valores, "nfse:vBC", ns),
        "p_aliq": _t(valores, "nfse:pAliqAplic", ns),
        "v_issqn": _t(valores, "nfse:vISSQN", ns),
        "v_total_ret": _t(valores, "nfse:vTotalRet", ns),
        "v_liq": _t(valores, "nfse:vLiq", ns),
        "v_calc_dr": _t(valores, "nfse:vCalcDR", ns),
    })

    # DPS â†’ infDPS â†’ prest / toma / serv / valores
    dps = inf.find("nfse:DPS", ns)
    if dps is None:
        dps = inf.find(".//nfse:DPS", ns)

    if dps is not None:
        _inf_dps_raw = dps.find("nfse:infDPS", ns)
        inf_dps = _inf_dps_raw if _inf_dps_raw is not None else dps
        data.update({
            "tp_amb": _t(inf_dps, "nfse:tpAmb", ns) or data.get("tp_amb"),
            "dh_emi": _t(inf_dps, "nfse:dhEmi", ns),
            "ver_aplic": _t(inf_dps, "nfse:verAplic", ns) or data.get("ver_aplic"),
            "serie": _t(inf_dps, "nfse:serie", ns),
            "n_dps": _t(inf_dps, "nfse:nDPS", ns),
            "d_compet": _t(inf_dps, "nfse:dCompet", ns),
        })

        # prest (prestador no DPS â€” regime tributÃ¡rio)
        prest = _el(inf_dps, "nfse:prest", ns)
        data["prest_email"] = _t(prest, "nfse:email", ns) or data.get("prest_email")
        reg_trib = _el(prest, "nfse:regTrib", ns)
        data.update({
            "op_simp_nac": _t(reg_trib, "nfse:opSimpNac", ns),
            "reg_esp_trib": _t(reg_trib, "nfse:regEspTrib", ns),
        })

        # toma (tomador)
        toma = _el(inf_dps, "nfse:toma", ns)
        _end_toma_a = toma.find("nfse:end", ns)
        _end_toma_b = toma.find("nfse:enderNac", ns)
        end_toma = _end_toma_a if _end_toma_a is not None else (_end_toma_b if _end_toma_b is not None else ET.Element("_"))
        data.update({
            "tom_cnpj": _t(toma, "nfse:CNPJ", ns),
            "tom_cpf": _t(toma, "nfse:CPF", ns),
            "tom_xnome": _t(toma, "nfse:xNome", ns),
            "tom_cmun": _t(end_toma, "nfse:cMun", ns),
            "tom_uf": _t(end_toma, "nfse:UF", ns),
            "tom_cep": _t(end_toma, "nfse:CEP", ns),
            "tom_email": _t(toma, "nfse:email", ns),
        })

        # serv
        serv = _el(inf_dps, "nfse:serv", ns)
        loc_prest = _el(serv, "nfse:locPrest", ns)
        data["c_loc_prestacao"] = (
            _t(loc_prest, "nfse:cLocPrestacao", ns)
            or _t(loc_prest, "nfse:cPaisPrestacao", ns)
        )
        cserv = _el(serv, "nfse:cServ", ns)
        data.update({
            "c_trib_nac": _t(cserv, "nfse:cTribNac", ns),
            "c_trib_mun": _t(cserv, "nfse:cTribMun", ns),
            "x_desc_serv": _t(cserv, "nfse:xDescServ", ns),
            "c_nbs": _t(cserv, "nfse:cNBS", ns),
        })

        # valores do serviÃ§o no DPS
        vals_dps = _el(inf_dps, "nfse:valores", ns)
        v_serv_prest = _el(vals_dps, "nfse:vServPrest", ns)
        v_serv = _t(v_serv_prest, "nfse:vServ", ns)
        if v_serv:
            data["v_serv"] = v_serv
        trib = _el(vals_dps, "nfse:trib", ns)
        trib_mun = _el(trib, "nfse:tribMun", ns)
        p_aliq_dps = _t(trib_mun, "nfse:pAliq", ns)
        if p_aliq_dps:
            data["p_aliq"] = p_aliq_dps

    return data


# ---------------------------------------------------------------------------
# NFS-e (padrão ABRASF – DominioWeb / sistemas municipais)
# ---------------------------------------------------------------------------

_NS_ABRASF = {"ab": "http://www.abrasf.org.br/nfse.xsd"}


def parse_nfse_abrasf(xml_path: str, informante: str = "") -> List[Dict[str, Any]]:
    """
    Extrai campos relevantes de NFS-e no formato ABRASF (DominioWeb / municipal).

    O arquivo pode ter root ListaNotaFiscal (múltiplas notas), CompNfse ou Nfse.
    Retorna uma lista — um dict por InfNfse encontrado.
    """
    root = _parse_tree(xml_path)
    if root is None:
        return []

    ns = _NS_ABRASF
    results: List[Dict[str, Any]] = []

    # Localiza todos os InfNfse no documento, com ou sem namespace
    inf_list = root.findall(".//ab:InfNfse", ns)
    if not inf_list:
        inf_list = root.findall(".//InfNfse")

    def _tx(parent, tag: str) -> Optional[str]:
        """Busca texto com ns ABRASF e, em fallback, sem namespace."""
        ns_tag = f"ab:{tag}"
        el = parent.find(ns_tag, ns)
        if el is None:
            el = parent.find(tag)
        return el.text.strip() if el is not None and el.text else None

    def _ex(parent, tag: str):
        """Retorna sub-elemento com ns ABRASF ou sem namespace, nunca None."""
        ns_tag = f"ab:{tag}"
        el = parent.find(ns_tag, ns)
        if el is None:
            el = parent.find(tag)
        return el if el is not None else ET.Element("_")

    for inf in inf_list:
        numero = _tx(inf, "Numero") or ""
        prest = _ex(inf, "PrestadorServico")
        id_prest = _ex(prest, "IdentificacaoPrestador")
        prest_cnpj = _tx(id_prest, "Cnpj") or ""

        # chave: CNPJ_prestador + numero (zero-padded to 15 digits) para unicidade
        if prest_cnpj and numero:
            chave = f"{prest_cnpj}_{numero.zfill(15)}"
        else:
            chave = inf.get("Id", "")

        end_prest = _ex(prest, "Endereco")
        cont_prest = _ex(prest, "Contato")

        toma = _ex(inf, "TomadorServico")
        id_toma = _ex(toma, "IdentificacaoTomador")
        cpf_cnpj_toma = _ex(id_toma, "CpfCnpj")
        tom_cnpj = _tx(cpf_cnpj_toma, "Cnpj")
        tom_cpf  = _tx(cpf_cnpj_toma, "Cpf")
        end_toma = _ex(toma, "Endereco")

        serv = _ex(inf, "Servico")
        valores = _ex(serv, "Valores")

        data: Dict[str, Any] = {
            "informante": informante,
            "caminho_xml": str(xml_path),
            "caminho_pdf": None,
            "xml_status": "COMPLETO",
            "indexado_em": _now_iso(),
            "chave": chave,
            "n_nfse": numero,
            "dh_emi": _tx(inf, "DataEmissao"),
            "d_compet": (_tx(inf, "Competencia") or "")[:10] or None,
            # prestador
            "prest_cnpj": prest_cnpj,
            "prest_im": _tx(id_prest, "InscricaoMunicipal"),
            "prest_xnome": _tx(prest, "RazaoSocial"),
            "prest_xfant": _tx(prest, "NomeFantasia"),
            "prest_uf": _tx(end_prest, "Uf"),
            "prest_cep": _tx(end_prest, "Cep"),
            "prest_cmun": _tx(end_prest, "CodigoMunicipio"),
            "prest_email": _tx(cont_prest, "Email"),
            # tomador
            "tom_cnpj": tom_cnpj,
            "tom_cpf": tom_cpf,
            "tom_xnome": _tx(toma, "RazaoSocial"),
            "tom_uf": _tx(end_toma, "Uf"),
            "tom_cep": _tx(end_toma, "Cep"),
            "tom_cmun": _tx(end_toma, "CodigoMunicipio"),
            "tom_email": _tx(_ex(toma, "Contato"), "Email"),
            # serviço
            "x_desc_serv": _tx(serv, "Discriminacao"),
            "c_trib_mun": _tx(serv, "ItemListaServico"),
            "c_loc_incid": _tx(serv, "CodigoMunicipio"),
            # valores
            "v_serv": _tx(valores, "ValorServicos"),
            "v_bc": _tx(valores, "BaseCalculo"),
            "p_aliq": _tx(valores, "Aliquota"),
            "v_issqn": _tx(valores, "ValorIss"),
            "v_liq": _tx(valores, "ValorLiquidoNfse"),
        }
        results.append(data)

    return results


# ---------------------------------------------------------------------------
# NFC-e (modelo 65)
# ---------------------------------------------------------------------------

def parse_nfce(xml_path: str, informante: str = "") -> Dict[str, Any]:
    """
    Extrai todos os campos relevantes de um XML NFC-e (modelo 65) e devolve
    um dicionário compatível com a tabela nfce_docs do banco de dados.
    """
    import json as _json
    from datetime import datetime as _dt

    _NS = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

    def _t(el, path):
        if el is None:
            return ""
        found = el.find(path, _NS)
        return (found.text or "").strip() if found is not None else ""

    root = _parse_tree(xml_path)
    if root is None:
        return {}

    # Suporte a nfeProc ou NFe como raiz
    inf = root.find(".//nfe:infNFe", _NS)
    if inf is None:
        return {}

    # Verifica modelo 65
    ide = inf.find("nfe:ide", _NS)
    mod = _t(ide, "nfe:mod")
    if mod != "65":
        return {}

    chave = (inf.get("Id") or "").replace("NFe", "")

    # --- Emitente ---
    emit = inf.find("nfe:emit", _NS)
    ender_emit = emit.find("nfe:enderEmit", _NS) if emit is not None else None

    # --- Destinatário (opcional na NFC-e) ---
    dest = inf.find("nfe:dest", _NS)
    ender_dest = dest.find("nfe:enderDest", _NS) if dest is not None else None  # noqa: F841

    # --- Produtos ---
    produtos = []
    for det in inf.findall("nfe:det", _NS):
        prod = det.find("nfe:prod", _NS)
        if prod is None:
            continue
        imp = det.find("nfe:imposto", _NS)
        icms_el = None
        if imp is not None:
            icms_group = imp.find("nfe:ICMS", _NS)
            if icms_group is not None:
                icms_el = next(iter(icms_group), None)

        v_bc_item = ""
        v_icms_item = ""
        if icms_el is not None:
            v_bc_item = _t(icms_el, "nfe:vBC")
            v_icms_item = _t(icms_el, "nfe:vICMS")

        item = {
            "nItem":   det.get("nItem", ""),
            "cProd":   _t(prod, "nfe:cProd"),
            "cEAN":    _t(prod, "nfe:cEAN"),
            "xProd":   _t(prod, "nfe:xProd"),
            "NCM":     _t(prod, "nfe:NCM"),
            "CFOP":    _t(prod, "nfe:CFOP"),
            "uCom":    _t(prod, "nfe:uCom"),
            "qCom":    _t(prod, "nfe:qCom"),
            "vUnCom":  _t(prod, "nfe:vUnCom"),
            "vProd":   _t(prod, "nfe:vProd"),
            "vDesc":   _t(prod, "nfe:vDesc"),
            "vBC":     v_bc_item,
            "vICMS":   v_icms_item,
        }
        infAdProd = _t(prod, "nfe:infAdProd")
        if infAdProd:
            item["infAdProd"] = infAdProd
        produtos.append(item)

    # --- Totais ---
    total = inf.find("nfe:total", _NS)
    icms_tot = total.find("nfe:ICMSTot", _NS) if total is not None else None

    # --- Pagamento ---
    pag = inf.find("nfe:pag", _NS)
    det_pag = pag.find("nfe:detPag", _NS) if pag is not None else None
    t_pag_list = []
    v_pag_total = ""
    if pag is not None:
        for dp in pag.findall("nfe:detPag", _NS):
            tp = _t(dp, "nfe:tPag")
            vp = _t(dp, "nfe:vPag")
            if tp:
                t_pag_list.append(tp)
            if vp and not v_pag_total:
                v_pag_total = vp
        v_troco = _t(pag, "nfe:vTroco")
    else:
        v_troco = ""

    # --- Suplementar (QR Code) ---
    supl = root.find(".//nfe:infNFeSupl", _NS)
    qr_code = _t(supl, "nfe:qrCode") if supl is not None else ""
    url_chave = _t(supl, "nfe:urlChave") if supl is not None else ""

    # --- Protocolo ---
    inf_prot = root.find(".//nfe:infProt", _NS)

    return {
        "chave":        chave,
        "informante":   informante,
        "caminho_xml":  str(xml_path),
        "caminho_pdf":  None,
        "xml_status":   "COMPLETO" if inf_prot is not None else "PENDENTE",
        # ide
        "c_uf":         _t(ide, "nfe:cUF"),
        "nat_op":       _t(ide, "nfe:natOp"),
        "mod":          mod,
        "serie":        _t(ide, "nfe:serie"),
        "n_nf":         _t(ide, "nfe:nNF"),
        "dh_emi":       _t(ide, "nfe:dhEmi"),
        "tp_nf":        _t(ide, "nfe:tpNF"),
        "c_mun_fg":     _t(ide, "nfe:cMunFG"),
        "tp_emis":      _t(ide, "nfe:tpEmis"),
        "fin_nfe":      _t(ide, "nfe:finNFe"),
        # emit
        "emit_cnpj":    _t(emit, "nfe:CNPJ"),
        "emit_cpf":     _t(emit, "nfe:CPF"),
        "emit_ie":      _t(emit, "nfe:IE"),
        "emit_xnome":   _t(emit, "nfe:xNome"),
        "emit_xfant":   _t(emit, "nfe:xFant"),
        "emit_xlgr":    _t(ender_emit, "nfe:xLgr"),
        "emit_nro":     _t(ender_emit, "nfe:nro"),
        "emit_xbairro": _t(ender_emit, "nfe:xBairro"),
        "emit_cmun":    _t(ender_emit, "nfe:cMun"),
        "emit_xmun":    _t(ender_emit, "nfe:xMun"),
        "emit_uf":      _t(ender_emit, "nfe:UF"),
        "emit_cep":     _t(ender_emit, "nfe:CEP"),
        "emit_crt":     _t(emit, "nfe:CRT"),
        # dest
        "dest_cnpj":    _t(dest, "nfe:CNPJ") if dest is not None else "",
        "dest_cpf":     _t(dest, "nfe:CPF") if dest is not None else "",
        "dest_xnome":   _t(dest, "nfe:xNome") if dest is not None else "",
        # produtos
        "produtos":     _json.dumps(produtos, ensure_ascii=False),
        "qt_itens":     len(produtos),
        # totais
        "v_prod":       _t(icms_tot, "nfe:vProd"),
        "v_desc":       _t(icms_tot, "nfe:vDesc"),
        "v_frete":      _t(icms_tot, "nfe:vFrete"),
        "v_seg":        _t(icms_tot, "nfe:vSeg"),
        "v_outro":      _t(icms_tot, "nfe:vOutro"),
        "v_pis":        _t(icms_tot, "nfe:vPIS"),
        "v_cofins":     _t(icms_tot, "nfe:vCOFINS"),
        "v_nf":         _t(icms_tot, "nfe:vNF"),
        "v_bc":         _t(icms_tot, "nfe:vBC"),
        "v_icms":       _t(icms_tot, "nfe:vICMS"),
        "v_icms_deson": _t(icms_tot, "nfe:vICMSDeson"),
        "v_tot_trib":   _t(icms_tot, "nfe:vTotTrib"),
        # pagamento
        "t_pag":        ",".join(t_pag_list),
        "v_pag":        v_pag_total,
        "v_troco":      v_troco,
        # suplementar
        "qr_code":      qr_code,
        "url_chave":    url_chave,
        # protocolo
        "n_prot":       _t(inf_prot, "nfe:nProt"),
        "dh_recbto":    _t(inf_prot, "nfe:dhRecbto"),
        "c_stat":       _t(inf_prot, "nfe:cStat"),
        "x_motivo":     _t(inf_prot, "nfe:xMotivo"),
        # controle
        "indexado_em":  _dt.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }


# ---------------------------------------------------------------------------
# Detecção automática de tipo por caminho ou conteúdo
# ---------------------------------------------------------------------------

def detectar_tipo(xml_path: str) -> Optional[str]:
    """
    Detecta o tipo de XML (NF-e, NFC-e, CT-e, NFS-e, NFS-e ABRASF) a partir
    do caminho do arquivo e, se necessário, do conteúdo da tag raiz.

    Returns:
        'NFe', 'CTe', 'NFSe', 'NFSe_ABRASF' ou None
    """
    path = Path(xml_path)
    partes = [p.upper() for p in path.parts]

    # Por conteúdo (lê apenas os primeiros 512 bytes) — mais confiável que pasta
    try:
        header = Path(xml_path).read_bytes()[:512].decode("utf-8", errors="ignore")
        if "abrasf.org.br" in header or "ListaNotaFiscal" in header:
            return "NFSe_ABRASF"
        if "sped.fazenda.gov.br/nfse" in header:
            return "NFSe"
        if "portalfiscal.inf.br/cte" in header:
            return "CTe"
        if "portalfiscal.inf.br/nfe" in header:
            # Distinguish NFC-e (model 65) from NF-e (model 55)
            try:
                from lxml import etree as _etree
                _tree = _etree.parse(xml_path)
                _inf = _tree.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
                if _inf is not None:
                    _ide = _inf.find('{http://www.portalfiscal.inf.br/nfe}ide')
                    _mod = _ide.findtext('{http://www.portalfiscal.inf.br/nfe}mod') if _ide is not None else ''
                    if (_mod or '').strip() == '65':
                        return "NFCe"
            except Exception:
                pass
            return "NFe"
    except Exception:
        pass

    # Fallback por pasta
    if "NFE" in partes or "NFe" in partes:
        return "NFe"
    if "CTE" in partes or "CTe" in partes:
        return "CTe"
    if "NFSE" in partes or "NFS-E" in partes:
        return "NFSe"

    # Por nome do arquivo
    nome = path.stem.upper()
    if nome.startswith("NFSE_") or nome.startswith("NFSe_"):
        return "NFSe"
    if nome.startswith("CTE") or nome.startswith("CTe"):
        return "CTe"
    if nome.startswith("NFE") or nome.startswith("NFe"):
        return "NFe"

    return None


def indexar_arquivo(xml_path: str, informante: str = "") -> Optional[Dict[str, Any]]:
    """
    Parser unificado: detecta o tipo e chama o parser correto.

    Para NFS-e ABRASF (que pode ter múltiplas notas por arquivo) retorna
    apenas o primeiro registro. Use parse_nfse_abrasf() diretamente para
    iterar todos.

    Returns:
        dict com os dados extraídos, ou None se o tipo não for reconhecido.
    """
    tipo = detectar_tipo(xml_path)
    if tipo == "NFe":
        return parse_nfe(xml_path, informante)
    if tipo == "NFCe":
        return parse_nfce(xml_path, informante)
    if tipo == "CTe":
        return parse_cte(xml_path, informante)
    if tipo == "NFSe":
        return parse_nfse(xml_path, informante)
    if tipo == "NFSe_ABRASF":
        lista = parse_nfse_abrasf(xml_path, informante)
        return lista[0] if lista else None
    return None

