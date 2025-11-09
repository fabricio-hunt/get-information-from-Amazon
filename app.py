import requests
from bs4 import BeautifulSoup
from typing import Union, List, Dict
from pathlib import Path
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

# Configuração de logging
logging.basicConfig(level=logging.WARNING)

# ========================================
# CONFIGURAÇÕES E CONSTANTES
# ========================================

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]

SELECTORS = {
    "titulo": [
        ('span', {'id': 'productTitle'}),
        ('h1', {'class': 'a-size-large'}),
        ('h1', {'id': 'title'})
    ],
    "imagem": [
        ('img', {'id': 'landingImage'}),
        ('img', {'class': 'a-dynamic-image'}),
        ('div', {'id': 'imgTagWrapperId'})
    ],
    "preco": [
        ('span', {'class': 'a-price-whole'}),
        ('span', {'id': 'priceblock_ourprice'}),
        ('span', {'id': 'priceblock_dealprice'}),
        ('span', {'class': 'a-color-price'}),
        ('span', {'id': 'tp_price_block_total_price_ww'}),
        ('span', {'class': 'a-offscreen'})
    ],
    "avaliacao": [
        ('span', {'id': 'acrPopover'}),
        ('i', {'class': 'a-icon-star'}),
        ('a', {'href': '#customerReviews'})
    ],
    "num_avaliacoes": [
        ('span', {'id': 'acrCustomerReviewText'}),
        ('span', {'class': 'a-size-base'})
    ],
    "disponibilidade": [
        ('div', {'id': 'availability'}),
        ('span', {'class': 'a-size-medium a-color-success'}),
        ('span', {'id': 'availability_string'})
    ],
    "categoria": [
        ('a', {'class': 'a-link-normal a-color-tertiary'}),
        ('span', {'class': 'a-list-item'})
    ],
    "marca": [
        ('a', {'id': 'bylineInfo'}),
        ('span', {'class': 'author'}),
        ('a', {'class': 'a-link-normal'})
    ],
    "features": [
        ('div', {'id': 'feature-bullets'}),
        ('ul', {'class': 'a-unordered-list a-vertical a-spacing-mini'})
    ]
}

# ========================================
# FUNÇÕES DE TRADUÇÃO MELHORADAS
# ========================================

# Dicionário de tradução estática (mais rápido e confiável)
TRADUCOES = {
    # Campos
    'titulo_h1': 'Título',
    'url_imagem': 'URL da Imagem',
    'preco': 'Preço',
    'avaliacao': 'Avaliação',
    'num_avaliacoes': 'Número de Avaliações',
    'disponibilidade': 'Disponibilidade',
    'categoria': 'Categoria',
    'marca': 'Marca',
    'sobre_o_produto': 'Sobre o Produto',
    'detalhes_tecnicos': 'Detalhes Técnicos',
    'asin': 'ASIN',
    'peso': 'Peso',
    'dimensoes': 'Dimensões',
    'data_coleta': 'Data da Coleta',
    'url_produto': 'URL do Produto',
    
    # Valores comuns
    'In Stock': 'Em Estoque',
    'Out of Stock': 'Fora de Estoque',
    'Usually ships within': 'Geralmente enviado em',
    'Free Shipping': 'Frete Grátis',
    'Prime': 'Prime',
    'Add to Cart': 'Adicionar ao Carrinho',
    'Buy Now': 'Comprar Agora',
    'ratings': 'avaliações',
    'rating': 'avaliação',
    'out of 5 stars': 'de 5 estrelas'
}

def traduzir_texto_simples(texto: str) -> str:
    """Tradução rápida usando dicionário estático"""
    if not texto or not isinstance(texto, str):
        return texto
    
    texto_lower = texto.lower()
    for en, pt in TRADUCOES.items():
        if en.lower() in texto_lower:
            texto = texto.replace(en, pt)
    
    return texto

