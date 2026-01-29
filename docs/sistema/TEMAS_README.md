# 🎨 Sistema de Temas - Busca NF-e

## 📋 Índice
1. [Visão Geral](#visão-geral)
2. [Temas Disponíveis](#temas-disponíveis)
3. [Como Usar](#como-usar)
4. [Personalização](#personalização)
5. [Estrutura Técnica](#estrutura-técnica)
6. [Desenvolvimento](#desenvolvimento)

---

## 🎯 Visão Geral

O sistema Busca NF-e agora conta com um **sistema de temas visual** completo que permite personalizar a aparência da interface de acordo com suas preferências ou necessidades de acessibilidade.

### ✨ Características

- **5 temas prontos** para uso imediato
- **Fácil troca de temas** através do menu
- **Persistência** - O tema escolhido é salvo e mantido entre sessões
- **Acessibilidade** - Inclui tema de alto contraste
- **Cores consistentes** em toda a interface

---

## 🎨 Temas Disponíveis

### 1. 📱 **Padrão** (Tema Original)
- **Tipo:** Claro
- **Descrição:** Tema claro padrão do sistema
- **Ideal para:** Uso diário em ambientes bem iluminados
- **Características:**
  - Fundo branco/cinza claro
  - Texto preto
  - Destaques em azul (#0078d7)
  - Visual limpo e profissional

### 2. 🌙 **Escuro**
- **Tipo:** Escuro
- **Descrição:** Tema escuro moderno para reduzir fadiga visual
- **Ideal para:** Trabalho noturno, ambientes com pouca luz
- **Características:**
  - Fundo cinza escuro (#2b2b2b)
  - Texto cinza claro (#d4d4d4)
  - Botões azuis com destaque
  - Reduz cansaço visual em uso prolongado
  - Inspirado no VS Code Dark+

### 3. 💼 **Azul Profissional**
- **Tipo:** Claro
- **Descrição:** Tema azul elegante para ambiente corporativo
- **Ideal para:** Apresentações, ambientes profissionais
- **Características:**
  - Fundo branco/cinza claro
  - Botões e cabeçalhos em azul Windows (#0078d7)
  - Visual sofisticado e profissional
  - Ótimo para ambientes formais

### 4. 🌿 **Verde Natureza**
- **Tipo:** Claro
- **Descrição:** Tema verde suave inspirado na natureza
- **Ideal para:** Reduzir estresse visual, ambiente relaxante
- **Características:**
  - Tons de verde natural
  - Fundo verde muito claro (#e8f5e9)
  - Botões e destaques em verde (#4caf50)
  - Visual calmo e harmonioso

---

## 🚀 Como Usar

### Alterando o Tema

1. **Via Menu Superior:**
   ```
   Menu → Temas → [Selecione o tema desejado]
   ```

2. **O tema é aplicado imediatamente** - não precisa reiniciar o programa

3. **Sua escolha é salva** - o tema será mantido quando você abrir o programa novamente

### Arquivo de Configuração

As preferências de tema são salvas em:
```
theme_config.json
```

**Conteúdo do arquivo:**
```json
{
    "theme": "Nome do Tema"
}
```

Se você apagar este arquivo, o sistema voltará ao tema Padrão.

---

## 🎨 Personalização

### Cores de Status na Tabela

Cada tema define cores específicas para os status das notas na tabela:

| Status | Padrão | Escuro | Azul Prof. | Verde |
|--------|--------|--------|------------|-------|
| ✅ Autorizada | 🟢 Verde claro | 🟢 Verde escuro | 🟢 Verde claro | 🟢 Verde médio |
| ❌ Cancelada | 🔴 Vermelho claro | 🔴 Vermelho escuro | 🔴 Vermelho claro | 🟠 Laranja claro |
| ⚪ Outros | ⚪ Cinza claro | ⚫ Cinza escuro | ⚪ Cinza claro | ⚪ Cinza claro |

### Elementos Personalizáveis

Cada tema personaliza:
- ✅ Cores de fundo (janelas, formulários, tabelas)
- ✅ Cores de texto
- ✅ Cores de botões
- ✅ Cores de links
- ✅ Cores de campos de entrada
- ✅ Cores de cabeçalhos de tabela
- ✅ Cores de status
- ✅ Cores de tooltips
- ✅ Bordas e destaques

---

## 🔧 Estrutura Técnica

### Arquivos do Sistema

```
📁 Busca NF-e/
├── 📄 themes.py              # Módulo principal de temas
├── 📄 theme_config.json      # Configuração salva (gerado automaticamente)
├── 📄 Busca NF-e.py          # Aplicação principal (integra os temas)
└── 📄 TEMAS_README.md        # Esta documentação
```

### Classes e Métodos

#### `ThemeManager` (themes.py)

**Métodos Principais:**

```python
# Aplicar tema
ThemeManager.apply_theme(app, "Nome do Tema")

# Obter lista de temas
temas = ThemeManager.get_theme_names()

# Obter informações de um tema
info = ThemeManager.get_theme_info("Escuro")

# Obter cores de status
cores = ThemeManager.get_status_colors("Padrão")

# Salvar preferência
ThemeManager.save_theme_preference("Escuro")

# Carregar preferência salva
tema_salvo = ThemeManager.load_theme_preference()
```

### Estrutura de um Tema

```python
{
    "name": "Nome do Tema",
    "description": "Descrição breve",
    "type": "light" ou "dark",
    "colors": {
        # Cores de fundo
        "window": "#f0f0f0",
        "base": "#ffffff",
        "alternate_base": "#f9f9f9",
        
        # Cores de texto
        "text": "#000000",
        "bright_text": "#ffffff",
        
        # Cores de destaque
        "highlight": "#0078d7",
        "highlight_text": "#ffffff",
        
        # Cores de botões
        "button": "#e1e1e1",
        "button_text": "#000000",
        
        # Cores de links
        "link": "#0066cc",
        "link_visited": "#551a8b",
        
        # Cores especiais
        "success": "#28a745",
        "warning": "#ffc107",
        "error": "#dc3545",
        "info": "#17a2b8",
        
        # Cores de status
        "status_autorizada": "#d6f5e0",
        "status_cancelada": "#ffdcdc",
        "status_outros": "#ebebeb"
    },
    "stylesheet": "/* QSS (Qt Style Sheets) */"
}
```

---

## 👨‍💻 Desenvolvimento

### Adicionando um Novo Tema

Para criar um novo tema, edite o arquivo `themes.py`:

1. **Copie um tema existente** como base
2. **Modifique as cores** no dicionário `colors`
3. **Ajuste o stylesheet** QSS conforme necessário
4. **Adicione ao dicionário `THEMES`**

**Exemplo:**

```python
"Meu Tema": {
    "name": "Meu Tema",
    "description": "Descrição do meu tema",
    "type": "light",  # ou "dark"
    "colors": {
        "window": "#cor_hex",
        # ... outras cores
    },
    "stylesheet": """
        /* Seus estilos QSS aqui */
    """
}
```

### Testando um Tema

1. Adicione o tema ao `themes.py`
2. Reinicie o programa
3. Selecione seu tema no menu
4. Teste todos os elementos da interface

### Dicas de Design

- **Contraste:** Garanta contraste suficiente entre texto e fundo (mínimo 4.5:1)
- **Consistência:** Use a mesma paleta de cores em toda a interface
- **Acessibilidade:** Teste com usuários que têm necessidades especiais
- **Performance:** Evite gradientes e efeitos pesados em QSS
- **Multiplataforma:** Teste em Windows, Linux e macOS

### Validadores de Contraste

Para garantir acessibilidade:
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- [Contrast Ratio](https://contrast-ratio.com/)

---

## 📊 Comparação de Temas

| Característica | Padrão | Escuro | Azul Prof. | Verde |
|----------------|--------|--------|------------|-------|
| **Tipo** | Claro | Escuro | Claro | Claro |
| **Fadiga Visual** | Média | Baixa | Média | Baixa |
| **Profissionalismo** | Alto | Médio | Muito Alto | Médio |
| **Uso Noturno** | ❌ | ✅ | ❌ | ❌ |
| **Apresentações** | ✅ | ❌ | ✅ | ✅ |

---

## ❓ FAQ (Perguntas Frequentes)

### **P: Como voltar ao tema original?**
**R:** Selecione o tema "Padrão" no menu Temas.

### **P: Posso criar meus próprios temas?**
**R:** Sim! Edite o arquivo `themes.py` e adicione seu tema personalizado.

### **P: O tema afeta a performance?**
**R:** Não. Os temas são apenas estilos visuais e não afetam a velocidade do programa.

### **P: Posso usar o tema em vários computadores?**
**R:** Sim. Copie o arquivo `theme_config.json` para outros computadores.

### **P: O que acontece se eu apagar o theme_config.json?**
**R:** O programa voltará ao tema Padrão na próxima inicialização.

### **P: Qual tema é melhor para acessibilidade?**

## 🐛 Solução de Problemas

### Tema não aplica corretamente

1. **Verifique se o arquivo `themes.py` está presente**
2. **Reinicie o programa**
3. **Delete o `theme_config.json` e tente novamente**

### Cores estranhas após trocar tema

1. **Isso é normal durante a transição**
2. **Feche e reabra janelas/diálogos para atualizar**
3. **Se persistir, reinicie o programa**

### Erro ao salvar preferência de tema

1. **Verifique permissões de escrita na pasta**
2. **Execute o programa como administrador (se necessário)**
3. **Verifique se há espaço em disco**

---

## 📝 Changelog

### Versão 1.0.92 (27/01/2026)
- ✅ Sistema de temas implementado
- ✅ 5 temas disponíveis
- ✅ Persistência de preferências
- ✅ Menu de seleção de temas
- ✅ Documentação completa

---

## 📞 Suporte

Para dúvidas ou sugestões sobre temas:
- Abra uma issue no repositório
- Entre em contato com o desenvolvedor

---

## 📄 Licença

Este sistema de temas é parte do projeto Busca NF-e e segue a mesma licença do projeto principal.

---

**🎨 Aproveite sua experiência visual personalizada no Busca NF-e!**
