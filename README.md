# affbot_back
Automated bot that made libarary reservations (reservations were made by people on affbot_front) as soon as a spot became vacant
Based on french reservations "Affluences" App's API (I "decoded" the API using debookee to read queries)
~100 users 
had to shut it down after request from Affluences Team.

#Tech
AWS (Lambda functions, step functions, dynamodb, rds) + Python + Serverless
Use psycopg2 folder when on AWS servers and import psycopg2 module when local use
