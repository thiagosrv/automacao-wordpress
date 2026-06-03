import json
import sys
from pathlib import Path
from config import WP_URL, WP_USER, WP_APP_PASSWORD, POSTADOS_FILE_PATH, ARTIGOS_DIR_PATH
from parser import parse_markdown_file
from wp_client import WordPressClient

def load_posted_files() -> set:
    """Carrega o arquivo local de arquivos ja publicados."""
    if not POSTADOS_FILE_PATH.exists():
        return set()
    try:
        with open(POSTADOS_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return set(str(item) for item in data)
    except Exception as e:
        print(f"[-] Erro ao carregar {POSTADOS_FILE_PATH.name}: {e}. Comecando com historico limpo.")
        return set()

def save_posted_files(posted_files: set):
    """Salva a lista de arquivos publicados no arquivo local."""
    try:
        with open(POSTADOS_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(sorted(list(posted_files)), f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[-] Erro ao salvar historico no {POSTADOS_FILE_PATH.name}: {e}")

def main():
    print("=" * 60)
    print(" INICIANDO AUTOMACAO BLOG: MARKDOWN (.md) -> WORDPRESS ")
    print("=" * 60)

    # 1. Carrega historico de arquivos publicados
    posted_files = load_posted_files()
    print(f"[+] Carregados {len(posted_files)} arquivos do historico local.")

    # 2. Varre os arquivos .md da pasta artigos
    if not ARTIGOS_DIR_PATH.exists():
        print(f"[-] Erro: A pasta de artigos '{ARTIGOS_DIR_PATH}' nao existe! Encerrando.")
        sys.exit(1)

    md_files = sorted(list(ARTIGOS_DIR_PATH.glob('*.md')))
    
    # Filtra arquivos de planejamento ou controle que nao sao posts
    files_to_process = []
    for filepath in md_files:
        filename = filepath.name
        if filename == 'temas_artigos_facilities.md':
            continue
        if filename in posted_files:
            continue
        files_to_process.append(filepath)

    if not files_to_process:
        print("[+] Nenhum novo arquivo .md encontrado para publicar. Finalizando.")
        sys.exit(0)

    print(f"[+] Encontrados {len(files_to_process)} novos arquivos .md para processar.")

    # 3. Inicializa cliente WordPress
    try:
        wp = WordPressClient(WP_URL, WP_USER, WP_APP_PASSWORD)
    except Exception as e:
        print(f"[-] Erro ao inicializar cliente WordPress: {e}")
        sys.exit(1)

    # 4. Processa apenas o primeiro artigo disponivel (1 post por rodada)
    filepath = files_to_process[0]
    filename = filepath.name
    print(f"\n[+] Lendo e processando: '{filename}'")

    try:
        # Extrai metadados e conteudo em HTML
        post_data = parse_markdown_file(filepath)

        # Se não especificou categoria no arquivo, usa "News"
        categorias_post = post_data["categories"]
        if not categorias_post or categorias_post.strip().lower() == "geral":
            categorias_post = "News"

        # Publica no WordPress
        result = wp.create_post(
            title=post_data["title"],
            content=post_data["content"],
            excerpt=post_data["excerpt"],
            tags_str=post_data["tags"],
            categories_str=categorias_post,
            status="publish"
        )

        post_id = result.get("id")
        post_link = result.get("link")
        print(f"[OK] Sucesso! Criado no WordPress com ID: {post_id}")
        print(f"    Link: {post_link}")

        # Atualiza historico
        posted_files.add(filename)
        save_posted_files(posted_files)
        print(f"[+] Arquivo '{filename}' marcado como publicado.")

    except Exception as e:
        print(f"[ERR] Falha ao publicar artigo '{filename}': {e}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print(" EXECUCAO CONCLUIDA COM SUCESSO ")
    print("=" * 60)

if __name__ == "__main__":
    main()
