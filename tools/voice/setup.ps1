# One-time setup of the offline voice pipeline (Windows, NVIDIA GPU).
# Creates the venvs under $env:TTS_BAKE (default D:/tts-bake) and downloads models on first use.
#   powershell -ExecutionPolicy Bypass -File tools/voice/setup.ps1 [-Only cbx,piper,eval,qwen,f5]
# 'cbx' is the ONE venv bake.py actually runs in (generation + QA in a single process).
# 'eval', 'qwen', 'f5' are only needed to reproduce the bake-off exploration in report/bakeoff.md;
# they are not required for a normal re-bake.
param([string[]]$Only = @('cbx', 'piper', 'eval', 'qwen', 'f5'))
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

if ($Only -contains 'cbx') {   # Chatterbox multilingual (MIT) + QA stack, all in one venv: this is what bake.py uses
  New-Venv 'cbx' '3.11' @('chatterbox-tts==0.1.7', 'faster-whisper==1.1.1', 'speechbrain==1.0.3', `
    'librosa==0.10.2.post1', 'soundfile', 'pyloudnorm', 'jiwer', 'huggingface_hub<1', 'pyarrow') $null
  # setuptools>=81 dropped pkg_resources, which chatterbox's watermarker (resemble-perth) still imports
  & "$B/venvs/cbx/Scripts/python.exe" -m pip install "setuptools<81"
}
if ($Only -contains 'piper') {  # Piper ONNX voices (MIT) - no venv, a static binary + model files
  $pb = "$B/piper/bin"; $pv = "$B/piper/voices"
  New-Item -ItemType Directory -Force -Path $pb, $pv | Out-Null
  if (-not (Test-Path "$pb/piper.exe")) {
    Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip' -OutFile "$B/tmp/piper.zip"
    Expand-Archive -Force -Path "$B/tmp/piper.zip" -DestinationPath "$B/tmp/piper_extract"
    Copy-Item -Force "$B/tmp/piper_extract/piper/*" $pb -Recurse
  }
  # voices actually used by casting.json (rhasspy/piper-voices on HF); add more here if casting grows
  $voices = @('de/de_DE/thorsten/high/de_DE-thorsten-high.onnx', 'de/de_DE/thorsten/high/de_DE-thorsten-high.onnx.json',
              'de/de_DE/thorsten_emotional/medium/de_DE-thorsten_emotional-medium.onnx', 'de/de_DE/thorsten_emotional/medium/de_DE-thorsten_emotional-medium.onnx.json',
              'de/de_DE/kerstin/low/de_DE-kerstin-low.onnx', 'de/de_DE/kerstin/low/de_DE-kerstin-low.onnx.json',
              'de/de_DE/eva_k/x_low/de_DE-eva_k-x_low.onnx', 'de/de_DE/eva_k/x_low/de_DE-eva_k-x_low.onnx.json',
              'de/de_DE/ramona/low/de_DE-ramona-low.onnx', 'de/de_DE/ramona/low/de_DE-ramona-low.onnx.json',
              'de/de_DE/karlsson/low/de_DE-karlsson-low.onnx', 'de/de_DE/karlsson/low/de_DE-karlsson-low.onnx.json')
  foreach ($v in $voices) {
    $dest = Join-Path $pv (Split-Path $v -Leaf)
    if (-not (Test-Path $dest)) {
      Invoke-WebRequest -UseBasicParsing -Uri "https://huggingface.co/rhasspy/piper-voices/resolve/main/$v" -OutFile $dest
    }
  }
}
if ($Only -contains 'eval') {   # standalone QA venv (only for ad-hoc qa_check.py runs outside bake.py)
  New-Venv 'eval' '3.11' @('faster-whisper==1.1.1', 'speechbrain==1.0.3', 'librosa==0.10.2.post1', 'soundfile', 'pyloudnorm', 'jiwer', 'numpy<2', 'huggingface_hub<1', 'requests') $null
}
if ($Only -contains 'qwen') {  # Qwen3-TTS (Apache-2.0) - explored in the bake-off, not used in final casting
  New-Venv 'qwen' '3.12' @('qwen-tts==0.1.1', 'soundfile') $null
}
if ($Only -contains 'f5') {    # F5-TTS + German fine-tune aihpi/F5-TTS-German (CC-BY-NC-4.0) - explored, not used (NC licence + weaker output)
  New-Venv 'f5' '3.11' @('f5-tts==1.1.5', 'numpy<2') $null
}
Write-Host '=== SETUP DONE ==='
