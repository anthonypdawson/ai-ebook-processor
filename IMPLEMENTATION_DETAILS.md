# Implementation Details and Technical Reference

This document contains detailed technical implementations, code examples, and architectural designs for the AI Ebook Processor RAG System features. 

**For the main roadmap and priorities, see [NEXT_FEATURES.md](NEXT_FEATURES.md)**

---

## Priority Features

### 🔥 High Priority

#### 1. Context Memory System 🆕
- **Graph-based Conversation Memory**: Query/response pairs as linked nodes with semantic relationships
- **Book-Specific Context Targeting**: Commands to focus conversations on specific books vs. entire library
- **Intelligent Query Suggestions**: Surface related past questions and suggest new ones based on context
- **Session-based Memory**: Remember conversation history within a session for natural follow-ups
- **Book-based Context**: Maintain context specific to each book for deeper exploration
- **Query Context Caching**: Cache retrieved chunks to avoid re-searching for follow-up questions
- **Conversation Threads**: Support branching conversations about different topics
- **Smart Context Pruning**: Manage memory efficiently by keeping relevant context and pruning old data
- **Timeline Visualization**: Visual representation of conversation flow and topic evolution

#### 2. Enhanced Search Strategies
- **Query Expansion**: Implement multiple query reformulation strategies
- **Semantic Clustering**: Group similar content chunks for better retrieval
- **Multi-modal Search**: Support for searching both content and metadata simultaneously
- **Search Result Ranking**: Implement custom scoring based on relevance and book metadata

#### 3. Advanced RAG Improvements
- **Hybrid Search**: Combine semantic search with keyword-based search (BM25)
- **Re-ranking**: Add a re-ranking step to improve result quality
- **Context Window Management**: Smart chunking that preserves sentence boundaries
- **Citation Tracking**: Better source attribution with page numbers and exact locations

#### 4. User Experience Enhancements
- **Interactive REPL Interface**: Command-line shell for seamless interaction without repeated CLI calls
- **Interactive Chat Interface**: Web-based chat UI for asking questions
- **Search History**: Track and revisit previous queries
- **Bookmark System**: Save important passages and insights
- **Export Functionality**: Export Q&A sessions to various formats

### 🚀 Medium Priority

#### 5. Performance Optimizations
- **Caching System**: Cache frequently accessed chunks and AI responses
- **Batch Processing**: Optimize bulk operations for large collections
- **Index Optimization**: Implement HNSW indexing for faster similarity search
- **Memory Management**: Optimize memory usage for large document collections

#### 6. Advanced AI Features
- **Multi-step Reasoning**: Break down complex queries into sub-questions
- **Cross-book Analysis**: Compare themes and concepts across multiple books
- **Summarization**: Generate book summaries and key insights automatically
- **Trend Analysis**: Identify patterns across reading history
- **Adaptive Persona System**: AI personality that evolves with user's interests and reading patterns

#### 7. Data Management
- **Incremental Updates**: Support for updating existing books without full reprocessing
- **Backup & Sync**: Cloud backup and synchronization capabilities
- **Import/Export**: Support for various ebook formats and metadata standards
- **Duplicate Detection**: Identify and handle duplicate books intelligently

### 💡 Low Priority / Future Ideas

#### 8. Integration Features
- **Goodreads Integration**: Import reading lists and ratings
- **Library Management**: Connect with library systems
- **Social Features**: Share insights and recommendations
- **Plugin System**: Allow custom processors and analyzers

#### 9. Analytics & Insights
- **Reading Analytics**: Track reading patterns and preferences
- **Knowledge Graphs**: Build connections between concepts across books
- **Learning Paths**: Suggest reading sequences based on interests
- **Progress Tracking**: Monitor comprehension and retention

#### 10. Advanced Processing
- **Multi-language Support**: Handle books in different languages
- **OCR Integration**: Process scanned PDFs and images
- **Audio Processing**: Support for audiobook transcripts
- **Real-time Processing**: Process books as they're being read

## Technical Improvements

### Architecture Enhancements
- [ ] Modular plugin system for different AI models
- [ ] API endpoints for external integrations
- [ ] Containerization with Docker
- [ ] Microservices architecture for scalability

### Code Quality
- [ ] Comprehensive unit test coverage
- [ ] Integration tests for end-to-end workflows
- [ ] Performance benchmarking suite
- [ ] Code documentation and API references

### Configuration & Deployment
- [ ] Configuration management system
- [ ] Environment-specific settings
- [ ] One-click deployment scripts
- [ ] Monitoring and logging improvements

## Recently Completed ✅

