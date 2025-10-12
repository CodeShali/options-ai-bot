# Contributing to Options Trading AI Bot

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Follow best practices

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in Issues
2. Create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - System information (OS, Python version)
   - Relevant log excerpts

### Suggesting Enhancements

1. Check if the enhancement has been suggested
2. Create an issue describing:
   - The problem you're trying to solve
   - Your proposed solution
   - Any alternatives considered
   - Potential impact on existing functionality

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Follow the existing code style
   - Add docstrings to functions and classes
   - Update documentation if needed
   - Add tests for new functionality

4. **Test your changes**
   ```bash
   # Run connection tests
   python scripts/test_connection.py
   
   # Test manually
   python main.py
   ```

5. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add new feature description"
   ```
   
   Use conventional commit messages:
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation changes
   - `style:` - Code style changes (formatting)
   - `refactor:` - Code refactoring
   - `test:` - Adding tests
   - `chore:` - Maintenance tasks

6. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create a Pull Request**
   - Provide a clear description
   - Reference any related issues
   - Explain what you changed and why

## Development Setup

1. **Clone your fork**
   ```bash
   git clone https://github.com/your-username/options-AI-BOT.git
   cd options-AI-BOT
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your test credentials
   ```

## Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Write descriptive variable and function names
- Keep functions focused and small
- Add docstrings to all public functions and classes
- Use async/await for I/O operations

### Example Function

```python
async def process_trade(
    symbol: str,
    quantity: int,
    action: str
) -> Dict[str, Any]:
    """
    Process a trade order.
    
    Args:
        symbol: Stock symbol
        quantity: Number of shares
        action: Trade action ('buy' or 'sell')
        
    Returns:
        Trade result dictionary
        
    Raises:
        ValueError: If action is invalid
    """
    if action not in ['buy', 'sell']:
        raise ValueError(f"Invalid action: {action}")
    
    # Implementation here
    return {"status": "success"}
```

## Testing Guidelines

- Test with paper trading first
- Verify all API connections work
- Test error handling
- Check edge cases
- Ensure no sensitive data in logs

## Documentation

- Update README.md for user-facing changes
- Update docstrings for code changes
- Add examples for new features
- Keep SETUP_GUIDE.md current

## Project Structure

When adding new features, follow the existing structure:

```
options-AI-BOT/
├── agents/          # Add new agents here
├── api/             # API endpoints
├── bot/             # Discord bot commands
├── config/          # Configuration
├── services/        # External service integrations
├── utils/           # Utility functions
└── scripts/         # Standalone scripts
```

## Areas for Contribution

### High Priority
- [ ] Additional technical indicators
- [ ] Backtesting framework
- [ ] Web dashboard
- [ ] More comprehensive tests
- [ ] Performance optimizations

### Medium Priority
- [ ] Additional order types
- [ ] Portfolio optimization
- [ ] Multi-timeframe analysis
- [ ] Email notifications
- [ ] Telegram bot support

### Low Priority
- [ ] Machine learning models
- [ ] Advanced options strategies
- [ ] Social sentiment analysis
- [ ] News integration

## Questions?

- Open an issue for questions
- Check existing documentation
- Review closed issues for similar questions

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for contributing! 🚀
