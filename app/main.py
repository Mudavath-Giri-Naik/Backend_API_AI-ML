# main.py
import os
import base64
import zipfile
import requests
import json
import pandas as pd
from io import BytesIO
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# === CONFIGURATION ===
API_KEY = "AIzaSyBVX_W2p5_WO4_PLYQPqRAmzj4CyWTLgc4"
API_URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# === CSV FILE STRUCTURE ===
COLUMNS = ["articleId", "title", "involvement", "past", "present", "points", "glossary"]

PROMPT_TEXT = """
Task: Extract all **news articles this is must and should you need to extract all articles except ads** from the given newspaper image. Return the output strictly in **JSON format** as a JSON array. Each news article must follow the structure and rules given below.

The format for each article should be:

{
  "articleId": <number>,  
  "title": "<exact title shown in the newspaper image>",

  "involvement": "<List all people, organizations, or groups involved in the article. For each one, write in this format — its name (don't include this label ,mention directly real name): a simple explanation of about it. Use very simple and short sentences.>",

  "past": "<Write a paragraph (minimum 4 lines) explaining the background or past events that led to this news. Use factual and accurate information. Use the internet if needed to get correct context. Write in very simple and clear words — like explaining to someone with no prior knowledge. Do not use bullet points — this should be a short paragraph.>",

  "present": "<Write a detailed paragraph (maximum 10 lines) summarizing what is happening now according to the article. Explain the full content of the article clearly. Keep it short and simple but cover everything. Do not use bullet points — this should be a descriptive paragraph.>",

  "points": [
    "<you should give minimum 5 important points in very simple words. These points should help students preparing for government exams like UPSC, SSC, etc. Each point must be clearly explained and easy to understand. End each point with a full stop.>"
  ],

  "glossary": { (you should give minimum 5 english words only not persons or organisation names these should be covered in Involvement section)
    "<word1>": "<simple meaning or explanation>",
    "<word2>": "<simple meaning or explanation>",
    "<abbreviation1>": "<full form and what it means in simple words>",
    "<...>": "<...>"
  }
}

Important Guidelines:

1. The final result must be a **JSON array** — one object per news article.
2. **title**: Must match exactly as shown in the newspaper image. Do not modify, fix, or translate it.
3. **involvement**: don't label as name or role etc just mention name directly-about it, List and explain all people, organizations, or entities mentioned in the article. Keep explanations short and very simple.
4. **past**: Give a short paragraph with 4 or more lines explaining past events related to the article. Keep it factual and easy to read.
5. **present**: Describe the current news in up to 10 lines. This must be a paragraph that clearly explains everything in the article in simple words.
6. **points**: minimum 5 key takeaways in very easy English. These should help someone preparing for exams like UPSC or SSC. Each point should be meaningful and informative.
7. **glossary**: This is a mandatory object. You must minimum 5 terms and above from each article. These can be:
   - Difficult or unique English words from the article (with simple meanings)
   - Abbreviations with full forms and simple explanations
   - Key terms or names (with short descriptions)
   - don't consider person or group or organisation names glossary should have only english words and its meanings which are extracted from that news article
"""

# === MIDDLEWARE (CORS) ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === PROCESS ZIP FILE ===
def process_zip(zip_bytes: bytes, zip_name: str) -> str:
    zip_path = os.path.join(UPLOAD_FOLDER, zip_name)
    with open(zip_path, "wb") as f:
        f.write(zip_bytes)

    csv_file_path = os.path.splitext(zip_path)[0] + "_articles.csv"
    if not os.path.exists(csv_file_path):
        pd.DataFrame(columns=COLUMNS).to_csv(csv_file_path, index=False)

    article_id_counter = pd.read_csv(csv_file_path).shape[0] + 1

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for file_name in sorted(zip_ref.namelist()):
            if file_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                with zip_ref.open(file_name) as file:
                    encoded_image = base64.b64encode(file.read()).decode("utf-8")

                payload = {
                    "contents": [
                        {
                            "parts": [
                                {"text": PROMPT_TEXT},
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

                        if result_text.startswith("```json"):
                            result_text = result_text.strip("`").split("json")[-1].strip()
                        elif result_text.startswith("```"):
                            result_text = result_text.strip("`").split("\n", 1)[-1].strip()

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
                        print(f"❌ Error: {e}")
                        print("Raw output:", result_text[:500])
                else:
                    print(f"❌ API Error {response.status_code}: {response.text}")

    return csv_file_path

# === ROUTES ===

@app.post("/upload-zip/")
async def upload_zip(file: UploadFile = File(...)):
    content = await file.read()
    csv_path = process_zip(content, file.filename)
    return {"message": "✅ File processed", "csv_file": os.path.basename(csv_path)}

@app.get("/get-csv/")
def get_csv(file_name: str):
    file_path = os.path.join(UPLOAD_FOLDER, file_name)
    if os.path.exists(file_path):
        return FileResponse(path=file_path, filename=file_name, media_type='text/csv')
    return {"error": "File not found"}
