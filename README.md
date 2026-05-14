# AI Infrastructure vs Platform Dashboard

This is a Streamlit dashboard that compares AI infrastructure-related tickers against a platform-company basket.

## Default comparison

Infrastructure:
- SOXX
- QQQ

Platform basket:
- GOOGL
- MSFT
- AMZN
- META

## What the dashboard shows

- Relative strength chart
- Current index value
- 1-week, 1-month, and 3-month changes
- Simple interpretation of the recent trend
- CSV download button

## How to run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## How to deploy on Streamlit Community Cloud

1. Create a GitHub repository.
2. Upload these files:
   - app.py
   - requirements.txt
   - README.md
3. Go to Streamlit Community Cloud.
4. Connect the GitHub repository.
5. Select `app.py` as the main file.
6. Deploy.

After deployment, the dashboard can be opened through a web link.
