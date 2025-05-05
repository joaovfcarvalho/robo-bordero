import os
import requests
import logging
from .utils import generate_urls, ensure_directory_exists

def download_pdfs(year, competition_code, download_dir):
    """
    Faz o download de PDFs de borderôs com base no ano e no código da competição.

    Args:
        year (int): Ano dos jogos.
        competition_code (str): Código da competição (142, 424, 242).
        download_dir (str): Diretório onde os PDFs serão salvos.

    Returns:
        list: Lista de arquivos baixados com sucesso.
    """
    ensure_directory_exists(download_dir)
    urls = generate_urls(year, competition_code)
    downloaded_files = []

    for url in urls:
        base_name = os.path.basename(url)
        # Add year to the filename before the extension
        name_part, ext = os.path.splitext(base_name)
        file_name = f"{name_part}_{year}{ext}" # e.g., 2421b_2025.pdf
        file_path = os.path.join(download_dir, file_name)

        if not os.path.exists(file_path):
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()

                with open(file_path, 'wb') as file:
                    file.write(response.content)

                downloaded_files.append(file_path)
                logging.info(f"Downloaded: {file_name}")

            except requests.RequestException as e:
                logging.error(f"Failed to download {url}: {e}")

    return downloaded_files