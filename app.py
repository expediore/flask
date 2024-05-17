from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import random
import time
from pymongo import MongoClient
import certifi
from datetime import datetime, timezone
import base64
import os
from flask_cors import CORS



def svg_to_data_url(svg_data):
    # SVG 데이터를 Base64로 인코딩
    base64_encoded_svg = base64.b64encode(svg_data.encode('utf-8')).decode('utf-8')
    return f'data:image/svg+xml;base64,{base64_encoded_svg}'

app = Flask(__name__)
CORS(app)

scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('hwik_key.json', scope)
client = gspread.authorize(creds)
sheet = client.open('auto_curation').get_worksheet(0)  # 스프레드시트 이름이 'auto_curation'인 시트를 열기

@app.route('/trigger_crawl', methods=['POST'])
def trigger_crawl():
    data = request.get_json()
    url = data.get('url')  # 스크립트에서 받은 URL 처리
    # URL로 크롤링 로직을 동작시키는 함수 호출
    result = run_crawl(url)  # 'run_crawl' 함수를 적절하게 수정하여 URL을 인자로 받을 수 있도록 해야 함
    # 중복으로 jsonify하면 TypeError: Object of type Response is not JSON serializable
    # return jsonify(result)
    if isinstance(result, dict) and result.get("status") == "error":
        return jsonify(result), 500  # 크롤링 중 에러가 발생한 경우
    if save_to_mongodb(result):
        return jsonify({"status": "success", "message": "Data saved to MongoDB", "data": result})
    else:
        return jsonify({"status": "error", "message": "Failed to save data to MongoDB"}), 500

# mongodb 에 저장
def save_to_mongodb(data):
    try:
        client = MongoClient(
            "mongodb+srv://admin:thhvUgtZ0kku4WuK@cluster0.vrzzp.mongodb.net/hwikDB?retryWrites=true&w=majority",
            tlsCAFile=certifi.where(),
        )
        db = client["hwikDB"]
        collection = db["testlodgment"]
        if isinstance(data, list):  # 데이터가 리스트인지 확인
            for doc in data:
                doc["createdAt"] = datetime.now(timezone.utc)
                inserted_id = collection.insert_one(doc).inserted_id
                doc["_id"] = str(inserted_id)  # _id를 문자열로 변환
            return True
    except Exception as e:
        print("Error saving to MongoDB:", str(e))
        return False

