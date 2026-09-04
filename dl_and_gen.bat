@echo off
setlocal
set BASE=D:\models\Wan2.1-T2V-1.3B-Diffusers
set URL=https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B-Diffusers/resolve/main
set LOG=C:\Users\leo\wan22_repo\wan_full_log.txt

echo [%date% %time%] Starting model download > %LOG%

:: Create directories
mkdir "%BASE%\text_encoder" 2>nul
mkdir "%BASE%\transformer" 2>nul
mkdir "%BASE%\vae" 2>nul
mkdir "%BASE%\scheduler" 2>nul
mkdir "%BASE%\tokenizer" 2>nul

:: Small config files
echo [%date% %time%] Downloading config files... >> %LOG%
curl -L -C - -o "%BASE%\model_index.json" "%URL%/model_index.json"
curl -L -C - -o "%BASE%\scheduler\scheduler_config.json" "%URL%/scheduler/scheduler_config.json"
curl -L -C - -o "%BASE%\text_encoder\config.json" "%URL%/text_encoder/config.json"
curl -L -C - -o "%BASE%\transformer\config.json" "%URL%/transformer/config.json"
curl -L -C - -o "%BASE%\vae\config.json" "%URL%/vae/config.json"
curl -L -C - -o "%BASE%\tokenizer\special_tokens_map.json" "%URL%/tokenizer/special_tokens_map.json"
curl -L -C - -o "%BASE%\tokenizer\spiece.model" "%URL%/tokenizer/spiece.model"
curl -L -C - -o "%BASE%\tokenizer\tokenizer.json" "%URL%/tokenizer/tokenizer.json"
curl -L -C - -o "%BASE%\tokenizer\tokenizer_config.json" "%URL%/tokenizer/tokenizer_config.json"
curl -L -C - -o "%BASE%\text_encoder\model.safetensors.index.json" "%URL%/text_encoder/model.safetensors.index.json"
curl -L -C - -o "%BASE%\transformer\diffusion_pytorch_model.safetensors.index.json" "%URL%/transformer/diffusion_pytorch_model.safetensors.index.json"

:: Large model files (with resume support)
echo [%date% %time%] Downloading transformer shard 1/2 (4.66GB)... >> %LOG%
curl -L -C - -o "%BASE%\transformer\diffusion_pytorch_model-00001-of-00002.safetensors" "%URL%/transformer/diffusion_pytorch_model-00001-of-00002.safetensors"
echo [%date% %time%] Downloading transformer shard 2/2 (646MB)... >> %LOG%
curl -L -C - -o "%BASE%\transformer\diffusion_pytorch_model-00002-of-00002.safetensors" "%URL%/transformer/diffusion_pytorch_model-00002-of-00002.safetensors"

echo [%date% %time%] Downloading VAE (484MB)... >> %LOG%
curl -L -C - -o "%BASE%\vae\diffusion_pytorch_model.safetensors" "%URL%/vae/diffusion_pytorch_model.safetensors"

echo [%date% %time%] Downloading text_encoder shard 1/5 (4.63GB)... >> %LOG%
curl -L -C - -o "%BASE%\text_encoder\model-00001-of-00005.safetensors" "%URL%/text_encoder/model-00001-of-00005.safetensors"
echo [%date% %time%] Downloading text_encoder shard 2/5 (4.56GB)... >> %LOG%
curl -L -C - -o "%BASE%\text_encoder\model-00002-of-00005.safetensors" "%URL%/text_encoder/model-00002-of-00005.safetensors"
echo [%date% %time%] Downloading text_encoder shard 3/5 (4.63GB)... >> %LOG%
curl -L -C - -o "%BASE%\text_encoder\model-00003-of-00005.safetensors" "%URL%/text_encoder/model-00003-of-00005.safetensors"
echo [%date% %time%] Downloading text_encoder shard 4/5 (4.66GB)... >> %LOG%
curl -L -C - -o "%BASE%\text_encoder\model-00004-of-00005.safetensors" "%URL%/text_encoder/model-00004-of-00005.safetensors"
echo [%date% %time%] Downloading text_encoder shard 5/5 (2.69GB)... >> %LOG%
curl -L -C - -o "%BASE%\text_encoder\model-00005-of-00005.safetensors" "%URL%/text_encoder/model-00005-of-00005.safetensors"

echo [%date% %time%] Download complete! Starting video generation... >> %LOG%

:: Run video generation
C:\Users\leo\liszt\venv\Scripts\python.exe -u C:\Users\leo\wan22_repo\dl_wan_1_3b.py >> %LOG% 2>&1

echo [%date% %time%] All done! >> %LOG%
