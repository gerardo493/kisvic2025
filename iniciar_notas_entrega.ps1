Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    SISTEMA DE NOTAS DE ENTREGA" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "🚀 Iniciando servidor web..." -ForegroundColor Green
Write-Host ""
Write-Host "📱 La aplicación estará disponible en:" -ForegroundColor Yellow
Write-Host "   http://127.0.0.1:5000" -ForegroundColor White
Write-Host ""
Write-Host "📋 Para acceder a las notas de entrega:" -ForegroundColor Yellow
Write-Host "   http://127.0.0.1:5000/notas-entrega" -ForegroundColor White
Write-Host ""
Write-Host "⏹️  Presiona CTRL+C para detener el servidor" -ForegroundColor Red
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

try {
    python app.py
} catch {
    Write-Host "❌ Error ejecutando la aplicación: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "🛑 Servidor detenido." -ForegroundColor Yellow
Read-Host "Presiona Enter para continuar"
