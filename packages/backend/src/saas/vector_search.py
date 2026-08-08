"""
Vector Search Service - Semantic Knowledge Retrieval
=====================================================

Handles vector similarity search using pgvector for knowledge base queries.
Supports hybrid search (vector + keyword) and filtering.

Author: W3J Consulting
Date: 2026-02-11
Phase: 2 - Knowledge Base System
"""

from typing import List, Dict, Optional, Tuple
import numpy as np
from loguru import logger
from google import genai


class VectorSearch:
    """
    Vector-based semantic search for knowledge bases
    
    Features:
    - Semantic similarity search using vector embeddings
    - Hybrid search combining vector and keyword matching
    - Configurable similarity thresholds
    - Multi-tenant isolation
    - Result ranking and reranking
    """

    def __init__(
        self,
        supabase_client,
        gemini_api_key: str,
        embedding_model: str = "models/text-embedding-004",
        similarity_threshold: float = 0.7
    ):
        """
        Initialize vector search service
        
        Args:
            supabase_client: Supabase client instance
            gemini_api_key: Gemini API key for embeddings
            embedding_model: Model to use for embeddings
            similarity_threshold: Minimum similarity score (0-1)
        """
        self.db = supabase_client
        self.similarity_threshold = similarity_threshold
        self.embedding_model = embedding_model
        
        # Initialize Gemini client for embeddings
        self.client = genai.Client(api_key=gemini_api_key)

    async def create_embedding(self, text: str) -> List[float]:
        """
        Create embedding for text using Gemini
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector (list of floats)
        """
        try:
            result = self.client.models.embed_content(
                model=self.embedding_model,
                content=text
            )
            
            # Extract embedding from response
            embedding = result.embeddings[0].values
            
            logger.debug(f"Created embedding with {len(embedding)} dimensions")
            return embedding
            
        except Exception as e:
            logger.error(f"Error creating embedding: {e}")
            raise

    async def search_knowledge(
        self,
        query: str,
        tenant_id: str,
        top_k: int = 5,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search knowledge base using semantic similarity
        
        Args:
            query: Search query
            tenant_id: Tenant ID for isolation
            top_k: Number of results to return
            filters: Optional filters (category, tags, etc.)
            
        Returns:
            List of matching knowledge chunks with scores
        """
        try:
            # Create embedding for query
            query_embedding = await self.create_embedding(query)
            
            # Build base query
            query_builder = (
                self.db.table("knowledge_chunks")
                .select("*, knowledge_bases!inner(title, category, tags)")
                .eq("tenant_id", tenant_id)
            )
            
            # Apply filters if provided
            if filters:
                if "category" in filters:
                    query_builder = query_builder.eq("knowledge_bases.category", filters["category"])
                
                if "knowledge_base_id" in filters:
                    query_builder = query_builder.eq("knowledge_base_id", filters["knowledge_base_id"])
            
            # Execute vector similarity search using RPC function
            results = await self._vector_similarity_search(
                query_embedding=query_embedding,
                tenant_id=tenant_id,
                top_k=top_k,
                filters=filters
            )
            
            # Filter by similarity threshold
            filtered_results = [
                r for r in results
                if r.get("similarity", 0) >= self.similarity_threshold
            ]
            
            logger.info(
                f"Found {len(filtered_results)} knowledge chunks "
                f"(threshold: {self.similarity_threshold})"
            )
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"Error searching knowledge: {e}")
            return []

    async def _vector_similarity_search(
        self,
        query_embedding: List[float],
        tenant_id: str,
        top_k: int,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Perform vector similarity search using pgvector
        
        Uses PostgreSQL function for optimized vector search
        """
        try:
            # Call PostgreSQL RPC function for vector search
            result = self.db.rpc(
                "search_knowledge_chunks",
                {
                    "query_embedding": query_embedding,
                    "p_tenant_id": tenant_id,
                    "match_count": top_k,
                    "similarity_threshold": self.similarity_threshold
                }
            ).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            # Fallback to basic search if RPC not available
            logger.warning(f"RPC search failed, using fallback: {e}")
            return await self._fallback_search(query_embedding, tenant_id, top_k, filters)

    async def _fallback_search(
        self,
        query_embedding: List[float],
        tenant_id: str,
        top_k: int,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Fallback search using Python-side similarity calculation
        
        Used when pgvector RPC functions are not available
        """
        # Get all chunks for tenant
        query_builder = (
            self.db.table("knowledge_chunks")
            .select("*, knowledge_bases!inner(title, category)")
            .eq("tenant_id", tenant_id)
        )
        
        # Apply filters
        if filters:
            if "category" in filters:
                query_builder = query_builder.eq("knowledge_bases.category", filters["category"])
        
        result = query_builder.execute()
        chunks = result.data if result.data else []
        
        # Calculate similarities
        scored_chunks = []
        for chunk in chunks:
            if chunk.get("embedding"):
                similarity = self._cosine_similarity(
                    query_embedding,
                    chunk["embedding"]
                )
                
                if similarity >= self.similarity_threshold:
                    chunk["similarity"] = similarity
                    scored_chunks.append(chunk)
        
        # Sort by similarity and return top_k
        scored_chunks.sort(key=lambda x: x["similarity"], reverse=True)
        return scored_chunks[:top_k]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        vec1_np = np.array(vec1)
        vec2_np = np.array(vec2)
        
        dot_product = np.dot(vec1_np, vec2_np)
        norm1 = np.linalg.norm(vec1_np)
        norm2 = np.linalg.norm(vec2_np)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))

    async def hybrid_search(
        self,
        query: str,
        tenant_id: str,
        top_k: int = 5,
        keyword_weight: float = 0.3,
        vector_weight: float = 0.7
    ) -> List[Dict]:
        """
        Hybrid search combining vector similarity and keyword matching
        
        Args:
            query: Search query
            tenant_id: Tenant ID
            top_k: Number of results
            keyword_weight: Weight for keyword matching (0-1)
            vector_weight: Weight for vector similarity (0-1)
            
        Returns:
            Ranked list of results
        """
        # Get vector search results
        vector_results = await self.search_knowledge(query, tenant_id, top_k=top_k*2)
        
        # Get keyword search results
        keyword_results = await self._keyword_search(query, tenant_id, top_k=top_k*2)
        
        # Combine and rerank
        combined = self._merge_and_rerank(
            vector_results,
            keyword_results,
            vector_weight,
            keyword_weight
        )
        
        return combined[:top_k]

    async def _keyword_search(
        self,
        query: str,
        tenant_id: str,
        top_k: int
    ) -> List[Dict]:
        """
        Keyword-based search using PostgreSQL full-text search
        """
        try:
            # Use PostgreSQL text search
            result = self.db.rpc(
                "keyword_search_knowledge",
                {
                    "search_query": query,
                    "p_tenant_id": tenant_id,
                    "match_count": top_k
                }
            ).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.warning(f"Keyword search failed: {e}")
            # Fallback to simple LIKE search
            result = (
                self.db.table("knowledge_chunks")
                .select("*")
                .eq("tenant_id", tenant_id)
                .ilike("chunk_text", f"%{query}%")
                .limit(top_k)
                .execute()
            )
            
            return result.data if result.data else []

    def _merge_and_rerank(
        self,
        vector_results: List[Dict],
        keyword_results: List[Dict],
        vector_weight: float,
        keyword_weight: float
    ) -> List[Dict]:
        """
        Merge vector and keyword results with weighted ranking
        """
        # Create score dictionary
        scores = {}
        
        # Add vector scores
        for i, result in enumerate(vector_results):
            chunk_id = result["id"]
            vector_score = result.get("similarity", 0)
            rank_score = 1 / (i + 1)  # Position-based score
            
            scores[chunk_id] = {
                "chunk": result,
                "vector_score": vector_score * vector_weight,
                "keyword_score": 0,
                "vector_rank": rank_score * vector_weight
            }
        
        # Add keyword scores
        for i, result in enumerate(keyword_results):
            chunk_id = result["id"]
            rank_score = 1 / (i + 1)
            
            if chunk_id in scores:
                scores[chunk_id]["keyword_score"] = rank_score * keyword_weight
            else:
                scores[chunk_id] = {
                    "chunk": result,
                    "vector_score": 0,
                    "keyword_score": rank_score * keyword_weight,
                    "vector_rank": 0
                }
        
        # Calculate combined scores
        ranked_results = []
        for chunk_id, score_data in scores.items():
            combined_score = (
                score_data["vector_score"] +
                score_data["keyword_score"] +
                score_data["vector_rank"]
            )
            
            chunk = score_data["chunk"]
            chunk["combined_score"] = combined_score
            ranked_results.append(chunk)
        
        # Sort by combined score
        ranked_results.sort(key=lambda x: x["combined_score"], reverse=True)
        
        return ranked_results

    async def search_with_context(
        self,
        query: str,
        tenant_id: str,
        conversation_history: Optional[List[str]] = None,
        top_k: int = 5
    ) -> Dict:
        """
        Search knowledge with conversation context
        
        Args:
            query: Current query
            tenant_id: Tenant ID
            conversation_history: Previous messages for context
            top_k: Number of results
            
        Returns:
            Search results with relevance scoring
        """
        # Enhance query with conversation context
        enhanced_query = query
        if conversation_history:
            # Use last 3 messages for context
            recent_context = " ".join(conversation_history[-3:])
            enhanced_query = f"{recent_context} {query}"
        
        # Search with enhanced query
        results = await self.search_knowledge(
            enhanced_query,
            tenant_id,
            top_k=top_k
        )
        
        return {
            "query": query,
            "results": results,
            "context_used": len(conversation_history) if conversation_history else 0
        }


# PostgreSQL functions to create for vector search
"""
-- Create vector similarity search function
CREATE OR REPLACE FUNCTION search_knowledge_chunks(
    query_embedding vector(1536),
    p_tenant_id uuid,
    match_count int DEFAULT 5,
    similarity_threshold float DEFAULT 0.7
)
RETURNS TABLE (
    id uuid,
    chunk_text text,
    chunk_index int,
    similarity float,
    knowledge_base_id uuid,
    section_title text
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        kc.id,
        kc.chunk_text,
        kc.chunk_index,
        1 - (kc.embedding <=> query_embedding) as similarity,
        kc.knowledge_base_id,
        kc.section_title
    FROM knowledge_chunks kc
    WHERE kc.tenant_id = p_tenant_id
        AND kc.embedding IS NOT NULL
        AND 1 - (kc.embedding <=> query_embedding) >= similarity_threshold
    ORDER BY kc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Create keyword search function
CREATE OR REPLACE FUNCTION keyword_search_knowledge(
    search_query text,
    p_tenant_id uuid,
    match_count int DEFAULT 5
)
RETURNS TABLE (
    id uuid,
    chunk_text text,
    rank float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        kc.id,
        kc.chunk_text,
        ts_rank(to_tsvector('english', kc.chunk_text), plainto_tsquery('english', search_query)) as rank
    FROM knowledge_chunks kc
    WHERE kc.tenant_id = p_tenant_id
        AND to_tsvector('english', kc.chunk_text) @@ plainto_tsquery('english', search_query)
    ORDER BY rank DESC
    LIMIT match_count;
END;
$$;
"""
