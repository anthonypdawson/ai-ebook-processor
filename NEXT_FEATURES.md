# Next Features and Improvements

This document tracks planned features, enhancements, and improvements for the AI Ebook Processor RAG System.

**For detailed technical implementations and code examples, see [IMPLEMENTATION_DETAILS.md](IMPLEMENTATION_DETAILS.md)**

---

## Priority Features

### 🔥 High Priority

#### 1. Context Memory System 🆕
- **Graph-based Conversation Memory**: Query/response pairs as linked nodes with semantic relationships
- **Book-Specific Context Targeting**: Commands to focus conversations on specific books vs. entire library
- **Intelligent Query Suggestions**: Surface related past questions and suggest new ones based on context
- **Session-based Memory**: Remember conversation history within a session for natural follow-ups
- **Query Context Caching**: Cache retrieved chunks to avoid re-searching for follow-up questions
- **Redis Integration**: Fast, persistent storage with automatic expiration policies

#### 2. Interactive REPL Interface
- **Command-line Shell**: Seamless interaction without repeated CLI calls
- **Auto-discovery**: Scan directories for ebooks, show available books without processing
- **Book Management**: List, browse, and select books from your collection
- **Book Targeting Commands**: `focus "book"`, `library`, `switch "book"`
- **Session Management**: Persistent state, command history, graceful error handling
- **Visual Feedback**: Clear prompts, emoji indicators, progress messages

#### 3. Enhanced Search Strategies
- **Hybrid Search**: Combine semantic search with keyword-based search (BM25)
- **Query Expansion**: AI-generated related search terms (✅ completed)
- **Re-ranking**: Improve result quality with custom scoring
- **Semantic Clustering**: Group similar content chunks for better retrieval

### 🚀 Medium Priority

#### 4. Advanced RAG Improvements
- **Context Window Management**: Smart chunking that preserves sentence boundaries
- **Citation Tracking**: Better source attribution with page numbers and locations
- **Multi-modal Search**: Search both content and metadata simultaneously

#### 5. Performance Optimizations
- **Caching System**: Cache frequently accessed chunks and AI responses
- **Index Optimization**: HNSW indexing for faster similarity search
- **Batch Processing**: Optimize bulk operations for large collections

#### 6. Advanced AI Features
- **Multi-step Reasoning**: Break down complex queries into sub-questions
- **Cross-book Analysis**: Compare themes and concepts across multiple books
- **Adaptive Persona System**: AI personality that evolves with user's interests

### 💡 Future Ideas

#### 7. User Experience Enhancements
- **Web Chat Interface**: Browser-based UI for asking questions
- **Bookmark System**: Save important passages and insights
- **Export Functionality**: Export Q&A sessions to various formats

#### 8. Integration & Analytics
- **Goodreads Integration**: Import reading lists and ratings
- **Reading Analytics**: Track patterns and preferences
- **Knowledge Graphs**: Build connections between concepts across books

## Recently Completed ✅

- **AI-Powered Search Term Generation**: Replaced hardcoded term mappings with intelligent AI-generated related search terms
- **Robust Fallback System**: Added fallback mechanisms for when AI generation fails
- **Flexible Domain Support**: Made the system work with any genre/type of book collection

## Implementation Priority

### Next Up: Book Discovery + REPL
The most impactful next implementation would combine:
1. **Auto-discovery**: Scan directories for ebooks, build searchable catalog
2. **REPL Interface**: Interactive shell with book browsing and selection
3. **Lazy Processing**: Only process books when user requests them
4. **Basic Book Targeting**: `focus "book"` command functionality

This provides immediate value for large collections and sets foundation for advanced features.

### Future: Advanced Context Memory
Later phases would add:
- Graph-based conversation nodes
- Redis storage for persistence
- Intelligent query suggestions
- Adaptive persona system

## Technical Architecture

### Storage Options
- **Redis** (recommended): Fast, TTL support, clustering capability
- **SQLite**: Persistent, single-user, no server required
- **In-memory**: Simple development, session-only

### Integration Points
- Builds on existing `EbookRAGSystem` class
- Extends current `ask_question` method
- Maintains backward compatibility

## Contributing

When implementing new features:
1. Start with REPL + basic book targeting for immediate impact
2. Add comprehensive tests for new functionality
3. Update this document with progress
4. Keep the system modular for optional feature adoption

## Notes

- Focus on user experience improvements first (REPL, book targeting)
- Balance new features with performance and stability
- Consider user feedback when re-prioritizing features
- Maintain clear separation between core features and advanced enhancements