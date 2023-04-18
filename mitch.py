import pandas as pd
import time
import requests
import json
import os
from bs4 import BeautifulSoup
from csv import writer
import schedule
import pytz
from datetime import datetime

def get_nutrient_data(food_name, api_key):
    url = f"https://api.nal.usda.gov/fdc/v1/foods/search?api_key={api_key}&query={food_name}"
    response = requests.get(url)

    max_retries = 3
    retries = 0

    while retries < max_retries:
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            if data['totalHits'] > 0:
                return data['foods'][0]['foodNutrients']
            else:
                return None
        elif response.status_code == 500:
            retries += 1
            time.sleep(5)  # Wait for 5 seconds before retrying
        else:
            raise Exception("API request failed with status code", response.status_code)

def extract_nutrient_values(nutrients):
    target_nutrients = {
        "Energy": "1008",
        "Total lipid (fat)": "1004",
        "Fatty acids, total saturated": "1258",
        "Cholesterol": "1253",
        "Carbohydrate, by difference": "1005",
        "Fiber, total dietary": "1079",
        "Sugars, total including NLEA": "2000",
        "Protein": "1003"
    }
    extracted_values = {}

    for nutrient in nutrients:
        nutrient_id = str(nutrient['nutrientId'])
        if nutrient_id in target_nutrients.values():
            nutrient_name = [name for name, id in target_nutrients.items() if id == nutrient_id][0]
            extracted_values[nutrient_name] = nutrient['value']

    return extracted_values

def main():
    print("starting...")

    api_key = "WcPhrCWFp3tkk1Dua7ukUIHphwEHibgBSvMNcndv"
    # Get the current script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))

    url = "https://willamette.cafebonappetit.com/"
    page = requests.get(url)

    soup = BeautifulSoup(page.content, 'html.parser')
    lists = soup.find_all('div', class_="site-panel__daypart-item")

    csv_file_path = os.path.join(script_dir, "goudy.csv")
    with open(csv_file_path, 'w', encoding='utf8', newline='') as f:
        thewriter = writer(f)
        header = ['Item', 'Station', 'Sides']
        thewriter.writerow(header)
        #loop through the lists and each time we find a title of each div
        for list in lists:
            title = list.find('button', class_="site-panel__daypart-item-title").text.strip()
            station = list.find('div', class_="site-panel__daypart-item-station").text.strip()
            sides = list.find('div', class_="site-panel__daypart-item-sides")
            #add if it's gluten-free or vegan


            #because not all dishes have sides, so will be 'NoneType' error if it's not checked
            if sides:
                sides_text = sides.text.strip().replace('\n', '').replace('\t', '')
            else:
                sides_text = ""
            
            info = [title, station.replace("@", ""), sides_text]
            #print([title, station.replace("@", ""), sides_text])
            thewriter.writerow(info)

    # Join the directory with the file name
    file_name = os.path.join(script_dir, "goudy.csv")

    # Read the CSV file
    df = pd.read_csv(file_name)

    USDA = {}

    for food_name in df['Item']:
        nutrients = get_nutrient_data(food_name, api_key)
        if nutrients:
            extracted_nutrients = extract_nutrient_values(nutrients)
            USDA[food_name] = {
                "Calories": extracted_nutrients.get("Energy", None),
                "Total Fat": extracted_nutrients.get("Total lipid (fat)", None),
                "Total Sat Fat": extracted_nutrients.get("Fatty acids, total saturated", None),
                "Cholesterol": extracted_nutrients.get("Cholesterol", None),
                "Total Carbs": extracted_nutrients.get("Carbohydrate, by difference", None),
                "Fiber": extracted_nutrients.get("Fiber, total dietary", None),
                "Sugars": extracted_nutrients.get("Sugars, total including NLEA", None),
                "Protein": extracted_nutrients.get("Protein", None),
            }
        else:
            print(f"No nutrient data found for {food_name}")

    json_file_path = os.path.join(script_dir, "usda.json")
    # Save the food data as a JSON file
    with open(json_file_path, 'w') as json_file:
        json.dump(USDA, json_file, indent=4)
    print("done...")


# Schedule the job to run every day
schedule.every().day.at("14:01").do(main)
main()
while True:
    schedule.run_pending()
    time.sleep(1)
