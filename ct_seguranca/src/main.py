import json
import sys
from pathlib import Path
from config import SHEETS_CSV_URL, WP_URL, WP_USER, WP_APP_PASSWORD, POSTADOS_FILE_PATH
from sheets_client import fetch_sheets_data
from wp_client import WordPressClient

# Configuração de postagens por rodada
MAX_POSTS_PER_RUN = 1


def load_posted_ids() -> set:
    """Carrega o arquivo local de posts ja publicados."""
    if not POSTADOS_FILE_PATH.exists():
        return set()
    try:
        with open(POSTADOS_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return set(str(item) for item in data)
    except Exception as e:
        print(f"[-] Erro ao carregar {POSTADOS_FILE_PATH.name}: {e}. Comecando com historico limpo.")
        return set()

def save_posted_ids(posted_ids: set):
    """Salva a lista de posts publicados no arquivo local."""
    try:
        with open(POSTADOS_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(list(posted_ids), f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[-] Erro ao salvar historico no {POSTADOS_FILE_PATH.name}: {e}")

def main():
    print("=" * 60)
    print(" INICIANDO AUTOMACAO ct-seguranca: GOOGLE SHEETS -> WORDPRESS ")
    print("=" * 60)

    # 1. Carrega historico local
    posted_ids = load_posted_ids()
    print(f"[+] Carregados {len(posted_ids)} posts do historico local.")

    # 2. Busca os dados da planilha
    posts = fetch_sheets_data(SHEETS_CSV_URL)
    if not posts:
        print("[-] Nenhuma informacao valida obtida da planilha. Encerrando.")
        sys.exit(0)

    # 3. Inicializa cliente WordPress
    try:
        wp = WordPressClient(WP_URL, WP_USER, WP_APP_PASSWORD)
    except Exception as e:
        print(f"[-] Erro ao inicializar cliente WordPress: {e}")
        sys.exit(1)

    # 4. Processa cada linha da planilha
    novos_posts_processados = 0
    erros = 0

    for index, row in enumerate(posts):
        # Para evitar spam se ja atingimos o limite de 2 posts nesta rodada
        if novos_posts_processados >= MAX_POSTS_PER_RUN:
            print(f"[+] Limite de {MAX_POSTS_PER_RUN} posts atingido nesta execucao. Parando.")
            break

        # Define a chave unica usando o 'ID' ou o 'Post Title'
        row_id = row.get("ID") or row.get("Post Title") or row.get("Titulo")
        
        if not row_id:
            print(f"[-] Linha {index + 2} ignorada por nao conter ID nem Titulo.")
            continue
            
        row_id_str = str(row_id).strip()

        # Pula se ja foi publicado anteriormente
        if row_id_str in posted_ids:
            continue

        titulo = row.get("Post Title", "").strip() or row.get("Titulo", "").strip()
        conteudo = row.get("Conteudo", "").strip()
        excerpt = (row.get("Resumo do Artigo") or row.get("Excerpt") or row.get("Resumo") or "").strip()
        tags = row.get("Tags", "").strip()
        
        categorias = row.get("Categoria", "").strip() or row.get("Categorias", "").strip()
        if not categorias or categorias.lower() == "geral":
            categorias = "Últimas Noticias"
        
        # Padrão de status: 'publish' para publicacao automatica imediata
        status = row.get("Status", "publish").strip().lower()
        if not status or status == "draft" or status not in ['draft', 'publish', 'pending', 'private']:
            status = 'publish'

        if not titulo or not conteudo:
            print(f"[-] Linha com ID {row_id_str} pulada (Titulo ou Conteudo ausentes).")
            continue

        print(f"\n[+] Processando post ID: {row_id_str} | Titulo: '{titulo}'")

        try:
            # Cria o post no WordPress
            result = wp.create_post(
                title=titulo,
                content=conteudo,
                excerpt=excerpt,
                tags_str=tags,
                categories_str=categorias,
                status=status
            )
            
            post_id = result.get("id")
            post_link = result.get("link")
            print(f"[OK] Sucesso! Criado no WordPress com ID: {post_id}")
            print(f"    Link: {post_link}")

            # Registra no historico e salva imediatamente
            posted_ids.add(row_id_str)
            save_posted_ids(posted_ids)
            novos_posts_processados += 1

        except Exception as e:
            print(f"[ERR] Falha ao publicar post ID {row_id_str}: {e}")
            print("[-] Encerrando execucao devido a erro para evitar postagens em massa ou duplicatas.")
            erros += 1
            break

    print("\n" + "=" * 60)
    print(" RESUMO DA EXECUCAO ")
    print("=" * 60)
    print(f"Novos posts publicados: {novos_posts_processados}")
    print(f"Erros encontrados: {erros}")
    print(f"Total de posts no historico agora: {len(posted_ids)}")
    print("=" * 60)

if __name__ == "__main__":
    main()
