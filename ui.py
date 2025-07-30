import logging
import threading
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
import os

from db import (
    atualizar_schema_sqlite,
    carregar_certificados,
    get_ult_nsu,
    set_ult_nsu,
    salvar_certificado
)
from sefaz_client import buscar_por_nsu, buscar_por_chave
from parser import (
    COLUMNS,
    ler_dados_detalhados_nfe,
    extrair_ult_nsu_resposta,
    extrair_status,
    extrair_xmls_e_chaves,
    listar_todos_xmls_detalhados_multiplos,
    salvar_xml_organizado
)
from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates

# --- Logging em nível DEBUG ---
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)-8s %(message)s")

# --- Constantes ---
INTERVALO_HORARIO_MS = 3600 * 1000
PASTA_XMLS = 'xmls'
PASTA_XML_EXTRAIDOS = 'xml_extraidos'


def garantir_pastas():
    """Garante que as pastas de XML existam."""
    for pasta in (PASTA_XMLS, PASTA_XML_EXTRAIDOS):
        os.makedirs(pasta, exist_ok=True)
        logging.debug(f"Pasta garantida: {pasta}")


def cadastrar_certificado():
    caminho = filedialog.askopenfilename(
        title="Selecione o PFX", filetypes=[("PFX", "*.pfx")]
    )
    if not caminho:
        return
    senha = simpledialog.askstring("Senha", "Senha do certificado:", show="*")
    if not senha:
        return

    try:
        with open(caminho, 'rb') as f:
            data = f.read()
        _, cert, _ = load_key_and_certificates(data, senha.encode())
        cnpjs = [
            ''.join(filter(str.isdigit, a.value))
            for a in cert.subject
            if any(ch.isdigit() for ch in a.value)
        ]
        cnpj_cpf = next((c for c in cnpjs if len(c) in (11, 14)), None)
        if not cnpj_cpf:
            cnpj_cpf = simpledialog.askstring(
                "CNPJ/CPF", "Digite manualmente (só dígitos):"
            )
        if not cnpj_cpf:
            raise ValueError("CNPJ/CPF não informado")
    except Exception as e:
        logging.error(f"Erro lendo PFX: {e}")
        messagebox.showerror("Erro", f"Falha ao ler PFX:\n{e}")
        return

    informante = simpledialog.askstring(
        "Informante", "CNPJ/CPF do informante (11 ou 14 dígitos):"
    )
    if not informante or len((informante := ''.join(filter(str.isdigit, informante)))) not in (11, 14):
        messagebox.showwarning("Inválido", "Informante incorreto")
        return

    cuf = simpledialog.askstring("UF", "Código da UF (ex: 35):")
    if not cuf or not cuf.isdigit() or len(cuf) != 2:
        messagebox.showwarning("Inválido", "UF incorreto")
        return

    salvar_certificado(cnpj_cpf, caminho, senha, informante, cuf)
    messagebox.showinfo("Sucesso", "Certificado cadastrado")


def resetar_nsu(tree: ttk.Treeview):
    certificados = carregar_certificados()
    informantes = [inf for *_, inf, _ in certificados]
    if not informantes:
        messagebox.showwarning("Sem certificados", "Cadastre um certificado primeiro")
        return

    dlg = tk.Toplevel()
    dlg.title("Resetar NSU")
    dlg.resizable(False, False)
    dlg.grab_set()

    ttk.Label(dlg, text="Selecione o informante para resetar NSU:", style='Dialog.TLabel')\
        .pack(padx=20, pady=(15, 5))

    lb = tk.Listbox(dlg, height=min(6, len(informantes)), font=('Segoe UI', 10))
    for inf in informantes:
        lb.insert('end', inf)
    lb.select_set(0)
    lb.pack(padx=20, pady=(0, 10), fill='x')

    def on_ok():
        escolha = lb.get(lb.curselection()[0])
        set_ult_nsu(escolha, '000000000000000')
        dlg.destroy()
        messagebox.showinfo("NSU Resetado", f"NSU de {escolha} agora é:\n{get_ult_nsu(escolha)}")
        atualizar_e_validar(tree)

    btns = ttk.Frame(dlg, style='Dialog.TFrame')
    btns.pack(pady=(0, 15))
    ttk.Button(btns, text="OK", command=on_ok, style='Accent.TButton').pack(side='left', padx=5)
    ttk.Button(btns, text="Cancelar", command=dlg.destroy, style='TButton').pack(side='left', padx=5)
    dlg.wait_window()


