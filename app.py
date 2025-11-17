import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import logging
import csv
import json
from urllib.parse import urlparse, urlunparse
import time
import io
import streamlit as st
from datetime import datetime 
import pandas as pd
import re
import random

logging.basicConfig(level=logging.WARNING)

# Importações de tradução
try:
    from deep_translator import GoogleTranslator
    TRADUTOR_DISPONIVEL = True
except ImportError:
    TRADUTOR_DISPONIVEL = False

try:
    from translate import Translator as LibreTranslator
    LIBRE_DISPONIVEL = True
except ImportError:
    LIBRE_DISPONIVEL = False

try:
    import google.generativeai as genai
    GEMINI_DISPONIVEL = True
except ImportError:
    GEMINI_DISPONIVEL = False

# User Agents mais diversos e recentes
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0'
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
    'technical_details': 'Detalhes Técnicos', 'data_coleta': 'Data da Coleta',
    'url_produto': 'URL do Produto',
}

# Tabelas de conversão
CONVERSAO_MEDIDAS = {
    # Comprimento
    'inch': {'para': 'cm', 'multiplicador': 2.54},
    'inches': {'para': 'cm', 'multiplicador': 2.54},
    'in': {'para': 'cm', 'multiplicador': 2.54},
    'ft': {'para': 'm', 'multiplicador': 0.3048},
    'feet': {'para': 'm', 'multiplicador': 0.3048},
    'foot': {'para': 'm', 'multiplicador': 0.3048},
    'yard': {'para': 'm', 'multiplicador': 0.9144},
    'yd': {'para': 'm', 'multiplicador': 0.9144},
    
    # Peso
    'lb': {'para': 'kg', 'multiplicador': 0.453592},
    'lbs': {'para': 'kg', 'multiplicador': 0.453592},
    'pound': {'para': 'kg', 'multiplicador': 0.453592},
    'pounds': {'para': 'kg', 'multiplicador': 0.453592},
    'oz': {'para': 'g', 'multiplicador': 28.3495},
    'ounce': {'para': 'g', 'multiplicador': 28.3495},
    'ounces': {'para': 'g', 'multiplicador': 28.3495},
    
    # Volume
    'gallon': {'para': 'L', 'multiplicador': 3.78541},
    'gal': {'para': 'L', 'multiplicador': 3.78541},
    'fl oz': {'para': 'ml', 'multiplicador': 29.5735},
    'fluid ounce': {'para': 'ml', 'multiplicador': 29.5735},
    'quart': {'para': 'L', 'multiplicador': 0.946353},
    'qt': {'para': 'L', 'multiplicador': 0.946353},
    'pint': {'para': 'ml', 'multiplicador': 473.176},
    'pt': {'para': 'ml', 'multiplicador': 473.176},
}

# Conversão de tamanhos de roupa
CONVERSAO_TAMANHOS = {
    'XXS': 'PP', 'XS': 'P', 'S': 'M', 'M': 'G', 'L': 'GG', 'XL': 'XG', 
    '2XL': 'XXG', '3XL': 'XXXG', '4XL': 'XXXXG'
}

def converter_medidas(texto: str) -> str:
    """Converte medidas americanas para brasileiras"""
    if not texto or texto == "N/A":
        return texto
    
    texto_convertido = texto
    
    # Padrão para encontrar números seguidos de unidades
    padrao = r'(\d+\.?\d*)\s*([a-zA-Z]+)'
    
    def substituir_medida(match):
        numero = float(match.group(1))
        unidade = match.group(2).lower()
        
        if unidade in CONVERSAO_MEDIDAS:
            conversao = CONVERSAO_MEDIDAS[unidade]
            valor_convertido = numero * conversao['multiplicador']
            unidade_brasileira = conversao['para']
            
            # Arredonda para 2 casas decimais
            valor_convertido = round(valor_convertido, 2)
            
            return f"{match.group(0)} ({valor_convertido} {unidade_brasileira})"
        
        return match.group(0)
    
    texto_convertido = re.sub(padrao, substituir_medida, texto_convertido)
    
    # Converte tamanhos de roupa
    for tamanho_us, tamanho_br in CONVERSAO_TAMANHOS.items():
        # Procura por tamanhos isolados ou entre espaços
        texto_convertido = re.sub(
            rf'\b{tamanho_us}\b',
            f"{tamanho_us} (Tam. BR: {tamanho_br})",
            texto_convertido,
            flags=re.IGNORECASE
        )
    
    return texto_convertido

