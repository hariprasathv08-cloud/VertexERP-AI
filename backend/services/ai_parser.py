import json
from pypdf import PdfReader
import io
from dotenv import load_dotenv
from pathlib import Path
import os
from google import genai

def extract_pdf_text(file_bytes: bytes) -> str:
    """
    Reads text from a PDF file using PyPDF. Reads every page, strips page text, and combines the text robustly.
    Raises ValueError if extraction fails or text is empty.
    """
    try:
        pdf_file = io.BytesIO(file_bytes)
        reader = PdfReader(pdf_file)
        pages_text = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                pages_text.append(page_text.strip())
        
        combined_text = "\n".join(pages_text).strip()
        if not combined_text:
            raise ValueError("Extracted text content from PDF is empty.")
        return combined_text
    except Exception as e:
        if isinstance(e, ValueError):
            raise e
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")

def parse_invoice(file_bytes: bytes, file_mime_type: str, model_name: str = "gemini-2.0-flash-lite") -> dict:
    """
    Parses an invoice file (image or PDF) using Gemini API with strict system constraints and prompt-based structured output.
    """
    # 2. Setup strict system instruction and prompt
    system_instruction = (
        "You are an ERP invoice extraction engine. "
        "Extract ONLY data visible in this invoice. "
        "Never create fake vendors. "
        "Never guess missing values. "
        "Return the output as a valid JSON object matching the requested schema."
    )

    prompt = """

You are an ERP invoice extraction AI.

Extract invoice information only from provided text.

Return ONLY valid JSON.

Format:

{{
 "vendor_name":"",
 "invoice_number":"",
 "invoice_date":"",
 "items":[
   {{
    "description":"",
    "quantity":"",
    "unit_price":"",
    "total_price":""
   }}
 ],
 "tax_amount":"",
 "total_amount":"",
 "payment_terms":"",
 "confidence":0
}}

If value is missing use null.

Do not create fake data.

Invoice Text:

{invoice_text}

"""

    try:
        # Reload environment
        BASE_DIR = Path(__file__).resolve().parents[2]
        env_path = BASE_DIR / ".env"
        load_dotenv(dotenv_path=env_path, override=True)
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise Exception("Gemini API key is not configured. Check .env location")
            
        genai.configure(api_key=api_key)
        
        configured_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")
        priority_models = ["gemini-2.0-flash-lite", "gemini-3.5-flash", "gemini-1.5-flash", "gemini-2.5-flash", "gemini-1.5-flash-8b"]
        
        models = []
        if configured_model:
            models.append(configured_model)
        for m in priority_models:
            if m not in models:
                models.append(m)

        raw_text = ""
        # 3. Handle PDF text extraction or image multimodal scan
        if "pdf" in file_mime_type.lower():
            raw_text = extract_pdf_text(file_bytes)
            invoice_text = raw_text[:8000] # Limit to 8000 characters
            content = prompt.format(invoice_text=invoice_text)
            generate_args = [content]
        else:
            raw_text = "Image scan (no local text extraction)."
            content = prompt.format(invoice_text="[Please extract directly from the provided image]")
            doc_part = {
                "mime_type": file_mime_type,
                "data": file_bytes
            }
            generate_args = [[doc_part, content]]

        response = None
        last_error = None
        for current_model_name in models:
            try:
                model = genai.GenerativeModel(
                    model_name=current_model_name,
                    system_instruction=system_instruction
                )
                response = model.generate_content(
                    *generate_args,
                    generation_config={
                        "temperature": 0.1,
                        "response_mime_type": "application/json"
                    }
                )
                if response and response.text:
                    break
            except Exception as e:
                last_error = e
                continue

        if not response:
            if last_error:
                raise last_error
            else:
                raise Exception("No Gemini models succeeded.")

        # 4. Parse JSON result
        raw_result = json.loads(response.text)
        
        # Map raw_result to backend invoice format
        materials = []
        for item in raw_result.get("items", []) or []:
            materials.append({
                "description": item.get("description"),
                "quantity": item.get("quantity"),
                "rate": item.get("unit_price"),
                "amount": item.get("total_price")
            })
            
        result = {
            "vendor": raw_result.get("vendor_name"),
            "invoice_number": raw_result.get("invoice_number"),
            "invoice_date": raw_result.get("invoice_date"),
            "materials": materials,
            "tax": raw_result.get("tax_amount"),
            "grand_total": raw_result.get("total_amount"),
            "payment_terms": raw_result.get("payment_terms"),
            "raw_text": raw_text
        }

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        err_msg = str(e)
        err_class = e.__class__.__name__
        if (
            "429" in err_msg 
            or "quota" in err_msg.lower() 
            or "limit" in err_msg.lower() 
            or "exhausted" in err_msg.lower()
            or err_class == "ResourceExhausted"
        ):
            err_msg = "AI limit reached. Try again later or change API key."
        else:
            err_msg = f"AI extraction failed: {err_msg}"
        return {
            "success": False,
            "error": err_msg
        }

def test_gemini_connection() -> bool:
    """
    Tests the connection to Google Gemini API by checking if API key is present
    and attempting a simple generate_content call. Returns True if successful, False otherwise.
    Does not crash the application on failure.
    """
    try:
        BASE_DIR = Path(__file__).resolve().parents[2]
        env_path = BASE_DIR / ".env"
        load_dotenv(dotenv_path=env_path, override=True)
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return False
            
        genai.configure(api_key=api_key)
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")
        model = genai.GenerativeModel(model_name)
        
        # Simple minimal API call to test connection
        response = model.generate_content("Ping", generation_config={"max_output_tokens": 5})
        return response is not None and response.text is not None
    except Exception:
        return False

