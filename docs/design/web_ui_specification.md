# Web UI Design Document

Status: Design Phase
Last Updated: 2025-09-21
Target: Path-based Local Ebook Processing Interface

## 1. Vision Statement

Create a modern, intuitive web interface that allows users to process and search their local ebook collections without file uploads. The interface should feel like a personal digital librarian—intelligent, organized, and respectful of existing file organization.

## 2. Core Principles

### User Experience
- **No file uploads**: Users work with existing file paths and folder structures
- **Progressive enhancement**: Works without JavaScript for basic functions
- **Responsive design**: Adapts to desktop, tablet, and mobile screens  
- **Familiar patterns**: Uses established web UI conventions
- **Performance first**: Fast loading, minimal resource usage

### Technical Philosophy
- **Leverage existing pipeline**: Web layer wraps current Python processing
- **Stateless where possible**: Minimize server-side session management
- **API-first design**: Clear separation between frontend and backend
- **Security by design**: Path validation and access control built-in
- **Extensible architecture**: Easy to add new features later

## 3. User Personas & Use Cases

### Primary Persona: The Digital Scholar
**Profile**: Has 100-5000 ebooks, researches themes/topics across multiple books, values organized file structure, comfortable with file paths.

**Key Workflows**:
1. Add new book → Process → Search across collection
2. Bulk process a folder of books → Organize into collections
3. Research session → Multiple complex queries → Export findings
4. Library maintenance → Review processed books → Remove duplicates

### Secondary Persona: The Casual Reader
**Profile**: 20-200 ebooks, occasional searches, prefers visual browsing, wants simple interface.

**Key Workflows**:
1. Point-and-click book addition
2. Simple search queries
3. Browse processed library visually

## 4. Information Architecture

### Primary Navigation
```
┌─────────────────────────────────────────────────────┐
│ [📚 EbookRAG]  Library | Process | Search | Settings │
└─────────────────────────────────────────────────────┘
```

### Page Structure

#### 4.1 Library Page (Default Landing)
**Purpose**: Overview of all processed books, quick access to common actions

**Layout**:
```
┌─── Library Overview ─────────────────────────────────┐
│                                                     │
│ 📊 Stats: 47 books, 12,450 chunks, 3.2M tokens     │
│                                                     │
│ 🔍 Quick Search: [                    ] [Search]   │
│                                                     │
│ ┌─── Recently Added ──────────────────────────────┐ │
│ │ 📖 Dracula (Oct 12) - 342 chunks               │ │
│ │ 📖 Pride & Prejudice (Oct 10) - 287 chunks     │ │
│ │ 📖 Moby Dick (Oct 8) - 523 chunks              │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ ┌─── All Books (Grid/List Toggle) ─────────────────┐ │
│ │ [Grid View] [List View] [Sort: Title ▼]        │ │
│ │                                                 │ │
│ │ Grid: Book covers + titles + status             │ │
│ │ List: Detailed table with paths, dates, stats  │ │
│ └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

#### 4.2 Process Page  
**Purpose**: Add new books, monitor processing status, batch operations

**Layout**:
```
┌─── Add Books ────────────────────────────────────────┐
│                                                     │
│ Single File:                                        │
│ [/path/to/book.epub                    ] [Browse]   │
│ [Process Book]                                      │
│                                                     │
│ Batch Process:                                      │
│ [/path/to/books/folder                 ] [Browse]   │
│ ☑️ Include subdirectories                           │
│ ☑️ Skip already processed                           │
│ [Process Folder]                                    │
│                                                     │
│ ┌─── Processing Queue ──────────────────────────────┐ │
│ │ ⏳ Dracula.epub - Processing chunks (45%)        │ │
│ │ ✅ 1984.epub - Complete (234 chunks)             │ │
│ │ 🔄 War and Peace.epub - Queued                   │ │
│ └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

#### 4.3 Search Page
**Purpose**: Advanced search interface, results exploration, query history

**Layout**:
```
┌─── Search Interface ─────────────────────────────────┐
│                                                     │
│ Query: [themes of isolation in 19th century lit]   │
│ [🔍 Search] [🎯 Advanced] [📋 History]              │
│                                                     │
│ Filters: [All Books ▼] [All Sections ▼] [Date ▼]   │
│                                                     │
│ ┌─── Results (23 found) ─────────────────────────────┐ │
│ │ 📖 Frankenstein - Chapter 14                     │ │
│ │ "The desert mountains and dreary glaciers are my │ │
│ │ refuge. I have wandered here many days..."       │ │
│ │ [📄 Full Context] [🔗 Open Book] Score: 0.94     │ │
│ │                                                 │ │
│ │ 📖 Wuthering Heights - Chapter 3                 │ │
│ │ "I never saw a more beautiful country! It was   │ │
│ │ completely removed from the stir of society..." │ │
│ │ [📄 Full Context] [🔗 Open Book] Score: 0.89     │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ [📤 Export Results] [💾 Save Query] [🔄 New Search] │
└─────────────────────────────────────────────────────┘
```

