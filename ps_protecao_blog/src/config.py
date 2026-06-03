import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Encontra a raiz do projeto (uma pasta acima do src)
BASE_DIR = Path(__file__).resolve().parent.parent

# Carrega o arquivo .env se ele existir (para testes locais)
env_path = BASE_DIR / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()  # fallback

def get_env_variable(name: str, required: bool = True) -> str:
    """Retorna uma variavel de ambiente ou encerra o programa se variavel obrigatoria estiver ausente."""
    value = os.getenv(name)
    if not value and required:
        print(f"[-] ERRO: A variavel de ambiente '{name}' nao foi configurada!")
        sys.exit(1)
    return value or ""

# URLs e credenciais do WordPress (recebe via environment)
WP_URL = get_env_variable("WP_URL").rstrip('/')
WP_USER = get_env_variable("WP_USER")
WP_APP_PASSWORD = get_env_variable("WP_APP_PASSWORD")

# Caminhos locais
POSTADOS_FILE_PATH = BASE_DIR / 'postados.json'
ARTIGOS_DIR_PATH = BASE_DIR / 'artigos'
