import requests
from bs4 import BeautifulSoup
from typing import Union
from pathlib import Path
import logging
import csv
from urllib.parse import urlparse
import time
import io
import streamlit as st

# Importação para tradução (com check melhorado)
try:
    from googletrans import Translator
    translator = Translator()  # Inicializa aqui para evitar erro
except ImportError:
    st.error("❌ Biblioteca 'googletrans' não encontrada! Instale com: pip install googletrans==3.1.0a0")
    st.stop()

# Configuração de logging (desativada para evitar spam no Streamlit)
logging.basicConfig(level=logging.WARNING)

# Cabeçalhos HTTP
HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/91.0.4472.124 Safari/537.36'
    ),
    'Accept-Language': 'pt-BR,en;q=0.9'  # Para português
}

# SELECTORS (mantidos)
SELECTORS = {
    "titulo": [('span', {'id': 'productTitle'}), ('h1', {'class': 'a-size-large'})],
    "imagem": [('img', {'id': 'landingImage'}), ('img', {'class': 'a-dynamic-image'})],
    "features": [('div', {'id': 'feature-bullets'}), ('div', {'class': 'feature'})],
    "lista": [('ul', {'class': 'a-unordered-list'})],
    "item": [('li', {'class': 'a-spacing-mini'})],
    "span_item": [('span', {'class': 'a-list-item'})],
    "preco": [('span', {'id': 'priceblock_ourprice'}), ('span', {'id': 'priceblock_dealprice'}),
              ('span', {'class': 'a-price-whole'}), ('span', {'class': 'a-color-price'}),
              ('span', {'id': 'tp_price_block_total_price_ww'})],
    "avaliacao": [('span', {'id': 'acrPopover'}), ('a', {'href': '#customerReviews'})],
    "num_avaliacoes": [('span', {'id': 'acrCustomerReviewText'})],
    "disponibilidade": [('div', {'id': 'availability'}), ('span', {'class': 'a-size-medium a-color-success'}),
                        ('span', {'id': 'availability_string'})],
    "categoria": [('a', {'class': 'a-link-normal a-color-tertiary'})],
    "marca": [('a', {'id': 'bylineInfo'}), ('span', {'class': 'author'})],
    "asin": [('table', {'id': 'productDetails_detailBullets_sections1'})],
    "peso": [('table', {'id': 'productDetails_detailBullets_sections1'})]
}

# Função de tradução
def traduzir_dados(dados: dict, destino: str = 'pt') -> dict:
    dados_traduzidos = {}
    for chave, valor in dados.items():
        chave_traduzida = translator.translate(chave.replace('_', ' '), dest=destino).text.capitalize() if isinstance(chave, str) else chave
        
        if isinstance(valor, str):
            if valor.startswith(('http', 'www', 'https')) or any(char.isdigit() for char in valor.split()) or 'pt' in destino.lower():
                dados_traduzidos[chave_traduzida] = valor
            else:
                try:
                    dados_traduzidos[chave_traduzida] = translator.translate(valor, dest=destino).text
                except Exception as e:
                    dados_traduzidos[chave_traduzida] = valor
        elif isinstance(valor, list):
            dados_traduzidos[chave_traduzida] = [translator.translate(item, dest=destino).text if isinstance(item, str) else item for item in valor]
        elif isinstance(valor, dict):
            dados_traduzidos[chave_traduzida] = traduzir_dados(valor, destino)
        else:
            dados_traduzidos[chave_traduzida] = valor
    return dados_traduzidos

# Função de coleta (mantida)
def coletar_dados_produto(url: str) -> dict:
    time.sleep(3)
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        return {
            "titulo_h1": extrair_texto(soup, SELECTORS["titulo"]),
            "url_imagem": extrair_imagem(soup),
            "preco": extrair_texto(soup, SELECTORS["preco"]),
            "avaliacao": extrair_avaliacao(soup),
            "num_avaliacoes": extrair_num_avaliacoes(soup),
            "disponibilidade": extrair_disponibilidade(soup),
            "categoria": extrair_categoria(soup),
            "marca": extrair_texto(soup, SELECTORS["marca"]),
            "sobre_o_produto": extrair_descricao(soup),
            "detalhes_tecnicos": extrair_detalhes_tecnicos(soup),
            "asin": extrair_asin(soup),
            "peso": extrair_peso(soup)
        }

    except requests.exceptions.RequestException as e:
        return {"erro": f"Erro de requisição: {e}"}
    except Exception as e:
        return {"erro": f"Um erro inesperado ocorreu: {e}"}

# ... (restante das funções auxiliares, iguais)

# Interface Streamlit
st.title("🌐 Amazon Product Scraper com Tradução")
st.markdown("Cole uma URL de produto da Amazon e extraia/traduza dados para português!")

traducao_ativa = st.checkbox("Ativar tradução para português", value=True)

url_input = st.text_input("Digite a URL do produto Amazon:", placeholder="https://www.amazon.com/...")

if st.button("Coletar e Traduzir Dados" if traducao_ativa else "Coletar Dados"):
    if url_input:
        with st.spinner("Coletando dados... Isso pode levar alguns segundos!"):
            dados = coletar_dados_produto(url_input)
        
        if 'erro' in dados:
            st.error(f"Falha ao coletar dados: {dados['erro']}")
        else:
            st.success("✅ Dados coletados com sucesso!")
            
            if traducao_ativa:
                with st.spinner("Traduzindo para português..."):
                    dados = traduzir_dados(dados, 'pt')
            
            st.subheader("Dados Extraídos (Traduzidos se ativado):")
            for chave, valor in dados.items():
                if isinstance(valor, dict):
                    st.write(f"**{chave}:**")
                    st.json(valor)
                elif isinstance(valor, list):
                    st.write(f"**{chave}:**")
                    for item in valor:
                        st.write(f"- {item}")
                else:
                    st.write(f"**{chave}:** {valor}")
            
            csv_data = gerar_csv(dados)
            st.download_button(
                label="📥 Baixar CSV (Traduzido)",
                data=csv_data,
                file_name="produto_amazon_traduzido.csv",
                mime="text/csv",
                key="download_csv"
            )
    else:
        st.warning("Por favor, digite uma URL válida.")

st.markdown("---")
st.caption("Desenvolvido para fins educacionais. Use VPN para evitar bloqueios.")