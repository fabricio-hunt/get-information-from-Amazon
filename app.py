import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import logging
import csv
import json
from urllib.parse import urlparse
import time
import io
import streamlit as st
from datetime import datetime
import pandas as pd
import re

# Configuração
logging.basicConfig(level=logging.WARNING)

# User Agents
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]

# Seletores expandidos
SELECTORS = {
    "titulo": [('span', {'id': 'productTitle'}), ('h1', {'class': 'a-size-large'})],
    "imagem": [('img', {'id': 'landingImage'}), ('img', {'class': 'a-dynamic-image'})],
    "preco": [('span', {'class': 'a-price-whole'}), ('span', {'id': 'priceblock_ourprice'})],
    "avaliacao": [('span', {'id': 'acrPopover'}), ('i', {'class': 'a-icon-star'})],
    "num_avaliacoes": [('span', {'id': 'acrCustomerReviewText'})],
    "disponibilidade": [('div', {'id': 'availability'})],
    "marca": [('a', {'id': 'bylineInfo'})],
    "about_item": [('div', {'id': 'feature-bullets'})],
    "product_info": [('table', {'id': 'productDetails_detailBullets_sections1'})]
}

# Traduções expandidas
TRADUCOES = {
    'titulo_h1': 'Título',
    'url_imagem': 'URL da Imagem',
    'preco': 'Preço',
    'avaliacao': 'Avaliação',
    'num_avaliacoes': 'Número de Avaliações',
    'disponibilidade': 'Disponibilidade',
    'marca': 'Marca',
    'asin': 'ASIN',
    'about_item': 'Sobre este Item',
    'product_info': 'Informações do Produto',
    'data_coleta': 'Data da Coleta',
    'url_produto': 'URL do Produto',
    'In Stock': 'Em Estoque',
    'Out of Stock': 'Fora de Estoque',
    'Package Dimensions': 'Dimensões da Embalagem',
    'Item Weight': 'Peso do Item',
    'Item model number': 'Número do Modelo',
    'Batteries': 'Baterias',
    'Customer Reviews': 'Avaliações de Clientes',
    'Best Sellers Rank': 'Ranking de Mais Vendidos',
    'Date First Available': 'Data de Disponibilidade',
    'Manufacturer': 'Fabricante',
    'Standing screen display size': 'Tamanho da Tela',
    'Memory Storage Capacity': 'Capacidade de Armazenamento'
}

def obter_headers():
    import random
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
    }

def validar_url_amazon(url: str) -> bool:
    parsed = urlparse(url)
    dominios = ['amazon.com', 'amazon.com.br', 'amazon.co.uk']
    return any(d in parsed.netloc for d in dominios)

def extrair_texto(soup: BeautifulSoup, selectors: list) -> str:
    for tag, attrs in selectors:
        elemento = soup.find(tag, attrs)
        if elemento:
            texto = elemento.get_text(strip=True)
            if texto:
                return texto
    return "N/A"

def extrair_imagem(soup: BeautifulSoup) -> str:
    for tag, attrs in SELECTORS["imagem"]:
        elemento = soup.find(tag, attrs)
        if elemento:
            for attr in ['data-old-hires', 'src']:
                url = elemento.get(attr)
                if url and url.startswith('http'):
                    return url
    return "N/A"

def extrair_about_item(soup: BeautifulSoup) -> List[str]:
    """Extrai os bullets de 'About this item'"""
    items = []
    feature_bullets = soup.find('div', {'id': 'feature-bullets'})
    
    if feature_bullets:
        ul = feature_bullets.find('ul', {'class': 'a-unordered-list'})
        if ul:
            for li in ul.find_all('li'):
                span = li.find('span', {'class': 'a-list-item'})
                if span:
                    texto = span.get_text(strip=True)
                    if texto and len(texto) > 10:
                        items.append(texto)
    
    return items if items else ["N/A"]

