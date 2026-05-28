import csv
import requests
import re
from typing import List, Dict

def convert_to_csv_url(url: str) -> str:
    """
    Converte um link padrao de visualizacao/edicao do Google Sheets em link de exportacao CSV.
    """
    if "docs.google.com/spreadsheets" in url:
        if "/export?" in url:
            return url
        url_converted = re.sub(r'/edit.*$', '/export?format=csv', url)
        return url_converted
    return url

def fetch_sheets_data(csv_url: str) -> List[Dict[str, str]]:
    """
    Baixa e processa a planilha do Google Sheets no formato CSV.
    Retorna uma lista de dicionarios contendo os dados de cada linha.
    """
    download_url = convert_to_csv_url(csv_url)
    print(f"[+] Baixando dados da planilha do link: {download_url}")
    
    try:
        response = requests.get(download_url, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[-] Erro ao tentar baixar a planilha: {e}")
        print("Certifique-se de que a planilha esta compartilhada como 'Qualquer pessoa com o link pode ler'.")
        return []
    
    csv_content = response.content.decode('utf-8')
    csv_lines = csv_content.splitlines()
    
    if not csv_lines:
        print("[-] Planilha vazia ou com formato invalido.")
        return []

    # Encontra a primeira linha de cabecalho valida (ignora linhas vazias ou apenas com virgulas/espacos no inicio)
    start_index = 0
    for idx, line in enumerate(csv_lines):
        if re.sub(r'[\s,",]*', '', line):
            start_index = idx
            break
            
    valid_csv_lines = csv_lines[start_index:]
    if not valid_csv_lines:
        print("[-] Nenhuma linha de cabecalho valida encontrada no CSV.")
        return []
        
    reader = csv.DictReader(valid_csv_lines)
    posts = []
    
    for row in reader:
        cleaned_row = {key.strip() if key else "": val.strip() if val else "" for key, val in row.items()}
        # Filtra linhas vazias (busca por ID ou Post Title)
        if cleaned_row.get("ID") or cleaned_row.get("Post Title") or cleaned_row.get("Titulo"):
            posts.append(cleaned_row)
            
    print(f"[+] {len(posts)} linhas lidas com sucesso do Google Sheets.")
    return posts
