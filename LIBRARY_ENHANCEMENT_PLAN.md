# Turtle App Enhancements: Library Search & Auto-Download

## Goals
1. Add intelligent search and filter capabilities to the library_manager tool while keeping API costs low by performing all filtering server-side and only returning relevant results to the LLM.
2. Auto-detect magnet links and torrent URLs in user messages and automatically add them to qBittorrent.

## User Requirements
- Search for specific movies: "Do I have Terminator 2?"
- Filter by file format: "Show me my MKV files"
- General library queries: "What movies do I have?"
- Keep token costs minimal (no sending 300+ movie titles to LLM)

## Implementation Approach

### Architecture Decision: Minimal Change
**Keep existing direct node pattern** - don't convert to ToolAgent. The tool will receive the full user message and intelligently parse it to determine search intent.

**Why this approach:**
- Minimal architectural changes
- Maintains current workflow structure
- Tool handles its own "intelligence" for parameter extraction
- Simpler to implement and test

### Core Strategy
1. **Smart message parsing**: Extract search intent from user message (keywords, file format hints, etc.)
2. **Server-side filtering**: Do all searching/filtering in tool code before returning results
3. **Tiered output**: Adjust verbosity based on result count (specific results vs. statistics)
4. **Fuzzy matching**: Find movies even with typos or variations

## Implementation Details

### 1. Enhanced Library Manager Tool (library_manager.py)

**Changes to `LibraryManagerTool._run()` method:**

```python
def _run(self, user_message: str = "") -> str:
    """Enhanced with smart search and filtering.

    Args:
        user_message: Full user query (e.g., "Do I have Inception?", "show mkv files")

    Returns:
        Formatted results based on query type and result count
    """
    # Parse user intent
    search_query, file_format, intent_type = self._parse_user_intent(user_message)

    # Scan SMB library (full scan)
    all_movies = scan_smb_movie_library()

    # Filter by file format if detected
    filtered_movies = self._filter_by_extension(all_movies, file_format)

    # Search with fuzzy matching if query detected
    if search_query:
        search_results = self._search_movies(filtered_movies, search_query, limit=20)
    else:
        search_results = [(name, path, 1.0) for name, path in list(filtered_movies.items())[:20]]

    # Format output based on result count (tiered strategy)
    return self._format_output(all_movies, search_results, search_query, intent_type)
```

**New helper methods to add:**

1. **`_parse_user_intent(message: str) -> Tuple[str, str, str]`**
   - Extract search keywords from message
   - Detect file format hints ("mkv", "mp4", ".avi")
   - Determine intent type: "specific_search", "format_filter", "general_scan"
   - Use regex patterns and keyword detection

2. **`_filter_by_extension(movies: Dict, format: str) -> Dict`**
   - Filter movies dictionary by file extension
   - Support: mkv, mp4, avi, mov, wmv
   - Case-insensitive matching

3. **`_search_movies(movies: Dict, query: str, limit: int) -> List[Tuple]`**
   - Multi-strategy matching (progressive fallback):
     1. Exact substring match (score: 1.0)
     2. All keywords present (score: 0.9)
     3. Fuzzy similarity using `difflib.SequenceMatcher` (threshold: 0.6)
     4. Partial keyword match (score: 0.5 * match_ratio)
   - Returns list of (movie_name, path, score) sorted by relevance
   - Uses `difflib` library for fuzzy matching

4. **`_format_output(all_movies: Dict, results: List, query: str, intent: str) -> str`**
   - **Tier 1** (1-5 specific results): Detailed listing with metadata
   - **Tier 2** (6-20 results): Summarized with top matches + count
   - **Tier 3** (general scan / 20+ results): Statistics + 5 samples (current behavior)

**Update tool description:**
```python
description: str = """Scan, search, and filter your local movie library from SMB shares.

Use when users ask about:
- Specific movies ("Do I have Inception?", "Is Terminator 2 in my library?")
- File format queries ("Show me MKV files", "What MP4 movies do I have?")
- General library info ("What movies do I own?", "Show my collection")

The tool intelligently parses your request and performs server-side filtering
to minimize token usage. Supports fuzzy matching for typos and variations.

Input: User's natural language query
Output: Relevant movies or library statistics (formatted for minimal tokens)
"""
```

### 2. Update library_scan_node Function (agents.py)

**Minimal change** - pass user message to tool instead of empty string:

```python
def library_scan_node(state: MessagesState) -> Command[Literal["supervisor"]]:
    """Direct library scan with smart message parsing."""
    try:
        # Get user's latest message
        latest_message = state["messages"][-1].content if state["messages"] else ""

        # Tool now receives full message for intelligent parsing
        result = library_manager_tool._run(latest_message)

        return Command(
            update={"messages": [HumanMessage(content=result)]},
            goto=SUPERVISOR_NODE
        )
    except Exception as e:
        error_msg = f"Library scan failed: {str(e)}"
        return Command(
            update={"messages": [HumanMessage(content=error_msg)]},
            goto=SUPERVISOR_NODE
        )
```

### 3. Add Metadata Extraction Utility (movie_names.py)

**New function** to extract year and quality tags:

```python
def extract_movie_metadata(filename: str) -> dict:
    """Extract metadata from movie filename.

    Returns:
        {
            'title': str,           # Cleaned movie title
            'year': str | None,     # Release year (YYYY)
            'quality': str | None,  # Quality tag (1080p, 720p, 4K, BluRay, etc.)
            'format': str           # File extension (.mkv, .mp4, etc.)
        }
    """
    name_without_ext = os.path.splitext(filename)[0]

    metadata = {
        'title': clean_movie_filename(filename),
        'year': None,
        'quality': None,
        'format': os.path.splitext(filename)[1].lower()
    }

    # Extract year: look for 4-digit year (1900-2099)
    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', name_without_ext)
    if year_match:
        metadata['year'] = year_match.group(1)

    # Extract quality: common video quality indicators
    quality_patterns = r'(1080p|720p|2160p|4K|BluRay|BRRip|WEB-DL|WEBRip|HDRip)'
    quality_match = re.search(quality_patterns, name_without_ext, re.IGNORECASE)
    if quality_match:
        metadata['quality'] = quality_match.group(1)

    return metadata
```

### 4. Comprehensive Testing (test_library_manager.py)

**Expand existing test file** with new test cases:

**Unit tests (no SMB required):**
- `test_parse_user_intent_specific_search()` - "Do I have Inception?"
- `test_parse_user_intent_format_filter()` - "Show me MKV files"
- `test_parse_user_intent_general()` - "What movies do I have?"
- `test_filter_by_extension()` - Filter MKV from mixed formats
- `test_search_movies_exact_match()` - Exact title match
- `test_search_movies_fuzzy_match()` - Typo handling ("Terminater" → "Terminator")
- `test_search_movies_partial_keywords()` - Multiple keywords
- `test_extract_metadata()` - Parse year and quality from filenames
- `test_format_output_tier1()` - 1-5 specific results
- `test_format_output_tier2()` - 6-20 results
- `test_format_output_tier3()` - General statistics

**Integration tests (requires SMB - mark as @pytest.mark.expensive):**
- `test_tool_specific_movie_search()` - Search for specific movie
- `test_tool_format_filter()` - Filter by file format
- `test_tool_general_scan()` - General library scan

---

## Enhancement 2: Auto-Detect Magnet Links & Torrent URLs

### Goal
Automatically detect when user sends a magnet link or torrent URL and route to download manager to add it to qBittorrent.

### Example User Message
```
magnet:?xt=urn:btih:B092C038E1B1367A34F1B3D48F8615FBEC19889F&dn=Labyrinth.1986.REMASTERED.1080p.BluRay.x265&tr=...
```

### Implementation Details

**Update Supervisor Prompt** (turtleapp/src/core/prompts/supervisor.py):

Add magnet/torrent URL detection to routing rules:

```python
SUPERVISOR_SYSTEM_MESSAGE = """You are the supervisor of a specialized home theater management system with three expert agents:

**Available Agents:**
- movie_details_retriever_agent: Expert in searching movie database (42k+ movies) for plot, cast, director, genre info
- movies_download_manager: Expert in movie file search and download management via download client
- library_manager_agent: Expert in scanning SMB network shares for existing movie files

**Routing Decision Rules:**

**PRIORITY: Auto-detect URLs and Magnet Links**
If the user's message contains a magnet link (starts with "magnet:?") or torrent URL (contains ".torrent"):
   - Route to movies_download_manager IMMEDIATELY
   - The agent will extract and add the torrent automatically

1. Route to movie_details_retriever_agent when user asks about:
   - Movie plots, summaries, or details
   - Cast, director, or crew information
   - Movie recommendations or similar films
   - Genre-based queries

2. Route to movies_download_manager when user wants to:
   - Download or find movies
   - Check download status/progress
   - Search for available movie files
   - **Message contains magnet links or .torrent URLs**

3. Route to library_manager_agent when user asks about:
   - What movies they already own
   - Library organization or scanning
   - Local file management

4. Route to FINISH when:
   - Task is complete and no further action needed
   - User says goodbye or thanks
   - Question is answered satisfactorily
   - Agent has provided requested information (e.g., library scan results, movie details, download status)

**Context**: This is a home theater enthusiast's personal system for managing their movie collection.

**Important**: If the latest message contains complete information that answers the user's request (like library scan results, movie details, or download status), route to FINISH rather than routing back to the same agent.

Analyze the user's request and route to the most appropriate specialist agent."""
```