def extrair_product_info(soup: BeautifulSoup) -> Dict[str, str]:
    """Extrai informações da tabela 'Product Information'"""
    info = {}
    
    # Procura a tabela de detalhes
    table = soup.find('table', {'id': 'productDetails_detailBullets_sections1'})
    
    if table:
        rows = table.find_all('tr')
        for row in rows:
            th = row.find('th')
            td = row.find('td')
            
            if th and td:
                chave = th.get_text(strip=True)
                valor = td.get_text(strip=True)
                
                # Limpa valores muito longos (como Customer Reviews com HTML)
                if len(valor) > 200:
                    # Tenta extrair apenas o texto relevante
                    simple_td = td.find(text=True, recursive=False)
                    if simple_td:
                        valor = simple_td.strip()
                
                if chave and valor and chave != 'Customer Reviews':
                    info[chave] = valor
    
    return info if info else {"N/A": "N/A"}

def extrair_asin(soup: BeautifulSoup, url: str) -> str:
    # Primeiro tenta da tabela de informações
    table = soup.find('table', {'id': 'productDetails_detailBullets_sections1'})
    if table:
        rows = table.find_all('tr')
        for row in rows:
            th = row.find('th')
            if th and 'ASIN' in th.get_text():
                td = row.find('td')
                if td:
                    return td.get_text(strip=True)
    
    # Fallback: extrai da URL
    asin_match = re.search(r'/dp/([A-Z0-9]{10})', url)
    if asin_match:
        return asin_match.group(1)
    return "N/A"

def traduzir_dados(dados: dict) -> dict:
    """Traduz dados usando dicionário estático"""
    dados_traduzidos = {}
    
    for chave, valor in dados.items():
        # Traduz a chave
        chave_trad = TRADUCOES.get(chave, chave.replace('_', ' ').title())
        
        # Traduz o valor
        if isinstance(valor, str):
            # Não traduz URLs, números
            if valor.startswith(('http', 'www', 'https')) or valor.replace('.', '').replace(',', '').isdigit():
                dados_traduzidos[chave_trad] = valor
            else:
                # Traduz palavras comuns
                valor_trad = valor
                for en, pt in TRADUCOES.items():
                    if en.lower() in valor.lower():
                        valor_trad = valor_trad.replace(en, pt)
                dados_traduzidos[chave_trad] = valor_trad
        elif isinstance(valor, list):
            # Traduz cada item da lista
            lista_trad = []
            for item in valor:
                if isinstance(item, str):
                    item_trad = item
                    for en, pt in TRADUCOES.items():
                        if en.lower() in item.lower():
                            item_trad = item_trad.replace(en, pt)
                    lista_trad.append(item_trad)
                else:
                    lista_trad.append(item)
            dados_traduzidos[chave_trad] = lista_trad
        elif isinstance(valor, dict):
            # Traduz dicionário recursivamente
            dict_trad = {}
            for sub_chave, sub_valor in valor.items():
                sub_chave_trad = TRADUCOES.get(sub_chave, sub_chave)
                dict_trad[sub_chave_trad] = sub_valor
            dados_traduzidos[chave_trad] = dict_trad
        else:
            dados_traduzidos[chave_trad] = valor
    
    return dados_traduzidos