def traduzir_dados(dados: dict) -> dict:
    """Traduz dados do produto usando dicionário estático"""
    dados_traduzidos = {}
    
    for chave, valor in dados.items():
        # Traduz a chave
        chave_traduzida = TRADUCOES.get(chave, chave.replace('_', ' ').title())
        
        # Traduz o valor
        if isinstance(valor, str):
            # Não traduz URLs, números ou já está em português
            if valor.startswith(('http', 'www', 'https', '$', 'R$')) or valor.replace('.', '').replace(',', '').isdigit():
                dados_traduzidos[chave_traduzida] = valor
            else:
                dados_traduzidos[chave_traduzida] = traduzir_texto_simples(valor)
        elif isinstance(valor, list):
            dados_traduzidos[chave_traduzida] = [traduzir_texto_simples(item) if isinstance(item, str) else item for item in valor]
        elif isinstance(valor, dict):
            dados_traduzidos[chave_traduzida] = traduzir_dados(valor)
        else:
            dados_traduzidos[chave_traduzida] = valor
    
    return dados_traduzidos

# ========================================
# FUNÇÕES AUXILIARES DE EXTRAÇÃO
# ========================================

def obter_headers() -> dict:
    """Retorna headers HTTP dinâmicos"""
    import random
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

def validar_url_amazon(url: str) -> bool:
    """Valida se a URL é da Amazon"""
    parsed = urlparse(url)
    dominios_validos = ['amazon.com', 'amazon.com.br', 'amazon.co.uk', 'amazon.de', 'amazon.fr', 'amazon.es', 'amazon.it']
    return any(dominio in parsed.netloc for dominio in dominios_validos)

def extrair_texto(soup: BeautifulSoup, selectors: list) -> str:
    """Extrai texto usando lista de seletores"""
    for tag, attrs in selectors:
        elemento = soup.find(tag, attrs)
        if elemento:
            texto = elemento.get_text(strip=True)
            if texto:
                return texto
    return "N/A"

def extrair_imagem(soup: BeautifulSoup) -> str:
    """Extrai URL da imagem principal do produto"""
    for tag, attrs in SELECTORS["imagem"]:
        elemento = soup.find(tag, attrs)
        if elemento:
            # Tenta pegar de diferentes atributos
            for attr in ['data-old-hires', 'data-a-dynamic-image', 'src']:
                url = elemento.get(attr)
                if url:
                    # Se for JSON (data-a-dynamic-image), pega a primeira URL
                    if url.startswith('{'):
                        try:
                            import json
                            urls = json.loads(url)
                            return list(urls.keys())[0]
                        except:
                            continue
                    return url
    return "N/A"

def extrair_preco(soup: BeautifulSoup) -> str:
    """Extrai preço do produto"""
    for tag, attrs in SELECTORS["preco"]:
        elemento = soup.find(tag, attrs)
        if elemento:
            preco = elemento.get_text(strip=True)
            # Limpa o preço
            preco = preco.replace('\n', '').replace(' ', '')
            if preco and any(char.isdigit() for char in preco):
                return preco
    return "N/A"

def extrair_avaliacao(soup: BeautifulSoup) -> str:
    """Extrai avaliação média do produto"""
    for tag, attrs in SELECTORS["avaliacao"]:
        elemento = soup.find(tag, attrs)
        if elemento:
            # Tenta pegar do título ou texto
            avaliacao = elemento.get('title') or elemento.get_text(strip=True)
            if avaliacao:
                # Extrai apenas números e pontos
                match = re.search(r'(\d+\.?\d*)\s*out of\s*5|(\d+\.?\d*)\s*de\s*5', avaliacao)
                if match:
                    return match.group(1) or match.group(2)
                # Tenta pegar qualquer número
                match = re.search(r'(\d+\.?\d*)', avaliacao)
                if match:
                    return match.group(1)
    return "N/A"

def extrair_num_avaliacoes(soup: BeautifulSoup) -> str:
    """Extrai número total de avaliações"""
    for tag, attrs in SELECTORS["num_avaliacoes"]:
        elemento = soup.find(tag, attrs)
        if elemento:
            texto = elemento.get_text(strip=True)
            # Extrai números
            match = re.search(r'([\d,\.]+)', texto)
            if match:
                return match.group(1)
    return "N/A"

def extrair_disponibilidade(soup: BeautifulSoup) -> str:
    """Extrai disponibilidade do produto"""
    for tag, attrs in SELECTORS["disponibilidade"]:
        elemento = soup.find(tag, attrs)
        if elemento:
            disp = elemento.get_text(strip=True)
            if disp:
                return disp
    return "N/A"