- **AI-Powered Search Term Generation**: Replaced hardcoded term mappings with intelligent AI-generated related search terms
- **Robust Fallback System**: Added fallback mechanisms for when AI generation fails
- **Flexible Domain Support**: Made the system work with any genre/type of book collection

## Ideas from Community

> Add community-suggested features here as they come up

## Implementation Notes

### Search Term Generation Enhancement (Completed)
- Replaced hardcoded apocalypse/zombie-themed terms with AI-powered generation
- Uses Ollama processor to generate contextually relevant search terms
- Includes fallback to keyword extraction when AI generation fails
- Supports any book genre/domain instead of being limited to specific themes

### Advanced Query Expansion Techniques

Beyond the basic AI-powered search term generation, several sophisticated expansion methods could further improve retrieval:

#### Multi-Query Expansion
```python
class MultiQueryExpander:
    def __init__(self, ollama_processor):
        self.ollama = ollama_processor
        
    def generate_query_variants(self, original_query, num_variants=3):
        """Generate multiple reformulations of the same query"""
        prompt = f"""Given this question: "{original_query}"

Generate {num_variants} alternative ways to phrase this same question that might find different relevant content:

1. Use different vocabulary/synonyms
2. Approach from different angles  
3. Be more specific or more general
4. Focus on different aspects

Return only the alternative questions, one per line."""

        response = self.ollama.client.chat(
            model=self.ollama.model_name,
            messages=[{'role': 'user', 'content': prompt}],
            options={'temperature': 0.7}
        )
        
        variants = [q.strip() for q in response['message']['content'].split('\n') if q.strip()]
        return [original_query] + variants[:num_variants-1]
    
    def search_with_variants(self, rag_system, query, context_chunks=5):
        """Search using multiple query variants and merge results"""
        variants = self.generate_query_variants(query)
        all_results = []
        
        for variant in variants:
            results = rag_system.search_books(variant, context_chunks)
            all_results.extend(results.get('results', []))
        
        # Deduplicate and score by frequency across variants
        return self._merge_and_score_results(all_results, context_chunks)
```

#### Morphological & Semantic Expansion
```python
import nltk
from nltk.corpus import wordnet

class SemanticExpander:
    def __init__(self):
        # Download required NLTK data
        nltk.download('wordnet', quiet=True)
        nltk.download('omw-1.4', quiet=True)
        
    def expand_query_terms(self, query):
        """Expand query with synonyms and morphological variations"""
        tokens = nltk.word_tokenize(query.lower())
        expanded_terms = set(tokens)
        
        for token in tokens:
            # Get synonyms from WordNet
            for syn in wordnet.synsets(token):
                for lemma in syn.lemmas():
                    synonym = lemma.name().replace('_', ' ')
                    if len(synonym) > 2:  # Filter short/meaningless terms
                        expanded_terms.add(synonym)
        
        return list(expanded_terms)
    
    def create_expanded_query(self, original_query, max_expansions=5):
        """Create search-optimized query with expansions"""
        expanded = self.expand_query_terms(original_query)
        # Use original query as primary + top expansions as secondary terms
        return {
            'primary': original_query,
            'expansions': expanded[:max_expansions]
        }
```

#### Pseudo-Relevance Feedback (PRF)
```python
from collections import Counter
import re

class PseudoRelevanceFeedback:
    def __init__(self):
        # Common stop words to filter out
        self.stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        
    def extract_key_terms(self, results, top_n=10):
        """Extract key terms from initial search results"""
        all_text = ' '.join([r['content'] for r in results])
        
        # Simple term extraction (could be enhanced with TF-IDF)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', all_text.lower())
        filtered_words = [w for w in words if w not in self.stop_words]
        
        # Get most frequent terms
        term_counts = Counter(filtered_words)
        return [term for term, count in term_counts.most_common(top_n)]
    
    def refine_search(self, rag_system, original_query, initial_results, context_chunks=5):
        """Use PRF to refine search with terms from initial results"""
        if not initial_results:
            return initial_results
            
        # Extract key terms from initial results
        feedback_terms = self.extract_key_terms(initial_results)
        
        # Create refined query incorporating feedback terms
        refined_queries = []
        for term in feedback_terms[:3]:  # Use top 3 feedback terms
            refined_query = f"{original_query} {term}"
            refined_queries.append(refined_query)
        
        # Search with refined queries
        refined_results = []
        for query in refined_queries:
            results = rag_system.search_books(query, context_chunks // len(refined_queries))
            refined_results.extend(results.get('results', []))
        
        # Merge with original results
        return self._combine_results(initial_results, refined_results, context_chunks)
```

