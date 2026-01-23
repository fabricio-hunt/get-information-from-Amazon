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
import concurrent.futures

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

# Tabelas de conversão expandidas
# Tabelas de conversão expandidas (EN + PT)
CONVERSAO_MEDIDAS = {
    # Comprimento
    'inch': {'para': 'cm', 'multiplicador': 2.54, 'precisao': 1, 'tipo': 'linear'},
    'inches': {'para': 'cm', 'multiplicador': 2.54, 'precisao': 1, 'tipo': 'linear'},
    'in': {'para': 'cm', 'multiplicador': 2.54, 'precisao': 1, 'tipo': 'linear'},
    '"': {'para': 'cm', 'multiplicador': 2.54, 'precisao': 1, 'tipo': 'linear'},
    'polegada': {'para': 'cm', 'multiplicador': 2.54, 'precisao': 1, 'tipo': 'linear'},
    'polegadas': {'para': 'cm', 'multiplicador': 2.54, 'precisao': 1, 'tipo': 'linear'},
    
    'ft': {'para': 'm', 'multiplicador': 0.3048, 'precisao': 2, 'tipo': 'linear'},
    'feet': {'para': 'm', 'multiplicador': 0.3048, 'precisao': 2, 'tipo': 'linear'},
    'foot': {'para': 'm', 'multiplicador': 0.3048, 'precisao': 2, 'tipo': 'linear'},
    "'": {'para': 'm', 'multiplicador': 0.3048, 'precisao': 2, 'tipo': 'linear'},
    'pé': {'para': 'm', 'multiplicador': 0.3048, 'precisao': 2, 'tipo': 'linear'},
    'pes': {'para': 'm', 'multiplicador': 0.3048, 'precisao': 2, 'tipo': 'linear'},
    'pés': {'para': 'm', 'multiplicador': 0.3048, 'precisao': 2, 'tipo': 'linear'},
    
    'yd': {'para': 'm', 'multiplicador': 0.9144, 'precisao': 2, 'tipo': 'linear'},
    'yard': {'para': 'm', 'multiplicador': 0.9144, 'precisao': 2, 'tipo': 'linear'},
    'yards': {'para': 'm', 'multiplicador': 0.9144, 'precisao': 2, 'tipo': 'linear'},
    'jarda': {'para': 'm', 'multiplicador': 0.9144, 'precisao': 2, 'tipo': 'linear'},
    'jardas': {'para': 'm', 'multiplicador': 0.9144, 'precisao': 2, 'tipo': 'linear'},
    
    'mi': {'para': 'km', 'multiplicador': 1.60934, 'precisao': 2, 'tipo': 'linear'},
    'mile': {'para': 'km', 'multiplicador': 1.60934, 'precisao': 2, 'tipo': 'linear'},
    'miles': {'para': 'km', 'multiplicador': 1.60934, 'precisao': 2, 'tipo': 'linear'},
    'milha': {'para': 'km', 'multiplicador': 1.60934, 'precisao': 2, 'tipo': 'linear'},
    'milhas': {'para': 'km', 'multiplicador': 1.60934, 'precisao': 2, 'tipo': 'linear'},

    # Peso
    'lb': {'para': 'kg', 'multiplicador': 0.453592, 'precisao': 2, 'tipo': 'peso'},
    'lbs': {'para': 'kg', 'multiplicador': 0.453592, 'precisao': 2, 'tipo': 'peso'},
    'pound': {'para': 'kg', 'multiplicador': 0.453592, 'precisao': 2, 'tipo': 'peso'},
    'pounds': {'para': 'kg', 'multiplicador': 0.453592, 'precisao': 2, 'tipo': 'peso'},
    'libra': {'para': 'kg', 'multiplicador': 0.453592, 'precisao': 2, 'tipo': 'peso'},
    'libras': {'para': 'kg', 'multiplicador': 0.453592, 'precisao': 2, 'tipo': 'peso'},
    
    'oz': {'para': 'g', 'multiplicador': 28.3495, 'precisao': 0, 'tipo': 'peso'},
    'ounce': {'para': 'g', 'multiplicador': 28.3495, 'precisao': 0, 'tipo': 'peso'},
    'ounces': {'para': 'g', 'multiplicador': 28.3495, 'precisao': 0, 'tipo': 'peso'},
    'onça': {'para': 'g', 'multiplicador': 28.3495, 'precisao': 0, 'tipo': 'peso'},
    'onças': {'para': 'g', 'multiplicador': 28.3495, 'precisao': 0, 'tipo': 'peso'},
    
    'us ton': {'para': 'kg', 'multiplicador': 907.185, 'precisao': 0, 'tipo': 'peso'},

    # Volume
    'fl oz': {'para': 'ml', 'multiplicador': 29.5735, 'precisao': 0, 'tipo': 'volume'},
    'fluid ounce': {'para': 'ml', 'multiplicador': 29.5735, 'precisao': 0, 'tipo': 'volume'}, 
    'fluid ounces': {'para': 'ml', 'multiplicador': 29.5735, 'precisao': 0, 'tipo': 'volume'},
    
    'cup': {'para': 'ml', 'multiplicador': 236.588, 'precisao': 0, 'tipo': 'volume'},
    'cups': {'para': 'ml', 'multiplicador': 236.588, 'precisao': 0, 'tipo': 'volume'},
    
    'pint': {'para': 'ml', 'multiplicador': 473.176, 'precisao': 0, 'tipo': 'volume'},
    'pt': {'para': 'ml', 'multiplicador': 473.176, 'precisao': 0, 'tipo': 'volume'},
    
    'quart': {'para': 'L', 'multiplicador': 0.946353, 'precisao': 3, 'tipo': 'volume'},
    'qt': {'para': 'L', 'multiplicador': 0.946353, 'precisao': 3, 'tipo': 'volume'},
    
    'gal': {'para': 'L', 'multiplicador': 3.78541, 'precisao': 2, 'tipo': 'volume'},
    'gallon': {'para': 'L', 'multiplicador': 3.78541, 'precisao': 2, 'tipo': 'volume'},
    'gallons': {'para': 'L', 'multiplicador': 3.78541, 'precisao': 2, 'tipo': 'volume'},
    'galão': {'para': 'L', 'multiplicador': 3.78541, 'precisao': 2, 'tipo': 'volume'},
    'galões': {'para': 'L', 'multiplicador': 3.78541, 'precisao': 2, 'tipo': 'volume'},
    
    'cu ft': {'para': 'L', 'multiplicador': 28.3168, 'precisao': 0, 'tipo': 'volume'},
    'cubic foot': {'para': 'L', 'multiplicador': 28.3168, 'precisao': 0, 'tipo': 'volume'},
    'cubic feet': {'para': 'L', 'multiplicador': 28.3168, 'precisao': 0, 'tipo': 'volume'},
    'pé cúbico': {'para': 'L', 'multiplicador': 28.3168, 'precisao': 0, 'tipo': 'volume'},
    'pés cúbicos': {'para': 'L', 'multiplicador': 28.3168, 'precisao': 0, 'tipo': 'volume'},

    # Area
    'sq in': {'para': 'cm²', 'multiplicador': 6.4516, 'precisao': 1, 'tipo': 'area'},
    'sq ft': {'para': 'm²', 'multiplicador': 0.0929, 'precisao': 2, 'tipo': 'area'},
    'acre': {'para': 'm²', 'multiplicador': 4046.86, 'precisao': 0, 'tipo': 'area'},
    
    # Potencia/Energia
    'hp': {'para': 'kW', 'multiplicador': 0.7457, 'precisao': 2, 'tipo': 'power'},
    'horsepower': {'para': 'kW', 'multiplicador': 0.7457, 'precisao': 2, 'tipo': 'power'},
    'btu': {'para': 'J', 'multiplicador': 1055.06, 'precisao': 0, 'tipo': 'energy'}, 
}

