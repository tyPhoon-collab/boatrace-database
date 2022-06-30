import sqlite3

import pandas as pd

from main import DB_NAME

con = sqlite3.connect(DB_NAME)
cur = con.cursor()

# for row in cur.execute("SELECT * FROM race"):
#     print(row)

# for row in cur.execute("SELECT * FROM odds"):
#     print(row)

# for row in cur.execute("SELECT * FROM env"):
#     print(row)

# a = pd.read_sql("SELECT * FROM race WHERE レースID LIKE '2020-09-28%'", con)
# a = pd.read_sql("SELECT * FROM odds WHERE レースID LIKE '2020-09-29%'", 
# con)
# a = pd.read_sql("""SELECT * FROM odds
#                 WHERE 
#                 レースID LIKE '2020-09-28%' OR
#                 レースID LIKE '2020-09-29%' OR
#                 レースID LIKE '2020-09-30%'
#                 """, con)
# print(a)

# env = pd.read_sql("SELECT * FROM env", con)
# result = pd.read_sql("SELECT * FROM result", con)
# schedule = pd.read_sql("SELECT * FROM schedule", con)

# race = pd.merge(pd.merge(env, result, on=["レースID"]), schedule, on=["レースID", "選手登番"])

race = pd.read_sql("SELECT * FROM race", con)

print(race.columns)

con.commit()
con.close()
