# LostArk API

로스트아크와 관련된 정보를 제공하는 API입니다.

---

## 📦 기본 설정

### 1. Redis 설치
Redis를 사용하여 데이터를 저장 및 관리합니다. 아래 방법 중 하나를 선택하여 설치하세요.

#### Docker로 설치
```bash
docker pull redis
docker run -d --name lostark-redis -p 6379:6379 redis
```

또는

#### Windows에서 직접 설치
[Redis Releases](https://github.com/microsoftarchive/redis/releases) 페이지에서 설치 파일을 다운로드하고 설치를 진행하세요.

---

### 2. 패키지 설치
필요한 Python 패키지를 설치합니다.

```bash
pip install -r requirements.txt
```

---

### 3. 설정 파일 구성
설정 파일을 구성하여 API 연동 및 데이터 캐시 설정을 완료하세요.

1. **`config_example` 폴더를 참고하여 `config` 폴더를 생성**합니다.
2. 아래 파일들을 `config` 폴더에 추가하고 적절히 수정하세요.

   - **`azure_config.json`**: Azure Cognitive Search 설정 (로스트아크 관련 RAG 연동)
   - **`genai_api.json`**: RAG를 위한 AI API 설정
   - **`stove_api.json`**: Stove API 키 설정
   - **`crawl_cache.json`**: 거래소 크롤링을 위한 캐시 설정 (SUAT 키, 유효시간 존재)

---

### 4. 실행
API 서버를 실행합니다. 아래 명령어 중 하나를 선택하여 실행하세요.

#### Uvicorn로 실행
```bash
uvicorn main:app --host 0.0.0.0 --port 80 --reload
```

또는

#### Python으로 실행
```bash
python main.py
```

---

## 🌐 테스트
서버 실행 후 [127.0.0.1](http://127.0.0.1)에 접속하여 API를 테스트할 수 있습니다.

> 자세한 내용은 각 엔드포인트의 주석을 참고해주세요!

---

### 📩 문의
API 사용 중 궁금한 점이 있다면 [디스코드 문의 채널](https://discord.gg/hx4Mb3NBWg)로 문의해주세요.