import csv
import requests
import re
import time
from typing import List, Dict

def convert_to_csv_url(url: str) -> str:
    """
    Converte um link padrao de visualizacao/edicao do Google Sheets em link de exportacao CSV.
    Ex: https://docs.google.com/spreadsheets/d/12345/edit?usp=sharing -> .../export?format=csv
    """
    if "docs.google.com/spreadsheets" in url:
        # Se ja for um link de exportacao, retorna ele mesmo
        if "/export?" in url:
            return url
        # Tenta substituir /edit... por /export?format=csv
        url_converted = re.sub(r'/edit.*$', '/export?format=csv', url)
        return url_converted
    return url

def fetch_sheets_data(csv_url: str) -> List[Dict[str, str]]:
    """
    Baixa e processa a planilha do Google Sheets no formato CSV.
    Retorna uma lista de dicionarios contendo os dados de cada linha.
    Com suporte a retry e user-agent customizado para evitar erros 500 do Google.
    """
    download_url = convert_to_csv_url(csv_url)
    print(f"[+] Baixando dados da planilha do link: {download_url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    max_retries = 5
    backoff_factor = 2
    response = None
    
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(download_url, headers=headers, timeout=15)
            response.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            print(f"[-] Tentativa {attempt}/{max_retries} de baixar a planilha falhou: {e}")
            if attempt < max_retries:
                sleep_time = backoff_factor ** attempt
                print(f"    Aguardando {sleep_time} segundos antes de tentar novamente...")
                time.sleep(sleep_time)
            else:
                print("[-] Limite de tentativas de download atingido. Encerrando.")
                print("Certifique-se de que a planilha esta compartilhada como 'Qualquer pessoa com o link pode ler'.")
                return []
    
    if response is None:
        return []

    # Decodifica o conteudo como UTF-8
    csv_content = response.content.decode('utf-8')
    csv_lines = csv_content.splitlines()
    
    if not csv_lines:
        print("[-] Planilha vazia ou com formato invalido.")
        return []
        
    reader = csv.DictReader(csv_lines)
    posts = []
    
    # Normaliza as chaves do dicionario (remove acentos e espacos extras se necessario)
    # Mas assumiremos cabecalhos limpos por simplicidade ou fazemos um map limpo.
    for row in reader:
        # Garante que cada valor tenha espacos extras removidos
        cleaned_row = {key.strip() if key else "": val.strip() if val else "" for key, val in row.items()}
        # Filtra linhas vazias (sem ID ou Titulo)
        if cleaned_row.get("ID") or cleaned_row.get("Titulo"):
            posts.append(cleaned_row)
            
    print(f"[+] {len(posts)} linhas lidas com sucesso do Google Sheets.")
    return posts
