import os
import sys
import logging
import tkinter as tk
import datetime
from tkinter import messagebox, ttk
from pathlib import Path
from .scraper import download_pdfs
from .gemini import analyze_pdf
from .db import append_to_csv, read_csv
from .utils import (
    setup_logging, 
    load_env_variables as load_env_vars, 
    ensure_directory_exists,
    get_logger,
    handle_error,
    CBFRobotError,
    ProcessingError,
    ConfigurationError,
)
from .normalize import refresh_lookups, write_clean_csv
import json

# Set up structured logging
logger = setup_logging()

def run_normalization(jogos_resumo_csv_path: Path, lookup_dir: Path, clean_csv_path: Path, gemini_api_key: str):
    """
    Runs the lookup refresh and clean CSV writing process.
    """
    try:
        logger.info("Starting normalization process")
        refresh_lookups(jogos_resumo_csv_path, lookup_dir, gemini_api_key)
        write_clean_csv(jogos_resumo_csv_path, clean_csv_path, lookup_dir)
        messagebox.showinfo("Sucesso", "Normalização de nomes concluída. Arquivo 'jogos_resumo_clean.csv' criado/atualizado.")
        logger.info("Normalization process finished successfully")
    except Exception as e:
        handle_error(
            error=e,
            log_context={"process": "normalization", "input_file": str(jogos_resumo_csv_path)},
            ui_callback=messagebox.showerror
        )

def run_operation(choice, year, competitions, pdf_dir, csv_dir, gemini_api_key):
    """
    Executes the selected operation based on the user's choice.
    """
    # Define paths using pathlib
    pdf_path = Path(pdf_dir)
    csv_path = Path(csv_dir)
    lookup_path = Path("lookups") 
    jogos_resumo_csv = csv_path / "jogos_resumo.csv"
    receitas_detalhe_csv = csv_path / "receitas_detalhe.csv"
    despesas_detalhe_csv = csv_path / "despesas_detalhe.csv"
    jogos_resumo_clean_csv = csv_path / "jogos_resumo_clean.csv" 

    try:
        operation_context = {
            "operation": choice,
            "year": year,
            "competitions": competitions,
            "pdf_dir": str(pdf_path),
            "csv_dir": str(csv_path)
        }

        if choice == "1": # Download PDFs
            logger.info("Starting PDF download", **operation_context)
            for competition in competitions:
                download_pdfs(year, competition, pdf_path)
            messagebox.showinfo("Sucesso", "Download dos PDFs concluído.")
            logger.info("PDF download completed", **operation_context)

        elif choice == "2": # Process PDFs
            logger.info("Starting PDF processing", **operation_context)
            process_pdfs(pdf_path, jogos_resumo_csv, receitas_detalhe_csv, despesas_detalhe_csv, gemini_api_key)
            messagebox.showinfo("Sucesso", "Processamento dos PDFs concluído.")
            logger.info("PDF processing completed", **operation_context)

        elif choice == "3": # Download and Process
            logger.info("Starting download and processing", **operation_context)
            for competition in competitions:
                download_pdfs(year, competition, pdf_path)
            process_pdfs(pdf_path, jogos_resumo_csv, receitas_detalhe_csv, despesas_detalhe_csv, gemini_api_key)
            messagebox.showinfo("Sucesso", "Download e processamento dos PDFs concluídos.")
            logger.info("Download and processing completed", **operation_context)

        elif choice == "4": # Normalize CSV
            logger.info("Starting CSV normalization", **operation_context)
            run_normalization(jogos_resumo_csv, lookup_path, jogos_resumo_clean_csv, gemini_api_key)

        else:
            error_message = f"Seleção inválida: {choice}"
            logger.warning(error_message, **operation_context)
            messagebox.showwarning("Seleção Inválida", "Por favor, selecione uma operação válida.")
            
    except CBFRobotError as e:
        # Handle custom application exceptions
        handle_error(
            error=e,
            log_context={"operation_details": operation_context},
            ui_callback=messagebox.showerror
        )
    except Exception as e:
        # Handle unexpected exceptions
        handle_error(
            error=e,
            log_context={"operation_details": operation_context},
            ui_callback=messagebox.showerror,
            log_level="critical"
        )

