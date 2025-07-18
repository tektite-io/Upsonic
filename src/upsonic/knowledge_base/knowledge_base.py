from dataclasses import Field
import uuid
from pydantic import BaseModel
from ..utils.error_wrapper import upsonic_error_handler

from typing import Any, List, Dict, Optional, Type, Union


class KnowledgeBase(BaseModel):
    sources: List[str] = []
    rag_model: str | None = None
    _rag = None

    @property
    def rag(self):
        if self.rag_model is None:
            return False
        return True


    def add_file(self, file_path: str):
        self.sources.append(file_path)

    def remove_file(self, file_path: str):
        self.sources.remove(file_path)

    @upsonic_error_handler(max_retries=2, show_error_details=True)
    async def setup_rag(self, client):
        from lightrag import LightRAG, QueryParam
        from lightrag.llm.openai import openai_embed, gpt_4o_mini_complete

        from lightrag.utils import setup_logger
        setup_logger("lightrag", level="WARNING")

        if not self._rag:
            if not self.rag_model:
                raise ValueError("rag_model must be set before querying")

            if self.rag_model.startswith("openai"):
                embedding_func = openai_embed
            else:
                raise ValueError(f"Unsupported rag_model type: {self.rag_model}")

            self._rag = LightRAG(embedding_func=embedding_func, llm_model_func=gpt_4o_mini_complete)
            await self._rag.initialize_storages()
            for each in self.sources:
                self._rag.ainsert(client.markdown(each))
            return self._rag



    @upsonic_error_handler(max_retries=2, show_error_details=True)
    async def query(self, query: str, mode: str = "naive") -> List[str]:
        from lightrag import LightRAG, QueryParam
        from lightrag.llm.openai import openai_embed, gpt_4o_mini_complete

        from lightrag.utils import setup_logger
        setup_logger("lightrag", level="WARNING")

        """
        Unified function to handle RAG operations and querying.
        
        Args:
            query: The query string to search for
            mode: The search mode (default: "naive")
            
        Returns:
            List of relevant text snippets
        """
        if not self._rag:
            raise ValueError("RAG system not initialized. Call setup_rag first.")
        
        # Perform the query
        results = await self._rag.aquery(query, param=QueryParam(mode=mode, only_need_context=True))

        return results




    @upsonic_error_handler(max_retries=1, show_error_details=True)
    def markdown(self):
        knowledges = {}
        
        for file_path in self.sources:
            # Convert to markdown
            from markitdown import MarkItDown

            md = MarkItDown()
            markdown_content = md.convert(file_path).text_content
            knowledges[file_path] = markdown_content

        the_overall_string = ""
        
        for file_path, content in knowledges.items():
            the_overall_string += f"""
            <{file_path}>
            {content}
            </{file_path}>
            \n\n
            """
        
        return the_overall_string

