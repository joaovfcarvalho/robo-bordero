import os
import logging
import tkinter as tk
import datetime # Added datetime import
from tkinter import messagebox, ttk
from pathlib import Path # Added pathlib
from .scraper import download_pdfs
from .gemini import analyze_pdf # Corrected import name
from .db import append_to_csv, read_csv
from .utils import setup_logging, load_env_variables as load_env_vars, ensure_directory_exists
from .normalize import refresh_lookups, write_clean_csv

# Centralized logging setup
setup_logging()

def run_normalization(jogos_resumo_csv_path: Path, lookup_dir: Path, clean_csv_path: Path, gemini_api_key: str):
    """
    Runs the lookup refresh and clean CSV writing process.
    """
    try:
        logging.info("Starting normalization process...")
        refresh_lookups(jogos_resumo_csv_path, lookup_dir, gemini_api_key)
        write_clean_csv(jogos_resumo_csv_path, clean_csv_path, lookup_dir)
        messagebox.showinfo("Sucesso", "Normalização de nomes concluída. Arquivo 'jogos_resumo_clean.csv' criado/atualizado.")
        logging.info("Normalization process finished successfully.")
    except Exception as e:
        logging.error(f"An error occurred during normalization: {e}")
        messagebox.showerror("Erro na Normalização", f"Ocorreu um erro: {e}")

def run_operation(choice, year, competitions, pdf_dir, csv_dir, gemini_api_key):
    """
    Executes the selected operation based on the user's choice.
    """
    # Define paths using pathlib
    pdf_path = Path(pdf_dir)
    csv_path = Path(csv_dir)
    lookup_path = Path("lookups") # Define lookup directory path
    jogos_resumo_csv = csv_path / "jogos_resumo.csv"
    receitas_detalhe_csv = csv_path / "receitas_detalhe.csv"
    despesas_detalhe_csv = csv_path / "despesas_detalhe.csv"
    jogos_resumo_clean_csv = csv_path / "jogos_resumo_clean.csv" # Define clean CSV path

    try:
        if choice == "1": # Download PDFs
            logging.info("Iniciando download de PDFs...")
            for competition in competitions:
                download_pdfs(year, competition, pdf_path) # Pass Path object
            messagebox.showinfo("Sucesso", "Download dos PDFs concluído.")
            logging.info("Download de PDFs concluído.")

        elif choice == "2": # Process PDFs
            logging.info("Iniciando processamento de PDFs...")
            process_pdfs(pdf_path, jogos_resumo_csv, receitas_detalhe_csv, despesas_detalhe_csv, gemini_api_key) # Pass Path objects
            messagebox.showinfo("Sucesso", "Processamento dos PDFs concluído.")
            logging.info("Processamento de PDFs concluído.")

        elif choice == "3": # Download and Process
            logging.info("Iniciando download e processamento de PDFs...")
            for competition in competitions:
                download_pdfs(year, competition, pdf_path) # Pass Path object
            process_pdfs(pdf_path, jogos_resumo_csv, receitas_detalhe_csv, despesas_detalhe_csv, gemini_api_key) # Pass Path objects
            messagebox.showinfo("Sucesso", "Download e processamento dos PDFs concluídos.")
            logging.info("Download e processamento de PDFs concluído.")

        elif choice == "4": # Normalize CSV
            logging.info("Iniciando normalização de nomes no CSV...")
            run_normalization(jogos_resumo_csv, lookup_path, jogos_resumo_clean_csv, gemini_api_key) # Pass Path objects
            # No need for messagebox here, run_normalization handles it

        else:
            messagebox.showwarning("Seleção Inválida", "Por favor, selecione uma operação válida.")
            logging.warning("Seleção de operação inválida.")

    except Exception as e:
        logging.error(f"Erro durante a operação {choice}: {e}")
        messagebox.showerror("Erro", f"Ocorreu um erro inesperado: {e}")

