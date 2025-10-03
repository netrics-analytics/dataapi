import pandas as pd
import snowflake.connector

# Domo Cred Prod Instance
clientID = '05d53070-8ad3-4196-a9d4-e330bc76e74b'
clientSecret = '15b3c6148dc6c5f1e1cbbc3f947f1eef7a5e63bdaa7840d66663f24693e369e1'
datasetID = '8f696fc2-0583-481c-8903-973e1aeb8647'

def getData(startDate, endDate, advertiserId = None):
    
    # Load the CSV file into a pandas DataFrame
    # data = pandas.read_csv("iMarketSolutions Conversion Journey Data Dump.csv")

    # Getting iMarketSolutions Convesion Journey Data
    conn = snowflake.connector.connect(
        user = "IMARKET_USR",
        password = "DataI$Cool2025",
        account = "hmimopy-dvb53256",
        warehouse = "PROD",
        database = "PROD",
        schema = "MART"
    )

    query = "SELECT * FROM IMARKET_CONVERSION_JOURNEY"
    conditions = []
    if startDate:
        conditions.append(f""" DATE("Conversion Time") >= '{startDate}' """)

    if endDate:
        conditions.append(f""" DATE("Conversion Time") < '{endDate}' """)

    if advertiserId:
        if isinstance(advertiserId, str):
            advertiserId = [advertiserId.strip()]  # Handling if it's a single string
        elif isinstance(advertiserId, list):
            advertiserId = [str(id).strip() for id in advertiserId]  # Ensure all elements are strings
        for adv_id in advertiserId:
            conditions.append(f""" "Advertiser ID" = '{adv_id}' """)

    query += " WHERE "
    if conditions:
        query += " AND ".join(conditions) + " AND "
    query += r""" ("Conversion Tracker" ILIKE '%Phone Call%' OR "Conversion Tracker" ILIKE '%Form Submit%' OR "Conversion Tracker" ILIKE '%SchedulerStarted%') """
    query += ";"
    print(query)
    cur = conn.cursor()
    cur.execute(query)
    dfs = []
    for batch_df in cur.fetch_pandas_batches():
        print(batch_df.shape)
        dfs.append(batch_df)
    cur.close()
    conn.close()
    data = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    data["Conversion Time"] = data["Conversion Time"].dt.strftime("%Y-%m-%dT%H:%M:%S%z")
    data["First Impression Time"] = data["First Impression Time"].dt.strftime("%Y-%m-%dT%H:%M:%S%z")
    return data

# getData('','','')


# import pandas
# import Cred

# def getDataFromSnowflake(startDate, endDate, advertiserId):
#     query = 'select * from DSP1.DSP1."iMarketSolutions Conversion Journey"'

#     # Add the WHERE clause only if conditions are provided
#     where_clauses = []

#     if startDate:
#         where_clauses.append(f"TO_DATE(\"Conversion Time\") >= '{startDate}'")

#     if endDate:
#         where_clauses.append(f"TO_DATE(\"Conversion Time\") <= '{endDate}'")

#     if advertiserId:
#         advertiser_ids = ','.join([f"'{id}'" for id in advertiserId])
#         where_clauses.append(f"\"Advertiser ID\" IN ({advertiser_ids})")

#     # If there are any where clauses, join them with 'AND' and prepend 'WHERE'
#     if where_clauses:
#         query += " WHERE " + " AND ".join(where_clauses)

#     engine = Cred.connectToSnowflake()
#     data = pandas.read_sql(query, engine)
#     return data