# Conversão de tamanhos de roupa (simplificado para detecção direta na string)
CONVERSAO_TAMANHOS = {
    # Genérico / Masculino Padrão
    'XS': 'PP', 'S': 'M', 'M': 'G', 'L': 'GG', 'XL': 'XGG', 
    '2XL': 'XXGG', '3XL': 'XXXGG', 'XXL': 'XXGG', 'XXS': 'PPP'
}

# Mapas de Roupas Específicos
CONVERSAO_FEMININO = {
    '0': '34', '2': '36', '4': '38', '6': '40', '8': '42', '10': '44', 
    '12': '46', '14': '48', '16': '50', '18': '52'
}

CONVERSAO_CALCADOS_FEM = {
    '5': '34', '5.5': '35', '6': '36', '6.5': '36', '7': '37', '7.5': '37',
    '8': '38', '8.5': '38', '9': '39', '9.5': '39', '10': '40', '11': '41'
}

CONVERSAO_CALCADOS_MASC = {
    '6': '38', '6.5': '38', '7': '39', '7.5': '39', '8': '40', '8.5': '40',
    '9': '41', '9.5': '41', '10': '42', '10.5': '42', '11': '43', '12': '44', '13': '45'
}

def identificar_genero(texto: str) -> str:
    """Identifica contexto de gênero no texto"""
    texto = texto.lower()
    if any(p in texto for p in ['women', 'woman', 'feminino', 'mulher', 'senhora', 'ladies']):
        return 'feminino'
    if any(p in texto for p in ['men', 'man', 'masculino', 'homem', 'senhor']):
        return 'masculino'
    if any(p in texto for p in ['kid', 'child', 'baby', 'infant', 'toddler', 'crianca', 'bebe', 'infantil']):
        return 'infantil'
    return 'unisex'

