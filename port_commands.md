# 8000 端口管理命令

## 查询 8000 端口应用

### Windows PowerShell 方式（推荐）

```powershell
# 方式 1：查看占用 8000 端口的进程信息
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object LocalAddress, LocalPort, State, OwningProcess | Format-Table

# 方式 2：查看进程详细信息
$port = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($port) {
    $pid = $port.OwningProcess
    Get-Process -Id $pid | Select-Object Id, ProcessName, Path, StartTime
} else {
    Write-Host "8000 端口未被占用"
}

# 方式 3：一行命令查看进程名和 PID
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { Get-Process -Id $_.OwningProcess | Select-Object Id, ProcessName }
```

### Windows CMD 方式

```cmd
# 查看占用 8000 端口的进程 ID
netstat -ano | findstr :8000

# 查看进程详细信息（需要替换 PID）
tasklist | findstr <PID>
```

### 快速查询脚本

```powershell
# 查询并显示详细信息
$conn = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($conn) {
    $pid = $conn.OwningProcess | Select-Object -First 1
    Write-Host "端口 8000 被占用" -ForegroundColor Yellow
    Write-Host "进程 ID: $pid"
    $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Host "进程名: $($proc.ProcessName)"
        Write-Host "路径: $($proc.Path)"
    }
} else {
    Write-Host "端口 8000 未被占用" -ForegroundColor Green
}
```

---

## 停止 8000 端口应用

### Windows PowerShell 方式（推荐）

```powershell
# 方式 1：通过端口查找并停止进程
$port = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($port) {
    $pid = $port.OwningProcess | Select-Object -First 1
    Stop-Process -Id $pid -Force
    Write-Host "已停止进程 PID: $pid"
} else {
    Write-Host "8000 端口未被占用"
}

# 方式 2：一行命令停止
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }

# 方式 3：停止所有 Python 进程（谨慎使用）
Get-Process python* -ErrorAction SilentlyContinue | Stop-Process -Force
```

### Windows CMD 方式

```cmd
# 步骤 1：查找进程 ID
netstat -ano | findstr :8000

# 步骤 2：停止进程（替换 <PID> 为实际进程 ID）
taskkill /PID <PID> /F

# 或者一行命令（需要先找到 PID）
for /f "tokens=5" %a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /PID %a /F
```

### 完整停止脚本

```powershell
# 查询并停止
$conn = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    $pid = $conn.OwningProcess
    $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Host "正在停止进程: $($proc.ProcessName) (PID: $pid)" -ForegroundColor Yellow
        Stop-Process -Id $pid -Force
        Start-Sleep -Seconds 2
        $check = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
        if (-not $check) {
            Write-Host "✅ 端口 8000 已释放" -ForegroundColor Green
        } else {
            Write-Host "⚠️  端口可能仍在关闭中，请稍后重试" -ForegroundColor Red
        }
    }
} else {
    Write-Host "端口 8000 未被占用" -ForegroundColor Green
}
```

---

## 快速使用

### 查询命令（复制到 PowerShell）
```powershell
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { $pid = $_.OwningProcess; Get-Process -Id $pid | Select-Object Id, ProcessName, Path }
```

### 停止命令（复制到 PowerShell）
```powershell
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }; Write-Host "已尝试停止占用 8000 端口的进程"
```

---

## 注意事项

1. **停止进程前**：确保这是你要停止的应用，避免误停止其他重要进程
2. **权限问题**：某些进程可能需要管理员权限才能停止
3. **数据安全**：停止应用前确保已保存重要数据
4. **端口释放延迟**：进程停止后，端口可能需要几秒钟才能完全释放


