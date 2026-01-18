#!/usr/bin/env python3
# -*- coding: utf-8 -*-

####################################
### 29cm 리뷰 크롤링 (통일 형식) ###
####################################

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re
from typing import List, Dict, Optional

def setup_driver():
    """Chrome WebDriver 설정"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
    
    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        '''
    })
    
    return driver

def extract_item_id_from_url(url: str) -> Optional[str]:
    """URL에서 item_id 추출 (예: /products/3437237 -> 3437237)"""
    try:
        match = re.search(r'/products/(\d+)', url)
        if match:
            return match.group(1)
        return None
    except Exception as e:
        print(f"[ERROR] item_id 추출 실패: {e}")
        return None

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

def extract_review_data(review_element) -> Dict:
    """개별 리뷰 요소에서 데이터 추출 (통일 형식)"""
    try:
        # 별점
        try:
            star_elements = review_element.find_elements(By.CSS_SELECTOR, "i.absolute svg")
            filled_stars = 0
            for star in star_elements:
                parent = star.find_element(By.XPATH, "..")
                style = parent.get_attribute('style')
                if style and 'width: 100%' in style:
                    filled_stars += 1
            rating = filled_stars if filled_stars > 0 else 5
        except:
            rating = 5
        
        # 작성일
        try:
            date_spans = review_element.find_elements(By.CSS_SELECTOR, "span.text-s.text-tertiary")
            review_date = date_spans[-1].text.strip() if date_spans else ""
            review_date = normalize_date(review_date)  # 날짜 형식 통일
        except:
            review_date = ""
        
        # 리뷰 내용
        try:
            content_element = review_element.find_element(By.CSS_SELECTOR, "p.text-l.text-primary")
            content = content_element.text.strip()
        except:
            content = ""
        
        # 이미지
        images = []
        try:
            img_element = review_element.find_element(By.CSS_SELECTOR, "img[src*='img.29cm.co.kr']")
            img_src = img_element.get_attribute('src')
            if img_src:
                img_src = img_src.split('?')[0]
                images.append(img_src)
        except:
            pass
        
        # 옵션 및 체형 정보
        option_text = ""
        user_height = None
        user_weight = None
        
        try:
            info_elements = review_element.find_elements(By.CSS_SELECTOR, "p.text-s.text-tertiary span")
            for elem in info_elements:
                text = elem.text.strip()
                if text.startswith('옵션 :'):
                    option_text = text.replace('옵션 :', '').strip()
                elif text.startswith('체형 :'):
                    # "158cm, 47kg" 형식 파싱
                    body_text = text.replace('체형 :', '').strip()
                    user_height, user_weight = parse_height_weight(body_text)
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
        print(f"리뷰 데이터 추출 중 오류: {str(e)}")
        return None

def collect_29cm_reviews(url: str, target_total: int = 20) -> List[Dict]:
    """
    29cm 리뷰 수집 (통일 형식)
    
    Returns:
        [
            {
                "rating": 5,
                "content": "좋아요",
                "review_date": "24.12.15",
                "images": ["url1"],
                "user_height": 154,
                "user_weight": 51,
                "option_text": "[디자인:사이즈]Smile Cherry Argyle:FREE"
            }
        ]
    """
    driver = setup_driver()
    
    try:
        item_id = extract_item_id_from_url(url)
        if not item_id:
            print("[ERROR] item_id를 추출할 수 없습니다.")
            return []
        
        #print(f"[시작] 29CM 상품번호 {item_id} 리뷰 수집 중...")
        driver.get(url)
        
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "main")))
        time.sleep(3)
        
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
        time.sleep(2)
        
        reviews = []
        
        review_selectors = ["li[data-review-id]", "div[data-review-id]"]
        review_elements = []
        
        for selector in review_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    review_elements = elements
                    print(f"[INFO] 리뷰 선택자 '{selector}'로 {len(elements)}개 발견")
                    break
            except:
                continue
        
        if not review_elements:
            print("[ERROR] 리뷰를 찾을 수 없습니다.")
            return []
        
        #print(f"총 {len(review_elements)}개의 리뷰 발견")
        
        for i, review_element in enumerate(review_elements[:target_total]):
            if i >= target_total:
                break
            
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", review_element)
                time.sleep(0.5)
                
                review_data = extract_review_data(review_element)
                if review_data and review_data.get('content'):
                    reviews.append(review_data)
                    #print(f"리뷰 {len(reviews)} 수집 완료")
            except Exception as e:
                print(f"리뷰 {i+1} 처리 중 오류: {str(e)}")
                continue
        
        #print(f"총 {len(reviews)}개의 리뷰를 수집했습니다.")
        return reviews
        
    except Exception as e:
        print(f"크롤링 중 오류 발생: {str(e)}")
        return []
        
    finally:
        driver.quit()