#### 4.4 Settings Page
**Purpose**: Configuration, model selection, system maintenance

**Layout**:
```
┌─── Settings ─────────────────────────────────────────┐
│                                                     │
│ ├─ Processing                                       │
│ │  Model: [llama2 ▼] [Test Connection]             │
│ │  Chunk size: [800] tokens                        │
│ │  Overlap: [80] tokens                            │
│ │  Auto-process: ☑️ On                             │
│ │                                                 │
│ ├─ Paths                                           │
│ │  Default browse: [~/Books] [Browse]              │
│ │  Output directory: [./output] [Browse]           │
│ │  Allowed extensions: epub, pdf, txt              │
│ │                                                 │
│ ├─ Search                                          │
│ │  Results per page: [20]                         │
│ │  Context window: [3] chunks                     │
│ │  Minimum score: [0.5]                           │
│ │                                                 │
│ ├─ Interface                                       │
│ │  Theme: [Light ▼]                               │
│ │  Show file paths: ☑️ On                         │
│ │  Auto-refresh: ☑️ On                            │
│ │                                                 │
│ └─ Maintenance                                     │
│    Database size: 2.3 GB                          │
│    [🗑️ Clear Cache] [📊 Rebuild Index] [⬇️ Backup] │
└─────────────────────────────────────────────────────┘
```

## 5. Component Specifications

### 5.1 File Browser Component
**Requirements**:
- Navigate local filesystem (within security constraints)
- Filter by file type (.epub, .pdf, .txt)
- Show file metadata (size, modified date)
- Support for UNC paths (Windows)
- Handle spaces and special characters
- Breadcrumb navigation

**Security**:
- Restrict to user home directory and subdirectories
- Validate all paths server-side
- Sanitize filenames for display
- Block system directories

### 5.2 Processing Status Component
**Requirements**:
- Real-time progress updates (WebSocket or Server-Sent Events)
- Queue management (pause, cancel, reorder)
- Error handling and retry options
- Processing statistics and timing
- Log access for troubleshooting

### 5.3 Search Interface Component
**Requirements**:
- Auto-complete based on processed content
- Query suggestions and history
- Advanced filters (date, book, section type)
- Result highlighting and context
- Export options (PDF, markdown, CSV)

### 5.4 Book Library Component
**Requirements**:
- Grid and list view modes
- Sorting (title, date, size, relevance)
- Filtering and grouping
- Bulk operations (delete, reprocess)
- Book metadata display and editing

## 6. Technical Architecture

### 6.1 Backend (Python/FastAPI)
```
┌─── Web Layer ───────────────────────────────────────┐
│ FastAPI Server (port 8000)                         │
│ ├─ /api/library    - Book management               │
│ ├─ /api/process    - File processing               │
│ ├─ /api/search     - RAG queries                   │
│ ├─ /api/browse     - File system navigation        │
│ └─ /api/settings   - Configuration                 │
└─────────────────────────────────────────────────────┘
           ▼
┌─── Integration Layer ───────────────────────────────┐
│ Adapters for existing code:                        │
│ ├─ pipeline.py     → ProcessingAdapter             │
│ ├─ rag_system.py   → SearchAdapter                 │
│ ├─ config.yml      → ConfigAdapter                 │
│ └─ cli.py          → CommandAdapter                │
└─────────────────────────────────────────────────────┘
```

### 6.2 Frontend (HTML/CSS/JS)
```
┌─── Frontend Stack ──────────────────────────────────┐
│ Option A: Vanilla JS + Bootstrap                   │
│ ├─ Simple, no build step                           │
│ ├─ Fast loading, minimal dependencies              │
│ └─ Easy to maintain and extend                     │
│                                                   │
│ Option B: Alpine.js + Tailwind                     │
│ ├─ Reactive components                             │
│ ├─ Modern utility CSS                              │
│ └─ Still no build step required                    │
└─────────────────────────────────────────────────────┘
```

### 6.3 Data Flow
```
User Action → Frontend JS → API Request → Backend Adapter → 
Existing Python Code → Database/Files → Response → 
Frontend Update → User Feedback
```

## 7. API Design

