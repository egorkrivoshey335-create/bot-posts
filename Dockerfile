FROM python:3.11-slim

WORKDIR /app

# Install poetry
RUN pip install --no-cache-dir poetry==1.8.4

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Configure poetry to not create virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-interaction --no-ansi --no-root --only main

# Copy application code
COPY . .

# Install the project itself
RUN poetry install --no-interaction --no-ansi --only main

# Run migrations and start the bot
CMD ["sh", "-c", "alembic upgrade head && python -m app.main"]
