# 목소리 복원 TTS (GPT-SoVITS)

루게릭병(ALS) 환자 목소리 복원을 위한 웹 애플리케이션입니다.
참조 음성을 업로드하면 Whisper가 자동으로 전사하고, 입력 텍스트를 해당 목소리로 변환합니다.

**GPT-SoVITS v2** 기반 — 1분 분량의 참조 음성만으로도 자연스러운 한국어 목소리 복제가 가능합니다.

---

## 아키텍처

```
[브라우저 :8000] ←→ [FastAPI main.py :8000]
                              ↓ HTTP
                    [GPT-SoVITS API :9880]
                     (별도 conda 환경에서 실행)
```

두 개의 Python 환경이 필요합니다:

| 환경 | 포트 | 역할 | 실행 방법 |
|------|------|------|-----------|
| `venv` (Python 3.x) | 8000 | FastAPI + Whisper | `venv\Scripts\activate` → `python main.py` |
| `gpt-sovits` conda (Python 3.10) | 9880 | GPT-SoVITS TTS 엔진 | `conda activate gpt-sovits` → `python api_v2.py` |

---

## 지원 언어

한국어, 영어

---

## 설치 방법

### 사전 요구사항

- [Miniforge3](https://github.com/conda-forge/miniforge) 또는 Anaconda
- Python 3.10 (conda 환경용)
- CUDA 지원 GPU (권장, CPU도 동작하나 느림)
- Git

---

### Step 1 — GPT-SoVITS 설치

```bash
# 1-1. GPT-SoVITS 클론
cd C:\Users\SSAFY\Desktop\AI
git clone https://github.com/RVC-Boss/GPT-SoVITS.git
cd GPT-SoVITS

# 1-2. conda 환경 생성 (Python 3.10 필수)
conda create -n gpt-sovits python=3.10 -y
conda activate gpt-sovits

# 1-3. PyTorch 설치 (CUDA 12.1 기준)
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121

# 1-4. 나머지 의존성 설치 (pyopenjtalk 제외)
cd C:\Users\SSAFY\Desktop\AI\TTS
python install_deps.py

# 1-5. 추가 패키지 설치
pip install jamo python-mecab-ko huggingface-hub
```

> CPU만 사용하는 경우: `pip install torch torchaudio` (index-url 없이)

---

### Step 2 — 사전 학습 모델 다운로드

```bash
conda activate gpt-sovits
cd C:\Users\SSAFY\Desktop\AI\GPT-SoVITS
python download_models.py
```

다운로드되는 모델 (HuggingFace `lj1995/GPT-SoVITS`):
- `pretrained_models/gsv-v2final-pretrained/` (GPT + SoVITS v2 모델)
- `pretrained_models/chinese-roberta-wwm-ext-large/`
- `pretrained_models/chinese-hubert-base/`

---

### Step 3 — Windows 호환 패치 적용

```bash
conda activate gpt-sovits
cd C:\Users\SSAFY\Desktop\AI\TTS
python patch_gptsovits.py
```

적용되는 패치:
- `tone_sandhi.py`: `jieba_fast` → `jieba` 폴백
- `chinese.py` / `chinese2.py`: `jieba_fast` → `jieba` 폴백
- `korean.py`: MeCab 없이 동작하도록 래퍼 추가
- `eunjeon` shim: `python-mecab-ko`를 `eunjeon`으로 연결

---

### Step 4 — FastAPI 환경 설치

```bash
# venv 생성 (TTS 폴더에서)
cd C:\Users\SSAFY\Desktop\AI\TTS
python -m venv venv
venv\Scripts\activate

# CUDA 사용 시
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121

# 의존성 설치
pip install -r requirements.txt
```

---

## 실행 방법

### 방법 A — 배치 파일 사용 (권장)

```
start_all.bat 더블클릭
```

두 개의 터미널이 열립니다:
- 터미널 1: GPT-SoVITS API (:9880)
- 터미널 2: FastAPI 서버 (:8000)

### 방법 B — 수동 실행 (터미널 2개)

**터미널 1 — GPT-SoVITS:**
```bash
conda activate gpt-sovits
cd C:\Users\SSAFY\Desktop\AI\GPT-SoVITS
python api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml
```

**터미널 2 — FastAPI:**
```bash
cd C:\Users\SSAFY\Desktop\AI\TTS
venv\Scripts\activate
python main.py
```

브라우저에서 `http://localhost:8000` 접속

---

## 사용 방법

1. **참조 음성 업로드** — 복제할 목소리의 MP3/WAV 파일 드래그앤드롭
2. **자동 전사** — Whisper가 참조 음성을 자동으로 텍스트로 변환 (편집 가능)
3. **텍스트 입력** — 해당 목소리로 읽힐 문장 입력
4. **언어 선택** — 한국어 / 영어
5. **변환하기** — 결과 음성 재생 및 다운로드

> **최초 실행 시** Whisper small 모델(~140MB)을 자동 다운로드합니다.

---

## 프로젝트 파일 구조

```
TTS/
├── main.py                  # FastAPI 서버 (포트 8000, Whisper + GPT-SoVITS 프록시)
├── requirements.txt         # FastAPI 환경 의존성
├── requirements_gptsovits.txt  # GPT-SoVITS conda 환경 의존성 참조용
├── install_deps.py          # GPT-SoVITS 의존성 설치 스크립트 (pyopenjtalk 제외)
├── patch_gptsovits.py       # Windows 호환 패치 자동 적용
├── start_all.bat            # 두 서버 동시 시작
├── start_gptsovits.bat      # GPT-SoVITS API 서버 시작 (start_all에서 호출)
├── static/
│   └── index.html           # 웹 UI
├── uploads/                 # 업로드된 참조 음성 (자동 생성)
└── outputs/                 # 변환 결과 음성 (자동 생성)

AI/GPT-SoVITS/              # git clone 위치 (TTS와 같은 레벨)
├── api_v2.py               # GPT-SoVITS API 서버
├── download_models.py       # 사전 학습 모델 다운로드
└── GPT_SoVITS/
    ├── configs/tts_infer.yaml
    └── pretrained_models/
```

---

## 의존성 목록

### FastAPI 환경 (`venv`) — `requirements.txt`

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
python-multipart==0.0.20
httpx>=0.27.0
openai-whisper>=20231117
torch>=2.1.0
torchaudio>=2.1.0
pydub
```

### GPT-SoVITS 환경 (`gpt-sovits` conda) — `requirements_gptsovits.txt`

```
torch torchaudio          # Step 1에서 별도 설치 (CUDA 버전 지정)
python-mecab-ko           # 한국어 형태소 분석 (eunjeon 대체)
jamo                      # 한국어 자모 분리
huggingface-hub           # 모델 다운로드
(나머지는 install_deps.py로 GPT-SoVITS/requirements.txt에서 설치)
```

---

## 음질 개선 팁

- 참조 음성은 **배경 소음이 없는 깨끗한 음성**일수록 복제 품질이 좋습니다.
- **3~10초** 분량의 참조 음성이 최적입니다 (자동으로 트리밍됨).
- 소음이 많은 파일은 [Adobe Podcast Enhancer](https://podcast.adobe.com/enhance) 또는 [UVR5](https://github.com/Anjok07/ultimatevocalremovergui)로 전처리를 권장합니다.
- Whisper가 전사한 텍스트가 실제 발화와 다를 경우 직접 수정 후 변환하세요.

---

## 문제 해결

| 오류 | 원인 | 해결 |
|------|------|------|
| GPT-SoVITS 연결 실패 | :9880 서버 미실행 | `start_gptsovits.bat` 먼저 실행 |
| `jieba_fast` 오류 | Windows 빌드 불가 | `python patch_gptsovits.py` 실행 |
| `400 참고 오디오 범위 오류` | 참조 음성 길이 문제 | 자동 트리밍됨, 서버 로그 확인 |
| Whisper 느린 전사 | CPU 동작 | CUDA 설치 후 GPU 사용 권장 |
