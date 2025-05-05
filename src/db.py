import os
import csv
import logging
# Removed setup_logging import

# Removed setup_logging() call

def append_to_csv(file_path, data, headers):
    """
    Adiciona dados a um arquivo CSV, criando o arquivo com cabeçalho se ele não existir.

    Args:
        file_path (str): Caminho do arquivo CSV.
        data (list): Lista de dicionários contendo os dados a serem adicionados.
        headers (list): Lista de cabeçalhos do CSV.
    """
    try:
        file_exists = os.path.exists(file_path)

        with open(file_path, mode='a', newline='', encoding='utf-8') as csv_file:
            # Ensure all data dictionaries contain all header keys, adding missing ones with None
            processed_data = []
            for row in data:
                processed_row = {header: row.get(header) for header in headers}
                processed_data.append(processed_row)

            writer = csv.DictWriter(csv_file, fieldnames=headers, extrasaction='ignore') # Ignore extra fields in data not in headers

            if not file_exists or os.path.getsize(file_path) == 0: # Check size to handle empty file case
                writer.writeheader()

            writer.writerows(processed_data)
    except IOError as e: # More specific exception for file operations
        logging.error(f"Erro de I/O ao adicionar dados ao CSV {file_path}: {e}")
    except csv.Error as e: # More specific exception for CSV writing issues
        logging.error(f"Erro de CSV ao adicionar dados ao CSV {file_path}: {e}")
    except Exception as e:
        logging.error(f"Erro inesperado ao adicionar dados ao CSV {file_path}: {e}")

def read_csv(file_path):
    """
    Lê o conteúdo de um arquivo CSV e retorna como uma lista de dicionários.

    Args:
        file_path (str): Caminho do arquivo CSV.

    Returns:
        list: Lista de dicionários representando as linhas do CSV.
    """
    try:
        if not os.path.exists(file_path):
            logging.warning(f"Arquivo CSV não encontrado, retornando lista vazia: {file_path}")
            return []

        with open(file_path, mode='r', newline='', encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)
            # Handle potential empty file or file with only headers
            data = list(reader)
            if not data and reader.fieldnames is None: # Check if file was truly empty
                 logging.warning(f"Arquivo CSV está vazio ou não contém cabeçalhos: {file_path}")
                 return []
            return data
    except FileNotFoundError:
        logging.warning(f"Arquivo CSV não encontrado durante leitura: {file_path}")
        return []
    except IOError as e: # More specific exception for file operations
        logging.error(f"Erro de I/O ao ler o arquivo CSV {file_path}: {e}")
        return []
    except csv.Error as e: # More specific exception for CSV reading issues
        logging.error(f"Erro de CSV ao ler o arquivo CSV {file_path}: {e}")
        return []
    except Exception as e:
        logging.error(f"Erro inesperado ao ler o arquivo CSV {file_path}: {e}")
        return []