from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import pytesseract
import cv2
import numpy as np
import re
import json
from dotenv import load_dotenv
import os
import pymongo


@csrf_exempt
def upload_file(request):

    if request.method == 'POST' and request.FILES['file']:

        img = cv2.imdecode(np.frombuffer(request.FILES['file'].read(), np.uint8), cv2.IMREAD_UNCHANGED)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        cv2.imwrite("enhanced.jpg", thresh)
        ocr_text = pytesseract.image_to_string(thresh)

        lines = ocr_text.split("\n")

        isP = False

        for line in lines:
            if line.startswith("P") and len(line) >= 44:
                isP = True
                break

        mrz_lines = []

        if isP:
            for i in range(len(lines)):
                line = lines[i].strip()
                if len(line) >= 44 and line.startswith("P"):
                    mrz_lines.append(line)
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        mrz_lines.append(next_line)
                    break

        else:
            clahe = cv2.createCLAHE(clipLimit=1.0, tileGridSize=(10, 10))
            enhanced = clahe.apply(gray)
            blur = cv2.GaussianBlur(enhanced, (5, 5), 0)
            thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            morph = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
            cv2.imwrite("enhanced.jpg", morph)
            ocr_text2 = pytesseract.image_to_string(morph)
            lines2 = ocr_text2.split("\n")
            for i in range(len(lines2)):
                line = lines2[i].strip()
                if len(line) >= 44 and line.startswith("P"):
                    mrz_lines.append(line)
                    if i + 1 < len(lines2):
                        next_line = lines2[i + 1].strip()
                        mrz_lines.append(next_line)
                    break

        mrz_data = {}

        if len(mrz_lines) >= 2:
            mrz_line_1 = mrz_lines[0].replace(" ", "")
            mrz_line_2 = mrz_lines[1].replace(" ", "")
            print(mrz_line_1)
            print(mrz_line_2)

            print(mrz_line_2[14:19])

            name = re.search(r'^[A-Z<]+', mrz_line_1[5:]).group().replace('<', ' ')
            print(name)
            passport_number = re.search(r'^[A-Z0-9<]+', mrz_line_2[0:9]).group().replace('<', ' ')
            print(passport_number)
            nationality = re.search(r'^[A-Z]{3}', mrz_line_2[10:13]).group()
            print(nationality)
            date_of_birth = re.search(r'\d{6}', mrz_line_2[13:]).group()
            print(date_of_birth)
            gender = mrz_line_2[20]
            print(gender)
            expiration_date = re.search(r'\d{6}', mrz_line_2[20:]).group()
            print(expiration_date)
            personal_number = re.search(r'\d+', mrz_line_2[28:]).group()
            print(personal_number)

            load_dotenv()
            db_uri = os.environ.get('DB')
            client = pymongo.MongoClient(db_uri)
            db = client["Quarta"]
            passport = db["passport"]

            query = { "passportNumber": passport_number, "nationality": nationality, "dob": date_of_birth, "expiry": expiration_date, "gender": gender, "personalNumber": personal_number  }

            isRegistered = passport.find_one(query)
            print(isRegistered)

            if isRegistered is not None:
                return HttpResponse("User already exists")
            else:
                passportData = {
                    "name": name,
                    "passportNumber": passport_number,
                    "nationality": nationality,
                    "dob": date_of_birth,
                    "expiry": expiration_date,
                    "gender": gender,
                    "personalNumber": personal_number
                }

                data_saved = passport.insert_one(passportData)
                print(data_saved.acknowledged)

                if data_saved.acknowledged:
                    return HttpResponse("Passport data saved successfully")
                else:
                    return HttpResponse("Failed to save data")


            # json_data = json.dumps(mrz_data)

        # return HttpResponse(json_data)
