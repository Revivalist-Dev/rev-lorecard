# lorebook_creator

## Setup

```bash
uv venv --python 3.10
uv pip install -r requirements.txt
```

## Local Development

To start the local PostgreSQL database, run the following command:

```bash
docker-compose up -d
```

The database will be available at `postgresql://user:password@localhost:5432/lorebook_creator`.

Create tables:
```bash
python src/init_db.py
```

To stop the database, run:

```bash
docker-compose down
```

## Start the Application

To start the application, run the following command:

```bash
python src/main.py
```

## Running Tests

To run the tests, use the following command:

```bash
python -m pytest
```
