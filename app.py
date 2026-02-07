import streamlit as st
import requests
import json
from datetime import datetime
import pandas as pd
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Streamlit page
st.set_page_config(
    page_title="PRA COREP Reporting Assistant",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API configuration
API_BASE_URL = f"http://{os.getenv('STREAMLIT_HOST', 'localhost')}:{os.getenv('API_PORT', '8000')}"

def check_api_health():
    """Check if the API is healthy and ready."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data["status"] == "healthy", data
        return False, {"message": "API not responding correctly"}
    except requests.exceptions.RequestException as e:
        return False, {"message": f"Cannot connect to API: {str(e)}"}

def initialize_system():
    """Initialize the system via API."""
    try:
        response = requests.post(f"{API_BASE_URL}/initialize", timeout=30)
        return response.status_code == 200, response.json() if response.status_code == 200 else None
    except requests.exceptions.RequestException as e:
        return False, {"error": str(e)}

def generate_corep_report(query, k_docs=3, export_format="json"):
    """Generate COREP report via API."""
    try:
        payload = {
            "user_query": query,
            "k_documents": k_docs,
            "export_format": export_format
        }
        response = requests.post(f"{API_BASE_URL}/generate_corep", json=payload, timeout=60)
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, {"error": response.text}
            
    except requests.exceptions.RequestException as e:
        return False, {"error": str(e)}

def format_currency(amount, currency="GBP"):
    """Format amount as currency."""
    if amount is None:
        return "N/A"
    try:
        if currency == "GBP":
            return f"£{float(amount):,.2f}"
        else:
            return f"{float(amount):,.2f} {currency}"
    except (ValueError, TypeError):
        return str(amount)

def main():
    """Main Streamlit application."""
    st.title("🏦 PRA COREP Reporting Assistant")
    st.markdown("*LLM-Assisted Regulatory Reporting for UK Banks*")
    
    # Sidebar
    st.sidebar.title("System Status")
    
    # Check API health
    with st.sidebar:
        with st.spinner("Checking API status..."):
            is_healthy, health_data = check_api_health()
        
        if is_healthy:
            st.success("✅ API Healthy")
            system = health_data.get("system", {})
            st.info(f"""
            📚 Documents: {system.get('documents_loaded', 0)}
            🤖 Groq API: {'✅' if system.get('groq_connected') else '❌'}
            🕐 Last Init: {system.get('last_init_time', 'Never')[:19] if system.get('last_init_time') else 'Never'}
            """)
        else:
            st.error("❌ API Unhealthy")
            st.error(health_data.get("message", "Unknown error"))
            
            if st.button("🔄 Initialize System", type="primary"):
                with st.spinner("Initializing system..."):
                    success, init_data = initialize_system()
                if success:
                    st.success("System initialized successfully!")
                    st.rerun()
                else:
                    st.error(f"Initialization failed: {init_data}")
            st.stop()
    
    # Main content
    st.header("COREP Template C 01.00 - Own Funds Reporting")
    
    # Example scenarios
    with st.expander("📝 Example Scenarios"):
        examples = [
            "The bank has £120m ordinary share capital, £30m retained earnings, £10m AT1 instruments, and £8m intangible assets.",
            "Our bank holds £50m in ordinary shares, £15m retained earnings, no AT1 instruments, and £2m in goodwill that needs deduction.",
            "Bank reports £200m CET1 capital consisting of £180m ordinary shares and £20m retained earnings, with £5m intangible deductions and £25m AT1 instruments."
        ]
        
        for i, example in enumerate(examples, 1):
            if st.button(f"Example {i}", key=f"example_{i}"):
                st.session_state.example_query = example
    
    # Query input
    query = st.text_area(
        "Enter reporting scenario:",
        height=100,
        value=st.session_state.get("example_query", ""),
        placeholder="Describe the bank's capital composition for COREP reporting..."
    )
    
    # Configuration options
    col1, col2, col3 = st.columns(3)
    with col1:
        k_docs = st.slider("Documents to retrieve", min_value=1, max_value=10, value=3)
    with col2:
        export_format = st.selectbox("Export format", ["json", "csv", "html"], index=0)
    with col3:
        show_sources = st.checkbox("Show retrieved sources", value=True)
    
    # Generate button
    if st.button("🚀 Generate COREP Report", type="primary", disabled=not query.strip()):
        with st.spinner("Analyzing scenario and generating COREP report..."):
            success, result = generate_corep_report(query, k_docs, export_format)
        
        if success:
            st.session_state.last_result = result
            st.success("✅ COREP report generated successfully!")
        else:
            st.error(f"❌ Generation failed: {result.get('error', 'Unknown error')}")
            st.stop()
    
    # Display results
    if "last_result" in st.session_state:
        result = st.session_state.last_result
        
        # Summary section
        st.header("📊 Report Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Template", result["structured_output"].get("template", "C 01.00"))
        with col2:
            st.metric("Currency", result["structured_output"].get("currency", "GBP"))
        with col3:
            st.metric("Sources Retrieved", len(result["retrieved_sources"]))
        with col4:
            validation_status = "✅ Pass" if result["validation_report"]["validation_summary"]["status"] == "PASS" else "❌ Issues"
            st.metric("Validation", validation_status)
        
        # COREP Template Results
        st.header("📋 COREP Template Results")
        
        if result["corep_template"]:
            template_df = pd.DataFrame(result["corep_template"])
            template_df["Amount"] = template_df["amount"].apply(lambda x: format_currency(x, result["structured_output"].get("currency", "GBP")))
            
            # Display template table
            st.dataframe(
                template_df[["row_number", "description", "Amount"]],
                column_config={
                    "row_number": st.column_config.TextColumn("Row"),
                    "description": st.column_config.TextColumn("Description"),
                    "Amount": st.column_config.TextColumn("Amount")
                },
                hide_index=True,
                use_container_width=True
            )
            
            # Summary calculations
            if "summary" in result["structured_output"]:
                st.subheader("💰 Summary Calculations")
                summary = result["structured_output"]["summary"]
                
                sum_cols = st.columns(4)
                with sum_cols[0]:
                    st.metric("Total CET1", format_currency(summary.get("total_cet1"), result["structured_output"].get("currency", "GBP")))
                with sum_cols[1]:
                    st.metric("Total AT1", format_currency(summary.get("total_at1"), result["structured_output"].get("currency", "GBP")))
                with sum_cols[2]:
                    st.metric("Total Tier 2", format_currency(summary.get("total_tier2"), result["structured_output"].get("currency", "GBP")))
                with sum_cols[3]:
                    st.metric("Total Own Funds", format_currency(summary.get("total_own_funds"), result["structured_output"].get("currency", "GBP")))
        else:
            st.warning("No template data generated")
        
        # Validation Results
        st.header("✅ Validation Results")
        
        validation_summary = result["validation_report"]["validation_summary"]
        validation_flags = result["validation_report"]["validation_flags"]
        
        # Validation summary metrics
        val_cols = st.columns(4)
        with val_cols[0]:
            st.metric("Total Flags", validation_summary["total_flags"])
        with val_cols[1]:
            st.metric("Errors", validation_summary["errors"], delta=None, delta_color="inverse")
        with val_cols[2]:
            st.metric("Warnings", validation_summary["warnings"])
        with val_cols[3]:
            st.metric("Info", validation_summary["info"])
        
        # Detailed validation flags
        if validation_summary["total_flags"] > 0:
            st.subheader("🚩 Detailed Validation")
            
            for flag_type in ["errors", "warnings", "info"]:
                flags = validation_flags.get(flag_type, [])
                if flags:
                    with st.expander(f"{flag_type.title()} ({len(flags)})"):
                        for i, flag in enumerate(flags):
                            st.write(f"**{i+1}.** {flag['message']}")
                            if flag.get("field"):
                                st.write(f"   📍 Field: `{flag['field']}`")
                            if flag.get("suggestion"):
                                st.write(f"   💡 Suggestion: {flag['suggestion']}")
                            st.write("")
        else:
            st.success("🎉 All validation checks passed!")
        
        # Recommendations
        if result["validation_report"].get("recommendations"):
            st.subheader("💡 Recommendations")
            for rec in result["validation_report"]["recommendations"]:
                st.write(f"• {rec}")
        
        # Retrieved Sources
        if show_sources and result["retrieved_sources"]:
            st.header("📚 Retrieved Regulatory Sources")
            
            for i, source in enumerate(result["retrieved_sources"], 1):
                with st.expander(f"Source {i}: {source['source']} (Score: {source.get('score', 0):.3f})"):
                    st.write(source["text"])
        
        # Structured Output
        st.header("🔧 Structured Output")
        
        output_format = st.selectbox("Display format", ["JSON", "Pretty"], key="output_format")
        
        if output_format == "JSON":
            st.json(result["structured_output"])
        else:
            # Pretty display
            structured = result["structured_output"]
            
            st.subheader("Template Information")
            st.write(f"**Template:** {structured.get('template', 'N/A')}")
            st.write(f"**Currency:** {structured.get('currency', 'N/A')}")
            st.write(f"**Reporting Date:** {structured.get('reporting_date', 'N/A')}")
            
            if "own_funds" in structured:
                st.subheader("Own Funds Breakdown")
                own_funds = structured["own_funds"]
                
                for tier_name, tier_data in own_funds.items():
                    st.write(f"**{tier_name} Capital:**")
                    for component, details in tier_data.items():
                        if isinstance(details, dict):
                            amount = details.get("amount")
                            st.write(f"  • {component.replace('_', ' ').title()}: {format_currency(amount, structured.get('currency', 'GBP'))}")
                            if details.get("explanation"):
                                st.write(f"    _{details['explanation']}_")
                            if details.get("justification_refs"):
                                st.write(f"    📖 Sources: {', '.join(details['justification_refs'])}")
        
        # Export functionality
        if result.get("export_data"):
            st.header("📤 Export Data")
            
            if export_format == "json":
                st.download_button(
                    label="📥 Download JSON",
                    data=result["export_data"],
                    file_name=f"corep_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
            elif export_format == "csv":
                st.download_button(
                    label="📥 Download CSV",
                    data=result["export_data"],
                    file_name=f"corep_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            elif export_format == "html":
                st.download_button(
                    label="📥 Download HTML",
                    data=result["export_data"],
                    file_name=f"corep_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                    mime="text/html"
                )

# Footer
st.markdown("---")
st.markdown("""
**PRA COREP Reporting Assistant** | Built with Groq API, FastAPI, and Streamlit  
*For demonstration purposes only - not for production regulatory submissions*
""")

if __name__ == "__main__":
    main()
