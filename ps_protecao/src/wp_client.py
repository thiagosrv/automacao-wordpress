import requests
from requests.auth import HTTPBasicAuth
import re
import unicodedata
from typing import List, Optional

class WordPressClient:
    def __init__(self, wp_url: str, user: str, app_password: str):
        """
        Inicializa o cliente WordPress REST API.
        wp_url: URL base do site (ex: https://meusite.com)
        user: Nome de usuario
        app_password: Senha de aplicativo (com ou sem espacos)
        """
        self.wp_url = wp_url.rstrip('/')
        self.api_url = f"{self.wp_url}/wp-json/wp/v2"
        # Limpa os espacos da senha de aplicativo se o usuario copiou com espacos
        cleaned_password = app_password.replace(" ", "")
        self.auth = HTTPBasicAuth(user, cleaned_password)

    def _request(self, method: str, endpoint: str, json_data: dict = None, params: dict = None):
        """Faz uma requisicao autenticada para a API REST do WordPress."""
        url = f"{self.api_url}/{endpoint}"
        headers = {
            "User-Agent": "WP-AutoPost-Client/1.0"
        }
        
        try:
            response = requests.request(
                method=method,
                url=url,
                json=json_data,
                params=params,
                auth=self.auth,
                headers=headers,
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            # Tenta ler a mensagem de erro detalhada retornada pelo WordPress
            try:
                err_data = response.json()
                message = err_data.get('message', str(e))
                code = err_data.get('code', 'http_error')
                print(f"[-] Erro na API WordPress ({code}): {message}")
            except Exception:
                print(f"[-] Erro HTTP na chamada para WordPress: {e}")
            raise
        except requests.exceptions.RequestException as e:
            print(f"[-] Erro de conexao ao WordPress: {e}")
            raise

    def _slugify(self, text: str) -> str:
        """Converte uma string em um slug limpo e sem acentos, compativel com WordPress."""
        text = text.lower().strip()
        # Remove os acentos e caracteres especiais normais
        text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
        # Filtra caracteres nao alfanumericos
        text = re.sub(r'[^a-z0-9\s-]', '', text)
        # Substitui espacos e hifens extras
        text = re.sub(r'[\s-]+', '-', text)
        return text.strip('-')

    def get_or_create_tag(self, tag_name: str) -> Optional[int]:
        """
        Busca uma tag pelo nome (ou slug). Se nao existir, cria.
        Retorna o ID inteiro da tag ou None se falhar.
        """
        tag_name = tag_name.strip()
        if not tag_name:
            return None

        slug = self._slugify(tag_name)
        
        try:
            # 1. Procura pela tag usando o slug
            tags = self._request("GET", "tags", params={"slug": slug})
            if tags:
                return tags[0]["id"]
            
            # 2. Se nao encontrou, busca por nome normalizado usando a pesquisa da API
            tags_search = self._request("GET", "tags", params={"search": tag_name})
            for tag in tags_search:
                if self._slugify(tag["name"]) == slug:
                    return tag["id"]
            
            # 3. Se nao encontrou de forma alguma, cria a tag
            print(f"[+] Tag '{tag_name}' nao encontrada. Criando no WordPress...")
            new_tag = self._request("POST", "tags", json_data={"name": tag_name})
            return new_tag["id"]
        except Exception as e:
            print(f"[-] Erro ao obter/criar a tag '{tag_name}': {e}")
            return None

    def get_or_create_category(self, category_name: str) -> Optional[int]:
        """
        Busca uma categoria pelo nome (ou slug). Se nao existir, cria.
        Retorna o ID inteiro da categoria ou None se falhar.
        """
        category_name = category_name.strip()
        if not category_name:
            return None

        slug = self._slugify(category_name)
        
        try:
            # 1. Procura pela categoria usando o slug
            categories = self._request("GET", "categories", params={"slug": slug})
            if categories:
                return categories[0]["id"]
            
            # 2. Se nao encontrou por slug, lista as categorias e busca por nome normalizado
            # (impede erro de termo duplicado caso o slug no WordPress seja ligeiramente diferente)
            all_categories = self._request("GET", "categories", params={"per_page": 100})
            for cat in all_categories:
                if self._slugify(cat["name"]) == slug:
                    return cat["id"]
            
            # 3. Se nao encontrou, cria a categoria
            print(f"[+] Categoria '{category_name}' nao encontrada. Criando no WordPress...")
            new_cat = self._request("POST", "categories", json_data={"name": category_name})
            return new_cat["id"]
        except Exception as e:
            print(f"[-] Erro ao obter/criar a categoria '{category_name}': {e}")
            return None

    def create_post(self, title: str, content: str, excerpt: Optional[str] = None,
                    tags_str: Optional[str] = None, categories_str: Optional[str] = None,
                    status: str = 'draft') -> dict:
        """
        Cria um post no WordPress.
        title: Titulo do post
        content: Conteudo em HTML
        excerpt: Resumo do post (sera adicionado como H2 no topo e no campo de resumo)
        tags_str: Tags separadas por virgula (ex: "wordpress, tutorial")
        categories_str: Categorias separadas por virgula
        status: 'draft' ou 'publish'
        """
        # 1. Verifica se o post ja existe no WordPress pelo slug do titulo (evita duplicidade por timeout)
        slug = self._slugify(title)
        try:
            existing = self._request("GET", "posts", params={"slug": slug, "status": "any"})
            if existing:
                print(f"[!] Post com o slug '{slug}' ja existe no WordPress. Retornando registro existente para evitar duplicidade.")
                return existing[0]
        except Exception as e:
            print(f"[-] Erro ao verificar post existente: {e}")

        # Se houver resumo, adiciona-o no topo do conteudo formatado como H2
        if excerpt:
            content = f"<h2>{excerpt}</h2>\n{content}"

        payload = {
            "title": title,
            "content": content,
            "status": status
        }
        
        if excerpt:
            payload["excerpt"] = excerpt
        
        # Resolve as tags
        if tags_str:
            tag_ids = []
            for t in tags_str.split(','):
                tag_id = self.get_or_create_tag(t)
                if tag_id:
                    tag_ids.append(tag_id)
            if tag_ids:
                payload["tags"] = tag_ids

        # Resolve as categorias
        if categories_str:
            cat_ids = []
            for c in categories_str.split(','):
                cat_id = self.get_or_create_category(c)
                if cat_id:
                    cat_ids.append(cat_id)
            if cat_ids:
                payload["categories"] = cat_ids

        print(f"[+] Enviando post '{title}' para o WordPress (Status: {status})...")
        return self._request("POST", "posts", json_data=payload)

