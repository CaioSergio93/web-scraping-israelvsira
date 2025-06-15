import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import streamlit as st
from urllib.parse import urljoin
from deep_translator import GoogleTranslator
import time
import os
from streamlit_autorefresh import st_autorefresh

# Configuração da página
st.set_page_config(
    page_title="Notícias Irã vs. Israel",
    page_icon="🌍",
    layout="wide"
)

# Dados das fontes atualizadas com headers personalizados
fontes = {
    "BBC News": {
        "url": "https://www.bbc.com/news",
        "selector_artigo": "article",
        "selector_imagem": "img",
        "selector_titulo": ["h1", "h2", "h3"],
        "max_noticias": 10,
        "headers": {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        }
    },
    "Al Jazeera": {
        "url": "https://www.aljazeera.com/",
        "selector_artigo": "article",
        "selector_imagem": "img",
        "selector_titulo": ["h1", "h2", "h3"],
        "max_noticias": 10,
        "headers": {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        }
    },
    "Reuters": {
        "url": "https://www.reuters.com/world/middle-east/",
        "selector_artigo": "article",
        "selector_imagem": "img",
        "selector_titulo": ["h1", "h2", "h3"],
        "max_noticias": 10,
        "headers": {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        }
    },
    "Times of Israel": {
        "url": "https://www.timesofisrael.com/",
        "selector_artigo": "article",
        "selector_imagem": "img",
        "selector_titulo": ["h1", "h2", "h3"],
        "max_noticias": 8,
        "headers": {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/'
        },
        "timeout": 15
    },
    "Jerusalem Post": {
        "url": "https://www.jpost.com/",
        "selector_artigo": "article",
        "selector_imagem": "img",
        "selector_titulo": ["h1", "h2", "h3"],
        "max_noticias": 8,
        "headers": {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/'
        },
        "timeout": 15
    },
    "Haaretz": {
        "url": "https://www.haaretz.com/",
        "selector_artigo": "article",
        "selector_imagem": "img",
        "selector_titulo": ["h1", "h2", "h3"],
        "max_noticias": 6,
        "headers": {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/'
        },
        "timeout": 15
    }
}

# Palavras-chave ampliadas
PALAVRAS_CHAVE_PADRAO = [
    "Iran", "Israel", "attack", "conflict", "war",
    "nuclear", "weapon", "missile", "drone",
    "ally", "allies", "military", "defense",
    "Hamas", "Hezbollah", "Gaza", "West Bank",
    "sanctions", "diplomacy", "UN", "security"
]

def criar_pasta_dados():
    """Cria a pasta de dados se não existir"""
    if not os.path.exists('data'):
        os.makedirs('data')

