import subprocess

import pandas as pd
from pymongo import MongoClient

client = MongoClient()
db = client["phase3"]

print("Following topics are available in the repository: ")
for collection_ in db.list_collection_names():
    if "csv" in collection_:
        continue
    print(collection_)

topic = input("Please enter the name of the topic \n").replace(
    ' ', '_') + "_csv"
file_name = "data_repository/{}_assange.csv".format(topic.replace(' ', '_'))

subprocess.run(
    [
        "mongoexport",
        "--collection={}".format(topic),
        "--db=phase3",
        "--out={}".format(file_name),
        "--type=csv",
        "--fields=tweet,sentiment"
    ]
)

df = pd.read_csv(file_name)
df.to_csv(path_or_buf=file_name, index=False)
print("File is written at: {}".format(file_name))
