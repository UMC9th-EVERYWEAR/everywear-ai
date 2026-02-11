###################################
### 29CM 상품 상세 페이지 크롤링 ###
###################################

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
import time
import re
import requests


# Chrome WebDriver 설정
def setup_driver():
    options = webdriver.ChromeOptions()

    # headless 모드 사용하려면 True로 변경
    USE_HEADLESS = True

    if USE_HEADLESS:
        options.add_argument('--headless=new')  # 새로운 headless 모드 사용
        options.add_argument('--disable-gpu')  # headless 모드에서 GPU 비활성화
        options.add_argument('--window-size=1920,1080')  # 뷰포트 크기 명시적 설정 (중요!)

    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    driver = webdriver.Chrome(options=options)

    # headless 모드일 때 뷰포트 크기 설정 (추가 보장)
    # headless 모드에서는 기본 뷰포트가 작아서 요소가 렌더링되지 않을 수 있음
    if USE_HEADLESS:
        driver.set_window_size(1920, 1080)

    return driver


# 여러 XPath를 순차적으로 시도하여 요소 추출 (fallback 처리)
def extract_by_xpath_with_fallback(driver, xpath_list, wait_time=10, is_attribute=False, attribute_name='src'):
    for xpath in xpath_list:
        try:
            # 먼저 요소가 존재하는지 확인
            element = WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )

            # 텍스트 추출의 경우 요소가 보일 때까지 추가 대기 (headless 모드 대응)
            if not is_attribute:
                try:
                    WebDriverWait(driver, 3).until(
                        EC.visibility_of_element_located((By.XPATH, xpath))
                    )
                except:
                    pass  # visibility 체크 실패해도 계속 진행

            if is_attribute:
                value = element.get_attribute(attribute_name)
            else:
                value = element.text.strip()

            if value:
                return value
        except (TimeoutException, NoSuchElementException):
            continue

    return "-"


# 단일 XPath로 요소 추출
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


# 별점
def extract_starpoint(driver, wait_time=10):
    try:
        star_container_xpath_absolute = "/html/body/main/div/div[2]/div[2]/div[2]/div/div[2]/div/div"
        star_container_xpath_relative = "//div[contains(@class, 'inline-flex') and contains(@class, 'items-center')]"

        # 컨테이너 찾기
        container = None
        for xpath in [star_container_xpath_relative, star_container_xpath_absolute]:
            try:
                container = WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
                break
            except (TimeoutException, NoSuchElementException):
                continue

        if not container:
            return None

        # 별 5개 찾기 (각 <i class="relative..."> 안의 <i class="absolute...">)
        # XPath: 각 relative i 안의 absolute i
        star_elements = container.find_elements(By.XPATH, ".//i[contains(@class, 'relative')]//i[contains(@class, 'absolute')]")

        if len(star_elements) != 5:
            # 대안: 직접 absolute i 찾기
            star_elements = container.find_elements(By.XPATH, ".//i[contains(@class, 'absolute') and contains(@class, 'inset-0')]")

        if len(star_elements) == 0:
            return None

        total_score = 0.0

        # 각 별의 width 스타일 추출하여 점수 계산
        for star in star_elements[:5]:  # 최대 5개만 처리
            try:
                style = star.get_attribute('style')
                if style:
                    # style에서 width 값 추출 (예: "width: 100%;" 또는 "width: 50%;")
                    width_match = re.search(r'width:\s*(\d+(?:\.\d+)?)%', style)
                    if width_match:
                        width_percent = float(width_match.group(1))
                        # width를 점수로 변환 (100% = 1.0, 50% = 0.5, 0% = 0.0)
                        score = width_percent / 100.0
                        total_score += score
            except (ValueError, AttributeError) as e:
                continue

        # 점수가 0 이상 5 이하인지 확인
        if 0.0 <= total_score <= 5.0:
            return round(total_score, 1)  # 소수점 첫째 자리까지 반올림
        else:
            return None

    except Exception as e:
        print(f"별점 추출 중 오류: {str(e)}")
        return None


