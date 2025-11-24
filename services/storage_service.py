# services/storage_service.py

import os
import uuid
from datetime import datetime
from models import Document

class StorageService:
    def generate_unique_app_id(self):
        """Generate a unique application ID"""
        return f"APP{uuid.uuid4().hex[:8].upper()}"
    
    def save_application_documents(self, mobile_number, app_id, files):
        """Save application documents to the filesystem"""
        saved_docs = []
        base_path = f"uploads/{mobile_number}/{app_id}"
        
        for doc_type, file in files.items():
            if file and file.filename:
                # Create directory if it doesn't exist
                os.makedirs(base_path, exist_ok=True)
                
                # Generate unique filename
                file_extension = os.path.splitext(file.filename)[1]
                filename = f"{doc_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_extension}"
                file_path = os.path.join(base_path, filename)
                
                # Save file
                file.save(file_path)
                
                # Create document record
                doc = Document(
                    application_id=app_id,
                    document_type=doc_type,
                    file_path=file_path,
                    original_filename=file.filename
                )
                saved_docs.append(doc)
        
        return saved_docs