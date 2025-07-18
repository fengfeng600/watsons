from selenium import webdriver
from selenium.webdriver.common.by import By
from datetime import datetime
from time import sleep
import mysql.connector
from sqlalchemy import create_engine
from sqlalchemy.types import Float, Text, String, Integer, Date
import pandas as pd
import re

def build_url(main_category, category_name, category_code, page_size=64, page=0):
    return f"https://www.watsons.com.tw/{main_category}/{category_name}/c/{category_code}?pageSize={page_size}&currentPage={page}"


def get_watsons_categories():
    return {
        "日用品": {
            "女性生理用品": "104501"
        }
    }

def scroll_to_bottom(driver, scroll_pause_time=2, scroll_step=300):
    height = driver.execute_script("return document.body.scrollHeight")
    current_position = 0

    while current_position < height:
        driver.execute_script(f"window.scrollTo(0, {current_position});")
        sleep(scroll_pause_time)
        current_position += scroll_step
        height = driver.execute_script("return document.body.scrollHeight")

def find_text(parent, selector, default):
    try:
        text = parent.find_element(By.CSS_SELECTOR, selector).text.strip()
        return text if text else default
    except:
        return default
    
def find_brand(parent):
    try:
        brand = parent.find_element(By.CSS_SELECTOR, "h2.productName a span").text.strip()
        return brand
    except:
        return "無品牌資訊"

def handle_adult_popup(driver):
    try:
        adult_button = driver.find_element(By.XPATH, "//a[text()='我已滿十八歲']")
        adult_button.click()
        sleep(1)
    except:
        pass
    
#判斷是否為組合包
def is_combo(name):
    patterns = [
        r"\(\d+\s*\+\s*\d+\)",                              
        r"\d+\s*(片|入|褲|件|條|棉)?\D{0,10}?\d+\s*(盒|組|包|袋|入)",  
        r"[xX＊*×]\s*\d+\s*(包|入|組|盒)?",
        r"\d+\s*(褲|件|條|棉|片|入)\s*\+\s*\d+\s*(褲|件|條|棉|片|入)",
        r"箱購"]
    for pattern in patterns:
        if re.search(pattern, name):
            return True
    return False

#去除$變成浮點數
def clean_price(price_str):
    try:
        price_type = re.search(r"\$?\s*(\d+(\.\d+)?)\s*/\s*件", price_str)
        if price_type:
            return float(price_type.group(1))  
        price_type2 = re.search(r"\$?\s*(\d+(\.\d+)?)", price_str)
        if price_type2:
            return float(price_type2.group(1))
        return 0.0
    except:
        return 0.0
    
#更改總銷量格式 K+ K 
def clean_sold(text):
    pattern = r"總銷量\s*>\s*(\d+)(K)?(\+)?"
    match = re.search(pattern, text)

    if match:
        num = int(match.group(1))
        has_k = match.group(2)
        
        if has_k:
            num *= 1000
        
        return num   
    return 0  
#將商品分群
category_patterns = {
    "類型": {
        r".*褲.*": "褲型",
        r"導管": "導管式棉條",
        r"指入": "指入式棉條",
        r"棉條": "一般棉條",
        r"護墊": "護墊",
        r"日用": "日用",
        r"夜用|超熟睡": "夜用"
    },
    "厚薄": {
        r"超薄": "超薄",
        r"極薄": "極薄",
        r"特薄": "特薄",
        r"極致薄": "極致薄",
        r"\b薄\b": "一般薄"
    },
    "吸收量": {
        r"量少": "量少",
        r"量多|大量|極多": "量多",
        r"\b一般\b": "一般"
    },
    "材質": {
        r"(漢本|.*草.*)": "草本",
        r"(Q棉|原生棉|柔棉|棉柔)": "棉製",
        r".*菌.*": "抗菌",
        r".*涼.*": "涼感",
        r"透氣": "透氣"
    },
    "氣味": {
        r"無香": "無香",
        r"(香氛|微香|花|香味)": "有香味",
        r"除味|.*味.*": "淨味"
    }
}

