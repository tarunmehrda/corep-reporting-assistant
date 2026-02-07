# LLM-Assisted PRA COREP Reporting Assistant

A modular, production-style prototype for automated regulatory reporting using Groq API and RAG (Retrieval-Augmented Generation).

## Features

- 📚 Regulatory document loading and embedding
- 🔍 Vector search for relevant PRA/COREP rules
- 🤖 Groq LLM for structured COREP output generation
- 📄 Template mapping to human-readable format
- ✅ Validation engine with audit trail
- 🌐 FastAPI backend
- 🖥️ Streamlit demo UI

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variable:
```bash
export GROQ_API_KEY="your_api_key_here"
```

3. Run the backend:
```bash
uvicorn main:app --reload
```

4. Run the frontend:
```bash
streamlit run app.py
```

## Project Structure

```
├── data_loader.py          # Phase 1: Document loading
├── retriever.py            # Phase 2: Vector search
├── llm_corep.py            # Phase 3: Groq LLM integration
├── template_mapper.py      # Phase 4: Template mapping
├── validator.py            # Phase 5: Validation engine
├── main.py                 # Phase 6: FastAPI backend
├── app.py                  # Phase 7: Streamlit UI
├── reg_docs/               # Sample regulatory documents
└── requirements.txt        # Dependencies
```

## Architecture

User Query → Document Retrieval → LLM Reasoning → Structured Output → Template Mapping → Validation

## Scope

Currently focused on COREP Template C 01.00 - Own Funds reporting with:
- CET1 components (ordinary share capital, retained earnings)
- AT1 instruments
- Tier 2 instruments
- Regulatory deductions (intangible assets)
