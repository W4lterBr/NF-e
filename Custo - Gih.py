import sys
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
import sqlite3
import json
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit
import os
import pandas as pd
import datetime
import csv  # Para exportar Relatório de Produtos em CSV
from contextlib import contextmanager
from tkinter.filedialog import asksaveasfilename

# ---------------------------------------
def ajustar_largura_colunas(tree, padding=20, min_width=80):
    import tkinter.font as tkFont
    columns = tree["columns"]
    heading_font = tkFont.Font(name="TkHeadingFont", exists=True)
    for col in columns:
        header_text = tree.heading(col)["text"]
        largura_titulo = heading_font.measure(header_text) + padding
        largura_final = max(largura_titulo, min_width)
        tree.column(col, width=largura_final)

# Detecta o diretório onde está o executável (.exe) ou o script (.py)
if getattr(sys, 'frozen', False):  # .exe
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "estoque.db")

# ---------------------------------------
@contextmanager
def db_conn():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()
with db_conn() as conn:
    cur = conn.cursor()

# ---------------------------------------
# Funções Auxiliares
# ---------------------------------------
def parse_monetary_to_float(value_str: str) -> float:
    """Converte string monetária (ex: 'R$ 1.234,56') em float (1234.56)."""
    print("[DEBUG] parse_monetary_to_float() recebeu:", value_str)
    value_str = value_str.strip().replace("R$", "").strip()
    if "," in value_str:
        value_str = value_str.replace(".", "").replace(",", ".")
    return float(value_str)

def format_usage(qtd_usada: float, unidade_estoque: str) -> str:
    """
    Exibe qtd_usada para exibição, ex.: 'Kilo' => qtd_usada * 1000 = gramas.
    """
    print("[DEBUG] format_usage() qtd_usada=", qtd_usada, "unidade_estoque=", unidade_estoque)
    u = (unidade_estoque or "").lower()
    if u == "kilo":
        return f"{qtd_usada * 1000:.2f} gramas"
    elif u == "litros":
        return f"{qtd_usada * 1000:.2f} ml"
    elif u == "gramas":
        return f"{qtd_usada:.2f} gramas"
    elif u == "unidades":
        return f"{qtd_usada:.2f} unidades"
    return f"{qtd_usada:.2f} ({unidade_estoque})"

def format_stock(qtd_estoque: float, unidade_estoque: str) -> str:
    """Exibe quantidade de estoque com 2 casas decimais e a unidade."""
    print("[DEBUG] format_stock() qtd_estoque=", qtd_estoque, "unidade_estoque=", unidade_estoque)
    return f"{qtd_estoque:.2f} {unidade_estoque}"

