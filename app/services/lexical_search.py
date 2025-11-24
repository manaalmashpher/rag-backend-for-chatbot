"""
Lexical search service using PostgreSQL full-text search
"""

from typing import List, Dict, Any, Optional
from sqlalchemy import text
from app.core.database import get_db
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class LexicalSearchService:
    """
    Handles lexical keyword search using PostgreSQL full-text search
    """
    
    def __init__(self):
        self.topk_lex = getattr(settings, 'topk_lex', 20)
        self.database_url = settings.database_url
    
    def search(self, query: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Perform lexical keyword search using PostgreSQL full-text search
        
        Args:
            query: Search query string
            limit: Maximum number of results (defaults to topk_lex)
            
        Returns:
            List of search results with metadata
        """
        # Set limit
        search_limit = limit or self.topk_lex
        
        # Get database connection
        db = next(get_db())
        
        try:
            # Check if we're using PostgreSQL
            if self.database_url.startswith('postgresql://'):
                return self._postgresql_search(query, search_limit, db)
            else:
                # Fallback to LIKE search for SQLite
                return self._sqlite_like_search(query, search_limit, db)
                
        except Exception as e:
            logger.error(f"Lexical search failed: {str(e)}")
            raise RuntimeError(f"Lexical search failed: {str(e)}")
        finally:
            db.close()
    
    def _get_synonym_variants(self, query: str) -> List[str]:
        """
        Get list of query variants including synonyms
        
        Args:
            query: Original search query
            
        Returns:
            List of query variants (original + synonyms)
        """
        import re
        
        # Extended synonym mapping: base term -> list of synonyms
        # Expanded for domain terms: requirements, expected, compliance, evidence, etc.
        synonym_map = {
            # Evidence and supporting documents
            'evidence': ['supporting documents', 'supporting evidence', 'evidences', 'indicators'],
            'evidences': ['evidence', 'supporting documents', 'supporting evidence', 'indicators'],
            'supporting documents': ['evidence', 'evidences', 'supporting evidence', 'indicators'],
            'supporting evidence': ['evidence', 'evidences', 'supporting documents', 'indicators'],
            'indicator': ['indicators', 'evidence', 'supporting documents', 'supporting evidence'],
            'indicators': ['indicator', 'evidence', 'supporting documents', 'supporting evidence'],
            
            # Requirements and expectations
            'requirement': ['requirements', 'expected', 'expectations', 'obligations', 'compliance requirements'],
            'requirements': ['requirement', 'expected', 'expectations', 'obligations', 'compliance requirements'],
            'expected': ['requirements', 'expectations', 'obligations', 'compliance requirements'],
            'expectations': ['requirements', 'expected', 'obligations'],
            'obligations': ['requirements', 'expected', 'expectations', 'compliance requirements'],
            'compliance': ['requirements', 'obligations', 'standards', 'controls'],
            'compliance requirements': ['requirements', 'obligations', 'compliance', 'standards'],
            
            # Purpose and objectives
            'purpose': ['objective', 'goal', 'aim'],
            'objective': ['purpose', 'goal', 'aim'],
            'goal': ['purpose', 'objective', 'aim'],
            'aim': ['purpose', 'objective', 'goal'],
        }
        
        query_lower = query.lower()
        variants = [query]  # Always include original query
        
        # Check if any synonym term appears in the query (using word boundaries)
        # Process all matches, not just the first one
        matched_terms = []
        for term, synonyms in synonym_map.items():
            # Use word boundary matching to find the term as a whole word
            pattern = r'\b' + re.escape(term) + r'\b'
            if re.search(pattern, query_lower, re.IGNORECASE):
                matched_terms.append((term, synonyms))
        
        # Generate variants by replacing each matched term with its synonyms
        if matched_terms:
            # Start with original query
            current_variants = [query_lower]
            
            for term, synonyms in matched_terms:
                pattern = r'\b' + re.escape(term) + r'\b'
                new_variants = []
                for variant in current_variants:
                    # Add original variant
                    new_variants.append(variant)
                    # Add variants with synonym replacements
                    for synonym in synonyms:
                        replaced = re.sub(
                            pattern,
                            synonym,
                            variant,
                            flags=re.IGNORECASE
                        )
                        if replaced.lower() != variant.lower():
                            new_variants.append(replaced)
                current_variants = new_variants
                logger.info(f"Found synonym term '{term}' in query, adding variants: {synonyms}")
            
            variants.extend(current_variants)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_variants = []
        for variant in variants:
            variant_lower = variant.lower()
            if variant_lower not in seen:
                seen.add(variant_lower)
                unique_variants.append(variant)
        
        logger.info(f"Query '{query}' expanded to {len(unique_variants)} variants")
        return unique_variants
    
    def _expand_query_synonyms(self, query: str) -> str:
        """
        Expand query with synonyms for better lexical matching
        
        Args:
            query: Original search query
            
        Returns:
            Expanded query string with synonyms using OR logic for PostgreSQL FTS
            Formatted for to_tsquery: multi-word terms use & (AND), terms joined with | (OR)
        """
        import re
        
        # Synonym mapping: base term -> list of synonyms
        # Include plural forms in the mapping
        synonym_map = {
            'evidence': ['supporting documents', 'supporting evidence', 'evidences'],
            'evidences': ['evidence', 'supporting documents', 'supporting evidence'],
            'supporting documents': ['evidence', 'evidences', 'supporting evidence'],
            'supporting evidence': ['evidence', 'evidences', 'supporting documents'],
        }
        
        query_lower = query.lower()
        expanded_terms = [query]  # Always include original query
        
        # Check if any synonym term appears in the query (using word boundaries)
        for term, synonyms in synonym_map.items():
            if term in query_lower:
                expanded_terms.extend(synonyms)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_terms = []
        for term in expanded_terms:
            term_lower = term.lower()
            if term_lower not in seen:
                seen.add(term_lower)
                unique_terms.append(term)
        
        # If no synonyms were added, return original query
        if len(unique_terms) == 1:
            return query
        
        # Format terms for to_tsquery:
        # - Single words: use as-is
        # - Multi-word terms: join words with & (AND)
        # - Join all terms with | (OR)
        formatted_terms = []
        for term in unique_terms:
            words = term.split()
            if len(words) > 1:
                # Multi-word term: join with & (AND)
                formatted_term = ' & '.join(words)
                formatted_terms.append(f"({formatted_term})")
            else:
                # Single word: use as-is
                formatted_terms.append(term)
        
        # Join all terms with | (OR) for PostgreSQL FTS
        return ' | '.join(formatted_terms)
    
    def _postgresql_search(self, query: str, search_limit: int, db) -> List[Dict[str, Any]]:
        """PostgreSQL full-text search"""
        try:
            # Get synonym variants for the query
            synonym_variants = self._get_synonym_variants(query)
            
            # Build WHERE clause with OR conditions for each variant
            # Use plainto_tsquery for each variant (more forgiving than to_tsquery)
            where_conditions = []
            query_params = {"limit": search_limit}
            
            for i, variant in enumerate(synonym_variants):
                param_name = f"query_{i}"
                query_params[param_name] = variant
                where_conditions.append(
                    f"to_tsvector('english', c.text) @@ plainto_tsquery('english', :{param_name})"
                )
            
            # Combine with OR
            where_clause = " OR ".join(where_conditions)
            
            # Build query with MAX rank across all variants for better scoring
            # Use GREATEST to get the highest rank score from any matching variant
            rank_expressions = [
                f"COALESCE(ts_rank(to_tsvector('english', c.text), plainto_tsquery('english', :query_{i})), 0)"
                for i in range(len(synonym_variants))
            ]
            
            fts_query = f"""
            SELECT 
                c.id as chunk_id,
                c.doc_id,
                c.method,
                c.page_from,
                c.page_to,
                c.hash,
                d.title as source,
                c.text,
                GREATEST({', '.join(rank_expressions)}) as rank_score
            FROM chunks c
            JOIN documents d ON c.doc_id = d.id
            WHERE {where_clause}
            ORDER BY rank_score DESC, c.id DESC
            LIMIT :limit
            """
            
            result = db.execute(text(fts_query), query_params)
            
            formatted_results = []
            for row in result:
                formatted_result = {
                    'chunk_id': f"ch_{row.chunk_id:05d}",
                    'doc_id': f"doc_{row.doc_id:02X}",
                    'method': int(row.method),
                    'page_from': int(row.page_from) if row.page_from else None,
                    'page_to': int(row.page_to) if row.page_to else None,
                    'hash': str(row.hash),
                    'source': str(row.source),
                    'text': str(row.text),
                    'score': float(row.rank_score),
                    'search_type': 'lexical'
                }
                formatted_results.append(formatted_result)
            
            logger.info(f"PostgreSQL lexical search completed: {len(formatted_results)} results for query: {query[:50]}...")
            return formatted_results
            
        except Exception as e:
            logger.error(f"PostgreSQL search failed: {str(e)}")
            # Fallback to LIKE search
            return self._sqlite_like_search(query, search_limit, db)
    
    def _sqlite_like_search(self, query: str, search_limit: int, db) -> List[Dict[str, Any]]:
        """
        Fallback LIKE search for SQLite using term-based matching instead of full query LIKE
        
        This approach:
        - Extracts individual terms from the query
        - Expands terms using synonyms
        - Matches chunks that contain any of the terms (OR logic)
        - Scores by relevance (match_count / total_terms)
        """
        try:
            import re
            
            # Extract terms from query (word characters only, excluding stopwords)
            stopwords = {"what", "whats", "in", "the", "and", "of", "is", "section", "show", "go", "to"}
            query_lower = query.lower()
            terms = [t for t in re.findall(r"\w+", query_lower) if t not in stopwords and len(t) > 2]
            
            # Get synonym variants and extract their terms too
            synonym_variants = self._get_synonym_variants(query)
            all_terms = set(terms)
            for variant in synonym_variants:
                variant_terms = [t for t in re.findall(r"\w+", variant.lower()) if t not in stopwords and len(t) > 2]
                all_terms.update(variant_terms)
            
            # Remove stopwords from all_terms
            all_terms = {t for t in all_terms if t not in stopwords}
            
            if not all_terms:
                # Fallback to original query if no valid terms extracted
                all_terms = {query_lower}
            
            # Build WHERE clause with OR conditions for each term
            where_conditions = []
            query_params = {"limit": search_limit}
            
            for i, term in enumerate(all_terms):
                param_name = f"term_{i}"
                query_params[param_name] = f"%{term}%"
                where_conditions.append(f"c.text LIKE :{param_name}")
            
            if not where_conditions:
                # Fallback: use original query if no conditions built
                where_clause = "c.text LIKE :query"
                query_params["query"] = f"%{query}%"
            else:
                where_clause = " OR ".join(where_conditions)
            
            like_query = f"""
            SELECT 
                c.id as chunk_id,
                c.doc_id,
                c.method,
                c.page_from,
                c.page_to,
                c.hash,
                d.title as source,
                c.text
            FROM chunks c
            JOIN documents d ON c.doc_id = d.id
            WHERE {where_clause}
            LIMIT :limit
            """
            
            result = db.execute(text(like_query), query_params)
            
            formatted_results = []
            for row in result:
                # Calculate relevance score based on term matches
                # Score = (number of matching terms) / (total query terms)
                relevance_score = self._calculate_relevance_score(row.text, query, list(all_terms))
                
                formatted_result = {
                    'chunk_id': f"ch_{row.chunk_id:05d}",
                    'doc_id': f"doc_{row.doc_id:02X}",
                    'method': int(row.method),
                    'page_from': int(row.page_from) if row.page_from else None,
                    'page_to': int(row.page_to) if row.page_to else None,
                    'hash': str(row.hash),
                    'source': str(row.source),
                    'text': str(row.text),
                    'score': float(relevance_score),
                    'search_type': 'lexical'
                }
                formatted_results.append(formatted_result)
            
            # Sort by relevance score (highest first)
            formatted_results.sort(key=lambda x: x['score'], reverse=True)
            
            logger.info(f"SQLite LIKE search completed: {len(formatted_results)} results for query: {query[:50]}... (using {len(all_terms)} terms)")
            return formatted_results
            
        except Exception as e:
            logger.error(f"SQLite LIKE search failed: {str(e)}")
            return []
    
    def search_with_metadata(self, query: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Perform lexical search with additional metadata
        
        Args:
            query: Search query string
            limit: Maximum number of results
            
        Returns:
            Dictionary with results and metadata
        """
        try:
            results = self.search(query, limit)
            
            return {
                'results': results,
                'total_results': len(results),
                'search_type': 'lexical',
                'query': query,
                'limit': limit or self.topk_lex
            }
            
        except Exception as e:
            logger.error(f"Lexical search with metadata failed: {str(e)}")
            raise RuntimeError(f"Lexical search with metadata failed: {str(e)}")
    
    def _calculate_relevance_score(self, text: str, query: str, query_terms: Optional[List[str]] = None) -> float:
        """
        Calculate relevance score based on query term matches
        
        Args:
            text: Text content to score
            query: Search query (for fallback)
            query_terms: Optional list of query terms to match (preferred)
            
        Returns:
            Relevance score between 0.0 and 1.0
        """
        if not text:
            return 0.0
        
        text_lower = text.lower()
        
        # Use provided query_terms if available, otherwise extract from query
        if query_terms is None:
            if not query:
                return 0.0
            import re
            stopwords = {"what", "whats", "in", "the", "and", "of", "is", "section", "show", "go", "to"}
            query_lower = query.lower()
            query_terms = [t for t in re.findall(r"\w+", query_lower) if t not in stopwords and len(t) > 2]
        
        if not query_terms:
            return 0.0
        
        # Count how many query terms appear in the text
        match_count = sum(1 for term in query_terms if term in text_lower)
        relevance_score = min(1.0, match_count / len(query_terms))
        
        return relevance_score
