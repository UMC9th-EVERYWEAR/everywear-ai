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
        # URL에서 /products/ 다음의 숫자 추출
        match = re.search(r'/products/(\d+)', url)
        if match:
            return match.group(1)
        
        return None
        
    except Exception as e:
        print(f"[ERROR] item_id 추출 실패: {e}")
        return None


def setup_driver():
    """Chrome WebDriver 설정 (봇 감지 우회 강화)"""
    options = webdriver.ChromeOptions()
    
    # Headless 모드
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    # WebDriver 감지 우회
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # User-Agent
    options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=options)
    
    # navigator.webdriver 제거 (중요!)
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
        
        # 리뷰 ID - data-review-id 속성
        try:
            review_id = review_element.get_attribute('data-review-id')
            review_data['review_id'] = review_id if review_id else ''
        except:
            pass
        
        # 사용자 ID - span.text-s (별점 옆)
        try:
            user_spans = review_element.find_elements(By.CSS_SELECTOR, "span.text-s")
            if len(user_spans) >= 1:
                review_data['user_id'] = user_spans[0].text.strip()
        except:
            pass
        
        # 별점 - width: 100% 스타일로 채워진 별 개수 세기
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
        
        # 날짜 - span.text-s.text-tertiary (우측)
        try:
            date_spans = review_element.find_elements(By.CSS_SELECTOR, "span.text-s.text-tertiary")
            if date_spans:
                review_data['date'] = date_spans[-1].text.strip()
        except:
            pass
        
        # 옵션, 체형, 사이즈 정보
        try:
            info_elements = review_element.find_elements(By.CSS_SELECTOR, "p.text-s.text-tertiary span")
            for elem in info_elements:
                text = elem.text.strip()
                if text.startswith('옵션 :'):
                    review_data['option'] = text.replace('옵션 :', '').strip()
                elif text.startswith('체형 :'):
                    # 158cm, 47kg 형식 파싱
                    body_text = text.replace('체형 :', '').strip()
                    height_match = re.search(r'(\d+)cm', body_text)
                    weight_match = re.search(r'(\d+)kg', body_text)
                    if height_match:
                        review_data['user_info']['height'] = f"{height_match.group(1)}cm"
                    if weight_match:
                        review_data['user_info']['weight'] = f"{weight_match.group(1)}kg"
        except:
            pass
        
        # 리뷰 내용 - p.text-l.text-primary
        try:
            content_element = review_element.find_element(By.CSS_SELECTOR, "p.text-l.text-primary")
            review_data['content'] = content_element.text.strip()
        except:
            pass
        
        # 리뷰 이미지
        try:
            img_element = review_element.find_element(By.CSS_SELECTOR, "img[src*='img.29cm.co.kr']")
            img_src = img_element.get_attribute('src')
            if img_src:
                # webp 포맷 제거하고 원본 이미지 URL로 변경
                img_src = img_src.split('?')[0]
                review_data['images'].append(img_src)
        except:
            pass
        
        return review_data
        
    except Exception as e:
        print(f"리뷰 데이터 추출 중 오류: {str(e)}")
        return None


def collect_29cm_reviews(url: str, target_total: int = 20) -> List[Dict]:
    """
    Selenium을 사용하여 29cm 상품 리뷰를 수집합니다.
    """
    driver = setup_driver()
    
    try:
        # item_id 추출
        item_id = extract_item_id_from_url(url)
        if not item_id:
            print("[ERROR] item_id를 추출할 수 없습니다.")
            return []
        
        print(f"[시작] 29CM 상품번호 {item_id} 리뷰 수집 중... (목표: {target_total}개)")
        print(f"페이지 로딩 중: {url}")
        
        driver.get(url)
        
        # 페이지 로딩 대기
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )
        
        time.sleep(3)
        
        # 페이지 스크롤 (리뷰 섹션까지)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
        time.sleep(2)
        
        reviews = []
        
        # 리뷰 요소 찾기 - 정확한 선택자
        review_selectors = [
            "li[data-review-id]",  # ✅ 29cm의 실제 구조
            "div[data-review-id]"
        ]
        
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
            # 디버깅: 페이지 소스 일부 출력
            print("[DEBUG] 페이지 소스 일부:")
            print(driver.page_source[:500])
            return []
        
        print(f"총 {len(review_elements)}개의 리뷰 발견")
        
        # 최대 개수만큼 리뷰 추출
        for i, review_element in enumerate(review_elements[:target_total]):
            if i >= target_total:
                break
            
            try:
                # 리뷰가 화면에 보이도록 스크롤
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", review_element)
                time.sleep(0.5)
                
                review_data = extract_review_data(review_element)
                if review_data and review_data.get('content'):
                    # item_id 추가
                    review_data['item_id'] = item_id
                    reviews.append(review_data)
                    print(f"리뷰 {len(reviews)} 수집 완료")
                else:
                    print(f"리뷰 {i+1}: 내용이 없어 스킵")
            except Exception as e:
                print(f"리뷰 {i+1} 처리 중 오류: {str(e)}")
                continue
        
        print(f"총 {len(reviews)}개의 리뷰를 수집했습니다.")
        return reviews
        
    except Exception as e:
        print(f"크롤링 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return []
        
    finally:
        driver.quit()


if __name__ == "__main__":
    # 테스트
    test_url = "https://www.29cm.co.kr/products/3437237"
    reviews = collect_29cm_reviews(test_url, target_total=20)
    
    print("\n=== 수집된 리뷰 ===")
    import json
    print(json.dumps(reviews, indent=4, ensure_ascii=False))
    print(f"\n최종 수집 개수: {len(reviews)}개")