# 🛒 Amazon Product Scraper Pro

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.51.0-FF4B4B.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Active-success.svg)

**Extraia dados completos de produtos da Amazon com tradução automática para PT-BR** 🇧🇷

[Demo](#-demo) • [Recursos](#-recursos) • [Instalação](#-instalação) • [Como Usar](#-como-usar) • [Deploy](#-deploy)

</div>

---

## 📖 Sobre o Projeto

**Amazon Product Scraper Pro** é uma ferramenta web desenvolvida em Python que permite extrair informações detalhadas de produtos da Amazon e traduzi-las automaticamente para português brasileiro usando **Deep Translator**.

### 🎯 Por que usar este projeto?

- ✅ **Interface intuitiva** - Fácil de usar, não precisa programar
- ✅ **Tradução automática** - Todos os dados em PT-BR
- ✅ **Dados completos** - Título, preço, avaliações, especificações e muito mais
- ✅ **Múltiplos formatos** - Exporta em CSV, JSON e Excel
- ✅ **Gratuito** - 100% open source

---

## ✨ Recursos

### 📊 Dados Extraídos

| Campo | Descrição |
|-------|-----------|
| **Título** | Nome completo do produto |
| **Preço** | Valor atual do produto |
| **Avaliação** | Rating médio (ex: 4.5 de 5 estrelas) |
| **Número de Avaliações** | Total de reviews |
| **Disponibilidade** | Em estoque / Fora de estoque |
| **Marca** | Fabricante do produto |
| **ASIN** | Código único da Amazon |
| **Imagem** | URL da imagem principal |
| **Sobre o Item** | Lista de características principais |
| **Informações do Produto** | Dimensões, peso, modelo, baterias, etc. |

### 🌐 Tradução Automática

- Tradução inteligente usando **Deep Translator**
- Suporte para textos longos (divide automaticamente)
- Preserva URLs, números e códigos
- Progress bar para acompanhar o progresso

### 📥 Formatos de Exportação

- **CSV** - Para análise em Excel/Google Sheets
- **JSON** - Para integração com outras aplicações
- **Excel** - Planilha formatada (.xlsx)

---

## 🖼️ Demo

### Interface Principal
```
🛒 Amazon Product Scraper Pro
┌──────────────────────────────────────┐
│ 🔗 Cole a URL do produto:            │
│ [https://www.amazon.com/dp/......]   │
│                                      │
│ [🚀 Coletar Dados]                   │
└──────────────────────────────────────┘
```

### Exemplo de Resultado

```
✅ Dados coletados com sucesso!

💰 Preço              ⭐ Avaliação       📦 Disponibilidade
$39.99               4.1/5 estrelas     Em Estoque

ℹ️ Informações Básicas
────────────────────────────────────────
Título: KEEPONFIT Smart Watches for Women...
Marca: KEEPONFIT
ASIN: B0DDQ7YCK6

📝 Sobre este Item
────────────────────────────────────────
1. Cuidados especiais para mulheres...
2. Rastreamento multifuncional...
3. Notificações inteligentes...
```

---

## 🚀 Instalação

### Pré-requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

### Passo 1: Clone o Repositório

```bash
git clone https://github.com/seu-usuario/amazon-scraper-pro.git
cd amazon-scraper-pro
```

### Passo 2: Instale as Dependências

```bash
pip install -r requirements.txt
```

**Conteúdo do `requirements.txt`:**
```txt
streamlit
beautifulsoup4
requests
pandas
openpyxl
deep-translator
```

### Passo 3: Execute o App

```bash
streamlit run app.py
```

O aplicativo abrirá automaticamente no seu navegador em `http://localhost:8501`

---

## 💡 Como Usar

### 1️⃣ Obtenha a URL do Produto

Acesse qualquer produto na Amazon e copie a URL:
```
https://www.amazon.com/dp/B08N5WRWNW
```

### 2️⃣ Cole no App

Cole a URL no campo de entrada e clique em **"🚀 Coletar Dados"**

### 3️⃣ Aguarde a Coleta

- ⏳ Coleta de dados: ~3-5 segundos
- 🌐 Tradução: ~5-10 segundos

### 4️⃣ Baixe os Dados

Escolha o formato desejado:
- 📄 **CSV** - Para análise
- 📋 **JSON** - Para desenvolvimento
- 📊 **Excel** - Para relatórios

---

## ⚙️ Configurações

### Ativar/Desativar Tradução

Na **sidebar**, você pode:
- ✅ Ativar tradução para PT-BR (padrão)
- ❌ Desativar para manter dados em inglês

### Anti-Bloqueio

Para evitar bloqueios da Amazon:
- 🔄 Use delays entre requisições (já implementado)
- 🌐 Use VPN se necessário
- ⏰ Evite fazer muitas requisições seguidas

---

## 🌍 Deploy

### Deploy no Streamlit Cloud (Grátis)

1. **Crie um repositório no GitHub** com:
   - `app.py`
   - `requirements.txt`

2. **Acesse** [share.streamlit.io](https://share.streamlit.io)

3. **Conecte seu GitHub** e selecione o repositório

4. **Deploy!** 🚀

Seu app ficará disponível em:
```
https://seu-usuario-amazon-scraper.streamlit.app
```

### Outras Opções de Deploy

- **Heroku** - Grátis com limitações
- **Railway** - Deploy rápido
- **Render** - Deploy automático

---

## 🛠️ Tecnologias Utilizadas

| Tecnologia | Uso |
|------------|-----|
| **Python 3.8+** | Linguagem principal |
| **Streamlit** | Framework web |
| **BeautifulSoup4** | Web scraping |
| **Requests** | HTTP requests |
| **Pandas** | Manipulação de dados |
| **Deep Translator** | Tradução automática |
| **OpenPyXL** | Geração de Excel |

---

## 📁 Estrutura do Projeto

```
amazon-scraper-pro/
│
├── app.py                 # Aplicação principal
├── requirements.txt       # Dependências
├── README.md             # Documentação
└── .gitignore            # Arquivos ignorados
```

---

## 🔧 Funções Principais

### `coletar_dados_produto(url: str) -> dict`
Extrai todos os dados do produto da Amazon

### `traduzir_dados(dados: dict) -> dict`
Traduz dados usando Deep Translator

### `extrair_about_item(soup: BeautifulSoup) -> List[str]`
Extrai lista de características do produto

### `extrair_product_info(soup: BeautifulSoup) -> Dict[str, str]`
Extrai tabela de informações técnicas

---

## ⚠️ Avisos Importantes

### Uso Responsável

- ⚖️ Respeite os Termos de Serviço da Amazon
- 🎓 Use apenas para fins educacionais
- 🚫 Não faça scraping em massa
- ⏰ Respeite os rate limits

### Limitações

- 🔒 Amazon pode bloquear IPs suspeitos
- 📊 Layout da Amazon pode mudar
- 🌐 Alguns produtos podem ter estrutura diferente
- ⏱️ Tradução pode demorar em textos longos

---

## 🐛 Solução de Problemas

### Erro: "Deep Translator não instalado"

```bash
pip install deep-translator
```

### Erro: "Amazon bloqueou a requisição"

- Use uma VPN
- Aguarde alguns minutos
- Use headers diferentes

### Dados vêm como "N/A"

- Amazon mudou o layout
- Produto tem estrutura diferente
- Use outro produto para testar

---

## 🤝 Contribuindo

Contribuições são bem-vindas! 🎉

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/NovaFuncionalidade`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/NovaFuncionalidade`)
5. Abra um Pull Request

---

## 📝 Roadmap

### Próximas Funcionalidades

- [ ] Suporte para múltiplas URLs
- [ ] Comparação de preços
- [ ] Histórico de preços
- [ ] Notificações de queda de preço
- [ ] API REST
- [ ] Dashboard com gráficos
- [ ] Suporte para outros marketplaces (Mercado Livre, etc)

---

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

---

## 👤 Autor

**Seu Nome**

- GitHub: [@seu-usuario](https://github.com/seu-usuario)
- LinkedIn: [Seu Nome](https://linkedin.com/in/seu-perfil)
- Email: fabriciomacedo@bemol.com.br

---

## 🌟 Mostre seu Apoio

Se este projeto te ajudou, considere dar uma ⭐️!

---

## 📞 Contato

Tem dúvidas ou sugestões? Entre em contato!

- 💬 Issues: [GitHub Issues](https://github.com/seu-usuario/amazon-scraper-pro/issues)
- 📧 Email: seu.email@exemplo.com

---

<div align="center">

**Desenvolvido com ❤️ e ☕ por [Seu Nome]**

⭐ **Se gostou, deixe uma estrela!** ⭐

</div>

---

## 🎓 Recursos Adicionais

### Tutoriais
- [Como fazer web scraping com Python](https://realpython.com/beautiful-soup-web-scraper-python/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Deep Translator Guide](https://deep-translator.readthedocs.io/)

### APIs Alternativas
- [Amazon Product Advertising API](https://webservices.amazon.com/paapi5/documentation/)
- [Rainforest API](https://www.rainforestapi.com/)
- [ScraperAPI](https://www.scraperapi.com/)

---

## 📊 Estatísticas do Projeto

![GitHub stars](https://img.shields.io/github/stars/seu-usuario/amazon-scraper-pro?style=social)
![GitHub forks](https://img.shields.io/github/forks/seu-usuario/amazon-scraper-pro?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/seu-usuario/amazon-scraper-pro?style=social)

---

## 🏆 Agradecimentos

- [Streamlit](https://streamlit.io/) - Framework incrível
- [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) - Web scraping
- [Deep Translator](https://github.com/nidhaloff/deep-translator) - Tradução
- Comunidade Python 🐍

---

**Última atualização:** Novembro 2025
