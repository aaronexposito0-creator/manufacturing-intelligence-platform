# Interview Cheatsheet

## “Walk me through the project.”

> I wanted to demonstrate the intersection of engineering and analytics, so I built a synthetic manufacturing-intelligence product rather than a generic dashboard. I generated reproducible production, downtime and quality data, modelled it in SQLite, centralised KPI logic in Python and SQL, then built an interactive Streamlit application that identifies the plant constraint, explains the loss pattern and quantifies improvement scenarios.

## “Why did you use synthetic data?”

> I wanted a portfolio project that was safe to publish publicly. I intentionally avoided using any employer or customer data. The generator creates deterministic patterns so the analysis is still realistic and reproducible.

## “What is the most important technical decision?”

> Not averaging OEE. OEE is non-additive, so I recompute Availability, Performance and Quality from their underlying sums at the current filter level, then multiply those components. That avoids misleading results when order sizes and runtimes differ.

## “Why SQLite?”

> It keeps the project self-contained and deployable without cloud credentials while still demonstrating dimensional modelling, SQL views, indexing and a separation between storage and presentation. In production I would map the same model to PostgreSQL, SQL Server, Snowflake or another managed warehouse depending on the environment.

## “Why Streamlit instead of only Power BI?”

> I wanted a live public application that a recruiter can open without a Power BI account. Streamlit also lets me demonstrate Python application logic and scenario modelling. I still keep the data model Power BI-ready and document the equivalent measures.

## “How does the opportunity estimate work?”

> For the worst asset, I take its target OEE and observed Performance and Quality. I solve for the Availability required to reach that target. I then convert the recovered productive time into additional good units using the observed cycle-time mix and value those units using observed gross contribution per good unit. I explicitly label it as a sizing scenario rather than guaranteed savings.

## “What would you add in a real company?”

- ERP / MES / CMMS ingestion instead of CSV.
- Incremental pipelines and data-quality monitoring.
- Role-based access and SSO.
- SPC / process-capability metrics where measurement data is available.
- Real cost-accounting logic validated with Finance.
- Alerting and action ownership.
- Production-grade database and orchestration.

## “What can you say you personally did?”

You can truthfully say you built and can explain the project, but be prepared to demonstrate it. Before interviews, be able to explain:

- each table and its grain;
- OEE formula and why weighting matters;
- one SQL view;
- one Python KPI function;
- the constraint-opportunity assumption;
- how the scenario model converts A/P/Q changes into output.

Do **not** claim that the synthetic results are real employer savings or that the app is an ML prediction system.
