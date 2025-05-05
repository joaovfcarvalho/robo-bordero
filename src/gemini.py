import os
import json
import logging
from google import genai
from google.genai import types
from pydantic import BaseModel
from typing import List

# Define Pydantic models for structured output
class RevenueDetail(BaseModel):
    source: str
    quantity: int | None = None # Add quantity (optional integer)
    price: float | None = None # Add price (optional float)
    amount: float

class ExpenseDetail(BaseModel):
    category: str
    amount: float

class MatchDetails(BaseModel):
    home_team: str
    away_team: str
    match_date: str
    stadium: str
    competition: str

class FinancialData(BaseModel):
    gross_revenue: float
    total_expenses: float
    net_result: float
    revenue_details: List[RevenueDetail]
    expense_details: List[ExpenseDetail]

class AudienceStatistics(BaseModel):
    paid_attendance: int
    non_paid_attendance: int
    total_attendance: int

class PDFExtract(BaseModel):
    match_details: MatchDetails
    financial_data: FinancialData
    audience_statistics: AudienceStatistics

def setup_client():
    """
    Sets up the Google Gen AI using the API key from environment variables.

    Returns:
        genai.Client: Configured Gen AI client.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY environment variable is not set.")

    return genai.Client(api_key=api_key)

def analyze_pdf(pdf_content_bytes: bytes, custom_prompt: str = None) -> dict:
    """
    Analyzes PDF content using the Google Gen AI API with a specified prompt.

    Args:
        pdf_content_bytes (bytes): The content of the PDF file as bytes.
        custom_prompt (str, optional): Custom prompt to guide the analysis. Defaults to a standard prompt.

    Returns:
        dict: Parsed JSON response from the Google Gen AI API or an error dictionary.
    """
    client = setup_client()

    if not pdf_content_bytes:
        logging.error("PDF content bytes are empty.")
        return {"error": "PDF content bytes are empty."}

    # Define the prompt
    default_prompt = (
        "Extract the following information from the PDF as a JSON object: "
        "1. Match details: home_team (str), away_team (str), match_date (str, YYYY-MM-DD), stadium (str), competition (str). "
        "2. Financial data: gross_revenue (float), total_expenses (float), net_result (float), revenue_details (list of dicts with 'source', 'quantity' (int), 'price' (float), and 'amount' (float) keys), expense_details (list of dicts with 'category' and 'amount' keys). "
        "3. Audience statistics: paid_attendance (int), non_paid_attendance (int), total_attendance (int)."
        "Ensure all monetary values are floats and attendances/quantities are integers. If a value (like quantity or price) is not applicable or found, use null."
    )
    prompt = custom_prompt if custom_prompt else default_prompt

    try:
        # Create the PDF part for document processing
        pdf_part = types.Part.from_bytes(data=pdf_content_bytes, mime_type="application/pdf")

        # Send the content to the API with structured schema
        logging.info("Sending PDF content to Gemini API for analysis.")
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=[pdf_part, prompt],
            config={
                "temperature": 0.2,
                "response_mime_type": "application/json",
                "response_schema": PDFExtract
            }
        )

        # Return structured parsed output or fallback to raw JSON parse
        if response.parsed:
            logging.info("Received structured response from Gemini API.")
            return response.parsed.model_dump()
        elif response.text:
            logging.info("Received unstructured response, attempting JSON parse.")
            try:
                return json.loads(response.text)
            except json.JSONDecodeError as json_err:
                logging.error(f"Failed to parse JSON response: {json_err}")
                return {"error": f"Failed to parse JSON response: {json_err}", "raw_response": response.text}
        else:
            block_reason = getattr(response.prompt_feedback, "block_reason", "Unknown") if hasattr(response, "prompt_feedback") else "Unknown"
            logging.warning(f"Gemini API response was empty or blocked. Reason: {block_reason}")
            return {"error": f"API response empty or blocked. Reason: {block_reason}"}

    except Exception as e:
        logging.error(f"An unexpected error occurred during Gemini API call: {e}")
        return {"error": f"An unexpected error occurred: {e}"}