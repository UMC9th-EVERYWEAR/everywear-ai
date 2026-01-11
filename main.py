#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#####################################
# FastAPI 서버 - 무신사 상품 크롤링 API #
#####################################

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Optional
import sys
import os

# scripts 폴더의 crawl_musinsa 모듈 import
scripts_path = os.path.join(os.path.dirname(__file__), 'scripts')
if scripts_path not in sys.path:
    sys.path.insert(0, scripts_path)

# crawl_musinsa 모듈 import
try:
    from crawl_musinsa import crawl_product_details
except ImportError as e:
    print(f"crawl_musinsa 모듈 import 실패: {e}", file=sys.stderr)
    raise

app = FastAPI(title="EveryWear AI API", version="1.0.0")

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


@app.get("/")
async def root():
    return {"message": "EveryWear AI API Server", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# 무신사 상품 URL을 받아 크롤링해서 상품 정보를 반환함.
@app.post("/crawl/musinsa", response_model=CrawlResponse)
async def crawl_musinsa_product(request: CrawlRequest):
    try:
        result = crawl_product_details(request.product_url)
        
        # star_point 처리 (크롤링에서 None 또는 float 반환, None은 그대로 유지)
        star_point = result.get('star_point')
        if star_point is None:
            star_point = None
        elif isinstance(star_point, str):
            # 문자열인 경우 숫자로 변환 시도 (예외 처리)
            try:
                star_point = float(star_point)
            except (ValueError, TypeError):
                star_point = None
        
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
