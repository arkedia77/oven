# leowin ComfyUI - Krea 2 person-reference test install (hf-playground 10-28 112328 / LEO 10-28 "test both on leowin")
# Run by LEO (oven's auto mode classifier blocks untrusted code integration). Repos pinned to commits oven reviewed 10-28:
#   no pip dependencies, node code has no network/subprocess calls. NOT installed: ComfyUI-ConditioningKrea2Rebalance (safety-filter bypass fork).
$ErrorActionPreference = 'Stop'
$cn = 'C:\comfyui_moss\ComfyUI\custom_nodes'
$lo = 'C:\comfyui_moss\ComfyUI\models\loras\studio_krea2\krea2_reid_rank32.safetensors'
$LoraSha = 'a80349faee4a2d80eff9a83820cd523c74cd0bbc6039cee21fa34b084d967944'   # HF x-linked-etag 10-28, 228,587,752 B
'before C: free={0:N2}GB' -f ((Get-PSDrive C).Free/1GB)
$repos = @(
  @('https://github.com/ostris/ComfyUI-Krea2-Ostris-Edit', 'ComfyUI-Krea2-Ostris-Edit', '7756566160c4a1b24bb1bd9f0ff3ced1a83d7547'),
  @('https://github.com/kgilper/krea-reference',           'krea-reference',            'b3aaf2fb7c398348bcf9c8e8223875507936a803')
)
foreach ($r in $repos) {
  $d = Join-Path $cn $r[1]
  if (-not (Test-Path $d)) { & git clone -q $r[0] $d }
  & git -C $d checkout -q $r[2]
  "$($r[1]) head=$(& git -C $d rev-parse HEAD)"
}
if (-not (Test-Path $lo)) { & curl.exe -sSL -o $lo 'https://huggingface.co/yijunwang2/krea2-reid/resolve/main/krea2_reid_rank32.safetensors' }
$h = (Get-FileHash $lo -Algorithm SHA256).Hash.ToLower()
"lora bytes=$((Get-Item $lo).Length) sha256_ok=$($h -eq $LoraSha)"
'after C: free={0:N2}GB' -f ((Get-PSDrive C).Free/1GB)
'DONE - tell oven (it restarts ComfyUI and checks /object_info)'
