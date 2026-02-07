from typing import Dict, List, Any, Tuple
import json
from template_mapper import calculate_summary

class ValidationFlag:
    """Represents a validation flag with severity and message."""
    
    def __init__(self, flag_type: str, message: str, field: str = None, suggestion: str = None):
        self.type = flag_type  # "error", "warning", "info"
        self.message = message
        self.field = field
        self.suggestion = suggestion
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert validation flag to dictionary."""
        result = {
            "type": self.type,
            "message": self.message
        }
        if self.field:
            result["field"] = self.field
        if self.suggestion:
            result["suggestion"] = self.suggestion
        return result

def validate_corep(data: Dict[str, Any]) -> List[ValidationFlag]:
    """
    Validate COREP structured output against business rules and regulatory requirements.
    
    Args:
        data (dict): Structured COREP output from LLM
        
    Returns:
        list: List of validation flags
    """
    flags = []
    
    # Basic structure validation
    if "own_funds" not in data:
        flags.append(ValidationFlag(
            "error", 
            "Missing own_funds section in structured output",
            "own_funds",
            "Ensure the LLM output includes the own_funds structure"
        ))
        return flags
    
    of = data["own_funds"]
    
    # Validate CET1 components
    cet1_flags = _validate_cet1(of)
    flags.extend(cet1_flags)
    
    # Validate AT1 components
    at1_flags = _validate_at1(of)
    flags.extend(at1_flags)
    
    # Validate Tier 2 components
    tier2_flags = _validate_tier2(of)
    flags.extend(tier2_flags)
    
    # Cross-component validation
    cross_flags = _validate_cross_components(of)
    flags.extend(cross_flags)
    
    # Summary validation
    summary_flags = _validate_summary(data)
    flags.extend(summary_flags)
    
    # Regulatory compliance checks
    regulatory_flags = _validate_regulatory_compliance(data)
    flags.extend(regulatory_flags)
    
    return flags

def _validate_cet1(of: Dict[str, Any]) -> List[ValidationFlag]:
    """Validate CET1 capital components."""
    flags = []
    
    if "CET1" not in of:
        flags.append(ValidationFlag(
            "error",
            "Missing CET1 section",
            "CET1",
            "Include CET1 capital components in the output"
        ))
        return flags
    
    cet1 = of["CET1"]
    
    # Check for required CET1 components
    required_components = ["ordinary_share_capital", "retained_earnings"]
    for component in required_components:
        if component not in cet1:
            flags.append(ValidationFlag(
                "warning",
                f"Missing CET1 component: {component}",
                f"CET1.{component}",
                f"Include {component} if applicable to the bank"
            ))
    
    # Validate intangible deductions
    if "intangibles_deduction" in cet1:
        deduction = cet1["intangibles_deduction"].get("amount", 0)
        if deduction is not None and deduction > 0:
            flags.append(ValidationFlag(
                "warning",
                "Intangible assets deduction should be negative (deduction from capital)",
                "CET1.intangibles_deduction",
                "Ensure intangible assets are recorded as negative amounts"
            ))
    
    # Check for missing amounts
    for component_name, component in cet1.items():
        if isinstance(component, dict) and "amount" in component:
            amount = component["amount"]
            if amount is None:
                flags.append(ValidationFlag(
                    "info",
                    f"No amount specified for CET1 component: {component_name}",
                    f"CET1.{component_name}",
                    "Provide amount or confirm component is not applicable"
                ))
    
    return flags

def _validate_at1(of: Dict[str, Any]) -> List[ValidationFlag]:
    """Validate AT1 capital components."""
    flags = []
    
    if "AT1" not in of:
        flags.append(ValidationFlag(
            "info",
            "No AT1 capital reported",
            "AT1",
            "Confirm if bank has no AT1 instruments or include them if applicable"
        ))
        return flags
    
    at1 = of["AT1"]
    
    if "instruments" in at1:
        amount = at1["instruments"].get("amount")
        if amount is not None and amount == 0:
            flags.append(ValidationFlag(
                "info",
                "AT1 instruments reported as zero",
                "AT1.instruments",
                "Confirm if bank truly has no AT1 instruments"
            ))
        elif amount is None:
            flags.append(ValidationFlag(
                "warning",
                "AT1 instruments amount is null",
                "AT1.instruments",
                "Provide amount or confirm no AT1 instruments exist"
            ))
    else:
        flags.append(ValidationFlag(
            "warning",
            "Missing AT1 instruments section",
            "AT1.instruments",
            "Include AT1 instruments if applicable"
        ))
    
    return flags

def _validate_tier2(of: Dict[str, Any]) -> List[ValidationFlag]:
    """Validate Tier 2 capital components."""
    flags = []
    
    if "Tier2" not in of:
        flags.append(ValidationFlag(
            "info",
            "No Tier 2 capital reported",
            "Tier2",
            "Confirm if bank has no Tier 2 instruments or include them if applicable"
        ))
        return flags
    
    tier2 = of["Tier2"]
    
    if "instruments" in tier2:
        amount = tier2["instruments"].get("amount")
        if amount is not None and amount == 0:
            flags.append(ValidationFlag(
                "info",
                "Tier 2 instruments reported as zero",
                "Tier2.instruments",
                "Confirm if bank truly has no Tier 2 instruments"
            ))
        elif amount is None:
            flags.append(ValidationFlag(
                "warning",
                "Tier 2 instruments amount is null",
                "Tier2.instruments",
                "Provide amount or confirm no Tier 2 instruments exist"
            ))
    else:
        flags.append(ValidationFlag(
            "warning",
            "Missing Tier 2 instruments section",
            "Tier2.instruments",
            "Include Tier 2 instruments if applicable"
        ))
    
    return flags

def _validate_cross_components(of: Dict[str, Any]) -> List[ValidationFlag]:
    """Validate cross-component relationships."""
    flags = []
    
    # Check if CET1 exists but higher tiers are missing
    has_cet1 = False
    has_at1 = False
    has_tier2 = False
    
    if "CET1" in of:
        cet1 = of["CET1"]
        for component in cet1.values():
            if isinstance(component, dict) and component.get("amount") not in [None, 0]:
                has_cet1 = True
                break
    
    if "AT1" in of and "instruments" in of["AT1"]:
        if of["AT1"]["instruments"].get("amount") not in [None, 0]:
            has_at1 = True
    
    if "Tier2" in of and "instruments" in of["Tier2"]:
        if of["Tier2"]["instruments"].get("amount") not in [None, 0]:
            has_tier2 = True
    
    # Business logic checks
    if has_cet1 and not has_at1 and not has_tier2:
        flags.append(ValidationFlag(
            "info",
            "Only CET1 capital reported - confirm no AT1 or Tier 2 instruments exist",
            "cross_component",
            "Review if bank should have AT1 or Tier 2 capital instruments"
        ))
    
    if (has_at1 or has_tier2) and not has_cet1:
        flags.append(ValidationFlag(
            "error",
            "Higher tier capital reported but no CET1 capital found",
            "cross_component",
            "CET1 capital is typically required before AT1/Tier 2 instruments"
        ))
    
    return flags

def _validate_summary(data: Dict[str, Any]) -> List[ValidationFlag]:
    """Validate summary calculations."""
    flags = []
    
    if "summary" not in data:
        flags.append(ValidationFlag(
            "warning",
            "Missing summary section",
            "summary",
            "Include summary calculations for total capital amounts"
        ))
        return flags
    
    summary = data["summary"]
    
    # Recalculate and verify totals
    calculated_summary = calculate_summary(data)
    
    for key in ["total_cet1", "total_at1", "total_tier2", "total_own_funds"]:
        if key in summary:
            expected = calculated_summary[key]
            actual = summary[key]
            
            if actual != expected:
                flags.append(ValidationFlag(
                    "warning",
                    f"Summary {key} mismatch: expected {expected}, got {actual}",
                    f"summary.{key}",
                    "Verify summary calculations are correct"
                ))
    
    return flags

def _validate_regulatory_compliance(data: Dict[str, Any]) -> List[ValidationFlag]:
    """Validate regulatory compliance rules."""
    flags = []
    
    # Check for proper currency formatting
    if "currency" not in data:
        flags.append(ValidationFlag(
            "warning",
            "Missing currency specification",
            "currency",
            "Specify reporting currency (typically GBP for UK banks)"
        ))
    
    # Check for reporting date
    if "reporting_date" not in data:
        flags.append(ValidationFlag(
            "info",
            "Missing reporting date",
            "reporting_date",
            "Include reporting date for the COREP submission"
        ))
    
    # Validate template reference
    if data.get("template") != "C 01.00":
        flags.append(ValidationFlag(
            "warning",
            f"Unexpected template reference: {data.get('template')}",
            "template",
            "Ensure template is set to 'C 01.00' for Own Funds reporting"
        ))
    
    # Check for audit trail references
    of = data.get("own_funds", {})
    for tier_name, tier in of.items():
        if isinstance(tier, dict):
            for component_name, component in tier.items():
                if isinstance(component, dict):
                    if "justification_refs" not in component or not component["justification_refs"]:
                        flags.append(ValidationFlag(
                            "warning",
                            f"Missing regulatory references for {tier_name}.{component_name}",
                            f"{tier_name}.{component_name}.justification_refs",
                            "Include regulatory source references for audit trail"
                        ))
    
    return flags

def format_validation_flags(flags: List[ValidationFlag]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group validation flags by type for reporting.
    
    Args:
        flags (list): List of validation flags
        
    Returns:
        dict: Grouped flags by type
    """
    grouped = {
        "errors": [],
        "warnings": [],
        "info": []
    }
    
    for flag in flags:
        flag_dict = flag.to_dict()
        flag_type_key = f"{flag.type}s"
        if flag_type_key in grouped:
            grouped[flag_type_key].append(flag_dict)
        else:
            # Handle any unexpected flag types
            if flag_type_key not in grouped:
                grouped[flag_type_key] = []
            grouped[flag_type_key].append(flag_dict)
    
    return grouped

