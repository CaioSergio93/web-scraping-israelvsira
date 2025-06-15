import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import streamlit as st
from urllib.parse import urljoin
from deep_translator import GoogleTranslator
import time
from threading import Thread
from queue import Queue
import os

# Configuração da página
st.set_page_config(
    page_title="Notícias Irã vs. Israel",
    page_icon="🌍",
    layout="wide"
)

# Dados das fontes atualizadas
fontes = {
    "BBC News": {
        "url": "https://www.bbc.com/news",
        "selector_artigo": "article",
        "selector_imagem": "img",
        "selector_titulo": ["h1", "h2", "h3"],
        "max_noticias": 10
    },
    "Al Jazeera": {
        "url": "https://www.aljazeera.com/",
        "selector_artigo": "article",
        "selector_imagem": "img",
        "selector_titulo": ["h1", "h2", "h3"],
        "max_noticias": 10
    },
    "Reuters": {
        "url": "https://www.reuters.com/world/middle-east/",
        "selector_artigo": "article",
        "selector_imagem": "img",
        "selector_titulo": ["h1", "h2", "h3"],
        "max_noticias": 10
    },
    "Times of Israel": {
        "url": "https://www.timesofisrael.com/",
        "selector_artigo": "article",
        "selector_imagem": "img",
        "selector_titulo": ["h1", "h2", "h3"],
        "max_noticias": 8
    },
    "Jerusalem Post": {
        "url": "https://www.jpost.com/",
        "selector_artigo": "article",
        "selector_imagem": "img",
        "selector_titulo": ["h1", "h2", "h3"],
        "max_noticias": 8
    },
    "Haaretz": {
        "url": "https://www.haaretz.com/",
        "selector_artigo": "article",
        "selector_imagem": "img",
        "selector_titulo": ["h1", "h2", "h3"],
        "max_noticias": 6
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

# Fila para armazenar notícias
noticias_queue = Queue()

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
    xlsx_path = f'data/noticias_{timestamp}.xlsx'
    
    # Salvar em CSV
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    
    # Salvar em XLSX
    df.to_excel(xlsx_path, index=False, engine='openpyxl')
    
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
    
    # Versão XLSX do consolidado
    consolidado.to_excel('data/noticias_consolidado.xlsx', index=False, engine='openpyxl')

def scrape_noticias(palavras_chave=PALAVRAS_CHAVE_PADRAO):
    noticias_coletadas = []
    
    for fonte, config in fontes.items():
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9'
            }
            
            response = requests.get(config['url'], headers=headers, timeout=20)
            response.raise_for_status()
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
                
                except Exception as e:
                    st.warning(f"Erro ao processar artigo de {fonte}: {str(e)}")
                    continue
                
        except Exception as e:
            st.warning(f"Erro ao acessar {fonte}: {str(e)}")
            continue
    
    # Ordenar por relevância e depois por data
    noticias_coletadas.sort(key=lambda x: (-x['relevante'], -x['timestamp']))
    
    return noticias_coletadas[:20]  # Limite máximo de 20 notícias

def traduzir_texto(texto):
    try:
        tradutor = GoogleTranslator(source='auto', target='pt')
        return tradutor.translate(texto[:500])  # Limita o tamanho para evitar erros
    except Exception as e:
        st.warning(f"Erro na tradução: {str(e)}")
        return texto

def processar_traducoes(noticias):
    noticias_traduzidas = []
    
    for noticia in noticias:
        try:
            time.sleep(0.3)  # Delay reduzido para melhor performance
            noticia['titulo_traduzido'] = traduzir_texto(noticia['titulo_original'])
            noticias_traduzidas.append(noticia)
        except Exception as e:
            st.warning(f"Erro ao traduzir notícia: {str(e)}")
            continue
    
    return noticias_traduzidas

def atualizar_noticias():
    while True:
        try:
            noticias = scrape_noticias()
            noticias_traduzidas = processar_traducoes(noticias)
            noticias_queue.put(noticias_traduzidas)
            
            # Salvar as notícias em arquivos
            csv_path, xlsx_path = salvar_noticias(noticias_traduzidas)
            print(f"Notícias salvas em {csv_path} e {xlsx_path}")
            
        except Exception as e:
            st.error(f"Erro na atualização: {str(e)}")
        
        # Espera 5 minutos antes da próxima atualização
        time.sleep(300)

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
    Atualizado automaticamente a cada 5 minutos.
    </div>
    """, unsafe_allow_html=True)
    
    # Controles na parte superior
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**Última atualização:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    with col2:
        if st.button("🔄 Atualizar Agora", help="Forçar atualização imediata das notícias"):
            st.cache_data.clear()
            with st.spinner("Atualizando notícias..."):
                noticias = scrape_noticias()
                noticias_traduzidas = processar_traducoes(noticias)
                noticias_queue.put(noticias_traduzidas)
    
    # Inicia a thread de atualização automática
    if 'update_thread' not in st.session_state:
        st.session_state.update_thread = Thread(target=atualizar_noticias, daemon=True)
        st.session_state.update_thread.start()
    
    # Exibição das notícias
    placeholder = st.empty()
    
    while True:
        if not noticias_queue.empty():
            noticias = noticias_queue.get()
            
            with placeholder.container():
                st.subheader(f"📰 Últimas Notícias ({len(noticias)} encontradas)")
                st.markdown("---")
                
                for i, noticia in enumerate(noticias, 1):
                    exibir_noticia(noticia, i)
                
                st.markdown("---")
                st.caption("""
                Sistema automático de coleta e tradução de notícias. 
                As traduções são geradas automaticamente e podem conter imprecisões.
                """)
        
        time.sleep(1)  # Reduz o consumo de CPU

if __name__ == "__main__":
    main()