def main():
    """
    Ponto de entrada principal para executar as operações de download e análise.
    Agora com interface gráfica.
    """
    load_env_vars()

    # Configurações - Get defaults, but year will be overridden by GUI
    default_year = int(os.getenv("YEAR", datetime.date.today().year)) # Default to current year
    competitions = os.getenv("COMPETITIONS", "142,424,242").split(",")
    pdf_dir = os.getenv("PDF_DIR", "pdfs")
    csv_dir = os.getenv("CSV_DIR", "csv")
    gemini_api_key = os.getenv("GEMINI_API_KEY")

    ensure_directory_exists(pdf_dir)
    ensure_directory_exists(csv_dir)

    # Configuração da interface gráfica
    root = tk.Tk()
    root.title("CBF Robot")

    # --- Add Year Selection --- 
    tk.Label(root, text="Ano para Download:").pack(pady=(10, 0))
    year_var = tk.StringVar(value=str(default_year))
    year_entry = tk.Entry(root, textvariable=year_var, width=10)
    year_entry.pack(pady=(0, 10))
    # --- End Year Selection ---

    tk.Label(root, text="Selecione a operação:").pack(pady=10)

    # --- Update Button Commands to get year from entry --- 
    tk.Button(root, text="1. Apenas download de novos borderôs", 
              command=lambda: run_operation("1", int(year_var.get()), competitions, pdf_dir, csv_dir, gemini_api_key)).pack(pady=5)

    tk.Button(root, text="2. Apenas análise de borderôs não processados", 
              # Option 2 doesn't strictly need the year, but pass it for consistency
              command=lambda: run_operation("2", int(year_var.get()), competitions, pdf_dir, csv_dir, gemini_api_key)).pack(pady=5)

    tk.Button(root, text="3. Download e análise (execução completa)", 
              command=lambda: run_operation("3", int(year_var.get()), competitions, pdf_dir, csv_dir, gemini_api_key)).pack(pady=5)

    # --- Add Normalization Button ---
    tk.Button(root, text="4. Normalizar Nomes (CSV)",
              command=lambda: run_operation("4", int(year_var.get()), competitions, pdf_dir, csv_dir, gemini_api_key)).pack(pady=5)
    # --- End Button Command Updates ---

    root.mainloop()

