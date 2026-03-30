# 🏠 Home Theater Architecture

This document provides a progressive overview of home theater architectures, starting from a basic client perspective and showing how the Turtle App enhances the experience.

## 🎭 The Traditional Home Theater Setup

### What Most People Start With

```mermaid
graph TB
    %% Basic Home Theater
    subgraph "Traditional Home Theater"
        User["🧑 User"]
        TV["📺 Smart TV / Media Player"]
        Storage["💾 Local Storage<br/>(External Drive, NAS)"]
        
        subgraph "Manual Processes"
            Search["🔍 Manual Movie Search<br/>(IMDB, Google)"]
            Download["⬇️ Manual Downloads<br/>(Various Sources)"]
            Organization["📁 Manual File Organization"]
        end
    end
    
    %% User Flow
    User --> Search
    Search --> Download
    Download --> Storage
    Storage --> TV
    User --> TV
```

**The Challenge**: Users manually search for movies, manage downloads, organize files, and remember what they have in their collection. It's time-consuming and fragmented.

## 🚀 Enhanced Home Theater with Download Automation

### Adding Download Management

```mermaid
graph TB
    %% Enhanced Setup
    subgraph "Enhanced Home Theater"
        User["🧑 User"]
        WebUI["🖥️ Download Client UI<br/>(qBittorrent Web)"]
        
        subgraph "Automated Downloads"
            QBittorrent["🌀 qBittorrent<br/>Download Manager"]
            Storage["📚 Network Storage<br/>(Samba/NAS)"]
        end
        
        TV["📺 Media Center<br/>(Plex, Jellyfin)"]
    end
    
    %% User Flow
    User --> WebUI
    WebUI --> QBittorrent
    QBittorrent --> Storage
    Storage --> TV
    User --> TV
```

**The Improvement**: Centralized download management with a web interface, automatic file organization, and network storage accessible by multiple devices.

**Remaining Challenges**: 
- Still need to manually search for content
- No intelligent recommendations
- Can't easily query "What movies do I have?"
- No conversation memory or context

## 🤖 AI-Powered Home Theater with Turtle App

### The Complete Solution

```mermaid
graph TB
    %% Complete AI System
    subgraph "AI-Enhanced Home Theater"
        User["🧑 User"]
        
        subgraph "Turtle App Layer"
            API["🌐 Turtle App API<br/>Natural Language Interface"]
            Supervisor["🎯 AI Supervisor<br/>Request Router"]
            
            subgraph "AI Agents"
                MovieAgent["🎬 Movie Expert<br/>42K+ Movies Database"]
                DownloadAgent["⬬ Download Manager<br/>Torrent Control"]
                LibraryAgent["📁 Library Manager<br/>Collection Scanner"]
            end
        end
        
        subgraph "Enhanced Infrastructure"
            QBittorrent["🌀 qBittorrent<br/>Download Client"]
            Storage["📚 Network Storage<br/>File Management"]
            VectorDB["🗄️ Pinecone<br/>Movie Embeddings"]
        end
        
        subgraph "AI Services"
            Claude["🧠 Claude<br/>Language Processing"]
            OpenAI["🔤 OpenAI<br/>Embeddings"]
        end
        
        TV["📺 Media Center"]
    end
    
    %% User Flow
    User --> API
    API --> Supervisor
    Supervisor --> MovieAgent
    Supervisor --> DownloadAgent  
    Supervisor --> LibraryAgent
    
    MovieAgent --> VectorDB
    MovieAgent --> Claude
    DownloadAgent --> QBittorrent
    LibraryAgent --> Storage
    
    QBittorrent --> Storage
    Storage --> TV
    User --> TV
    
    %% AI Service Connections
    MovieAgent --> OpenAI
    DownloadAgent --> Claude
    LibraryAgent --> Claude
```

**The Transformation**: 
- **Natural Language Interface**: "Find me a sci-fi movie like Blade Runner"
- **Intelligent Recommendations**: AI-powered suggestions based on 42,000+ movie database
- **Automated Management**: AI agents handle downloads, library scanning, and organization
- **Conversation Memory**: Maintains context across multiple interactions
- **Unified Control**: Single interface for movie discovery, downloads, and library management

### Real-World Usage Examples

**Movie Night Planning**:
```
User: "I want to watch something like Inception"
Turtle App: "Found similar movies: The Matrix, Dark City, Shutter Island. 
            You already have The Matrix in your library. 
            Would you like me to download Dark City?"
```

**Library Management**:
```
User: "What sci-fi movies do I have?"
Turtle App: "You have 23 sci-fi movies including: Blade Runner, The Matrix, 
            Interstellar... Would you like the full list or recommendations?"
```

**Download Automation**:
```
User: "Download the latest Marvel movie"
Turtle App: "Found 'Guardians of the Galaxy Vol. 3' (2023). 
            Starting download... Current progress: 15% complete."
```

## 🐳 Docker Implementation Architecture

### How It All Works Together

```mermaid
graph TB
    %% Docker Compose Services
    subgraph "Docker Network"
        subgraph "AI Application"
            TurtleApp["🐳 Turtle App API<br/>FastAPI + LangGraph"]
        end
        
        subgraph "Infrastructure Services"
            QBittorrent["🐳 qBittorrent<br/>Download Server"]
            Samba["🐳 Samba<br/>Network Share"]
        end
    end

    %% External AI Services
    subgraph "Cloud AI Services"
        Claude["🌐 Claude API<br/>Language Processing"]
        OpenAI["🌐 OpenAI API<br/>Embeddings"]
        Pinecone["🌐 Pinecone API<br/>Vector Database"]
    end

    %% Volume Mounts
    subgraph "Shared Storage"
        Downloads["📁 ./downloads<br/>Shared Media Storage"]
        Config["📁 ./volumes/<br/>Configuration"]
    end

    %% Network Connections
    TurtleApp --> Claude
    TurtleApp --> OpenAI
    TurtleApp --> Pinecone
    TurtleApp -.->|Internal Network| QBittorrent
    TurtleApp -.->|Internal Network| Samba
    
    QBittorrent --> Downloads
    Samba --> Downloads
    TurtleApp --> Downloads
    QBittorrent --> Config
```

