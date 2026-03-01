import os
import uuid
import shutil
from pathlib import Path

import httpx
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Voice Clone TTS (GPT-SoVITS)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# GPT-SoVITS API 서버 주소 (환경변수로 덮어쓸 수 있음)
GPT_SOVITS_API = os.environ.get("GPT_SOVITS_API", "http://127.0.0.1:9880")

whisper_model = None


def to_wav(input_path: str) -> str:
    """WAV가 아닌 오디오 파일을 WAV로 변환"""
    if input_path.lower().endswith(".wav"):
        return input_path
    wav_path = str(Path(input_path).with_suffix(".wav"))
    try:
        from pydub import AudioSegment
        AudioSegment.from_file(input_path).export(wav_path, format="wav")
    except Exception:
        import torchaudio
        waveform, sr = torchaudio.load(input_path)
        torchaudio.save(wav_path, waveform, sr)
    return wav_path


def trim_ref_audio(wav_path: str, min_sec: float = 3.0, max_sec: float = 10.0) -> str:
    """GPT-SoVITS 참조 음성 길이 제한(3~10초)에 맞게 자동 트리밍"""
    from pydub import AudioSegment
    audio = AudioSegment.from_wav(wav_path)
    duration = len(audio) / 1000.0  # ms → 초

    if min_sec <= duration <= max_sec:
        return wav_path  # 범위 내이면 그대로

    if duration > max_sec:
        # 앞부분 max_sec초만 사용
        trimmed = audio[: int(max_sec * 1000)]
        trimmed_path = str(Path(wav_path).with_stem(Path(wav_path).stem + "_trimmed"))
        trimmed.export(trimmed_path, format="wav")
        return trimmed_path

    # 3초 미만이면 경고만 (GPT-SoVITS에 그냥 전달, 서버가 판단)
    return wav_path


def get_whisper():
    global whisper_model
    if whisper_model is None:
        import whisper
        print("Whisper 모델 로딩 중... (최초 실행 시 다운로드 ~140MB)")
        whisper_model = whisper.load_model("small")
        print("Whisper 로드 완료!")
    return whisper_model


def transcribe_audio(wav_path: str, language: str = "ko") -> str:
    """Whisper로 오디오 전사. 언어 코드를 Whisper 형식으로 변환."""
    lang_map = {"ko": "ko", "en": "en", "ja": "ja", "zh-cn": "zh", "fr": "fr", "de": "de"}
    whisper_lang = lang_map.get(language, "ko")
    model = get_whisper()
    result = model.transcribe(wav_path, language=whisper_lang)
    return result["text"].strip()


app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/health")
async def health():
    """GPT-SoVITS API 서버 연결 상태 확인"""
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            res = await client.get(f"{GPT_SOVITS_API}/")
            return JSONResponse({"status": "ok", "gptsovits": res.status_code})
    except Exception as e:
        return JSONResponse({"status": "error", "gptsovits": str(e)}, status_code=503)


@app.post("/upload-reference")
async def upload_reference(file: UploadFile = File(...)):
    """참조 음성 업로드 (전사 없이 저장만)"""
    ext = Path(file.filename).suffix.lower()
    if ext not in [".mp3", ".wav", ".m4a", ".flac", ".ogg"]:
        raise HTTPException(status_code=400, detail="지원하지 않는 오디오 형식입니다.")
    filename = f"{uuid.uuid4()}{ext}"
    save_path = UPLOAD_DIR / filename
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    try:
        wav_path = to_wav(str(save_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"오디오 변환 실패: {str(e)}")
    return JSONResponse({
        "reference_path": str(Path(wav_path).resolve()),
        "filename": file.filename,
        "message": "업로드 완료!"
    })


@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(None),
    reference_path: str = Form(None),
    language: str = Form("ko"),
):
    """참조 음성을 Whisper로 자동 전사"""
    if file and file.filename:
        ext = Path(file.filename).suffix.lower()
        if ext not in [".mp3", ".wav", ".m4a", ".flac", ".ogg"]:
            raise HTTPException(status_code=400, detail="지원하지 않는 오디오 형식입니다.")
        tmp_path = UPLOAD_DIR / f"{uuid.uuid4()}{ext}"
        with open(tmp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        try:
            wav_path = to_wav(str(tmp_path))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"오디오 변환 실패: {str(e)}")
    elif reference_path:
        if not Path(reference_path).exists():
            raise HTTPException(status_code=400, detail="파일을 찾을 수 없습니다.")
        try:
            wav_path = to_wav(reference_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"오디오 변환 실패: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="파일 또는 경로를 제공해주세요.")

    # 전사 전에 트리밍 (GPT-SoVITS 3~10초 제한 + prompt_text 일치 보장)
    try:
        wav_path = trim_ref_audio(wav_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"트리밍 실패: {str(e)}")

    try:
        text = transcribe_audio(wav_path, language)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"전사 실패: {str(e)}")

    return JSONResponse({
        "transcript": text,
        "reference_path": str(Path(wav_path).resolve()),
        "message": "전사 완료!"
    })


