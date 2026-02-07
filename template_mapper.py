from typing import Dict, List, Any, Tuple
import json

def map_to_template(data: Dict[str, Any]) -> List[Tuple[str, str, Any]]:
    """
    Convert structured COREP JSON output to human-readable template format.
    
    Args:
        data (dict): Structured COREP output from LLM
        
    Returns:
        list: List of tuples (row_number, description, amount)
    """
    rows = []
    
    if "own_funds" not in data:
        return rows
    
    of = data["own_funds"]
    
    # CET1 Components
    if "CET1" in of:
        cet1 = of["CET1"]
        
        # Ordinary Share Capital (Row 010)
        if "ordinary_share_capital" in cet1:
            amount = cet1["ordinary_share_capital"].get("amount")
            rows.append(("010", "Ordinary Share Capital", amount))
        
        # Retained Earnings (Row 020)
        if "retained_earnings" in cet1:
            amount = cet1["retained_earnings"].get("amount")
            rows.append(("020", "Retained Earnings", amount))
        
        # Intangible Assets Deduction (Row 350)
        if "intangibles_deduction" in cet1:
            amount = cet1["intangibles_deduction"].get("amount")
            rows.append(("350", "Intangible Assets Deduction", amount))
    
    # AT1 Instruments (Row 120)
    if "AT1" in of and "instruments" in of["AT1"]:
        amount = of["AT1"]["instruments"].get("amount")
        rows.append(("120", "AT1 Instruments", amount))
    
    # Tier 2 Instruments (Row 200)
    if "Tier2" in of and "instruments" in of["Tier2"]:
        amount = of["Tier2"]["instruments"].get("amount")
        rows.append(("200", "Tier 2 Instruments", amount))
    
    return rows

def format_template_rows(rows: List[Tuple[str, str, Any]], currency: str = "GBP") -> List[Dict[str, Any]]:
    """
    Format template rows with proper currency formatting.
    
    Args:
        rows (list): List of template rows
        currency (str): Currency code
        
    Returns:
        list: Formatted rows with currency formatting
    """
    formatted_rows = []
    
    for row_num, description, amount in rows:
        formatted_amount = format_currency(amount, currency) if amount is not None else "N/A"
        
        formatted_rows.append({
            "row_number": row_num,
            "description": description,
            "amount": amount,
            "formatted_amount": formatted_amount,
            "currency": currency
        })
    
    return formatted_rows

def format_currency(amount: Any, currency: str = "GBP") -> str:
    """
    Format amount as currency string.
    
    Args:
        amount: Numeric amount
        currency (str): Currency code
        
    Returns:
        str: Formatted currency string
    """
    if amount is None:
        return "N/A"
    
    try:
        # Convert to float if it's not already
        numeric_amount = float(amount)
        
        # Format with thousand separators and 2 decimal places
        if currency == "GBP":
            return f"£{numeric_amount:,.2f}"
        else:
            return f"{numeric_amount:,.2f} {currency}"
    
    except (ValueError, TypeError):
        return str(amount)

