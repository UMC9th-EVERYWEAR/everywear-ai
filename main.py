#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#####################################
# FastAPI 서버 - 무신사 상품 크롤링 API #
#####################################

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import sys
import os
import asyncio

# scripts 폴더의 crawl_musinsa 모듈 import
scripts_path = os.path.join(os.path.dirname(__file__), 'scripts')
if scripts_path not in sys.path:
    sys.path.insert(0, scripts_path)

# crawl_musinsa 모듈 import
try:
    from crawl_musinsa import crawl_product_details
    from crawl_musinsa_reviews import extract_product_no_from_url, collect_reviews
except ImportError as e:
    print(f"crawl_musinsa 모듈 import 실패: {e}", file=sys.stderr)
    raise

# crawl_zigzag 모듈 import
try:
    from crawl_zigzag import crawl_product_details as crawl_zigzag_product_details
    from crawl_zigzag_reviews import crawl_zigzag_reviews
except ImportError as e:
    print(f"crawl_zigzag 모듈 import 실패: {e}", file=sys.stderr)
    raise

# crawl_29cm 모듈 import
try:
    from crawl_29cm import crawl_product_details as crawl_29cm_product_details
    from crawl_29cm_reviews import extract_item_id_from_url, collect_29cm_reviews
except ImportError as e:
    print(f"crawl_29cm 모듈 import 실패: {e}", file=sys.stderr)
    raise

# crawl_wconcept 모듈 import
try:
    from crawl_wconcept import crawl_product_details as crawl_wconcept_product_details
    from crawl_wconcept_reviews import collect_wconcept_reviews
except ImportError as e:
    print(f"crawl_wconcept 모듈 import 실패: {e}", file=sys.stderr)
    raise

