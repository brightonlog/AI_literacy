@echo off
call C:\Users\SSAFY\miniforge3\Scripts\activate.bat gpt-sovits
cd /d C:\Users\SSAFY\Desktop\AI\GPT-SoVITS
python api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml
