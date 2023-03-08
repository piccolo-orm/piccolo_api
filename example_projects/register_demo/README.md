# Register demo

This project demos how to use the `register` endpoint, along with CAPTCHAs.

## Setup

### Install requirements

```bash
pip install -r requirements.txt
```

### Create database

Make sure a Postgres database exists, called 'piccolo_api_captcha'. See
`piccolo_conf.py` for the full details.

### Run migrations

```
piccolo migrations forwards all
```

## Run the app

```bash
python main.py
```

For the available URLs, see `app.py`. For example, `http://localhost:8000/register/hcaptcha`.
