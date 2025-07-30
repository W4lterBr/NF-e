#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOT - Busca NFE Completo (versão com sidebar mais legível e contadores independentes)
"""

import gzip
import base64
import logging
import sqlite3
import threading
from pathlib import Path
from datetime import datetime, timedelta

import requests
import requests_pkcs12
from zeep import Client
from zeep.transports import Transport
from zeep.exceptions import Fault
from lxml import etree

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, Menu, filedialog

from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

# -------------------------------------------------------------------
# Suprimir excesso de logs das bibliotecas SOAP/HTTP
# -------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logging.getLogger('zeep').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('requests_pkcs12').setLevel(logging.WARNING)

# -------------------------------------------------------------------
# Configurações gerais
# -------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent
URL_DISTRIBUICAO = (
    "https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/"
    "NFeDistribuicaoDFe.asmx?wsdl"
)
INTERVALO_HORARIO = 3600  # segundos (1 hora)

CODIGOS_UF = {
    '11':'RO','12':'AC','13':'AM','14':'RR','15':'PA','16':'AP','17':'TO',
    '21':'MA','22':'PI','23':'CE','24':'RN','25':'PB','26':'PE','27':'AL','28':'SE','29':'BA',
    '31':'MG','32':'ES','33':'RJ','35':'SP','41':'PR','42':'SC','43':'RS',
    '50':'MS','51':'MT','52':'GO','53':'DF'
}

PASTA_XMLS          = SCRIPT_DIR / "xmls"
PASTA_XML_EXTRAIDOS = SCRIPT_DIR / "xml_extraidos"
PASTA_XML_ENVIO     = SCRIPT_DIR / "xml_envio"
PASTA_XML_RESPOSTA  = SCRIPT_DIR / "xml_resposta_sefaz"
for pasta in (PASTA_XMLS, PASTA_XML_EXTRAIDOS, PASTA_XML_ENVIO, PASTA_XML_RESPOSTA):
    pasta.mkdir(exist_ok=True)

BANCO_PATH = SCRIPT_DIR / "notas.db"

COLUNAS = [
    "IE Tomador","Filial","Nome","CNPJ/CPF","Num","DtEmi",
    "Tipo","Valor","Status","UF","Chave","Natureza"
]

# -------------------------------------------------------------------
# Gerenciamento de Banco de Dados
# -------------------------------------------------------------------
class DatabaseManager:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._initialize()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _initialize(self):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute('''CREATE TABLE IF NOT EXISTS certificados (
                id INTEGER PRIMARY KEY,
                cnpj_cpf TEXT, caminho TEXT, senha TEXT,
                informante TEXT, cUF_autor TEXT
            )''')
            cur.execute('''CREATE TABLE IF NOT EXISTS armazenamento (
                informante TEXT PRIMARY KEY, pasta TEXT
            )''')
            cur.execute('''CREATE TABLE IF NOT EXISTS nsu (
                informante TEXT PRIMARY KEY, ult_nsu TEXT
            )''')
            cur.execute('''CREATE TABLE IF NOT EXISTS xmls_baixados (
                chave TEXT PRIMARY KEY, cnpj_cpf TEXT
            )''')
            cur.execute('''CREATE TABLE IF NOT EXISTS last_search (
                key TEXT PRIMARY KEY, last_run TEXT
            )''')
            conn.commit()

    def add_certificado(self, cnpj, caminho, senha, informante, cuf):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM certificados WHERE informante=?", (informante,))
            if cur.fetchone():
                return False
            cur.execute(
                "INSERT INTO certificados (cnpj_cpf,caminho,senha,informante,cUF_autor)"
                " VALUES (?,?,?,?,?)",
                (cnpj, caminho, senha, informante, cuf)
            )
            conn.commit()
        return True

    def update_certificado(self, caminho, new_cnpj, new_informante):
        with self._connect() as conn:
            conn.execute(
                "UPDATE certificados SET cnpj_cpf=?, informante=? WHERE caminho=?",
                (new_cnpj, new_informante, caminho)
            )
            conn.commit()

    def get_certificados(self):
        with self._connect() as conn:
            return conn.execute(
                "SELECT cnpj_cpf,caminho,senha,informante,cUF_autor FROM certificados"
            ).fetchall()

    def get_ult_nsu(self, informante):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT ult_nsu FROM nsu WHERE informante=?", (informante,)
            ).fetchone()
            return row[0] if row else "000000000000000"

    def set_ult_nsu(self, informante, nsu):
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO nsu (informante,ult_nsu) VALUES (?,?)",
                (informante, nsu)
            )
            conn.commit()

    def set_pasta(self, informante, pasta):
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO armazenamento (informante,pasta) VALUES (?,?)",
                (informante, pasta)
            )
            conn.commit()

    def get_pasta(self, informante):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT pasta FROM armazenamento WHERE informante=?", (informante,)
            ).fetchone()
            return row[0] if row else None

    def registrar_xml(self, chave, cnpj):
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO xmls_baixados (chave,cnpj_cpf) VALUES (?,?)",
                (chave, cnpj)
            )
            conn.commit()

    def set_last_search(self, key, when_iso):
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO last_search (key,last_run) VALUES (?,?)",
                (key, when_iso)
            )
            conn.commit()

    def get_last_search(self, key):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT last_run FROM last_search WHERE key=?", (key,)
            ).fetchone()
            return row[0] if row else None


# -------------------------------------------------------------------
# Processamento de XML
# -------------------------------------------------------------------
class XMLProcessor:
    NS = {'nfe':'http://www.portalfiscal.inf.br/nfe'}

    @staticmethod
    def formatar_brl(valor):
        try:
            v = float(valor)
            return f"R$ {v:,.2f}".replace(',','X').replace('.',',').replace('X','.')
        except:
            return valor or ""

    def parse_nfe(self, xml_str, cert_informante=None):
        try:
            tree = etree.fromstring(xml_str.encode('utf-8'))
            inf = tree.find('.//nfe:infNFe', namespaces=self.NS)
            if not inf:
                return {}
            ide  = inf.find('nfe:ide', namespaces=self.NS)
            emit = inf.find('nfe:emit', namespaces=self.NS)
            dest = inf.find('nfe:dest', namespaces=self.NS)
            tot  = tree.find('.//nfe:ICMSTot', namespaces=self.NS)
            vnf  = tot.findtext('nfe:vNF', namespaces=self.NS) if tot else ''
            valor= self.formatar_brl(vnf)
            xm   = tree.find('.//nfe:xMotivo', namespaces=self.NS)
            xmot = xm.text if xm is not None else ''

            filial = dest.findtext('nfe:IE', namespaces=self.NS) or ''
            cnpj_dest = dest.findtext('nfe:CNPJ', namespaces=self.NS) or ''
            if cert_informante and cnpj_dest == cert_informante:
                nome_dest = dest.findtext('nfe:xNome', namespaces=self.NS)
                if nome_dest:
                    filial = nome_dest

            return {
                'IE Tomador': dest.findtext('nfe:IE', namespaces=self.NS) or '',
                'Filial':      filial,
                'Nome':        emit.findtext('nfe:xNome', namespaces=self.NS) or '',
                'CNPJ/CPF':    emit.findtext('nfe:CNPJ', namespaces=self.NS)
                               or emit.findtext('nfe:CPF', namespaces=self.NS) or '',
                'Num':         ide.findtext('nfe:nNF',  namespaces=self.NS) or '',
                'DtEmi':       (ide.findtext('nfe:dhEmi', namespaces=self.NS)[:10]
                                if ide.findtext('nfe:dhEmi', namespaces=self.NS) else ''),
                'Tipo':        'NFe',
                'Valor':       valor,
                'Status':      xmot,
                'UF':          CODIGOS_UF.get(ide.findtext('nfe:cUF', namespaces=self.NS) or '', ''),
                'Chave':       inf.attrib.get('Id','')[-44:],
                'Natureza':    ide.findtext('nfe:natOp', namespaces=self.NS) or ''
            }
        except Exception:
            return {}

    def extract_docs(self, resp_xml):
        docs = []
        try:
            tree = etree.fromstring(resp_xml.encode('utf-8'))
            for dz in tree.findall('.//nfe:docZip', namespaces=self.NS):
                nsu = dz.get('NSU','')
                content = dz.text or ''
                data = base64.b64decode(content)
                xml  = gzip.decompress(data).decode('utf-8')
                docs.append((nsu,xml))
        except:
            pass
        return docs

    def extract_last_nsu(self, resp_xml):
        try:
            tree = etree.fromstring(resp_xml.encode('utf-8'))
            ult  = tree.find('.//nfe:ultNSU', namespaces=self.NS)
            if ult is not None and ult.text.isdigit():
                return ult.text.zfill(15)
        except:
            pass
        return None


# -------------------------------------------------------------------
# Serviço SOAP
# -------------------------------------------------------------------
class NFeService:
    def __init__(self, cert_path, senha, informante, cuf):
        sess = requests.Session()
        sess.mount('https://', requests_pkcs12.Pkcs12Adapter(
            pkcs12_filename=cert_path, pkcs12_password=senha
        ))
        trans = Transport(session=sess)
        self.client = Client(wsdl=URL_DISTRIBUICAO, transport=trans)
        self.informante = informante
        self.cuf = cuf

    def _check_status(self, resp_str):
        tree = etree.fromstring(resp_str.encode('utf-8'))
        cstat = tree.find('.//{http://www.portalfiscal.inf.br/nfe}cStat')
        xmot  = tree.find('.//{http://www.portalfiscal.inf.br/nfe}xMotivo')
        code = cstat.text if cstat is not None else None

        if code == '656':
            logging.info(f"{self.informante}: sem novos documentos ({code})")
            return False

        if code and code != '138':
            msg = xmot.text if xmot is not None else f"cStat={code}"
            logging.error(f"SEFAZ inválido: {msg}")
            messagebox.showerror("Erro SEFAZ", msg)
            return False

        return True

    def fetch_by_cnpj(self, tipo, ult_nsu):
        root = etree.Element("distDFeInt",
            xmlns=XMLProcessor.NS['nfe'], versao="1.01"
        )
        etree.SubElement(root, "tpAmb").text    = "1"
        etree.SubElement(root, "cUFAutor").text = str(self.cuf)
        etree.SubElement(root, tipo).text       = self.informante
        dist = etree.SubElement(root, "distNSU")
        etree.SubElement(dist, "ultNSU").text   = ult_nsu

        try:
            resp = self.client.service.nfeDistDFeInteresse(nfeDadosMsg=root)
        except Fault as fault:
            logging.error(f"SOAP Fault: {fault}")
            messagebox.showerror("Erro SEFAZ", str(fault))
            return None

        resp_str = etree.tostring(resp, encoding='utf-8').decode()
        if not self._check_status(resp_str):
            return None

        (PASTA_XML_ENVIO / f"{datetime.now():%Y%m%d_%H%M%S}_envio.xml"
        ).write_bytes(etree.tostring(root, pretty_print=True, encoding='utf-8'))
        (PASTA_XML_RESPOSTA / f"{self.informante}_{datetime.now():%Y%m%d_%H%M%S}_resposta.xml"
        ).write_text(resp_str, encoding='utf-8')

        return resp_str

    def fetch_by_chave(self, chave):
        root = etree.Element("distDFeInt",
            xmlns=XMLProcessor.NS['nfe'], versao="1.01"
        )
        etree.SubElement(root, "tpAmb").text    = "1"
        etree.SubElement(root, "cUFAutor").text = str(self.cuf)
        tag = "CNPJ" if len(self.informante)==14 else "CPF"
        etree.SubElement(root, tag).text        = self.informante
        cons = etree.SubElement(root, "consChNFe")
        etree.SubElement(cons, "chNFe").text    = chave

        try:
            resp = self.client.service.nfeDistDFeInteresse(nfeDadosMsg=root)
        except Fault as fault:
            logging.error(f"SOAP Fault: {fault}")
            messagebox.showerror("Erro SEFAZ", str(fault))
            return None

        resp_str = etree.tostring(resp, encoding='utf-8').decode()
        if not self._check_status(resp_str):
            return None

        (PASTA_XML_ENVIO / f"{datetime.now():%Y%m%d_%H%M%S}_ch{chave}_envio.xml"
        ).write_bytes(etree.tostring(root, pretty_print=True, encoding='utf-8'))
        (PASTA_XML_RESPOSTA / f"{datetime.now():%Y%m%d_%H%M%S}_ch{chave}_resposta.xml"
        ).write_text(resp_str, encoding='utf-8')

        return resp_str


# -------------------------------------------------------------------
# Interface Tkinter
# -------------------------------------------------------------------
class AppUI:
    def __init__(self, root):
        self.db     = DatabaseManager(BANCO_PATH)
        self.parser = XMLProcessor()

        root.title("BOT - Busca NFE")
        root.geometry("1600x700")
        self._load_certificates()
        self._setup_style()
        self._build_menu()
        self._build_sidebar()
        self._build_tree()
        self.show_all_xmls()
        self._start_countdowns()

    def _load_certificates(self):
        self.certs = []
        for cnpj, path, senha, inf, cuf in self.db.get_certificados():
            last_iso = self.db.get_last_search(inf) or datetime.now().isoformat()
            last_dt  = datetime.fromisoformat(last_iso)
            next_run = last_dt + timedelta(seconds=INTERVALO_HORARIO)
            # grava o last_search de volta pra manter consistência
            self.db.set_last_search(inf, last_iso)
            self.certs.append({
                "cnpj":cnpj, "path":path, "senha":senha,
                "informante":inf, "cuf":cuf,
                "last":last_dt, "next":next_run
            })

    def _setup_style(self):
        self.font = ("Arial",9)
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", font=self.font)
        style.configure("Treeview.Heading", background="#37506c", foreground="#ffffff")
        style.configure("Treeview", rowheight=24, fieldbackground="#ffffff")
        style.configure("TFrame", background="#F0F4F8")
        style.configure("TLabel", background="#F0F4F8")

    def _build_menu(self):
        mb = Menu(self.root, font=self.font)
        ac = Menu(mb, tearoff=0, font=self.font)
        ac.add_command(label="Certificados",       command=self.show_certificates_popup)
        ac.add_command(label="Adicionar Certificado", command=self.add_certificate)
        ac.add_command(label="Buscar por Chave",      command=self.prompt_search_key)
        ac.add_separator()
        ac.add_command(label="Atualizar Agora",       command=self.update_all_async)
        mb.add_cascade(label="Ações", menu=ac)
        mb.add_command(label="Sair", command=self.root.destroy)
        self.root.config(menu=mb)

    def _build_sidebar(self):
        frm = ttk.Frame(self.root)
        frm.pack(side="left", fill="y", padx=8, pady=8)
        ttk.Label(frm, text="Certificados", font=("Arial",14,"bold")).pack(anchor="w", pady=(0,8))
        self.check_vars = {}
        all_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm, text="Todos", variable=all_var,
                        command=self.toggle_all).pack(anchor="w", pady=(0,8))
        self.check_vars["ALL"] = all_var

        self.lbl_counters = {}
        for cert in self.certs:
            inf = cert["informante"]
            v = tk.BooleanVar(value=True)
            row = ttk.Frame(frm)
            row.pack(anchor="w", padx=12, pady=2)
            cb = ttk.Checkbutton(
                row,
                text=f"{cert['informante']} : {cert['cnpj']}",
                variable=v,
                command=self.filter_tree
            )
            cb.pack(side="left")
            lbl = ttk.Label(
                row,
                text="próximo em --:--",
                font=self.font
            )
            lbl.pack(side="left", padx=8)
            self.check_vars[inf] = v
            self.lbl_counters[inf] = lbl

    def toggle_all(self):
        val = self.check_vars["ALL"].get()
        for k,v in self.check_vars.items():
            if k!="ALL":
                v.set(val)
        self.filter_tree()

    def _build_tree(self):
        cont = ttk.Frame(self.root)
        cont.pack(side="right", fill="both", expand=True, padx=8, pady=8)
        self.tree = ttk.Treeview(cont, columns=COLUNAS, show="headings")
        for col in COLUNAS:
            self.tree.heading(col, text=col,
                              command=lambda c=col: self.sort_column(c, False))
            self.tree.column(col, width=100 if col!="Nome" else 200)
        self.tree.pack(fill="both", expand=True, side="left")
        sb = ttk.Scrollbar(cont, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscroll=sb.set)
        self.tree.tag_configure('even', background="#ffffff")
        self.tree.tag_configure('odd',  background="#f4f4f4")

    def add_certificate(self):
        path = filedialog.askopenfilename(filetypes=[("PFX","*.pfx")])
        if not path: return
        senha = simpledialog.askstring("Senha","Senha do certificado:",show="*")
        if senha is None: return
        try:
            data = Path(path).read_bytes()
            _, cert, _ = pkcs12.load_key_and_certificates(data, senha.encode())
            cn = next(a.value for a in cert.subject
                      if a.oid==NameOID.COMMON_NAME)
            digits = ''.join(filter(str.isdigit, cn))
            informante = digits
        except Exception as e:
            messagebox.showerror("Erro","Falha ao ler certificado:\n"+str(e))
            return

        cuf = simpledialog.askstring("UF","Código UF (ex:35):")
        if not (cuf and cuf in CODIGOS_UF):
            messagebox.showwarning("UF inválida","Digite um código UF válido.")
            return

        if self.db.add_certificado(informante,path,senha,informante,cuf):
            messagebox.showinfo("OK","Certificado salvo. Reinicie o app.")
        else:
            messagebox.showwarning("Duplicado","Certificado já cadastrado.")

    def prompt_search_key(self):
        key = simpledialog.askstring("Chave","Chave 44 dígitos:")
        if not (key and key.isdigit() and len(key)==44):
            messagebox.showwarning("Inválida","Chave deve ter 44 dígitos.")
            return
        cert = self.certs[0]
        svc  = NFeService(cert["path"],cert["senha"],cert["cnpj"],cert["cuf"])
        resp = svc.fetch_by_chave(key)
        if not resp:
            return
        for nsu,xml in self.parser.extract_docs(resp):
            fn = f"{nsu}_{datetime.now():%Y%m%d_%H%M%S}.xml"
            (PASTA_XMLS/ fn).write_text(xml,encoding='utf-8')
        self.show_all_xmls()

    def show_all_xmls(self):
        self._full = []
        seen = set()
        self.tree.delete(*self.tree.get_children())
        for arq in PASTA_XMLS.glob("*.xml"):
            txt = arq.read_text(encoding='utf-8')
            for cert in self.certs:
                d = self.parser.parse_nfe(txt, cert_informante=cert["cnpj"])
                chave = d.get("Chave")
                if d and chave and chave not in seen:
                    seen.add(chave)
                    d["_owner"] = cert["informante"]
                    self._full.append(d)
        for i,d in enumerate(self._full):
            tag = 'even' if i%2==0 else 'odd'
            self.tree.insert("", "end",
                values=[d.get(c,"") for c in COLUNAS],
                tags=(tag,)
            )

    def filter_tree(self):
        ativos = {k for k,v in self.check_vars.items()
                  if k!="ALL" and v.get()}
        self.tree.delete(*self.tree.get_children())
        for i,d in enumerate(self._full):
            if d["_owner"] in ativos:
                tag = 'even' if i%2==0 else 'odd'
                self.tree.insert("", "end",
                    values=[d.get(c,"") for c in COLUNAS],
                    tags=(tag,)
                )

    def sort_column(self, col, rev):
        data = [(self.tree.set(k,col), k) for k in self.tree.get_children("")]
        try:
            data.sort(key=lambda t: float(
                t[0].replace("R$","").replace(".","").replace(",",".")),
                       reverse=rev)
        except:
            data.sort(reverse=rev)
        for idx,(_,k) in enumerate(data):
            self.tree.move(k,"",idx)
        self.tree.heading(col,
            command=lambda: self.sort_column(col, not rev)
        )

    def update_all_async(self):
        for cert in self.certs:
            threading.Thread(
                target=self._update_worker,
                args=(cert,), daemon=True
            ).start()

    def _update_worker(self, cert):
        svc  = NFeService(cert["path"],cert["senha"],cert["cnpj"],cert["cuf"])
        last = self.db.get_ult_nsu(cert["informante"])
        resp = svc.fetch_by_cnpj(
            "CNPJ" if len(cert["cnpj"])==14 else "CPF",
            last
        )
        if not resp:
            return
        new_nsu = self.parser.extract_last_nsu(resp)
        for nsu,xml in self.parser.extract_docs(resp):
            fn = f"{nsu}_{datetime.now():%Y%m%d_%H%M%S}.xml"
            (PASTA_XMLS/ fn).write_text(xml,encoding='utf-8')
        if new_nsu:
            self.db.set_ult_nsu(cert["informante"], new_nsu)
        now = datetime.now()
        self.db.set_last_search(cert["informante"], now.isoformat())
        cert["next"] = now + timedelta(seconds=INTERVALO_HORARIO)
        self.show_all_xmls()

    def show_certificates_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("Certificados Cadastrados")
        popup.transient(self.root)
        popup.grab_set()
        popup.geometry("+%d+%d" % (self.root.winfo_rootx()+150,
                                   self.root.winfo_rooty()+100))
        frame = ttk.Frame(popup, padding=10)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Certificado", font=("Arial",11,"bold")).grid(row=0,column=0,sticky="w")
        ttk.Label(frame, text="Próximo em",   font=("Arial",11,"bold")).grid(row=0,column=1,sticky="w", padx=20)
        for idx, cert in enumerate(self.certs, start=1):
            ttk.Label(frame, text=cert["informante"] , wraplength=300).grid(row=idx,column=0, sticky="w", pady=5)
            # crio um label de contador temporário no cert para ser atualizado
            lbl = ttk.Label(frame, text="--:--")
            lbl.grid(row=idx,column=1, sticky="w", padx=20)
            cert.setdefault("popup_lbls", []).append(lbl)
            btn = ttk.Button(frame, text="Excluir",
                             command=lambda c=cert: self._delete_cert(c, popup))
            btn.grid(row=idx, column=2, padx=10)

        ttk.Button(popup, text="Fechar", command=popup.destroy).pack(pady=10)

    def _delete_cert(self, cert, popup):
        self.db._connect().execute(
            "DELETE FROM certificados WHERE informante=?", (cert["informante"],)
        )
        self.db._connect().commit()
        popup.destroy()
        self._load_certificates()
        self.show_all_xmls()
        self._build_sidebar()

    def _start_countdowns(self):
        for cert in self.certs:
            self._tick(cert)

    def _tick(self, cert):
        remaining = (cert["next"] - datetime.now()).total_seconds()
        if remaining <= 0:
            # dispara nova busca e reinicia o próximo horário
            self.update_all_async()
            cert["next"] = datetime.now() + timedelta(seconds=INTERVALO_HORARIO)
            remaining = INTERVALO_HORARIO

        mins, secs = divmod(int(remaining), 60)
        text = f"próximo em {mins:02d}:{secs:02d}"

        # atualiza contador na sidebar
        lbl_side = self.lbl_counters.get(cert["informante"])
        if lbl_side and lbl_side.winfo_exists():
            lbl_side.config(text=text)

        # atualiza contador no popup, se existir
        for lbl in cert.get("popup_lbls", []):
            if lbl.winfo_exists():
                lbl.config(text=text)

        # agenda próxima atualização
        self.root.after(1000, lambda c=cert: self._tick(c))

    @property
    def root(self):
        return tk._default_root

def main():
    root = tk.Tk()
    AppUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()
