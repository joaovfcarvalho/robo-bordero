import os
import requests
from .utils import (
    generate_urls, 
    ensure_directory_exists, 
    get_logger,
    handle_error,
    DownloadError
)

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
    logger = get_logger("downloader")
    ensure_directory_exists(download_dir)
    
    try:
        urls = generate_urls(year, competition_code)
    except Exception as e:
        handle_error(
            error=e, 
            log_context={"year": year, "competition_code": competition_code}, 
            log_level="error"
        )
        return []
        
    downloaded_files = []
    total_urls = len(urls)
    
    logger.info("Starting PDF downloads", 
               year=year, 
               competition=competition_code, 
               url_count=total_urls,
               download_dir=str(download_dir))
    
    for idx, url in enumerate(urls):
        base_name = os.path.basename(url)
        # Add year to the filename before the extension
        name_part, ext = os.path.splitext(base_name)
        file_name = f"{name_part}_{year}{ext}" # e.g., 2421b_2025.pdf
        file_path = os.path.join(download_dir, file_name)

        # Log progress every 10 URLs
        if idx % 10 == 0:
            logger.info(f"Download progress", 
                       current=idx, 
                       total=total_urls, 
                       percentage=f"{(idx/total_urls)*100:.1f}%")

        if not os.path.exists(file_path):
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()

                with open(file_path, 'wb') as file:
                    file.write(response.content)

                downloaded_files.append(file_path)
                logger.info("Downloaded file", 
                           filename=file_name, 
                           url=url, 
                           size_bytes=len(response.content))

            except requests.RequestException as e:
                error_context = {
                    "url": url, 
                    "file_name": file_name,
                    "year": year,
                    "competition_code": competition_code
                }
                # We use warning level since this is expected for certain URLs
                handle_error(
                    error=DownloadError(f"Failed to download {url}", error_context),
                    log_context=error_context,
                    log_level="warning"
                )
        else:
            logger.debug("File already exists", filename=file_name)

    logger.info("Download completed", 
               total_downloaded=len(downloaded_files),
               total_attempted=total_urls)
    return downloaded_files