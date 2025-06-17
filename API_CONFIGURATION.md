# Usage Instructions for API Configuration

## TextExtract API Environment Configuration

TextExtract now supports switching between development (local) and production (hosted) APIs through a simple environment variable.

### Running the Application

Two batch files have been created for your convenience:

- **run_dev.bat** - Runs TextExtract using the local development API (`http://localhost:5000`)
- **run_prod.bat** - Runs TextExtract using the production API (`https://textextract.onrender.com`)

### Manual Environment Configuration

If you prefer to set the environment variable manually:

```bash
# For production API
$env:USE_PRODUCTION_API = "True"
python -m src.main

# For development API
$env:USE_PRODUCTION_API = "False"
python -m src.main
```

### API Configuration

The API URLs are centrally defined in `src/config.py`:

- Development API URL: `http://localhost:5000`
- Production API URL: `https://textextract.onrender.com`

If you need to change these URLs, edit the `DEV_API_URL` and `PROD_API_URL` variables in this file.