def montar_sidebar_certificados(parent, on_change):
    certificados = carregar_certificados()
    frame = ttk.Frame(parent, style='Sidebar.TFrame')
    ttk.Label(frame, text="Certificados", style='Sidebar.TLabel')\
        .pack(anchor='w', pady=(0, 5), padx=10)

    vars_chk = {'ALL': tk.BooleanVar(value=True)}

    def sel_all():
        estado = vars_chk['ALL'].get()
        for k, v in vars_chk.items():
            if k != 'ALL':
                v.set(estado)
        on_change()

    # Agora usamos o estilo correto para Checkbutton:
    ttk.Checkbutton(
        frame, text="Todas", variable=vars_chk['ALL'],
        command=sel_all, style='Sidebar.TCheckbutton'
    ).pack(anchor='w', padx=10, pady=(0, 5))

    for cnpj, *_ in certificados:
        vars_chk[cnpj] = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame, text=cnpj, variable=vars_chk[cnpj],
            command=on_change, style='Sidebar.TCheckbutton'
        ).pack(anchor='w', padx=20)

    frame.pack(fill='y', padx=(0, 10), pady=10)
    return vars_chk, frame


def _exibir(tree, *pastas):
    try:
        os.listdir(PASTA_XMLS)
        os.listdir(PASTA_XML_EXTRAIDOS)
    except Exception:
        pass

    rows = listar_todos_xmls_detalhados_multiplos(*pastas)
    tree.delete(*tree.get_children())
    for d in rows:
        tree.insert('', 'end', values=[d.get(col, '') for col in COLUMNS])
    tree._full_data = rows


def atualizar_e_validar(tree):
    def tarefa():
        for pfx, pwd, inf, cuf in [(c[1], c[2], c[3], c[4]) for c in carregar_certificados()]:
            old_nsu = get_ult_nsu(inf)
            resp = buscar_por_nsu(pfx, pwd, inf, cuf, old_nsu)
            status, _ = extrair_status(resp)
            if status == '656':
                resp = buscar_por_nsu(pfx, pwd, inf, cuf, '000000000000000')
            docs = extrair_xmls_e_chaves(resp)
            if docs:
                new_nsu = extrair_ult_nsu_resposta(resp)
                if new_nsu and new_nsu != old_nsu:
                    set_ult_nsu(inf, new_nsu)
                for nsu, xml in docs:
                    dados = ler_dados_detalhados_nfe(xml)
                    salvar_xml_organizado(xml, dados, inf)
        tree.after(0, lambda: _exibir(tree, PASTA_XMLS, PASTA_XML_EXTRAIDOS))

    threading.Thread(target=tarefa, daemon=True).start()


def agendar_atualizacao(root, tree):
    def loop():
        atualizar_e_validar(tree)
        root.after(INTERVALO_HORARIO_MS, loop)
    root.after(INTERVALO_HORARIO_MS, loop)


def importar_txt(tree: ttk.Treeview):
    path = filedialog.askopenfilename(
        title="Importar TXT", filetypes=[("Text", "*.txt")]
    )
    if not path:
        return

    with open(path, 'r', encoding='utf-8') as f:
        chaves = [l.strip() for l in f if l.strip()]

    certificados = carregar_certificados()
    if not certificados:
        messagebox.showwarning("Sem certificados", "Cadastre um certificado antes")
        return

    total = 0
    for _, pfx, pwd, inf, cuf in certificados:
        for chave in chaves:
            try:
                xml = buscar_por_chave(pfx, pwd, inf, cuf, chave)
                nome = f"{chave}.xml"
                with open(os.path.join(PASTA_XMLS, nome), 'w', encoding='utf-8') as xf:
                    xf.write(xml)
                total += 1
            except Exception as e:
                logging.error(f"Erro ao baixar {chave}: {e}")

    _exibir(tree, PASTA_XMLS, PASTA_XML_EXTRAIDOS)
    messagebox.showinfo("Importação concluída", f"{total} XML(s) importado(s).")