**Optional: Add URL Extraction Prompt for Torrent Agent**

Create specialized prompt for torrent agent (turtleapp/src/core/prompts/agents.py):

```python
TORRENT_AGENT_TEMPLATE = """You are a download manager expert with access to qBittorrent tools.

Your expertise includes:
- Adding torrents via magnet links or .torrent URLs
- Monitoring download progress and status
- Managing torrent categories and organization
- Searching for available torrents

**Available Tools:** {tools}
**Tool Usage Guidelines:**
- If the user's message contains a magnet link (magnet:?) or torrent URL (.torrent):
  * Extract the complete URL/magnet link
  * Use qb_add_torrent tool with the URL
  * Optionally set category="Movies" for organization
- For status queries: use qb_list_torrents
- For search queries: use qb_search_torrents

**Task:** {input}

Think step by step:
1. Check if message contains magnet link or .torrent URL
2. If yes, extract the complete URL and add it using qb_add_torrent
3. If no, determine what download-related action user wants
4. Use appropriate tool with correct parameters
5. Present results clearly

Action: {tool_names}
Action Input: the input for the action
Observation: the result of the action
Thought: What's the result and what should I do next?
Final Answer: Complete response for the user

{agent_scratchpad}"""

TORRENT_AGENT_PROMPT = PromptTemplate(
    template=TORRENT_AGENT_TEMPLATE,
    input_variables=["tools", "tool_names", "input", "agent_scratchpad"]
)
```

**Update Torrent Agent** (turtleapp/src/core/nodes/agents.py):

```python
# Add specialized prompt for torrent agent
torrent_agent = ToolAgent(
    get_qbittorrent_tools(),
    name="movies_download_manager",
    specialized_prompt=TORRENT_AGENT_PROMPT  # Add this line
)
```

### How It Works

**User Flow:**
1. User sends: `magnet:?xt=urn:btih:B092C038E1B1367A34F1B3D48F8615FBEC19889F&dn=Labyrinth.1986...`
2. Supervisor detects "magnet:?" in message
3. Routes to movies_download_manager agent
4. Agent extracts magnet link and calls `qb_add_torrent(url="magnet:?...")`
5. Returns confirmation: "Added Labyrinth (1986) to downloads"

**Supported Formats:**
- Magnet links: `magnet:?xt=urn:btih:...`
- Torrent URLs: `https://example.com/file.torrent`
- Mixed messages: "Download this: magnet:?..." (agent extracts URL)

### Testing

**Unit Tests** (add to turtleapp/tests/test_torrent_agent.py):
- `test_detect_magnet_link()` - Verify magnet link detection
- `test_extract_magnet_from_message()` - Extract URL from mixed message
- `test_detect_torrent_url()` - Verify .torrent URL detection

**Integration Tests** (@pytest.mark.expensive):
- `test_add_magnet_link()` - Send magnet link, verify qb_add_torrent called
- `test_add_torrent_url()` - Send .torrent URL, verify addition
- `test_supervisor_routes_magnet_links()` - Test full workflow routing

### Files to Modify for Auto-Download Feature

1. **turtleapp/src/core/prompts/supervisor.py** (~10 lines changed)
   - Add magnet/torrent URL detection to routing rules
   - Make it a priority check

2. **turtleapp/src/core/prompts/agents.py** (~40 lines added) - OPTIONAL
   - Add TORRENT_AGENT_TEMPLATE with URL extraction guidance
   - Add TORRENT_AGENT_PROMPT export

3. **turtleapp/src/core/nodes/agents.py** (~2 lines changed) - OPTIONAL
   - Add specialized_prompt parameter to torrent_agent

4. **turtleapp/tests/test_torrent_agent.py** (~50 lines added)
   - Add tests for URL detection and extraction
   - Test integration with qBittorrent tools

### Implementation Sequence

**Phase A1: Supervisor Routing** (Low Risk)
1. Update supervisor prompt with magnet/torrent detection
2. Test routing with sample magnet links

**Phase A2: Agent Enhancement** (Optional, Medium Risk)
1. Add specialized torrent agent prompt
2. Update torrent agent to use specialized prompt
3. Test URL extraction and tool invocation

**Phase A3: Testing**
1. Test with various magnet link formats
2. Test with .torrent URLs
3. Test mixed messages ("Download this: magnet...")
4. Test full workflow end-to-end

---

## Files to Modify

