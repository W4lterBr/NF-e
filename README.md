# BOT - Busca NFE

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Windows%2010%2B-lightgrey)
![GUI](https://img.shields.io/badge/GUI-PyQt6-41cd52)
![PDF](https://img.shields.io/badge/PDF-brazil--fiscal--report-brightgreen)

Aplicativo desktop para buscar e consolidar documentos fiscais eletrônicos (NF-e e CT-e), com interface PyQt6, cache local e abertura de DANFE/DACTE em PDF.

> Destaques: múltiplos certificados A1, cooldown inteligente entre consultas, exibição do último NSU por certificado, tabela somente leitura com duplo clique para abrir PDF, cache dos XMLs, e geração de PDFs com layout oficial via brazil-fiscal-report.

---

## ✨ Recursos

- Busca de eventos/NSU por certificado A1 (PKCS#12)
- Resumo e extração de detalhes das notas (NF-e e CT-e)
- Contagem regressiva/cooldown entre consultas com botão para forçar
- Exibição do último NSU por certificado (alias) no cabeçalho
- Tabela somente leitura, duplo clique abre DANFE/DACTE em PDF
- Cache e organização de XMLs por CNPJ/ano-mês
- Banco local SQLite para notas, status e controle de downloads
- Geração de PDF:
  - Primário: brazil-fiscal-report (DANFE/DACTE completos)
  - Alternativos: PyNFe (NF-e), erpbrasil.edoc.pdf (CT-e, pode limitar no Windows)
  - Fallback: ReportLab (PDF simplificado, último recurso)

---

## 🖼️ Capturas de tela

> Adicione imagens em `docs/` e atualize os caminhos abaixo.

- Tela principal: `docs/screenshot-home.png`
- DANFE gerado: `docs/screenshot-danfe.png`
- DACTE gerado: `docs/screenshot-dacte.png`

```text
docs/
  screenshot-home.png
  screenshot-danfe.png
  screenshot-dacte.png
```

---

## 🧭 Arquitetura (alto nível)

- `interface_pyqt6.py`: Interface gráfica (PyQt6), timers de cooldown, grid de notas e double-click para PDF.
- `nfe_search.py`: Distribuição por NSU/chave, download e parsing dos XMLs, validação por XSD.
- `modules/pdf_generator.py`: Geração de PDF a partir do XML completo (usa brazil-fiscal-report por padrão).
- `modules/deps_checker.py`: Verificador/instalador automático de dependências de PDF.
- `Arquivo_xsd/`: Schemas XSD oficiais para validação.
- `xmls/`: Repositório dos XMLs por CNPJ/ano-mês (cache local para acesso rápido).
- Banco de dados: SQLite com tabelas como `notas_detalhadas`, `nsu`, `xmls_baixados`, `nf_status`.

---

## ✅ Pré-requisitos

- Windows 10 ou superior
- Python 3.11+ (recomendado 3.12)
- Certificado A1 (arquivo .pfx/.p12) com senha
- Acesso à internet para consultas na SEFAZ

---

## 🚀 Instalação

Use um ambiente virtual e instale as dependências (PowerShell):

```powershell
# 1) Crie e ative o venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) Atualize pip e instale os requisitos
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Se preferir, os pacotes essenciais de PDF são:

```powershell
pip install brazil-fiscal-report qrcode[pil] reportlab
```

---

## ▶️ Como executar

```powershell
.\.venv\Scripts\Activate.ps1
python interface_pyqt6.py
```

- Na primeira execução, o app pode instalar automaticamente dependências de PDF e avisará na interface.
- Cadastre/aponte seus certificados e selecione o período para busca.

---

## 📄 Geração de PDFs

O módulo `modules/pdf_generator.py` usa a seguinte prioridade:

1) brazil-fiscal-report — DANFE/DACTE oficiais (Windows-friendly)
2) PyNFe — dependendo da versão, pode não conter gerador de PDF funcional
3) erpbrasil.edoc.pdf — pode depender de libs não disponíveis no Windows
4) ReportLab — fallback simplificado (sem layout oficial)

Dependências relevantes:

- `brazil-fiscal-report` (DANFE/DACTE) — usa xFPDF
- `qrcode[pil]` — exigido para DACTE (QR Code)

---

## 🗂️ Estrutura de pastas

```text
BOT - Busca NFE/
  interface_pyqt6.py            # GUI principal (PyQt6)
  nfe_search.py                 # Busca/distribuição e parsing
  modules/
    pdf_generator.py            # Geração de DANFE/DACTE
    deps_checker.py             # Verificador/instalador de deps PDF
  Arquivo_xsd/                  # Schemas XSD
  xmls/                         # Cache de XMLs por CNPJ/ano-mês
  requirements.txt
  README.md
  ...
```

---

## 🛠️ Configurações

- Certificados A1: utilize o alias/nome mostrado na interface; o app exibirá o último NSU por certificado no topo.
- Cooldown: intervalo inteligente de 60 minutos entre buscas, com contagem regressiva e opção de forçar nova rodada.
- XMLs: salvos automaticamente em `xmls/<CNPJ>/<YYYY-MM>/...` e registrados no SQLite.

---

## ❗ Solução de problemas

- “PDF simplificado” ao abrir DANFE:
  - Certifique-se de ter `brazil-fiscal-report` instalado (o app tenta instalar automaticamente).
- CT-e não abre por falta de QR Code:
  - Instale `qrcode[pil]` (já incluso no requirements).
- ImportError em `erpbrasil.edoc.pdf` no Windows:
  - Normal em alguns ambientes. O app usará brazil-fiscal-report ou fallback.
- Problemas com certificado A1 (senha/arquivo):
  - Verifique o caminho do .pfx/.p12 e a senha. Consulte os guias `CERTIFICADOS_*.md` no repositório.

---

## 🧭 Roadmap

- Exportações CSV/Excel a partir da grade
- Filtros avançados e busca por chave
- Melhorias visuais no DANFE/DACTE (logos e estilos)

---

## 🙏 Créditos

- [brazil-fiscal-report](https://pypi.org/project/brazil-fiscal-report/) — Geração de DANFE/DACTE
- [PyNFe](https://pypi.org/project/PyNFe/)
- [erpbrasil.edoc.pdf](https://github.com/erpbrasil/erpbrasil.edoc.pdf)
- [ReportLab](https://www.reportlab.com/dev/opensource/)
- [PyQt6](https://pypi.org/project/PyQt6/)
- [Zeep](https://docs.python-zeep.org/en/master/)

> Este projeto consome serviços da SEFAZ e requer certificação digital válida. Utilize em conformidade com a legislação vigente.