def main():
    atualizar_schema_sqlite()
    garantir_pastas()

    root = tk.Tk()
    root.title("BOT - Busca NFE")
    root.geometry("1200x700")

    style = ttk.Style(root)
    style.theme_use('clam')

    # Paleta e estilos
    style.configure('Header.TFrame', background='#3A6EA5')
    style.configure('Header.TLabel', background='#3A6EA5', foreground='#FFFFFF',
                    font=('Segoe UI', 16, 'bold'))
    style.configure('Sidebar.TFrame', background='#F0F3F7')
    style.configure('Sidebar.TLabel', background='#F0F3F7', foreground='#333333',
                    font=('Segoe UI', 12, 'bold'))
    style.configure('Sidebar.TCheckbutton', background='#F0F3F7', font=('Segoe UI', 10))
    style.configure('Accent.TButton', font=('Segoe UI', 10), padding=6, relief='flat',
                    background='#3A6EA5', foreground='#FFFFFF')
    style.map('Accent.TButton', background=[('active', '#2E5C8A')])
    style.configure('Treeview', background='#FFFFFF', fieldbackground='#FFFFFF',
                    foreground='#333333', rowheight=26, font=('Segoe UI', 10))
    style.configure('Treeview.Heading', font=('Segoe UI', 11, 'bold'),
                    background='#3A6EA5', foreground='#FFFFFF')
    style.map('Treeview', background=[('selected', '#BBD6F5')],
              foreground=[('selected', '#000000')])
    style.configure('Dialog.TFrame', background='#FFFFFF')
    style.configure('Dialog.TLabel', background='#FFFFFF', font=('Segoe UI', 10))

    # Header
    header = ttk.Frame(root, style='Header.TFrame')
    header.pack(side='top', fill='x')
    ttk.Label(header, text='BOT - Busca NFE', style='Header.TLabel').pack(pady=10)

    # Menu
    menubar = tk.Menu(root)
    cfg = tk.Menu(menubar, tearoff=0)
    cfg.add_command(label="Cadastrar Certificado", command=cadastrar_certificado)
    cfg.add_command(label="Resetar NSU", command=lambda: resetar_nsu(tree))
    cfg.add_separator()
    cfg.add_command(label="Atualizar Agora", command=lambda: atualizar_e_validar(tree))
    menubar.add_cascade(label="Configurações", menu=cfg)
    menubar.add_command(label="Importar TXT", command=lambda: importar_txt(tree))
    root.config(menu=menubar)

    # Layout
    content = ttk.Frame(root, style='Sidebar.TFrame')
    content.pack(fill='both', expand=True, padx=10, pady=10)

    sidebar = ttk.Frame(content, style='Sidebar.TFrame')
    sidebar.pack(side='left', fill='y')
    montar_sidebar_certificados(sidebar, lambda: _exibir(tree, PASTA_XMLS, PASTA_XML_EXTRAIDOS))

    main_area = ttk.Frame(content, style='Sidebar.TFrame')
    main_area.pack(side='left', fill='both', expand=True)

    global tree
    tree = ttk.Treeview(main_area, columns=COLUMNS, show='headings',
                        height=25, style='Treeview')
    for col in COLUMNS:
        tree.heading(col, text=col)
        tree.column(col, width=100, anchor='center')
    tree.pack(side='left', fill='both', expand=True)

    vsb = ttk.Scrollbar(main_area, orient='vertical', command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    vsb.pack(side='left', fill='y')

    _exibir(tree, PASTA_XMLS, PASTA_XML_EXTRAIDOS)
    agendar_atualizacao(root, tree)

    root.mainloop()


if __name__ == "__main__":
    main()
