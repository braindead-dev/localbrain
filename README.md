# 🧠 LocalBrain

> **The personalization layer for the next generation of AI apps**  
> Provide AI apps with context about your life, on autopilot.

## What is LocalBrain?

Using connector plugins, LocalBrain automatically checks for new info about you from your communication channels (Gmail, Discord, etc.). Any time something new about your life is revealed, LocalBrain automatically ingests it 

**Ask questions like:**
- "What internship applications did I submit?"
- "Find emails about the Q3 launch"
- "Show me notes about machine learning"

**Get instant answers** from your personal knowledge base.

---

## ✨ Features

### 🔍 **Agentic Search**
- Natural language queries powered by Claude
- 95% retrieval accuracy on benchmark tests
- Multi-tool agentic system (grep, read, analyze)

### 🔌 **Universal Connectors**
Plugin system for syncing external data:
- **Gmail** - Emails and threads
- **Discord** - DMs and channels
- **Browser History** - Web activity
- **iMessage** - Text conversations (coming soon)
- **Custom** - Easy to add your own!

### 🎯 **Claude Desktop Integration**
- MCP (Model Context Protocol) extension
- Search your vault directly from Claude
- Open files, list directories, generate summaries

### 🚀 **Smart Ingestion**
- Automatic chunking with citations
- Metadata extraction
- Multi-stage summarization
- Source tracking

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Claude Desktop                        │
│                  (MCP Extension)                         │
└──────────────────────┬──────────────────────────────────┘
                       │ stdio
┌──────────────────────▼──────────────────────────────────┐
│                  MCP Server (Port 8766)                  │
│           Pure proxy - auth, audit, routing              │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP
┌──────────────────────▼──────────────────────────────────┐
│              Daemon Backend (Port 8765)                  │
│  • Agentic Search (Claude + Tools)                      │
│  • Connector Manager (Plugin System)                    │
│  • Ingestion Pipeline                                   │
└──────────────────────┬──────────────────────────────────┘
                       │
           ┌───────────┴───────────┐
           │                       │
┌──────────▼──────────┐  ┌────────▼─────────┐
│   Markdown Vault    │  │    Connectors    │
│  (Your Knowledge)   │  │  (Gmail, Discord) │
└─────────────────────┘  └──────────────────┘
```

---

## 🚀 Quick Start

**Get running in 5 minutes!**

```bash
# 1. Clone
git clone https://github.com/yourusername/localbrain.git
cd localbrain

# 2. Install backend
cd electron/backend
pip install -r requirements.txt

# 3. Configure
mkdir -p ~/.localbrain
echo '{"vault_path": "'$HOME'/my-vault", "port": 8765}' > ~/.localbrain/config.json
export ANTHROPIC_API_KEY="your-key"

# 4. Create test vault
mkdir -p ~/my-vault
echo "# Test\nMachine learning project notes" > ~/my-vault/test.md

# 5. Start
python src/daemon.py
```

**First search:**
```bash
curl -X POST http://localhost:8765/protocol/search \
  -d '{"q": "machine learning"}'
```

**[Full setup guide →](docs/QUICKSTART.md)**

---

## 📚 Documentation

- **[Architecture Overview](docs/ARCHITECTURE.md)** - System design and components
- **[Search System](docs/SEARCH.md)** - How agentic search works
- **[Connectors](docs/CONNECTORS.md)** - Plugin system for external data
- **[MCP Extension](docs/MCP.md)** - Claude Desktop integration
- **[API Reference](docs/API.md)** - REST endpoints

---

## 🎯 Use Cases

### Personal Knowledge Management
- Search across emails, notes, and documents
- Find information instantly without manual organization
- Track projects, ideas, and research

### Professional Work
- Quick access to past conversations
- Project documentation search
- Meeting notes and action items

### Research & Learning
- Aggregate research papers and notes
- Cross-reference sources
- Build knowledge graphs

---

## 🧪 Performance

**Benchmark**: LongMemEval test suite (20 questions)

| Metric | Score |
|--------|-------|
| **Retrieval Accuracy** | 95% (19/20) |
| **Average Query Time** | 2-4 seconds |
| **False Positives** | 1/20 |

---

## 🔌 Connector System

Add new data sources by implementing 4 methods:

```python
from connectors.base_connector import BaseConnector

class MyConnector(BaseConnector):
    def get_metadata(self) -> ConnectorMetadata:
        # Connector info
        pass
    
    def has_updates(self, since=None) -> bool:
        # Check for new data
        pass
    
    def fetch_updates(self, since=None, limit=None) -> List[ConnectorData]:
        # Fetch and convert data
        pass
    
    def get_status(self) -> ConnectorStatus:
        # Return connection status
        pass
```

Drop in `connectors/<name>/` and it's auto-discovered!

See [Connector Plugin Architecture](electron/backend/src/connectors/PLUGIN_ARCHITECTURE.md) for details.

---

## 🛠️ Tech Stack

**Backend**
- FastAPI - REST API
- Claude Haiku - Agentic search
- ChromaDB - Vector storage (optional)
- Python 3.10+

**Frontend**
- Next.js - Web interface
- Electron - Desktop app
- TailwindCSS - Styling

**Integration**
- MCP Protocol - Claude Desktop
- OAuth 2.0 - Gmail connector
- Discord.py - Discord connector

---

## 📦 Project Structure

```
localbrain/
├── docs/                    # Documentation
├── electron/
│   ├── app/                 # Next.js frontend
│   └── backend/             # FastAPI backend
│       ├── src/
│       │   ├── daemon.py    # Main service
│       │   ├── agentic_search.py  # Search engine
│       │   ├── connectors/  # Plugin system
│       │   └── core/
│       │       └── mcp/     # Claude Desktop integration
│       └── requirements.txt
├── my-vault/                # Example vault
└── README.md                # This file
```

---

## 🤝 Contributing

We welcome contributions! Areas we'd love help with:

- **New connectors** (Slack, Notion, Todoist, etc.)
- **Search improvements** (better retrieval, ranking)
- **UI enhancements** (better visualization)
- **Performance optimization**

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

---

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built with [Claude](https://anthropic.com) by Anthropic
- Inspired by personal knowledge management systems
- Thanks to the open-source community

---

## 💬 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/localbrain/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/localbrain/discussions)
- **Email**: support@localbrain.dev

---

**Made with ❤️ for personal knowledge management**
