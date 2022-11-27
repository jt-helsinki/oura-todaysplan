# Oura Syncer

Syncs data from the Oura Ring API to Today's Plan API.

## Environment Variables

* OURA_API_KEY
* TODAYS_PLAN_API_KEY
* TODAYS_PLAN_BASE_URL=whats.todaysplan.com.au
* TODAYS_PLAN_USERNAME
* TODAYS_PLAN_PASSWORD
* ATHLETE_EMAIL

# Startup Jupyter for experimenting

From the root of this project, run this command in the terminal:

`jupyter-lab  --ip=0.0.0.0 `

# Run the syncer

`python ./oura_todays_plan_sync.py`

It should work
