import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import logging
import csv
import json
from urllib.parse import urlparse, urlunparse, parse_qs
import time
import io
import streamlit as st
from datetime import datetime 
import pandas as pd
import re

logging.basicConfig(level=logging.WARNING)

# Importações de tradução
try:
    from deep_translator import GoogleTranslator
    TRADUTOR_DISPONIVEL = True
except ImportError:
    TRADUTOR_DISPONIVEL = False

try:
    import google.generativeai as genai
    GEMINI_DISPONIVEL = True
except ImportError:
    GEMINI_DISPONIVEL = False

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
    'technical_details': 'Detalhes Técnicos', 'data_coleta': 'Data da Coleta',
    'url_produto': 'URL do Produto',
}

def limpar_url_amazon(url: str) -> str:
    """Remove parâmetros desnecessários da URL"""
    parsed = urlparse(url)
    
    # Mantém apenas o domínio e o path
    clean_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        '', '', ''
    ))
    
    return clean_url

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
        return traduzir_texto(texto)

def traduzir_texto(texto: str) -> str:
    """Traduz texto usando Deep Translator (fallback)"""
    if not TRADUTOR_DISPONIVEL or not texto or texto == "N/A":
        return texto
    
    if texto.startswith(('http', 'www', 'https', '$', 'R$')):
        return texto
    
    if len(texto) < 3:
        return texto
    
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
    
    # Procura por todas as tabelas de detalhes técnicos
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
    
    # Tabelas de informações
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

def traduzir_dados(dados: dict, usar_gemini: bool = False, gemini_key: str = None, progress_bar=None) -> dict:
    """Traduz todos os dados usando Deep Translator ou Gemini"""
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
                if usar_gemini and gemini_key:
                    dados_traduzidos[chave_trad] = traduzir_com_gemini(valor, gemini_key)
                else:
                    dados_traduzidos[chave_trad] = traduzir_texto(valor)
        
        elif isinstance(valor, list):
            lista_trad = []
            for item in valor:
                if isinstance(item, str) and item != "N/A":
                    if usar_gemini and gemini_key:
                        lista_trad.append(traduzir_com_gemini(item, gemini_key))
                    else:
                        lista_trad.append(traduzir_texto(item))
                else:
                    lista_trad.append(item)
            dados_traduzidos[chave_trad] = lista_trad
        
        elif isinstance(valor, dict):
            dict_trad = {}
            for sub_chave, sub_valor in valor.items():
                if sub_chave != "N/A":
                    sub_chave_trad = traduzir_texto(sub_chave)
                    if usar_gemini and gemini_key and sub_valor != "N/A":
                        dict_trad[sub_chave_trad] = traduzir_com_gemini(sub_valor, gemini_key)
                    else:
                        dict_trad[sub_chave_trad] = sub_valor
                else:
                    dict_trad[sub_chave] = sub_valor
            dados_traduzidos[chave_trad] = dict_trad
        
        else:
            dados_traduzidos[chave_trad] = valor
        
        time.sleep(0.1)
    
    return dados_traduzidos

def coletar_dados_produto(url: str) -> dict:
    if not validar_url_amazon(url):
        return {"erro": "URL não é da Amazon válida"}
    
    # Limpa a URL
    url_limpa = limpar_url_amazon(url)
    
    time.sleep(2)
    
    try:
        response = requests.get(url_limpa, headers=obter_headers(), timeout=20)
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
    
    # Informações técnicas
    tech_details = dados.get('Detalhes Técnicos', dados.get('technical_details', {}))
    product_info = dados.get('Informações do Produto', dados.get('product_info', {}))
    
    # Combina todas as especificações
    specs = {**tech_details, **product_info}
    
    markdown = f"#### {titulo}\n<endDescription>\n"
    
    # Adiciona especificações
    for chave, valor in specs.items():
        if chave != "N/A" and valor != "N/A":
            markdown += f"{chave}:{valor}<br>\n"
    
    # Adiciona informações adicionais
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
    st.set_page_config(page_title="Amazon Scraper Pro v2.0", page_icon="🛒", layout="wide")
    
    st.title("🛒 Amazon Product Scraper Pro v2.0")
    st.markdown("**Extraia dados completos de produtos da Amazon com tradução automática via IA**")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configurações")
        
        # Recomendação VPN
        st.info("🔒 **Recomendação: Use Opera Browser**\n\nO Opera possui VPN nativa gratuita que ajuda a evitar bloqueios da Amazon.\n\n[Baixar Opera](https://www.opera.com/pt-br)")
        
        st.markdown("---")
        
        # Opções de tradução
        st.subheader("🌐 Tradução")
        
        if TRADUTOR_DISPONIVEL:
            traducao = st.checkbox("Traduzir para PT-BR", value=True)
            
            if GEMINI_DISPONIVEL:
                usar_gemini = st.checkbox("🤖 Usar Gemini AI (melhor qualidade)", value=False)
                
                if usar_gemini:
                    gemini_key = st.text_input(
                        "Gemini API Key:",
                        type="password",
                        help="Obtenha em: https://makersuite.google.com/app/apikey"
                    )
                else:
                    gemini_key = None
            else:
                usar_gemini = False
                gemini_key = None
                st.warning("📦 Para usar Gemini: `pip install google-generativeai`")
        else:
            traducao = False
            usar_gemini = False
            gemini_key = None
            st.error("❌ Deep Translator não instalado")
            st.code("pip install deep-translator", language="bash")
        
        st.markdown("---")
        st.caption("v2.0 - Com suporte VTEX e Gemini AI")
    
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
                    
                    # Tradução
                    if traducao and TRADUTOR_DISPONIVEL:
                        metodo = "Gemini AI" if usar_gemini and gemini_key else "Deep Translator"
                        with st.spinner(f"🌐 Traduzindo com {metodo}..."):
                            progress_bar = st.progress(0)
                            dados = traduzir_dados(dados, usar_gemini, gemini_key, progress_bar)
                            progress_bar.empty()
                            st.success(f"✅ Tradução concluída com {metodo}!")
                    
                    # Salva no session_state
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
        
        # Detalhes Técnicos (NOVO)
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
            # NOVO: Exportar para VTEX
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

if __name__ == "__main__":
    main()