def limpar_url_amazon(url: str) -> str:
    """Remove parâmetros desnecessários da URL"""
    parsed = urlparse(url)
    clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
    return clean_url

def obter_headers():
    """Gera headers mais realistas para evitar bloqueios"""
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0',
    }

def validar_url_amazon(url: str) -> bool:
    parsed = urlparse(url)
    dominios = ['amazon.com', 'amazon.com.br', 'amazon.co.uk']
    return any(d in parsed.netloc for d in dominios)

def traduzir_com_mymemory(texto: str) -> str:
    """Traduz usando MyMemory API (gratuita, sem necessidade de chave)"""
    if not texto or texto == "N/A" or len(texto) < 3:
        return texto
    
    if texto.startswith(('http', 'www', 'https', '$', 'R$')):
        return texto
    
    try:
        # MyMemory API - gratuita, 1000 palavras/dia sem chave
        url = "https://api.mymemory.translated.net/get"
        params = {
            'q': texto[:500],  # Limita para não exceder
            'langpair': 'en|pt-br'
        }
        
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('responseStatus') == 200:
                return data['responseData']['translatedText']
    except Exception as e:
        logging.warning(f"MyMemory falhou: {e}")
    
    return texto

def traduzir_com_libre(texto: str) -> str:
    """Traduz usando translate library (fallback)"""
    if not LIBRE_DISPONIVEL or not texto or texto == "N/A":
        return texto
    
    if texto.startswith(('http', 'www', 'https', '$', 'R$')):
        return texto
    
    try:
        translator = LibreTranslator(from_lang="en", to_lang="pt")
        return translator.translate(texto[:500])
    except Exception as e:
        logging.warning(f"Libre Translate falhou: {e}")
        return texto

def traduzir_com_gemini(texto: str, gemini_key: str = None) -> str:
    """Traduz texto usando Gemini API para melhor qualidade"""
    if not GEMINI_DISPONIVEL or not gemini_key:
        return traduzir_texto(texto)
    
    if not texto or texto == "N/A":
        return texto
    
    if texto.startswith(('http', 'www', 'https', '$', 'R$')):
        return texto
    
    try:
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""Traduza o seguinte texto de produto do inglês para português brasileiro de forma natural e fluida.
Mantenha termos técnicos quando apropriado. Não adicione explicações, apenas retorne a tradução.

Texto: {texto}