def extrair_categoria(soup: BeautifulSoup) -> str:
    """Extrai categoria/breadcrumb do produto"""
    # Tenta pegar breadcrumb
    breadcrumb = soup.find('div', {'id': 'wayfinding-breadcrumbs_feature_div'})
    if breadcrumb:
        links = breadcrumb.find_all('a')
        if links:
            categorias = [link.get_text(strip=True) for link in links if link.get_text(strip=True)]
            return ' > '.join(categorias)
    
    # Fallback para seletores genéricos
    return extrair_texto(soup, SELECTORS["categoria"])

def extrair_descricao(soup: BeautifulSoup) -> List[str]:
    """Extrai lista de características do produto"""
    features = []
    
    for tag, attrs in SELECTORS["features"]:
        feature_div = soup.find(tag, attrs)
        if feature_div:
            items = feature_div.find_all('li')
            for item in items:
                texto = item.get_text(strip=True)
                if texto and len(texto) > 5:  # Ignora textos muito curtos
                    features.append(texto)
            if features:
                break
    
    return features if features else ["N/A"]

def extrair_detalhes_tecnicos(soup: BeautifulSoup) -> Dict[str, str]:
    """Extrai detalhes técnicos do produto"""
    detalhes = {}
    
    # Procura na tabela de detalhes
    tabelas = soup.find_all('table', {'id': re.compile('productDetails')})
    for tabela in tabelas:
        linhas = tabela.find_all('tr')
        for linha in linhas:
            colunas = linha.find_all(['th', 'td'])
            if len(colunas) >= 2:
                chave = colunas[0].get_text(strip=True)
                valor = colunas[1].get_text(strip=True)
                if chave and valor:
                    detalhes[chave] = valor
    
    # Procura em listas de detalhes
    if not detalhes:
        detail_bullets = soup.find('div', {'id': 'detailBullets_feature_div'})
        if detail_bullets:
            items = detail_bullets.find_all('li')
            for item in items:
                texto = item.get_text(strip=True)
                if ':' in texto:
                    partes = texto.split(':', 1)
                    detalhes[partes[0].strip()] = partes[1].strip()
    
    return detalhes if detalhes else {"N/A": "N/A"}

def extrair_asin(soup: BeautifulSoup) -> str:
    """Extrai código ASIN do produto"""
    # Método 1: Procura em detalhes técnicos
    detalhes = extrair_detalhes_tecnicos(soup)
    for chave, valor in detalhes.items():
        if 'ASIN' in chave.upper():
            return valor
    
    # Método 2: Procura em inputs hidden
    asin_input = soup.find('input', {'name': 'ASIN'})
    if asin_input:
        return asin_input.get('value', 'N/A')
    
    # Método 3: Extrai da URL
    asin_match = re.search(r'/dp/([A-Z0-9]{10})', str(soup))
    if asin_match:
        return asin_match.group(1)
    
    return "N/A"

def extrair_peso(soup: BeautifulSoup) -> str:
    """Extrai peso do produto"""
    detalhes = extrair_detalhes_tecnicos(soup)
    for chave, valor in detalhes.items():
        if any(palavra in chave.lower() for palavra in ['weight', 'peso', 'shipping weight']):
            return valor
    return "N/A"

# ========================================
# FUNÇÃO PRINCIPAL DE COLETA
# ========================================

