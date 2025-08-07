# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
This is a crewAI-based market research system that uses multiple AI agents to analyze market trends and generate reports. The project uses Python 3.10-3.13 with UV for dependency management.

## Common Commands

### Running the Project
```bash
crewai run                    # Run the crew with default inputs (AI LLMs topic)
crewai install               # Install dependencies using crewAI CLI
uv sync                      # Install dependencies using UV
```

### Development Scripts (via pyproject.toml)
```bash
market_research              # Run main crew execution
run_crew                     # Alias for main execution
train <n_iterations> <filename>  # Train the crew
replay <task_id>             # Replay specific task execution  
test <n_iterations> <eval_llm>   # Test crew with evaluation
```

### Environment Setup
- Create `.env` file with `OPENAI_API_KEY`
- Python >=3.10,<3.14 required

## Architecture

### Core Components
- **MarketResearch crew**: Main crew class in `src/market_research/crew.py` using crewAI decorators
- **Agent configuration**: `src/market_research/config/agents.yaml` defines researcher and reporting_analyst agents
- **Task configuration**: `src/market_research/config/tasks.yaml` defines research and reporting tasks
- **Main execution**: `src/market_research/main.py` with run/train/replay/test functions

### Agent Structure
The current configuration in `config/agents.yaml` and `config/tasks.yaml` shows a mismatch - agents are defined for market research with ticker symbols, but main.py uses 'AI LLMs' topic. The project appears to be transitioning between different use cases.

### Custom Tools
- Template custom tool in `src/market_research/tools/custom_tool.py`
- Tools can be added to agents via the crewAI framework

### Output
- Generates `report.md` in project root with research findings
- Uses sequential process by default (can be changed to hierarchical)

### Knowledge Sources
- `knowledge/user_preference.txt` contains user profile information that can be leveraged by agents