Tradução:"""
        
        response = model.generate_content(prompt)
        return response.text.strip()
        
    except Exception as e:
        logging.warning(f"Gemini falhou: {e}")
        return traduzir_texto(texto)

def traduzir_texto(texto: str, metodo: str = "auto") -> str:
    """Traduz texto tentando múltiplos métodos (cascata de fallback)"""
    if not texto or texto == "N/A" or len(texto) < 3:
        return texto
    
    if texto.startswith(('http', 'www', 'https', '$', 'R$')):
        return texto
    
    # Tenta MyMemory primeiro (mais confiável e gratuito)
    resultado = traduzir_com_mymemory(texto)
    if resultado != texto:
        return resultado
    
    # Fallback para Libre Translate
    if LIBRE_DISPONIVEL:
        resultado = traduzir_com_libre(texto)
        if resultado != texto:
            return resultado
    
    # Fallback para Deep Translator
    if TRADUTOR_DISPONIVEL:
        try:
            translator = GoogleTranslator(source='en', target='pt')
            if len(texto) > 4500:
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
            logging.warning(f"Deep Translator falhou: {e}")
    
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

def extrair_technical_details(soup: BeautifulSoup) -> Dict[str, str]:
    """Extrai todos os detalhes técnicos (Summary e Other Technical Details)"""
    technical_info = {}
    
    tables = soup.find_all('table', class_='prodDetTable')
    
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            th = row.find('th', class_='prodDetSectionEntry')
            td = row.find('td', class_='prodDetAttrValue')
            
            if th and td:
                chave = th.get_text(strip=True)
                valor = td.get_text(strip=True)
                
                if chave and valor:
                    technical_info[chave] = valor
    
    return technical_info if technical_info else {"N/A": "N/A"}

def extrair_product_info(soup: BeautifulSoup) -> Dict[str, str]:
    """Extrai tabela 'Product Information' e 'Additional Information'"""
    info = {}
    
    table_ids = [
        'productDetails_detailBullets_sections1',
        'productDetails_techSpec_section_1',
        'productDetails_techSpec_section_2'
    ]
    
    for table_id in table_ids:
        table = soup.find('table', {'id': table_id})
        
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

def traduzir_e_converter_dados(dados: dict, usar_gemini: bool = False, gemini_key: str = None, progress_bar=None) -> dict:
    """Traduz e converte medidas de todos os dados"""
    dados_traduzidos = {}
    total_campos = len(dados)
    
    for idx, (chave, valor) in enumerate(dados.items()):
        if progress_bar:
            progress_bar.progress((idx + 1) / total_campos)
        
        chave_trad = TRADUCOES_MANUAIS.get(chave, traduzir_texto(chave.replace('_', ' ').title()))
        
        if isinstance(valor, str):
            if valor.startswith(('http', 'www', 'https')) or valor == "N/A":
                dados_traduzidos[chave_trad] = valor
            else:
                # Traduz
                if usar_gemini and gemini_key:
                    valor_trad = traduzir_com_gemini(valor, gemini_key)
                else:
                    valor_trad = traduzir_texto(valor)
                
                # Converte medidas
                dados_traduzidos[chave_trad] = converter_medidas(valor_trad)
        
        elif isinstance(valor, list):
            lista_trad = []
            for item in valor:
                if isinstance(item, str) and item != "N/A":
                    if usar_gemini and gemini_key:
                        item_trad = traduzir_com_gemini(item, gemini_key)
                    else:
                        item_trad = traduzir_texto(item)
                    lista_trad.append(converter_medidas(item_trad))
                else:
                    lista_trad.append(item)
            dados_traduzidos[chave_trad] = lista_trad
        
        elif isinstance(valor, dict):
            dict_trad = {}
            for sub_chave, sub_valor in valor.items():
                if sub_chave != "N/A":
                    sub_chave_trad = traduzir_texto(sub_chave)
                    if usar_gemini and gemini_key and sub_valor != "N/A":
                        sub_valor_trad = traduzir_com_gemini(sub_valor, gemini_key)
                    else:
                        sub_valor_trad = traduzir_texto(sub_valor)
                    dict_trad[sub_chave_trad] = converter_medidas(sub_valor_trad)
                else:
                    dict_trad[sub_chave] = sub_valor
            dados_traduzidos[chave_trad] = dict_trad
        
        else:
            dados_traduzidos[chave_trad] = valor
        
        time.sleep(0.05)  # Reduz delay para melhor performance
    
    return dados_traduzidos

def coletar_dados_produto(url: str) -> dict:
    if not validar_url_amazon(url):
        return {"erro": "URL não é da Amazon válida"}
    
    url_limpa = limpar_url_amazon(url)
    
    # Delay aleatório mais humano (2-4 segundos)
    time.sleep(random.uniform(2, 4))
    
    try:
        # Usa session para melhor performance
        session = requests.Session()
        response = session.get(url_limpa, headers=obter_headers(), timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        if 'To discuss automated access' in response.text:
            return {"erro": "Amazon bloqueou a requisição. Use VPN ou aguarde alguns minutos."}
        
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
            "technical_details": extrair_technical_details(soup),
            "asin": extrair_asin(soup, url_limpa),
            "url_produto": url_limpa,
            "data_coleta": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return dados
        
    except Exception as e:
        return {"erro": f"Erro: {str(e)}"}

def gerar_vtex_markdown(dados: dict) -> str:
    """Gera formato Markdown para VTEX"""
    titulo = dados.get('Título', dados.get('titulo_h1', 'Produto'))
    marca = dados.get('Marca', dados.get('marca', 'N/A'))
    
    tech_details = dados.get('Detalhes Técnicos', dados.get('technical_details', {}))
    product_info = dados.get('Informações do Produto', dados.get('product_info', {}))
    
    specs = {**tech_details, **product_info}
    
    markdown = f"#### {titulo}\n<endDescription>\n"
    
    for chave, valor in specs.items():
        if chave != "N/A" and valor != "N/A":
            markdown += f"{chave}:{valor}<br>\n"
    
    markdown += f"Marca:{marca}<br>\n"
    markdown += f"ASIN:{dados.get('ASIN', dados.get('asin', 'N/A'))}<br>\n"
    markdown += f"Data da Coleta:{dados.get('Data da Coleta', dados.get('data_coleta', 'N/A'))}<br>\n"
    markdown += f"Aviso:Imagens meramente ilustrativas\n"
    
    return markdown

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

def resetar_aplicacao():
    """Reseta o estado da aplicação"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

