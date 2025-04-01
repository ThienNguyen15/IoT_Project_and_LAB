import threading
import subprocess
import os

current_directory = os.path.dirname(os.path.abspath(__file__))
python_interpreter = r"C:/Users/thien/AppData/Local/Programs/Python/Python310/python.exe"
scripts = [
    'Model1.py',
    'Model2.py'
]

def run_script(script):
    script_path = os.path.join(current_directory, script)
    try:
        subprocess.run([python_interpreter, script_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error")

threads = []
for script in scripts:
    thread = threading.Thread(target=run_script, args=(script,))
    threads.append(thread)
    thread.start()

for thread in threads:
    thread.join()

# import pandas as pd
# import random
# file_path = r"C:/GIT/IOT LAB/test.csv"
# df = pd.read_csv(file_path)

# num_rows = len(df)
# temperature_values = [round(random.uniform(15, 24), 4) for _ in range(num_rows)]

# df['Indoor_temperature_room'] = temperature_values


# df.to_csv(file_path, index=False)

# print(f"✅ 'Indoor_temperature_room' ({num_rows}) test.csv")
