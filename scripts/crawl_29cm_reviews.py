#!/usr/bin/env python3
# -*- coding: utf-8 -*-

####################################
### 29CM 상품 리뷰 크롤링 (Selenium) ###
####################################

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import re
from typing import List, Dict, Optional


def extract_item_id_from_url(url: str) -> Optional[str]:
    """
    29cm 상품 URL에서 item_id를 추출합니다.
    예: https://www.29cm.co.kr/products/3437237?categoryLargeCode=... -> 3437237
    
    Args:
        url: 29cm 상품 URL
        
    Returns:
        item_id 또는 None
    """
    try:
        match = re.search(r'/products/(\d+)', url)
        if match:
            return match.group(1)
        return None
    except Exception:
        return None


def setup_driver():
    """Chrome WebDriver 설정 (봇 감지 우회 강화)"""
    options = webdriver.ChromeOptions()
    
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=options)
    
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        '''
    })
    
    return driver


def extract_review_data(review_element):
    """개별 리뷰 요소에서 데이터 추출"""
    try:
        review_data = {
            'review_id': '',
            'user_id': '',
            'rating': 0.0,
            'content': '',
            'option': '',
            'date': '',
            'user_info': {
                'height': '',
                'weight': ''
            },
            'images': [],
            'is_gift': False
        }
        
        try:
            review_id = review_element.get_attribute('data-review-id')
            review_data['review_id'] = review_id if review_id else ''
        except:
            pass
        
        try:
            user_spans = review_element.find_elements(By.CSS_SELECTOR, "span.text-s")
            if len(user_spans) >= 1:
                review_data['user_id'] = user_spans[0].text.strip()
        except:
            pass
        
        try:
            star_elements = review_element.find_elements(By.CSS_SELECTOR, "i.absolute svg")
            filled_stars = 0
            for star in star_elements:
                parent = star.find_element(By.XPATH, "..")
                style = parent.get_attribute('style')
                if style and 'width: 100%' in style:
                    filled_stars += 1
            review_data['rating'] = float(filled_stars) if filled_stars > 0 else 5.0
        except:
            review_data['rating'] = 5.0
        
        try:
            date_spans = review_element.find_elements(By.CSS_SELECTOR, "span.text-s.text-tertiary")
            if date_spans:
                review_data['date'] = date_spans[-1].text.strip()
        except:
            pass
        
        try:
            info_elements = review_element.find_elements(By.CSS_SELECTOR, "p.text-s.text-tertiary span")
            for elem in info_elements:
                text = elem.text.strip()
                if text.startswith('옵션 :'):
                    review_data['option'] = text.replace('옵션 :', '').strip()
                elif text.startswith('체형 :'):
                    body_text = text.replace('체형 :', '').strip()
                    height_match = re.search(r'(\d+)cm', body_text)
                    weight_match = re.search(r'(\d+)kg', body_text)
                    if height_match:
                        review_data['user_info']['height'] = f"{height_match.group(1)}cm"
                    if weight_match:
                        review_data['user_info']['weight'] = f"{weight_match.group(1)}kg"
        except:
            pass
        
        try:
            content_element = review_element.find_element(By.CSS_SELECTOR, "p.text-l.text-primary")
            review_data['content'] = content_element.text.strip()
        except:
            pass
        
        try:
            img_element = review_element.find_element(By.CSS_SELECTOR, "img[src*='img.29cm.co.kr']")
            img_src = img_element.get_attribute('src')
            if img_src:
                img_src = img_src.split('?')[0]
                review_data['images'].append(img_src)
        except:
            pass
        
        return review_data
        
    except Exception:
        return None


def collect_29cm_reviews(url: str, target_total: int = 20) -> List[Dict]:
    """Selenium을 사용하여 29cm 상품 리뷰를 수집합니다."""
    driver = setup_driver()
    
    try:
        item_id = extract_item_id_from_url(url)
        if not item_id:
            return []
        
        driver.get(url)
        
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )
        
        time.sleep(3)
        
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
        time.sleep(2)
        
        reviews = []
        
        review_selectors = [
            "li[data-review-id]",
            "div[data-review-id]"
        ]
        
        review_elements = []
        for selector in review_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    review_elements = elements
                    break
            except:
                continue
        
        if not review_elements:
            return []
        
        for i, review_element in enumerate(review_elements[:target_total]):
            if i >= target_total:
                break
            
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", review_element)
                time.sleep(0.5)
                
                review_data = extract_review_data(review_element)
                if review_data and review_data.get('content'):
                    review_data['item_id'] = item_id
                    reviews.append(review_data)
            except Exception:
                continue
        
        return reviews
        
    except Exception:
        return []
        
    finally:
        driver.quit()