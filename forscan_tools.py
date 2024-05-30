import os
import struct
import csv
from datetime import datetime

def list_abt_files(directory):
    abt_files = []
    for file_name in os.listdir(directory):
        if file_name.endswith('.abt'):
            parts = file_name.split('_')
            if len(parts) >= 4:
                vin = parts[0]
                system = parts[1]
                date_str = parts[2]
                time_str = parts[3].split('.')[0]
                try:
                    dt = datetime.strptime(date_str + time_str, '%Y%m%d%H%M%S')
                    abt_files.append((file_name, vin, system, dt))
                except ValueError:
                    continue
    abt_files.sort(key=lambda x: x[3], reverse=True)
    return abt_files

def prompt_user_to_select_file(abt_files):
    print("Please select a file to parse:")
    for idx, (file_name, vin, system, dt) in enumerate(abt_files):
        print(f"{idx + 1}: {file_name} (VIN: {vin}, System: {system}, Date: {dt.strftime('%Y-%m-%d %H:%M:%S')})")
    
    choice = input("Enter the number of the file you want to parse: ")
    try:
        choice_idx = int(choice) - 1
        if 0 <= choice_idx < len(abt_files):
            return abt_files[choice_idx][0]
        else:
            print("Invalid choice. Exiting.")
            exit()
    except ValueError:
        print("Invalid input. Exiting.")
        exit()

def read_abt_file(file_path):
    parsed_data = []

    with open(file_path, 'rb') as file:
        # Example: Read first 4 bytes as an integer (adjust according to actual structure)
        data = file.read(4)
        value = struct.unpack('I', data)[0]
        parsed_data.append(['First Integer', value])

        # Continue reading and parsing the rest of the file as needed
        # For demonstration, let's assume we read another integer
        data = file.read(4)
        another_value = struct.unpack('I', data)[0]
        parsed_data.append(['Second Integer', another_value])

        # Add more parsing logic based on the file structure
        # ...

    return parsed_data

def write_to_csv(parsed_data, csv_file_path):
    with open(csv_file_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Description', 'Value'])
        writer.writerows(parsed_data)

if __name__ == "__main__":
    abt_directory = 'C:\\source\\forscan_tools\\abt'
    csv_file_path = 'output_file.csv'
    
    abt_files = list_abt_files(abt_directory)
    if not abt_files:
        print("No .abt files found in the directory.")
        exit()
    
    selected_file = prompt_user_to_select_file(abt_files)
    abt_file_path = os.path.join(abt_directory, selected_file)
    
    parsed_data = read_abt_file(abt_file_path)
    write_to_csv(parsed_data, csv_file_path)
    print(f"Processed {selected_file}")
