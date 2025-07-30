import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, Menu, filedialog, simpledialog
import requests_pkcs12

from lxml import etree
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

# --- CONFIGURAÇÃO ---------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
DB_PATH    = SCRIPT_DIR / "notas.db"   # <-- único banco sempre aqui
XML_DIR    = SCRIPT_DIR / "xmls"

CODIGOS_UF = {
    '11':'RO','12':'AC','13':'AM','14':'RR','15':'PA','16':'AP','17':'TO',
    '21':'MA','22':'PI','23':'CE','24':'RN','25':'PB','26':'PE','27':'AL','28':'SE','29':'BA',
    '31':'MG','32':'ES','33':'RJ','35':'SP','41':'PR','42':'SC','43':'RS',
    '50':'MS','51':'MT','52':'GO','53':'DF'
}

COLUMNS = [
    "IE Tomador","Filial","Nome","CNPJ/CPF","Num","DtEmi",
    "Tipo","Valor","Status","UF","Chave","Natureza"
]

# --- ACESSO A BANCO -------------------------------------------------------

class DatabaseManager:
    def __init__(self, path: Path):
        self.path = path

    def _connect(self):
        return sqlite3.connect(self.path)

    def add_certificado(self, cnpj, caminho, senha, informante, cuf):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM certificados WHERE informante=?", (informante,))
            if cur.fetchone():
                return False
            cur.execute(
                "INSERT INTO certificados (cnpj_cpf,caminho,senha,informante,cUF_autor)"
                " VALUES (?,?,?,?,?)",
                (cnpj, str(caminho), senha, informante, cuf)
            )
            conn.commit()
        return True

    def delete_certificate(self, informante: str):
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM certificados WHERE informante = ?", (informante,)
            )
            conn.commit()

    def get_certificates(self):
        with self._connect() as conn:
            return conn.execute(
                "SELECT cnpj_cpf,caminho,senha,informante,cUF_autor FROM certificados"
            ).fetchall()

    def get_nf_status(self, chave: str):
        """Retorna (cStat, xMotivo) ou None."""
        try:
            with self._connect() as conn:
                # CORREÇÃO: usar chNFe (coluna real) e não "chave"
                cur = conn.execute(
                    "SELECT cStat, xMotivo FROM nf_status WHERE chNFe = ?", (chave,)
                )
                return cur.fetchone()
        except sqlite3.OperationalError:
            return None

# --- PARSE XML ------------------------------------------------------------

class XMLProcessor:
    NS = {'nfe': "http://www.portalfiscal.inf.br/nfe"}

    @staticmethod
    def formatar_brl(valor):
        try:
            v = float(valor)
            return f"R$ {v:,.2f}"\
                   .replace(',','X').replace('.',',').replace('X','.')
        except:
            return valor or ""

    def parse_nfe(self, xml_str):
        try:
            tree = etree.fromstring(xml_str.encode('utf-8'))
            inf = tree.find('.//nfe:infNFe', namespaces=self.NS)
            if inf is None:
                return {}
            ide  = inf.find('nfe:ide', namespaces=self.NS)
            emit = inf.find('nfe:emit', namespaces=self.NS)
            dest = inf.find('nfe:dest', namespaces=self.NS)
            tot  = tree.find('.//nfe:ICMSTot', namespaces=self.NS)
            vnf  = tot.findtext('nfe:vNF', namespaces=self.NS) if tot else ''
            valor= self.formatar_brl(vnf)

            return {
                'IE Tomador': dest.findtext('nfe:IE', namespaces=self.NS) or '',
                'Filial':      dest.findtext('nfe:IE', namespaces=self.NS) or '',
                'Nome':        emit.findtext('nfe:xNome', namespaces=self.NS) or '',
                'CNPJ/CPF':    emit.findtext('nfe:CNPJ', namespaces=self.NS)
                               or emit.findtext('nfe:CPF', namespaces=self.NS) or '',
                'Num':         ide.findtext('nfe:nNF',  namespaces=self.NS) or '',
                'DtEmi':       (ide.findtext('nfe:dhEmi', namespaces=self.NS)[:10]
                                if ide.findtext('nfe:dhEmi', namespaces=self.NS) else ''),
                'Tipo':        'NFe',
                'Valor':       valor,
                'UF':          CODIGOS_UF.get(ide.findtext('nfe:cUF', namespaces=self.NS) or '', ''),
                'Chave':       inf.attrib.get('Id','')[-44:],
                'Natureza':    ide.findtext('nfe:natOp', namespaces=self.NS) or ''
            }
        except:
            return {}

