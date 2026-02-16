# EveryWear AI Crawler
EveryWear AI는 외부 쇼핑몰(무신사, 지그재그, W컨셉, 29CM)의 상품과 리뷰 정보를 크롤링하고, 카테고리 분류를 수행하여 EveryWear Backend에 제공하는 **FastAPI 기반 크롤링 보조 서버**입니다.


## 💻 Tech Stack
- **Framework/Language**: FastAPI, Python 3.x
- **Server**: Uvicorn
- **Crawling**: Selenium (Chrome/Chromium), webdriver-manager, requests
- **Validation**: Pydantic
- **Database**: PyMySQL (MySQL 클라이언트), cryptography
- **AI**: Gemini API (gemini-2.5-flash)
- **Deploy**: Docker (Chrome headless 환경)


## **📂 Project Structure**
```
everywear-ai/
├── .github/                       # Issue/PR 템플릿 및 CI/CD 설정
├── scripts/                       # 크롤링 및 AI 연동 스크립트
│   ├── crawl_musinsa.py           # 무신사 상품 상세 크롤링
│   ├── crawl_musinsa_reviews.py   # 무신사 리뷰 수집
│   ├── crawl_zigzag.py            # 지그재그 상품 상세 크롤링
│   ├── crawl_zigzag_reviews.py    # 지그재그 리뷰 수집
│   ├── ...
│   └── db_handler.py              # DB 연결 유틸
├── main.py                        # FastAPI 진입점 (상품/리뷰 크롤링 API)
├── requirements.txt
├── Dockerfile
└── README.md
```

## **🛠️ Architecture**
<img width="1005" height="541" alt="스크린샷 2026-02-12 오후 7 13 10" src="https://github.com/user-attachments/assets/7795c4ee-5704-4878-a025-5a8d9c837b2c" />


## **🚀** Getting Started
1. 가상환경 생성 및 활성화
```bash
# 가상환경 생성
python -m venv .venv
# 가상환경 활성화
# Windows:
.venv\\Scripts\\activate
# Linux/Mac:
source .venv/bin/activate
```

2. 의존성 설치
```bash
pip install -r requirements.txt
```

3. FastAPI 서버 실행
```bash
uvicorn main:app --port 8001 --reload
# 또는
python main.py
```

서버 실행 후 다음 URL에서 Swagger UI를 확인할 수 있습니다:
- 로컬 스웨거 : `http://localhost:8001/docs`
- 서버 스웨거 : `http://dev-app-alb-160354142.ap-northeast-2.elb.amazonaws.com/crawler/docs`


## **📝 Commit Convention**
| type | 의미 | 예시 |
| --- | --- | --- |
| ✨ **feat** | 새로운 기능 | 로그인 API 구현 |
| 🐞 **fix** | 버그 수정 | NPE 해결 |
| 📝 **docs** | 문서 수정 | README 업데이트 |
| ⚙️ **setting** | 프로젝트/환경 설정 | yml, CI |
| **♻️ refactor** | 기능 변화 없는 코드 리팩터링 | Service 분리 |
| 🎨 **style** | 포맷/세미콜론/네이밍 등 | 포맷팅, 공백 |
| 🧪 **test** | 테스트 코드 | Controller 단위 테스트 |
| 🧹 **chore** | 패키지 관리, 기타잡무 | Gradle 설정 변경 |
