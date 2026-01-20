#!/usr/bin/env python3
# -*- coding: utf-8 -*-

####################################
### 무신사 리뷰 크롤링 (셀레니움 강화 버전) ###
####################################

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import re
import requests
from typing import List, Dict, Optional
from urllib.parse import urlparse, parse_qs

def setup_driver():
    """Chrome WebDriver 설정 (봇 감지 우회 및 최적화)"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=options)
    return driver

def extract_product_no_from_url(url: str) -> Optional[str]:
    """URL에서 상품번호 추출 (공유 URL 및 일반 URL 대응)"""
    if 'onelink.me' in url or 'musinsa.link' in url:
        try:
            response = requests.head(url, allow_redirects=True, timeout=10)
            url = response.url
        except: return None
    
    match = re.search(r'/products/(\d+)', url)
    return match.group(1) if match else None

def collect_reviews(goods_no: str, target_total: int = 20) -> List[Dict]:
    """DOM Recycling을 극복하기 위해 마지막 요소를 추적하며 스크롤 수집"""
    driver = setup_driver()
    review_url = f"https://www.musinsa.com/review/goods/{goods_no}?sort=up_cnt_desc"
    collected_reviews = {}
    
    try:
        driver.get(review_url)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(3)

        scroll_attempts = 0
        max_attempts = 50

        while len(collected_reviews) < target_total and scroll_attempts < max_attempts:
            items = driver.find_elements(By.CSS_SELECTOR, "div.gtm-impression-content")
            
            if not items:
                driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(1)
                scroll_attempts += 1
                continue

            for item in items:
                try:
                    review_id = item.get_attribute("data-content-id")
                    if not review_id or review_id in collected_reviews:
                        continue

                    nickname = item.find_element(By.CSS_SELECTOR, "span[class*='Nickname']").text.strip()
                    date_val = item.find_element(By.CSS_SELECTOR, "span[class*='PurchaseDate']").text.strip()
                    
                    try:
                        score_text = item.find_element(By.CSS_SELECTOR, "div[class*='StarsScore'] span").text.strip()
                        score = int(score_text)
                    except:
                        score = 5

                    options_info = item.find_elements(By.CSS_SELECTOR, "div[class*='OptionRow__Container']")
                    survey = {}
                    option_text = ""
                    user_body = {"sex": "미선택", "height": "", "weight": ""}

                    for opt in options_info:
                        spans = opt.find_elements(By.TAG_NAME, "span")
                        if len(spans) < 2: continue
                        label = spans[0].text.strip()
                        value = spans[1].text.strip()
                        
                        if "구매옵션" in label:
                            option_text = value
                        elif "체형정보" in label:
                            parts = [p.strip() for p in value.split('·')]
                            user_body["sex"] = parts[0] if len(parts) > 0 else "미선택"
                            user_body["height"] = parts[1] if len(parts) > 1 else ""
                            user_body["weight"] = parts[2] if len(parts) > 2 else ""
                        elif "만족도" in label:
                            s_parts = [s.strip() for s in value.split('·')]
                            for i, s_val in enumerate(s_parts):
                                survey[f"satisfaction_{i}"] = s_val

                    content = item.find_element(By.CSS_SELECTOR, "div[class*='ExpandableContent'] span[class*='text-black']").text.strip()
                    images = [img.get_attribute("src") for img in item.find_elements(By.CSS_SELECTOR, "div[class*='ExpandableImageGroup'] img")]

                    try:
                        help_text = item.find_element(By.CSS_SELECTOR, "button[class*='HelpButton'] span").text.strip()
                        help_count = int(re.sub(r'[^0-9]', '', help_text))
                    except:
                        help_count = 0

                    collected_reviews[review_id] = {
                        'product_no': goods_no,
                        'review_no': review_id,
                        'content': content,
                        'date': date_val,
                        'score': score,
                        'option': option_text,
                        'user_info': user_body,
                        'satisfaction': survey,
                        'help_count': help_count,
                        'images': images
                    }
                    
                    if len(collected_reviews) >= target_total:
                        break
                        
                except Exception:
                    continue

            if items:
                driver.execute_script("arguments[0].scrollIntoView();", items[-1])
                time.sleep(2)
            
            scroll_attempts += 1
            
        return list(collected_reviews.values())[:target_total]

    except Exception:
        return list(collected_reviews.values())
    finally:
        driver.quit()