#### Integrated Query Expansion Pipeline
```python
class AdvancedQueryProcessor:
    def __init__(self, rag_system, ollama_processor):
        self.rag = rag_system
        self.multi_query = MultiQueryExpander(ollama_processor)
        self.semantic = SemanticExpander()
        self.prf = PseudoRelevanceFeedback()
        
    def enhanced_search(self, query, context_chunks=5, use_prf=True):
        """Multi-stage query expansion and search"""
        
        # Stage 1: Multi-query expansion
        query_variants = self.multi_query.generate_query_variants(query)
        
        # Stage 2: Semantic expansion for each variant
        expanded_variants = []
        for variant in query_variants:
            semantic_expansion = self.semantic.create_expanded_query(variant)
            expanded_variants.append(semantic_expansion)
        
        # Stage 3: Initial search with expanded queries
        initial_results = []
        for expansion in expanded_variants:
            # Search with primary query
            primary_results = self.rag.search_books(expansion['primary'], context_chunks // 2)
            initial_results.extend(primary_results.get('results', []))
            
            # Search with expansion terms
            for exp_term in expansion['expansions']:
                exp_results = self.rag.search_books(exp_term, 1)  # Fewer results per expansion
                initial_results.extend(exp_results.get('results', []))
        
        # Stage 4: Pseudo-relevance feedback (optional)
        if use_prf and initial_results:
            final_results = self.prf.refine_search(self.rag, query, initial_results, context_chunks)
        else:
            final_results = initial_results
        
        # Deduplicate and rank
        return self._deduplicate_and_rank(final_results, context_chunks)
```

**Benefits of Advanced Query Expansion:**
- **Multi-Query**: Better coverage by rephrasing questions multiple ways
- **Semantic Expansion**: Catch synonyms and morphologically related terms  
- **PRF**: Learn from good initial results to find more relevant content
- **Combined Pipeline**: Systematic application of all techniques for maximum recall

### Next Up: Context Memory System
The context memory system would be the next major enhancement, offering:

#### Implementation Approaches:

**1. Session-Based Memory**
```python
class SessionMemory:
    def __init__(self, redis_client=None):
        self.conversation_history = []
        self.cached_contexts = {}
        self.current_topics = set()
        self.redis = redis_client  # Optional Redis backend
    
    def add_query_response(self, query, response, context_chunks):
        # Store the Q&A with retrieved context
        
    def get_relevant_history(self, new_query):
        # Find related previous queries for context
```

**2. Graph-Based Conversation Nodes**
```python
class ConversationNode:
    def __init__(self, node_id, query, response, timestamp):
        self.node_id = node_id
        self.query = query
        self.response = response
        self.timestamp = timestamp
        self.embedding_vector = None  # Query embedding for similarity
        self.source_chunks = []       # Referenced text chunks
        self.parent_nodes = []        # Previous related queries
        self.child_nodes = []         # Follow-up queries
        self.topic_tags = set()       # Extracted topics/themes
        
class ConversationGraph:
    def __init__(self, redis_client=None):
        self.nodes = {}  # node_id -> ConversationNode
        self.redis = redis_client
        
    def add_conversation_node(self, query, response, context_chunks, parent_id=None):
        # Create new node and establish relationships
        node = ConversationNode(
            node_id=self._generate_id(),
            query=query,
            response=response, 
            timestamp=time.time()
        )
        
        # Generate embedding for semantic similarity
        node.embedding_vector = self._get_query_embedding(query)
        node.source_chunks = context_chunks
        node.topic_tags = self._extract_topics(query, response)
        
        # Link to related nodes
        if parent_id and parent_id in self.nodes:
            self._link_nodes(parent_id, node.node_id)
            
        # Find semantically similar nodes
        similar_nodes = self._find_similar_nodes(node.embedding_vector)
        for similar_id, similarity in similar_nodes:
            if similarity > 0.8:  # High similarity threshold
                self._add_semantic_link(similar_id, node.node_id)
                
        self.nodes[node.node_id] = node
        return node.node_id
    
    def get_conversation_context(self, current_query, max_nodes=5):
        # Find most relevant nodes based on:
        # 1. Semantic similarity
        # 2. Recent temporal proximity  
        # 3. Topic overlap
        # 4. Graph connectivity
        pass
        
    def visualize_conversation_graph(self):
        # Generate graph visualization of conversation flow
        pass
```

