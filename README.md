# Walk 

An agentic coding system that generates production-ready code using AI.

## Features

- Context management system for code and documentation
- Pipeline-based code generation process
- Human-in-the-loop feedback system

## Installation

```bash
# Clone the repository
git clone https://github.com/leejavaa/walk-backend.git
cd walk-backend 

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

## Configuration

Create a `.env` file in the root directory with the following variables:

```
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=walk
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4
```

## Usage

```bash
# Run the CLI
walk --help
```

## Development

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only end-to-end tests
pytest -m e2e
```

## License

MIT