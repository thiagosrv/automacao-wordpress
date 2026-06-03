import re
import markdown

def parse_markdown_file(filepath: str) -> dict:
    """
    Le um arquivo .md, extrai metadados do cabecalho (Titulo, Excerpt, Categorias, Tags)
    e converte o corpo do texto em HTML.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"[-] Erro ao ler o arquivo {filepath}: {e}")
        raise

    title = ""
    excerpt = ""
    categories = "News"
    tags = ""
    content_lines = []

    # Regex para identificar metadados comuns nos arquivos
    title_pat = re.compile(r'^#\s*(.*)$')
    meta_desc_pat = re.compile(r'^\*\*Meta Description:\*\*\s*(.*)$', re.IGNORECASE)
    categories_pat = re.compile(r'^\*\*(Categorias|Categories):\*\*\s*(.*)$', re.IGNORECASE)
    tags_pat = re.compile(r'^\*\*Tags:\*\*\s*(.*)$', re.IGNORECASE)
    meta_title_pat = re.compile(r'^\*\*Meta Title:\*\*\s*(.*)$', re.IGNORECASE)

    in_metadata_block = True

    for line in lines:
        cleaned_line = line.strip()
        
        # 1. Tenta extrair o Titulo do Post (iniciando com #)
        title_match = title_pat.match(cleaned_line)
        if title_match:
            title = title_match.group(1).strip()
            continue

        # 2. Ignora o Meta Title (usado apenas no SEO Yoast/RankMath local)
        if meta_title_pat.match(cleaned_line):
            continue

        # 3. Extrai o Meta Description como Excerpt (Resumo)
        meta_desc_match = meta_desc_pat.match(cleaned_line)
        if meta_desc_match:
            excerpt = meta_desc_match.group(1).strip()
            continue

        # 4. Extrai Categorias
        categories_match = categories_pat.match(cleaned_line)
        if categories_match:
            categories = categories_match.group(2).strip()
            continue

        # 5. Extrai Tags
        tags_match = tags_pat.match(cleaned_line)
        if tags_match:
            tags = tags_match.group(1).strip()
            continue

        # 6. Pula linhas vazias ate comecar o conteudo de fato
        if in_metadata_block:
            if not cleaned_line:
                continue
            else:
                in_metadata_block = False

        content_lines.append(line)

    # Reconstrói o markdown do corpo
    markdown_content = "".join(content_lines).strip()
    
    # Se nao encontrar titulo no arquivo, usa o nome do arquivo limpo
    if not title:
        title = filepath.stem.replace('_', ' ').title()

    # Converte o Markdown para HTML limpo
    html_content = markdown.markdown(
        markdown_content,
        extensions=['extra', 'nl2br']
    )

    return {
        "title": title,
        "excerpt": excerpt,
        "categories": categories,
        "tags": tags,
        "content": html_content
    }
