"""
GPT-SoVITS Windows 한국어 패치 스크립트
새로 git clone한 GPT-SoVITS에 Windows 호환 패치를 자동 적용합니다.

사용법:
    conda activate gpt-sovits
    cd C:\\...\\TTS
    python patch_gptsovits.py
"""
import os
import sys
import site
import pathlib

# GPT-SoVITS 경로 (이 스크립트 기준 상위 폴더의 GPT-SoVITS)
SCRIPT_DIR = pathlib.Path(__file__).parent.resolve()
GPT_DIR = SCRIPT_DIR.parent / "GPT-SoVITS" / "GPT_SoVITS" / "text"

if not GPT_DIR.exists():
    print(f"[ERROR] GPT-SoVITS 경로를 찾을 수 없습니다: {GPT_DIR}")
    print("        GPT-SoVITS가 올바른 위치에 clone되어 있는지 확인하세요.")
    sys.exit(1)


# ── 패치 1: tone_sandhi.py ──────────────────────────────────────────────────
def patch_tone_sandhi():
    path = GPT_DIR / "tone_sandhi.py"
    text = path.read_text(encoding="utf-8")
    old = "import jieba_fast as jieba"
    new = "try:\n    import jieba_fast as jieba\nexcept ImportError:\n    import jieba"
    if old not in text:
        print("[SKIP] tone_sandhi.py — 이미 패치됨")
        return
    path.write_text(text.replace(old, new), encoding="utf-8")
    print("[OK]   tone_sandhi.py 패치 완료")


# ── 패치 2: chinese.py / chinese2.py ───────────────────────────────────────
def patch_chinese(filename):
    path = GPT_DIR / filename
    text = path.read_text(encoding="utf-8")
    old = "import jieba_fast\nimport logging\n\njieba_fast.setLogLevel(logging.CRITICAL)\nimport jieba_fast.posseg as psg"
    new = (
        "import logging\n"
        "try:\n"
        "    import jieba_fast\n"
        "    jieba_fast.setLogLevel(logging.CRITICAL)\n"
        "    import jieba_fast.posseg as psg\n"
        "except ImportError:\n"
        "    import jieba as jieba_fast\n"
        "    jieba_fast.setLogLevel(logging.CRITICAL)\n"
        "    import jieba.posseg as psg"
    )
    if "except ImportError" in text:
        print(f"[SKIP] {filename} — 이미 패치됨")
        return
    path.write_text(text.replace(old, new), encoding="utf-8")
    print(f"[OK]   {filename} 패치 완료")


# ── 패치 3: korean.py — MeCab 없이 동작하도록 ──────────────────────────────
def patch_korean():
    path = GPT_DIR / "korean.py"
    text = path.read_text(encoding="utf-8")

    # _g2p 초기화 패치
    old_init = "_g2p = G2p()"
    new_init = (
        "try:\n"
        "    _g2p = G2p()\n"
        "    _g2p('테스트')  # MeCab 없으면 여기서 오류 발생\n"
        "    _g2p_available = True\n"
        "except Exception:\n"
        "    _g2p = None\n"
        "    _g2p_available = False\n"
        "\n"
        "\n"
        "def _apply_g2p(text):\n"
        "    \"\"\"g2pk2 적용. MeCab(eunjeon) 없으면 원문 그대로 반환.\"\"\"\n"
        "    if not _g2p_available:\n"
        "        return text\n"
        "    try:\n"
        "        return _g2p(text)\n"
        "    except Exception:\n"
        "        return text"
    )

    if "_g2p_available" in text:
        print("[SKIP] korean.py — 이미 패치됨")
        return

    # g2p() 함수 내 _g2p(text) → _apply_g2p(text)
    text = text.replace(old_init, new_init)
    text = text.replace(
        "def korean_to_ipa(text):\n    text = latin_to_hangul(text)\n    text = number_to_hangul(text)\n    text = _g2p(text)",
        "def korean_to_ipa(text):\n    text = latin_to_hangul(text)\n    text = number_to_hangul(text)\n    text = _apply_g2p(text)",
    )
    text = text.replace(
        "def g2p(text):\n    text = latin_to_hangul(text)\n    text = _g2p(text)",
        "def g2p(text):\n    text = latin_to_hangul(text)\n    text = _apply_g2p(text)",
    )
    path.write_text(text, encoding="utf-8")
    print("[OK]   korean.py 패치 완료")


# ── 패치 4: eunjeon shim (python-mecab-ko 연결) ────────────────────────────
def patch_eunjeon_shim():
    sp = site.getsitepackages()
    # conda 환경의 site-packages 찾기
    candidates = [p for p in sp if "site-packages" in p]
    if not candidates:
        candidates = sp
    sp_dir = pathlib.Path(candidates[0]) / "Lib" / "site-packages" if sys.platform == "win32" else pathlib.Path(candidates[0])

    # Windows conda 구조: envs/xxx/Lib/site-packages
    # getsitepackages()[0]이 envs/xxx 를 반환하는 경우도 있음
    if not (sp_dir / "mecab").exists():
        # 직접 경로 시도
        for p in sp:
            candidate = pathlib.Path(p)
            if (candidate / "mecab").exists():
                sp_dir = candidate
                break

    eunjeon_dir = sp_dir / "eunjeon"
    init_file = eunjeon_dir / "__init__.py"

    if init_file.exists():
        print("[SKIP] eunjeon shim — 이미 존재함")
        return

    eunjeon_dir.mkdir(parents=True, exist_ok=True)
    init_file.write_text(
        "# eunjeon compatibility shim — wraps python-mecab-ko\n"
        "from mecab import MeCab as Mecab\n"
        "__all__ = ['Mecab']\n",
        encoding="utf-8",
    )
    print(f"[OK]   eunjeon shim 생성: {init_file}")


# ── 실행 ────────────────────────────────────────────────────────────────────
print("=== GPT-SoVITS Windows 한국어 패치 시작 ===\n")
patch_tone_sandhi()
patch_chinese("chinese.py")
patch_chinese("chinese2.py")
patch_korean()
patch_eunjeon_shim()
print("\n=== 패치 완료! ===")
print("이제 api_v2.py를 실행하세요:")
print("  python api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml")