**3. Book-Based Context**
```python
class BookContext:
    def __init__(self, book_id, redis_client=None):
        self.book_id = book_id
        self.query_history = []
        self.frequently_accessed_chunks = {}
        self.user_interests = set()  # Topics user asks about
        self.redis = redis_client

class BookTargetingSystem:
    def __init__(self, rag_system, context_manager):
        self.rag = rag_system
        self.context = context_manager
        
    def enter_book_mode(self, book_title_or_id):
        """Switch to book-specific conversation mode"""
        book_context = self._load_book_context(book_title_or_id)
        recent_queries = self._get_recent_book_queries(book_title_or_id, limit=10)
        
        # Preload relevant context
        self._preload_book_context(book_context, recent_queries)
        
        # Generate suggestions based on past conversations
        suggestions = self._generate_query_suggestions(book_context, recent_queries)
        
        return {
            'book_info': book_context.metadata,
            'recent_queries': recent_queries,
            'suggested_questions': suggestions,
            'conversation_threads': self._get_active_threads(book_title_or_id)
        }
    
    def suggest_related_questions(self, current_query, book_id, limit=5):
        """Find semantically similar past questions and suggest new ones"""
        # Find similar past queries
        query_embedding = self._get_query_embedding(current_query)
        similar_queries = self._find_similar_book_queries(book_id, query_embedding, limit=3)
        
        # Generate new question suggestions using AI
        ai_suggestions = self._generate_ai_suggestions(current_query, book_id, limit=2)
        
        return {
            'similar_past_queries': similar_queries,
            'ai_generated_suggestions': ai_suggestions
        }
    
    def _generate_ai_suggestions(self, current_query, book_id, limit=3):
        """Use AI to suggest related follow-up questions"""
        book_context = self._get_book_summary(book_id)
        recent_topics = self._get_recent_topics(book_id)
        
        prompt = f"""Based on this question about "{book_context['title']}": "{current_query}"

Book context: {book_context['summary']}
Recent discussion topics: {', '.join(recent_topics)}

Suggest {limit} related follow-up questions that would deepen understanding of the book. Focus on:
- Different aspects of the same topic
- Connections to other themes or characters  
- Deeper analysis or interpretation
- Comparisons within the book

Return only the questions, one per line."""
        
        # Call AI to generate suggestions
        return self._call_ai_for_suggestions(prompt)
```

**4. Smart Query Preloading & Suggestions**
```python
class IntelligentSuggestionEngine:
    def __init__(self, conversation_graph, redis_client):
        self.graph = conversation_graph
        self.redis = redis_client
        
    def preload_book_return(self, book_id, user_session):
        """When user returns to a book, preload relevant context"""
        # Get user's query history for this book
        book_queries = self._get_user_book_queries(book_id, user_session)
        
        # Calculate recency and frequency weights
        weighted_queries = self._calculate_query_relevance(book_queries)
        
        # Preload top chunks that were frequently accessed
        top_chunks = self._get_frequently_referenced_chunks(book_id, weighted_queries)
        self._preload_chunks_to_cache(top_chunks)
        
        return {
            'preloaded_context': len(top_chunks),
            'recent_topics': self._extract_recent_topics(weighted_queries),
            'suggested_continuations': self._suggest_conversation_continuations(weighted_queries)
        }
    
    def generate_contextual_suggestions(self, current_query, book_id, conversation_history):
        """Generate smart suggestions based on conversation context"""
        
        # Analyze conversation patterns
        patterns = self._analyze_conversation_patterns(conversation_history)
        
        # Find unexplored aspects of current topic
        unexplored = self._find_unexplored_aspects(current_query, book_id, patterns)
        
        # Suggest connections to other parts of the book
        connections = self._suggest_thematic_connections(current_query, book_id)
        
        return {
            'continue_current_thread': unexplored,
            'explore_connections': connections,
            'return_to_previous': self._suggest_thread_returns(conversation_history)
        }
```

