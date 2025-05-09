import os
import requests
from .utils import (
    generate_urls, 
    ensure_directory_exists, 
    get_logger,
    handle_error,
    DownloadError,
    OperationCancelledError # Added
)
from typing import Callable, Optional # Added
import threading # Added

def download_pdfs(year, competition_code, download_dir, 
                  progress_callback: Optional[Callable[[float], None]] = None, 
                  cancel_event: Optional[threading.Event] = None):
    """
    Faz o download de PDFs de borderôs com base no ano e no código da competição.

    Args:
        year (int): Ano dos jogos.
        competition_code (str): Código da competição (142, 424, 242).
        download_dir (str): Diretório onde os PDFs serão salvos.
        progress_callback (Optional[Callable[[float], None]]): Callback to report progress (0.0 to 100.0).
        cancel_event (Optional[threading.Event]): Event to signal cancellation.

    Returns:
        list: Lista de arquivos baixados com sucesso.
        
    Raises:
        OperationCancelledError: If the operation is cancelled.
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
    
    if total_urls == 0:
        if progress_callback:
            progress_callback(100.0)
        return []

    logger.info("Starting PDF downloads", 
               year=year, 
               competition=competition_code, 
               url_count=total_urls,
               download_dir=str(download_dir))
    
    for idx, url in enumerate(urls):
        if cancel_event and cancel_event.is_set():
            logger.info("Download operation cancelled by user.")
            raise OperationCancelledError("Download cancelled by user.")

        base_name = os.path.basename(url)
        name_part, ext = os.path.splitext(base_name)
        file_name = f"{name_part}_{year}{ext}"
        file_path = os.path.join(download_dir, file_name)

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
                handle_error(
                    error=DownloadError(f"Failed to download {url}: {str(e)}", error_context), # Pass original error string
                    log_context=error_context,
                    log_level="warning"
                )
        else:
            logger.debug("File already exists", filename=file_name)
        
        if progress_callback:
            progress_percentage = ((idx + 1) / total_urls) * 100
            progress_callback(progress_percentage)

    logger.info("Download completed", 
               total_downloaded=len(downloaded_files),
               total_attempted=total_urls)
    return downloaded_files