def coletar_dados_produto(url: str, usar_cache: bool = True) -> dict:
    """
    Coleta dados de um produto da Amazon
    
    Args:
        url: URL do produto
        usar_cache: Se True, usa cache se disponível
    
    Returns:
        Dicionário com dados do produto
    """
    
    # Valida URL
    if not validar_url_amazon(url):
        return {"erro": "URL não é da Amazon válida"}
    
    # Delay para evitar bloqueio
    time.sleep(2)
    
    try:
        headers = obter_headers()
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Verifica se foi bloqueado
        if 'To discuss automated access to Amazon data' in response.text:
            return {"erro": "Amazon bloqueou a requisição. Tente usar VPN ou aguarde alguns minutos."}
        
        # Extrai dados
        dados = {
            "titulo_h1": extrair_texto(soup, SELECTORS["titulo"]),
            "url_imagem": extrair_imagem(soup),
            "preco": extrair_preco(soup),
            "avaliacao": extrair_avaliacao(soup),
            "num_avaliacoes": extrair_num_avaliacoes(soup),
            "disponibilidade": extrair_disponibilidade(soup),
            "categoria": extrair_categoria(soup),
            "marca": extrair_texto(soup, SELECTORS["marca"]),
            "sobre_o_produto": extrair_descricao(soup),
            "detalhes_tecnicos": extrair_detalhes_tecnicos(soup),
            "asin": extrair_asin(soup),
            "peso": extrair_peso(soup),
            "url_produto": url,
            "data_coleta": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return dados
        
    except requests.exceptions.Timeout:
        return {"erro": "Tempo de requisição excedido. Tente novamente."}
    except requests.exceptions.RequestException as e:
        return {"erro": f"Erro de requisição: {str(e)}"}
    except Exception as e:
        return {"erro": f"Erro inesperado: {str(e)}"}

# ========================================
# FUNÇÕES DE EXPORTAÇÃO
# ========================================

def gerar_csv(dados: dict) -> str:
    """Gera CSV a partir dos dados coletados"""
    output = io.StringIO()
    
    # Achata o dicionário para CSV
    dados_flat = {}
    for chave, valor in dados.items():
        if isinstance(valor, list):
            dados_flat[chave] = ' | '.join(str(v) for v in valor)
        elif isinstance(valor, dict):
            for sub_chave, sub_valor in valor.items():
                dados_flat[f"{chave}_{sub_chave}"] = sub_valor
        else:
            dados_flat[chave] = valor
    
    writer = csv.DictWriter(output, fieldnames=dados_flat.keys())
    writer.writeheader()
    writer.writerow(dados_flat)
    
    return output.getvalue()

def gerar_json(dados: dict) -> str:
    """Gera JSON formatado"""
    return json.dumps(dados, ensure_ascii=False, indent=2)

def gerar_excel(dados: dict) -> bytes:
    """Gera arquivo Excel"""
    # Achata dados
    dados_flat = {}
    for chave, valor in dados.items():
        if isinstance(valor, list):
            dados_flat[chave] = '\n'.join(str(v) for v in valor)
        elif isinstance(valor, dict):
            dados_flat[chave] = json.dumps(valor, ensure_ascii=False)
        else:
            dados_flat[chave] = valor
    
    df = pd.DataFrame([dados_flat])
    output = io.BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    return output.getvalue()

# ========================================
# INTERFACE STREAMLIT
# ========================================

def main():
    st.set_page_config(
        page_title="Amazon Scraper Pro",
        page_icon="🛒",
        layout="wide"
    )
    
    st.title("🛒 Amazon Product Scraper Pro v2.0")
    st.markdown("**Extraia dados de produtos da Amazon de forma profissional!**")
    
    # Sidebar com configurações
    with st.sidebar:
        st.header("⚙️ Configurações")
        traducao_ativa = st.checkbox("🌐 Traduzir para Português", value=True)
        usar_cache = st.checkbox("💾 Usar Cache", value=True, help="Evita coletar o mesmo produto várias vezes")
        
        st.markdown("---")
        st.subheader("📊 Estatísticas")
        if 'historico' not in st.session_state:
            st.session_state.historico = []
        st.metric("Produtos Coletados", len(st.session_state.historico))
        
        if st.button("🗑️ Limpar Histórico"):
            st.session_state.historico = []
            st.success("Histórico limpo!")
    
    # Área principal
    tab1, tab2, tab3 = st.tabs(["📦 Coletar Produto", "📋 Histórico", "ℹ️ Sobre"])
    
    with tab1:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            url_input = st.text_input(
                "🔗 URL do Produto Amazon:",
                placeholder="https://www.amazon.com/dp/B08N5WRWNW",
                help="Cole a URL completa do produto"
            )
        
        with col2:
            st.write("")
            st.write("")
            coletar_btn = st.button("🚀 Coletar Dados", type="primary", use_container_width=True)
        
        if coletar_btn:
            if not url_input:
                st.warning("⚠️ Por favor, insira uma URL válida.")
            elif not validar_url_amazon(url_input):
                st.error("❌ URL inválida! Certifique-se de usar uma URL da Amazon.")
            else:
                with st.spinner("🔍 Coletando dados... Aguarde!"):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    status_text.text("Enviando requisição...")
                    progress_bar.progress(20)
                    
                    dados = coletar_dados_produto(url_input, usar_cache)
                    progress_bar.progress(60)
                    
                    if 'erro' in dados:
                        st.error(f"❌ {dados['erro']}")
                    else:
                        status_text.text("Processando dados...")
                        progress_bar.progress(80)
                        
                        if traducao_ativa:
                            status_text.text("Traduzindo...")
                            dados = traduzir_dados(dados)
                        
                        progress_bar.progress(100)
                        status_text.text("✅ Concluído!")
                        time.sleep(0.5)
                        progress_bar.empty()
                        status_text.empty()
                        
                        st.success("✅ Dados coletados com sucesso!")
                        
                        # Adiciona ao histórico
                        st.session_state.historico.append(dados)
                        
                        # Exibe dados
                        st.subheader("📊 Dados Extraídos")
                        
                        # Cards com informações principais
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("💰 Preço", dados.get('Preço' if traducao_ativa else 'preco', 'N/A'))
                        with col2:
                            st.metric("⭐ Avaliação", dados.get('Avaliação' if traducao_ativa else 'avaliacao', 'N/A'))
                        with col3:
                            st.metric("💬 Avaliações", dados.get('Número de Avaliações' if traducao_ativa else 'num_avaliacoes', 'N/A'))
                        with col4:
                            st.metric("📦 Disponibilidade", dados.get('Disponibilidade' if traducao_ativa else 'disponibilidade', 'N/A')[:20])
                        
                        st.markdown("---")
                        
                        # Informações detalhadas
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.subheader("ℹ️ Informações Gerais")
                            for chave in ['Título', 'Marca', 'Categoria', 'ASIN', 'Peso']:
                                key = chave if traducao_ativa else chave.lower().replace(' ', '_')
                                if key in dados and dados[key] != 'N/A':
                                    st.write(f"**{chave}:** {dados[key]}")
                            
                            # Imagem
                            if dados.get('URL da Imagem' if traducao_ativa else 'url_imagem', 'N/A') != 'N/A':
                                st.image(dados['URL da Imagem' if traducao_ativa else 'url_imagem'], width=300)
                        
                        with col2:
                            st.subheader("📝 Características")
                            features = dados.get('Sobre o Produto' if traducao_ativa else 'sobre_o_produto', [])
                            if isinstance(features, list) and features != ['N/A']:
                                for feature in features:
                                    st.write(f"• {feature}")
                            else:
                                st.write("N/A")
                        
                        # Detalhes técnicos
                        st.subheader("🔧 Detalhes Técnicos")
                        detalhes = dados.get('Detalhes Técnicos' if traducao_ativa else 'detalhes_tecnicos', {})
                        if isinstance(detalhes, dict) and detalhes != {"N/A": "N/A"}:
                            df_detalhes = pd.DataFrame(list(detalhes.items()), columns=['Especificação', 'Valor'])
                            st.dataframe(df_detalhes, use_container_width=True)
                        else:
                            st.write("N/A")
                        
                        # Botões de download
                        st.markdown("---")
                        st.subheader("📥 Exportar Dados")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            csv_data = gerar_csv(dados)
                            st.download_button(
                                label="📄 Baixar CSV",
                                data=csv_data,
                                file_name=f"produto_amazon_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                        
                        with col2:
                            json_data = gerar_json(dados)
                            st.download_button(
                                label="📋 Baixar JSON",
                                data=json_data,
                                file_name=f"produto_amazon_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                mime="application/json",
                                use_container_width=True
                            )
                        
                        with col3:
                            try:
                                excel_data = gerar_excel(dados)
                                st.download_button(
                                    label="📊 Baixar Excel",
                                    data=excel_data,
                                    file_name=f"produto_amazon_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    use_container_width=True
                                )
                            except:
                                st.info("Excel requer: pip install openpyxl")
    
    with tab2:
        st.subheader("📋 Histórico de Produtos Coletados")
        
        if st.session_state.historico:
            for idx, produto in enumerate(reversed(st.session_state.historico)):
                with st.expander(f"🛍️ {produto.get('Título', produto.get('titulo_h1', 'Produto'))} - {produto.get('Data da Coleta', produto.get('data_coleta', ''))}"):
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        img_url = produto.get('URL da Imagem', produto.get('url_imagem'))
                        if img_url and img_url != 'N/A':
                            st.image(img_url, width=150)
                    with col2:
                        st.json(produto)
        else:
            st.info("Nenhum produto coletado ainda. Vá para a aba 'Coletar Produto'!")
    