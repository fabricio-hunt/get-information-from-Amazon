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

# Seletores
SELECTORS = {
    "titulo": [('span', {'id': 'productTitle'}), ('h1', {'class': 'a-size-large'})],
    "imagem": [('img', {'id': 'landingImage'}), ('img', {'class': 'a-dynamic-image'})],
    "preco": [('span', {'class': 'a-price-whole'}), ('span', {'id': 'priceblock_ourprice'})],
    "avaliacao": [('span', {'id': 'acrPopover'}), ('i', {'class': 'a-icon-star'})],
    "num_avaliacoes": [('span', {'id': 'acrCustomerReviewText'})],
    "disponibilidade": [('div', {'id': 'availability'})],
    "marca": [('a', {'id': 'bylineInfo'})]
}

# Traduções
TRADUCOES = {
    'titulo_h1': 'Título', 'url_imagem': 'URL da Imagem', 'preco': 'Preço',
    'avaliacao': 'Avaliação', 'num_avaliacoes': 'Número de Avaliações',
    'disponibilidade': 'Disponibilidade', 'marca': 'Marca',
    'asin': 'ASIN', 'data_coleta': 'Data da Coleta', 'url_produto': 'URL do Produto',
    'In Stock': 'Em Estoque', 'Out of Stock': 'Fora de Estoque'
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

def extrair_asin(soup: BeautifulSoup, url: str) -> str:
    asin_match = re.search(r'/dp/([A-Z0-9]{10})', url)
    if asin_match:
        return asin_match.group(1)
    return "N/A"

def traduzir_dados(dados: dict) -> dict:
    dados_traduzidos = {}
    for chave, valor in dados.items():
        chave_trad = TRADUCOES.get(chave, chave.replace('_', ' ').title())
        if isinstance(valor, str):
            dados_traduzidos[chave_trad] = valor
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
            return {"erro": "Amazon bloqueou a requisição. Use VPN."}
        
        dados = {
            "titulo_h1": extrair_texto(soup, SELECTORS["titulo"]),
            "url_imagem": extrair_imagem(soup),
            "preco": extrair_texto(soup, SELECTORS["preco"]),
            "avaliacao": extrair_texto(soup, SELECTORS["avaliacao"]),
            "num_avaliacoes": extrair_texto(soup, SELECTORS["num_avaliacoes"]),
            "disponibilidade": extrair_texto(soup, SELECTORS["disponibilidade"]),
            "marca": extrair_texto(soup, SELECTORS["marca"]),
            "asin": extrair_asin(soup, url),
            "url_produto": url,
            "data_coleta": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return dados
        
    except Exception as e:
        return {"erro": f"Erro: {str(e)}"}

def gerar_csv(dados: dict) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=dados.keys())
    writer.writeheader()
    writer.writerow(dados)
    return output.getvalue()

def gerar_json(dados: dict) -> str:
    return json.dumps(dados, ensure_ascii=False, indent=2)

# Interface Streamlit
def main():
    st.set_page_config(page_title="Amazon Scraper", page_icon="🛒", layout="wide")
    
    st.title("🛒 Amazon Product Scraper")
    st.markdown("**Extraia dados de produtos da Amazon**")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configurações")
        traducao = st.checkbox("🌐 Traduzir para Português", value=True)
        
        st.markdown("---")
        st.info("💡 **Dica:** Use VPN se a Amazon bloquear")
    
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
                    
                    st.success("✅ Dados coletados!")
                    
                    # Métricas
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("💰 Preço", dados.get('Preço' if traducao else 'preco', 'N/A'))
                    with col2:
                        st.metric("⭐ Avaliação", dados.get('Avaliação' if traducao else 'avaliacao', 'N/A'))
                    with col3:
                        st.metric("📦 Disponibilidade", 
                                 dados.get('Disponibilidade' if traducao else 'disponibilidade', 'N/A')[:15])
                    
                    st.markdown("---")
                    
                    # Dados detalhados
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("ℹ️ Informações")
                        for chave, valor in dados.items():
                            if chave not in ['URL da Imagem', 'url_imagem']:
                                st.write(f"**{chave}:** {valor}")
                    
                    with col2:
                        st.subheader("🖼️ Imagem do Produto")
                        img_url = dados.get('URL da Imagem' if traducao else 'url_imagem', 'N/A')
                        if img_url != 'N/A':
                            st.image(img_url, width=300)
                        else:
                            st.info("Imagem não disponível")
                    
                    # Downloads
                    st.markdown("---")
                    st.subheader("📥 Exportar Dados")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        csv_data = gerar_csv(dados)
                        st.download_button(
                            label="📄 Baixar CSV",
                            data=csv_data,
                            file_name=f"produto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    
                    with col2:
                        json_data = gerar_json(dados)
                        st.download_button(
                            label="📋 Baixar JSON",
                            data=json_data,
                            file_name=f"produto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json"
                        )

if __name__ == "__main__":
    main()