## 🖥️ Client-Server Architecture

### Communication Flow

```mermaid
graph TB
    %% Client Layer
    subgraph "Client Layer"
        User["🧑 User"]
        WebUI["🖥️ qBittorrent Web UI"]
    end

    %% Server Layer
    subgraph "Server Layer"
        TurtleApp["🌐 Turtle App API<br/>FastAPI Server"]
    end

    %% AI Services Layer
    subgraph "AI Services"
        ClaudeAPI["🌐 Claude API<br/>Language Processing"]
        OpenAIAPI["🌐 OpenAI API<br/>Embeddings"]
        PineconeAPI["🌐 Pinecone API<br/>Vector Database"]
    end

    %% Infrastructure Layer
    subgraph "Infrastructure"
        QBittorrent["🌀 qBittorrent<br/>Download Client"]
        Samba["📚 Samba<br/>File Sharing"]
    end

    %% Client-Server Communication
    User --> TurtleApp
    WebUI --> QBittorrent
    
    %% Server to AI Services
    TurtleApp --> ClaudeAPI
    TurtleApp --> OpenAIAPI
    TurtleApp --> PineconeAPI
    
    %% Server to Infrastructure
    TurtleApp --> QBittorrent
    TurtleApp --> Samba
```

## 🤖 LLM Client-Server Architecture

### AI Service Integration

```mermaid
graph TB
    %% Docker Services
    subgraph "Docker Network"
        TurtleApp["🐳 Turtle App API<br/>FastAPI Application"]
    end

    %% External AI Services
    subgraph "Cloud AI Services"
        ClaudeAPI["🌐 Claude API<br/>Language Processing"]
        OpenAIAPI["🌐 OpenAI API<br/>Embeddings Service"]
        PineconeAPI["🌐 Pinecone API<br/>Vector Database"]
    end

    %% AI Agent Components
    subgraph "AI Agents"
        Supervisor["🎯 Supervisor Agent<br/>Request Routing"]
        MovieRetriever["🎬 Movie Retriever<br/>Vector Search"]
        TorrentManager["⬬ Torrent Manager<br/>Download Control"]
        LibraryManager["📁 Library Manager<br/>File System"]
    end

    %% Data Flow
    TurtleApp --> Supervisor
    Supervisor --> MovieRetriever
    Supervisor --> TorrentManager
    Supervisor --> LibraryManager

    MovieRetriever --> ClaudeAPI
    MovieRetriever --> PineconeAPI
    TorrentManager --> ClaudeAPI
    LibraryManager --> ClaudeAPI

    MovieRetriever --> OpenAIAPI
```

## 🔄 Complete System Flow

### User Request to Response

```mermaid
sequenceDiagram
    participant User as 🧑 User
    participant API as 🌐 Turtle App API
    participant Supervisor as 🎯 Supervisor Agent
    participant Agents as 🤖 AI Agents
    participant Services as 🌐 External Services

    User->>API: "Tell me about Terminator 2"
    API->>Supervisor: Route request
    Supervisor->>Agents: Select appropriate agent
    Agents->>Services: Query AI services
    Services-->>Agents: Return AI response
    Agents-->>Supervisor: Process results
    Supervisor-->>API: Compile response
    API-->>User: Return movie information
```

## 🛠️ Technology Stack

### Core Components

```mermaid
graph LR
    %% Application Layer
    subgraph "Application"
        FastAPI["⚡ FastAPI<br/>Python 3.11+"]
        LangGraph["🔄 LangGraph<br/>Multi-Agent Orchestration"]
    end

    %% AI Layer
    subgraph "AI Services"
        Claude["🧠 Claude API<br/>Language Processing"]
        OpenAI["🔤 OpenAI<br/>Embeddings"]
        Pinecone["🗄️ Pinecone<br/>Vector DB"]
    end

    %% Infrastructure Layer
    subgraph "Infrastructure"
        Docker["🐳 Docker Compose"]
        QBittorrent["🌀 qBittorrent"]
        Samba["📚 Samba/CIFS"]
    end

    %% Connections
    FastAPI --> LangGraph
    LangGraph --> Claude
    LangGraph --> OpenAI
    OpenAI --> Pinecone
    FastAPI --> Docker
    Docker --> QBittorrent
    Docker --> Samba
```

## 🎯 Key Features

### What the System Does

1. **🎬 Movie Information**: Query 42,000+ movie database with AI-powered search
2. **⬬ Download Management**: Control qBittorrent for movie file downloads
3. **📁 Library Management**: Scan and organize local movie collection
4. **🤖 AI Orchestration**: Multi-agent system with specialized AI agents
5. **🌐 Web API**: RESTful endpoints for external integration

### How It Works

1. **User sends request** to FastAPI endpoint
2. **Supervisor Agent** routes request to appropriate specialized agent
3. **Specialized Agents** handle specific tasks (movies, downloads, library)
4. **External AI Services** provide language processing and vector search
5. **Infrastructure Services** manage downloads and file storage
6. **Response returned** to user with comprehensive information

This architecture provides a clean, scalable foundation for AI-powered home theater management with clear separation between Docker infrastructure, AI services, and application logic. 