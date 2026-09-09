# Deployment — Streamlit Community Cloud

## Prerequisites

- Public GitHub repository.
- Repository name recommended: `manufacturing-intelligence-platform`.
- `app.py` at repository root.
- `requirements.txt` committed.
- `data/processed/manufacturing.db` committed.

No secrets, API keys or external databases are required.

## Steps

1. Push the complete project to GitHub.
2. Sign in to Streamlit Community Cloud with GitHub.
3. Choose **Create app**.
4. Select the repository and branch (`main`).
5. Main file path: `app.py`.
6. Deploy.
7. Open the public URL and verify every tab.

## Post-deployment checks

- Executive Overview loads without errors.
- Sidebar filters update every page.
- `M04` appears as the primary constraint in the default six-month window.
- Scenario Lab updates after slider changes.
- CSV downloads work.
- Mobile layout remains usable.

## Recommended final repository polish

After deployment:

- add the live Streamlit URL to the GitHub repository **About** field;
- add the same URL near the top of `README.md`;
- pin the repository on your GitHub profile;
- add the live URL to LinkedIn Featured and your CV.