**4. Redis Graph Storage**
```python
class RedisGraphContextManager:
    def __init__(self, redis_host='localhost', redis_port=6379):
        import redis
        self.redis = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        
    def store_conversation_node(self, node, ttl=86400):  # 24 hour default
        # Store node data
        node_key = f"conversation:node:{node.node_id}"
        node_data = {
            'query': node.query,
            'response': node.response,
            'timestamp': node.timestamp,
            'embedding': json.dumps(node.embedding_vector.tolist()),
            'source_chunks': json.dumps(node.source_chunks),
            'topics': json.dumps(list(node.topic_tags))
        }
        self.redis.hset(node_key, mapping=node_data)
        self.redis.expire(node_key, ttl)
        
        # Store graph relationships
        for parent_id in node.parent_nodes:
            self.redis.sadd(f"conversation:children:{parent_id}", node.node_id)
            self.redis.sadd(f"conversation:parents:{node.node_id}", parent_id)
            
        # Store semantic similarity links
        for similar_id in node.semantic_links:
            self.redis.zadd(f"conversation:similar:{node.node_id}", {similar_id: similarity_score})
    
    def find_context_path(self, start_node, end_node):
        # Find path through conversation graph using graph traversal
        return self._bfs_path_finding(start_node, end_node)
        
    def get_topic_timeline(self, topic, limit=10):
        # Get chronological progression of a topic through conversations
        topic_nodes = self.redis.smembers(f"conversation:topic:{topic}")
        # Sort by timestamp and return evolution
        pass
```
```python
class RedisContextManager:
    def __init__(self, redis_host='localhost', redis_port=6379):
        import redis
        self.redis = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        
    def store_session_context(self, session_id, query, response, chunks, ttl=3600):
        # Store with automatic expiration
        key = f"session:{session_id}:context"
        context_data = {
            'query': query,
            'response': response,
            'chunks': json.dumps(chunks),
            'timestamp': time.time()
        }
        self.redis.hset(key, mapping=context_data)
        self.redis.expire(key, ttl)  # Auto-expire after 1 hour
    
    def get_session_history(self, session_id, limit=10):
        # Retrieve recent conversation history
        pattern = f"session:{session_id}:*"
        keys = self.redis.keys(pattern)
        return [self.redis.hgetall(key) for key in keys[-limit:]]
    
    def cache_search_results(self, query_hash, results, ttl=300):
        # Cache search results to avoid re-querying
        key = f"search_cache:{query_hash}"
        self.redis.setex(key, ttl, json.dumps(results))
    
    def get_cached_results(self, query_hash):
        key = f"search_cache:{query_hash}"
        cached = self.redis.get(key)
        return json.loads(cached) if cached else None
    
    def track_book_interests(self, book_id, topics):
        # Track user interests per book
        key = f"book:{book_id}:interests"
        self.redis.sadd(key, *topics)
        self.redis.expire(key, 86400 * 30)  # Keep for 30 days
```

**Book-Specific Command Examples:**

**Entering Book Mode**
```bash
# Focus on specific book
> focus "The Great Gatsby"
Entering book mode for "The Great Gatsby" by F. Scott Fitzgerald
Recent topics: symbolism, character development, American Dream
Suggested questions:
- "How does the green light symbolism evolve throughout the story?"
- "What aspects of Tom's character haven't we explored?"
- "How does Nick's perspective change from our last discussion?"

# Quick book switch
> switch "1984" 
Switched to "1984" - preloading your previous discussions about surveillance and freedom

# Return to library mode  
> library
Now searching across your entire collection
```

**Smart Suggestion Interface**
```bash
> ask "What motivates Gatsby's actions?"
[Response about Gatsby's motivations]

Related questions you might explore:
✓ Similar past query: "Why does Gatsby throw parties?" (asked 3 days ago)
🔮 AI suggestions: 
  - "How do Gatsby's motivations compare to Tom's?"
  - "What childhood experiences shaped Gatsby's desires?"
  - "How does Daisy represent Gatsby's deeper motivations?"
  
> explore 2  # Ask the second AI suggestion
> related 1  # Return to the similar past query
```

**Context Preloading Benefits**
```python
# When user returns to a book:
user_returns_to_book("The Great Gatsby") 
→ Preloads: 15 frequently accessed chunks about symbolism, characters
→ Surfaces: 3 unfinished conversation threads  
→ Suggests: 5 new questions based on past interests
→ Response time: 200ms faster due to preloaded context
```

**Advanced Graph Features:**

**Topic Evolution Tracking**
- Track how understanding of themes develops over time
- "Show me how my understanding of character X has evolved"
- Visual timeline of topic progression

**Conversation Branching** 
- Support multiple conversation threads from a single point
- "Let's explore that character's motivation instead"
- Maintain context for different exploration paths

**Semantic Clustering**
- Group related queries even across different sessions
- "Find all conversations about similar themes"
- Discover conversation patterns and recurring interests

**Citation Networks**
- Link queries that reference the same text chunks
- "What other questions were asked about this passage?"
- Build knowledge maps of book content exploration

**Context Inference**
- Use graph relationships to infer context for ambiguous queries
- "Tell me more about that" → analyze connected nodes to understand "that"
- Smart context resolution based on conversation flow