### Primary Implementation (Library Search)
1. **turtleapp/src/core/tools/library_manager.py** (~200 lines added)
   - Add 4 new helper methods (_parse_user_intent, _filter_by_extension, _search_movies, _format_output)
   - Update _run() method to accept and process user message
   - Update tool description
   - Import difflib for fuzzy matching

2. **turtleapp/src/core/nodes/agents.py** (~5 lines changed)
   - Update library_scan_node() to pass user message to tool
   - Extract latest message from state

3. **turtleapp/src/utils/movie_names.py** (~30 lines added)
   - Add extract_movie_metadata() function
   - Import re and os for pattern matching

4. **turtleapp/tests/test_library_manager.py** (~150 lines added)
   - Add 12+ new test functions
   - Create mock movie data fixtures
   - Test all helper methods and integration scenarios

### No Changes Needed
- **turtleapp/src/workflows/graph.py** - No changes (still uses library_scan_node)
- **turtleapp/src/core/prompts/** - No changes (direct node doesn't use prompts)
- **turtleapp/settings.py** - No changes (no new config needed)

## Combined Implementation Sequence

### Phase 0: Auto-Download Feature (Quickest Win)
1. Update supervisor prompt with magnet/torrent detection (Phase A1)
2. Optionally add specialized torrent agent prompt (Phase A2)
3. Test magnet link detection (Phase A3)

### Phase 1: Core Utilities (Low Risk)
1. Add `extract_movie_metadata()` to movie_names.py
2. Add unit tests for metadata extraction
3. Verify regex patterns work correctly

### Phase 2: Tool Helper Methods (Medium Risk)
1. Add `_parse_user_intent()` method
2. Add `_filter_by_extension()` method
3. Add `_search_movies()` method with fuzzy matching
4. Add `_format_output()` method
5. Add unit tests for each method (can use mock data)

### Phase 3: Tool Integration (Medium Risk)
1. Update `_run()` method to use new helpers
2. Update tool description
3. Test with mock SMB data

### Phase 4: Node Update (Low Risk)
1. Update `library_scan_node()` to pass user message
2. Test integration with state/messages

### Phase 5: Integration Testing (Requires SMB)
1. Add integration tests (mark as expensive)
2. Test with real SMB connection
3. Verify output formats and token counts

### Phase 6: Validation
1. Test various user query patterns
2. Test full workflow with supervisor routing
3. Verify token usage is minimal

## Expected Outcomes

### Before Enhancement
**Query**: "Do I have Terminator 2?"
**Output**: "Library scan completed. Found 247 movies. File types: .mkv: 156, .mp4: 78, .avi: 13. Sample movies: Avatar, The Shawshank Redemption, Inception, Pulp Fiction, The Dark Knight... and 242 more"
**Problem**: LLM has no information about Terminator 2 (only saw 5 samples)

### After Enhancement
**Query**: "Do I have Terminator 2?"
**Output**: "Found 1 movie matching 'Terminator 2':

Terminator 2 Judgment Day (1991) [1080p BluRay]
Format: .mkv | Path: /Movies/Terminator.2.1991.1080p.BluRay.mkv"

**Benefit**: Specific answer, minimal tokens (~50 vs ~200 in statistics mode)

## Token Cost Analysis

**Current approach** (statistics only):
- ~150-200 tokens per response (regardless of query)
- Cannot answer specific questions

**Enhanced approach**:
- Specific search (1-5 results): ~50-100 tokens
- Moderate search (6-20 results): ~150-300 tokens
- General scan (statistics): ~150-200 tokens (same as before)

**Key insight**: Token usage scales with relevance, not library size.

## Future Enhancements (Out of Scope)

These can be added later without major refactoring:
1. **Caching layer** - Cache SMB scan results for 10 minutes (add when performance becomes issue)
2. **Year filtering** - "Show me movies from the 90s"
3. **Quality filtering** - "Show me 1080p movies"
4. **Multi-library support** - Scan multiple SMB shares
5. **Advanced fuzzy matching** - Use Levenshtein distance or rapidfuzz for better performance
6. **Regex search** - Power users can use regex patterns

## Success Criteria

### Library Search Enhancement
- ✅ Can search for specific movies by title
- ✅ Can filter by file format (mkv, mp4, etc.)
- ✅ Fuzzy matching handles typos
- ✅ Output tokens scale with result count (not library size)
- ✅ General "show library" queries still work
- ✅ Works seamlessly with supervisor routing and workflow

### Auto-Download Enhancement
- ✅ Magnet links automatically detected and added to qBittorrent
- ✅ Torrent URLs (.torrent) automatically detected and added
- ✅ Works with mixed messages ("Download this: magnet...")
- ✅ User receives confirmation after torrent is added
- ✅ All tests pass (unit + integration)