# --- INTERFACE ------------------------------------------------------------

class AppUI:
    def __init__(self, root):
        self.root     = root
        self.db       = DatabaseManager(DB_PATH)
        self.parser   = XMLProcessor()
        self.all_data = []
        self._build_style()
        self._build_menu()
        self._build_controls()
        self._build_tree()
        self._load_and_show()

    def _build_style(self):
        font = ("Arial", 9)
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", font=font)
        style.configure("Treeview.Heading", background="#37506c", foreground="#fff")
        style.configure("Treeview", rowheight=24, fieldbackground="#fff")

    def _build_menu(self):
        mb = Menu(self.root)
        ac = Menu(mb, tearoff=0)
        ac.add_command(label="Adicionar Certificado", command=self.add_certificate)
        ac.add_command(label="Baixar por Chave",      command=self.prompt_search_key)
        ac.add_separator()
        ac.add_command(label="Ver Certificados",       command=self.show_certificates_popup)
        ac.add_command(label="Executar Busca NF-e",    command=self.run_search_script)
        ac.add_separator()
        ac.add_command(label="Sair",                    command=self.root.destroy)
        mb.add_cascade(label="Ações", menu=ac)
        self.root.config(menu=mb)

    def _build_controls(self):
        frm = ttk.Frame(self.root)
        frm.pack(fill="x", padx=8, pady=6)

        ttk.Label(frm, text="Chave:").pack(side="left")
        self.entry_key = ttk.Entry(frm, width=30)
        self.entry_key.pack(side="left", padx=(0,10))
        self.entry_key.bind("<Return>", lambda e: self._apply_filters())

        ttk.Label(frm, text="Dt Início (DD/MM/AAAA):").pack(side="left")
        self.entry_date_start = ttk.Entry(frm, width=12)
        self.entry_date_start.pack(side="left", padx=(0,10))
        self.entry_date_start.bind("<Return>", lambda e: self._apply_filters())

        ttk.Label(frm, text="Dt Fim (DD/MM/AAAA):").pack(side="left")
        self.entry_date_end = ttk.Entry(frm, width=12)
        self.entry_date_end.pack(side="left", padx=(0,10))
        self.entry_date_end.bind("<Return>", lambda e: self._apply_filters())

        ttk.Button(frm, text="Atualizar Interface", command=self._load_and_show)\
            .pack(side="right")

    def _build_tree(self):
        cont = ttk.Frame(self.root)
        cont.pack(fill="both", expand=True, padx=8, pady=4)

        self.tree = ttk.Treeview(cont, columns=COLUMNS, show="headings")
        for col in COLUMNS:
            self.tree.heading(col, text=col,
                              command=lambda c=col: self.sort_column(c))
            w = 200 if col=="Nome" else 100
            self.tree.column(col, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, side="left")

        sb = ttk.Scrollbar(cont, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscroll=sb.set)
        self.tree.tag_configure('even', background="#fff")
        self.tree.tag_configure('odd',  background="#f4f4f4")

    def _load_and_show(self):
        data = []
        seen = set()
        for xml_file in XML_DIR.rglob("*.xml"):
            txt = xml_file.read_text(encoding='utf-8')
            rec = self.parser.parse_nfe(txt)
            chave = rec.get("Chave")
            if not rec or not chave or chave in seen:
                continue
            seen.add(chave)

            stat = self.db.get_nf_status(chave)
            rec['Status'] = f"{stat[0]} – {stat[1]}" if stat else "—"

            d = rec.get('DtEmi','')
            if d:
                try:
                    dt = datetime.fromisoformat(d)
                    rec['DtEmi'] = dt.strftime("%d/%m/%Y")
                except:
                    pass

            data.append(rec)

        data.sort(
            key=lambda r: datetime.strptime(r['DtEmi'], "%d/%m/%Y")
                          if r['DtEmi'] else datetime.min,
            reverse=True
        )

        self.all_data = data
        self._apply_filters()

    def _apply_filters(self):
        key   = self.entry_key.get().strip()
        start = self.entry_date_start.get().strip()
        end   = self.entry_date_end.get().strip()

        def in_date_range(dstr):
            try:
                d = datetime.strptime(dstr, "%d/%m/%Y")
                s = datetime.strptime(start, "%d/%m/%Y") if start else datetime.min
                e = datetime.strptime(end,   "%d/%m/%Y") if end   else datetime.max
                return s <= d <= e
            except:
                return False

        if key:
            filtered = [r for r in self.all_data if r['Chave']==key]
        elif start or end:
            filtered = [r for r in self.all_data if in_date_range(r['DtEmi'])]
        else:
            filtered = list(self.all_data)

        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for idx, rec in enumerate(filtered):
            tag = 'even' if idx%2==0 else 'odd'
            vals = [rec.get(c,"") for c in COLUMNS]
            self.tree.insert("", "end", values=vals, tags=(tag,))

    def sort_column(self, col):
        data = [(self.tree.set(k,col), k) for k in self.tree.get_children("")]
        rev  = getattr(self, '_rev_'+col, False)
        try:
            if col=="DtEmi":
                data.sort(key=lambda t: datetime.strptime(t[0], "%d/%m/%Y"), reverse=rev)
            else:
                data.sort(key=lambda t: float(
                    t[0].replace("R$","").replace(".","").replace(",",".")
                ), reverse=rev)
        except:
            data.sort(key=lambda t: t[0], reverse=rev)
        for idx, (_, k) in enumerate(data):
            self.tree.move(k, "", idx)
        setattr(self, '_rev_'+col, not rev)

    def add_certificate(self):
        path = filedialog.askopenfilename(filetypes=[("PFX","*.pfx")])
        if not path:
            return
        senha = simpledialog.askstring("Senha","Senha do certificado:", show="*")
        if senha is None:
            return
        try:
            data = Path(path).read_bytes()
            _, cert, _ = pkcs12.load_key_and_certificates(data, senha.encode())
            cn = next(a.value for a in cert.subject if a.oid==NameOID.COMMON_NAME)
            digits = ''.join(filter(str.isdigit, cn))
            informante = digits
        except Exception as e:
            messagebox.showerror("Erro","Falha ao ler certificado:\n"+str(e))
            return

        cuf = simpledialog.askstring("UF","Código UF (ex:35):")
        if not (cuf and cuf in CODIGOS_UF):
            messagebox.showwarning("UF inválida","Digite um código UF válido.")
            return

        if self.db.add_certificado(informante, path, senha, informante, cuf):
            messagebox.showinfo("OK","Certificado salvo.")
        else:
            messagebox.showwarning("Duplicado","Certificado já cadastrado.")

    def prompt_search_key(self):
        key = simpledialog.askstring("Chave","Chave 44 dígitos:")
        if not (key and key.isdigit() and len(key)==44):
            messagebox.showwarning("Inválida","Chave deve ter 44 dígitos.")
            return
        try:
            subprocess.Popen([
                "python", str(SCRIPT_DIR/"nfe_search.py"),
                "--chave", key
            ])
        except Exception as e:
            messagebox.showerror("Erro","Não foi possível baixar por chave:\n"+str(e))

    def show_certificates_popup(self):
        certs = self.db.get_certificates()
        top   = tk.Toplevel(self.root)
        top.title("Certificados Cadastrados")
        top.transient(self.root)
        top.grab_set()
        x = self.root.winfo_rootx() + 50
        y = self.root.winfo_rooty() + 50
        top.geometry(f"+{x}+{y}")
        top.resizable(True, True)

        fr = ttk.Frame(top, padding=10)
        fr.pack(fill="both", expand=True)

        tree2 = ttk.Treeview(fr,
            columns=("Informante","CNPJ/CPF","UF"), show="headings", height=8
        )
        for h,w in [("Informante",100),("CNPJ/CPF",140),("UF",60)]:
            tree2.heading(h, text=h)
            tree2.column(h, width=w, anchor="w")
        tree2.pack(fill="both", expand=True, side="left")

        sb2 = ttk.Scrollbar(fr, orient="vertical", command=tree2.yview)
        sb2.pack(side="right", fill="y")
        tree2.configure(yscroll=sb2.set)

        for cert in certs:
            cnpj,_,_,inf,cuf = cert
            uf = CODIGOS_UF.get(cuf,"")
            tree2.insert("", "end", values=(inf, cnpj, uf))

        def delete_selected():
            sel = tree2.selection()
            if not sel:
                messagebox.showwarning("Seleção","Selecione um certificado.")
                return
            inf = tree2.item(sel[0])['values'][0]
            if messagebox.askyesno("Confirma", f"Excluir {inf}?"):
                self.db.delete_certificate(inf)
                tree2.delete(sel[0])

        ttk.Button(top, text="Excluir Certificado Selecionado",
                   command=delete_selected).pack(pady=(5,10))

    def run_search_script(self):
        try:
            subprocess.Popen(["python", str(SCRIPT_DIR/"nfe_search.py")])
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível executar busca:\n{e}")

def main():
    root = tk.Tk()
    root.title("BOT – NF-e Browser")
    root.geometry("1200x600")
    AppUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