**Benefits:**
**Implementation Benefits:**
- **Book-focused conversations**: "focus 'Dune'" → all queries target that specific book
- **Smart suggestions**: Return to a book → see related past questions and AI-generated follow-ups  
- **Context preloading**: Faster responses by preloading frequently accessed chunks
- **Conversation continuations**: "Continue where we left off discussing Paul's prescience"
- **Cross-book insights**: "Compare this theme to what we discussed in Foundation"
- **Personalized exploration**: System learns your interests and suggests deeper questions
- **Thread management**: Track multiple conversation threads per book
- **Graph advantages**: Rich context relationships, conversation branching, topic evolution tracking
- **Redis advantages**: Lightning-fast graph traversal, automatic expiration, clustering support

**Book Targeting System Benefits:**
- **Focused context**: Avoid information overload from entire library
- **Personalized suggestions**: Based on your specific reading patterns and interests  
- **Efficient exploration**: Guided discovery of unexplored aspects
- **Conversation memory**: Pick up discussions exactly where you left off
- **Performance optimization**: Preloaded context for instant responses
- **Pattern recognition**: System learns your questioning style and preferences

**Graph Data Structure Benefits:**
- **Non-linear conversations**: Support branching and merging discussion threads
- **Semantic relationships**: Connect related queries across time and sessions
- **Source traceability**: Direct links from queries to specific text chunks
- **Pattern discovery**: Identify recurring themes and question patterns
- **Context resolution**: Use graph structure to resolve ambiguous references
- **Timeline analysis**: Track how understanding evolves over time

**Storage Options:**

**Option 1: Redis (Recommended)**
- **Pros**: Ultra-fast access, built-in TTL, rich data structures, clustering support
- **Cons**: Requires Redis server, memory-based (data lost on restart unless persisted)
- **Use cases**: Production deployments, high-frequency usage, multi-user scenarios
- **Setup**: `pip install redis` + Redis server installation

**Option 2: In-Memory (Current)**  
- **Pros**: No external dependencies, simple setup
- **Cons**: Lost on restart, no persistence, limited scalability
- **Use cases**: Development, single-user, simple scenarios

**Option 3: SQLite Hybrid**
- **Pros**: Persistent, no server required, good for single-user
- **Cons**: Slower than Redis, limited concurrent access
- **Use cases**: Desktop applications, offline usage

**Memory Management:**
- **Redis TTL**: Automatic expiration (sessions: 1 hour, search cache: 5 minutes, interests: 30 days)
- **LRU eviction**: Redis handles memory pressure automatically
- **Configurable retention**: Different TTL policies for different data types
- **Persistence options**: Redis RDB/AOF for durability if needed
- **Clustering**: Scale horizontally with Redis Cluster for large deployments

### Also Priority: Enhanced Search Strategies
In parallel with context memory, implementing hybrid search:
1. Current semantic search (ChromaDB)
2. Keyword-based search (BM25) 
3. Metadata filtering
4. Custom relevance scoring


### Interactive REPL Interface Implementation

A command-line REPL would eliminate the need to repeatedly type `python cli.py` and create a more natural interactive experience:

