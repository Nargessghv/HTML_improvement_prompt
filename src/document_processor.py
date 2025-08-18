"""
Document processor for handling uploaded context documents.
Extracts text from PDF, Word, PowerPoint, and text files for use as context in presentation generation.
"""

import os
import logging
import base64
import mimetypes
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
from datetime import datetime, timezone
import tempfile
import uuid

# Document processing libraries
import PyPDF2
from docx import Document as WordDocument
from pptx import Presentation

# Try to import textract, but make it optional
try:
    import textract
    TEXTRACT_AVAILABLE = True
except ImportError:
    TEXTRACT_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("textract not available - fallback text extraction disabled")

from .database import get_supabase_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Handles document upload, storage, and text extraction for context"""
    
    SUPPORTED_FORMATS = {
        'application/pdf': '.pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
        'application/msword': '.doc',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
        'application/vnd.ms-powerpoint': '.ppt',
        'text/plain': '.txt',
        'text/markdown': '.md'
    }
    
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit
    
    def __init__(self):
        """Initialize document processor with database client"""
        self.db = get_supabase_client()
        self.storage_bucket = 'project-documents'
    
    async def process_uploaded_document(
        self,
        file_content: Union[bytes, str],
        filename: str,
        project_id: str,
        user_id: str,
        mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process an uploaded document for use as context.
        
        Args:
            file_content: Raw file content (bytes or base64 string)
            filename: Original filename
            project_id: Project UUID
            user_id: User UUID
            mime_type: MIME type of the file
            
        Returns:
            Document record with extracted text and metadata
        """
        try:
            # Convert base64 to bytes if needed
            if isinstance(file_content, str):
                # Handle base64 data URLs
                if file_content.startswith('data:'):
                    header, data = file_content.split(',', 1)
                    file_content = base64.b64decode(data)
                else:
                    file_content = base64.b64decode(file_content)
            
            # Validate file size
            file_size = len(file_content)
            if file_size > self.MAX_FILE_SIZE:
                raise ValueError(f"File size ({file_size} bytes) exceeds maximum allowed size ({self.MAX_FILE_SIZE} bytes)")
            
            # Determine mime type if not provided
            if not mime_type:
                mime_type, _ = mimetypes.guess_type(filename)
            
            # Validate file type
            if mime_type not in self.SUPPORTED_FORMATS:
                raise ValueError(f"Unsupported file type: {mime_type}")
            
            # Generate unique storage path
            file_extension = self.SUPPORTED_FORMATS[mime_type]
            file_id = str(uuid.uuid4())
            storage_path = f"{user_id}/{project_id}/{file_id}{file_extension}"
            
            # Upload to Supabase Storage
            try:
                storage_response = self.db.client.storage.from_(self.storage_bucket).upload(
                    path=storage_path,
                    file=file_content,
                    file_options={"content-type": mime_type}
                )
                
                # Get signed URL for access (valid for 1 year)
                url_response = self.db.client.storage.from_(self.storage_bucket).create_signed_url(
                    path=storage_path,
                    expires_in=365 * 24 * 60 * 60  # 1 year
                )
                storage_url = url_response.get('signedURL', '')
                
            except Exception as e:
                logger.error(f"Failed to upload document to storage: {e}")
                raise ValueError(f"Storage upload failed: {str(e)}")
            
            # Create initial database record
            document_record = {
                'project_id': project_id,
                'user_id': user_id,
                'filename': filename,
                'file_type': file_extension[1:],  # Remove the dot
                'file_size': file_size,
                'mime_type': mime_type,
                'storage_path': storage_path,
                'storage_url': storage_url,
                'processing_status': 'processing',
                'extracted_metadata': {}
            }
            
            # Insert record into database
            result = self.db.client.table('project_documents').insert(document_record).execute()
            document_id = result.data[0]['id'] if result.data else None
            
            if not document_id:
                raise ValueError("Failed to create document record")
            
            # Extract text based on file type
            extracted_text = ""
            metadata = {}
            
            try:
                if mime_type == 'application/pdf':
                    extracted_text, metadata = self._extract_pdf_text(file_content)
                elif mime_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword']:
                    extracted_text, metadata = self._extract_word_text(file_content)
                elif mime_type in ['application/vnd.openxmlformats-officedocument.presentationml.presentation', 'application/vnd.ms-powerpoint']:
                    extracted_text, metadata = self._extract_powerpoint_text(file_content)
                elif mime_type in ['text/plain', 'text/markdown']:
                    extracted_text = file_content.decode('utf-8', errors='ignore')
                    metadata = {'character_count': len(extracted_text)}
                else:
                    # Fallback to textract for other formats
                    extracted_text = self._extract_with_textract(file_content, file_extension)
                    metadata = {'extraction_method': 'textract'}
                
                # Update document record with extracted content
                update_data = {
                    'extracted_text': extracted_text[:500000],  # Limit to 500k chars
                    'extracted_metadata': metadata,
                    'processing_status': 'completed',
                    'processed_at': datetime.now(timezone.utc).isoformat()
                }
                
                self.db.client.table('project_documents').update(update_data).eq('id', document_id).execute()
                
                # Update project to indicate it has context documents
                self.db.client.table('projects').update({
                    'has_context_documents': True
                }).eq('id', project_id).execute()
                
                logger.info(f"Successfully processed document {filename} for project {project_id}")
                
                return {
                    'id': document_id,
                    'filename': filename,
                    'extracted_text': extracted_text,
                    'metadata': metadata,
                    'storage_url': storage_url
                }
                
            except Exception as e:
                # Update document record with error
                self.db.client.table('project_documents').update({
                    'processing_status': 'failed',
                    'error_message': str(e)
                }).eq('id', document_id).execute()
                
                logger.error(f"Failed to extract text from document: {e}")
                raise ValueError(f"Text extraction failed: {str(e)}")
                
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            raise
    
    def _extract_pdf_text(self, file_content: bytes) -> tuple[str, Dict[str, Any]]:
        """Extract text and metadata from PDF file"""
        text_parts = []
        metadata = {}
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(file_content)
            tmp_file.flush()
            
            try:
                with open(tmp_file.name, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    
                    # Extract metadata
                    metadata['page_count'] = len(pdf_reader.pages)
                    if pdf_reader.metadata:
                        metadata['title'] = getattr(pdf_reader.metadata, 'title', None)
                        metadata['author'] = getattr(pdf_reader.metadata, 'author', None)
                        metadata['subject'] = getattr(pdf_reader.metadata, 'subject', None)
                    
                    # Extract text from each page
                    for page_num, page in enumerate(pdf_reader.pages, 1):
                        page_text = page.extract_text()
                        if page_text.strip():
                            text_parts.append(f"[Page {page_num}]\n{page_text}")
                
                extracted_text = "\n\n".join(text_parts)
                
            finally:
                os.unlink(tmp_file.name)
        
        return extracted_text, metadata
    
    def _extract_word_text(self, file_content: bytes) -> tuple[str, Dict[str, Any]]:
        """Extract text and metadata from Word document"""
        text_parts = []
        metadata = {}
        
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp_file:
            tmp_file.write(file_content)
            tmp_file.flush()
            
            try:
                doc = WordDocument(tmp_file.name)
                
                # Extract metadata
                core_properties = doc.core_properties
                metadata['title'] = core_properties.title
                metadata['author'] = core_properties.author
                metadata['paragraph_count'] = len(doc.paragraphs)
                
                # Extract text from paragraphs
                for para in doc.paragraphs:
                    if para.text.strip():
                        text_parts.append(para.text)
                
                # Extract text from tables
                for table in doc.tables:
                    for row in table.rows:
                        row_text = []
                        for cell in row.cells:
                            if cell.text.strip():
                                row_text.append(cell.text.strip())
                        if row_text:
                            text_parts.append(" | ".join(row_text))
                
                extracted_text = "\n\n".join(text_parts)
                
            finally:
                os.unlink(tmp_file.name)
        
        return extracted_text, metadata
    
    def _extract_powerpoint_text(self, file_content: bytes) -> tuple[str, Dict[str, Any]]:
        """Extract text and metadata from PowerPoint presentation"""
        text_parts = []
        metadata = {}
        
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp_file:
            tmp_file.write(file_content)
            tmp_file.flush()
            
            try:
                prs = Presentation(tmp_file.name)
                
                # Extract metadata
                core_properties = prs.core_properties
                metadata['title'] = core_properties.title
                metadata['author'] = core_properties.author
                metadata['slide_count'] = len(prs.slides)
                
                # Extract text from slides
                for slide_num, slide in enumerate(prs.slides, 1):
                    slide_text = []
                    
                    # Extract text from shapes
                    for shape in slide.shapes:
                        if hasattr(shape, "text") and shape.text.strip():
                            slide_text.append(shape.text)
                    
                    if slide_text:
                        text_parts.append(f"[Slide {slide_num}]\n" + "\n".join(slide_text))
                
                extracted_text = "\n\n".join(text_parts)
                
            finally:
                os.unlink(tmp_file.name)
        
        return extracted_text, metadata
    
    def _extract_with_textract(self, file_content: bytes, file_extension: str) -> str:
        """Fallback text extraction using textract"""
        if not TEXTRACT_AVAILABLE:
            logger.warning("textract not available - returning empty text")
            return "Text extraction not available for this file type"
            
        with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as tmp_file:
            tmp_file.write(file_content)
            tmp_file.flush()
            
            try:
                text = textract.process(tmp_file.name).decode('utf-8', errors='ignore')
                return text
            finally:
                os.unlink(tmp_file.name)
    
    async def get_project_documents(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all documents for a project"""
        result = self.db.client.table('project_documents')\
            .select('*')\
            .eq('project_id', project_id)\
            .eq('processing_status', 'completed')\
            .execute()
        
        return result.data if result.data else []
    
    async def get_combined_context(self, project_id: str) -> str:
        """Get combined text context from all project documents"""
        documents = await self.get_project_documents(project_id)
        
        if not documents:
            return ""
        
        context_parts = []
        for doc in documents:
            if doc.get('extracted_text'):
                context_parts.append(f"=== Document: {doc['filename']} ===\n{doc['extracted_text']}")
        
        return "\n\n".join(context_parts)
    
    async def delete_document(self, document_id: str, user_id: str) -> bool:
        """Delete a document and its storage file"""
        try:
            # Get document record
            result = self.db.client.table('project_documents')\
                .select('storage_path')\
                .eq('id', document_id)\
                .eq('user_id', user_id)\
                .execute()
            
            if not result.data:
                return False
            
            storage_path = result.data[0]['storage_path']
            
            # Delete from storage
            self.db.client.storage.from_(self.storage_bucket).remove([storage_path])
            
            # Delete from database
            self.db.client.table('project_documents')\
                .delete()\
                .eq('id', document_id)\
                .execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False