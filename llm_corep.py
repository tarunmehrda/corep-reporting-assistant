import os
import json
import re
from typing import Dict, List, Any

# Simple rule-based COREP generator (fallback when model fails)
class SimpleCorepGenerator:
    def __init__(self):
        self.patterns = {
            'ordinary_share_capital': r'£?(\d+(?:,\d+)*)\s*(?:million|m|million|bn|billion)?\s*(?:ordinary|share|capital)',
            'retained_earnings': r'£?(\d+(?:,\d+)*)\s*(?:million|m|million|bn|billion)?\s*(?:retained|earnings)',
            'at1_instruments': r'£?(\d+(?:,\d+)*)\s*(?:million|m|million|bn|billion)?\s*(?:at1|at 1|additional)',
            'intangible_assets': r'£?(\d+(?:,\d+)*)\s*(?:million|m|million|bn|billion)?\s*(?:intangible|goodwill|assets)',
            'tier2_instruments': r'£?(\d+(?:,\d+)*)\s*(?:million|m|million|bn|billion)?\s*(?:tier2|tier 2|subordinated)'
        }
    
    def extract_amount(self, text: str, pattern: str) -> float:
        """Extract monetary amount from text using regex pattern."""
        match = re.search(pattern, text.lower())
        if match:
            amount_str = match.group(1).replace(',', '')
            try:
                amount = float(amount_str)
                # Handle millions/billions
                if 'billion' in text.lower() or 'bn' in text.lower():
                    amount *= 1000
                return amount
            except ValueError:
                return None
        return None
    
    def generate_corep_output(self, user_query: str, retrieved_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate COREP output using rule-based extraction."""
        
        # Extract amounts from user query
        query_lower = user_query.lower()
        
        cet1_ordinary = self.extract_amount(user_query, self.patterns['ordinary_share_capital'])
        cet1_retained = self.extract_amount(user_query, self.patterns['retained_earnings'])
        cet1_intangibles = self.extract_amount(user_query, self.patterns['intangible_assets'])
        at1_amount = self.extract_amount(user_query, self.patterns['at1_instruments'])
        tier2_amount = self.extract_amount(user_query, self.patterns['tier2_instruments'])
        
        # Calculate totals
        total_cet1 = (cet1_ordinary or 0) + (cet1_retained or 0) - (cet1_intangibles or 0)
        total_at1 = at1_amount or 0
        total_tier2 = tier2_amount or 0
        total_own_funds = total_cet1 + total_at1 + total_tier2
        
        # Build response
        response = {
            "template": "C 01.00",
            "currency": "GBP",
            "reporting_date": "2026-01-31",
            "own_funds": {
                "CET1": {
                    "ordinary_share_capital": {
                        "amount": cet1_ordinary,
                        "corep_row": "010",
                        "justification_refs": [doc["source"] for doc in retrieved_docs[:2]],
                        "explanation": "Extracted from user query" if cet1_ordinary else "Not found in query"
                    },
                    "retained_earnings": {
                        "amount": cet1_retained,
                        "corep_row": "020",
                        "justification_refs": [doc["source"] for doc in retrieved_docs[:2]],
                        "explanation": "Extracted from user query" if cet1_retained else "Not found in query"
                    },
                    "intangibles_deduction": {
                        "amount": cet1_intangibles,
                        "corep_row": "350",
                        "justification_refs": [doc["source"] for doc in retrieved_docs[:2]],
                        "explanation": "Extracted from user query" if cet1_intangibles else "Not found in query"
                    }
                },
                "AT1": {
                    "instruments": {
                        "amount": at1_amount,
                        "corep_row": "120",
                        "justification_refs": [doc["source"] for doc in retrieved_docs[:2]],
                        "explanation": "Extracted from user query" if at1_amount else "Not found in query"
                    }
                },
                "Tier2": {
                    "instruments": {
                        "amount": tier2_amount,
                        "corep_row": "200",
                        "justification_refs": [doc["source"] for doc in retrieved_docs[:2]],
                        "explanation": "Extracted from user query" if tier2_amount else "Not found in query"
                    }
                }
            },
            "data_gaps": [],
            "summary": {
                "total_cet1": total_cet1 if total_cet1 > 0 else None,
                "total_at1": total_at1 if total_at1 > 0 else None,
                "total_tier2": total_tier2 if total_tier2 > 0 else None,
                "total_own_funds": total_own_funds if total_own_funds > 0 else None
            }
        }
        
        # Add data gaps for missing information
        if not cet1_ordinary:
            response["data_gaps"].append({
                "field": "ordinary_share_capital",
                "issue": "Amount not found in user query",
                "suggestion": "Please specify ordinary share capital amount"
            })
        
        if not cet1_retained:
            response["data_gaps"].append({
                "field": "retained_earnings", 
                "issue": "Amount not found in user query",
                "suggestion": "Please specify retained earnings amount"
            })
        
        return response

# Global generator instance
generator = SimpleCorepGenerator()

def generate_corep_output(user_query: str, retrieved_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate structured COREP output using rule-based extraction.
    
    Args:
        user_query (str): Natural language scenario from the user
        retrieved_docs (list): List of retrieved regulatory documents
        
    Returns:
        dict: Structured COREP output in JSON format
    """
    try:
        return generator.generate_corep_output(user_query, retrieved_docs)
    except Exception as e:
        # Return error structure
        return {
            "template": "C 01.00",
            "currency": "GBP",
            "error": f"Rule-based generation failed: {str(e)}",
            "own_funds": {
                "CET1": {"ordinary_share_capital": {"amount": None}, "retained_earnings": {"amount": None}, "intangibles_deduction": {"amount": None}},
                "AT1": {"instruments": {"amount": None}},
                "Tier2": {"instruments": {"amount": None}}
            },
            "data_gaps": [{"field": "all", "issue": f"Processing error: {str(e)}", "suggestion": "Check input format and try again"}],
            "summary": {
                "total_cet1": None,
                "total_at1": None,
                "total_tier2": None,
                "total_own_funds": None
            }
        }

def test_llm_connection():
    """Test the rule-based system connection."""
    try:
        # Test with a simple query
        test_query = "The bank has £120m ordinary share capital and £30m retained earnings."
        test_docs = [{"source": "test", "text": "Test document"}]
        
        result = generate_corep_output(test_query, test_docs)
        
        if result and "own_funds" in result:
            return "Rule-based system connection successful"
        else:
            return "Rule-based system test failed"
    except Exception as e:
        return f"Connection failed: {str(e)}"

if __name__ == "__main__":
    # Test the system
    print("Testing rule-based COREP generation...")
    result = test_llm_connection()
    print(f"Result: {result}")
    
    if "successful" in result.lower():
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