@app.post("/clone")
async def clone_voice(
    text: str = Form(...),
    language: str = Form("ko"),
    prompt_text: str = Form(None),
    reference_audio: UploadFile = File(None),
    reference_path: str = Form(None),
):
    """GPT-SoVITS API를 통한 음성 합성"""
    if not text.strip():
        raise HTTPException(status_code=400, detail="텍스트를 입력해주세요.")

    # 참조 음성 저장 및 WAV 변환
    if reference_audio and reference_audio.filename:
        ext = Path(reference_audio.filename).suffix.lower()
        if ext not in [".mp3", ".wav", ".m4a", ".flac", ".ogg"]:
            raise HTTPException(status_code=400, detail="지원하지 않는 오디오 형식입니다.")
        ref_filename = f"{uuid.uuid4()}{ext}"
        ref_path = UPLOAD_DIR / ref_filename
        with open(ref_path, "wb") as f:
            shutil.copyfileobj(reference_audio.file, f)
        try:
            audio_ref = to_wav(str(ref_path))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"오디오 변환 실패: {str(e)}")
    elif reference_path:
        if not Path(reference_path).exists():
            raise HTTPException(status_code=400, detail="참조 음성 파일을 찾을 수 없습니다.")
        try:
            audio_ref = to_wav(reference_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"오디오 변환 실패: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="참조 음성 파일을 업로드해주세요.")

    # GPT-SoVITS 참조 음성 길이 제한(3~10초) 자동 트리밍
    try:
        audio_ref = trim_ref_audio(audio_ref)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"참조 음성 트리밍 실패: {str(e)}")

    # prompt_text가 없으면 Whisper로 자동 전사
    if not prompt_text or not prompt_text.strip():
        try:
            prompt_text = transcribe_audio(audio_ref, language)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"참조 음성 전사 실패: {str(e)}")

    # GPT-SoVITS 언어 코드 변환
    lang_map = {"ko": "ko", "en": "en", "ja": "ja", "zh-cn": "zh", "fr": "fr", "de": "de"}
    gptsovits_lang = lang_map.get(language, "ko")

    # GPT-SoVITS API 호출 (POST + JSON — 한국어 UTF-8 깨짐 방지)
    abs_ref_path = str(Path(audio_ref).resolve())
    payload = {
        "text": text,
        "text_lang": gptsovits_lang,
        "ref_audio_path": abs_ref_path,
        "prompt_text": prompt_text,
        "prompt_lang": gptsovits_lang,
        "media_type": "wav",
        "streaming_mode": False,
        "top_k": 5,
        "top_p": 1,
        "temperature": 1,
        "speed_factor": 1.0,
    }

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(f"{GPT_SOVITS_API}/tts", json=payload)
        if res.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"GPT-SoVITS 오류 ({res.status_code}): {res.text[:200]}"
            )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="GPT-SoVITS API 서버에 연결할 수 없습니다. start_all.bat으로 서버를 먼저 시작하세요."
        )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="GPT-SoVITS 응답 시간 초과 (120초)")

    # 결과 저장
    output_filename = f"{uuid.uuid4()}.wav"
    output_path = OUTPUT_DIR / output_filename
    with open(output_path, "wb") as f:
        f.write(res.content)

    return JSONResponse({
        "audio_url": f"/outputs/{output_filename}",
        "reference_path": abs_ref_path,
        "prompt_text": prompt_text,
        "message": "변환 완료!"
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
