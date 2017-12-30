# ek_twitter
A twitter mining tool based on python (tweepy & textblob) and Elasticsearch / Kibana

## Requirements
Docker and Docker Compose installed.

## "Quick + Dirty" HowTo
* Save a copy of ./config/tweepy/default.config.py as ./config/tweepy/config.py and replace the default values with your project specific values.
* Save a copy of ./default.env as ./.env and replace the default values with your environment specific values.
* Start mining by execute at the root of this directory "docker-compose up -d"

That's it.
