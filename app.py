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

logging.basicConfig(level=logging.WARNING)

# Importação do Deep Translator
try:
    from deep_translator import GoogleTranslator
    TRADUTOR_DISPONIVEL = True
except ImportError:
    TRADUTOR_DISPONIVEL = False

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]

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

TRADUCOES_MANUAIS = {
    'titulo_h1': 'Título', 'url_imagem': 'URL da Imagem', 'preco': 'Preço',
    'avaliacao': 'Avaliação', 'num_avaliacoes': 'Número de Avaliações',
    'disponibilidade': 'Disponibilidade', 'marca': 'Marca', 'asin': 'ASIN',
    'about_item': 'Sobre este Item', 'product_info': 'Informações do Produto',
    'data_coleta': 'Data da Coleta', 'url_produto': 'URL do Produto',
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

def traduzir_texto(texto: str) -> str:
    """Traduz texto usando Deep Translator"""
    if not TRADUTOR_DISPONIVEL or not texto or texto == "N/A":
        return texto
    
    # Não traduz URLs, números, etc
    if texto.startswith(('http', 'www', 'https', '$', 'R$')):
        return texto
    
    if len(texto) < 3:
        return texto
    
    try:
        translator = GoogleTranslator(source='en', target='pt')
        
        # Limite de 5000 caracteres
        if len(texto) > 4500:
            # Traduz por partes
            partes = []
            palavras = texto.split('. ')
            parte_atual = ""
            
            for frase in palavras:
                if len(parte_atual) + len(frase) < 4000:
                    parte_atual += frase + ". "
                else:
                    partes.append(translator.translate(parte_atual.strip()))
                    parte_atual = frase + ". "
            
            if parte_atual:
                partes.append(translator.translate(parte_atual.strip()))
            
            return ' '.join(partes)
        else:
            return translator.translate(texto)
    except Exception as e:
        return texto

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
    """Extrai bullets de 'About this item'"""
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
    """Extrai tabela 'Product Information'"""
    info = {}
    table = soup.find('table', {'id': 'productDetails_detailBullets_sections1'})
    
    if table:
        rows = table.find_all('tr')
        for row in rows:
            th = row.find('th')
            td = row.find('td')
            
            if th and td:
                chave = th.get_text(strip=True)
                valor = td.get_text(strip=True)
                
                if len(valor) > 200:
                    simple_td = td.find(text=True, recursive=False)
                    if simple_td:
                        valor = simple_td.strip()
                
                if chave and valor and chave != 'Customer Reviews':
                    info[chave] = valor
    
    return info if info else {"N/A": "N/A"}

def extrair_asin(soup: BeautifulSoup, url: str) -> str:
    table = soup.find('table', {'id': 'productDetails_detailBullets_sections1'})
    if table:
        rows = table.find_all('tr')
        for row in rows:
            th = row.find('th')
            if th and 'ASIN' in th.get_text():
                td = row.find('td')
                if td:
                    return td.get_text(strip=True)
    
    asin_match = re.search(r'/dp/([A-Z0-9]{10})', url)
    if asin_match:
        return asin_match.group(1)
    return "N/A"

def traduzir_dados(dados: dict, progress_bar=None) -> dict:
    """Traduz todos os dados usando Deep Translator"""
    dados_traduzidos = {}
    total_campos = len(dados)
    
    for idx, (chave, valor) in enumerate(dados.items()):
        # Atualiza progress bar
        if progress_bar:
            progress_bar.progress((idx + 1) / total_campos)
        
        # Traduz chave
        chave_trad = TRADUCOES_MANUAIS.get(chave, traduzir_texto(chave.replace('_', ' ').title()))
        
        # Traduz valor
        if isinstance(valor, str):
            if valor.startswith(('http', 'www', 'https')) or valor == "N/A":
                dados_traduzidos[chave_trad] = valor
            else:
                dados_traduzidos[chave_trad] = traduzir_texto(valor)
        
        elif isinstance(valor, list):
            lista_trad = []
            for item in valor:
                if isinstance(item, str) and item != "N/A":
                    lista_trad.append(traduzir_texto(item))
                else:
                    lista_trad.append(item)
            dados_traduzidos[chave_trad] = lista_trad
        
        elif isinstance(valor, dict):
            dict_trad = {}
            for sub_chave, sub_valor in valor.items():
                if sub_chave != "N/A":
                    sub_chave_trad = traduzir_texto(sub_chave)
                    dict_trad[sub_chave_trad] = sub_valor
                else:
                    dict_trad[sub_chave] = sub_valor
            dados_traduzidos[chave_trad] = dict_trad
        
        else:
            dados_traduzidos[chave_trad] = valor
        
        # Pequeno delay para evitar sobrecarga
        time.sleep(0.1)
    
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
    dados_flat = {}
    for chave, valor in dados.items():
        if isinstance(valor, list):
            dados_flat[chave] = ' | '.join(str(v) for v in valor)
        elif isinstance(valor, dict):
            dados_flat[chave] = json.dumps(valor, ensure_ascii=False)
        else:
            dados_flat[chave] = valor
    
    writer = csv.DictWriter(output, fieldnames=dados_flat.keys())
    writer.writeheader()
    writer.writerow(dados_flat)
    return output.getvalue()

def gerar_json(dados: dict) -> str:
    return json.dumps(dados, ensure_ascii=False, indent=2)

def main():
    st.set_page_config(page_title="Amazon Scraper Pro", page_icon="🛒", layout="wide")
    
    st.title("🛒 Amazon Product Scraper Pro")
    st.markdown("**Extraia dados completos de produtos da Amazon com tradução automática**")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configurações")
        
        if TRADUTOR_DISPONIVEL:
            traducao = st.checkbox("🌐 Traduzir para PT-BR (Deep Translator)", value=True)
            st.success("✅ Deep Translator instalado!")
        else:
            traducao = False
            st.error("❌ Deep Translator não instalado")
            st.code("pip install deep-translator", language="bash")
        
        st.markdown("---")
        st.info("💡 **Dica:** A tradução automática pode levar alguns segundos extras")
    
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
            with st.spinner("🔍 Coletando dados da Amazon..."):
                dados = coletar_dados_produto(url_input)
                
                if 'erro' in dados:
                    st.error(f"❌ {dados['erro']}")
                else:
                    st.success("✅ Dados coletados!")
                    
                    # Tradução
                    if traducao and TRADUTOR_DISPONIVEL:
                        with st.spinner("🌐 Traduzindo para português brasileiro..."):
                            progress_bar = st.progress(0)
                            dados = traduzir_dados(dados, progress_bar)
                            progress_bar.empty()
                            st.success("✅ Tradução concluída!")
                    
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
                    
                    # Layout
                    col1, col2 = st.columns([1, 1])
                    
                    with col1:
                        st.subheader("ℹ️ Informações Básicas")
                        
                        info_basica = ['Título', 'Preço', 'Marca', 'ASIN', 'Avaliação', 
                                      'Número de Avaliações', 'Disponibilidade']
                        if not traducao:
                            info_basica = ['titulo_h1', 'preco', 'marca', 'asin', 
                                          'avaliacao', 'num_avaliacoes', 'disponibilidade']
                        
                        for campo in info_basica:
                            if campo in dados and dados[campo] != 'N/A':
                                st.write(f"**{campo}:** {dados[campo]}")
                        
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
                        
                        st.markdown("---")
                        st.subheader("🔧 Informações do Produto")
                        product_info = dados.get('Informações do Produto' if traducao else 'product_info', {})
                        
                        if isinstance(product_info, dict) and product_info != {"N/A": "N/A"}:
                            df_info = pd.DataFrame(
                                list(product_info.items()),
                                columns=['Especificação', 'Valor']
                            )
                            st.dataframe(df_info, use_container_width=True, hide_index=True)
                        else:
                            st.info("Não disponível")
                    
                    # Downloads
                    st.markdown("---")
                    st.subheader("📥 Exportar Dados em PT-BR")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        csv_data = gerar_csv(dados)
                        st.download_button(
                            label="📄 Baixar CSV",
                            data=csv_data,
                            file_name=f"produto_ptbr_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    
                    with col2:
                        json_data = gerar_json(dados)
                        st.download_button(
                            label="📋 Baixar JSON",
                            data=json_data,
                            file_name=f"produto_ptbr_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json",
                            use_container_width=True
                        )
                    
                    with col3:
                        try:
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
                                file_name=f"produto_ptbr_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                        except:
                            st.info("Excel: pip install openpyxl")

if __name__ == "__main__":
    main()