#!/usr/bin/env python3
# -*- coding: utf-8 -*-

####################################
### W concept 상품 리뷰 크롤링 ###
####################################
import time
import re
from typing import List, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    driver = webdriver.Chrome(options=options)
    return driver

def extract_wconcept_review_data(review_element) -> Dict:
    """사용자가 제공한 HTML 구조 기반 데이터 추출"""
    data = {'score': 0.0, 'option': '', 'user_id': '', 'date': '', 'satisfaction': {}, 'content': '', 'images': []}
    try:
        try:
            star_strong = review_element.find_element(By.CSS_SELECTOR, ".star-grade strong")
            style_str = star_strong.get_attribute('style')
            width_match = re.search(r'width:\s*(\d+)%', style_str)
            if width_match:
                width_val = int(width_match.group(1))
                data['score'] = width_val / 20.0
        except: pass

        try:
            info_elements = review_element.find_elements(By.CSS_SELECTOR, ".pdt_review_option p")
            data['option'] = " | ".join([el.text.strip() for el in info_elements if el.text.strip()])
        except: pass

        try:
            info_right = review_element.find_element(By.CLASS_NAME, "product_review_info_right")
            data['user_id'] = info_right.find_element(By.TAG_NAME, "em").text.strip()
            data['date'] = info_right.find_element(By.TAG_NAME, "span").text.strip()
        except: pass

        try:
            eval_items = review_element.find_elements(By.CSS_SELECTOR, ".product_review_evaluation li")
            for item in eval_items:
                label = item.find_element(By.TAG_NAME, "strong").text.strip()
                val = item.find_element(By.TAG_NAME, "em").text.strip()
                data['satisfaction'][label] = val
        except: pass

        try:
            data['content'] = review_element.find_element(By.CLASS_NAME, "pdt_review_text").text.strip()
            imgs = review_element.find_elements(By.CSS_SELECTOR, ".pdt_review_photo img")
            data['images'] = [img.get_attribute('src') for img in imgs if img.get_attribute('src')]
        except: pass

    except Exception:
        pass
    return data

def collect_wconcept_reviews(url: str, target_total: int = 20) -> List[Dict]:
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
                    if len(all_reviews) >= target_total: break
                    item = extract_wconcept_review_data(row)
                    if item['content']:
                        all_reviews.append(item)

                if len(all_reviews) >= target_total: break

                current_page += 1
                try:
                    pagination_id = "reviewPageNavigation"
                    next_page_xpath = f"//*[@id='{pagination_id}']//a[@title='{current_page}']"
                    
                    next_page_btn = driver.find_element(By.XPATH, next_page_xpath)
                    
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_page_btn)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", next_page_btn)
                    
                    time.sleep(2.5)
                    
                except NoSuchElementException:
                    break

            except TimeoutException:
                break

        return all_reviews
    finally:
        driver.quit()