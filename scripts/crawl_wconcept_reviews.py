#!/usr/bin/env python3
# -*- coding: utf-8 -*-

####################################
### W컨셉 리뷰 크롤링 (통일 형식) ###
####################################

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import re
from typing import List, Dict

def setup_driver():
    """Chrome WebDriver 설정"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
    
    driver = webdriver.Chrome(options=options)
    return driver

def parse_height_weight(text: str) -> tuple:
    """키/몸무게 텍스트에서 숫자 추출"""
    height = None
    weight = None
    
    height_match = re.search(r'(\d+)cm', text)
    if height_match:
        height = int(height_match.group(1))
    
    weight_match = re.search(r'(\d+)kg', text)
    if weight_match:
        weight = int(weight_match.group(1))
    
    return height, weight

def normalize_date(date_str: str) -> str:
    """날짜 형식 통일 (25.12.12 -> 2025.12.12)"""
    if not date_str:
        return ""
    
    # 이미 4자리 연도면 그대로 반환
    if date_str.startswith('20'):
        return date_str
    
    # 2자리 연도를 4자리로 변환 (25.12.12 -> 2025.12.12)
    match = re.match(r'^(\d{2})\.(\d{2})\.(\d{2})$', date_str)
    if match:
        year, month, day = match.groups()
        full_year = f"20{year}"
        return f"{full_year}.{month}.{day}"
    
    return date_str

def extract_wconcept_review_data(review_element) -> Dict:
    """개별 리뷰 요소에서 데이터 추출 (통일 형식)"""
    try:
        # 별점 (style="width:100%" 등 추출)
        rating = 5
        try:
            star_strong = review_element.find_element(By.CSS_SELECTOR, ".star-grade strong")
            style_str = star_strong.get_attribute('style')
            width_match = re.search(r'width:\s*(\d+)%', style_str)
            if width_match:
                width_val = int(width_match.group(1))
                rating = int(width_val / 20.0)  # 100 -> 5, 80 -> 4
        except: 
            pass

        # 작성일
        review_date = ""
        try:
            info_right = review_element.find_element(By.CLASS_NAME, "product_review_info_right")
            review_date = info_right.find_element(By.TAG_NAME, "span").text.strip()
            review_date = normalize_date(review_date)  # 날짜 형식 통일
        except: 
            pass

        # 리뷰 내용
        content = ""
        try:
            content = review_element.find_element(By.CLASS_NAME, "pdt_review_text").text.strip()
        except: 
            pass
        
        # 이미지
        images = []
        try:
            imgs = review_element.find_elements(By.CSS_SELECTOR, ".pdt_review_photo img")
            images = [img.get_attribute('src') for img in imgs if img.get_attribute('src')]
        except: 
            pass
        
        # 옵션 및 체형 정보
        option_text = ""
        user_height = None
        user_weight = None
        
        try:
            info_elements = review_element.find_elements(By.CSS_SELECTOR, ".pdt_review_option p")
            combined_option = " | ".join([el.text.strip() for el in info_elements if el.text.strip()])
            option_text = combined_option
            
            # 체형 정보에서 키/몸무게 추출 시도
            user_height, user_weight = parse_height_weight(combined_option)
        except: 
            pass
        
        # 통일 형식으로 반환
        return {
            'rating': rating,
            'content': content,
            'review_date': review_date,
            'images': images,
            'user_height': user_height,
            'user_weight': user_weight,
            'option_text': option_text
        }

    except Exception as e:
        print(f"[DEBUG] 파싱 에러: {e}")
        return None

def collect_wconcept_reviews(url: str, target_total: int = 20) -> List[Dict]:
    """
    W컨셉 리뷰 수집 (통일 형식)
    
    Returns:
        [
            {
                "rating": 5,
                "content": "좋아요",
                "review_date": "2025.01.10",
                "images": ["url1", "url2"],
                "user_height": None,  # W컨셉은 체형 정보 없는 경우 많음
                "user_weight": None,
                "option_text": "구매옵션 : FREE,"
            }
        ]
    """
    driver = setup_driver()
    all_reviews = []
    current_page = 1
    
    try:
        target_url = url if "#review" in url else f"{url}#review"
        driver.get(target_url)
        time.sleep(3)

        while len(all_reviews) < target_total:
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "pdt_review_text"))
                )
                
                rows = driver.find_elements(By.XPATH, "//tr[descendant::p[@class='pdt_review_text']]")
                
                for row in rows:
                    if len(all_reviews) >= target_total: 
                        break
                    
                    item = extract_wconcept_review_data(row)
                    if item and item['content']:
                        all_reviews.append(item)

                if len(all_reviews) >= target_total: 
                    break

                # 다음 페이지
                current_page += 1
                try:
                    pagination_id = "reviewPageNavigation"
                    next_page_xpath = f"//*[@id='{pagination_id}']//a[@title='{current_page}']"
                    next_page_btn = driver.find_element(By.XPATH, next_page_xpath)
                    
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_page_btn)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", next_page_btn)
                    
                    #print(f"[INFO] {current_page}페이지 클릭 완료")
                    time.sleep(2.5)
                    
                except NoSuchElementException:
                    print(f"[INFO] {current_page}페이지 버튼을 찾을 수 없어 종료합니다.")
                    break

            except TimeoutException:
                print("[ERROR] 리뷰 로딩 시간 초과")
                break

        #print(f"총 {len(all_reviews)}개의 리뷰를 수집했습니다.")
        return all_reviews
        
    except Exception as e:
        print(f"크롤링 중 오류 발생: {str(e)}")
        return all_reviews
        
    finally:
        driver.quit()