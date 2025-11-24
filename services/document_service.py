# services/document_service.py
from models import db, Document, Application
from datetime import datetime

class DocumentService:
    @staticmethod
    def upload_document(application_id, document_type, file_path, original_filename):
        """Upload document and set initial verification status"""
        try:
            document = Document(
                application_id=application_id,
                document_type=document_type,
                file_path=file_path,
                original_filename=original_filename,
                uploaded_at=datetime.utcnow(),
                verification_status='VERIFIED',  # Auto-verify on upload
                ai_verification_result='AI Verified',
                risk_level='Low'
            )
            
            db.session.add(document)
            db.session.commit()
            
            # Update application document verification status
            application = Application.query.get(application_id)
            if application:
                application.document_verification_status = 'IN_PROGRESS'
                db.session.commit()
            
            return document
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def get_document_verification_summary(application_id):
        """Get document verification summary for an application"""
        documents = Document.query.filter_by(application_id=application_id).all()
        
        verified_count = len([d for d in documents if d.verification_status == 'VERIFIED'])
        pending_count = len([d for d in documents if d.verification_status == 'PENDING'])
        rejected_count = len([d for d in documents if d.verification_status == 'REJECTED'])
        total_documents = len(documents)
        
        return {
            'total_documents': total_documents,
            'verified_count': verified_count,
            'pending_count': pending_count,
            'rejected_count': rejected_count,
            'verification_rate': (verified_count / total_documents * 100) if total_documents > 0 else 0,
            'documents': documents
        }

    @staticmethod
    def update_document_verification(application_id, document_type, status, notes=None):
        """Update document verification status manually"""
        try:
            document = Document.query.filter_by(
                application_id=application_id, 
                document_type=document_type
            ).first()
            
            if document:
                document.verification_status = status
                if notes:
                    document.verification_notes = notes
                
                db.session.commit()
                return True
            return False
        except Exception as e:
            db.session.rollback()
            raise e