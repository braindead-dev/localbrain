# Contributing to LocalBrain

Thank you for your interest in contributing! This document provides guidelines and information for contributors.

---

## Ways to Contribute

### 🐛 Bug Reports
- Use GitHub Issues
- Include steps to reproduce
- Provide system information
- Include error logs if applicable

### ✨ Feature Requests
- Describe the use case
- Explain why it's valuable
- Consider implementation complexity

### 🔌 New Connectors
- High-impact contributions
- Follow the connector template
- Include documentation
- Add tests

### 📝 Documentation
- Fix typos and errors
- Add examples
- Improve clarity
- Translate to other languages

### 🎨 UI/UX Improvements
- Better visualizations
- Improved user flows
- Accessibility enhancements

---

## Development Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- Git

### Getting Started

```bash
# Clone repository
git clone https://github.com/yourusername/localbrain.git
cd localbrain

# Backend setup
cd electron/backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Frontend setup
cd ../app
npm install

# Create config
mkdir -p ~/.localbrain
echo '{"vault_path": "/path/to/test/vault", "port": 8765}' > ~/.localbrain/config.json

# Run tests
cd ../backend
pytest
```

---

## Code Style

### Python
- Follow PEP 8
- Use type hints
- Docstrings for public functions
- Max line length: 100 characters

```python
def search(query: str, limit: int = 10) -> List[SearchResult]:
    """
    Search vault with natural language query.
    
    Args:
        query: Natural language search string
        limit: Maximum results to return
    
    Returns:
        List of SearchResult objects
    """
    pass
```

### TypeScript
- Use TypeScript strict mode
- Functional components for React
- Descriptive variable names

```typescript
interface SearchProps {
  query: string;
  onResults: (results: SearchResult[]) => void;
}

const SearchBar: React.FC<SearchProps> = ({ query, onResults }) => {
  // ...
};
```

---

## Creating a Connector

### 1. Use Template

```bash
cp -r electron/backend/src/connectors/gmail electron/backend/src/connectors/my_service
```

### 2. Implement Interface

```python
from connectors.base_connector import BaseConnector

class MyServiceConnector(BaseConnector):
    def get_metadata(self) -> ConnectorMetadata:
        # Return connector info
        pass
    
    def has_updates(self, since=None) -> bool:
        # Check for new data
        pass
    
    def fetch_updates(self, since=None, limit=None) -> List[ConnectorData]:
        # Fetch and return data
        pass
    
    def get_status(self) -> ConnectorStatus:
        # Return connection status
        pass
```

### 3. Add Documentation

Create `connectors/my_service/README.md`:
- Setup instructions
- Authentication steps
- Configuration options
- Known limitations

### 4. Add Tests

```python
def test_my_service_connector():
    connector = MyServiceConnector()
    assert connector.get_metadata().id == "my_service"
    # More tests...
```

### 5. Submit PR

- Reference issue number
- Describe changes
- Include screenshots if UI changes
- Ensure tests pass

---

## Pull Request Process

### Before Submitting

1. **Test thoroughly**
   ```bash
   pytest                    # Backend tests
   npm test                  # Frontend tests
   python src/daemon.py      # Manual testing
   ```

2. **Update documentation**
   - Update relevant README files
   - Add docstrings
   - Update CHANGELOG.md

3. **Follow commit conventions**
   ```
   feat: add Slack connector
   fix: resolve search timeout issue
   docs: update API documentation
   refactor: simplify connector manager
   ```

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] Added new tests
- [ ] Manual testing completed

## Related Issues
Fixes #123
```

### Review Process

1. Maintainer reviews code
2. Address feedback
3. Tests must pass
4. Documentation updated
5. Merge!

---

## Testing Guidelines

### Unit Tests
- Test individual functions
- Mock external dependencies
- Fast execution

```python
def test_search_parser():
    parser = SearchParser()
    result = parser.parse("test query")
    assert result.query == "test query"
```

### Integration Tests
- Test component interactions
- Use test vault
- May be slower

```python
def test_full_search_flow():
    daemon = start_test_daemon()
    result = daemon.search("test")
    assert len(result.contexts) > 0
```

### Manual Testing
- Test in real environment
- Try edge cases
- Verify UI changes

---

## Documentation Guidelines

### README Files
- Clear and concise
- Include examples
- Link to related docs
- Keep up to date

### Code Comments
- Explain "why", not "what"
- Complex algorithms need explanation
- Keep comments current

### API Documentation
- Document all endpoints
- Include request/response examples
- Note authentication requirements
- List error codes

---

## Release Process

### Version Numbers
Follow Semantic Versioning:
- **Major**: Breaking changes
- **Minor**: New features (backwards-compatible)
- **Patch**: Bug fixes

### Creating a Release

1. **Update version**
   ```json
   // package.json
   "version": "1.2.0"
   ```

2. **Update CHANGELOG**
   ```markdown
   ## [1.2.0] - 2025-10-25
   ### Added
   - Slack connector
   ### Fixed
   - Search timeout issue
   ```

3. **Create tag**
   ```bash
   git tag -a v1.2.0 -m "Release version 1.2.0"
   git push origin v1.2.0
   ```

4. **Build artifacts**
   ```bash
   npm run build
   npm run package
   ```

---

## Community Guidelines

### Be Respectful
- Constructive feedback
- Assume good intentions
- Welcome newcomers

### Communication
- GitHub Issues for bugs/features
- Discussions for questions
- Discord for chat (if available)

### Attribution
- Credit contributors
- Acknowledge inspirations
- Link to related work

---

## Questions?

- 📧 Email: support@localbrain.dev
- 💬 GitHub Discussions
- 🐦 Twitter: @localbrain

Thank you for contributing! 🎉
