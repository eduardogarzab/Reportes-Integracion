# Banca móvil híbrida + serverless (ZIP corregido)

Incluye:
- `extensionBundle` en `host.json`
- HTTP `function.json` con `"name": "$return"`
- `local.settings.example.json` con `DEMO_NO_SB=1` y trigger deshabilitado

## Pasos que seguimos
1. Instalar Core Tools y verificar:
   ```
   func --version
   ```
2. Crear venv e instalar dependencias:
   ```
   cd backend
   py -m venv .venv
   Set-ExecutionPolicy -Scope Process Bypass
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```
3. Copiar settings y usar modo demo / desactivar trigger:
   ```
   copy .\local.settings.example.json .\local.settings.json
   ```
4. (Opcional) Azurite para Storage local:
   ```
   npm i -g azurite
   azurite
   ```
5. Arrancar:
   ```
   func start
   ```
   - GET: `http://localhost:7071/api/accounts/MX1234567890/balance`
   - POST (demo):
     ```
     curl -Method POST "http://localhost:7071/api/payments/transfer" `
       -Headers @{ "Content-Type"="application/json"; "Idempotency-Key"="demo-12345678"; "x-user-id"="demo-user" } `
       -Body '{"source_account":"MX1234567890","destination_account":"MX0987654321","amount":150.00,"currency":"MXN","reference":"TEST"}'
     ```