def center_popup(parent, popup, min_width=700, min_height=400, pad=60):
    popup.update_idletasks()
    screen_w = popup.winfo_screenwidth()
    screen_h = popup.winfo_screenheight()
    w = max(popup.winfo_reqwidth(), min_width)
    h = max(popup.winfo_reqheight(), min_height)
    if w > screen_w - pad:
        w = screen_w - pad
    if h > screen_h - pad:
        h = screen_h - pad
    x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (w // 2)
    y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (h // 2)
    x = max(x, 0)
    y = max(y, 0)
    popup.geometry(f"{int(w)}x{int(h)}+{int(x)}+{int(y)}")
    popup.minsize(min_width, min_height)
    popup.transient(parent)
    popup.grab_set()

def convert_usage_for_cost(qtd_usada: float, unidade_estoque: str) -> float:
    """
    Ajusta qtd_usada à mesma escala do BD (ex.: se 'gramas' => qtd_usada*1000).
    """
    u = (unidade_estoque or "").lower()
    if u == "kilo":
        return qtd_usada
    elif u == "gramas":
        return qtd_usada * 1000
    elif u == "litros":
        return qtd_usada
    elif u == "unidades":
        return qtd_usada
    return qtd_usada

# =========================================
# ABA: ESTOQUE
# =========================================
class EstoqueFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.editing_item_id = None
        self._masking_data = False  # Controle de máscara para evitar loop

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        cadastro_frame = ttk.LabelFrame(self, text="Cadastrar / Atualizar Item")
        cadastro_frame.grid(row=0, column=0, sticky="ns", padx=5, pady=5)

        # Data com máscara automática
        ttk.Label(cadastro_frame, text="Data (dd/mm/aaaa):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.var_data = tk.StringVar()
        self.entry_data = ttk.Entry(cadastro_frame, width=25, textvariable=self.var_data)
        self.entry_data.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.entry_data.bind("<KeyRelease>", self.mask_data)

        # Nome do item
        ttk.Label(cadastro_frame, text="Nome do Item:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.entry_nome = ttk.Entry(cadastro_frame, width=25)
        self.entry_nome.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Valor de Aquisição
        ttk.Label(cadastro_frame, text="Valor de Aquisição (R$):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.entry_valor = ttk.Entry(cadastro_frame, width=25)
        self.entry_valor.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        # Quantidade
        ttk.Label(cadastro_frame, text="Quantidade:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.entry_quantidade = ttk.Entry(cadastro_frame, width=25)
        self.entry_quantidade.grid(row=3, column=1, padx=5, pady=5, sticky="w")

        # Instruções
        instr_text = (
            "Ao informar a quantidade, faça como exemplo:\n"
            "Digite: 1.000 para KG.\n"
            "Digite: 0.900 para Gramas."
        )
        instructions_label = ttk.Label(cadastro_frame, text=instr_text)
        instructions_label.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky="w")

        # Unidade
        ttk.Label(cadastro_frame, text="Unidade:").grid(row=5, column=0, padx=5, pady=5, sticky="w")
        self.unidades_list = ["Kilo", "Gramas", "Litros", "Unidades"]
        self.cb_unidade = ttk.Combobox(cadastro_frame, values=self.unidades_list, state="readonly")
        self.cb_unidade.current(0)
        self.cb_unidade.grid(row=5, column=1, padx=5, pady=5, sticky="w")

        # Botão Salvar Item
        btn_salvar_item = ttk.Button(cadastro_frame, text="Salvar Item", command=self.salvar_item)
        btn_salvar_item.grid(row=6, column=0, columnspan=2, pady=10)

        # Frame da tabela do estoque
        list_frame = ttk.LabelFrame(self, text="Estoque Atual")
        list_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        self.tree_estoque = ttk.Treeview(
            list_frame,
            columns=("Data", "Nome", "Valor", "Quantidade", "Unidade", "PrecoFrac"),
            show="headings"
        )
        for col in ("Data", "Nome", "Valor", "Quantidade", "Unidade", "PrecoFrac"):
            self.tree_estoque.heading(col, text=col)
        self.tree_estoque.grid(row=0, column=0, sticky="nsew")

        scroll_y = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree_estoque.yview)
        scroll_y.grid(row=0, column=1, sticky="ns")
        self.tree_estoque.configure(yscrollcommand=scroll_y.set)

        # Menu popup direito
        self.menu_popup = tk.Menu(self.tree_estoque, tearoff=0)
        self.menu_popup.add_command(label="Alterar", command=self.popup_alterar_item)
        self.menu_popup.add_command(label="Excluir", command=self.excluir_item)

        # Suporte a Mac: Button-2 ou Button-3
        self.tree_estoque.bind("<Button-3>", self.on_right_click_estoque)
        self.tree_estoque.bind("<Button-2>", self.on_right_click_estoque)

        self.load_estoque()

    def mask_data(self, event=None):
        """Mascara automática para data no formato dd/mm/aaaa."""
        if self._masking_data:
            return
        self._masking_data = True

        value = self.var_data.get()
        digits = ''.join(filter(str.isdigit, value))[:8]
        result = ""
        if len(digits) >= 2:
            result += digits[:2]
        else:
            result += digits
        if len(digits) >= 3:
            result += "/" + digits[2:4]
        elif len(digits) > 2:
            result += "/" + digits[2:]
        if len(digits) >= 5:
            result += "/" + digits[4:8]
        self.var_data.set(result)
        self.entry_data.icursor(len(result))  # Cursor no final
        self._masking_data = False

    def load_estoque(self):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        try:
            cur.execute("ALTER TABLE estoque ADD COLUMN data_cadastro TEXT")
        except:
            pass

        for item in self.tree_estoque.get_children():
            self.tree_estoque.delete(item)

        cur.execute("SELECT id, nome, valor_aquisicao, quantidade, unidade, IFNULL(data_cadastro, '') FROM estoque ORDER BY nome")
        rows = cur.fetchall()
        conn.close()

        for (id_, nome, val, qtd, und, data_cad) in rows:
            preco_frac = val / qtd if qtd != 0 else 0.0
            self.tree_estoque.insert("", tk.END, iid=id_,
                values=(data_cad, nome, f"R$ {val:,.2f}", f"{qtd}", und, f"R$ {preco_frac:,.2f}"))
        ajustar_largura_colunas(self.tree_estoque)

    def on_right_click_estoque(self, event):
        try:
            row_id = self.tree_estoque.identify_row(event.y)
            if row_id:
                self.tree_estoque.selection_set(row_id)
                self.menu_popup.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu_popup.grab_release()

    def popup_alterar_item(self):
        sel = self.tree_estoque.selection()
        if not sel:
            return
        item_id = sel[0]
        values = self.tree_estoque.item(item_id, "values")
        data_item = values[0]
        nome_item = values[1]
        valor_str = values[2].replace("R$", "").replace(".", "").replace(",", ".").strip()
        qtd_str = values[3]
        unidade = values[4]

        self.entry_data.delete(0, tk.END)
        self.entry_data.insert(0, data_item)

        self.entry_nome.delete(0, tk.END)
        self.entry_nome.insert(0, nome_item)

        self.entry_valor.delete(0, tk.END)
        self.entry_valor.insert(0, valor_str)

        self.entry_quantidade.delete(0, tk.END)
        self.entry_quantidade.insert(0, qtd_str)

        if unidade in self.unidades_list:
            self.cb_unidade.set(unidade)
        else:
            self.cb_unidade.current(0)

        self.editing_item_id = item_id

    def excluir_item(self):
        sel = self.tree_estoque.selection()
        if not sel:
            return
        item_id = sel[0]
        resp = messagebox.askyesno("Excluir Item", "Deseja realmente excluir este item do estoque?")
        if not resp:
            return
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("DELETE FROM estoque WHERE id=?", (item_id,))
        conn.commit()
        conn.close()
        self.editing_item_id = None
        self.load_estoque()
        self.app.update_all_frames()
        messagebox.showinfo("Estoque", "Item excluído com sucesso!")

    def salvar_item(self):
        data_cad = self.entry_data.get().strip()
        nome = self.entry_nome.get().strip()
        valor_str = self.entry_valor.get().strip()
        qtd_str = self.entry_quantidade.get().strip()
        unidade = self.cb_unidade.get()

        if not data_cad:
            messagebox.showerror("Erro", "Data de cadastro é obrigatória!")
            return
        if not nome:
            messagebox.showerror("Erro", "Nome do item é obrigatório.")
            return

        # Verifica formato simples da data (você pode aprimorar depois!)
        try:
            if "/" in data_cad:
                import datetime
                datetime.datetime.strptime(data_cad, "%d/%m/%Y")
            else:
                import datetime
                datetime.datetime.strptime(data_cad, "%Y-%m-%d")
        except:
            messagebox.showerror("Erro", "Data em formato inválido! Use dd/mm/aaaa.")
            return

        try:
            valor = parse_monetary_to_float(valor_str)
            qtd = float(qtd_str.replace(",", "."))
            if qtd <= 0 or valor <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Erro", "Valor e quantidade devem ser números maiores que zero.")
            return

        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            if self.editing_item_id:
                cur.execute("""
                    UPDATE estoque
                    SET data_cadastro=?, nome=?, valor_aquisicao=?, quantidade=?, unidade=?
                    WHERE id=?
                """, (data_cad, nome, valor, qtd, unidade, self.editing_item_id))
            else:
                cur.execute("""
                    INSERT INTO estoque (data_cadastro, nome, valor_aquisicao, quantidade, unidade)
                    VALUES (?, ?, ?, ?, ?)
                """, (data_cad, nome, valor, qtd, unidade))
            conn.commit()
            conn.close()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar item: {e}")
            return

        self.editing_item_id = None
        self.entry_data.delete(0, tk.END)
        self.entry_nome.delete(0, tk.END)
        self.entry_valor.delete(0, tk.END)
        self.entry_quantidade.delete(0, tk.END)
        self.cb_unidade.current(0)
        self.load_estoque()
        self.app.update_all_frames()
        messagebox.showinfo("Estoque", "Item salvo com sucesso!")

# =========================================
# ABA: EMBALAGENS
# =========================================
class EmbalagemFrame(ttk.Frame):
    """
    Mini-estoque de embalagens. Exibe Nome, Valor, ValorUnit, Quantidade, Unidade.
    Permite alterar e excluir embalagens com clique direito.
    """
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.editing_emb_id = None

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        cadastro_frame = ttk.LabelFrame(self, text="Cadastrar / Atualizar Embalagem")
        cadastro_frame.grid(row=0, column=0, sticky="ns", padx=5, pady=5)

        ttk.Label(cadastro_frame, text="Nome da Embalagem:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.entry_emb_nome = ttk.Entry(cadastro_frame, width=25)
        self.entry_emb_nome.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(cadastro_frame, text="Valor (R$):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.entry_emb_valor = ttk.Entry(cadastro_frame, width=25)
        self.entry_emb_valor.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(cadastro_frame, text="Quantidade:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.entry_emb_qtd = ttk.Entry(cadastro_frame, width=25)
        self.entry_emb_qtd.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(cadastro_frame, text="Unidade:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.emb_unidades = ["Unidades", "Pacotes", "Caixas"]
        self.cb_emb_unidade = ttk.Combobox(cadastro_frame, values=self.emb_unidades, state="readonly")
        self.cb_emb_unidade.current(0)
        self.cb_emb_unidade.grid(row=3, column=1, padx=5, pady=5, sticky="w")

        btn_salvar_emb = ttk.Button(cadastro_frame, text="Salvar Embalagem", command=self.salvar_embalagem)
        btn_salvar_emb.grid(row=4, column=0, columnspan=2, pady=10)

        list_frame = ttk.LabelFrame(self, text="Lista de Embalagens")
        list_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        self.tree_embalagens = ttk.Treeview(
            list_frame,
            columns=("Nome", "Valor", "ValUnit", "Quantidade", "Unidade"),
            show="headings"
        )
        for col in ("Nome", "Valor", "ValUnit", "Quantidade", "Unidade"):
            self.tree_embalagens.heading(col, text=col)
        self.tree_embalagens.grid(row=0, column=0, sticky="nsew")

        scroll_y = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree_embalagens.yview)
        scroll_y.grid(row=0, column=1, sticky="ns")
        self.tree_embalagens.configure(yscrollcommand=scroll_y.set)

        # Menu popup de contexto para Alterar e Excluir
        self.menu_popup = tk.Menu(self.tree_embalagens, tearoff=0)
        self.menu_popup.add_command(label="Alterar Embalagem", command=self.popup_alterar_embalagem)
        self.menu_popup.add_command(label="Excluir Embalagem", command=self.excluir_embalagem)
        self.tree_embalagens.bind("<Button-3>", self.on_right_click_embalagem)
        self.tree_embalagens.bind("<Button-2>", self.on_right_click_embalagem)

        self.load_embalagens()

    def load_embalagens(self):
        for item in self.tree_embalagens.get_children():
            self.tree_embalagens.delete(item)

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        # Tenta criar colunas se não existir
        try:
            cur.execute("ALTER TABLE embalagens ADD COLUMN quantidade REAL")
        except:
            pass
        try:
            cur.execute("ALTER TABLE embalagens ADD COLUMN unidade TEXT")
        except:
            pass
        cur.execute("SELECT id, nome, valor, quantidade, unidade FROM embalagens ORDER BY nome")
        rows = cur.fetchall()
        conn.close()

        for (eid, nome, val, qtd, und) in rows:
            qtd_val = qtd if qtd else 0.0
            valor_unit = (val / qtd_val) if (qtd_val != 0) else 0.0
            self.tree_embalagens.insert(
                "", tk.END, iid=eid,
                values=(
                    nome,
                    f"R$ {val:,.2f}",
                    f"R$ {valor_unit:,.2f}",
                    f"{qtd_val}",
                    und if und else ""
                )
            )
        ajustar_largura_colunas(self.tree_embalagens)

    def on_right_click_embalagem(self, event):
        item_id = self.tree_embalagens.identify_row(event.y)
        if item_id:
            self.tree_embalagens.selection_set(item_id)
            self.menu_popup.post(event.x_root, event.y_root)

    def popup_alterar_embalagem(self):
        sel = self.tree_embalagens.selection()
        if not sel:
            return
        emb_id = sel[0]
        values = self.tree_embalagens.item(emb_id, "values")
        nome_emb = values[0]
        valor_str = values[1].replace("R$", "").replace(".", "").replace(",", ".").strip()
        qtd_str = values[3]
        unidade = values[4]

        self.entry_emb_nome.delete(0, tk.END)
        self.entry_emb_nome.insert(0, nome_emb)
        self.entry_emb_valor.delete(0, tk.END)
        self.entry_emb_valor.insert(0, valor_str)
        self.entry_emb_qtd.delete(0, tk.END)
        self.entry_emb_qtd.insert(0, qtd_str)

        if unidade in self.emb_unidades:
            self.cb_emb_unidade.set(unidade)
        else:
            self.cb_emb_unidade.current(0)

        self.editing_emb_id = emb_id

    def excluir_embalagem(self):
        sel = self.tree_embalagens.selection()
        if not sel:
            return
        emb_id = sel[0]
        resp = messagebox.askyesno("Excluir Embalagem", "Deseja realmente excluir esta embalagem?")
        if not resp:
            return
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("DELETE FROM embalagens WHERE id=?", (emb_id,))
        conn.commit()
        conn.close()
        self.editing_emb_id = None
        self.load_embalagens()
        self.app.update_all_frames()
        messagebox.showinfo("Embalagens", "Embalagem excluída com sucesso!")

    def salvar_embalagem(self):
        nome_novo = self.entry_emb_nome.get().strip()
        valor_str = self.entry_emb_valor.get().strip()
        qtd_str = self.entry_emb_qtd.get().strip()
        unidade = self.cb_emb_unidade.get()

        if not nome_novo:
            messagebox.showerror("Erro", "Nome da embalagem é obrigatório.")
            return
        try:
            valor = parse_monetary_to_float(valor_str)
            qtd = float(qtd_str.replace(",", "."))
            if qtd <= 0 or valor <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Erro", "Valor e quantidade devem ser números maiores que zero.")
            return

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        if self.editing_emb_id:
            # Descobrir o nome antigo:
            cur.execute("SELECT nome FROM embalagens WHERE id=?", (self.editing_emb_id,))
            row = cur.fetchone()
            nome_antigo = row[0] if row else nome_novo

            cur.execute("""
                UPDATE embalagens
                SET nome=?, valor=?, quantidade=?, unidade=?
                WHERE id=?
            """, (nome_novo, valor, qtd, unidade, self.editing_emb_id))

            # --- Atualizar todos os produtos que usam o nome antigo ---
            if nome_novo != nome_antigo:
                cur.execute("SELECT id, embalagens_usadas FROM vitrine")
                produtos = cur.fetchall()
                for pid, emb_json in produtos:
                    if not emb_json:
                        continue
                    try:
                        emb_dict = json.loads(emb_json)
                    except:
                        emb_dict = {}
                    if nome_antigo in emb_dict:
                        emb_dict[nome_novo] = emb_dict.pop(nome_antigo)
                        cur2 = conn.cursor()
                        cur2.execute(
                            "UPDATE vitrine SET embalagens_usadas=? WHERE id=?",
                            (json.dumps(emb_dict), pid)
                        )
        else:
            cur.execute("""
                INSERT INTO embalagens (nome, valor, quantidade, unidade)
                VALUES (?, ?, ?, ?)
            """, (nome_novo, valor, qtd, unidade))

        conn.commit()
        conn.close()

        self.editing_emb_id = None
        self.entry_emb_nome.delete(0, tk.END)
        self.entry_emb_valor.delete(0, tk.END)
        self.entry_emb_qtd.delete(0, tk.END)
        self.cb_emb_unidade.current(0)

        self.load_embalagens()
        self.app.update_all_frames()

# =========================================
# ABA: VITRINE
# =========================================
class VitrineFrame(ttk.Frame):
    """
    Aba Vitrine: cadastra produtos, usando itens/embalagens.
    Botão Preço Sugerido = soma custos + admin_porcentagem.
    """
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.editing_product_id = None
        self.itens_usados_dict = {}
        self.embalagens_usadas_dict = {}

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.cadastro_frame = ttk.LabelFrame(self, text="Cadastrar/Alterar Produto")
        self.cadastro_frame.grid(row=0, column=0, sticky="ns", padx=5, pady=5)

        ttk.Label(self.cadastro_frame, text="Nome do Produto:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.entry_nome_produto = ttk.Entry(self.cadastro_frame, width=25)
        self.entry_nome_produto.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(self.cadastro_frame, text="Preço de Venda (R$):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.entry_preco_venda = ttk.Entry(self.cadastro_frame, width=25)
        self.entry_preco_venda.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        btn_preco_sug = ttk.Button(self.cadastro_frame, text="Preço Sugerido", command=self.calcular_preco_sugerido)
        btn_preco_sug.grid(row=2, column=0, columnspan=2, pady=(0,10))

        ttk.Label(self.cadastro_frame, text="Itens usados (p/ 1 un.):").grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky="w")
        self.entry_itens_usados = ttk.Entry(self.cadastro_frame, width=40)
        self.entry_itens_usados.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky="w")

        btn_add_itens = ttk.Button(self.cadastro_frame, text="Adicionar Itens do Estoque", command=self.adicionar_itens_estoque)
        btn_add_itens.grid(row=5, column=0, columnspan=2, pady=5)

        ttk.Label(self.cadastro_frame, text="Embalagens usadas (p/ 1 un.):").grid(row=6, column=0, columnspan=2, padx=5, pady=5, sticky="w")
        self.entry_embalagens_usadas = ttk.Entry(self.cadastro_frame, width=40)
        self.entry_embalagens_usadas.grid(row=7, column=0, columnspan=2, padx=5, pady=5, sticky="w")

        btn_add_emb = ttk.Button(self.cadastro_frame, text="Adicionar Embalagens", command=self.adicionar_embalagens_uso)
        btn_add_emb.grid(row=8, column=0, columnspan=2, pady=5)

        btn_salvar_prod = ttk.Button(self.cadastro_frame, text="Salvar Produto", command=self.salvar_produto)
        btn_salvar_prod.grid(row=9, column=0, columnspan=2, pady=10)

        self.produtos_frame = ttk.LabelFrame(self, text="Lista de Produtos (Clique direito p/ opções)")
        self.produtos_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.produtos_frame.grid_rowconfigure(0, weight=1)
        self.produtos_frame.grid_columnconfigure(0, weight=1)

        self.tree_produtos = ttk.Treeview(
            self.produtos_frame,
            columns=("Nome", "PrecoVenda"),
            show="headings"
        )
        self.tree_produtos.heading("Nome", text="Nome")
        self.tree_produtos.heading("PrecoVenda", text="Preço Venda (R$)")
        self.tree_produtos.column("Nome", width=120)
        self.tree_produtos.column("PrecoVenda", width=120)
        self.tree_produtos.grid(row=0, column=0, sticky="nsew")

        scroll_p = ttk.Scrollbar(self.produtos_frame, orient=tk.VERTICAL, command=self.tree_produtos.yview)
        scroll_p.grid(row=0, column=1, sticky="ns")
        self.tree_produtos.configure(yscrollcommand=scroll_p.set)

        # MENU DE CONTEXTO (BOTÃO DIREITO)
        self.menu_popup = tk.Menu(self.tree_produtos, tearoff=0)
        self.menu_popup.add_command(label="Alterar Produto", command=self.alterar_produto)
        self.menu_popup.add_command(label="Excluir Produto", command=self.excluir_produto)
        self.tree_produtos.bind("<Button-3>", self.on_right_click_produto)
        self.tree_produtos.bind("<Button-2>", self.on_right_click_produto) # MacOS as fallback

        self.load_produtos()

    def load_produtos(self):
        for item in self.tree_produtos.get_children():
            self.tree_produtos.delete(item)
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id, nome, preco_venda FROM vitrine ORDER BY nome")
        rows = cur.fetchall()
        conn.close()
        for (pid, nome, preco) in rows:
            self.tree_produtos.insert("", tk.END, iid=pid, values=(nome, f"R$ {preco:,.2f}"))
        ajustar_largura_colunas(self.tree_produtos)

    def on_right_click_produto(self, event):
        # MacOS usa <Button-2> para menu, Windows/Linux <Button-3>
        try:
            item_id = self.tree_produtos.identify_row(event.y)
            if item_id:
                self.tree_produtos.selection_set(item_id)
                self.menu_popup.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu_popup.grab_release()

    def calcular_preco_sugerido(self):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        custo_itens = 0.0
        for nome_item, qtd_usada in self.itens_usados_dict.items():
            cur.execute("SELECT valor_aquisicao, quantidade, unidade FROM estoque WHERE nome=?", (nome_item,))
            row_e = cur.fetchone()
            if row_e:
                val_aquis, qtd_estoque, und_estoque = row_e
                if qtd_estoque != 0:
                    usage_db_scale = qtd_usada
                    custo_itens += (val_aquis / qtd_estoque) * usage_db_scale
        custo_emb = 0.0
        for emb_name, emb_usage in self.embalagens_usadas_dict.items():
            cur.execute("SELECT valor, quantidade, unidade FROM embalagens WHERE nome=?", (emb_name,))
            row_eb = cur.fetchone()
            if row_eb:
                val_eb, qtd_eb, und_emb = row_eb
                if qtd_eb != 0:
                    usage_db_scale = emb_usage
                    custo_emb += (val_eb / qtd_eb) * usage_db_scale
        conn.close()
        total_custo = custo_itens + custo_emb
        preco_sug = total_custo * (1 + self.app.admin_porcentagem / 100.0)
        self.entry_preco_venda.delete(0, tk.END)
        self.entry_preco_venda.insert(0, f"{preco_sug:,.2f}")

    def adicionar_itens_estoque(self):
        top = tk.Toplevel(self)
        top.title("Selecionar Itens do Estoque")
        top.geometry("600x400")
        center_popup(self.app, top)
        cols = ("Nome", "Quantidade", "Unidade", "Preço Unitário")
        tree = ttk.Treeview(top, columns=cols, show="headings")
        for col in cols:
            tree.heading(col, text=col, anchor="w")
            tree.column(col, anchor="w", stretch=True, width=100)
        tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scrollbar = ttk.Scrollbar(top, orient=tk.VERTICAL, command=tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=scrollbar.set)
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT nome, quantidade, unidade, valor_aquisicao FROM estoque ORDER BY nome")
        for nome, qtd, und, val in cur.fetchall():
            preco_unit = val / qtd if qtd else 0.0
            tree.insert("", tk.END, values=(nome, f"{qtd:.2f}", und, f"R$ {preco_unit:,.2f}"))
        conn.close()
        def on_double_click(event):
            sel = tree.selection()
            if not sel:
                return
            nome_item, *_ = tree.item(sel[0], "values")
            q_win = tk.Toplevel(top)
            q_win.title(f"Uso de '{nome_item}'")
            q_win.geometry("300x120")
            center_popup(self.app, q_win)
            ttk.Label(q_win, text=f"Quantas unidades de '{nome_item}' serão usadas?").pack(pady=5)
            e_qtd = ttk.Entry(q_win)
            e_qtd.pack(fill=tk.X, padx=20)
            def confirmar():
                try:
                    qfloat = float(e_qtd.get().replace(",", "."))
                except ValueError:
                    messagebox.showerror("Erro", "Quantidade inválida.")
                    return
                self.itens_usados_dict[nome_item] = qfloat
                self.update_itens_usados_entry()
                q_win.destroy()
            ttk.Button(q_win, text="OK", command=confirmar).pack(pady=10)
        tree.bind("<Double-1>", on_double_click)
    def update_itens_usados_entry(self):
        self.entry_itens_usados.delete(0, tk.END)
        parts = [f"{k}:{v}" for (k, v) in self.itens_usados_dict.items()]
        self.entry_itens_usados.insert(0, ",".join(parts))
    def adicionar_embalagens_uso(self):
        top = tk.Toplevel(self)
        top.title("Selecionar Embalagens")
        top.geometry("600x400")
        center_popup(self.app, top)
        cols = ("Nome", "Quantidade", "Unidade", "Preço Unitário")
        tree = ttk.Treeview(top, columns=cols, show="headings")
        for col in cols:
            tree.heading(col, text=col, anchor="w")
            tree.column(col, anchor="w", stretch=True, width=100)
        tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scrollbar = ttk.Scrollbar(top, orient=tk.VERTICAL, command=tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=scrollbar.set)
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT nome, quantidade, unidade, valor FROM embalagens ORDER BY nome")
        for nome, qtd, und, val in cur.fetchall():
            preco_unit = (val / qtd) if qtd else 0.0
            tree.insert("", tk.END, values=(nome, f"{qtd:.2f}", und, f"R$ {preco_unit:,.2f}"))
        conn.close()
        def on_double_click(event):
            sel = tree.selection()
            if not sel:
                return
            emb_name = tree.item(sel[0], "values")[0]
            q_win = tk.Toplevel(top)
            q_win.title(f"Uso de '{emb_name}'")
            q_win.geometry("300x120")
            center_popup(self.app, q_win)
            ttk.Label(q_win, text=f"Quantas unidades de '{emb_name}' serão usadas?").pack(pady=5)
            e_qtd = ttk.Entry(q_win)
            e_qtd.pack(fill=tk.X, padx=20)
            def confirmar():
                try:
                    qfloat = float(e_qtd.get().replace(",", "."))
                except ValueError:
                    messagebox.showerror("Erro", "Quantidade inválida.")
                    return
                self.embalagens_usadas_dict[emb_name] = qfloat
                self.update_embalagens_usadas_entry()
                q_win.destroy()
            ttk.Button(q_win, text="OK", command=confirmar).pack(pady=10)
        tree.bind("<Double-1>", on_double_click)
    def update_embalagens_usadas_entry(self):
        self.entry_embalagens_usadas.delete(0, tk.END)
        parts = [f"{k}:{v}" for (k, v) in self.embalagens_usadas_dict.items()]
        self.entry_embalagens_usadas.insert(0, ",".join(parts))
    def salvar_produto(self):
        nome_produto = self.entry_nome_produto.get().strip()
        preco_venda_str = self.entry_preco_venda.get().strip()
        if not nome_produto:
            return
        try:
            preco_venda = parse_monetary_to_float(preco_venda_str) if preco_venda_str else 0.0
        except ValueError:
            return
        itens_json = json.dumps(self.itens_usados_dict)
        emb_json = json.dumps(self.embalagens_usadas_dict)
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        if self.editing_product_id:
            cur.execute("""
                UPDATE vitrine
                SET nome=?, preco_venda=?, itens_usados=?, embalagens_usadas=?
                WHERE id=?
            """, (nome_produto, preco_venda, itens_json, emb_json, self.editing_product_id))
        else:
            cur.execute("""
                INSERT INTO vitrine (nome, preco_venda, itens_usados, embalagens_usadas)
                VALUES (?, ?, ?, ?)
            """, (nome_produto, preco_venda, itens_json, emb_json))
        conn.commit()
        conn.close()
        self.editing_product_id = None
        self.entry_nome_produto.delete(0, tk.END)
        self.entry_preco_venda.delete(0, tk.END)
        self.entry_itens_usados.delete(0, tk.END)
        self.entry_embalagens_usadas.delete(0, tk.END)
        self.itens_usados_dict.clear()
        self.embalagens_usadas_dict.clear()
        self.load_produtos()
        self.app.update_all_frames()
    def alterar_produto(self):
        sel = self.tree_produtos.selection()
        if not sel:
            return
        pid = sel[0]
        self.editing_product_id = pid
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT nome, preco_venda, itens_usados, embalagens_usadas FROM vitrine WHERE id=?", (pid,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return
        nome_produto, preco_venda, itens_json, emb_json = row
        self.entry_nome_produto.delete(0, tk.END)
        self.entry_nome_produto.insert(0, nome_produto)
        self.entry_preco_venda.delete(0, tk.END)
        self.entry_preco_venda.insert(0, f"{preco_venda:,.2f}")
        self.itens_usados_dict.clear()
        if itens_json:
            try:
                self.itens_usados_dict.update(json.loads(itens_json))
            except:
                pass
        self.update_itens_usados_entry()
        self.embalagens_usadas_dict.clear()
        if emb_json:
            try:
                self.embalagens_usadas_dict.update(json.loads(emb_json))
            except:
                pass
        self.update_embalagens_usadas_entry()
    def excluir_produto(self):
        sel = self.tree_produtos.selection()
        if not sel:
            return
        pid = sel[0]
        resp = messagebox.askyesno("Excluir Produto", "Deseja realmente excluir este produto?")
        if not resp:
            return
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("DELETE FROM vitrine WHERE id=?", (pid,))
        conn.commit()
        conn.close()
        self.editing_product_id = None
        self.entry_nome_produto.delete(0, tk.END)
        self.entry_preco_venda.delete(0, tk.END)
        self.entry_itens_usados.delete(0, tk.END)
        self.entry_embalagens_usadas.delete(0, tk.END)
        self.itens_usados_dict.clear()
        self.embalagens_usadas_dict.clear()
        self.load_produtos()
        self.app.update_all_frames()

# =========================================
# ABA: PRODUTOS
# =========================================
class ProdutosFrame(ttk.Frame):
    """
    Exibe lista de produtos, com cada item e estoque atual.
    """
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        lbl_info = ttk.Label(self, text=(
            "Lista de todos os produtos e seus itens.\n"
            "Mostra 'Estoque Atual' para cada item."
        ))
        lbl_info.grid(row=0, column=0, sticky="w", padx=5, pady=5)

        columns = ("Produto", "Item", "Uso", "EstoqueAtual")
        self.tree_produtos_detalhes = ttk.Treeview(self, columns=columns, show="headings")
        self.tree_produtos_detalhes.heading("Produto", text="Produto")
        self.tree_produtos_detalhes.heading("Item", text="Item")
        self.tree_produtos_detalhes.heading("Uso", text="Uso no Produto")
        self.tree_produtos_detalhes.heading("EstoqueAtual", text="Estoque Atual")

        self.tree_produtos_detalhes.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        scroll_y = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree_produtos_detalhes.yview)
        scroll_y.grid(row=1, column=1, sticky="ns")
        self.tree_produtos_detalhes.configure(yscrollcommand=scroll_y.set)

        self.load_produtos()

    def load_produtos(self):
        # Limpa a tabela
        for item in self.tree_produtos_detalhes.get_children():
            self.tree_produtos_detalhes.delete(item)

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id, nome, itens_usados FROM vitrine ORDER BY nome")
        rows = cur.fetchall()
        conn.close()

        for (prod_id, prod_nome, itens_json) in rows:
            try:
                itens_dict = json.loads(itens_json) if itens_json else {}
            except Exception:
                itens_dict = {}

            for nome_item, qtd_usada in itens_dict.items():
                # Só mostra o item se ele ainda existir no estoque!
                with sqlite3.connect(DB_PATH) as conn2:
                    cur2 = conn2.cursor()
                    cur2.execute("SELECT quantidade, unidade FROM estoque WHERE nome=?", (nome_item,))
                    row_e = cur2.fetchone()
                if row_e:
                    qtd_estoque, unidade_estoque = row_e
                    uso_str = format_usage(qtd_usada, unidade_estoque)
                    estoque_str = format_stock(qtd_estoque, unidade_estoque)
                    self.tree_produtos_detalhes.insert(
                        "", tk.END,
                        values=(prod_nome, nome_item, uso_str, estoque_str)
                    )
        ajustar_largura_colunas(self.tree_produtos_detalhes)

    def tkraise(self, aboveThis=None):
        super().tkraise(aboveThis)
        self.load_produtos()

# =========================================
# ABA: PRODUÇÃO
# =========================================
class ProducaoFrame(ttk.Frame):
    """
    Aba Produção: subtrai do estoque e registra em 'producao'.
    Clique direito => Editar ou Excluir (ambos atualizam o Lucro/Prejuizo na hora).
    """
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.tree_producao = ttk.Treeview(
            self,
            columns=("Nome", "Quantidade", "Data", "Valor"),
            show="headings"
        )
        self.tree_producao.heading("Nome", text="Nome")
        self.tree_producao.heading("Quantidade", text="Quantidade")
        self.tree_producao.heading("Data", text="Produzido em")
        self.tree_producao.heading("Valor", text="Valor")
        self.tree_producao.grid(row=0, column=0, sticky="nsew")

        scroll_y = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree_producao.yview)
        scroll_y.grid(row=0, column=1, sticky="ns")
        self.tree_producao.configure(yscrollcommand=scroll_y.set)

        self.menu_popup = tk.Menu(self.tree_producao, tearoff=0)
        self.menu_popup.add_command(label="Editar", command=self.editar_producao)
        self.menu_popup.add_command(label="Excluir", command=self.excluir_producao)
        self.tree_producao.bind("<Button-3>", self.on_right_click_producao)

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=1, column=0, sticky="ew", pady=5)
        btn_add = ttk.Button(btn_frame, text="Adicionar produto", command=self.adicionar_producao)
        btn_add.pack()

        self.load_producao()

    def on_right_click_producao(self, event):
        item_id = self.tree_producao.identify_row(event.y)
        if item_id:
            self.tree_producao.selection_set(item_id)
            self.menu_popup.post(event.x_root, event.y_root)

    def load_producao(self):
        for item in self.tree_producao.get_children():
            self.tree_producao.delete(item)

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            SELECT producao.id, vitrine.nome, producao.qty, producao.data, producao.total
            FROM producao
            JOIN vitrine ON producao.product_id = vitrine.id
            ORDER BY producao.id
        """)
        rows = cur.fetchall()
        conn.close()

        for (p_id, nome, qty, data_str, total) in rows:
            val_str = f"R$ {total:,.2f}"
            self.tree_producao.insert("", tk.END, iid=p_id,
                values=(nome, qty, data_str, val_str))
        ajustar_largura_colunas(self.tree_producao)

    def adicionar_producao(self):
        popup = tk.Toplevel(self)
        popup.title("Adicionar produto na Produção")
        center_popup(self.app, popup)

        tree = ttk.Treeview(popup, columns=("Nome", "PrecoVenda"), show="headings")
        tree.heading("Nome", text="Nome")
        tree.heading("PrecoVenda", text="Preço Venda (R$)")
        tree.column("Nome", width=150)
        tree.column("PrecoVenda", width=120)
        tree.pack(fill=tk.BOTH, expand=True)

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id, nome, preco_venda FROM vitrine ORDER BY nome")
        rows = cur.fetchall()
        conn.close()
        for (pid, nome, preco) in rows:
            tree.insert("", tk.END, iid=pid, values=(nome, f"R$ {preco:,.2f}"))

        qty_frame = ttk.Frame(popup)
        qty_frame.pack(pady=5)
        ttk.Label(qty_frame, text="Quantidade a produzir:").grid(row=0, column=0, padx=5)
        entry_qty = ttk.Entry(qty_frame, width=10)
        entry_qty.grid(row=0, column=1, padx=5)

        def on_salvar():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Produção", "Selecione um produto da lista.")
                return
            pid = sel[0]

            qtd_str = entry_qty.get().strip()
            if not qtd_str:
                messagebox.showwarning("Produção", "Digite a quantidade a produzir.")
                return
            try:
                qtd = float(qtd_str.replace(",", "."))
            except ValueError:
                messagebox.showwarning("Produção", "Quantidade inválida.")
                return
            if qtd <= 0:
                messagebox.showwarning("Produção", "Quantidade deve ser maior que zero.")
                return

            conn2 = sqlite3.connect(DB_PATH)
            c2 = conn2.cursor()
            c2.execute("SELECT preco_venda, itens_usados, embalagens_usadas FROM vitrine WHERE id=?", (pid,))
            row_v = c2.fetchone()
            if not row_v:
                conn2.close()
                messagebox.showerror("Produção", "Produto não encontrado na vitrine.")
                return
            preco_venda, itens_json, emb_json = row_v
            valor_total = preco_venda * qtd

            try:
                itens_dict = json.loads(itens_json) if itens_json else {}
            except:
                itens_dict = {}
            try:
                emb_dict = json.loads(emb_json) if emb_json else {}
            except:
                emb_dict = {}

            # Subtrai do estoque
            for nome_item, qtd_para1 in itens_dict.items():
                c3 = conn2.cursor()
                c3.execute("SELECT id, quantidade, unidade FROM estoque WHERE nome=?", (nome_item,))
                row_e = c3.fetchone()
                if row_e:
                    estoque_id, estoque_qtd, estoque_und = row_e
                    usage_db_scale = convert_usage_for_cost(qtd_para1, estoque_und)
                    usado_total = usage_db_scale * qtd
                    if estoque_qtd < usado_total:
                        conn2.close()
                        messagebox.showerror("Produção", f"Estoque insuficiente de {nome_item}!")
                        return
                    c3.execute("UPDATE estoque SET quantidade=? WHERE id=?", (estoque_qtd - usado_total, estoque_id))

            # Subtrai das embalagens
            for emb_name, emb_usage_para1 in emb_dict.items():
                c4 = conn2.cursor()
                c4.execute("SELECT id, quantidade, unidade FROM embalagens WHERE nome=?", (emb_name,))
                row_eb = c4.fetchone()
                if row_eb:
                    emb_id, emb_qtd, emb_und = row_eb
                    usage_db_scale = convert_usage_for_cost(emb_usage_para1, emb_und)
                    embalado = usage_db_scale * qtd
                    if emb_qtd < embalado:
                        conn2.close()
                        messagebox.showerror("Produção", f"Quantidade insuficiente de {emb_name}!")
                        return
                    c4.execute("UPDATE embalagens SET quantidade=? WHERE id=?", (emb_qtd - embalado, emb_id))

            data_str = datetime.datetime.now().strftime("%d/%m/%Y")
            c2.execute("""
                INSERT INTO producao (product_id, qty, total, data)
                VALUES (?, ?, ?, ?)
            """, (pid, qtd, valor_total, data_str))
            conn2.commit()
            conn2.close()

            messagebox.showinfo("Produção", "Produto produzido com sucesso!")
            popup.destroy()
            self.load_producao()
            # Atualiza Lucro/Prejuizo na hora
            self.app.update_lucro_label()
            # Se preferir, poderia chamar: self.app.update_all_frames()

        btn_salvar = ttk.Button(popup, text="Salvar Produção", command=on_salvar)
        btn_salvar.pack(pady=5)

    def editar_producao(self):
        sel = self.tree_producao.selection()
        if not sel:
            return
        prod_id = sel[0]

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT product_id, qty, total, data FROM producao WHERE id=?", (prod_id,))
        row_prod = cur.fetchone()
        if not row_prod:
            conn.close()
            messagebox.showerror("Produção", "Registro não encontrado na tabela 'producao'.")
            return
        (vid_product_id, vid_qty, vid_total, vid_data) = row_prod

        # Carrega itens
        c2 = conn.cursor()
        c2.execute("SELECT itens_usados, embalagens_usadas, preco_venda FROM vitrine WHERE id=?", (vid_product_id,))
        row_v = c2.fetchone()
        if not row_v:
            conn.close()
            messagebox.showerror("Produção", "Produto não encontrado na vitrine (para reverter).")
            return
        itens_json, emb_json, preco_venda = row_v
        try:
            itens_dict = json.loads(itens_json) if itens_json else {}
        except:
            itens_dict = {}
        try:
            emb_dict = json.loads(emb_json) if emb_json else {}
        except:
            emb_dict = {}

        # Reverte do estoque
        for nome_item, qtd_para1 in itens_dict.items():
            c3 = conn.cursor()
            c3.execute("SELECT id, quantidade, unidade FROM estoque WHERE nome=?", (nome_item,))
            row_e = c3.fetchone()
            if row_e:
                estoque_id, estoque_qtd, estoque_und = row_e
                usage_db_scale = convert_usage_for_cost(qtd_para1, estoque_und)
                usado_total = usage_db_scale * vid_qty
                novo_estoque = estoque_qtd + usado_total
                c3.execute("UPDATE estoque SET quantidade=? WHERE id=?", (novo_estoque, estoque_id))

        # Reverte embalagens
        for emb_name, emb_usage_para1 in emb_dict.items():
            c4 = conn.cursor()
            c4.execute("SELECT id, quantidade, unidade FROM embalagens WHERE nome=?", (emb_name,))
            row_eb = c4.fetchone()
            if row_eb:
                emb_id, emb_qtd, emb_und = row_eb
                usage_db_scale = convert_usage_for_cost(emb_usage_para1, emb_und)
                embalado = usage_db_scale * vid_qty
                novo_emb = emb_qtd + embalado
                c4.execute("UPDATE embalagens SET quantidade=? WHERE id=?", (novo_emb, emb_id))

        edit_popup = tk.Toplevel(self)
        edit_popup.title("Editar Produção")
        center_popup(self.app, edit_popup)
        ttk.Label(edit_popup, text=f"Editar Produção (ID={prod_id})").pack(pady=5)
        ttk.Label(edit_popup, text="Nova quantidade:").pack(pady=5)
        entry_nova_qtd = ttk.Entry(edit_popup, width=10)
        entry_nova_qtd.pack()

        def confirmar_edicao():
            qtd_str = entry_nova_qtd.get().strip()
            try:
                nova_qtd = float(qtd_str.replace(",", "."))
            except ValueError:
                messagebox.showerror("Erro", "Quantidade inválida.")
                return
            if nova_qtd <= 0:
                messagebox.showerror("Erro", "Quantidade deve ser > 0.")
                return

            novo_total = preco_venda * nova_qtd

            # Re-aplica subtração
            for nome_item, qtd_para1 in itens_dict.items():
                c5 = conn.cursor()
                c5.execute("SELECT id, quantidade, unidade FROM estoque WHERE nome=?", (nome_item,))
                row_e2 = c5.fetchone()
                if row_e2:
                    estoque_id2, estoque_qtd2, estoque_und2 = row_e2
                    usage_db_scale2 = convert_usage_for_cost(qtd_para1, estoque_und2)
                    usado_total2 = usage_db_scale2 * nova_qtd
                    if estoque_qtd2 < usado_total2:
                        messagebox.showerror("Produção", f"Estoque insuficiente de {nome_item}!")
                        edit_popup.destroy()
                        conn.close()
                        return
                    c5.execute("UPDATE estoque SET quantidade=? WHERE id=?",
                               (estoque_qtd2 - usado_total2, estoque_id2))

            for emb_name, emb_usage_para1 in emb_dict.items():
                c6 = conn.cursor()
                c6.execute("SELECT id, quantidade, unidade FROM embalagens WHERE nome=?", (emb_name,))
                row_eb2 = c6.fetchone()
                if row_eb2:
                    emb_id2, emb_qtd2, emb_und2 = row_eb2
                    usage_db_scale2 = convert_usage_for_cost(emb_usage_para1, emb_und2)
                    embalado2 = usage_db_scale2 * nova_qtd
                    if emb_qtd2 < embalado2:
                        messagebox.showerror("Produção", f"Quantidade insuficiente de {emb_name}!")
                        edit_popup.destroy()
                        conn.close()
                        return
                    c6.execute("UPDATE embalagens SET quantidade=? WHERE id=?",
                               (emb_qtd2 - embalado2, emb_id2))

            # Atualiza producao
            c2.execute("""
                UPDATE producao
                SET qty=?, total=?
                WHERE id=?
            """, (nova_qtd, novo_total, prod_id))
            conn.commit()
            conn.close()

            messagebox.showinfo("Produção", "Produção editada com sucesso!")
            edit_popup.destroy()
            self.load_producao()
            self.app.update_lucro_label()  # <--- Atualiza Lucro aqui

        ttk.Button(edit_popup, text="OK", command=confirmar_edicao).pack(pady=5)

    def excluir_producao(self):
        sel = self.tree_producao.selection()
        if not sel:
            return
        prod_id = sel[0]

        resp = messagebox.askyesno("Excluir Produção", "Deseja realmente excluir este registro de produção?")
        if not resp:
            return

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT product_id, qty FROM producao WHERE id=?", (prod_id,))
        row_p = cur.fetchone()
        if not row_p:
            conn.close()
            messagebox.showerror("Produção", "Registro não encontrado na tabela 'producao'.")
            return
        (vid_product_id, vid_qty) = row_p

        c2 = conn.cursor()
        c2.execute("SELECT itens_usados, embalagens_usadas FROM vitrine WHERE id=?", (vid_product_id,))
        row_v = c2.fetchone()
        if not row_v:
            conn.close()
            messagebox.showerror("Produção", "Produto não encontrado na vitrine (para reverter).")
            return
        itens_json, emb_json = row_v
        try:
            itens_dict = json.loads(itens_json) if itens_json else {}
        except:
            itens_dict = {}
        try:
            emb_dict = json.loads(emb_json) if emb_json else {}
        except:
            emb_dict = {}

        # Reverte estoque
        for nome_item, qtd_para1 in itens_dict.items():
            c3 = conn.cursor()
            c3.execute("SELECT id, quantidade, unidade FROM estoque WHERE nome=?", (nome_item,))
            row_e = c3.fetchone()
            if row_e:
                estoque_id, estoque_qtd, estoque_und = row_e
                usage_db_scale = convert_usage_for_cost(qtd_para1, estoque_und)
                usado_total = usage_db_scale * vid_qty
                novo_estoque = estoque_qtd + usado_total
                c3.execute("UPDATE estoque SET quantidade=? WHERE id=?", (novo_estoque, estoque_id))

        # Reverte embalagens
        for emb_name, emb_usage_para1 in emb_dict.items():
            c4 = conn.cursor()
            c4.execute("SELECT id, quantidade, unidade FROM embalagens WHERE nome=?", (emb_name,))
            row_eb = c4.fetchone()
            if row_eb:
                emb_id, emb_qtd, emb_und = row_eb
                usage_db_scale = convert_usage_for_cost(emb_usage_para1, emb_und)
                embalado = usage_db_scale * vid_qty
                novo_emb = emb_qtd + embalado
                c4.execute("UPDATE embalagens SET quantidade=? WHERE id=?", (novo_emb, emb_id))

        cur.execute("DELETE FROM producao WHERE id=?", (prod_id,))
        conn.commit()
        conn.close()

        messagebox.showinfo("Produção", "Registro de produção excluído com sucesso!")
        self.load_producao()
        self.app.update_lucro_label()  # <--- Atualiza Lucro

# =========================================
# ABA: VENDAS
# =========================================
class VendasFrame(ttk.Frame):
    """
    Aba Vendas: não subtrai do estoque; só registra a venda em 'vendas'.
    Exibe últimas 10 vendas no lado direito, e atualiza o Lucro/Prejuizo na hora.
    """
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        # Garante expansão máxima
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Lista de produtos (esquerda)
        self.list_frame = ttk.LabelFrame(self, text="Produtos (Vitrine)")
        self.list_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.list_frame.grid_rowconfigure(0, weight=1)
        self.list_frame.grid_columnconfigure(0, weight=1)

        self.tree_produtos_vitrine = ttk.Treeview(
            self.list_frame,
            columns=("Nome", "PrecoVenda"),
            show="headings"
        )
        self.tree_produtos_vitrine.heading("Nome", text="Nome")
        self.tree_produtos_vitrine.heading("PrecoVenda", text="Preço Venda (R$)")
        self.tree_produtos_vitrine.column("Nome", width=180)
        self.tree_produtos_vitrine.column("PrecoVenda", width=140)
        self.tree_produtos_vitrine.grid(row=0, column=0, sticky="nsew")

        scroll_v = ttk.Scrollbar(self.list_frame, orient=tk.VERTICAL, command=self.tree_produtos_vitrine.yview)
        scroll_v.grid(row=0, column=1, sticky="ns")
        self.tree_produtos_vitrine.configure(yscrollcommand=scroll_v.set)

        # Frame da direita: Formulário e últimas vendas
        self.right_frame = ttk.Frame(self)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.right_frame.grid_rowconfigure(1, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)

        self.action_frame = ttk.LabelFrame(self.right_frame, text="Vender Produto (sem alterar estoque)")
        self.action_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        ttk.Label(self.action_frame, text="Quantidade Vendida:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.entry_qty = ttk.Entry(self.action_frame, width=10)
        self.entry_qty.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(self.action_frame, text="Valor da Venda (R$):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.entry_total = ttk.Entry(self.action_frame, width=10)
        self.entry_total.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        btn_vender = ttk.Button(self.action_frame, text="Vender", command=self.vender_produto)
        btn_vender.grid(row=2, column=0, columnspan=2, pady=(10,2))

        btn_desfazer = ttk.Button(self.action_frame, text="Desfazer Venda", command=self.desfazer_venda)
        btn_desfazer.grid(row=3, column=0, columnspan=2, pady=(2,5))

        # Lista das últimas 10 vendas
        self.ultimas_vendas_frame = ttk.LabelFrame(self.right_frame, text="Últimas 10 Vendas")
        self.ultimas_vendas_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.ultimas_vendas_frame.grid_rowconfigure(0, weight=1)
        self.ultimas_vendas_frame.grid_columnconfigure(0, weight=1)

        self.tree_ultimas_vendas = ttk.Treeview(
            self.ultimas_vendas_frame,
            columns=("Nome", "Qtd", "Total", "Data"),
            show="headings"
        )
        self.tree_ultimas_vendas.heading("Nome", text="Nome")
        self.tree_ultimas_vendas.heading("Qtd", text="Qtd")
        self.tree_ultimas_vendas.heading("Total", text="Total (R$)")
        self.tree_ultimas_vendas.heading("Data", text="Data")
        self.tree_ultimas_vendas.grid(row=0, column=0, sticky="nsew")

        scroll_uv = ttk.Scrollbar(self.ultimas_vendas_frame, orient=tk.VERTICAL, command=self.tree_ultimas_vendas.yview)
        scroll_uv.grid(row=0, column=1, sticky="ns")
        self.tree_ultimas_vendas.configure(yscrollcommand=scroll_uv.set)

        self.load_produtos_vitrine()
        self.load_ultimas_vendas()

    def load_produtos_vitrine(self):
        for item in self.tree_produtos_vitrine.get_children():
            self.tree_produtos_vitrine.delete(item)

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id, nome, preco_venda FROM vitrine ORDER BY nome")
        rows = cur.fetchall()
        conn.close()

        for (pid, nome, preco) in rows:
            self.tree_produtos_vitrine.insert("", tk.END, iid=pid,
                values=(nome, f"R$ {preco:,.2f}"))
        ajustar_largura_colunas(self.tree_produtos_vitrine)

    def load_ultimas_vendas(self):
        for item in self.tree_ultimas_vendas.get_children():
            self.tree_ultimas_vendas.delete(item)

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            SELECT v.id, vt.nome, v.qty, v.total, v.data
            FROM vendas v
            JOIN vitrine vt ON v.product_id = vt.id
            ORDER BY v.id DESC
            LIMIT 10
        """)
        rows = cur.fetchall()
        conn.close()

        for (vid, nome, qty, total, data_str) in rows:
            self.tree_ultimas_vendas.insert("", tk.END,
                values=(nome, qty, f"R$ {total:,.2f}", data_str))
        ajustar_largura_colunas(self.tree_ultimas_vendas)

    def vender_produto(self):
        sel = self.tree_produtos_vitrine.selection()
        if not sel:
            messagebox.showwarning("Vendas", "Nenhum produto selecionado.")
            return
        pid = sel[0]

        qty_str = self.entry_qty.get().strip()
        total_str = self.entry_total.get().strip()
        if not qty_str or not total_str:
            messagebox.showwarning("Vendas", "Digite quantidade e valor da venda.")
            return

        try:
            qty = float(qty_str.replace(",", "."))
            total = parse_monetary_to_float(total_str)
        except ValueError:
            messagebox.showwarning("Vendas", "Valores inválidos.")
            return

        if qty <= 0 or total <= 0:
            messagebox.showwarning("Vendas", "Quantidade e valor devem ser > 0.")
            return

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        data_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("""
            INSERT INTO vendas (product_id, qty, total, data)
            VALUES (?, ?, ?, ?)
        """, (pid, qty, total, data_str))
        conn.commit()
        conn.close()

        self.entry_qty.delete(0, tk.END)
        self.entry_total.delete(0, tk.END)

        messagebox.showinfo("Vendas", "Venda registrada (estoque não alterado).")
        self.load_ultimas_vendas()
        self.app.update_lucro_label()  # <--- Atualiza Lucro

    def desfazer_venda(self):
        try:
            with sqlite3.connect(DB_PATH, timeout=10) as conn:
                cur = conn.cursor()
                cur.execute("SELECT id FROM vendas ORDER BY id DESC LIMIT 1")
                row_last = cur.fetchone()
                if not row_last:
                    messagebox.showwarning("Vendas", "Não há vendas para desfazer.")
                    return

                vid = row_last[0]
                cur.execute("DELETE FROM vendas WHERE id=?", (vid,))
                conn.commit()
        except sqlite3.OperationalError as e:
            messagebox.showerror("Erro", f"Erro de acesso ao banco de dados:\n{e}")
            return

        messagebox.showinfo("Vendas", "Venda desfeita com sucesso! (sem afetar estoque).")
        self.load_ultimas_vendas()
        self.app.update_lucro_label()  # <--- Atualiza Lucro
# =========================================
# TELA DE LOGIN
# =========================================
def center_on_screen(window, width=400, height=250, pad=0):
    window.update_idletasks()
    screen_w = window.winfo_screenwidth()
    screen_h = window.winfo_screenheight()
    w = width
    h = height
    x = max((screen_w // 2) - (w // 2), pad)
    y = max((screen_h // 2) - (h // 2), pad)
    window.geometry(f"{w}x{h}+{x}+{y}")
    window.minsize(w, h)
    window.lift()
    window.focus_force()


class LoginScreen(tk.Toplevel):
    def __init__(self, master, on_login_success):
        super().__init__(master)
        self.on_login_success = on_login_success
        self.title("Login - Futura Loja da Gih ❤")

        # Detecta o SO
        is_mac = sys.platform == "darwin"
        is_win = sys.platform.startswith("win")
        bg_dark = "#28282a"
        fg_light = "#fff"

        if is_mac:
            # Estilo original (usa ttk e clam theme)
            style = ttk.Style()
            style.theme_use("clam")
            style.configure("Dark.TFrame", background=bg_dark)
            self.resizable(False, False)
            frame = ttk.Frame(self, style="Dark.TFrame")
            frame.pack(padx=30, pady=30, fill="both", expand=True)
            title = ttk.Label(frame, text="Bem-vindo à Loja da Gih ❤", font=("Segoe UI", 16, "bold"), background=bg_dark, foreground=fg_light)
            title.pack(pady=(0,20), fill="x")
            ttk.Label(frame, text="Nome:", background=bg_dark, foreground=fg_light).pack(anchor="w")
            self.entry_nome = ttk.Entry(frame, font=("Segoe UI", 12))
            self.entry_nome.pack(fill="x", pady=5)
            self.entry_nome.focus()
            ttk.Label(frame, text="Senha:", background=bg_dark, foreground=fg_light).pack(anchor="w")
            self.entry_senha = ttk.Entry(frame, font=("Segoe UI", 12), show="●")
            self.entry_senha.pack(fill="x", pady=5)
            self.msg = ttk.Label(frame, text="", foreground="red", background=bg_dark)
            self.msg.pack(pady=5)
            btns = ttk.Frame(frame, style="Dark.TFrame")
            btns.pack(fill="x", pady=15)
            self.btn_entrar = ttk.Button(btns, text="Entrar", command=self.try_login)
            self.btn_entrar.pack(side="left", expand=True, fill="x", padx=5)
            self.btn_criar = ttk.Button(btns, text="Criar Usuário", command=self.open_create_user)
            self.btn_criar.pack(side="left", expand=True, fill="x", padx=5)
        else: # WINDOWS (ou Linux)
            # Estilo todo em TK para cor funcionar!
            self.configure(bg=bg_dark)
            self.resizable(False, False)
            frame = tk.Frame(self, bg=bg_dark)
            frame.pack(padx=30, pady=30, fill="both", expand=True)
            title = tk.Label(frame, text="Bem-vindo à Loja da Gih ❤", font=("Segoe UI", 16, "bold"), bg=bg_dark, fg=fg_light)
            title.pack(pady=(0,20), fill="x")
            tk.Label(frame, text="Nome:", bg=bg_dark, fg=fg_light, font=("Segoe UI", 11)).pack(anchor="w")
            self.entry_nome = tk.Entry(frame, font=("Segoe UI", 12), bg="#444", fg="#fff", insertbackground="#fff")
            self.entry_nome.pack(fill="x", pady=5)
            self.entry_nome.focus()
            tk.Label(frame, text="Senha:", bg=bg_dark, fg=fg_light, font=("Segoe UI", 11)).pack(anchor="w")
            self.entry_senha = tk.Entry(frame, font=("Segoe UI", 12), show="●", bg="#444", fg="#fff", insertbackground="#fff")
            self.entry_senha.pack(fill="x", pady=5)
            self.msg = tk.Label(frame, text="", fg="red", bg=bg_dark, font=("Segoe UI", 10))
            self.msg.pack(pady=5)
            btns = tk.Frame(frame, bg=bg_dark)
            btns.pack(fill="x", pady=15)
            self.btn_entrar = tk.Button(btns, text="Entrar", command=self.try_login, bg="#444", fg=fg_light, relief=tk.FLAT)
            self.btn_entrar.pack(side="left", expand=True, fill="x", padx=5)
            self.btn_criar = tk.Button(btns, text="Criar Usuário", command=self.open_create_user, bg="#444", fg=fg_light, relief=tk.FLAT)
            self.btn_criar.pack(side="left", expand=True, fill="x", padx=5)
        # Enter para logar
        self.entry_senha.bind("<Return>", lambda e: self.try_login())
        self.after(10, lambda: center_on_screen(self, 400, 340, 40))
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def try_login(self):
        nome = self.entry_nome.get().strip()
        senha = self.entry_senha.get().strip()
        if not nome or not senha:
            self.msg.config(text="Preencha todos os campos!", foreground="red")
            return

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT senha FROM usuarios WHERE nome=?", (nome,))
        row = cur.fetchone()
        conn.close()
        if row and row[0] == senha:
            self.msg.config(text="Acesso liberado!", foreground="green")
            self.after(200, self.success)
        else:
            self.msg.config(text="Nome ou senha inválidos!", foreground="red")

    def success(self):
        self.grab_release()
        self.destroy()
        self.on_login_success()

    def on_close(self):
        self.master.destroy()

    def open_create_user(self):
        CreateUserScreen(self)

class CreateUserScreen(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Criar Usuário")
        self.configure(bg="#f6f4ff")
        self.resizable(False, False)

        frame = ttk.Frame(self)
        frame.pack(padx=20, pady=20, fill="both", expand=True)

        ttk.Label(frame, text="Nome:").pack(anchor="w")
        self.entry_nome = ttk.Entry(frame, font=("Segoe UI", 12))
        self.entry_nome.pack(fill="x", pady=5)
        self.entry_nome.focus()

        ttk.Label(frame, text="Senha:").pack(anchor="w")
        self.entry_senha = ttk.Entry(frame, font=("Segoe UI", 12), show="●")
        self.entry_senha.pack(fill="x", pady=5)

        ttk.Label(frame, text="Confirmar Senha:").pack(anchor="w")
        self.entry_senha2 = ttk.Entry(frame, font=("Segoe UI", 12), show="●")
        self.entry_senha2.pack(fill="x", pady=5)

        self.msg = ttk.Label(frame, text="", foreground="red")
        self.msg.pack(pady=5)

        btn_criar = ttk.Button(frame, text="Criar", command=self.create_user)
        btn_criar.pack(fill="x", pady=15)

        # Centraliza o popup em relação ao master!
        self.after(10, lambda: center_on_screen(self, 360, 320, 40))
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_user(self):
        nome = self.entry_nome.get().strip()
        senha = self.entry_senha.get().strip()
        senha2 = self.entry_senha2.get().strip()

        if not nome or not senha or not senha2:
            self.msg.config(text="Preencha todos os campos.", foreground="red")
            return
        if senha != senha2:
            self.msg.config(text="As senhas não coincidem.", foreground="red")
            return

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO usuarios (nome, senha) VALUES (?, ?)", (nome, senha))
            conn.commit()
            self.msg.config(text="Usuário criado com sucesso!", foreground="green")
            self.after(1200, self.destroy)
        except sqlite3.IntegrityError:
            self.msg.config(text="Usuário já existe.", foreground="red")
        finally:
            conn.close()

    def on_close(self):
        self.grab_release()
        self.destroy()

# =========================================
# APP (Principal)
# =========================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        print("[DEBUG] Iniciando App.__init__")

        # Garante que a janela principal ocupe toda a tela
        self.title("Futura Loja da Gih ❤")
        self.geometry("1920x1080")
        self.minsize(900, 500)

        # >>> ESSENCIAL para expansão total da área:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        self.lucro_acumulado = 0.0
        self.admin_porcentagem = 0.0
        self.bg_color = "#FFFFFF"

        self.create_database()
        self.load_admin_config()

        self.main_frame = ttk.Frame(self)
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)  # Padding pode aumentar se quiser!

        self.status_label = ttk.Label(self.main_frame, text="Lucro R$ 0,00", anchor='w')
        self.status_label.grid(row=1, column=0, sticky="ew")

        # CRIANDO ABAS
        self.estoque_frame = EstoqueFrame(self.notebook, self)
        self.embalagem_frame = EmbalagemFrame(self.notebook, self)
        self.vitrine_frame = VitrineFrame(self.notebook, self)
        self.produtos_frame = ProdutosFrame(self.notebook, self)
        self.producao_frame = ProducaoFrame(self.notebook, self)
        self.vendas_frame = VendasFrame(self.notebook, self)

        self.notebook.add(self.estoque_frame, text="Estoque")
        self.notebook.add(self.embalagem_frame, text="Embalagens")
        self.notebook.add(self.vitrine_frame, text="Vitrine")
        self.notebook.add(self.produtos_frame, text="Produtos")
        self.notebook.add(self.producao_frame, text="Produção")
        self.notebook.add(self.vendas_frame, text="Vendas")

        # MENU SUPERIOR
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        config_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Configurações", menu=config_menu)
        config_menu.add_command(label="Cores", command=self.escolher_cor)
        config_menu.add_command(label="Lucro", command=self.abrir_lucro)
        config_menu.add_command(label="Relatorio de Venda", command=self.mostrar_relatorio_venda)
        config_menu.add_command(label="Relatorio de Produtos", command=self.mostrar_relatorio_produtos)
        config_menu.add_command(label="Extrato", command=self.mostrar_extrato)
        config_menu.add_command(label="Relatórios", command=self.abrir_menu_relatorios)

        self.update_lucro_label()
        self.apply_bg_color()
#------------------------------------------------------
    def abrir_menu_relatorios(self):
        popup = tk.Toplevel(self)
        popup.title("Relatórios")
        center_popup(self, popup, min_width=300, min_height=200)
        ttk.Label(popup, text="Selecione o tipo de relatório para exportar:", font=("Segoe UI", 11)).pack(pady=10)
        ttk.Button(popup, text="Relatório de Vendas (Excel)", command=self.exportar_vendas_excel).pack(fill="x", padx=20, pady=5)
        ttk.Button(popup, text="Relatório de Vendas (PDF)", command=self.exportar_vendas_pdf).pack(fill="x", padx=20, pady=5)
        ttk.Button(popup, text="Relatório de Vendas (CSV)", command=self.exportar_csv_vendas).pack(fill="x", padx=20, pady=5)
        ttk.Button(popup, text="Relatório de Produtos (Excel)", command=self.exportar_produtos_excel).pack(fill="x", padx=20, pady=5)
        ttk.Button(popup, text="Relatório de Produtos (PDF)", command=self.exportar_produtos_pdf).pack(fill="x", padx=20, pady=5)
        ttk.Button(popup, text="Extrato (Excel)", command=self.exportar_extrato_excel).pack(fill="x", padx=20, pady=5)
        ttk.Button(popup, text="Extrato (PDF)", command=self.exportar_extrato_pdf).pack(fill="x", padx=20, pady=5)
        ttk.Button(popup, text="Fechar", command=popup.destroy).pack(pady=10)

# ------------------------------------------------ Exportar        
    def exportar_vendas_excel(self):
        import pandas as pd
        import datetime
        from tkinter.filedialog import asksaveasfilename
        import os

        filename = asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Planilha Excel", "*.xlsx")],
            initialfile=f"RelatorioVendas_{datetime.datetime.now():%Y%m%d_%H%M%S}.xlsx",
            title="Salvar relatório de vendas como..."
        )
        if not filename:
            return

        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("""
            SELECT v.data AS Data, vt.nome AS Produto, v.qty AS Quantidade, v.total AS Valor
            FROM vendas v
            JOIN vitrine vt ON v.product_id = vt.id
            ORDER BY v.data
        """, conn)
        conn.close()
        df.to_excel(filename, index=False)
        messagebox.showinfo("Exportar Excel", f"Relatório de vendas salvo como:\n{os.path.basename(filename)}")

    def exportar_vendas_pdf(self):
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        import datetime
        from tkinter.filedialog import asksaveasfilename
        import os

        filename = asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"RelatorioVendas_{datetime.datetime.now():%Y%m%d_%H%M%S}.pdf",
            title="Salvar relatório de vendas como PDF"
        )
        if not filename:
            return

        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("""
            SELECT v.data, vt.nome, v.qty, v.total
            FROM vendas v
            JOIN vitrine vt ON v.product_id = vt.id
            ORDER BY v.data
        """).fetchall()
        conn.close()

        c = canvas.Canvas(filename, pagesize=letter)
        c.drawString(30, 750, "Relatório de Vendas")
        y = 730
        for data, nome, qty, total in rows:
            c.drawString(30, y, f"Data: {data} | Produto: {nome} | Qtd: {qty} | Valor: R$ {total:.2f}")
            y -= 20
            if y < 40:
                c.showPage()
                y = 750
        c.save()
        messagebox.showinfo("Exportar PDF", f"Relatório de vendas salvo como:\n{os.path.basename(filename)}")

#-------------------------------------------------------------------------------------------------
    def exportar_vendas_excel(self):
        import pandas as pd
        import datetime
        from tkinter.filedialog import asksaveasfilename
        import os

        filename = asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Planilha Excel", "*.xlsx")],
            initialfile=f"RelatorioVendas_{datetime.datetime.now():%Y%m%d_%H%M%S}.xlsx",
            title="Salvar relatório de vendas como..."
        )
        if not filename:
            return

        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("""
            SELECT v.data AS Data, vt.nome AS Produto, v.qty AS Quantidade, v.total AS Valor
            FROM vendas v
            JOIN vitrine vt ON v.product_id = vt.id
            ORDER BY v.data
        """, conn)
        conn.close()
        df.to_excel(filename, index=False)
        messagebox.showinfo("Exportar Excel", f"Relatório de vendas salvo como:\n{os.path.basename(filename)}")

    def exportar_vendas_pdf(self):
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        import datetime
        from tkinter.filedialog import asksaveasfilename
        import os

        filename = asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"RelatorioVendas_{datetime.datetime.now():%Y%m%d_%H%M%S}.pdf",
            title="Salvar relatório de vendas como PDF"
        )
        if not filename:
            return

        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("""
            SELECT v.data, vt.nome, v.qty, v.total
            FROM vendas v
            JOIN vitrine vt ON v.product_id = vt.id
            ORDER BY v.data
        """).fetchall()
        conn.close()

        c = canvas.Canvas(filename, pagesize=letter)
        c.drawString(30, 750, "Relatório de Vendas")
        y = 730
        for data, nome, qty, total in rows:
            c.drawString(30, y, f"Data: {data} | Produto: {nome} | Qtd: {qty} | Valor: R$ {total:.2f}")
            y -= 20
            if y < 40:
                c.showPage()
                y = 750
        c.save()
        messagebox.showinfo("Exportar PDF", f"Relatório de vendas salvo como:\n{os.path.basename(filename)}")

    def exportar_produtos_excel(self):
        import pandas as pd
        import datetime
        from tkinter.filedialog import asksaveasfilename
        import os

        filename = asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Planilha Excel", "*.xlsx")],
            initialfile=f"RelatorioProdutos_{datetime.datetime.now():%Y%m%d_%H%M%S}.xlsx",
            title="Salvar relatório de produtos como..."
        )
        if not filename:
            return

        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("""
            SELECT nome AS Produto, preco_venda AS PrecoVenda, itens_usados AS Itens, embalagens_usadas AS Embalagens
            FROM vitrine
            ORDER BY nome
        """, conn)
        conn.close()
        df.to_excel(filename, index=False)
        messagebox.showinfo("Exportar Excel", f"Relatório de produtos salvo como:\n{os.path.basename(filename)}")

    def exportar_csv_produtos(self):
        import csv
        import datetime
        from tkinter.filedialog import asksaveasfilename
        import os

        filename = asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=f"RelatorioProdutos_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            title="Salvar relatório de produtos como CSV"
        )
        if not filename:
            return

        try:
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(["Produto", "Preço de Venda (R$)", "Custo Total (R$)", "Lucro Líquido (R$)"])
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute("SELECT nome, preco_venda, itens_usados, embalagens_usadas FROM vitrine ORDER BY nome")
                produtos_rows = cur.fetchall()
                for (prod_nome, preco_venda, itens_json, emb_json) in produtos_rows:
                    # Calcula custo total do produto
                    custo_total = 0.0
                    try:
                        itens_dict = json.loads(itens_json) if itens_json else {}
                    except:
                        itens_dict = {}
                    for nome_item, qtd_usada in itens_dict.items():
                        c2 = conn.cursor()
                        c2.execute("SELECT valor_aquisicao, quantidade, unidade FROM estoque WHERE nome=?", (nome_item,))
                        row_e = c2.fetchone()
                        if row_e:
                            val_aquis, qtd_estoque, und_estoque = row_e
                            usage_db_scale = qtd_usada
                            if qtd_estoque != 0:
                                custo_item = (val_aquis / qtd_estoque) * usage_db_scale
                            else:
                                custo_item = 0.0
                            custo_total += custo_item

                    try:
                        emb_dict = json.loads(emb_json) if emb_json else {}
                    except:
                        emb_dict = {}
                    for emb_name, emb_usage in emb_dict.items():
                        c3 = conn.cursor()
                        c3.execute("SELECT valor, quantidade, unidade FROM embalagens WHERE nome=?", (emb_name,))
                        row_eb = c3.fetchone()
                        if row_eb:
                            val_eb, qtd_eb, und_emb = row_eb
                            usage_db_scale = emb_usage
                            if qtd_eb != 0:
                                custo_emb = (val_eb / qtd_eb) * usage_db_scale
                            else:
                                custo_emb = 0.0
                            custo_total += custo_emb

                    lucro_liquido = preco_venda - custo_total
                    writer.writerow([prod_nome, f"{preco_venda:.2f}", f"{custo_total:.2f}", f"{lucro_liquido:.2f}"])
                conn.close()
            messagebox.showinfo("Exportar CSV", f"Relatório de produtos salvo em\n{os.path.basename(filename)}!")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exportar CSV: {e}")

    def exportar_produtos_pdf(self):
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        import datetime
        from tkinter.filedialog import asksaveasfilename
        import os

        filename = asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"RelatorioProdutos_{datetime.datetime.now():%Y%m%d_%H%M%S}.pdf",
            title="Salvar relatório de produtos como PDF"
        )
        if not filename:
            return

        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("""
            SELECT nome, preco_venda
            FROM vitrine
            ORDER BY nome
        """).fetchall()
        conn.close()
        c = canvas.Canvas(filename, pagesize=letter)
        c.drawString(30, 750, "Relatório de Produtos")
        y = 730
        for nome, preco in rows:
            c.drawString(30, y, f"Produto: {nome} | Preço de Venda: R$ {preco:.2f}")
            y -= 20
            if y < 40:
                c.showPage()
                y = 750
        c.save()
        messagebox.showinfo("Exportar PDF", f"Relatório de produtos salvo como:\n{os.path.basename(filename)}")

    def exportar_extrato_excel(self):
        import pandas as pd
        import datetime
        from tkinter.filedialog import asksaveasfilename
        import os

        filename = asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Planilha Excel", "*.xlsx")],
            initialfile=f"Extrato_{datetime.datetime.now():%Y%m%d_%H%M%S}.xlsx",
            title="Salvar extrato como..."
        )
        if not filename:
            return

        movimentos = []
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        # Compras (Estoque)
        cur.execute("SELECT nome, valor_aquisicao, quantidade, unidade, data_cadastro FROM estoque")
        for nome, valor, qtd, unidade, data in cur.fetchall():
            descricao = f"Compra Estoque ({nome})"
            movimentos.append({
                "data": data or "",
                "descricao": descricao,
                "debito": valor,
                "credito": 0.0
            })
        # Vendas
        cur.execute("""
            SELECT v.data, vt.nome, v.total
            FROM vendas v
            JOIN vitrine vt ON v.product_id = vt.id
            ORDER BY v.data
        """)
        for data, nome, total in cur.fetchall():
            descricao = f"Venda ({nome})"
            movimentos.append({
                "data": data or "",
                "descricao": descricao,
                "debito": 0.0,
                "credito": total
            })
        conn.close()
        df = pd.DataFrame(movimentos)
        df.to_excel(filename, index=False)
        messagebox.showinfo("Exportar Excel", f"Extrato salvo como:\n{os.path.basename(filename)}")

    def exportar_extrato_pdf(self):
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        import datetime
        from tkinter.filedialog import asksaveasfilename
        import os

        filename = asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"Extrato_{datetime.datetime.now():%Y%m%d_%H%M%S}.pdf",
            title="Salvar extrato como PDF"
        )
        if not filename:
            return

        movimentos = []
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        # Compras (Estoque)
        cur.execute("SELECT nome, valor_aquisicao, quantidade, unidade, data_cadastro FROM estoque")
        for nome, valor, qtd, unidade, data in cur.fetchall():
            descricao = f"Compra Estoque ({nome})"
            movimentos.append({
                "data": data or "",
                "descricao": descricao,
                "debito": valor,
                "credito": 0.0
            })
        # Vendas
        cur.execute("""
            SELECT v.data, vt.nome, v.total
            FROM vendas v
            JOIN vitrine vt ON v.product_id = vt.id
            ORDER BY v.data
        """)
        for data, nome, total in cur.fetchall():
            descricao = f"Venda ({nome})"
            movimentos.append({
                "data": data or "",
                "descricao": descricao,
                "debito": 0.0,
                "credito": total
            })
        conn.close()
        c = canvas.Canvas(filename, pagesize=letter)
        c.drawString(30, 750, "Extrato Bancário")
        y = 730
        for m in movimentos:
            c.drawString(30, y, f"Data: {m['data']} | {m['descricao']} | Débito: R$ {m['debito']:.2f} | Crédito: R$ {m['credito']:.2f}")
            y -= 20
            if y < 40:
                c.showPage()
                y = 750
        c.save()
        messagebox.showinfo("Exportar PDF", f"Extrato salvo como:\n{os.path.basename(filename)}")

    # ------- Agora TODAS as funções auxiliares estão como métodos abaixo -------

    def create_database(self):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # Tabela de estoque de ingredientes
        cur.execute("""
            CREATE TABLE IF NOT EXISTS estoque (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                valor_aquisicao REAL NOT NULL,
                quantidade REAL NOT NULL,
                unidade TEXT NOT NULL,
                data_cadastro TEXT
            );
        """)

        # Tabela de embalagens
        cur.execute("""
            CREATE TABLE IF NOT EXISTS embalagens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                valor REAL NOT NULL,
                quantidade REAL,
                unidade TEXT
            );
        """)

        # Tabela de vitrine (produtos finais)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vitrine (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                preco_venda REAL NOT NULL,
                itens_usados TEXT,
                embalagens_usadas TEXT
            );
        """)

        # Tabela de configuração administrativa
        cur.execute("""
            CREATE TABLE IF NOT EXISTS admin (
                id INTEGER PRIMARY KEY,
                porcentagem REAL,
                bg_color TEXT
            );
        """)
        cur.execute("SELECT id FROM admin WHERE id=1")
        if not cur.fetchone():
            cur.execute("INSERT INTO admin (id, porcentagem, bg_color) VALUES (1, 0.0, NULL)")

        # Tabela de vendas
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vendas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                qty REAL,
                total REAL,
                data TEXT
            );
        """)

        # Tabela de produção
        cur.execute("""
            CREATE TABLE IF NOT EXISTS producao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                qty REAL,
                total REAL,
                data TEXT
            );
        """)

        # Tabela de usuários (login)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL
            );
        """)
        conn.commit()
        conn.close()

    def load_admin_config(self):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        try:
            cur.execute("SELECT porcentagem, bg_color FROM admin WHERE id=1")
            row = cur.fetchone()
        except:
            row = (0.0, None)
        conn.close()
        if row:
            p, c = row
            if p is not None:
                self.admin_porcentagem = p
            if c is not None:
                self.bg_color = c

    def save_admin_config(self):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        try:
            cur.execute("UPDATE admin SET porcentagem=?, bg_color=? WHERE id=1",
                        (self.admin_porcentagem, self.bg_color))
        except:
            cur.execute("UPDATE admin SET porcentagem=? WHERE id=1", (self.admin_porcentagem,))
        conn.commit()
        conn.close()

    # COLE AQUI!
    def calcular_lucro_liquido(self):
        """
        Calcula o lucro líquido do período:
        soma das vendas - custo estimado das vendas
        O cálculo é igual ao do relatório de vendas!
        """
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT product_id, qty, total FROM vendas")
        vendas_rows = cur.fetchall()
        lucro_liquido = 0.0
        venda_total = 0.0
        custo_total = 0.0

        for (prod_id, qty_vendida, valor_venda_real) in vendas_rows:
            venda_total += valor_venda_real
            c2 = conn.cursor()
            c2.execute("SELECT itens_usados, embalagens_usadas FROM vitrine WHERE id=?", (prod_id,))
            row_v = c2.fetchone()
            if not row_v:
                continue
            itens_json = row_v[0] or ""
            emb_json = row_v[1] or ""
            try:
                itens_dict = json.loads(itens_json)
            except:
                itens_dict = {}
            try:
                emb_dict = json.loads(emb_json)
            except:
                emb_dict = {}
            custo_venda = 0.0
            for nome_item, qtd_usada_para1 in itens_dict.items():
                usage_total = qtd_usada_para1 * qty_vendida
                c3 = conn.cursor()
                c3.execute("SELECT valor_aquisicao, quantidade, unidade FROM estoque WHERE nome=?", (nome_item,))
                row_e = c3.fetchone()
                if row_e:
                    val_aquis, qtd_estoque, und_estoque = row_e
                    if qtd_estoque != 0:
                        custo_venda += (val_aquis / qtd_estoque) * usage_total
            for emb_name, emb_usage_para1 in emb_dict.items():
                usage_total = emb_usage_para1 * qty_vendida
                c4 = conn.cursor()
                c4.execute("SELECT valor, quantidade, unidade FROM embalagens WHERE nome=?", (emb_name,))
                row_eb = c4.fetchone()
                if row_eb:
                    val_eb, qtd_eb, und_emb = row_eb
                    if qtd_eb != 0:
                        custo_venda += (val_eb / qtd_eb) * usage_total
            custo_total += custo_venda
            lucro_liquido += (valor_venda_real - custo_venda)
        conn.close()
        return lucro_liquido
    
    def update_lucro_label(self):
        """
        Calcula o lucro igual ao relatório de vendas e exibe.
        """
        lucro_liquido = self.calcular_lucro_liquido()
        if lucro_liquido >= 0:
            text = f"Lucro R$ {lucro_liquido:,.2f}"
        else:
            text = f"Prejuízo R$ {abs(lucro_liquido):,.2f}"
        self.status_label.config(text=text)

    def mostrar_extrato(self):
        import datetime

        popup = tk.Toplevel(self)
        popup.title("Extrato Bancário")
        center_popup(self, popup, min_width=900, min_height=400)

        text_area = tk.Text(popup, wrap="none", font=("Courier", 10))
        text_area.pack(fill=tk.BOTH, expand=True)
        scroll_y = tk.Scrollbar(popup, orient=tk.VERTICAL, command=text_area.yview)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x = tk.Scrollbar(popup, orient=tk.HORIZONTAL, command=text_area.xview)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        text_area.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        header = f"{'Dia':<12} {'Descrição':<35} {'Débito':>15} {'Crédito':>15} {'Saldo':>16}\n"
        text_area.insert(tk.END, header)
        text_area.insert(tk.END, "-" * 98 + "\n")

        movimentos = []

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT nome, valor_aquisicao, quantidade, unidade, data_cadastro FROM estoque")
        estoque_rows = cur.fetchall()
        for nome, valor, qtd, unidade, data in estoque_rows:
            descricao = f"Compra Estoque ({nome})"
            data_fmt = "??/??/????"
            if data:
                try:
                    if '-' in data and len(data) >= 10:
                        dt = datetime.datetime.strptime(data[:10], "%Y-%m-%d")
                        data_fmt = dt.strftime("%d/%m/%Y")
                    elif '/' in data and len(data) >= 10:
                        dt = datetime.datetime.strptime(data[:10], "%d/%m/%Y")
                        data_fmt = dt.strftime("%d/%m/%Y")
                except Exception:
                    data_fmt = data
            movimentos.append({
                "data": data_fmt,
                "descricao": descricao,
                "debito": valor,
                "credito": 0.0
            })

        cur.execute("""
            SELECT v.data, vt.nome, v.total
            FROM vendas v
            JOIN vitrine vt ON v.product_id = vt.id
            ORDER BY v.data
        """)
        for data, nome, total in cur.fetchall():
            descricao = f"Venda ({nome})"
            data_fmt = "??/??/????"
            if data:
                try:
                    if '-' in data and len(data) >= 10:
                        dt = datetime.datetime.strptime(data[:10], "%Y-%m-%d")
                        data_fmt = dt.strftime("%d/%m/%Y")
                    elif '/' in data and len(data) >= 10:
                        dt = datetime.datetime.strptime(data[:10], "%d/%m/%Y")
                        data_fmt = dt.strftime("%d/%m/%Y")
                except Exception:
                    data_fmt = data
            movimentos.append({
                "data": data_fmt,
                "descricao": descricao,
                "debito": 0.0,
                "credito": total
            })
        conn.close()

        def safe_date(x):
            for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                try:
                    return datetime.datetime.strptime(x['data'], fmt)
                except Exception:
                    continue
            return datetime.datetime(1900, 1, 1)
        movimentos.sort(key=safe_date)

        saldo = 0.0
        for m in movimentos:
            saldo = saldo - m['debito'] + m['credito']
            debito_str = f"R$ {m['debito']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            credito_str = f"R$ {m['credito']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            saldo_str = f"R$ {abs(saldo):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            if saldo >= 0:
                saldo_str = saldo_str + " C"
            else:
                saldo_str = saldo_str + " D"
            linha = f"{m['data']:<12} {m['descricao']:<35} {debito_str:>15} {credito_str:>15} {saldo_str:>16}\n"
            text_area.insert(tk.END, linha)

        text_area.config(state="disabled")

    def apply_bg_color(self):
        if not self.bg_color:
            self.bg_color = "#FFFFFF"
        self.configure(bg=self.bg_color)
        style = ttk.Style(self)
        style.configure(".", background=self.bg_color)
        style.configure("TNotebook", background=self.bg_color)
        style.configure("TFrame", background=self.bg_color)
        style.configure("TLabelFrame", background=self.bg_color)

    def update_all_frames(self):
        print("[DEBUG] update_all_frames() - Recarregando abas.")
        self.estoque_frame.load_estoque()
        self.embalagem_frame.load_embalagens()
        self.vitrine_frame.load_produtos()
        self.produtos_frame.load_produtos()
        self.producao_frame.load_producao()
        self.vendas_frame.load_produtos_vitrine()
        self.vendas_frame.load_ultimas_vendas()
        self.update_lucro_label()

    def escolher_cor(self):
        cor = colorchooser.askcolor(title="Escolha uma cor")
        if cor and cor[1]:
            self.bg_color = cor[1]
            self.apply_bg_color()
            self.save_admin_config()
            messagebox.showinfo("Cores", f"Cor selecionada: {self.bg_color}")

    def abrir_lucro(self):
        popup = tk.Toplevel(self)
        popup.title("Lucro")
        center_popup(self, popup)

        ttk.Label(popup, text=f"Porcentagem atual: {self.admin_porcentagem}%").pack(pady=5)

        ttk.Label(popup, text="Nova porcentagem:").pack()
        entry_porcent = ttk.Entry(popup, width=10)
        entry_porcent.pack()
        entry_porcent.insert(0, str(self.admin_porcentagem))

        def salvar():
            try:
                p = float(entry_porcent.get().replace(",", "."))
            except ValueError:
                messagebox.showerror("Erro", "Porcentagem inválida.")
                return
            self.admin_porcentagem = p
            self.save_admin_config()
            self.recalc_all_products()
            self.update_all_frames()
            messagebox.showinfo("Lucro", "Porcentagem salva e preços recalculados.")

        ttk.Button(popup, text="Salvar", command=salvar).pack(pady=5)

    def mostrar_relatorio_venda(self):
        import sqlite3
        import tkinter as tk
        from tkinter import messagebox
        from datetime import datetime

        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()

            # Seleciona vendas e puxa o nome do produto da vitrine
            cur.execute("""
                SELECT v.data, v.product_id, v.qty, v.total, vt.nome
                FROM vendas v
                LEFT JOIN vitrine vt ON v.product_id = vt.id
                ORDER BY v.data ASC
            """)
            vendas = cur.fetchall()
            conn.close()

            relatorio = []
            total_geral = 0.0
            for venda in vendas:
                data, product_id, qtd, valor, nome_produto = venda
                # Se não achou o nome na vitrine, mostra o ID
                if not nome_produto:
                    nome_produto = f"ID {product_id} (NOME NÃO ENCONTRADO)"

                # Formata data para DD/MM/AAAA HH:MM
                try:
                    dt_obj = datetime.strptime(data, "%Y-%m-%d %H:%M:%S")
                    data_fmt = dt_obj.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    data_fmt = data  # Usa como veio se der erro

                relatorio.append(
                    f"Data: {data_fmt}\n"
                    f"Produto: {nome_produto}\n"
                    f"Quantidade: {qtd}\n"
                    f"Valor Total: R$ {float(valor):,.2f}\n"
                    f"{'-'*40}"
                )
                try:
                    total_geral += float(valor)
                except Exception:
                    pass
            relatorio.append(f"\nTotal Geral de Vendas: R$ {total_geral:,.2f}\n")

            # Exibe relatório em nova janela Tkinter
            rel_dialog = tk.Toplevel(self)
            rel_dialog.title("Relatório de Venda")
            txt = tk.Text(rel_dialog, width=70, height=30)
            txt.pack(padx=10, pady=10)
            txt.insert(tk.END, "\n".join(relatorio))
            txt.config(state=tk.DISABLED)

        except Exception as e:
            messagebox.showerror("Erro ao gerar relatório", str(e))

    def recalc_all_products(self):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id, itens_usados, embalagens_usadas FROM vitrine")
        rows = cur.fetchall()

        for (pid, itens_json, emb_json) in rows:
            try:
                itens_dict = json.loads(itens_json) if itens_json else {}
            except:
                itens_dict = {}
            try:
                emb_dict = json.loads(emb_json) if emb_json else {}
            except:
                emb_dict = {}

            custo_itens = 0.0
            for nome_item, qtd_usada in itens_dict.items():
                c2 = conn.cursor()
                c2.execute("SELECT valor_aquisicao, quantidade, unidade FROM estoque WHERE nome=?", (nome_item,))
                row_e = c2.fetchone()
                if row_e:
                    val_aquis, qtd_estoque, und_estoque = row_e
                    if qtd_estoque != 0:
                        usage_db_scale = convert_usage_for_cost(qtd_usada, und_estoque)
                        custo_itens += (val_aquis / qtd_estoque) * usage_db_scale

            custo_emb = 0.0
            for emb_name, emb_usage in emb_dict.items():
                c3 = conn.cursor()
                c3.execute("SELECT valor, quantidade, unidade FROM embalagens WHERE nome=?", (emb_name,))
                row_eb = c3.fetchone()
                if row_eb:
                    val_eb, qtd_eb, und_emb = row_eb
                    if qtd_eb != 0:
                        usage_db_scale2 = convert_usage_for_cost(emb_usage, und_emb)
                        custo_emb += (val_eb / qtd_eb) * usage_db_scale2

            preco_venda = (custo_itens + custo_emb) * (1 + (self.admin_porcentagem / 100))
            cur2 = conn.cursor()
            cur2.execute("UPDATE vitrine SET preco_venda=? WHERE id=?", (preco_venda, pid))

        conn.commit()
        conn.close()

    def mostrar_relatorio_produtos(self):
        popup = tk.Toplevel(self)
        popup.title("Relatório de Produtos (CSV)")
        center_popup(self, popup)

        text_area = tk.Text(popup, wrap="word")
        text_area.pack(fill=tk.BOTH, expand=True)

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id, nome, preco_venda, itens_usados, embalagens_usadas FROM vitrine ORDER BY nome")
        produtos_rows = cur.fetchall()
        relatorio_data = []

        for (prod_id, prod_nome, preco_venda, itens_json, emb_json) in produtos_rows:
            text_area.insert(tk.END, f"=== Produto: {prod_nome} ===\n")
            custo_total = 0.0
            try:
                itens_dict = json.loads(itens_json) if itens_json else {}
            except:
                itens_dict = {}
            for nome_item, qtd_usada in itens_dict.items():
                c2 = conn.cursor()
                c2.execute("SELECT valor_aquisicao, quantidade, unidade FROM estoque WHERE nome=?", (nome_item,))
                row_e = c2.fetchone()
                if row_e:
                    val_aquis, qtd_estoque, und_estoque = row_e
                    usage_db_scale = qtd_usada
                    if qtd_estoque != 0:
                        custo_item = (val_aquis / qtd_estoque) * usage_db_scale
                    else:
                        custo_item = 0.0
                    custo_total += custo_item
                    text_area.insert(tk.END, f"  [Item] {nome_item}, qtd usada: {qtd_usada}, custo: R$ {custo_item:,.2f}\n")
                else:
                    text_area.insert(tk.END, f"  [Item] {nome_item} -> não encontrado no estoque\n")

            try:
                emb_dict = json.loads(emb_json) if emb_json else {}
            except:
                emb_dict = {}
            for emb_name, emb_usage in emb_dict.items():
                c3 = conn.cursor()
                c3.execute("SELECT valor, quantidade, unidade FROM embalagens WHERE nome=?", (emb_name,))
                row_eb = c3.fetchone()
                if row_eb:
                    val_eb, qtd_eb, und_emb = row_eb
                    usage_db_scale = emb_usage
                    if qtd_eb != 0:
                        custo_emb = (val_eb / qtd_eb) * usage_db_scale
                    else:
                        custo_emb = 0.0
                    custo_total += custo_emb
                    text_area.insert(tk.END, f"  [Emb] {emb_name}, qtd usada: {emb_usage}, custo: R$ {custo_emb:,.2f}\n")
                else:
                    text_area.insert(tk.END, f"  [Emb] {emb_name} -> não encontrado\n")

            lucro_liquido = preco_venda - custo_total
            text_area.insert(
                tk.END,
                f" => Custo total: R$ {custo_total:,.2f}\n"
                f" => Preço de Venda Previsto: R$ {preco_venda:,.2f}\n"
                f" => Lucro Liquido Previsto: R$ {lucro_liquido:,.2f}\n"
                "-----------------------------------\n"
            )
            relatorio_data.append({
                "produto": prod_nome,
                "preco_venda": preco_venda,
                "custo_total": custo_total,
                "lucro_liquido": lucro_liquido
            })
        conn.close()

        text_area.config(state="disabled")
        
        # O botão deve ficar aqui, alinhado à esquerda!
        btn_export = ttk.Button(popup, text="Exportar CSV", command=self.exportar_csv_produtos)
        btn_export.pack(pady=5)

    def exportar_csv_vendas(self):
        import csv
        import datetime
        from tkinter.filedialog import asksaveasfilename
        import os

        filename = asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=f"RelatorioVendas_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            title="Salvar relatório de vendas como CSV"
        )
        if not filename:
            return

        try:
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(["Data", "Produto", "Quantidade", "Valor Total (R$)"])
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute("""
                    SELECT v.data, vt.nome, v.qty, v.total
                    FROM vendas v
                    JOIN vitrine vt ON v.product_id = vt.id
                    ORDER BY v.data
                """)
                for data, nome, qtd, total in cur.fetchall():
                    writer.writerow([data, nome, f"{qtd:.2f}", f"{total:.2f}"])
                conn.close()
            messagebox.showinfo("Exportar CSV", f"Relatório de vendas salvo em\n{os.path.basename(filename)}!")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exportar CSV: {e}")

def create_initial_database():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Repita exatamente o que está no método App.create_database, para garantir!
    cur.execute("""
        CREATE TABLE IF NOT EXISTS estoque (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            valor_aquisicao REAL NOT NULL,
            quantidade REAL NOT NULL,
            unidade TEXT NOT NULL,
            data_cadastro TEXT
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS embalagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            valor REAL NOT NULL,
            quantidade REAL,
            unidade TEXT
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vitrine (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            preco_venda REAL NOT NULL,
            itens_usados TEXT,
            embalagens_usadas TEXT
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY,
            porcentagem REAL,
            bg_color TEXT
        );
    """)
    cur.execute("SELECT id FROM admin WHERE id=1")
    if not cur.fetchone():
        cur.execute("INSERT INTO admin (id, porcentagem, bg_color) VALUES (1, 0.0, NULL)")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            qty REAL,
            total REAL,
            data TEXT
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS producao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            qty REAL,
            total REAL,
            data TEXT
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()

# =========================================
# MAIN
# =========================================
if __name__ == "__main__":
    create_initial_database()  # <-- GARANTE O BANCO/TABELAS
    root = tk.Tk()
    root.withdraw()
    def iniciar_app():
        root.destroy()
        app = App()
        app.mainloop()
    LoginScreen(root, on_login_success=iniciar_app)
    root.mainloop()