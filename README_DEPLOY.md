# 🚀 Desplegador Automático para Render

Sistema completo para desplegar automáticamente tu aplicación web al hosting de Render.

## 📋 Características

- ✅ **Despliegue automático** a Render usando la API oficial
- ✅ **Backup automático** antes de cada despliegue
- ✅ **Filtrado inteligente** de archivos (excluye archivos innecesarios)
- ✅ **Monitoreo en tiempo real** del estado del despliegue
- ✅ **Logs detallados** de todo el proceso
- ✅ **Configuración flexible** mediante archivo JSON
- ✅ **Scripts multiplataforma** (Windows, Linux, Mac)

## 🛠️ Instalación

### 1. Configuración Inicial (Recomendado)

```bash
python setup_deploy.py
```

Este script te guiará paso a paso para:
- Instalar dependencias
- Crear directorios necesarios
- Configurar credenciales de Render
- Crear scripts de ejecución

### 2. Instalación Manual

```bash
# Instalar dependencias
pip install -r requirements_deploy.txt

# Crear archivo de configuración
python deploy_render.py --config
```

## 🔑 Configuración de Render

### Obtener API Key
1. Ve a [Render Dashboard](https://dashboard.render.com/account/api-keys)
2. Haz clic en "New API Key"
3. Dale un nombre descriptivo
4. Copia la clave generada

### Obtener Service ID
1. Ve a tu servicio en Render
2. Copia el ID de la URL: `https://dashboard.render.com/web/srv-XXXXXXXXXXXXXX`
3. El Service ID es `srv-XXXXXXXXXXXXXX`

### Obtener Account ID
1. Ve a tu dashboard de Render
2. El Account ID está en la URL: `https://dashboard.render.com/account/acc-XXXXXXXXXXXXXX`
3. El Account ID es `acc-XXXXXXXXXXXXXX`

## 📁 Estructura de Archivos

```
proyecto/
├── deploy_render.py          # Script principal de despliegue
├── setup_deploy.py           # Configurador inicial
├── requirements_deploy.txt    # Dependencias Python
├── render_config.json        # Configuración (se crea automáticamente)
├── deploy_render.bat         # Script para Windows
├── deploy_render.sh          # Script para Linux/Mac
├── backups/                  # Backups automáticos
├── temp/                     # Archivos temporales
└── deploy_render.log         # Log del último despliegue
```

## 🚀 Uso

### Despliegue Automático

#### Windows
```bash
deploy_render.bat
```

#### Linux/Mac
```bash
./deploy_render.sh
```

#### Manual
```bash
python deploy_render.py
```

### Verificar Estado
```bash
# Ver logs del último despliegue
tail -f deploy_render.log

# Ver configuración actual
cat render_config.json
```

## ⚙️ Configuración Avanzada

### Archivo `render_config.json`

```json
{
    "render": {
        "api_key": "tu_api_key_aqui",
        "service_id": "tu_service_id_aqui",
        "account_id": "tu_account_id_aqui"
    },
    "deploy": {
        "exclude_patterns": [
            "__pycache__",
            "*.pyc",
            "venv",
            "*.log"
        ],
        "include_patterns": [
            "*.py",
            "*.html",
            "*.css",
            "templates/*"
        ],
        "backup_before_deploy": true,
        "create_zip_backup": true
    },
    "paths": {
        "source": ".",
        "backup": "./backups",
        "temp": "./temp"
    }
}
```

### Patrones de Exclusión

Archivos y carpetas que **NO** se subirán:
- `__pycache__` - Caché de Python
- `*.pyc` - Archivos compilados de Python
- `venv` - Entorno virtual
- `.git` - Repositorio Git
- `*.log` - Archivos de log
- `backups/` - Carpeta de backups
- `temp/` - Archivos temporales

### Patrones de Inclusión

Archivos que **SÍ** se subirán:
- `*.py` - Código Python
- `*.html` - Plantillas HTML
- `*.css` - Estilos CSS
- `*.js` - JavaScript
- `templates/*` - Carpeta de plantillas
- `static/*` - Archivos estáticos
- `requirements.txt` - Dependencias

## 📊 Monitoreo del Despliegue

El script monitorea automáticamente el estado del despliegue:

- 🔄 **Building** - Construyendo la aplicación
- 🔄 **Deploying** - Desplegando archivos
- ✅ **Live** - Despliegue exitoso
- ❌ **Failed** - Despliegue falló

## 🔒 Seguridad

- ✅ Las credenciales se almacenan localmente
- ✅ No se suben archivos sensibles (`.env`, `.git`)
- ✅ Logs no contienen información sensible
- ✅ Backups se crean antes de cada despliegue

## 🐛 Solución de Problemas

### Error: "API Key inválida"
- Verifica que la API Key esté correctamente copiada
- Asegúrate de que la API Key tenga permisos de escritura

### Error: "Service ID no encontrado"
- Verifica que el Service ID sea correcto
- Asegúrate de que el servicio esté activo en Render

### Error: "Despliegue falló"
- Revisa los logs en `deploy_render.log`
- Verifica que tu aplicación se compile correctamente
- Revisa la configuración de build en Render

### Error: "Dependencias no encontradas"
```bash
pip install -r requirements_deploy.txt
```

## 📝 Logs

Los logs se guardan en:
- **Archivo**: `deploy_render.log`
- **Consola**: Salida en tiempo real
- **Nivel**: INFO, WARNING, ERROR

## 🔄 Automatización

### Cron Job (Linux/Mac)
```bash
# Editar crontab
crontab -e

# Desplegar cada día a las 2:00 AM
0 2 * * * cd /ruta/a/tu/proyecto && python deploy_render.py
```

### Task Scheduler (Windows)
1. Abre "Programador de tareas"
2. Crea una nueva tarea
3. Programa la ejecución de `deploy_render.bat`

## 📞 Soporte

Si tienes problemas:

1. **Revisa los logs**: `deploy_render.log`
2. **Verifica la configuración**: `render_config.json`
3. **Prueba la conexión**: Verifica credenciales de Render
4. **Revisa el estado**: Dashboard de Render

## 🆕 Actualizaciones

Para actualizar el script:

```bash
# Hacer backup de tu configuración
cp render_config.json render_config.json.backup

# Descargar nueva versión
# (reemplazar archivos)

# Restaurar configuración
cp render_config.json.backup render_config.json
```

## 📄 Licencia

Este script es de uso libre para proyectos personales y comerciales.

---

**¡Despliega tu aplicación a Render con un solo clic! 🚀**