def extract_features_combined(text):
    result = {}
    for category in ["類型", "厚薄", "吸收量"]:
        matched = []
        for pattern, value in category_patterns[category].items():
            if re.search(pattern, text):
                matched.append(value)
        result[category] = matched[0] if matched else None

    for category in ["材質", "氣味"]:
        matched_features = []
        for pattern, value in category_patterns[category].items():
            if re.search(pattern, text):
                matched_features.append(value)
        result[category] = matched_features if matched_features else None

    return result
  

#取出長度數值    
def extract_length_cm(text):
    length = re.search(r"(\d{2,3}(?:\.\d)?)\s*(?:cm|公分)", text.lower())
    if length:
        return float(length.group(1))
    return None
    

driver = webdriver.Chrome()
driver.implicitly_wait(5)
driver.get("https://www.watsons.com.tw/")
main_window = driver.current_window_handle

all_products = []
today = datetime.today().strftime("%Y-%m-%d")
categories = get_watsons_categories()

for category, subtypes in categories.items():
    for subtype, sub_code in subtypes.items():
        try:
            driver.execute_script("window.open('');")
            driver.switch_to.window(driver.window_handles[1])

            page = 0
            while True:
                url = build_url(category, subtype, sub_code, page=page)
                driver.get(url)
                sleep(3)
                handle_adult_popup(driver)
                scroll_to_bottom(driver)

                product = driver.find_elements(By.CSS_SELECTOR, "e2-product-tile")
                if not product:
                    print(f"{category} - {subtype} 第 {page} 頁無商品，停止翻頁")
                    break

                print(f"{category} - {subtype} 第 {page} 頁抓到 {len(product)} 筆商品")

                for p in product:
                    brand = find_brand(p)
                    name = find_text(p, "h2.productName a", "無名稱")
                    promo = find_text(p, "div.productHighlight", "無促銷方案")
                    special_price = find_text(p, "div.formatted-value", "無特價")
                    original_price = find_text(p, "div.productOriginalPrice del", "無原價")
                    sold = find_text(p, "div.social-proof-box span", "無銷量")
                    
                    features = extract_features_combined(name)


                    all_products.append({
                        "日期": today,
                        "主分類": category,
                        "子分類": subtype,
                        "品牌": brand,
                        "商品名稱": name,
                        "促銷方案": promo,
                        "特價": clean_price(special_price),
                        "原價": clean_price(original_price),
                        "銷量": clean_sold(sold),
                        "是否組合包": "是" if is_combo(name) else "否",
                        "長度":extract_length_cm(name),
                        "類型": features.get("類型"),
                        "厚薄": features.get("厚薄"),
                        "吸收量": features.get("吸收量"),
                        "材質": ", ".join(features.get("材質")) if features.get("材質") else None,
                        "氣味": ", ".join(features.get("氣味")) if features.get("氣味") else None
                    })

                page += 1

            print(f"已累計抓取 {len(all_products)} 筆商品")

            driver.close()
            driver.switch_to.window(main_window)

        except Exception as e:
            print(f"錯誤於分類：{category} - {subtype}，錯誤訊息：{e}")
            driver.close()
            driver.switch_to.window(main_window)

driver.quit()
watsons_data = pd.DataFrame(all_products)
watsons_data.replace("", None, inplace=True)

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="123456789"
)
cursor = conn.cursor()
cursor.execute("CREATE DATABASE IF NOT EXISTS watsons")
cursor.close()
conn.close()

engine = create_engine("mysql+mysqlconnector://root:123456789@localhost/watsons")

watsons_data.to_sql(
    name="watsons_products",
    con=engine,
    if_exists="append",
    index=False,
    dtype={
        "日期": Date,
        "主分類": String(100),
        "子分類": String(100),
        "品牌": String(100),
        "商品名稱": Text,
        "促銷方案": Text,
        "特價": Float,
        "原價": Float,
        "銷量": Integer,
        "是否組合包": String(10),
        "類型": String(20),
        "長度": Float,
        "厚薄": String(20),
        "吸收量": String(20),
        "材質": Text,
        "氣味": Text,
    }
)