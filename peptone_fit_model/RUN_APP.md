# Streamlit 앱 실행 가이드

## Phase 4: Web UI 시작하기

### 1. 설치 확인

```bash
# 현재 디렉토리 확인
cd D:\folder1\peptone_fit_model

# 필요한 패키지가 설치되어 있는지 확인
pip list | grep streamlit
pip list | grep plotly
```

### 2. Streamlit 앱 실행

```bash
# 기본 실행
streamlit run app.py

# 또는 포트 지정
streamlit run app.py --server.port 8501
```

### 3. 브라우저에서 접속

앱이 실행되면 자동으로 브라우저가 열립니다.

기본 주소: `http://localhost:8501`

### 4. 주요 기능

#### 🏠 Home
- 시스템 개요
- 데이터베이스 현황
- Quick start 가이드

#### 🔍 Single Recommendation
- 개별 균주 선택
- 단일 펩톤 추천
- Interactive 차트
- CSV/HTML 내보내기

#### ⚗️ Blend Optimization
- 최적화된 블렌드 생성
- scipy 알고리즘 사용
- 배합비 시각화
- 상세 점수 분석

#### 📊 Batch Processing
- 여러 균주 일괄 처리
- 카테고리별 필터링
- 결과 일괄 다운로드

#### 📈 Advanced Analysis
- 데이터베이스 탐색
- 민감도 분석
- 커스텀 최적화

#### ℹ️ About
- 시스템 정보
- 알고리즘 설명
- 문서 링크

### 5. 문제 해결

#### 앱이 시작되지 않음

```bash
# streamlit 재설치
pip uninstall streamlit
pip install streamlit

# 캐시 초기화
streamlit cache clear
```

#### 데이터 파일을 찾을 수 없음

`app.py` 파일의 `load_databases()` 함수에서 파일 경로 확인:

```python
strain_file = Path(r"D:\folder1\★신사업1팀 균주 리스트 (2024 ver.).xlsx")
peptone_file = Path(r"D:\folder1\composition_template.xlsx")
```

필요시 경로 수정

#### 메모리 부족

```bash
# 가벼운 모드로 실행
streamlit run app.py --server.maxUploadSize 50
```

#### 포트가 이미 사용 중

```bash
# 다른 포트 사용
streamlit run app.py --server.port 8502
```

### 6. 앱 설정

`~/.streamlit/config.toml` 파일을 생성하여 설정 커스터마이즈:

```toml
[server]
port = 8501
enableCORS = false

[theme]
primaryColor = "#3498db"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"
```

### 7. 성능 최적화

#### 캐싱 활용

앱은 자동으로 데이터를 캐싱하여 성능 향상:
- `@st.cache_resource`: 데이터베이스 로딩
- `@st.cache_data`: 계산 결과

#### 메모리 관리

- 대량의 균주 처리 시 Batch 크기 제한 (최대 10개)
- 불필요한 시각화 최소화

### 8. 팁

#### 키보드 단축키

- `R`: 앱 새로고침
- `C`: 캐시 초기화
- `Ctrl + Enter`: 코드 실행

#### 사이드바 활용

- 설정을 사이드바에서 조정
- 네비게이션 메뉴 사용

#### 세션 상태

- 페이지 전환 시 결과 유지
- 브라우저 새로고침 시 초기화

### 9. 배포 (선택사항)

#### Streamlit Cloud

```bash
# GitHub에 push
git add .
git commit -m "Add Streamlit app"
git push

# streamlit.io에서 배포
```

#### Docker

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501
CMD ["streamlit", "run", "app.py"]
```

### 10. 스크린샷 (예상)

**Home Page:**
- Welcome message
- Database statistics
- Strain distribution pie chart

**Single Recommendation:**
- Strain selector
- Settings panel
- Results table
- Score comparison chart
- Detailed radar chart
- Amino acid heatmap

**Blend Optimization:**
- Optimization settings
- Optimized blend list
- Composition pie charts
- Score breakdown

**Batch Processing:**
- Multi-strain selector
- Progress bar
- Results table
- Summary statistics
- Download button

### 11. 데모 워크플로우

1. **Home** 페이지에서 시스템 확인
2. **Single Recommendation**으로 이동
3. "KCCM 12116" 균주 선택
4. "Generate Recommendations" 클릭
5. 결과 확인 및 차트 탐색
6. CSV 다운로드
7. **Blend Optimization**에서 최적화 실행
8. 최적 배합비 확인

### 12. 지원

문의사항:
- Sempio R&D Team
- GitHub Issues (내부 레포)

---

**Happy Analyzing! 🧬**