def formatar_numero_br(valor: float, precisao: int = 2) -> str:
    """Formata número para padrão brasileiro (vírgula decimal)"""
    if precisao == 0:
        s = f"{int(round(valor))}"
    else:
        s = f"{valor:.{precisao}f}"
    return s.replace('.', ',')

def converter_medidas(texto: str, genero_ctx: str = 'unisex') -> str:
    """
    Converte medidas americanas para brasileiras e tamanhos de roupa.
    Suporta: Peso, Comprimento, Volume, Área, Temperatura, Roupas/Calçados.
    """
    if not texto or texto == "N/A":
        return texto
    
    texto_final = texto
    
    # --- 1. Conversão de Temperatura (F -> C) ---
    # Busca padrões como 98.6°F, 98.6 F, 98.6 degrees F, 98.6 graus F
    padrao_temp = r'(-?[\d\.,]+)\s*(?:°|º|deg|degrees|graus)?\s*F\b'
    
    def conv_temp(match):
        orig = match.group(0)
        try:
            val_str = match.group(1).replace(',', '.')
            # Se existirem multiplos pontos (ex 1.200.5), falha
            if val_str.count('.') > 1: return orig
            
            val_f = float(val_str)
            val_c = (val_f - 32) * 5/9
            return f"{formatar_numero_br(val_c, 1)}°C ({orig})"
        except:
            return orig

    texto_final = re.sub(padrao_temp, conv_temp, texto_final, flags=re.IGNORECASE)

    # --- 2. Conversão de Medidas Físicas (Peso, Dimensão, Volume) ---
    # Captura números com vírgulas OU pontos + unidade com possíveis acentos
    padrao_fisico = r'((?:[\d]+(?:[.,][\d]{3})*|\d+)(?:[.,]\d+)?(?:\s*[xX]\s*(?:[\d]+(?:[.,][\d]{3})*|\d+)(?:[.,]\d+)?)*)\s*([a-zA-Z\u00C0-\u00FF"\']+(?:\s+[a-zA-Z\u00C0-\u00FF]+)?)'
    
    def conv_fisico(match):
        numeros_str = match.group(1)
        unidade_raw = match.group(2).lower()
        unidade = unidade_raw.replace('.', '') 
        
        info_unidade = None
        
        # Tentativa exata e singular
        if unidade in CONVERSAO_MEDIDAS:
            info_unidade = CONVERSAO_MEDIDAS[unidade]
        else:
            if unidade.endswith('s') and unidade[:-1] in CONVERSAO_MEDIDAS:
                info_unidade = CONVERSAO_MEDIDAS[unidade[:-1]]
            elif unidade.endswith('oes') and unidade[:-3]+'ao' in CONVERSAO_MEDIDAS: # galões -> galão
                info_unidade = CONVERSAO_MEDIDAS[unidade[:-3]+'ao']
        
        if info_unidade:
            novo_std = info_unidade['para']
            fator = info_unidade['multiplicador']
            precisao = info_unidade['precisao']
            tipo = info_unidade.get('tipo', 'geral')
            
            # Heurística para detectar formato de número (BR vs US)
            # Se unidade é PT (ex: libras, pés), assume vírgula = decimal
            unidade_pt = any(u in unidade for u in ['libra', 'polegada', 'pé', 'jarda', 'milha', 'onça', 'galão'])
            
            partes = re.split(r'\s*[xX]\s*', numeros_str)
            partes_convertidas = []
            
            for parte in partes:
                try:
                    val_float = 0.0
                    parte_limpa = parte.replace(' ', '')
                    
                    if unidade_pt: 
                        # Formato BR: 1.200,50 ou 1200,50
                        # Remove pontos de milhar, troca vírgula decimal por ponto
                        aux = parte_limpa.replace('.', '').replace(',', '.')
                        val_float = float(aux)
                    else:
                        # Formato US: 1,200.50 ou 1200.50
                        # Remove vírgulas de milhar
                        aux = parte_limpa.replace(',', '')
                        val_float = float(aux)
                        
                    val_conv = val_float * fator
                    
                    # Lógica de escala inteligente
                    std_final = novo_std
                    val_final = val_conv
                    
                    if tipo == 'peso':
                        if std_final == 'kg' and val_final < 1:
                            val_final *= 1000
                            std_final = 'g'
                            precisao = 0
                        elif std_final == 'g' and val_final >= 1000:
                            val_final /= 1000
                            std_final = 'kg'
                            precisao = 2
                            
                    elif tipo == 'linear':
                        if std_final == 'm' and val_final < 1:
                            val_final *= 100
                            std_final = 'cm'
                            precisao = 1
                        elif std_final == 'cm' and val_final >= 100:
                            val_final /= 100
                            std_final = 'm'
                            precisao = 2
                    
                    elif tipo == 'volume':
                         if std_final == 'L' and val_final < 1:
                             val_final *= 1000
                             std_final = 'ml'
                             precisao = 0
                    
                    partes_convertidas.append(formatar_numero_br(val_final, precisao))
                    novo_std = std_final 
                    
                except ValueError:
                    partes_convertidas.append(parte)
            
            valores_formatados = " x ".join(partes_convertidas)
            return f"{valores_formatados} {novo_std}"
            
        return match.group(0)

    texto_final = re.sub(padrao_fisico, conv_fisico, texto_final, flags=re.IGNORECASE)

    # --- 3. Conversão de Tamanhos (Roupas/Calçados) ---
    # Apenas se o texto for curto (provavelmente um campo de "Tamanho") ou parecer um tamanho isolado
    if len(texto) < 50: 
        # Calçados
        if 'shoe' in texto.lower() or 'tênis' in texto.lower() or 'calçado' in texto.lower() or 'boot' in texto.lower():
            mapa = CONVERSAO_CALCADOS_MASC if genero_ctx == 'masculino' else CONVERSAO_CALCADOS_FEM
            # Procura número isolado
            match_num = re.search(r'\b(\d+(?:\.\d)?)\b', texto_final)
            if match_num:
                num_us = match_num.group(1)
                if num_us in mapa:
                    texto_final = texto_final.replace(num_us, f"BR {mapa[num_us]} (US {num_us})")
        
        # Roupas (Numérico Feminino)
        elif genero_ctx == 'feminino' and re.match(r'^\s*\d+\s*$', texto_final):
             num = texto_final.strip()
             if num in CONVERSAO_FEMININO:
                 texto_final = f"BR {CONVERSAO_FEMININO[num]} (US {num})"

        # Letras (S, M, L...) - Single Pass Replacement + Lookbehind Protection
        # Cria padrão que evita correspondência se precedido por dígito e espaço/hífen
        # Ex: "10 L" -> "10 GG" (Não queremos isso). "Size L" -> "Size GG" (OK)
        
        def replace_callback(match):
            key = match.group(0).upper() # Normalize case for lookup
            return CONVERSAO_TAMANHOS.get(key, match.group(0))

        # Ordenar chaves por tamanho reverso para evitar match parcial (ex: XXL vs XL) - embora aqui tenhamos word boundary
        keys = sorted(CONVERSAO_TAMANHOS.keys(), key=len, reverse=True)
        # Regex: (?<![\d.,]\s)(?<!['])\b(XXL|XL|L|...)\b
        # Evita: "10 L" (Liters), "Men's" ('s -> S -> M)
        pattern = r'(?<![\d.,]\s)(?<![\'])\b(' + '|'.join(map(re.escape, keys)) + r')\b'
        
        texto_final = re.sub(pattern, replace_callback, texto_final, flags=re.IGNORECASE)

    return texto_final

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
    """Traduz e converte medidas de todos os dados usando Threads"""
    dados_traduzidos = {}
    items_to_process = list(dados.items())
    total_campos = len(items_to_process)
    
    # 1. Identificar Gênero Globalmente para contexto de conversão
    texto_contexto = (str(dados.get('titulo_h1', '')) + ' ' + str(dados.get('about_item', ''))).lower()
    genero_ctx = identificar_genero(texto_contexto)

    def processar_item(item_tuple):
        chave, valor = item_tuple
        chave_trad = TRADUCOES_MANUAIS.get(chave, traduzir_texto(chave.replace('_', ' ').title()))
        valor_processado = None
        
        if isinstance(valor, str):
            if valor.startswith(('http', 'www', 'https')) or valor == "N/A":
                valor_processado = valor
            else:
                if usar_gemini and gemini_key:
                    valor_trad = traduzir_com_gemini(valor, gemini_key)
                else:
                    valor_trad = traduzir_texto(valor)
                # Passa o contexto de genero
                valor_processado = converter_medidas(valor_trad, genero_ctx)
        
        elif isinstance(valor, list):
            lista_trad = []
            for item in valor:
                if isinstance(item, str) and item != "N/A":
                    if usar_gemini and gemini_key:
                        item_trad = traduzir_com_gemini(item, gemini_key)
                    else:
                        item_trad = traduzir_texto(item)
                    lista_trad.append(converter_medidas(item_trad, genero_ctx))
                else:
                    lista_trad.append(item)
            valor_processado = lista_trad
            
        elif isinstance(valor, dict):
            dict_trad = {}
            for sub_chave, sub_valor in valor.items():
                if sub_chave != "N/A":
                    sub_chave_trad = traduzir_texto(sub_chave)
                    if usar_gemini and gemini_key and sub_valor != "N/A":
                        sub_valor_trad = traduzir_com_gemini(sub_valor, gemini_key)
                    else:
                        sub_valor_trad = traduzir_texto(sub_valor)
                    dict_trad[sub_chave_trad] = converter_medidas(sub_valor_trad, genero_ctx)
                else:
                    dict_trad[sub_chave] = sub_valor
            valor_processado = dict_trad
            
        else:
            valor_processado = valor
            
        return chave_trad, valor_processado

    # Execução Paralela
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(processar_item, item): item for item in items_to_process}
        
        completed_count = 0
        for future in concurrent.futures.as_completed(futures):
            chave_trad, valor_processado = future.result()
            dados_traduzidos[chave_trad] = valor_processado
            
            completed_count += 1
            if progress_bar:
                progress_bar.progress(completed_count / total_campos)
                
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
    """Gera formato HTML específico para VTEX"""
    titulo = dados.get('Título', dados.get('titulo_h1', 'Produto'))
    marca = dados.get('Marca', dados.get('marca', 'N/A'))
    
    tech_details = dados.get('Detalhes Técnicos', dados.get('technical_details', {}))
    product_info = dados.get('Informações do Produto', dados.get('product_info', {}))
    
    # Tenta montar uma descrição fluida a partir dos bullets
    about_list = dados.get('Sobre este Item', dados.get('about_item', []))
    descricao = ""
    if isinstance(about_list, list) and about_list and about_list != ["N/A"]:
        # Junta os bullets em um parágrafo único.
        descricao = " ".join(about_list)
    else:
        descricao = f"O {titulo} da marca {marca} oferece qualidade e praticidade."

    specs = {**tech_details, **product_info}
    
    # Formato solicitado:
    # <h4>Titulo<h4> (Note: user showed closing with <h4> too, but standard is </h4>, let's allow standard or user exact req? User said: <h4>...<h4>. I'll stick to standard valid HTML </h4> but keeps the visual structure.)
    # Actually user typed <h4>...<h4>. Browsers treat unclosed tags weirdly. Best to use </h4>.
    # <p>Descricao</p>
    # <endDescription>
    # Chave: Valor <br>
    
    output = f"<h4>{titulo}</h4>\n"
    output += f"<p>{descricao}</p>\n"
    output += "<endDescription>\n"
    
    # Priorizar Marca e Cor se existirem
    if marca != "N/A":
         output += f"Marca: {marca} <br>\n"

    # Adiciona specs
    for chave, valor in specs.items():
        if chave != "N/A" and valor != "N/A":
            # Limpa chave para ficar bonito (remove 'prodDetAttrValue' lixo se houver)
            chave_limpa = chave.strip()
            # Evita duplicar marca
            if chave_limpa.lower() != 'marca' and chave_limpa.lower() != 'nome da marca':
                output += f"{chave_limpa}: {valor} <br>\n"
    
    output += f"ASIN: {dados.get('ASIN', dados.get('asin', 'N/A'))} <br>\n"
    output += "Aviso: Imagens meramente ilustrativas <br>\n"
    
    return output

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
                        value="AIzaSyBJqosIPVowPBHyf4Bm_MM27Kznx7-9oSg",
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