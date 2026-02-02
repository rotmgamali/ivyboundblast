
# Ivybound System Quickstart

To get this system running in production, follow these steps.

## 1. Prerequisites (What You Need)

- **OpenAI API Key**: You need a valid key starting with `sk-...`.
- **Target List**: A CSV file (e.g., `schools.csv`) with at least a `Website` column.
- **Python 3.9+** OR **Docker**: Installed on your machine.

## 2. Configuration

Create a `.env` file in the project root (`/Users/mac/Desktop/Ivybound/.env`):

```bash
# Required
OPENAI_API_KEY=sk-your-key-here

# Optional (Defaults provided in config.py)
RATE_LIMIT=1.0
DAILY_SEND_LIMIT=100
PROMETHEUS_PORT=8000
```

## 3. Running Locally (Development)

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Prepare Input Data:**
   Ensure your CSV file is ready (e.g., `input_websites.csv`).

3. **Run Pipeline:**
   ```bash
   python pipeline.py input_websites.csv
   ```

4. **Monitor:**
   - View logs in terminal.
   - Check `data/scraped/results_YYYYMMDD.csv` for success.
   - Check `data/dlq/` for any failed records.
   - Metrics available at `http://localhost:8000`.

## 4. Running with Docker (Production)

1. **Build Image:**
   ```bash
   docker build -t ivybound-scraper .
   ```

2. **Run Container:**
   Mount your local `.env` and data files:
   ```bash
   docker run -d \
     --env-file .env \
     -v $(pwd)/data:/app/data \
     -v $(pwd)/input_websites.csv:/app/input_websites.csv \
     -p 8000:8000 \
     ivybound-scraper
   ```

## 5. Deployment Checklist (Before Scale)

- [ ] **Validate API Limits**: Ensure your OpenAI tier supports the volume (e.g., Tier 2+ for high throughput).
- [ ] **Proxies**: If scraping >1000 sites/hour, configure proxy rotation in `SchoolScraper` (currently direct).
- [ ] **Mailreef/Smartlead**: Ensure domains are warmed up if you plan to pipe output directly to sending.