app = FastAPI(
    title="EveryWear AI API",
    version="1.0.0",
    root_path="/crawler"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 요청 모델
class CrawlRequest(BaseModel):
    product_url: str


class ReviewCrawlRequest(BaseModel):
    product_url: str
    review_count: Optional[int] = 20


# 응답 모델
class CrawlResponse(BaseModel):
    shoppingmall_name: str
    product_url: str
    category: str
    product_img_url: str
    product_name: str
    brand_name: str
    price: str
    star_point: Optional[float] = None
    AI_review: Optional[str] = None
    product_num: Optional[int] = None


class UserInfo(BaseModel):
    sex: str
    height: str
    weight: str


class ReviewItem(BaseModel):
    product_no: str
    review_no: str
    content: str
    date: str
    score: int
    option: str
    user_info: UserInfo
    satisfaction: Dict[str, str]
    help_count: int
    images: List[str]


class ReviewCrawlResponse(BaseModel):
    product_no: str
    product_url: str
    total_reviews: int
    reviews: List[ReviewItem]


# 지그재그 리뷰용 응답 모델
class ZigzagReviewerInfo(BaseModel):
    nickname: Optional[str] = None


class ZigzagReviewItem(BaseModel):
    reviewer_info: ZigzagReviewerInfo
    satisfaction: Dict[str, str]
    review_content: str
    star_rating: Optional[float] = None
    review_images: List[str]
    review_date: Optional[str] = None


class ZigzagReviewCrawlResponse(BaseModel):
    product_url: str
    total_reviews: int
    reviews: List[ZigzagReviewItem]


# 29cm 리뷰용 응답 모델
class Cm29UserInfo(BaseModel):
    height: str
    weight: str


class Cm29ReviewItem(BaseModel):
    item_id: str
    review_id: str
    user_id: str
    rating: float
    content: str
    option: str
    date: str
    user_info: Cm29UserInfo
    images: List[str]
    is_gift: bool


class Cm29ReviewCrawlResponse(BaseModel):
    item_id: str
    product_url: str
    total_reviews: int
    reviews: List[Cm29ReviewItem]

# W concept 리뷰용 응답 모델
class WconceptReviewItem(BaseModel):
    score: float
    option: str
    user_id: str
    date: str
    satisfaction: Dict[str, str]
    content: str
    images: List[str]

class WconceptReviewCrawlResponse(BaseModel):
    product_url: str
    total_reviews: int
    reviews: List[WconceptReviewItem]


@app.get("/")
async def root():
    return {"message": "EveryWear AI API Server", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


def _normalize_star_point(result: dict) -> Optional[float]:
    star_point = result.get('star_point')
    if star_point is None:
        return None
    if isinstance(star_point, str):
        try:
            return float(star_point)
        except (ValueError, TypeError):
            return None
    if isinstance(star_point, (int, float)):
        return float(star_point)
    return None


# 무신사 상품 URL을 받아 크롤링해서 상품 정보를 반환함.
@app.post("/crawl/musinsa", response_model=CrawlResponse)
async def crawl_musinsa_product(request: CrawlRequest):
    try:
        result = await asyncio.to_thread(crawl_product_details, request.product_url)
        star_point = _normalize_star_point(result)

        return CrawlResponse(
            shoppingmall_name=result.get('shoppingmall_name', '무신사'),
            product_url=result.get('product_url', request.product_url),
            category=result.get('category', '-'),
            product_img_url=result.get('product_img_url', '-'),
            product_name=result.get('product_name', '-'),
            brand_name=result.get('brand_name', '-'),
            price=result.get('price', '-'),
            star_point=star_point,
            AI_review=result.get('AI_review'),
            product_num=result.get('product_num')
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"크롤링 중 오류 발생: {str(e)}")


# 지그재그 상품 URL을 받아 크롤링해서 상품 정보를 반환함.
@app.post("/crawl/zigzag", response_model=CrawlResponse)
async def crawl_zigzag_product(request: CrawlRequest):
    try:
        result = await asyncio.to_thread(crawl_zigzag_product_details, request.product_url)
        star_point = _normalize_star_point(result)

        return CrawlResponse(
            shoppingmall_name=result.get('shoppingmall_name', '지그재그'),
            product_url=result.get('product_url', request.product_url),
            category=result.get('category', '-'),
            product_img_url=result.get('product_img_url', '-'),
            product_name=result.get('product_name', '-'),
            brand_name=result.get('brand_name', '-'),
            price=result.get('price', '-'),
            star_point=star_point,
            AI_review=result.get('AI_review'),
            product_num=result.get('product_num')
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"크롤링 중 오류 발생: {str(e)}")


# 29cm 상품 URL을 받아 크롤링해서 상품 정보를 반환함.
@app.post("/crawl/29cm", response_model=CrawlResponse)
async def crawl_29cm_product(request: CrawlRequest):
    try:
        result = await asyncio.to_thread(crawl_29cm_product_details, request.product_url)
        star_point = _normalize_star_point(result)

        return CrawlResponse(
            shoppingmall_name=result.get('shoppingmall_name', '29CM'),
            product_url=result.get('product_url', request.product_url),
            category=result.get('category', '-'),
            product_img_url=result.get('product_img_url', '-'),
            product_name=result.get('product_name', '-'),
            brand_name=result.get('brand_name', '-'),
            price=result.get('price', '-'),
            star_point=star_point,
            AI_review=result.get('AI_review'),
            product_num=result.get('product_num')
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"크롤링 중 오류 발생: {str(e)}")


# W컨셉 상품 URL을 받아 크롤링해서 상품 정보를 반환함.
@app.post("/crawl/wconcept", response_model=CrawlResponse)
async def crawl_wconcept_product(request: CrawlRequest):
    try:
        result = await asyncio.to_thread(crawl_wconcept_product_details, request.product_url)
        star_point = _normalize_star_point(result)

        return CrawlResponse(
            shoppingmall_name=result.get('shoppingmall_name', 'W컨셉'),
            product_url=result.get('product_url', request.product_url),
            category=result.get('category', '-'),
            product_img_url=result.get('product_img_url', '-'),
            product_name=result.get('product_name', '-'),
            brand_name=result.get('brand_name', '-'),
            price=result.get('price', '-'),
            star_point=star_point,
            AI_review=result.get('AI_review'),
            product_num=result.get('product_num')
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"크롤링 중 오류 발생: {str(e)}")


# 무신사 리뷰 크롤링 API
@app.post("/crawl/musinsa/reviews", response_model=ReviewCrawlResponse)
async def crawl_musinsa_reviews(request: ReviewCrawlRequest):
    """
    무신사 상품 리뷰를 크롤링합니다.
    - 일반 URL: https://www.musinsa.com/products/5432652
    - 원클릭 URL: https://musinsa.onelink.me/ANAQ/xxxxx
    """
    try:
        goods_no = extract_product_no_from_url(request.product_url)
        if not goods_no:
            raise HTTPException(status_code=400, detail="상품번호를 추출할 수 없습니다.")

        reviews = collect_reviews(goods_no, target_total=request.review_count)
        if not reviews:
            raise HTTPException(status_code=404, detail="리뷰를 찾을 수 없습니다.")

        review_items: List[ReviewItem] = []
        for review in reviews:
            review_items.append(ReviewItem(
                product_no=review['product_no'],
                review_no=review['review_no'],
                content=review['content'],
                date=review['date'],
                score=review['score'],
                option=review['option'],
                user_info=UserInfo(**review['user_info']),
                satisfaction=review['satisfaction'],
                help_count=review['help_count'],
                images=review['images']
            ))

        return ReviewCrawlResponse(
            product_no=goods_no,
            product_url=request.product_url,
            total_reviews=len(review_items),
            reviews=review_items
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"리뷰 크롤링 중 오류 발생: {str(e)}")


# 지그재그 리뷰 크롤링 API
@app.post("/crawl/zigzag/reviews", response_model=ZigzagReviewCrawlResponse)
async def crawl_zigzag_product_reviews(request: ReviewCrawlRequest):
    """
    지그재그 상품 리뷰를 크롤링합니다.
    - URL: https://zigzag.kr/catalog/products/143224732
    """
    try:
        # review_count 필드 사용 (기존 ReviewCrawlRequest 모델 유지)
        max_reviews = request.review_count if request.review_count else 20
        
        # 크롤링 실행 (asyncio로 비동기 처리)
        reviews = await asyncio.to_thread(crawl_zigzag_reviews, request.product_url, max_reviews)
        
        return ZigzagReviewCrawlResponse(
            product_url=request.product_url,
            total_reviews=len(reviews),
            reviews=reviews
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"리뷰 크롤링 중 오류 발생: {str(e)}")


# 29cm 리뷰 크롤링 API
@app.post("/crawl/29cm/reviews", response_model=Cm29ReviewCrawlResponse)
async def crawl_29cm_product_reviews(request: ReviewCrawlRequest):
    """
    29cm 상품 리뷰를 크롤링합니다 (Selenium 사용).
    - URL: https://www.29cm.co.kr/products/3437237?categoryLargeCode=...
    """
    try:
        # URL에서 item_id 추출
        item_id = extract_item_id_from_url(request.product_url)
        if not item_id:
            raise HTTPException(status_code=400, detail="상품 ID를 추출할 수 없습니다.")

        # 리뷰 수집 (URL 전체를 전달!)
        max_reviews = request.review_count if request.review_count else 20
        reviews = await asyncio.to_thread(collect_29cm_reviews, request.product_url, max_reviews)
        #                                                        ^^^^^^^^^^^^^^^^^^^
        #                                                        URL 전체 전달로 변경
        
        if not reviews:
            raise HTTPException(status_code=404, detail="리뷰를 찾을 수 없습니다.")

        # 응답 모델로 변환
        review_items: List[Cm29ReviewItem] = []
        for review in reviews:
            review_items.append(Cm29ReviewItem(
                item_id=review['item_id'],
                review_id=review['review_id'],
                user_id=review['user_id'],
                rating=review['rating'],
                content=review['content'],
                option=review['option'],
                date=review['date'],
                user_info=Cm29UserInfo(**review['user_info']),
                images=review['images'],
                is_gift=review['is_gift']
            ))

        return Cm29ReviewCrawlResponse(
            item_id=item_id,
            product_url=request.product_url,
            total_reviews=len(review_items),
            reviews=review_items
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"리뷰 크롤링 중 오류 발생: {str(e)}")

@app.post("/crawl/wconcept/reviews", response_model=WconceptReviewCrawlResponse)
async def crawl_wconcept_product_reviews(request: ReviewCrawlRequest):
    try:
        max_reviews = request.review_count if request.review_count else 20
        # asyncio.to_thread를 통해 비동기로 실행
        reviews = await asyncio.to_thread(collect_wconcept_reviews, request.product_url, max_reviews)
        
        # 리뷰가 하나도 수집되지 않았을 때 404를 명시적으로 반환 (500 방지)
        if not reviews:
            raise HTTPException(status_code=404, detail="해당 상품의 리뷰를 찾을 수 없습니다. (리뷰가 없거나 로딩 실패)")

        # 응답 데이터 구성
        return WconceptReviewCrawlResponse(
            product_url=request.product_url,
            total_reviews=len(reviews),
            reviews=reviews
        )
    except HTTPException as he:
        raise he # 정의된 HTTP 에러는 그대로 던짐
    except Exception as e:
        # 실제 어떤 에러가 났는지 로그 출력
        print(f"[CRITICAL] WConcept Reviews Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"서버 내부 오류: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
