from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import our modules
from data_loader import load_regulatory_docs
from retriever import RegulatoryRetriever
from llm_corep import generate_corep_output, test_llm_connection
from template_mapper import map_to_template, format_template_rows, generate_template_export
from validator import generate_validation_report

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=getattr(logging, log_level))
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PRA COREP Reporting Assistant API",
    description="LLM-assisted regulatory reporting for PRA COREP templates",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for the system components
retriever = None
system_status = {
    "initialized": False,
    "documents_loaded": 0,
    "groq_connected": False,
    "last_init_time": None,
    "api_status": "unknown"  # Adding the missing field
}

# Pydantic models for API
class CorepRequest(BaseModel):
    user_query: str
    k_documents: int = 3
    export_format: Optional[str] = "json"

class CorepResponse(BaseModel):
    status: str
    timestamp: str
    retrieved_sources: List[Dict[str, Any]]
    structured_output: Dict[str, Any]
    corep_template: List[Dict[str, Any]]
    validation_report: Dict[str, Any]
    export_data: Optional[str] = None

class SystemStatus(BaseModel):
    initialized: bool
    documents_loaded: int
    groq_connected: bool
    last_init_time: Optional[str]
    api_status: str

class HealthResponse(BaseModel):
    status: str
    system: SystemStatus
    message: str

def initialize_system():
    """Initialize the system components."""
    global retriever, system_status
    
    try:
        logger.info("Initializing PRA COREP Reporting Assistant...")
        
        # Load regulatory documents
        logger.info("Loading regulatory documents...")
        docs_folder = os.getenv("DOCS_FOLDER", "reg_docs")
        docs = load_regulatory_docs(docs_folder)
        
        if not docs:
            logger.warning("No regulatory documents found. Please add documents to reg_docs folder.")
            system_status["documents_loaded"] = 0
        else:
            logger.info(f"Loaded {len(docs)} regulatory documents")
            system_status["documents_loaded"] = len(docs)
            
            # Initialize retriever
            logger.info("Initializing vector retriever...")
            embedding_model = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
            cache_file = os.getenv("EMBEDDINGS_CACHE_FILE", "embeddings_cache.pkl")
            retriever = RegulatoryRetriever(docs, model_name=embedding_model, cache_file=cache_file)
        
        # Test Hugging Face model connection
        logger.info("Testing Hugging Face model connection...")
        hf_test = test_llm_connection()
        system_status["groq_connected"] = "connection successful" in hf_test.lower() or "model connection successful" in hf_test.lower()
        
        if not system_status["groq_connected"]:
            logger.error(f"Hugging Face model connection failed: {hf_test}")
        else:
            logger.info("Hugging Face model connection successful")
        
        system_status["initialized"] = True
        system_status["last_init_time"] = datetime.now().isoformat()
        system_status["api_status"] = "healthy" if system_status["initialized"] and system_status["groq_connected"] else "unhealthy"
        
        logger.info("System initialization completed")
        
    except Exception as e:
        logger.error(f"System initialization failed: {str(e)}")
        system_status["initialized"] = False
        system_status["api_status"] = "unhealthy"
        raise

@app.on_event("startup")
async def startup_event():
    """Initialize system on startup."""
    try:
        initialize_system()
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "PRA COREP Reporting Assistant API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    # Ensure api_status is always set
    if "api_status" not in system_status:
        system_status["api_status"] = "unknown"
    
    api_status = "healthy" if system_status["initialized"] and system_status["groq_connected"] else "unhealthy"
    system_status["api_status"] = api_status  # Update status for the response
    
    return HealthResponse(
        status=api_status,
        system=SystemStatus(**system_status),
        message=f"System is {'initialized and ready' if system_status['initialized'] else 'not initialized'}"
    )

@app.post("/initialize")
async def initialize_endpoint(background_tasks: BackgroundTasks):
    """Manually reinitialize the system."""
    background_tasks.add_task(initialize_system)
    return {"message": "System reinitialization started"}

