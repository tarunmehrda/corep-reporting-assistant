import os

def load_regulatory_docs(folder_path="reg_docs"):
    """
    Load regulatory documents from the specified folder.
    
    Args:
        folder_path (str): Path to the folder containing regulatory documents
        
    Returns:
        list: List of dictionaries containing document source and text
    """
    docs = []
    
    if not os.path.exists(folder_path):
        print(f"Warning: Folder '{folder_path}' does not exist.")
        return docs
    
    for file in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file)
        if os.path.isfile(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
                    docs.append({
                        "source": file,
                        "text": text
                    })
                    print(f"Loaded: {file}")
            except Exception as e:
                print(f"Error loading {file}: {e}")
    
    return docs

if __name__ == "__main__":
    # Test the loader
    documents = load_regulatory_docs()
    print(f"\nLoaded {len(documents)} documents")
    for doc in documents:
        print(f"- {doc['source']}: {len(doc['text'])} characters")
