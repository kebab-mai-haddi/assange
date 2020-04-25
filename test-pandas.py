import pandas as pd

df = pd.read_csv('data_repository/Modi.csv', header=0)

df = df[1:]
print(df.head(5))

df.write_csv(header=False)