def coletar_dados_produto(url: str) -> dict:
    if not validar_url_amazon(url):
        return {"erro": "URL não é da Amazon válida"}
    
    time.sleep(2)
    
    try:
        response = requests.get(url, headers=obter_headers(), timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        if 'To discuss automated access' in response.text:
            return {"erro": "Amazon bloqueou a requisição. Use VPN ou aguarde."}
        
        dados = {
            "titulo_h1": extrair_texto(soup, SELECTORS["titulo"]),
            "url_imagem": extrair_imagem(soup),
            "preco": extrair_texto(soup, SELECTORS["preco"]),
            "avaliacao": extrair_texto(soup, SELECTORS["avaliacao"]),
            "num_avaliacoes": extrair_texto(soup, SELECTORS["num_avaliacoes"]),
            "disponibilidade": extrair_texto(soup, SELECTORS["disponibilidade"]),
            "marca": extrair_texto(soup, SELECTORS["marca"]),
            "about_item": extrair_about_item(soup),
            "product_info": extrair_product_info(soup),
            "asin": extrair_asin(soup, url),
            "url_produto": url,
            "data_coleta": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return dados
        
    except Exception as e:
        return {"erro": f"Erro: {str(e)}"}

def gerar_csv(dados: dict) -> str:
    output = io.StringIO()
    
    # Achata dados complexos
    dados_flat = {}
    for chave, valor in dados.items():
        if isinstance(valor, list):
            dados_flat[chave] = ' | '.join(str(v) for v in valor)
        elif isinstance(valor, dict):
            # Converte dict para string formatada
            dados_flat[chave] = json.dumps(valor, ensure_ascii=False)
        else:
            dados_flat[chave] = valor
    
    writer = csv.DictWriter(output, fieldnames=dados_flat.keys())
    writer.writeheader()
    writer.writerow(dados_flat)
    return output.getvalue()

def gerar_json(dados: dict) -> str:
    return json.dumps(dados, ensure_ascii=False, indent=2)

# Interface Streamlit
def main():
    st.set_page_config(page_title="Amazon Scraper Pro", page_icon="🛒", layout="wide")
    
    st.title("🛒 Amazon Product Scraper Pro")
    st.markdown("**Extraia dados completos de produtos da Amazon**")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configurações")
        traducao = st.checkbox("🌐 Traduzir para Português", value=True)
        
        st.markdown("---")
        st.subheader("📚 Dicas de Tradução")
        
        with st.expander("💡 Como usar tradução gratuita"):
            st.markdown("""
            **Opções de Tradução Gratuita:**
            
            **1. Extensão do Navegador (Mais Fácil)**
            - Google Translate Extension
            - Microsoft Translator
            - Traduz a página inteira automaticamente
            
            **2. API Gratuita - LibreTranslate**
            ```bash
            # Instalar
            pip install libretranslate
            
            # Rodar servidor local
            libretranslate --port 5000
            ```
            
            **3. Deep Translator (Offline)**
            ```bash
            pip install deep-translator
            ```
            
            **4. Argos Translate (100% Offline)**
            ```bash
            pip install argostranslate
            ```
            """)
        
        st.markdown("---")
        st.info("💡 **Dica:** Use extensão do navegador para tradução instantânea!")
    
    # Input
    url_input = st.text_input(
        "🔗 Cole a URL do produto:",
        placeholder="https://www.amazon.com/dp/B08N5WRWNW"
    )
    
    if st.button("🚀 Coletar Dados", type="primary"):
        if not url_input:
            st.warning("⚠️ Por favor, insira uma URL")
        elif not validar_url_amazon(url_input):
            st.error("❌ URL inválida! Use uma URL da Amazon")
        else:
            with st.spinner("🔍 Coletando dados..."):
                dados = coletar_dados_produto(url_input)
                
                if 'erro' in dados:
                    st.error(f"❌ {dados['erro']}")
                else:
                    if traducao:
                        dados = traduzir_dados(dados)
                    
                    st.success("✅ Dados coletados com sucesso!")
                    
                    # Métricas
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("💰 Preço", dados.get('Preço' if traducao else 'preco', 'N/A'))
                    with col2:
                        st.metric("⭐ Avaliação", dados.get('Avaliação' if traducao else 'avaliacao', 'N/A'))
                    with col3:
                        st.metric("📦 Disponibilidade", 
                                 dados.get('Disponibilidade' if traducao else 'disponibilidade', 'N/A')[:20])
                    
                    st.markdown("---")
                    
                    # Layout em duas colunas
                    col1, col2 = st.columns([1, 1])
                    
                    with col1:
                        st.subheader("ℹ️ Informações Básicas")
                        
                        # Informações principais
                        info_basica = ['Título', 'Preço', 'Marca', 'ASIN', 'Avaliação', 
                                      'Número de Avaliações', 'Disponibilidade']
                        if not traducao:
                            info_basica = ['titulo_h1', 'preco', 'marca', 'asin', 
                                          'avaliacao', 'num_avaliacoes', 'disponibilidade']
                        
                        for campo in info_basica:
                            if campo in dados and dados[campo] != 'N/A':
                                st.write(f"**{campo}:** {dados[campo]}")
                        
                        # About this item
                        st.markdown("---")
                        st.subheader("📝 Sobre este Item")
                        about = dados.get('Sobre este Item' if traducao else 'about_item', [])
                        if isinstance(about, list) and about != ['N/A']:
                            for idx, item in enumerate(about, 1):
                                st.write(f"{idx}. {item}")
                        else:
                            st.info("Não disponível")
                    
                    with col2:
                        st.subheader("🖼️ Imagem do Produto")
                        img_url = dados.get('URL da Imagem' if traducao else 'url_imagem', 'N/A')
                        if img_url != 'N/A':
                            try:
                                st.image(img_url, width=400, caption="Produto")
                            except:
                                st.info("Imagem não pôde ser carregada")
                        else:
                            st.info("Imagem não disponível")
                        
                        # Product Information
                        st.markdown("---")
                        st.subheader("🔧 Informações do Produto")
                        product_info = dados.get('Informações do Produto' if traducao else 'product_info', {})
                        
                        if isinstance(product_info, dict) and product_info != {"N/A": "N/A"}:
                            # Cria DataFrame para exibição mais limpa
                            df_info = pd.DataFrame(
                                list(product_info.items()),
                                columns=['Especificação', 'Valor']
                            )
                            st.dataframe(df_info, use_container_width=True, hide_index=True)
                        else:
                            st.info("Não disponível")
                    
                    # Downloads
                    st.markdown("---")
                    st.subheader("📥 Exportar Dados")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        csv_data = gerar_csv(dados)
                        st.download_button(
                            label="📄 Baixar CSV",
                            data=csv_data,
                            file_name=f"produto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    
                    with col2:
                        json_data = gerar_json(dados)
                        st.download_button(
                            label="📋 Baixar JSON",
                            data=json_data,
                            file_name=f"produto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json",
                            use_container_width=True
                        )
                    
                    with col3:
                        try:
                            # Excel
                            dados_flat = {}
                            for chave, valor in dados.items():
                                if isinstance(valor, list):
                                    dados_flat[chave] = '\n'.join(str(v) for v in valor)
                                elif isinstance(valor, dict):
                                    dados_flat[chave] = json.dumps(valor, ensure_ascii=False)
                                else:
                                    dados_flat[chave] = valor
                            
                            df = pd.DataFrame([dados_flat])
                            excel_buffer = io.BytesIO()
                            df.to_excel(excel_buffer, index=False, engine='openpyxl')
                            excel_data = excel_buffer.getvalue()
                            
                            st.download_button(
                                label="📊 Baixar Excel",
                                data=excel_data,
                                file_name=f"produto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                        except:
                            st.info("Excel: pip install openpyxl")
    
    # Footer com instruções
    st.markdown("---")
    with st.expander("📖 Como implementar tradução automática gratuita"):
        st.markdown("""
        ### 🌐 Opções de Tradução Gratuita
        
        #### **1. LibreTranslate (API Local - Melhor opção)**
        
        **Instalação:**
        ```bash
        pip install libretranslate
        ```
        
        **Rodar servidor:**
        ```bash
        libretranslate --host 0.0.0.0 --port 5000
        ```
        
        **Usar no código:**
        ```python
        import requests
        
        def traduzir_libretranslate(texto):
            response = requests.post(
                "http://localhost:5000/translate",
                json={
                    "q": texto,
                    "source": "en",
                    "target": "pt"
                }
            )
            return response.json()["translatedText"]
        ```
        
        ---
        
        #### **2. Deep Translator (Sem servidor)**
        
        ```bash
        pip install deep-translator
        ```
        
        ```python
        from deep_translator import GoogleTranslator
        
        translator = GoogleTranslator(source='en', target='pt')
        texto_traduzido = translator.translate("Hello World")
        ```
        
        ---
        
        #### **3. Argos Translate (100% Offline)**
        
        ```bash
        pip install argostranslate
        ```
        
        ```python
        import argostranslate.package
        import argostranslate.translate
        
        # Baixa pacote (apenas uma vez)
        argostranslate.package.update_package_index()
        available = argostranslate.package.get_available_packages()
        package = list(filter(
            lambda x: x.from_code == "en" and x.to_code == "pt", 
            available
        ))[0]
        argostranslate.package.install_from_path(package.download())
        
        # Traduz
        texto_traduzido = argostranslate.translate.translate("Hello", "en", "pt")
        ```
        
        ---
        
        ### 🎯 Recomendação
        
        Para este app, a **melhor solução** é:
        1. Use **extensão do navegador** (mais simples)
        2. Ou implemente **LibreTranslate** local
        3. Ou use **Deep Translator** (Google Translate não oficial)
        """)

if __name__ == "__main__":
    main()