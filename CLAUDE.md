# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
This is a crewAI-based market research system that uses multiple AI agents to analyze financial markets and generate reports. The system scrapes Yahoo Finance for stock ticker news and provides comprehensive market analysis through a sequential agent workflow.

## Common Commands

### Running the Project
```bash
crewai run                    # Run the crew with default TLN ticker
crewai install               # Install dependencies using crewAI CLI
uv sync --all-groups         # Install all dependencies including dev tools
```

### Development Scripts (via pyproject.toml)
```bash
market_research              # Run main crew execution
run_crew                     # Alias for main execution
train <n_iterations> <filename>  # Train the crew
replay <task_id>             # Replay specific task execution  
test <n_iterations> <eval_llm>   # Test crew with evaluation
```

### Development Tools (via justfile)
```bash
just install                 # Install dependencies with all groups
just fmt                     # Format code with ruff
just push "commit message"   # Git add, commit, and push
```

### Code Quality
```bash
uv run ruff check --fix .    # Run linter and fix issues
ruff format .                # Format code
```

### Environment Setup
- Create `.env` file with `OPENAI_API_KEY`
- Python >=3.10,<3.14 required
- Playwright browser installation: `playwright install`

## Architecture

### Agent Workflow (Sequential Process)
1. **market_news_scraper**: Gathers latest news from Yahoo Finance for ticker
2. **market_researcher**: Analyzes market trends, news, and fundamentals 
3. **data_analyst**: Creates detailed reports with actionable recommendations

### Core Components
- **MarketResearch crew**: Main crew class in `src/market_research/crew.py` using crewAI @decorators
- **Agent configuration**: `src/market_research/config/agents.yaml` defines 3 agents with ticker interpolation
- **Task configuration**: `src/market_research/config/tasks.yaml` defines 3 sequential tasks
- **Main execution**: `src/market_research/main.py` with hardcoded TLN ticker

### Custom Tools
- **YahooNewsScraperTool**: Primary tool in `src/market_research/tools/yahoo_news_scraper.py`
  - Uses Playwright for web scraping Yahoo Finance
  - Scrapes headlines, summaries, and detailed article content
  - Configurable max articles and content length
  - Only assigned to the market_news_scraper agent

### Key Dependencies
- `crewai[tools]`: Multi-agent framework with built-in tools
- `playwright`: Web scraping for dynamic content
- `beautifulsoup4`: HTML parsing
- `requests`: HTTP requests
- `ruff`: Code formatting and linting

### Configuration Notes
- Default ticker is "TLN" in `main.py:26` and `main.py:40`
- Output generates `report.md` in project root
- Agent roles focus on financial market analysis rather than general AI topics
- Sequential processing ensures each agent builds on previous work

### Knowledge Sources
- `knowledge/user_preference.txt` contains user profile information that can be leveraged by agents