### 7.1 Core Endpoints
```python
# Library Management
GET    /api/library              # List all processed books
POST   /api/library              # Add book by path
DELETE /api/library/{book_id}    # Remove book from library
GET    /api/library/{book_id}    # Get book details

# Processing
POST   /api/process/file         # Process single file
POST   /api/process/folder       # Process folder recursively
GET    /api/process/status       # Get processing queue status
DELETE /api/process/{job_id}     # Cancel processing job

# Search
GET    /api/search               # Perform search query
GET    /api/search/suggest       # Get query suggestions
GET    /api/search/history       # Get search history

# File System
GET    /api/browse               # Browse directory contents
POST   /api/browse/validate      # Validate file path

# Configuration
GET    /api/settings             # Get current settings
PUT    /api/settings             # Update settings
POST   /api/settings/test        # Test configuration
```

### 7.2 WebSocket Events
```python
# Real-time updates
"processing.started"   - Job began
"processing.progress"  - Progress update (percentage)
"processing.completed" - Job finished successfully
"processing.failed"    - Job failed with error
"library.updated"      - Book added/removed from library
```

## 8. User Experience Flow

### 8.1 First-Time User Journey
1. **Landing**: Opens localhost:8000 → Library page (empty state)
2. **Discovery**: Notices "Process" tab → clicks
3. **File Selection**: Uses file browser → selects first book
4. **Processing**: Sees progress bar → completion notification
5. **Success**: Returns to Library → sees processed book
6. **Search**: Tries search → gets meaningful results
7. **Satisfaction**: Understands value → processes more books

### 8.2 Power User Journey
1. **Batch Processing**: Bulk processes entire directory
2. **Advanced Search**: Uses filters and complex queries
3. **Result Export**: Saves research findings
4. **Configuration**: Tweaks chunk size and models
5. **Maintenance**: Monitors database size and performance

## 9. Performance Considerations

### 9.1 Frontend Performance
- **Lazy loading**: Load book list progressively
- **Virtual scrolling**: Handle large libraries efficiently
- **Image optimization**: Compress book cover thumbnails
- **Caching**: Browser cache for static assets

### 9.2 Backend Performance
- **Async processing**: Non-blocking file operations
- **Queue management**: Background processing with progress
- **Database optimization**: Indexed searches, connection pooling
- **Caching**: Redis for frequently accessed data

## 10. Security Model

### 10.1 File System Access
```python
# Allowed paths
~/Books/**/*.(epub|pdf|txt)
~/Documents/**/*.(epub|pdf|txt)
~/Downloads/**/*.(epub|pdf|txt)

# Blocked paths
/system/**
C:\Windows\**
/etc/**
~/.*config/**
```

### 10.2 Input Validation
- Path sanitization and canonicalization
- File extension whitelist
- File size limits (configurable)
- Rate limiting on API endpoints

## 11. Deployment Options

### 11.1 Development Mode
```bash
poetry run uvicorn web_app:app --reload --port 8000
# Auto-restart on code changes
# Debug mode enabled
```

### 11.2 Production Mode  
```bash
poetry run uvicorn web_app:app --port 8000 --workers 1
# Single user application
# Error logging enabled
# Optimized for personal use
```

### 11.3 System Service (Optional)
- Auto-start with system
- Run in background
- System tray icon (future native wrapper)

## 12. Future Enhancements

### Phase 2 Features
- **Collections**: Group books by theme/genre
- **Annotations**: Highlight and note-taking
- **Sharing**: Export/import book collections
- **Mobile app**: Companion native mobile interface

### Phase 3 Features
- **Multi-user**: Family/team sharing
- **Cloud sync**: Optional cloud backup
- **AI assistants**: Specialized models per genre
- **Integration**: Connect with Calibre, Goodreads, etc.

## 13. Success Metrics

### Usability Goals
- **Time to first result**: < 2 minutes from startup
- **Processing speed**: Match or exceed CLI performance
- **Error rate**: < 5% of operations result in errors
- **User satisfaction**: Intuitive without documentation

### Technical Goals
- **Response time**: < 200ms for search queries
- **Concurrent users**: Support 1 user reliably (personal use)
- **Uptime**: 99.9% availability during usage sessions
- **Resource usage**: < 1GB RAM, < 10% CPU idle

## 14. Implementation Priority

### MVP (Minimum Viable Product)
1. Library page with processed book list
2. Process page with single file selection
3. Search page with basic query interface
4. Settings page with core configuration

### Phase 1 Enhancements
1. File browser component
2. Real-time processing updates
3. Advanced search filters
4. Result export functionality

### Phase 2 Features
1. Batch processing interface
2. Book management (edit, delete, reprocess)
3. Search history and saved queries
4. Theme customization

---
End of document.