def main():
    """
    Ponto de entrada principal para executar as operações de download e análise.
    Agora com interface gráfica.
    """
    load_env_vars()

    try:
        # Configurações - Get defaults, but year will be overridden by GUI
        default_year = int(os.getenv("YEAR", datetime.date.today().year))
        competitions = os.getenv("COMPETITIONS", "142,424,242").split(",")
        pdf_dir = os.getenv("PDF_DIR", "pdfs")
        csv_dir = os.getenv("CSV_DIR", "csv")
        gemini_api_key = os.getenv("GEMINI_API_KEY")

        if not gemini_api_key:
            raise ConfigurationError("Chave da API Gemini não encontrada. Configure a variável GEMINI_API_KEY no arquivo .env.")

        ensure_directory_exists(pdf_dir)
        ensure_directory_exists(csv_dir)
        logger.info("Application started", 
                   default_year=default_year, 
                   competitions=competitions, 
                   pdf_dir=pdf_dir, 
                   csv_dir=csv_dir)

        # Configuração da interface gráfica
        root = tk.Tk()
        root.title("CBF Robot")

        # --- Add Year Selection --- 
        tk.Label(root, text="Ano para Download:").pack(pady=(10, 0))
        year_var = tk.StringVar(value=str(default_year))
        year_entry = tk.Entry(root, textvariable=year_var, width=10)
        year_entry.pack(pady=(0, 10))

        tk.Label(root, text="Selecione a operação:").pack(pady=10)

        # --- Update Button Commands to get year from entry --- 
        tk.Button(root, text="1. Apenas download de novos borderôs", 
                command=lambda: run_operation("1", int(year_var.get()), competitions, pdf_dir, csv_dir, gemini_api_key)).pack(pady=5)

        tk.Button(root, text="2. Apenas análise de borderôs não processados", 
                command=lambda: run_operation("2", int(year_var.get()), competitions, pdf_dir, csv_dir, gemini_api_key)).pack(pady=5)

        tk.Button(root, text="3. Download e análise (execução completa)", 
                command=lambda: run_operation("3", int(year_var.get()), competitions, pdf_dir, csv_dir, gemini_api_key)).pack(pady=5)

        # --- Add Normalization Button ---
        tk.Button(root, text="4. Normalizar Nomes (CSV)",
                command=lambda: run_operation("4", int(year_var.get()), competitions, pdf_dir, csv_dir, gemini_api_key)).pack(pady=5)

        root.mainloop()
        
    except ConfigurationError as e:
        # Handle configuration errors specially since UI might not be available yet
        handle_error(
            error=e,
            log_level="critical",
            ui_callback=lambda title, msg: messagebox.showerror(title, msg) if 'root' in locals() else print(f"{title}: {msg}")
        )
        sys.exit(1)
    except Exception as e:
        # Handle any other initialization errors
        handle_error(
            error=e,
            log_level="critical",
            ui_callback=lambda title, msg: messagebox.showerror(title, msg) if 'root' in locals() else print(f"{title}: {msg}")
        )
        sys.exit(1)

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
    operation_logger = get_logger("pdf_processing")
    
    try:
        # Read existing summary data
        summary_data = read_csv(jogos_resumo_csv)
        for row in summary_data:
            jogo_id = row.get("id_jogo_cbf")
            if jogo_id:
                processed_ids.add(str(jogo_id))
        operation_logger.info("Loaded processed IDs", count=len(processed_ids), csv_file=str(jogos_resumo_csv))
    except Exception as e:
        handle_error(
            error=e, 
            log_context={"csv_file": str(jogos_resumo_csv)},
            log_level="warning"
        )

    pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith(".pdf")]
    operation_logger.info("Found PDF files", count=len(pdf_files), directory=str(pdf_dir))

    for pdf_file in pdf_files:
        # Extract ID from filename (without extension)
        id_jogo_cbf = str(os.path.splitext(pdf_file)[0])

        # Skip already processed PDFs
        if id_jogo_cbf in processed_ids:
            operation_logger.info("Skipping processed PDF", filename=pdf_file, id=id_jogo_cbf)
            continue

        pdf_path = os.path.join(pdf_dir, pdf_file)
        operation_logger.info("Processing PDF", filename=pdf_file, id=id_jogo_cbf, path=pdf_path)

        try:
            # Read PDF content as bytes
            with open(pdf_path, 'rb') as f:
                pdf_content_bytes = f.read()

            # Call the refactored analyze_pdf function
            response = analyze_pdf(pdf_content_bytes)
            
            # Cache successful responses locally for reuse
            try:
                if not response.get("error"):
                    cache_dir = Path("cache")
                    cache_dir.mkdir(exist_ok=True)
                    cache_file = cache_dir / f"{id_jogo_cbf}.json"
                    with open(cache_file, 'w', encoding='utf-8') as cf:
                        json.dump(response, cf)
            except Exception as cache_err:
                operation_logger.warning("Failed to write cache file", error=str(cache_err), id=id_jogo_cbf)

            # Check for error in response
            if response.get("error"):
                error_message = response.get("error")
                operation_logger.error("Error analyzing PDF", 
                                      error=error_message, 
                                      filename=pdf_file, 
                                      id=id_jogo_cbf)
                
                error_log_entry = {
                    "id_jogo_cbf": id_jogo_cbf,
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
                    "data_processamento": datetime.date.today().isoformat(),
                    "status": "Erro Analise",
                    "log_erro": error_message
                }
                append_to_csv(jogos_resumo_csv, [error_log_entry], error_log_entry.keys())
                processed_ids.add(id_jogo_cbf)
                continue

            # Extract data safely
            match_details = response.get("match_details", {})
            financial_data = response.get("financial_data", {})
            audience_stats = response.get("audience_statistics", {})
            revenue_details = financial_data.get("revenue_details", [])
            expense_details = financial_data.get("expense_details", [])

            # Prepare summary data
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
                "data_processamento": datetime.date.today().isoformat(),
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

            # Add match ID to detailed revenue/expense data
            for item in revenue_details:
                item["id_jogo_cbf"] = id_jogo_cbf
            for item in expense_details:
                item["id_jogo_cbf"] = id_jogo_cbf

            # Append detailed data if present
            if revenue_details:
                receita_headers = ["id_jogo_cbf"] + [k for k in revenue_details[0].keys() if k != "id_jogo_cbf"]
                append_to_csv(receitas_detalhe_csv, revenue_details, receita_headers)

            if expense_details:
                despesa_headers = ["id_jogo_cbf"] + [k for k in expense_details[0].keys() if k != "id_jogo_cbf"]
                append_to_csv(despesas_detalhe_csv, expense_details, despesa_headers)

            operation_logger.info("Successfully processed PDF", 
                                 id=id_jogo_cbf, 
                                 match_date=match_details.get("match_date"),
                                 teams=f"{match_details.get('home_team')} vs {match_details.get('away_team')}")
            processed_ids.add(id_jogo_cbf)

        except FileNotFoundError:
            handle_error(
                error=FileNotFoundError(f"PDF file not found: {pdf_path}"),
                log_context={"id": id_jogo_cbf, "filename": pdf_file},
                log_level="error"
            )
        except IOError as io_err:
            handle_error(
                error=io_err,
                log_context={"id": id_jogo_cbf, "filename": pdf_file, "path": pdf_path},
                log_level="error"
            )
        except Exception as e:
            # Log unexpected error and record it in CSV
            error_details = handle_error(
                error=e,
                log_context={"id": id_jogo_cbf, "filename": pdf_file, "path": pdf_path},
                log_level="error"
            )
            
            # Log error to CSV
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
            processed_ids.add(id_jogo_cbf)

if __name__ == "__main__":
    main()