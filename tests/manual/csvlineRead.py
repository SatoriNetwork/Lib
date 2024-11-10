''' turns out it's not faster to read in a single line from a csv file... '''
import pandas as pd
import time

# Generate a DataFrame with 1 million rows
data = {'Column1': range(1, 10000001)}
df = pd.DataFrame(data)

# Timing the process of saving to CSV
start_time = time.time()
csv_file = 'data.csv'
df.to_csv(csv_file, float_format='%.10g', index=False)
save_time = time.time() - start_time
print(f"Time taken to save to CSV: {save_time} seconds")

# Timing the process of reading from CSV
start_time = time.time()
df_read = pd.read_csv(csv_file)
read_time = time.time() - start_time
print(f"Time taken to read from CSV: {read_time} seconds")

start_time = time.time()
x = pd.read_table(
    csv_file,
    sep=",",
    index_col=0,
    header=None,
    skiprows=10000001-6,
    # skipfooter=end, # slicing is faster; since using c engine
    # engine='python', # required for skipfooter
)
print(x.iloc[0:2])
read_time = time.time() - start_time
print(f"Time taken to read 1 line from CSV: {read_time} seconds")
