from groq import Groq
import os
import json
from typing import Dict, List, Any

# Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """
You are a UK bank regulatory reporting assistant specializing in PRA COREP reporting.
Your task is to analyze user scenarios and generate structured regulatory output.

CRITICAL RULES:
1. Use ONLY the provided regulatory context from the retrieved documents
2. Output STRICT JSON following the exact schema provided
3. If data is missing or unclear, set amount=null and explain in data_gaps
4. All amounts should be in the currency specified (default GBP)
5. Provide specific regulatory references for each populated field
6. Do not invent values or make assumptions beyond the context provided
7. Focus on COREP Template C 01.00 - Own Funds reporting
"""

def generate_corep_output(user_query: str, retrieved_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate structured COREP output using Groq LLM based on user query and retrieved documents.
    
    Args:
        user_query (str): Natural language scenario from the user
        retrieved_docs (list): List of retrieved regulatory documents
        
    Returns:
        dict: Structured COREP output in JSON format
    """
    
    # Format retrieved context
    context = "\n\n".join([
        f"SOURCE: {d['source']}\n{d['text']}" 
        for d in retrieved_docs
    ])
    
    prompt = f"""
REGULATORY CONTEXT:
{context}

USER SCENARIO:
{user_query}

TASK: Generate structured COREP output for Template C 01.00 - Own Funds.

Return JSON in this exact format:

{{
  "template": "C 01.00",
  "currency": "GBP",
  "reporting_date": "2026-01-31",
  "own_funds": {{
    "CET1": {{
      "ordinary_share_capital": {{
        "amount": number or null,
        "corep_row": "010",
        "justification_refs": ["source1", "source2"],
        "explanation": "Brief explanation of why this amount is included"
      }},
      "retained_earnings": {{
        "amount": number or null,
        "corep_row": "020", 
        "justification_refs": ["source1", "source2"],
        "explanation": "Brief explanation of why this amount is included"
      }},
      "intangibles_deduction": {{
        "amount": number or null,
        "corep_row": "350",
        "justification_refs": ["source1", "source2"],
        "explanation": "Brief explanation of why this amount is deducted"
      }}
    }},
    "AT1": {{
      "instruments": {{
        "amount": number or null,
        "corep_row": "120",
        "justification_refs": ["source1", "source2"],
        "explanation": "Brief explanation of why this amount is included"
      }}
    }},
    "Tier2": {{
      "instruments": {{
        "amount": number or null,
        "corep_row": "200",
        "justification_refs": ["source1", "source2"],
        "explanation": "Brief explanation of why this amount is included"
      }}
    }}
  }},
  "data_gaps": [
    {{
      "field": "field_name",
      "issue": "description of missing/unclear data",
      "suggestion": "how to resolve"
    }}
  ],
  "summary": {{
    "total_cet1": number or null,
    "total_at1": number or null,
    "total_tier2": number or null,
    "total_own_funds": number or null
  }}
}}

IMPORTANT:
- Amounts should be numeric values (not strings)
- Use null for missing/unclear amounts
- Provide specific regulatory references from the context
- Include explanations for each populated field
- List any data gaps or uncertainties
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-70b-versatile",  # Updated to a currently supported model
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=2000
        )
        
        result_text = response.choices[0].message.content
        
        # Parse JSON response
        try:
            result = json.loads(result_text)
        except json.JSONDecodeError:
            # Try to extract JSON from response if it contains extra text
            start_idx = result_text.find('{')
            end_idx = result_text.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                json_text = result_text[start_idx:end_idx]
                result = json.loads(json_text)
            else:
                raise ValueError("Could not parse JSON from LLM response")
        
        # Validate required fields
        if "template" not in result:
            result["template"] = "C 01.00"
        if "currency" not in result:
            result["currency"] = "GBP"
        if "data_gaps" not in result:
            result["data_gaps"] = []
        
        return result
        
    except Exception as e:
        # Return error structure
        return {
            "template": "C 01.00",
            "currency": "GBP",
            "error": f"LLM generation failed: {str(e)}",
            "own_funds": {
                "CET1": {"ordinary_share_capital": {"amount": None}, "retained_earnings": {"amount": None}, "intangibles_deduction": {"amount": None}},
                "AT1": {"instruments": {"amount": None}},
                "Tier2": {"instruments": {"amount": None}}
            },
            "data_gaps": [{"field": "all", "issue": f"LLM processing error: {str(e)}", "suggestion": "Check API key and try again"}]
        }

def test_llm_connection():
    """Test the Groq API connection."""
    try:
        response = client.chat.completions.create(
            model="llama-3.1-70b-versatile",  # Updated to a currently supported model
            messages=[{"role": "user", "content": "Hello, can you respond with 'API connection successful'?"}],
            temperature=0,
            max_tokens=50
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Connection failed: {str(e)}"

if __name__ == "__main__":
    # Test the LLM connection
    print("Testing Groq API connection...")
    result = test_llm_connection()
    print(f"Result: {result}")
    
    # Example usage with mock data
    if "API connection successful" in result:
        mock_query = "The bank has £120m ordinary share capital, £30m retained earnings, £10m AT1 instruments, and £8m intangible assets."
        mock_docs = [
            {
                "source": "PRA_Own_Funds.txt",
                "text": "CET1 capital includes ordinary share capital and retained earnings. Intangible assets must be deducted."
            }
        ]
        
        print("\nTesting COREP generation...")
        output = generate_corep_output(mock_query, mock_docs)
        print(json.dumps(output, indent=2))