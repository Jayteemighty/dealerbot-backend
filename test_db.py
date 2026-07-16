import psycopg2

conn = psycopg2.connect(
    dbname="postgres",
    user="postgres.lhzdtcmtwlitnckzxnoh",
    password="FzgSYEc4QWM.fe-",
    host="aws-0-eu-west-1.pooler.supabase.com",
    port="5432",
    sslmode="require"
)

print("Connected!")

conn.close()