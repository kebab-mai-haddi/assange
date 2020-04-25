import pandas as pd
import subprocess

topic = input("Please enter the name of the topic \n")
file_name = "data_repository/{}.csv".format(topic.replace(' ', '_'))

subprocess.run(
    [
        "mongoexport",
        "--collection={}".format(topic),
        "--db=phase3",
        "--out={}".format(file_name),
        "--type=csv",
        "--fields=tweet,sentiment_label"
    ]
)

df = pd.read_csv(file_name)
df.to_csv(path_or_buf=file_name, header=False, index=False)