@app.post("/generate_corep", response_model=CorepResponse)
async def generate_corep(request: CorepRequest):
    """
    Generate COREP report from user query.
    
    Args:
        request: CorepRequest containing user query and options
        
    Returns:
        CorepResponse with complete analysis results
    """
    # Check system status
    if not system_status["initialized"]:
        raise HTTPException(status_code=503, detail="System not initialized. Call /initialize first.")
    
    if not system_status["groq_connected"]:
        raise HTTPException(status_code=503, detail="Hugging Face model not connected. Check model installation.")
    
    if not retriever:
        raise HTTPException(status_code=503, detail="Retriever not initialized. Check regulatory documents.")
    
    try:
        logger.info(f"Processing COREP request: {request.user_query[:100]}...")
        
        # Step 1: Retrieve relevant documents
        logger.info("Retrieving relevant regulatory documents...")
        retrieved_docs = retriever.search(request.user_query, k=request.k_documents)
        
        if not retrieved_docs:
            logger.warning("No relevant documents retrieved")
            raise HTTPException(
                status_code=404, 
                detail="No relevant regulatory documents found for the query"
            )
        
        # Step 2: Generate structured COREP output
        logger.info("Generating structured COREP output...")
        structured_output = generate_corep_output(request.user_query, retrieved_docs)
        
        if "error" in structured_output:
            logger.error(f"LLM generation failed: {structured_output['error']}")
            raise HTTPException(
                status_code=500,
                detail=f"LLM generation failed: {structured_output['error']}"
            )
        
        # Step 3: Map to template format
        logger.info("Mapping to COREP template...")
        template_rows = map_to_template(structured_output)
        formatted_template = format_template_rows(template_rows, structured_output.get("currency", "GBP"))
        
        # Step 4: Validate output
        logger.info("Validating COREP output...")
        validation_report = generate_validation_report(structured_output)
        
        # Step 5: Generate export if requested
        export_data = None
        if request.export_format:
            try:
                export_data = generate_template_export(structured_output, request.export_format)
            except Exception as e:
                logger.warning(f"Export generation failed: {str(e)}")
                export_data = f"Export failed: {str(e)}"
        
        # Step 6: Prepare response
        response = CorepResponse(
            status="success",
            timestamp=datetime.now().isoformat(),
            retrieved_sources=[{
                "source": doc["source"],
                "text": doc["text"],
                "score": doc.get("score", 0)
            } for doc in retrieved_docs],
            structured_output=structured_output,
            corep_template=formatted_template,
            validation_report=validation_report,
            export_data=export_data
        )
        
        logger.info("COREP generation completed successfully")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_corep: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/templates")
async def get_templates():
    """Get available COREP templates."""
    return {
        "templates": [
            {
                "id": "C 01.00",
                "name": "Own Funds",
                "description": "Template for reporting own funds composition (CET1, AT1, Tier 2)",
                "status": "active"
            }
        ]
    }

@app.get("/documents")
async def get_documents():
    """Get list of loaded regulatory documents."""
    if not retriever:
        raise HTTPException(status_code=503, detail="Retriever not initialized")
    
    documents = []
    for i, source in enumerate(retriever.sources):
        documents.append({
            "id": i,
            "source": source,
            "length": len(retriever.texts[i])
        })
    
    return {"documents": documents}

@app.post("/search")
async def search_documents(query: str, k: int = 5):
    """Search regulatory documents."""
    if not retriever:
        raise HTTPException(status_code=503, detail="Retriever not initialized")
    
    try:
        results = retriever.search(query, k=k)
        return {
            "query": query,
            "results": results,
            "total_found": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/stats")
async def get_system_stats():
    """Get system statistics."""
    stats = {
        "system_status": system_status,
        "retriever_info": None
    }
    
    if retriever:
        stats["retriever_info"] = {
            "documents_count": len(retriever.documents),
            "embedding_dimension": retriever.embeddings.shape[1] if hasattr(retriever, 'embeddings') else None,
            "index_size": retriever.index.ntotal if hasattr(retriever, 'index') else None
        }
    
    return stats

if __name__ == "__main__":
    import uvicorn
    
    # Get API configuration from environment
    api_host = os.getenv("API_HOST", "0.0.0.0")
    api_port = int(os.getenv("API_PORT", "8000"))
    api_debug = os.getenv("API_DEBUG", "false").lower() == "true"
    
    print("Starting PRA COREP Reporting Assistant API...")
    print(f"API will be available at: http://{api_host}:{api_port}")
    print("API documentation at: http://localhost:8000/docs")
    
    uvicorn.run(app, host=api_host, port=api_port, reload=api_debug)