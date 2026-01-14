######################################
### 지그재그 상품 상세 페이지 크롤링 ###
######################################

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
import time

# Chrome WebDriver 설정
def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    driver = webdriver.Chrome(options=options)
    return driver


# 여러 XPath를 순차적으로 시도하여 요소 추출 (fallback 처리)
def extract_by_xpath_with_fallback(driver, xpath_list, wait_time=10, is_attribute=False, attribute_name='src'):
    for xpath in xpath_list:
        try:
            element = WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            if is_attribute:
                value = element.get_attribute(attribute_name)
            else:
                value = element.text.strip()

            if value:
                return value
        except (TimeoutException, NoSuchElementException):
            continue

    return "-"


def extract_by_xpath(driver, xpath, wait_time=10, is_attribute=False, attribute_name='src'):
    try:
        element = WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        if is_attribute:
            return element.get_attribute(attribute_name)
        else:
            return element.text.strip()
    except (TimeoutException, NoSuchElementException):
        return "-"


# 지그재그 상품 상세 페이지에서 모든 정보 크롤링
def crawl_product_details(url):
    driver = setup_driver()

    try:
        print(f"페이지 로딩 중: {url}")
        driver.get(url)

        # 페이지 로딩 대기 (JavaScript 렌더링 고려)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[@id='__next']"))
        )

        # 추가 대기 (동적 콘텐츠 로딩)
        time.sleep(2)

        result = {}

        # 1. 쇼핑몰 이름
        result['shoppingmall_name'] = "지그재그"

        # 2. 상품 URL
        result['product_url'] = url

        # 3. 카테고리 (고정값)
        result['category'] = "-"

        # 4. 대표 이미지 추출
        image_xpath_absolute = "//*[@id='__next']/div[1]/div[1]/div/div[1]/div[1]/div/div/div[1]/div[1]/div/div/picture/img"
        image_xpath_relative = "//picture/img[1]"

        image_url = extract_by_xpath_with_fallback(
            driver,
            [image_xpath_relative, image_xpath_absolute],
            is_attribute=True,
            attribute_name='src'
        )
        result['product_img_url'] = image_url if image_url else "-"

        # 5. 상품명 추출 (두 가지 케이스)
        product_name_xpath_case1 = "//*[@id='__next']/div[1]/div[1]/div/div[4]/h1"
        product_name_xpath_case2 = "//*[@id='__next']/div[1]/div[1]/div/div[3]/h1"
        product_name_xpath_relative = "//h1[contains(@class, 'product') or contains(@class, 'title')] | //div[contains(@class, 'product')]//h1"

        product_name = extract_by_xpath_with_fallback(
            driver,
            [product_name_xpath_case1, product_name_xpath_case2, product_name_xpath_relative]
        )
        result['product_name'] = product_name if product_name else "-"

        # 6. 브랜드명 추출
        brand_xpath_absolute = "//*[@id='__next']/div[1]/div[1]/div/div[2]/button[1]/span"
        brand_xpath_relative = "//button[contains(@class, 'brand') or contains(@class, 'Brand')]/span | //div[contains(@class, 'brand')]//span[1]"

        brand_name = extract_by_xpath_with_fallback(
            driver,
            [brand_xpath_absolute, brand_xpath_relative]
        )
        result['brand_name'] = brand_name if brand_name else "-"

        # 7. 가격 추출 (두 가지 케이스)
        price_xpath_case1 = "//*[@id='__next']/div[1]/div[1]/div/div[5]/div/div[1]/div[1]/div[2]/div[1]"
        price_xpath_case2 = "//*[@id='__next']/div[1]/div[1]/div/div[6]/div/div[1]/div[1]/div[2]/div[1]"
        price_xpath_relative = "//div[contains(@class, 'price')]//div[contains(text(), ',') or contains(text(), '원')] | //div[contains(@class, 'Price')]//div[1]"

        price = extract_by_xpath_with_fallback(
            driver,
            [price_xpath_case1, price_xpath_case2, price_xpath_relative]
        )

        if price and price != "-":
            price = price.strip()
            if not price.endswith('원'):
                import re
                numbers = re.findall(r'[\d,]+', price)
                if numbers:
                    price = numbers[0] + '원'
                else:
                    price = price + '원'
        else:
            price = "-"

        result['price'] = price

        # 8. 별점 추출 (두 가지 케이스)
        starpoint_xpath_case1 = "//*[@id='__next']/div[1]/div[1]/div/div[4]/div"
        starpoint_xpath_case2 = "//*[@id='__next']/div[1]/div[1]/div/div[5]/div"
        starpoint_xpath_relative = "//div[contains(@class, 'rating') or contains(@class, 'star') or contains(@class, 'review')]//div[contains(text(), '.') or contains(text(), '점')]"

        starpoint = extract_by_xpath_with_fallback(
            driver,
            [starpoint_xpath_case1, starpoint_xpath_case2, starpoint_xpath_relative]
        )
        # 별점이 "-"이거나 없으면 None, 있으면 float로 변환 시도
        if not starpoint or starpoint == "-":
            result['star_point'] = None
        else:
            try:
                # 숫자 문자열인 경우 float로 변환
                result['star_point'] = float(starpoint)
            except (ValueError, TypeError):
                result['star_point'] = None

        # 9. AI 리뷰
        result['AI_review'] = None

        return result

    except Exception as e:
        print(f"크롤링 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"shoppingmall_name": "지그재그", "product_url": url, "category": "-", "product_img_url": "-", "product_name": "-", "brand_name": "-", "price": "-", "star_point": None, "AI_review": None}

    finally:
        driver.quit()

