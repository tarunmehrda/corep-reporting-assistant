# Quick Start Guide - PRA COREP Reporting Assistant

## Prerequisites

1. **Python 3.8+** installed on your system
2. **GROQ API Key** - You need to sign up for a free account at [groq.com](https://groq.com/) to get your API key
3. Basic understanding of banking regulatory reporting (COREP/PRA requirements)

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure API Keys
Create or update the `.env` file with your GROQ API key:

```env
# API Configuration
GROQ_API_KEY=your_actual_groq_api_key_here  # Replace with your API key
API_HOST=localhost
API_PORT=8000
STREAMLIT_HOST=localhost
STREAMLIT_PORT=8501

# Document Configuration
DOCS_FOLDER=reg_docs
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDINGS_CACHE_FILE=embeddings_cache.pkl

# Logging
LOG_LEVEL=INFO

# Frontend Configuration
FRONTEND_PORT=3001
```

### 3. Start the System

#### Option A: API Backend + Web Frontend (Recommended)

1. **Start the API server:**
```bash
python main.py
```
The API will be available at `http://localhost:8000`

2. **In a separate terminal, start the frontend:**
```bash
python serve_frontend.py
```
The frontend will be available at `http://localhost:3001`

3. **Open your browser** and navigate to `http://localhost:3001/frontend/index.html`

#### Option B: Streamlit Interface (Alternative)

```bash
streamlit run app.py
```
The Streamlit interface will be available at `http://localhost:8501`

## How to Use

1. **System Initialization**: On first load, click "Initialize System" to load regulatory documents and connect to the LLM
2. **Enter Scenario**: Describe your bank's capital composition in natural language
3. **Generate Report**: Click "Generate COREP Report" to analyze and create the report
4. **Review Results**: Check the generated template, validation results, and regulatory sources
5. **Export**: Download the report in your preferred format (JSON, CSV, HTML)

## Example Queries

Try these example scenarios:
- "The bank has £120m ordinary share capital, £30m retained earnings, £10m AT1 instruments, and £8m intangible assets."
- "Our bank holds £50m in ordinary shares, £15m retained earnings, no AT1 instruments, and £2m in goodwill that needs deduction."
- "Bank reports £200m CET1 capital consisting of £180m ordinary shares and £20m retained earnings, with £5m intangible deductions and £25m AT1 instruments."

## Troubleshooting

- **API Key Error**: Ensure your GROQ API key is correctly entered in the `.env` file
- **System Not Initialized**: Click "Initialize System" to load documents and connect to LLM
- **Slow Response**: Initial requests may take longer as embeddings are processed
- **Document Loading**: Make sure the `reg_docs` folder contains regulatory documents

## System Architecture

- **Frontend**: Modern HTML/CSS/JS interface (port 3001)
- **Backend API**: FastAPI server (port 8000)
- **LLM Integration**: Groq API with Llama 3 70B model
- **Document Retrieval**: FAISS vector database with sentence transformers
- **Validation Engine**: Comprehensive regulatory compliance checker

## Regulatory Documents

The system comes with sample regulatory documents in the `reg_docs` folder:
- COREP_C01_Instructions.txt
- CRR_Article_26.txt (Capital Requirements Regulation)
- CRR_Article_36.txt
- PRA_Own_Funds.txt

You can add more regulatory documents to enhance the system's knowledge base.

## Security Note

This system is intended for demonstration and educational purposes only. Do not use for actual regulatory submissions without proper validation and compliance review.