# @app.route('/run_crawl', methods=['POST'])
def run_crawl(url):
    # print("start run")
    # data = request.get_json()
    # print("data", data)
    # url = data['url']  # URL 추출

    # Selenium WebDriver 설정
    options = Options()
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    options.add_argument(f'user-agent={user_agent}')
    options.add_argument('--incognito')
    options.add_experimental_option('detach', True)
    driver = webdriver.Chrome(options=options)

    # 화면 크기 목록
    pc_device_sizes = ["1920,1440", "1920,1200", "1920,1080", "1600,1200", "1600,900",
                       "1536,864", "1440,1080", "1440,900", "1360,768"]
    mobile_device_sizes = [
        "360,640", "360,740", "375,667", "375,812", "412,732", "412,846",
        "412,869", "412,892", "412,915"]

    try:
        # 랜덤 화면 크기 설정
        size = random.choice(pc_device_sizes if random.choice([True, False]) else mobile_device_sizes)
        width, height = map(int, size.split(","))
        
        # 창 크기 조정
        driver.set_window_size(width, height)
        driver.get(url)
        time.sleep(random.uniform(1, 2))

        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.ID, "entryIframe")))
        driver.switch_to.default_content()
        WebDriverWait(driver, 10).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "entryIframe")))
        time.sleep(random.uniform(1, 2))

        gomain_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//a[contains(., '홈')]")))
        gomain_button.click()

        collected_data = []
        try:
            rooms_tab = driver.find_elements(By.XPATH, "//a[.//span[contains(text(), '객실')]]")
            time.sleep(random.uniform(1, 2))
        except NoSuchElementException:
            rooms_tab = None

        if rooms_tab:
            try:
                lodgment_name = driver.find_element(By.CSS_SELECTOR, '.GHAhO').text
            except NoSuchElementException:
                lodgment_name = 'None'

            try:
                lodgment_address = driver.find_element(By.CSS_SELECTOR, '.LDgIH').text
            except NoSuchElementException:
                lodgment_address = 'None'


            information_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//a[contains(., '정보')]")))
            information_button.click()

            try:
                lodgment_story = driver.find_element(By.CSS_SELECTOR, '.T8RFa').text
            except NoSuchElementException:
                lodgment_story = 'None'


            room_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//a[contains(., '객실')]")))
            room_button.click()

            #여기서 배열을 계속 갱신해주니까 문제가 해결되었다 너무나도 기쁘다!!!!!!!!!
            list_rooms = driver.find_elements(By.CSS_SELECTOR, "li.QqcXW")
            total_rooms = len(list_rooms)

            for index in range(total_rooms):
                # <a> 태그를 찾아 클릭합니다.
                list_rooms = driver.find_elements(By.CSS_SELECTOR, "li.QqcXW")
                room = list_rooms[index]

                WebDriverWait(driver, 10).until(EC.element_to_be_clickable(room))
                room.click()

                try:
                    lodgment_roomname = driver.find_element(By.CSS_SELECTOR, '.HBtVH').text
                except NoSuchElementException:
                    lodgment_roomname = 'None'

                try:
                    lodgment_information_elements = driver.find_elements(By.CSS_SELECTOR, '.iSeSf')
                    lodgment_information = [element.text for element in lodgment_information_elements]
                    lodgment_people_num = ""
                    max_people_num = ""
                    check_in_time = ""
                    check_out_time = ""

                    for info in lodgment_information:
                        if "기준" in info:
                            # 기준 인원 추출
                            lodgment_people_num = int(info.split("기준", 1)[1].split("인")[0].strip())
                            # 최대 인원 추출
                        if "최대" in info:
                            max_people_num = int(info.split("최대", 1)[1].split("인")[0].strip())
                        if "입실" in info:
                            # 입실 시간 추출
                            check_in_time = info.split("입실", 1)[1].split(",")[0].strip()
                        if "퇴실" in info:
                            # 퇴실 시간 추출
                            check_out_time = info.split("퇴실", 1)[1].split(",")[0].strip()
                except NoSuchElementException:
                    lodgment_information = 'None'

                try:
                    lodgment_facility_elements = driver.find_elements(By.CSS_SELECTOR, '.Ex6zM')
                    lodgment_facility = []
                    for element in lodgment_facility_elements:
                        # 각 요소에서 텍스트 추출
                        title = element.text
    
                        # SVG 데이터 추출 (SVG가 없을 경우를 대비하여 예외 처리)
                        try:
                            svg_element = element.find_element(By.CSS_SELECTOR, 'svg')
                            svg_data = svg_element.get_attribute('outerHTML')

                            # SVG를 Data URL로 변환
                            img_src = svg_to_data_url(svg_data)

                        except NoSuchElementException:
                            img_src = None  # SVG 요소가 없는 경우 None 할당
    
                        # 딕셔너리에 저장
                        facility = {
                                    "name" : title,
                                    "img" : img_src}
                        lodgment_facility.append(facility)
                except NoSuchElementException:
                    lodgment_facility = 'None'

                try:
                    lodgment_structure_elements = driver.find_elements(By.CSS_SELECTOR, '.k2AT3')
                    lodgment_structure = []
                    for element in lodgment_structure_elements:
                        first_text = element.find_element(By.TAG_NAME, 'em').text

                        svg_element = element.find_element(By.CSS_SELECTOR, 'svg')
                        svg_data = svg_element.get_attribute('outerHTML')
                        second_text = element.find_element(By.CSS_SELECTOR, 'div.Yk_tu').text

                        structure = [first_text, svg_data, second_text]
                        lodgment_structure.append(structure)
                except NoSuchElementException:
                    lodgment_structure = 'None'

                try:
                    lodgment_introduce = driver.find_element(By.CSS_SELECTOR, '.nwx9d').text
                except NoSuchElementException:
                    lodgment_introduce = 'None'

                try:
                    lodgment_rule = driver.find_element(By.CSS_SELECTOR, '.yloSp').text
                    lodgment_cautions = []
                    cautions = {
                                "title" : None,
                                "description" : lodgment_rule
                    }
                    lodgment_cautions.append(cautions)
                except NoSuchElementException:
                    lodgment_cautions = 'None'

                try:
                    expand_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '._zphO')))
                    expand_button.click()

                    lodgment_curation = []
                    imgs = []
                    lodgment_images_elements = driver.find_elements(By.CSS_SELECTOR, '.yenNT img')

                    coverImg = lodgment_images_elements[0].get_attribute('src')

                    for element in lodgment_images_elements :
                        src_image = element.get_attribute('src')
                        src_image_dict = {
                                          "src" : src_image,
                                          "description" : None
                        }
                        imgs.append(src_image_dict)

                    curation_dict = {
                                     "title" : None,
                                     "description" : None,
                                     "imgs" : imgs
                    }
                    lodgment_curation.append(curation_dict)
                    
                except NoSuchElementException:
                    lodgment_curation = 'None'


                if len(list_rooms) > 1 :
                    lodgment_fullname = lodgment_name + "- " + lodgment_roomname
                else :
                    lodgment_fullname = lodgment_name

                priceDetails = []
                priceNotices = []
                additional = []
                refund = {}


                collected_data.append({
                'name': lodgment_fullname,
                'fullAddress': lodgment_address,
                'description' : lodgment_story + lodgment_introduce,
                'defaultHeadcount' : lodgment_people_num,
                'maximumHeadcount' : max_people_num,
                'checkin' : check_in_time,
                'checkOut' : check_out_time,
                'facilities' : lodgment_facility,
                'cautions' : lodgment_cautions,
                'curation' : lodgment_curation,
                'coverImg' : coverImg,
                'country' : "korea",
                'isOpen' : True,
                'priceDetails' : priceDetails,
                'priceNotices' : priceNotices,
                'additionalConvenience' : additional,
                'refundRules' : refund
                })


                escape_room = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.DDfpb")))
                escape_room.click()


            for room_data in collected_data:
                row = [
                    room_data['name'], 
                    room_data['fullAddress'], 
                    room_data['description'], 
                    room_data['defaultHeadcount'], 
                    room_data['maximumHeadcount'],
                    room_data['checkin'],
                    room_data['checkOut'],
                    str(room_data['facilities']),
                    str(room_data['cautions']),
                    str(room_data['curation'])
                ]
                sheet.append_row(row)
        else :
            print("네이버 예약이 없습니다.")
        return collected_data
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        driver.quit()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)