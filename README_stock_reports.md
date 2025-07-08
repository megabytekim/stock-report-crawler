# Telegram Stock Reports Bot

이 스크립트는 네이버 금융에서 어제 등록된 투자 리포트를 자동으로 수집하고, PDF의 첫 페이지를 요약한 후 텔레그램으로 전송하는 봇입니다.

## 주요 기능

- 📊 네이버 금융에서 어제 등록된 투자 리포트 자동 수집
- 📄 PDF 첫 페이지 텍스트 추출
- 🤖 OpenAI GPT를 사용한 투자 리포트 요약
- 📱 텔레그램 채널로 요약된 리포트 전송
- ⏰ 중복 방지 및 속도 제한 고려

## 설치 및 설정

### 1. 의존성 설치

```bash
pip install -r requirements_stock_reports.txt
```

### 2. 환경 변수 설정

`.env` 파일을 생성하고 다음 변수들을 설정하세요:

```env
# Telegram API 설정
TELEGRAM_API_ID=your_telegram_api_id
TELEGRAM_API_HASH=your_telegram_api_hash

# 텔레그램 채널 설정
TARGET_CHANNEL=@your_target_channel
TEST_TARGET_CHANNEL=@your_test_channel

# OpenAI API 설정
OPEN_API_KEY=your_openai_api_key

# 테스트 모드 (선택사항)
TEST_MODE=false
```

### 3. Telegram API 설정

1. [my.telegram.org](https://my.telegram.org)에 접속
2. 로그인 후 "API development tools" 클릭
3. 새로운 앱 생성
4. `api_id`와 `api_hash`를 `.env` 파일에 입력

### 4. OpenAI API 설정

1. [OpenAI Platform](https://platform.openai.com)에서 API 키 생성
2. `.env` 파일의 `OPEN_API_KEY`에 입력

## 사용법

### 기본 실행

```bash
python telegram_stock_reports.py
```

### 스케줄링 (cron 사용)

매일 오전 9시에 실행하려면:

```bash
# crontab 편집
crontab -e

# 다음 줄 추가
0 9 * * * cd /path/to/your/project && python telegram_stock_reports.py
```

## 작동 방식

1. **날짜 확인**: 어제 날짜를 YYYYMMDD 형식으로 계산
2. **웹 스크래핑**: 네이버 금융 페이지를 순회하며 어제 등록된 리포트 검색
3. **PDF 다운로드**: 각 리포트의 PDF 파일 다운로드
4. **텍스트 추출**: PDF 첫 페이지에서 텍스트 추출
5. **AI 요약**: OpenAI GPT를 사용하여 투자 관점에서 요약
6. **텔레그램 전송**: 요약된 내용을 텔레그램 채널로 전송

## 출력 형식

텔레그램 메시지 형식:

```
📊 **회사명 투자 리포트**

🏢 **연구사**: 연구사명
📋 **제목**: 리포트 제목
📅 **날짜**: YYYYMMDD
👁️ **조회수**: 조회수

📝 **요약**:
AI가 생성한 투자 요약 내용

🔗 **원본 PDF**: [다운로드](PDF_URL)
```

## 주의사항

- **속도 제한**: 네이버 서버와 텔레그램 API 속도 제한을 고려하여 적절한 딜레이 설정
- **API 비용**: OpenAI API 사용 시 토큰당 비용 발생
- **PDF 품질**: 일부 PDF는 텍스트 추출이 어려울 수 있음
- **네트워크**: 안정적인 인터넷 연결 필요

## 문제 해결

### 일반적인 오류

1. **텔레그램 연결 실패**
   - API ID와 Hash 확인
   - 인터넷 연결 상태 확인

2. **PDF 텍스트 추출 실패**
   - PDF가 이미지 기반인 경우 텍스트 추출 불가
   - PyPDF2 버전 확인

3. **OpenAI API 오류**
   - API 키 유효성 확인
   - API 사용량 한도 확인

### 로그 확인

스크립트 실행 시 상세한 로그가 출력됩니다. 오류 발생 시 로그를 확인하여 문제를 파악하세요.

## 커스터마이징

### 요약 프롬프트 수정

`summarize_pdf_with_llm` 함수의 system prompt를 수정하여 요약 스타일을 변경할 수 있습니다.

### 검색 페이지 수 조정

`scrape_yesterday_reports` 함수의 `max_pages` 변수를 수정하여 검색할 페이지 수를 조정할 수 있습니다.

### 딜레이 조정

각 함수의 `time.sleep()` 값을 수정하여 요청 간격을 조정할 수 있습니다. 