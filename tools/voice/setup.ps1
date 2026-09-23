# One-time setup of the offline voice pipeline (Windows, NVIDIA GPU).
# Creates the venvs under $env:TTS_BAKE (default D:/tts-bake) and downloads models on first use.
#   powershell -ExecutionPolicy Bypass -File tools/voice/setup.ps1 [-Only eval,qwen,cbx,f5]
param([string[]]$Only = @('eval', 'qwen', 'cbx', 'f5'))
$ErrorActionPreference = 'Continue'
$B = if ($env:TTS_BAKE) { $env:TTS_BAKE } else { 'D:/tts-bake' }
New-Item -ItemType Directory -Force -Path "$B/venvs", "$B/tmp", "$B/cache/pip", "$B/hf", "$B/logs" | Out-Null
# keep every cache off C: (it is nearly full on the build tower)
$env:PIP_CACHE_DIR = "$B/cache/pip"; $env:TMP = "$B/tmp"; $env:TEMP = "$B/tmp"; $env:HF_HOME = "$B/hf"
$env:TORCH_HOME = "$B/cache/torch"; $env:PYTHONUTF8 = '1'
$TORCH = @('torch==2.6.0+cu124', 'torchaudio==2.6.0+cu124', '--index-url', 'https://download.pytorch.org/whl/cu124')

function New-Venv($name, $pyver, [string[]]$pkgs, [string[]]$extra) {
  $v = "$B/venvs/$name"; $py = "$v/Scripts/python.exe"
  Write-Host "=== $name ($pyver) ==="
  if (-not (Test-Path $py)) { & py "-$pyver" -m venv $v }
  & $py -m pip install --upgrade pip wheel setuptools
  & $py -m pip install @TORCH
  if ($pkgs) { & $py -m pip install @pkgs }
  if ($extra) { & $py -m pip install @extra }
  # a package may have pulled a CPU torch from PyPI: force the CUDA build back
  & $py -m pip install --force-reinstall --no-deps @TORCH
  & $py -c "import torch;print('TORCH', torch.__version__, torch.cuda.is_available())"
}

if ($Only -contains 'eval') {   # orchestrator + QA: whisper, MOS, speaker similarity, loudness
  New-Venv 'eval' '3.11' @('faster-whisper==1.1.1', 'speechbrain==1.0.3', 'librosa==0.10.2.post1', 'soundfile', 'pyloudnorm', 'jiwer', 'numpy<2', 'huggingface_hub<1', 'requests') $null
}
if ($Only -contains 'qwen') {  # Qwen3-TTS (Apache-2.0): voice design + clone, instruction-controlled delivery
  New-Venv 'qwen' '3.12' @('qwen-tts==0.1.1', 'soundfile') $null
}
if ($Only -contains 'cbx') {   # Chatterbox multilingual (MIT)
  New-Venv 'cbx' '3.11' @('chatterbox-tts==0.1.7') $null
}
if ($Only -contains 'f5') {    # F5-TTS + German fine-tune aihpi/F5-TTS-German (CC-BY-NC-4.0)
  New-Venv 'f5' '3.11' @('f5-tts==1.1.5', 'numpy<2') $null
}
Write-Host '=== SETUP DONE ==='