# 상품 URL에서 product_num 추출
def extract_product_num(url):
    # onelink.me 또는 단축 URL 리다이렉트 처리
    if 'onelink.me' in url or '29cm.link' in url:
        try:
            response = requests.head(url, allow_redirects=True, timeout=10)
            url = response.url
        except:
            return None

    # URL에서 /products/ 다음의 숫자 추출
    match = re.search(r'/products/(\d+)', url)
    if match:
        product_num = match.group(1)
        # 총 15자리로 포맷팅: 맨 앞에 3, 중간은 0으로 채움, 끝에 추출한 상품 번호
        total_length = 15
        prefix = "3"
        zeros_needed = total_length - len(prefix) - len(product_num)
        if zeros_needed < 0:
            # 상품 번호가 너무 길면 그대로 반환 (예외 처리)
            try:
                return int(product_num)
            except ValueError:
                return None
        formatted_num = prefix + "0" * zeros_needed + product_num
        try:
            return int(formatted_num)
        except ValueError:
            return None
    
    return None


# 29CM 상품 상세 페이지 크롤링
def crawl_product_details(url):
    driver = setup_driver()

    try:
        print(f"페이지 로딩 중: {url}")
        driver.get(url)

        # 페이지 로딩 대기 (JavaScript 렌더링 고려)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//main"))
        )

        # 추가 대기 (동적 콘텐츠 로딩)
        time.sleep(2)

        # headless 모드에서 요소가 렌더링되도록 페이지 상단으로 스크롤
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.5)

        # 페이지를 약간 스크롤하여 lazy loading 요소 활성화
        driver.execute_script("window.scrollTo(0, 300);")
        time.sleep(1)

        result = {}

        # 1. 쇼핑몰 이름
        result['shoppingmall_name'] = "29CM"

        # 2. 상품 URL
        final_url = driver.current_url
        result['product_url'] = final_url

        # 3. 상품 번호 추출
        product_num = extract_product_num(final_url)
        result['product_num'] = product_num

        # 4. 카테고리 추출
        category_xpath_absolute = "/html/body/main/div/div[1]/div/ul/li[2]/div/div[1]/span"
        category_xpath_relative = "//main//ul//li[2]//span[1] | //nav//span[contains(text(), '/')]"

        # 카테고리 요소로 스크롤 (headless 모드 대응)
        try:
            category_element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, category_xpath_absolute))
            )
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", category_element)
            time.sleep(0.5)
        except:
            pass

        category = extract_by_xpath_with_fallback(
            driver,
            [category_xpath_absolute, category_xpath_relative]
        )

        # 카테고리 분류 로직
        final_category = "기타"

        if category and category != "-":
            category = category.strip()

            # 기본 매핑
            if category == "바지":
                final_category = "하의"
            elif category == "점프수트":
                final_category = "하의"
            elif category == "셋업":
                final_category = "기타"
            elif category == "스커트":
                final_category = "원피스"
            elif category == "니트웨어":
                final_category = "상의"
            elif category == "홈웨어":
                final_category = "기타"
            elif category == "파티복/행사복":
                final_category = "기타"
            elif category == "언더웨어":
                final_category = "기타"
            elif category == "이너웨어":
                final_category = "기타"
            elif category == "상의" :
                final_category = "상의"
            elif category == "원피스" :
                final_category = "원피스"
            elif category == "해외브랜드":
                # 추가 XPath 확인: /html/body/main/div/div[1]/div/ul/li[3]/div/div[1]/span
                sub_category_xpath = "/html/body/main/div/div[1]/div/ul/li[3]/div/div[1]/span"
                try:
                    sub_category_element = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, sub_category_xpath))
                    )
                    sub_category = sub_category_element.text.strip()

                    if sub_category == "아우터":
                        final_category = "아우터"
                    elif sub_category == "티셔츠":
                        final_category = "상의"
                    elif sub_category == "셔츠/블라우스":
                        final_category = "상의"
                    elif sub_category == "니트웨어":
                        final_category = "상의"
                    elif sub_category == "원피스":
                        final_category = "원피스"
                    elif sub_category == "팬츠":
                        final_category = "하의"
                    elif sub_category == "스커트":
                        final_category = "원피스"
                    elif sub_category == "홈웨어":
                        final_category = "기타"
                    elif sub_category == "액티브웨어":
                        final_category = "기타"
                    elif sub_category == "셔츠":
                        final_category = "상의"
                    elif sub_category == "상의" :
                        final_category = "상의"
                    else:
                        final_category = "기타"
                except (TimeoutException, NoSuchElementException):
                    final_category = "기타"
            elif category == "단독":
                # 추가 XPath 확인: /html/body/main/div/div[1]/div/ul/li[3]/div/div[1]/span
                sub_category_xpath = "/html/body/main/div/div[1]/div/ul/li[3]/div/div[1]/span"
                try:
                    sub_category_element = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, sub_category_xpath))
                    )
                    sub_category = sub_category_element.text.strip()

                    if sub_category == "상의":
                        final_category = "상의"
                    elif sub_category == "하의":
                        final_category = "하의"
                    elif sub_category == "아우터":
                        final_category = "아우터"
                    elif sub_category == "원피스":
                        final_category = "원피스"
                    elif sub_category == "홈웨어":
                        final_category = "기타"
                    elif sub_category == "언더웨어":
                        final_category = "기타"
                    else:
                        final_category = "기타"
                except (TimeoutException, NoSuchElementException):
                    final_category = "기타"
            else:
                final_category = "기타"

        result['category'] = final_category

        # 5. 대표 이미지 추출
        image_xpath_absolute = "/html/body/main/div/div[2]/div[2]/div[1]/section/div/div/div[1]/div[1]/img"
        image_xpath_relative = "//main//section//img[1] | //div[contains(@class, 'product')]//img[1] | //div[contains(@class, 'image')]//img[1]"

        image_url = extract_by_xpath_with_fallback(
            driver,
            [image_xpath_relative, image_xpath_absolute],
            is_attribute=True,
            attribute_name='src'
        )
        result['product_img_url'] = image_url if image_url else "-"

        # 6. 상품명 추출
        product_name_xpath_id = "//*[@id='pdp_product_name']"
        product_name_xpath_fallback = "//h1[contains(@class, 'product')] | //div[contains(@class, 'product-name')] | //h1"

        product_name = extract_by_xpath_with_fallback(
            driver,
            [product_name_xpath_id, product_name_xpath_fallback]
        )
        result['product_name'] = product_name if product_name else "-"

        # 7. 브랜드명 추출
        brand_xpath_absolute = "/html/body/main/div/div[2]/div[1]/div/div/a/div/div/h3/span"
        brand_xpath_relative = "//main//h3//span | //a[contains(@href, 'brand')]//span | //div[contains(@class, 'brand')]//span"

        # 브랜드명 요소로 스크롤 (headless 모드 대응)
        try:
            brand_element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, brand_xpath_absolute))
            )
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", brand_element)
            time.sleep(0.5)
        except:
            pass

        brand_name = extract_by_xpath_with_fallback(
            driver,
            [brand_xpath_absolute, brand_xpath_relative]
        )
        result['brand_name'] = brand_name if brand_name else "-"

        # 8. 가격 추출
        price_xpath_id = "//*[@id='pdp_product_price']"
        price_xpath_fallback = "//div[contains(@class, 'price')]//span | //span[contains(@class, 'price')] | //div[contains(text(), ',') and contains(text(), '원')]"

        price = extract_by_xpath_with_fallback(
            driver,
            [price_xpath_id, price_xpath_fallback]
        )

        if price:
            price = price.strip()
            if not price.endswith('원'):
                numbers = re.findall(r'[\d,]+', price)
                if numbers:
                    price = numbers[0] + '원'
                else:
                    price = price + '원'
        else:
            price = "-"

        result['price'] = price

        # 9. 별점 추출
        starpoint = extract_starpoint(driver)
        result['star_point'] = starpoint

        # 10. AI 리뷰
        result['AI_review'] = None

        return result

    except Exception as e:
        print(f"크롤링 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        # 예외 발생 시 리다이렉트된 URL 우선 사용, 없으면 요청 URL 사용
        try:
            fallback_url = driver.current_url
        except Exception:
            fallback_url = url
        product_num = extract_product_num(fallback_url)
        return {"shoppingmall_name": "29CM", "product_url": fallback_url, "product_num": product_num, "category": "-", "product_img_url": "-", "product_name": "-", "brand_name": "-", "price": "-", "star_point": None, "AI_review": None}

    finally:
        driver.quit()