```python
# repl.py
import cmd
import sys
from pathlib import Path
from main import EbookProcessorApp
from rag_system import EnhancedEbookProcessor

class EbookREPL(cmd.Cmd):
    """Interactive REPL for the Ebook Processor"""
    
    intro = '''
╔══════════════════════════════════════════════════════════════╗
║                    AI Ebook Processor REPL                  ║
║              Your Intelligent Reading Companion             ║
╠══════════════════════════════════════════════════════════════╣
║ Commands:                                                    ║
║   process <file>     - Process an ebook file                ║
║   ask <question>     - Ask about your collection            ║
║   focus <book>       - Enter book-specific mode             ║
║   library           - Return to library-wide mode           ║
║   stats             - Show collection statistics            ║
║   help              - Show detailed command help            ║
║   quit/exit         - Exit the REPL                         ║
╚══════════════════════════════════════════════════════════════╝
Type 'help' for more information.
'''
    
    prompt = '📚 > '
    
    def __init__(self):
        super().__init__()
        self.processor = None
        self.current_book = None
        self.session_history = []
        self._initialize_system()
    
    def _initialize_system(self):
        """Initialize the ebook processor system"""
        try:
            print("🔧 Initializing AI Ebook Processor...")
            self.processor = EnhancedEbookProcessor()
            print("✅ System ready!")
        except Exception as e:
            print(f"❌ Error initializing system: {e}")
            sys.exit(1)
    
    def do_process(self, arg):
        """Process an ebook file
        Usage: process <file_path>
        Example: process "books/great_gatsby.epub"
        """
        if not arg.strip():
            print("❌ Please provide a file path")
            return
        
        file_path = arg.strip().strip('"').strip("'")
        if not Path(file_path).exists():
            print(f"❌ File not found: {file_path}")
            return
            
        print(f"📖 Processing {file_path}...")
        try:
            result = self.processor.process_and_store(file_path)
            if 'error' in result:
                print(f"❌ Error: {result['error']}")
            else:
                title = result.get('metadata', {}).get('title', 'Unknown')
                print(f"✅ Successfully processed: {title}")
                print(f"📊 Added {len(result.get('combined_result', '').split())} words to your collection")
        except Exception as e:
            print(f"❌ Processing error: {e}")
    
    def do_ask(self, arg):
        """Ask a question about your book collection
        Usage: ask <your_question>
        Example: ask What are the main themes in my books?
        """
        if not arg.strip():
            print("❌ Please ask a question")
            return
            
        question = arg.strip()
        
        # Show context if in book mode
        context_msg = f" [📖 {self.current_book}]" if self.current_book else " [📚 Library]"
        print(f"🤔 Thinking{context_msg}...")
        
        try:
            answer = self.processor.ask_about_collection(question)
            print(f"\n💡 {answer}\n")
            
            # Store in session history
            self.session_history.append({
                'question': question,
                'answer': answer,
                'context': self.current_book or 'library',
                'timestamp': self._get_timestamp()
            })
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def do_focus(self, arg):
        """Focus on a specific book for targeted conversations
        Usage: focus <book_title>
        Example: focus "The Great Gatsby"
        """
        if not arg.strip():
            print("❌ Please specify a book title")
            return
            
        book_title = arg.strip().strip('"').strip("'")
        # TODO: Implement book targeting system
        self.current_book = book_title
        self.prompt = f'📖 [{book_title}] > '
        print(f"🎯 Focused on: {book_title}")
        print("💡 All questions will now target this specific book")
        print("💡 Type 'library' to return to collection-wide mode")
    
    def do_library(self, arg):
        """Return to library-wide mode (search across all books)"""
        self.current_book = None
        self.prompt = '📚 > '
        print("📚 Switched to library-wide mode")
        print("💡 Questions will now search across your entire collection")
    
    def do_stats(self, arg):
        """Show collection and session statistics"""
        try:
            # Get RAG system stats
            if hasattr(self.processor, 'rag_system') and self.processor.rag_system:
                rag_stats = self.processor.rag_system.get_collection_stats()
                print(f"📊 Collection Statistics:")
                print(f"   📚 Total chunks: {rag_stats.get('total_chunks', 0)}")
                print(f"   💾 Database: {rag_stats.get('database_path', 'N/A')}")
            
            # Session stats
            print(f"🔄 Session Statistics:")
            print(f"   ❓ Questions asked: {len(self.session_history)}")
            if self.current_book:
                book_questions = [h for h in self.session_history if h['context'] == self.current_book]
                print(f"   📖 Questions about {self.current_book}: {len(book_questions)}")
                
        except Exception as e:
            print(f"❌ Error getting stats: {e}")
    
    def do_history(self, arg):
        """Show session history
        Usage: history [n]  - Show last n questions (default: 5)
        """
        try:
            limit = int(arg.strip()) if arg.strip().isdigit() else 5
            recent = self.session_history[-limit:]
            
            if not recent:
                print("📝 No questions asked yet this session")
                return
                
            print(f"📝 Last {len(recent)} questions:")
            for i, entry in enumerate(recent, 1):
                context = f"[{entry['context']}]" if entry['context'] != 'library' else '[Library]'
                print(f"   {i}. {context} {entry['question']}")
                
        except Exception as e:
            print(f"❌ Error showing history: {e}")
    
    def do_clear(self, arg):
        """Clear the screen"""
        import os
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def do_quit(self, arg):
        """Exit the REPL"""
        print("👋 Goodbye! Happy reading!")
        return True
    
    def do_exit(self, arg):
        """Exit the REPL"""
        return self.do_quit(arg)
    
    def do_EOF(self, arg):
        """Handle Ctrl+D (EOF)"""
        print("\n👋 Goodbye!")
        return True
    
    def emptyline(self):
        """Don't repeat last command on empty line"""
        pass
    
    def _get_timestamp(self):
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def cmdloop(self, intro=None):
        """Override to handle keyboard interrupts gracefully"""
        try:
            super().cmdloop(intro)
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            return


if __name__ == '__main__':
    EbookREPL().cmdloop()
```

**Usage Examples:**