def calculate_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate summary totals from COREP data.
    
    Args:
        data (dict): Structured COREP output
        
    Returns:
        dict: Summary calculations
    """
    summary = {
        "total_cet1": 0,
        "total_at1": 0,
        "total_tier2": 0,
        "total_own_funds": 0
    }
    
    if "own_funds" not in data:
        return summary
    
    of = data["own_funds"]
    
    # Calculate CET1 total
    if "CET1" in of:
        cet1_total = 0
        cet1 = of["CET1"]
        
        # Add components
        for component in ["ordinary_share_capital", "retained_earnings"]:
            if component in cet1:
                amount = cet1[component].get("amount", 0)
                if amount is not None:
                    cet1_total += float(amount)
        
        # Subtract deductions
        if "intangibles_deduction" in cet1:
            amount = cet1["intangibles_deduction"].get("amount", 0)
            if amount is not None:
                cet1_total -= float(amount)
        
        summary["total_cet1"] = cet1_total
    
    # Calculate AT1 total
    if "AT1" in of and "instruments" in of["AT1"]:
        amount = of["AT1"]["instruments"].get("amount", 0)
        if amount is not None:
            summary["total_at1"] = float(amount)
    
    # Calculate Tier 2 total
    if "Tier2" in of and "instruments" in of["Tier2"]:
        amount = of["Tier2"]["instruments"].get("amount", 0)
        if amount is not None:
            summary["total_tier2"] = float(amount)
    
    # Calculate total own funds
    summary["total_own_funds"] = (
        summary["total_cet1"] + 
        summary["total_at1"] + 
        summary["total_tier2"]
    )
    
    return summary

def generate_template_export(data: Dict[str, Any], format_type: str = "json") -> str:
    """
    Generate exportable template in various formats.
    
    Args:
        data (dict): Structured COREP output
        format_type (str): Export format ("json", "csv", "html")
        
    Returns:
        str: Formatted export string
    """
    rows = map_to_template(data)
    formatted_rows = format_template_rows(rows, data.get("currency", "GBP"))
    summary = calculate_summary(data)
    
    if format_type == "json":
        export_data = {
            "template": data.get("template", "C 01.00"),
            "currency": data.get("currency", "GBP"),
            "reporting_date": data.get("reporting_date"),
            "rows": formatted_rows,
            "summary": summary
        }
        return json.dumps(export_data, indent=2)
    
    elif format_type == "csv":
        csv_lines = ["Row,Description,Amount,Currency"]
        for row in formatted_rows:
            csv_lines.append(f"{row['row_number']},{row['description']},{row['amount']},{row['currency']}")
        
        # Add summary
        csv_lines.extend([
            "",
            "SUMMARY",
            f"Total CET1,{summary['total_cet1']},{data.get('currency', 'GBP')}",
            f"Total AT1,{summary['total_at1']},{data.get('currency', 'GBP')}",
            f"Total Tier 2,{summary['total_tier2']},{data.get('currency', 'GBP')}",
            f"Total Own Funds,{summary['total_own_funds']},{data.get('currency', 'GBP')}"
        ])
        
        return "\n".join(csv_lines)
    
    elif format_type == "html":
        html = f"""
        <html>
        <head><title>COREP Template {data.get('template', 'C 01.00')}</title></head>
        <body>
        <h1>COREP Template {data.get('template', 'C 01.00')}</h1>
        <p>Currency: {data.get('currency', 'GBP')} | Date: {data.get('reporting_date', 'N/A')}</p>
        
        <table border="1">
        <tr><th>Row</th><th>Description</th><th>Amount</th></tr>
        """
        
        for row in formatted_rows:
            html += f"<tr><td>{row['row_number']}</td><td>{row['description']}</td><td>{row['formatted_amount']}</td></tr>"
        
        html += """
        </table>
        
        <h2>Summary</h2>
        <ul>
        """
        
        for key, value in summary.items():
            html += f"<li>{key.replace('_', ' ').title()}: {format_currency(value, data.get('currency', 'GBP'))}</li>"
        
        html += """
        </ul>
        </body>
        </html>
        """
        
        return html
    
    else:
        raise ValueError(f"Unsupported format type: {format_type}")

if __name__ == "__main__":
    # Test with sample data
    sample_data = {
        "template": "C 01.00",
        "currency": "GBP",
        "own_funds": {
            "CET1": {
                "ordinary_share_capital": {"amount": 120000000},
                "retained_earnings": {"amount": 30000000},
                "intangibles_deduction": {"amount": 8000000}
            },
            "AT1": {
                "instruments": {"amount": 10000000}
            },
            "Tier2": {
                "instruments": {"amount": 5000000}
            }
        }
    }
    
    print("Template Mapping Test:")
    rows = map_to_template(sample_data)
    formatted_rows = format_template_rows(rows)
    
    for row in formatted_rows:
        print(f"{row['row_number']} - {row['description']}: {row['formatted_amount']}")
    
    print("\nSummary:")
    summary = calculate_summary(sample_data)
    for key, value in summary.items():
        print(f"{key}: {format_currency(value, 'GBP')}")
    
    print("\nJSON Export:")
    print(generate_template_export(sample_data, "json"))
