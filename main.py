#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#####################################
# FastAPI 서버 - 통일된 리뷰 응답 ###
#####################################

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import sys
import os
import asyncio
import json

# scripts 폴더 경로 추가
scripts_path = os.path.join(os.path.dirname(__file__), 'scripts')
if scripts_path not in sys.path:
    sys.path.insert(0, scripts_path)

# 상품 크롤링 모듈
try:
    from crawl_musinsa import crawl_product_details
    from crawl_zigzag import crawl_product_details as crawl_zigzag_product_details
    from crawl_29cm import crawl_product_details as crawl_29cm_product_details
    from crawl_wconcept import crawl_product_details as crawl_wconcept_product_details
except ImportError as e:
    print(f"상품 크롤링 모듈 import 실패: {e}", file=sys.stderr)
    raise

# 리뷰 크롤링 모듈 (통일 형식)
try:
    from crawl_musinsa_reviews import extract_product_no_from_url, collect_reviews
    from crawl_zigzag_reviews import crawl_zigzag_reviews
    from crawl_29cm_reviews import extract_item_id_from_url, collect_29cm_reviews
    from crawl_wconcept_reviews import collect_wconcept_reviews
except ImportError as e:
    print(f"리뷰 크롤링 모듈 import 실패: {e}", file=sys.stderr)
    raise

app = FastAPI(
    title="EveryWear AI API",
    version="2.0.0",
    root_path="/crawler"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================================
# 요청 모델
# ========================================

class CrawlRequest(BaseModel):
    product_url: str

class ReviewCrawlRequest(BaseModel):
    product_url: str
    review_count: Optional[int] = 20

# ========================================
# 응답 모델 - 상품
# ========================================

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

# ========================================
# 응답 모델 - 리뷰 (통일 형식)
# ========================================

class UnifiedReviewItem(BaseModel):
    """통일된 리뷰 아이템 (7개 필드)"""
    rating: int  # 별점 (1~5)
    content: str
    review_date: str
    images: List[str]
    user_height: Optional[int] = None
    user_weight: Optional[int] = None
    option_text: Optional[str] = None

class UnifiedReviewResponse(BaseModel):
    """통일된 리뷰 응답"""
    product_url: str
    total_reviews: int
    reviews: List[UnifiedReviewItem]

# ========================================
# 헬스 체크
# ========================================

@app.get("/")
async def root():
    return {"message": "EveryWear AI API Server (Unified Review)", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# ========================================
# 상품 크롤링 엔드포인트
# ========================================

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
            AI_review=result.get('AI_review')
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
            AI_review=result.get('AI_review')
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
            AI_review=result.get('AI_review')
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
            AI_review=result.get('AI_review')
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"크롤링 중 오류 발생: {str(e)}")

# ========================================
# 리뷰 크롤링 엔드포인트 (통일 형식)
# ========================================

@app.post("/crawl/musinsa/reviews", response_model=UnifiedReviewResponse)
async def crawl_musinsa_reviews(request: ReviewCrawlRequest):
    """무신사 리뷰 크롤링 (통일 형식)"""
    try:
        goods_no = extract_product_no_from_url(request.product_url)
        if not goods_no:
            raise HTTPException(status_code=400, detail="상품번호를 추출할 수 없습니다.")

        reviews = await asyncio.to_thread(collect_reviews, goods_no, request.review_count)
        if not reviews:
            raise HTTPException(status_code=404, detail="리뷰를 찾을 수 없습니다.")

        return UnifiedReviewResponse(
            product_url=request.product_url,
            total_reviews=len(reviews),
            reviews=[UnifiedReviewItem(**r) for r in reviews]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"리뷰 크롤링 중 오류 발생: {str(e)}")

@app.post("/crawl/zigzag/reviews", response_model=UnifiedReviewResponse)
async def crawl_zigzag_product_reviews(request: ReviewCrawlRequest):
    """지그재그 리뷰 크롤링 (통일 형식)"""
    try:
        max_reviews = request.review_count if request.review_count else 20
        reviews = await asyncio.to_thread(crawl_zigzag_reviews, request.product_url, max_reviews)
        
        return UnifiedReviewResponse(
            product_url=request.product_url,
            total_reviews=len(reviews),
            reviews=[UnifiedReviewItem(**r) for r in reviews]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"리뷰 크롤링 중 오류 발생: {str(e)}")

@app.post("/crawl/29cm/reviews", response_model=UnifiedReviewResponse)
async def crawl_29cm_product_reviews(request: ReviewCrawlRequest):
    """29cm 리뷰 크롤링 (통일 형식)"""
    try:
        item_id = extract_item_id_from_url(request.product_url)
        if not item_id:
            raise HTTPException(status_code=400, detail="상품 ID를 추출할 수 없습니다.")

        max_reviews = request.review_count if request.review_count else 20
        reviews = await asyncio.to_thread(collect_29cm_reviews, request.product_url, max_reviews)
        
        if not reviews:
            raise HTTPException(status_code=404, detail="리뷰를 찾을 수 없습니다.")

        return UnifiedReviewResponse(
            product_url=request.product_url,
            total_reviews=len(reviews),
            reviews=[UnifiedReviewItem(**r) for r in reviews]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"리뷰 크롤링 중 오류 발생: {str(e)}")

@app.post("/crawl/wconcept/reviews", response_model=UnifiedReviewResponse)
async def crawl_wconcept_product_reviews(request: ReviewCrawlRequest):
    """W컨셉 리뷰 크롤링 (통일 형식)"""
    try:
        max_reviews = request.review_count if request.review_count else 20
        reviews = await asyncio.to_thread(collect_wconcept_reviews, request.product_url, max_reviews)
        
        if not reviews:
            raise HTTPException(status_code=404, detail="해당 상품의 리뷰를 찾을 수 없습니다.")

        return UnifiedReviewResponse(
            product_url=request.product_url,
            total_reviews=len(reviews),
            reviews=[UnifiedReviewItem(**r) for r in reviews]
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"[CRITICAL] WConcept Reviews Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"서버 내부 오류: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)