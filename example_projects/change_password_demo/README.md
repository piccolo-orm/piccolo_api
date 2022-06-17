# Change password demo

This project demos how to use the `change_password` endpoint.

## Setup

### Install requirements

```bash
pip install -r requirements.txt
```

### Create database

Make sure a Postgres database exists, called 'piccolo_api_change_password'. See
`piccolo_conf.py` for the full details.

### Run migrations

```
piccolo migrations forwards all
```

## Run the app

```bash
python main.py
```