def salvar_noticias(noticias):
    """Salva as notícias nos formatos CSV e XLSX com timestamp"""
    criar_pasta_dados()
    
    # Criar DataFrame
    df = pd.DataFrame(noticias)
    
    # Remover colunas temporárias
    df = df.drop(columns=['timestamp', 'relevante'], errors='ignore')
    
    # Adicionar data de coleta
    df['data_coleta'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Nome do arquivo com timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_path = f'data/noticias_{timestamp}.csv'
    
    # Salvar em CSV
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    
    # Tentar salvar em XLSX se openpyxl estiver instalado
    try:
        import openpyxl
        xlsx_path = f'data/noticias_{timestamp}.xlsx'
        df.to_excel(xlsx_path, index=False, engine='openpyxl')
    except ImportError:
        xlsx_path = None
    
    # Salvar arquivo consolidado
    salvar_consolidado(df)
    
    return csv_path, xlsx_path

def salvar_consolidado(novas_noticias):
    """Salva todas as notícias em um arquivo consolidado"""
    consolidado_path = 'data/noticias_consolidado.csv'
    
    if os.path.exists(consolidado_path):
        # Carrega o existente e adiciona as novas
        consolidado = pd.read_csv(consolidado_path)
        consolidado = pd.concat([consolidado, novas_noticias], ignore_index=True)
    else:
        consolidado = novas_noticias
    
    # Remove duplicados baseado no link
    consolidado = consolidado.drop_duplicates(subset=['link'], keep='last')
    
    # Salva o consolidado
    consolidado.to_csv(consolidado_path, index=False, encoding='utf-8-sig')
    
    # Versão XLSX do consolidado (se openpyxl estiver instalado)
    try:
        import openpyxl
        consolidado.to_excel('data/noticias_consolidado.xlsx', index=False, engine='openpyxl')
    except ImportError:
        pass

@st.cache_data(ttl=300)  # Cache de 5 minutos
def scrape_noticias(palavras_chave=PALAVRAS_CHAVE_PADRAO):
    noticias_coletadas = []
    fontes_indisponiveis = []
    
    for fonte, config in fontes.items():
        try:
            timeout = config.get('timeout', 10)
            
            try:
                response = requests.get(
                    config['url'],
                    headers=config['headers'],
                    timeout=timeout
                )
                response.raise_for_status()
            except Exception:
                fontes_indisponiveis.append(fonte)
                continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            artigos = soup.select(config['selector_artigo'])[:config['max_noticias']]
            
            for artigo in artigos:
                try:
                    titulo_elem = next((artigo.find(tag) for tag in config['selector_titulo'] if artigo.find(tag)), None)
                    
                    if not titulo_elem:
                        continue
                        
                    titulo = titulo_elem.get_text().strip()
                    
                    # Obter link
                    link_elem = artigo.find('a', href=True)
                    link = link_elem['href'] if link_elem else None
                    if link and not link.startswith('http'):
                        link = urljoin(config['url'], link)
                    
                    # Obter imagem
                    img_elem = artigo.select_one(config['selector_imagem'])
                    img_url = None
                    if img_elem:
                        img_url = img_elem.get('src') or img_elem.get('data-src')
                        if img_url and not img_url.startswith('http'):
                            img_url = urljoin(config['url'], img_url)
                    
                    # Obter data
                    data_elem = artigo.find('time') or artigo.find(class_=lambda x: x and 'date' in x.lower())
                    data = data_elem['datetime'] if data_elem and data_elem.has_attr('datetime') else str(datetime.now())
                    
                    # Verificar relevância
                    relevante = any(p.lower() in titulo.lower() for p in palavras_chave)
                    
                    noticias_coletadas.append({
                        'fonte': fonte,
                        'titulo_original': titulo,
                        'link': link,
                        'imagem': img_url,
                        'data': data,
                        'timestamp': datetime.now().timestamp(),
                        'relevante': relevante
                    })
                
                except Exception:
                    continue
                
        except Exception:
            fontes_indisponiveis.append(fonte)
            continue
    
    
    # Ordenar por relevância e depois por data
    noticias_coletadas.sort(key=lambda x: (-x['relevante'], -x['timestamp']))
    
    return noticias_coletadas[:20]  # Limite máximo de 20 notícias

@st.cache_data(ttl=300)  # Cache de 5 minutos
def processar_traducoes(noticias):
    noticias_traduzidas = []
    
    for noticia in noticias:
        try:
            time.sleep(0.3)  # Delay reduzido para melhor performance
            noticia['titulo_traduzido'] = traduzir_texto(noticia['titulo_original'])
            noticias_traduzidas.append(noticia)
        except Exception:
            # Mantém a notícia com o título original se a tradução falhar
            noticia['titulo_traduzido'] = noticia['titulo_original']
            noticias_traduzidas.append(noticia)
    
    return noticias_traduzidas

def traduzir_texto(texto):
    try:
        tradutor = GoogleTranslator(source='auto', target='pt')
        return tradutor.translate(texto[:500])  # Limita o tamanho para evitar erros
    except Exception:
        return texto  # Retorna o texto original se a tradução falhar

def exibir_noticia(noticia, index):
    with st.container(border=True):
        col1, col2 = st.columns([1, 3])
        
        with col1:
            if noticia.get('imagem'):
                st.image(noticia['imagem'], width=200, use_container_width=True)
            else:
                st.image("https://via.placeholder.com/200x150?text=Sem+Imagem", 
                        width=200, 
                        use_container_width=True)
        
        with col2:
            if noticia.get('relevante', True):
                st.markdown("🔍 **Notícia relevante**")
            st.subheader(f"{noticia.get('titulo_traduzido', 'Sem título')}")
            st.caption(f"**Fonte:** {noticia.get('fonte', '')} | **Data:** {noticia.get('data', '')}")
            
            if noticia.get('link'):
                st.markdown(f"[📰 Ler notícia completa]({noticia['link']})")

@st.cache_resource
def carregar_noticias():
    with st.spinner("Coletando e processando notícias..."):
        noticias = scrape_noticias()
        noticias_traduzidas = processar_traducoes(noticias)
        salvar_noticias(noticias_traduzidas)
        return noticias_traduzidas

def main():
    st.title("🌍 Notícias Irã vs. Israel")
    
    # Cabeçalho informativo
    st.markdown("""
    <style>
    .info-header {
        font-size: 16px;
        color: #666;
        margin-bottom: 20px;
    }
    </style>
    <div class="info-header">
    Monitoramento de notícias internacionais sobre o conflito entre Irã e Israel.
    </div>
    """, unsafe_allow_html=True)
    
    # Controles
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**Última atualização:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    with col2:
        if st.button("🔄 Atualizar Agora", help="Forçar atualização imediata das notícias"):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.rerun()
    
    # Carregar notícias
    noticias = carregar_noticias()
    
    # Exibir notícias
    st.subheader(f"📰 Últimas Notícias ({len(noticias)} encontradas)")
    st.markdown("---")
    
    for i, noticia in enumerate(noticias, 1):
        exibir_noticia(noticia, i)
    
    st.markdown("---")
    st.caption("""
    Sistema automático de coleta e tradução de notícias. 
    As traduções são geradas automaticamente e podem conter imprecisões.
    """)
    
    # Configura auto-recarga (5 minutos)
    st_autorefresh(interval=5*60*1000, key="auto_refresh")

if __name__ == "__main__":
    # Verifica e informa sobre dependências ausentes
    try:
        import openpyxl
    except ImportError:
        st.warning("Para exportar para Excel, instale o openpyxl: pip install openpyxl")
    
    main()