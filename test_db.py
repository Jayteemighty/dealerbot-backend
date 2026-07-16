import psycopg2

conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="YOUR_PASSWORD",
    host="db.lhzdtcmtwlitnckzxnoh.supabase.co",
    port="5432",
    sslmode="require"
)

print("Connected!")

conn.close()