```bash
# Start the REPL
$ python repl.py

📚 > process "books/dune.epub"
📖 Processing books/dune.epub...
✅ Successfully processed: Dune
📊 Added 187,000 words to your collection

📚 > ask What are the main themes in Dune?
🤔 Thinking [📚 Library]...
💡 The main themes in Dune include power and politics, ecology and environmental stewardship...

📚 > focus "Dune"
🎯 Focused on: Dune
💡 All questions will now target this specific book

📖 [Dune] > ask Tell me more about Paul's prescience
🤔 Thinking [📖 Dune]...
💡 Paul Atreides' prescient abilities are central to the narrative...

📖 [Dune] > library
📚 Switched to library-wide mode

📚 > stats
📊 Collection Statistics:
   📚 Total chunks: 1,247
   💾 Database: ebook_db
🔄 Session Statistics:
   ❓ Questions asked: 3

📚 > quit
👋 Goodbye! Happy reading!
```

**REPL Benefits:**
- **Persistent session**: No need to restart Python/load models repeatedly
- **Natural workflow**: Ask questions, switch book focus, check stats seamlessly  
- **Command history**: Built-in readline support for command history and editing
- **Visual feedback**: Emoji indicators and clear status messages
- **Error handling**: Graceful error messages without crashing
- **Session memory**: Track questions asked during the session

### Future: Adaptive Persona System 🆕
An innovative feature where the AI's communication style and focus areas subtly evolve based on the user's interests and conversation patterns. This would create a truly dynamic reading companion that grows alongside the user's literary sophistication.

**Key Concept**: Track user evolution over time and gradually adapt AI personality traits like formality level, analytical depth, enthusiasm, and literary focus areas.

Both the enhanced search strategies and context memory system would significantly improve search quality and user experience.

### Adaptive Persona System Implementation

The adaptive persona system would track user evolution and gradually adjust AI personality:

```python
class AdaptivePersona:
    def __init__(self, user_id, conversation_graph):
        self.user_id = user_id
        self.graph = conversation_graph
        self.base_persona = "knowledgeable reading companion"
        self.current_traits = {
            'formality_level': 0.5,      # 0=casual, 1=formal
            'analytical_depth': 0.5,      # 0=surface, 1=deep analysis
            'enthusiasm_level': 0.5,      # 0=reserved, 1=enthusiastic
            'question_style': 'balanced', # exploratory, focused, comparative
            'literary_focus': 'general'   # literary, philosophical, historical, etc.
        }
        
    def analyze_user_evolution(self, recent_conversations, time_window_days=30):
        """Analyze how user's interests and preferences are evolving"""
        
        # Track interest evolution
        topic_progression = self._analyze_topic_progression(recent_conversations)
        question_complexity = self._measure_question_sophistication(recent_conversations)
        engagement_patterns = self._analyze_engagement_levels(recent_conversations)
        
        # Detect shifts in reading focus
        focus_shifts = self._detect_focus_changes(topic_progression, time_window_days)
        
        return {
            'topic_evolution': topic_progression,
            'complexity_trend': question_complexity,
            'engagement_evolution': engagement_patterns,
            'detected_shifts': focus_shifts
        }
    
    def generate_contextual_system_prompt(self, current_book=None):
        """Generate AI system prompt that reflects current persona"""
        
        base_prompt = "You are a knowledgeable reading companion helping someone explore their book collection."
        
        # Adjust tone based on formality and enthusiasm
        if self.current_traits['enthusiasm_level'] > 0.7:
            tone_modifier = " You're genuinely excited about literature and love diving deep into themes and characters."
        elif self.current_traits['formality_level'] > 0.7:
            tone_modifier = " You maintain a scholarly, analytical approach to literary discussion."
        else:
            tone_modifier = " You're friendly and approachable, adapting to the user's interests."
        
        return base_prompt + tone_modifier
```

**Persona Evolution Examples:**

**Early Stage**: "That's an interesting question about Gatsby. The green light symbolizes his yearning for the American Dream..."

**After Deep Analysis Interest**: "Excellent point! The green light's symbolism operates on multiple layers - notice how Fitzgerald positions it geometrically in relation to the bay, creating a physical manifestation of the metaphysical distance between desire and reality..."

**After Historical Focus Emerges**: "The green light takes on additional resonance when you consider the post-WWI context. Fitzgerald was writing during a period when American optimism was being questioned..."

## Contributing

When implementing new features:
1. Update this document with progress
2. Add tests for new functionality
3. Update documentation
4. Consider backwards compatibility
5. Add configuration options where appropriate

## Notes

- Features marked with 🔥 should be prioritized for next development cycle
- Consider user feedback when re-prioritizing features
- Balance new features with performance and stability improvements
- Keep the system modular to allow optional feature adoption