def main():
    st.set_page_config(page_title="Amazon Scraper Pro v2.1", page_icon="🛒", layout="wide")
    
    st.title("🛒 Amazon Product Scraper Pro v2.1")
    st.markdown("**Extraia dados completos de produtos da Amazon com tradução automática e conversão de medidas**")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configurações")
        
        st.info("🔒 **Dicas Anti-Bloqueio**\n\n✅ Use Opera Browser com VPN\n✅ Aguarde 3-5 segundos entre coletas\n✅ Evite coletar muitos produtos seguidos\n\n[Baixar Opera](https://www.opera.com/pt-br)")
        
        st.markdown("---")
        
        st.subheader("🌐 Tradução e Conversão")
        
        traducao = st.checkbox("Traduzir para PT-BR", value=True)
        converter = st.checkbox("Converter medidas para padrão BR", value=True, 
                               help="Converte polegadas→cm, libras→kg, etc.")
        
        if traducao:
            metodo_traducao = st.selectbox(
                "Método de Tradução:",
                ["Auto (Múltiplas APIs)", "MyMemory API", "Gemini AI (melhor qualidade)"],
                help="Auto tenta MyMemory, Libre Translate e Deep Translator em cascata"
            )
            
            usar_gemini = "Gemini" in metodo_traducao
            
            if usar_gemini:
                if GEMINI_DISPONIVEL:
                    gemini_key = st.text_input(
                        "Gemini API Key:",
                        type="password",
                        help="Obtenha em: https://makersuite.google.com/app/apikey"
                    )
                else:
                    st.warning("📦 Gemini indisponível. Instale: `pip install google-generativeai`")
                    usar_gemini = False
                    gemini_key = None
            else:
                gemini_key = None
        else:
            usar_gemini = False
            gemini_key = None
        
        st.markdown("---")
        
        # Status das APIs
        st.caption("**Status das APIs de Tradução:**")
        st.caption(f"{'✅' if True else '❌'} MyMemory (sempre disponível)")
        st.caption(f"{'✅' if LIBRE_DISPONIVEL else '❌'} Libre Translate")
        st.caption(f"{'✅' if TRADUTOR_DISPONIVEL else '❌'} Deep Translator")
        st.caption(f"{'✅' if GEMINI_DISPONIVEL else '❌'} Gemini AI")
        
        st.markdown("---")
        st.caption("v2.1 - Múltiplas APIs de tradução + Conversão de medidas")
    
    # Input
    url_input = st.text_input(
        "🔗 Cole a URL do produto:",
        placeholder="https://www.amazon.com/dp/B08N5WRWNW"
    )
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        coletar_btn = st.button("🚀 Coletar Dados", type="primary", use_container_width=True)
    
    with col2:
        if 'dados_coletados' in st.session_state:
            if st.button("🔄 Reiniciar", use_container_width=True):
                resetar_aplicacao()
    
    if coletar_btn:
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
                    
                    # Tradução e conversão
                    if traducao or converter:
                        metodo = "Gemini AI" if usar_gemini and gemini_key else "APIs Múltiplas"
                        with st.spinner(f"🌐 Traduzindo e convertendo com {metodo}..."):
                            progress_bar = st.progress(0)
                            dados = traduzir_e_converter_dados(dados, usar_gemini, gemini_key, progress_bar)
                            progress_bar.empty()
                            st.success(f"✅ Processamento concluído com {metodo}!")
                    
                    st.session_state['dados_coletados'] = dados
    
    # Exibe dados se já coletados
    if 'dados_coletados' in st.session_state:
        dados = st.session_state['dados_coletados']
        traducao = any(key in dados for key in ['Título', 'Preço', 'Marca'])
        
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
        
        # Detalhes Técnicos
        st.markdown("---")
        st.subheader("🔧 Detalhes Técnicos Completos")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Informações do Produto**")
            product_info = dados.get('Informações do Produto' if traducao else 'product_info', {})
            
            if isinstance(product_info, dict) and product_info != {"N/A": "N/A"}:
                df_info = pd.DataFrame(
                    list(product_info.items()),
                    columns=['Especificação', 'Valor']
                )
                st.dataframe(df_info, use_container_width=True, hide_index=True)
            else:
                st.info("Não disponível")
        
        with col2:
            st.markdown("**Detalhes Técnicos**")
            tech_details = dados.get('Detalhes Técnicos' if traducao else 'technical_details', {})
            
            if isinstance(tech_details, dict) and tech_details != {"N/A": "N/A"}:
                df_tech = pd.DataFrame(
                    list(tech_details.items()),
                    columns=['Especificação', 'Valor']
                )
                st.dataframe(df_tech, use_container_width=True, hide_index=True)
            else:
                st.info("Não disponível")
        
        # Downloads
        st.markdown("---")
        st.subheader("📥 Exportar Dados")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            csv_data = gerar_csv(dados)
            st.download_button(
                label="📄 CSV",
                data=csv_data,
                file_name=f"produto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            json_data = gerar_json(dados)
            st.download_button(
                label="📋 JSON",
                data=json_data,
                file_name=f"produto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
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
                    label="📊 Excel",
                    data=excel_data,
                    file_name=f"produto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except:
                st.info("Excel indisponível")
        
        with col4:
            vtex_data = gerar_vtex_markdown(dados)
            st.download_button(
                label="🏪 VTEX",
                data=vtex_data,
                file_name=f"vtex_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown",
                use_container_width=True
            )
        
        # Preview VTEX
        with st.expander("👁️ Preview VTEX Markdown"):
            st.code(vtex_data, language="markdown")
        
        # Preview de Conversões
        with st.expander("📏 Conversões de Medidas Aplicadas"):
            st.info("""
            **Conversões Automáticas Realizadas:**
            
            📐 **Comprimento:** inches → cm, feet → m, yards → m
            
            ⚖️ **Peso:** pounds/lbs → kg, ounces → g
            
            🧪 **Volume:** gallons → L, fl oz → ml, quarts → L, pints → ml
            
            👕 **Tamanhos:** XS→P, S→M, M→G, L→GG, XL→XG, etc.
            
            *Valores originais são mantidos junto com as conversões.*
            """)

if __name__ == "__main__":
    main()