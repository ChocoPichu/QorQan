# Contributing to QorQan

Thanks for your interest in contributing!

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/QorQan.git`
3. Create a virtual environment: `python -m venv .venv`
4. Activate it and install dependencies: `pip install -r requirements.txt`
5. Create a `.env` file from `.env.example` and fill in your tokens

## Code Standards

- **Linter:** We use `ruff`. Run `ruff check` before committing.
- **Formatter:** Run `ruff format` to format your code.
- **Tests:** Add or update tests in the `tests/` directory. Run `pytest -v` to verify.
- **Python version:** 3.10+

## Pull Request Process

1. Create a feature branch: `git checkout -b feat/your-feature`
2. Make your changes
3. Run `ruff check` and `pytest -v` — both must pass
4. Commit with a clear message: `feat: description` or `fix: description`
5. Push and open a Pull Request

## Code of Conduct

Be respectful and constructive. This is a school project — everyone is learning.