def generate_validation_report(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate comprehensive validation report.
    
    Args:
        data (dict): Structured COREP output
        
    Returns:
        dict: Complete validation report
    """
    flags = validate_corep(data)
    grouped_flags = format_validation_flags(flags)
    
    report = {
        "validation_summary": {
            "total_flags": len(flags),
            "errors": len(grouped_flags["errors"]),
            "warnings": len(grouped_flags["warnings"]),
            "info": len(grouped_flags["info"]),
            "status": "PASS" if len(grouped_flags["errors"]) == 0 else "FAIL"
        },
        "validation_flags": grouped_flags,
        "recommendations": _generate_recommendations(flags)
    }
    
    return report

def _generate_recommendations(flags: List[ValidationFlag]) -> List[str]:
    """Generate recommendations based on validation flags."""
    recommendations = []
    
    error_count = sum(1 for f in flags if f.type == "error")
    warning_count = sum(1 for f in flags if f.type == "warning")
    
    if error_count > 0:
        recommendations.append(f"Address {error_count} critical error(s) before submission")
    
    if warning_count > 0:
        recommendations.append(f"Review {warning_count} warning(s) for regulatory compliance")
    
    # Specific recommendations based on common issues
    missing_refs = sum(1 for f in flags if "justification_refs" in f.message)
    if missing_refs > 0:
        recommendations.append("Add regulatory source references for audit trail completeness")
    
    missing_amounts = sum(1 for f in flags if "amount" in f.message and f.field)
    if missing_amounts > 0:
        recommendations.append("Complete all applicable amount fields or confirm they are truly not applicable")
    
    if not recommendations:
        recommendations.append("Validation passed - review output for accuracy before submission")
    
    return recommendations

if __name__ == "__main__":
    # Test validation with sample data
    sample_data = {
        "template": "C 01.00",
        "currency": "GBP",
        "own_funds": {
            "CET1": {
                "ordinary_share_capital": {"amount": 120000000},
                "retained_earnings": {"amount": None},  # Missing amount
                "intangibles_deduction": {"amount": 8000000}  # Should be negative
            },
            "AT1": {
                "instruments": {"amount": 0}  # Zero amount
            }
            # Missing Tier2
        }
    }
    
    print("Validation Test:")
    flags = validate_corep(sample_data)
    
    for flag in flags:
        print(f"[{flag.type.upper()}] {flag.message}")
        if flag.field:
            print(f"  Field: {flag.field}")
        if flag.suggestion:
            print(f"  Suggestion: {flag.suggestion}")
        print()
    
    print("\nValidation Report:")
    report = generate_validation_report(sample_data)
    print(json.dumps(report, indent=2))
