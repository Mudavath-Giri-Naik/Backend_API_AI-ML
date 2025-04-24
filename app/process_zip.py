import os
import base64
import zipfile
import requests
import json
import pandas as pd
from io import BytesIO
from .config import API_KEY, API_URL, TEMP_FOLDER

def process_zip_file(zip_file_path):
    # Initialize the CSV file and columns
    csv_file_path = os.path.splitext(zip_file_path)[0] + "_articles.csv"
    columns = ["articleId", "title", "involvement", "past", "present", "points", "glossary"]
    
    if not os.path.exists(csv_file_path):
        pd.DataFrame(columns=columns).to_csv(csv_file_path, index=False)

    article_id_counter = pd.read_csv(csv_file_path).shape[0] + 1

    # Process the images inside the ZIP file
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        for file_name in sorted(zip_ref.namelist()):
            if file_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                with zip_ref.open(file_name) as file:
                    encoded_image = base64.b64encode(file.read()).decode("utf-8")

                payload = {
                    "contents": [
                        {
                            "parts": [
                                {"text": "<your original prompt here>"},
                                {
                                    "inline_data": {
                                        "mime_type": "image/png",
                                        "data": encoded_image
                                    }
                                }
                            ]
                        }
                    ]
                }

                headers = {"Content-Type": "application/json"}
                response = requests.post(API_URL, headers=headers, json=payload)

                if response.status_code == 200:
                    try:
                        result_text = response.json()['candidates'][0]['content']['parts'][0]['text'].strip()

                        articles = json.loads(result_text)
                        rows = []

                        for art in articles:
                            rows.append({
                                "articleId": article_id_counter,
                                "title": art.get("title", ""),
                                "involvement": art.get("involvement", ""),
                                "past": art.get("past", ""),
                                "present": art.get("present", ""),
                                "points": "\n".join(art.get("points", [])),
                                "glossary": json.dumps(art.get("glossary", {}))
                            })
                            article_id_counter += 1

                        pd.DataFrame(rows).to_csv(csv_file_path, mode='a', header=False, index=False)
                    except Exception as e:
                        print(f"❌ Error parsing response from {file_name}: {e}")
                else:
                    print(f"❌ API Error {response.status_code}: {response.text}")
    
    return csv_file_path
