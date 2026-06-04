import uuid
import re
from typing import List, Dict, Any
from config.settings import settings
from utils.logger import logger

class ChunkingService:
    @staticmethod
    def split_into_sentences(text: str) -> List[str]:
        """Split text into sentences using regex, ignoring common abbreviations."""
        # Split on sentence endings (. ? !) followed by whitespace, avoiding common abbreviations
        sentence_endings = re.compile(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s')
        sentences = sentence_endings.split(text)
        return [s.strip() for s in sentences if s.strip()]

    @classmethod
    def generate_chunks(
        cls,
        pages: Dict[int, str],
        workspace_id: str,
        document_id: int,
        parent_size: int = None,
        child_size: int = None,
        child_overlap: int = None
    ) -> List[Dict[str, Any]]:
        """
        Processes pages of a document and returns a list of parent chunks and child chunks.
        
        Args:
            pages: Dict of page numbers to text.
            workspace_id: ID of the active workspace.
            document_id: SQLite primary key for the document.
            parent_size: Target character count for parent chunks. Defaults to settings.CHUNK_SIZE.
            child_size: Target character count for child chunks. Defaults to parent_size // 4.
            child_overlap: Character overlap for child chunks. Defaults to child_size // 5.
            
        Returns:
            List of dictionaries containing either type "parent" or "child".
        """
        if parent_size is None:
            parent_size = settings.CHUNK_SIZE
        if child_size is None:
            child_size = parent_size // 4
        if child_overlap is None:
            child_overlap = child_size // 5
            
        logger.info(
            f"Chunking document {document_id} in workspace {workspace_id} "
            f"(Parent size: {parent_size}, Child size: {child_size}, Child overlap: {child_overlap})"
        )
        
        chunks = []
        parent_counter = 0
        
        for page_num, text in pages.items():
            if not text.strip():
                continue
                
            # Split page text into paragraphs
            paragraphs = re.split(r'\n\s*\n', text)
            paragraphs = [p.strip() for p in paragraphs if p.strip()]
            
            current_parent_paragraphs = []
            current_parent_len = 0
            
            def create_chunks_for_text(content_text: str):
                nonlocal parent_counter
                parent_counter += 1
                parent_id = f"{workspace_id}_{document_id}_p{parent_counter}_{uuid.uuid4().hex[:6]}"
                
                # 1. Store Parent Chunk
                chunks.append({
                    "type": "parent",
                    "parent_id": parent_id,
                    "workspace_id": workspace_id,
                    "document_id": document_id,
                    "page_number": page_num,
                    "content": content_text
                })
                
                # 2. Store Child Chunks
                sentences = cls.split_into_sentences(content_text)
                current_child_sentences = []
                current_child_len = 0
                
                for sentence in sentences:
                    # Flush if adding the sentence exceeds child_size limit
                    if current_child_len + len(sentence) > child_size and current_child_sentences:
                        child_text = " ".join(current_child_sentences)
                        chunks.append({
                            "type": "child",
                            "parent_id": parent_id,
                            "workspace_id": workspace_id,
                            "document_id": document_id,
                            "page_number": page_num,
                            "content": child_text
                        })
                        
                        # Apply overlap by stepping backward from current sentence list
                        overlap_sentences = []
                        overlap_len = 0
                        for s in reversed(current_child_sentences):
                            if overlap_len + len(s) < child_overlap:
                                overlap_sentences.insert(0, s)
                                overlap_len += len(s)
                            else:
                                break
                        current_child_sentences = overlap_sentences
                        current_child_len = overlap_len
                        
                    current_child_sentences.append(sentence)
                    current_child_len += len(sentence) + 1
                    
                # Final child chunk flush
                if current_child_sentences:
                    child_text = " ".join(current_child_sentences)
                    chunks.append({
                        "type": "child",
                        "parent_id": parent_id,
                        "workspace_id": workspace_id,
                        "document_id": document_id,
                        "page_number": page_num,
                        "content": child_text
                    })

            for para in paragraphs:
                para_len = len(para)
                
                # If paragraph exceeds the size of a parent chunk, split paragraph by sentences
                if para_len > parent_size:
                    if current_parent_paragraphs:
                        create_chunks_for_text("\n\n".join(current_parent_paragraphs))
                        current_parent_paragraphs = []
                        current_parent_len = 0
                        
                    para_sentences = cls.split_into_sentences(para)
                    sentence_buffer = []
                    buffer_len = 0
                    for sent in para_sentences:
                        if buffer_len + len(sent) > parent_size and sentence_buffer:
                            create_chunks_for_text(" ".join(sentence_buffer))
                            sentence_buffer = []
                            buffer_len = 0
                        sentence_buffer.append(sent)
                        buffer_len += len(sent) + 1
                    if sentence_buffer:
                        create_chunks_for_text(" ".join(sentence_buffer))
                        
                elif current_parent_len + para_len > parent_size and current_parent_paragraphs:
                    create_chunks_for_text("\n\n".join(current_parent_paragraphs))
                    current_parent_paragraphs = [para]
                    current_parent_len = para_len
                else:
                    current_parent_paragraphs.append(para)
                    current_parent_len += para_len + 2
                    
            if current_parent_paragraphs:
                create_chunks_for_text("\n\n".join(current_parent_paragraphs))
                
        logger.info(f"Chunked document {document_id}. Total chunks generated: {len(chunks)}.")
        return chunks
