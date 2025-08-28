# 🚀 Script de Deploy Automático para Render

Este script automatiza completamente el proceso de deploy de tu aplicación web a Render, incluyendo commit automático, push a Git y despliegue en Render.

## ✨ Características

- 🔄 **Commit automático** de cambios pendientes
- 📤 **Push automático** al repositorio remoto
- 🚀 **Deploy automático** en Render
- 👀 **Monitoreo en tiempo real** del progreso del deploy
- 📝 **Logs detallados** de todo el proceso
- ⚙️ **Configuración flexible** mediante archivo JSON
- 🛡️ **Manejo robusto de errores**

## 📋 Requisitos Previos

1. **Python 3.7+** instalado
2. **Git** configurado con acceso al repositorio
3. **Token de Render** configurado como variable de entorno
4. **Service ID** de Render configurado

## 🛠️ Instalación

### 1. Instalar dependencias
```bash
pip install -r requirements_deploy.txt
```

### 2. Configurar variables de entorno
```bash
# Windows (PowerShell)
$env:RENDER_TOKEN="tu_token_aqui"

# Windows (CMD)
set RENDER_TOKEN=tu_token_aqui

# Linux/Mac
export RENDER_TOKEN="tu_token_aqui"
```

### 3. Configurar render_config.json
Edita el archivo `render_config.json` y coloca tu Service ID:
```json
{
    "service_id": "srv-d2ckh46r433s73appvug",
    "service_name": "mi_app_web",
    "environment": "production"
}
```

## 🚀 Uso

### Opción 1: Script Python directo
```bash
# Deploy automático completo
python deploy_render_automatico.py

# Deploy con mensaje personalizado
python deploy_render_automatico.py "Mejoras en el sistema de recordatorios"

# Deploy sin commit automático
python deploy_render_automatico.py --no-commit

# Mostrar ayuda
python deploy_render_automatico.py --help
```

### Opción 2: Script Batch (Windows)
```bash
# Deploy automático
deploy_render.bat

# Deploy con argumentos
deploy_render.bat "Mejoras en recordatorios"
deploy_render.bat --no-commit
```

## 📊 Flujo del Deploy

1. **🔍 Verificación de Git**
   - Revisa si hay cambios pendientes
   - Muestra estado del repositorio

2. **📝 Commit Automático**
   - Agrega todos los cambios al staging
   - Realiza commit con timestamp automático
   - Permite mensaje personalizado

3. **📤 Push al Repositorio**
   - Envía cambios al repositorio remoto
   - Verifica que el push sea exitoso

4. **🚀 Deploy en Render**
   - Dispara deploy manual en Render
   - Obtiene ID del deploy para monitoreo

5. **👀 Monitoreo del Deploy**
   - Verifica estado cada 10 segundos
   - Muestra progreso en tiempo real
   - Espera máximo 5 minutos

## ⚙️ Configuración

### render_config.json
```json
{
    "service_id": "srv-xxxxxxxxxxxxxxxxx",
    "service_name": "nombre_del_servicio",
    "environment": "production",
    "auto_deploy": true,
    "clear_cache": false,
    "timeout_minutes": 10,
    "retry_attempts": 3
}
```

### Variables de Entorno
- `RENDER_TOKEN`: Token de API de Render (requerido)

## 📝 Logs

El script genera logs detallados en:
- **Consola**: Output en tiempo real
- **Archivo**: `deploy_render.log`

### Niveles de Log
- `INFO`: Información general del proceso
- `WARNING`: Advertencias no críticas
- `ERROR`: Errores que impiden el deploy

## 🚨 Solución de Problemas

### Error: RENDER_TOKEN no encontrado
```bash
# Verificar que la variable esté configurada
echo $env:RENDER_TOKEN  # PowerShell
echo %RENDER_TOKEN%     # CMD
```

### Error: Service ID no configurado
- Verifica que `render_config.json` exista
- Asegúrate de que `service_id` tenga un valor válido

### Error: Git no configurado
```bash
# Verificar configuración de Git
git config --list
git remote -v
```

### Error: Deploy falló
- Revisa los logs en `deploy_render.log`
- Verifica el estado en el dashboard de Render
- Revisa que el código compile correctamente

## 🔧 Personalización

### Modificar timeout del deploy
```python
# En deploy_render_automatico.py, línea ~200
max_attempts = 60  # 10 minutos en lugar de 5
```

### Agregar más validaciones
```python
# En la función check_git_status()
# Agregar validaciones personalizadas antes del deploy
```

### Modificar mensajes de commit
```python
# En la función commit_changes()
commit_message = f"Deploy automático - {timestamp} - {os.environ.get('USER', 'Sistema')}"
```

## 📚 Comandos Útiles

### Ver estado del repositorio
```bash
git status
git log --oneline -5
```

### Ver logs del deploy
```bash
# Ver logs en tiempo real
Get-Content deploy_render.log -Wait  # PowerShell
tail -f deploy_render.log            # Linux/Mac
```

### Verificar configuración
```bash
python -c "import json; print(json.load(open('render_config.json')))"
```

## 🤝 Contribución

Para reportar problemas o sugerir mejoras:
1. Revisa los logs del script
2. Verifica la configuración
3. Prueba con un deploy manual primero

## 📄 Licencia

Este script es parte del sistema de deploy automático de mi_app_web.

---

**¡Deploy feliz! 🚀✨**
