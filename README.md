# EveryWear AI - FastAPI 서버

무신사 상품 크롤링을 위한 FastAPI 서버입니다.

## 설치 및 실행

### 1. 가상환경 생성 및 활성화

```bash
# 가상환경 생성
python -m venv .venv

# 가상환경 활성화
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. FastAPI 서버 실행

```bash
uvicorn main:app --port 8001 --reload
```

또는

```bash
python main.py
```

서버가 실행되면 `http://localhost:8001`에서 접근할 수 있습니다.

## API 엔드포인트

### 1. 헬스 체크
- **GET** `/health`
- 서버 상태 확인

### 2. 무신사 상품 크롤링
- **POST** `/crawl/musinsa`
- 요청 본문:
  ```json
  {
    "product_url": "https://www.musinsa.com/products/..."
  }
  ```
- 응답:
  ```json
  {
    "shoppingmall_name": "무신사",
    "product_url": "https://www.musinsa.com/products/...",
    "category": "상의",
    "product_img_url": "https://...",
    "product_name": "상품명",
    "brand_name": "브랜드명",
    "price": "29,000원",
    "star_point": 4.5,
    "AI_review": null
  }
  ```

## API 문서

서버 실행 후 다음 URL에서 Swagger UI를 확인할 수 있습니다:
- 로컬 스웨거 : `http://localhost:8001/docs`
- 서버 스웨거 : `http://dev-app-alb-160354142.ap-northeast-2.elb.amazonaws.com/crawler/docs`
