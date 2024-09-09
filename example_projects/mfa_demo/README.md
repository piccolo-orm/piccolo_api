# MFA demo

This project demos how to use the MFA with the `session_login` endpoint.

## Setup

### Install requirements

```bash
pip install -r requirements.txt
```

### Create database

Make sure a Postgres database exists, called 'piccolo_api_mfa'. See
`piccolo_conf.py` for the full details.

### Run migrations

```
piccolo migrations forwards all
```

## Run the app

```bash
python main.py
```