def process_pdfs(pdf_dir, jogos_resumo_csv, receitas_detalhe_csv, despesas_detalhe_csv, gemini_api_key):
    """
    Processa os PDFs não analisados e salva os resultados nos arquivos CSV.

    Args:
        pdf_dir (str): Diretório onde os PDFs estão armazenados.
        jogos_resumo_csv (str): Caminho do arquivo CSV de resumo dos jogos.
        receitas_detalhe_csv (str): Caminho do arquivo CSV de receitas detalhadas.
        despesas_detalhe_csv (str): Caminho do arquivo CSV de despesas detalhadas.
        gemini_api_key (str): Chave da API Google Gemini.
    """
    processed_ids = set()
    try:
        # Read existing summary data
        summary_data = read_csv(jogos_resumo_csv)
        for row in summary_data:
            # Check if 'id_jogo_cbf' exists and is not empty or None
            jogo_id = row.get("id_jogo_cbf")
            if jogo_id: # Ensures it's not None or empty string
                processed_ids.add(str(jogo_id)) # Ensure it's stored/compared as a string
        logging.info(f"Loaded {len(processed_ids)} processed game IDs from {jogos_resumo_csv}")
    except Exception as e:
        # Log error but continue, assuming no IDs processed if file read fails
        logging.error(f"Error reading processed IDs from {jogos_resumo_csv}: {e}. Proceeding cautiously.")
        # Keep any IDs potentially loaded before the error
        # processed_ids = set() # Avoid resetting if partially loaded

    pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith(".pdf")]

    for pdf_file in pdf_files:
        # Extract ID from filename (without extension)
        id_jogo_cbf = str(os.path.splitext(pdf_file)[0]) # Use filename as the definitive ID

        # Check 1: Using filename-based ID before reading/analyzing PDF
        if id_jogo_cbf in processed_ids:
            logging.info(f"Skipping already processed PDF (filename match): {pdf_file} (ID: {id_jogo_cbf})")
            continue

        pdf_path = os.path.join(pdf_dir, pdf_file)
        logging.info(f"Processing PDF: {pdf_path} (ID: {id_jogo_cbf})")

        try:
            # Read PDF content as bytes
            with open(pdf_path, 'rb') as f:
                pdf_content_bytes = f.read()

            # Call the refactored analyze_pdf function
            response = analyze_pdf(pdf_content_bytes)

            # Robust check for error in response
            if response.get("error"):
                logging.error(f"Error analyzing {pdf_file} (ID: {id_jogo_cbf}): {response['error']}")
                error_log_entry = {
                    "id_jogo_cbf": id_jogo_cbf, # Use filename ID
                    "data_jogo": None,
                    "time_mandante": None,
                    "time_visitante": None,
                    "estadio": None,
                    "competicao": None,
                    "publico_total": None,
                    "receita_bruta_total": None,
                    "despesa_total": None,
                    "resultado_liquido": None,
                    "caminho_pdf_local": pdf_path,
                    "data_processamento": datetime.date.today().isoformat(), # Use dynamic date
                    "status": "Erro Analise",
                    "log_erro": response['error']
                }
                append_to_csv(jogos_resumo_csv, [error_log_entry], error_log_entry.keys())
                # Add the ID to processed_ids even on error to prevent retries
                processed_ids.add(id_jogo_cbf)
                continue

            # --- Safely extract data using .get() --- 
            match_details = response.get("match_details", {})
            financial_data = response.get("financial_data", {})
            audience_stats = response.get("audience_statistics", {})
            revenue_details = financial_data.get("revenue_details", [])
            expense_details = financial_data.get("expense_details", [])

            # Prepare summary data - id_jogo_cbf is already defined from filename
            resumo_jogo = {
                "id_jogo_cbf": id_jogo_cbf,
                "data_jogo": match_details.get("match_date"),
                "time_mandante": match_details.get("home_team"),
                "time_visitante": match_details.get("away_team"),
                "estadio": match_details.get("stadium"),
                "competicao": match_details.get("competition"),
                "publico_pagante": audience_stats.get("paid_attendance"),
                "publico_nao_pagante": audience_stats.get("non_paid_attendance"),
                "publico_total": audience_stats.get("total_attendance"),
                "receita_bruta_total": financial_data.get("gross_revenue"),
                "despesa_total": financial_data.get("total_expenses"),
                "resultado_liquido": financial_data.get("net_result"),
                "caminho_pdf_local": pdf_path,
                "data_processamento": datetime.date.today().isoformat(), # Use dynamic date
                "status": "Sucesso",
                "log_erro": None
            }
            # Define headers explicitly for consistency
            jogos_resumo_headers = [
                "id_jogo_cbf", "data_jogo", "time_mandante", "time_visitante", "estadio", "competicao",
                "publico_pagante", "publico_nao_pagante", "publico_total",
                "receita_bruta_total", "despesa_total", "resultado_liquido",
                "caminho_pdf_local", "data_processamento", "status", "log_erro"
            ]
            append_to_csv(jogos_resumo_csv, [resumo_jogo], jogos_resumo_headers)

            # Add match ID (from filename) to detailed revenue/expense data
            for item in revenue_details:
                item["id_jogo_cbf"] = id_jogo_cbf
            for item in expense_details:
                item["id_jogo_cbf"] = id_jogo_cbf

            # Append detailed data if present
            if revenue_details:
                # Build headers: ID first, then other fields
                receita_headers = ["id_jogo_cbf"] + [k for k in revenue_details[0].keys() if k != "id_jogo_cbf"]
                append_to_csv(receitas_detalhe_csv, revenue_details, receita_headers)

            if expense_details:
                # Build headers: ID first, then other fields
                despesa_headers = ["id_jogo_cbf"] + [k for k in expense_details[0].keys() if k != "id_jogo_cbf"]
                append_to_csv(despesas_detalhe_csv, expense_details, despesa_headers)

            logging.info(f"Successfully processed and saved data for {id_jogo_cbf}")
            # Add the ID used for saving to the set *after* successful save
            processed_ids.add(id_jogo_cbf)

        except FileNotFoundError:
            logging.error(f"PDF file not found: {pdf_path}")
        except IOError as io_err:
            logging.error(f"Error reading PDF file {pdf_path}: {io_err}")
        except Exception as e:
            # Catch any other unexpected error during processing of a single PDF
            logging.exception(f"Unexpected error processing {pdf_file} (ID: {id_jogo_cbf}): {e}")
            # Log error to CSV using filename ID
            error_log_entry = {
                "id_jogo_cbf": id_jogo_cbf,
                "data_jogo": None, "time_mandante": None, "time_visitante": None, "estadio": None, "competicao": None,
                "publico_total": None, "receita_bruta_total": None, "despesa_total": None, "resultado_liquido": None,
                "caminho_pdf_local": pdf_path,
                "data_processamento": datetime.date.today().isoformat(),
                "status": "Erro Inesperado",
                "log_erro": str(e)
            }
            append_to_csv(jogos_resumo_csv, [error_log_entry], error_log_entry.keys())
            # Add the ID to processed_ids even on error to prevent retries
            processed_ids.add(id_jogo_cbf)

if __name__ == "__main__":
    main()