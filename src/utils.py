import os
from dotenv import load_dotenv
import logging
import logging.handlers # Import handlers

def load_env_variables():
    """Load environment variables from the .env file."""
    load_dotenv()

def setup_logging():
    """
    Configures rotating logging for the application.
    Logs daily, keeping the last 7 days.
    """
    log_file = 'cbf_robot.log'
    log_level = logging.INFO
    log_format = '%(asctime)s - %(levelname)s - %(message)s'

    # Create formatter
    formatter = logging.Formatter(log_format)

    # Create a handler that rotates daily and keeps 7 backups
    # 'D' means daily rotation, interval=1 means rotate every 1 day
    handler = logging.handlers.TimedRotatingFileHandler(
        log_file,
        when='D',
        interval=1,
        backupCount=7, # Keep logs for 7 days
        encoding='utf-8' # Specify encoding
    )
    handler.setFormatter(formatter)

    # Get the root logger and add the handler
    # Remove any existing handlers first to avoid duplicate logs if called multiple times
    logger = logging.getLogger()
    logger.setLevel(log_level)
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.addHandler(handler)

def generate_urls(year, competition_code):
    """
    Gera URLs para download de borderôs com base no ano e no código da competição,
    considerando as regras de numeração específicas.

    Args:
        year (int): Ano dos jogos.
        competition_code (str): Código da competição (142, 424, 242).

    Returns:
        list: Lista de URLs geradas.
    """
    urls = []
    base_url = f"https://conteudo.cbf.com.br/sumulas/{year}/"

    if competition_code == "142": # Série A - Rounds 1-38, Matches 0-9
        for round_number in range(1, 39): # Rounds 1 to 38
            for match_in_round in range(10): # Matches 0 to 9
                match_id = f"{competition_code}{round_number}{match_in_round}"
                url = f"{base_url}{match_id}b.pdf"
                urls.append(url)

    elif competition_code == "424": # Copa do Brasil - Sequential 1 to 150
        for match_number in range(1, 151): # Matches 1 to 150
            match_id = f"{competition_code}{match_number}"
            url = f"{base_url}{match_id}b.pdf"
            urls.append(url)

    elif competition_code == "242": # Série B - Sequential 1 to 380
        for match_number in range(1, 381): # Matches 1 to 380
            match_id = f"{competition_code}{match_number}"
            url = f"{base_url}{match_id}b.pdf"
            urls.append(url)

    else:
        logging.warning(f"Código de competição desconhecido ou não suportado: {competition_code}")

    return urls

def ensure_directory_exists(directory):
    """
    Garante que o diretório especificado existe, criando-o se necessário.

    Args:
        directory (str): Caminho do diretório.
    """
    if not os.path.exists(directory):
        os.makedirs(directory)