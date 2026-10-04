$ErrorActionPreference = "Stop"

Set-Location "C:\Proyectos\Monitoreo_SRV"

# Configuración del arranque
$ProjectRoot = "C:\Proyectos\Monitoreo_SRV"
$DbContainer = "mon-postgres-local"
$AdminEmail = "admin@monitoreo.local"
$AdminPassword = "Admin123!"
$HostLabel = "monitor-host"
$NodeExporterContainer = "monitoreo-node-exporter"

# 1) Crear .env si no existe
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

# 2) Asegurar que la base PostgreSQL local esté levantada
$pgExists = docker ps -a --format "{{.Names}}" | Where-Object { $_ -eq $DbContainer }
if (-not $pgExists) {
    docker run -d --name $DbContainer `
      -e POSTGRES_DB=monitoreo_srv `
      -e POSTGRES_USER=postgres `
      -e POSTGRES_PASSWORD=Abc123.. `
      -p 5432:5432 `
      postgres:16-alpine
}

# 3) Esperar a que PostgreSQL esté listo
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        docker exec $DbContainer pg_isready -U postgres -d monitoreo_srv | Out-Null
        $ready = $true
        break
    }
    catch {
        Start-Sleep -Seconds 2
    }
}
if (-not $ready) {
    throw "PostgreSQL no quedó listo en tiempo esperado."
}

# 4) Levantar el stack principal
Write-Host "[1/7] Levantando contenedores del proyecto..."
docker compose up -d --build

# 5) Esperar al backend
Write-Host "[2/7] Esperando a que el backend responda..."
$backendReady = $false
for ($i = 0; $i -lt 40; $i++) {
    try {
        $resp = docker compose exec -T backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/health').read().decode())"
        if ($resp -match '"backend":"ok"') {
            $backendReady = $true
            break
        }
    }
    catch {
        Start-Sleep -Seconds 2
    }
}
if (-not $backendReady) {
    throw "El backend no respondió a /api/health."
}

# 6) Bootstrap del admin inicial
Write-Host "[3/7] Creando administrador inicial..."
docker compose exec -T backend python -c "import urllib.request, urllib.parse; url='http://localhost:8000/api/auth/bootstrap'; payload=urllib.parse.urlencode({'email':'$AdminEmail','password':'$AdminPassword'}); req=urllib.request.Request(url+'?'+payload, method='POST'); print(urllib.request.urlopen(req).read().decode())"

# 7) Login para obtener token
Write-Host "[4/7] Obteniendo token del administrador..."
$token = docker compose exec -T backend python -c "import json, urllib.request, urllib.parse; login='http://localhost:8000/api/auth/login'; data=urllib.parse.urlencode({'username':'$AdminEmail','password':'$AdminPassword'}).encode(); req=urllib.request.Request(login, data=data, headers={'Content-Type':'application/x-www-form-urlencoded'}, method='POST'); body=json.loads(urllib.request.urlopen(req).read().decode()); print(body['access_token'])"

# 8) Registrar servidor base
Write-Host "[5/7] Registrando servidor base..."
docker compose exec -T backend python -c "
import json, urllib.request

token = r'''$token'''
payload = json.dumps({'hostname':'$HostLabel','system_uuid':'local-host-001','primary_ip':'node-exporter','os':'Linux'}).encode()
req = urllib.request.Request('http://localhost:8000/api/servers', data=payload, headers={'Content-Type':'application/json','Authorization':'Bearer '+token}, method='POST')
print(urllib.request.urlopen(req).read().decode())
"

# 9) Levantar node-exporter si no existe
Write-Host "[6/7] Levantando node-exporter..."
$nodeExists = docker ps -a --format "{{.Names}}" | Where-Object { $_ -eq $NodeExporterContainer }
if (-not $nodeExists) {
    docker run -d --name $NodeExporterContainer `
      --network monitoreo_srv_mon-net `
      --hostname node-exporter `
      -p 9100:9100 `
      prom/node-exporter:v1.8.2 `
      --web.listen-address=:9100
}

# 10) Validar Prometheus target
Write-Host "[7/7] Validando target de Prometheus..."
docker compose exec -T prometheus sh -lc "wget -qO- http://localhost:9090/api/v1/targets | grep -o 'node-exporter:9100' | head"

Write-Host ""
Write-Host "=============================================="
Write-Host "Proyecto levantado correctamente"
Write-Host "Frontend: http://localhost/"
Write-Host "API:      http://localhost:8000/api/docs"
Write-Host "Health:   http://localhost:8000/api/health"
Write-Host "Login:    $AdminEmail / $AdminPassword"
Write-Host "=============================================="
