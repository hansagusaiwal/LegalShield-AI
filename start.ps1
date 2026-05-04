Write-Host "Starting LegalShield AI Deployment..."
Write-Host "Installing Python Dependencies..."
pip install fastapi uvicorn python-multipart pytesseract pdf2image scikit-learn pandas joblib

Write-Host "Installing NPM Dependencies..."
Set-Location -Path ".\frontend"
npm install
Set-Location -Path ".."

Write-Host "Generating Dataset..."
Set-Location -Path ".\model"
python generate_dataset.py

Write-Host "Training Legal Brain Model..."
python train_model.py
Set-Location -Path ".."

Write-Host "Starting FastAPI Backend on Port 8000..."
Start-Process -NoNewWindow -FilePath "python" -ArgumentList "-m uvicorn backend.main:app --host 0.0.0.0 --port 8000"

Write-Host "Starting React Frontend on Port 3000..."
Set-Location -Path ".\frontend"
Start-Process -NoNewWindow -FilePath "npm" -ArgumentList "run dev"
Set-Location -Path ".."

Start-Sleep -Seconds 5
Write-Host "SYSTEM LIVE: Ready to Win"
