# 🚀 Script de Deploy Simple - Solo Git

Este script automatiza el proceso de deploy usando únicamente comandos Git. No requiere configuración de Render API ni tokens.

## ✨ Características

- 🔄 **Commit automático** de cambios pendientes
- 📤 **Push automático** al repositorio remoto
- 🚀 **Deploy automático** en Render (detecta cambios)
- 📝 **Logs detallados** del proceso
- 🛡️ **Manejo robusto de errores**
- ⚡ **Sin configuración compleja**

## 📋 Requisitos Previos

1. **Python 3.7+** instalado
2. **Git** configurado con acceso al repositorio
3. **Repositorio remoto** configurado (origin)

## 🚀 Cómo Usar

### **Opción 1: Script Python**
```bash
# Deploy automático completo
python deploy_simple.py

# Con mensaje personalizado
python deploy_simple.py "Mejoras en recordatorios"

# Mostrar ayuda
python deploy_simple.py --help
```

### **Opción 2: Script Batch (Windows)**
```bash
# Doble clic en deploy_simple.bat
# O desde línea de comandos:
deploy_simple.bat "Mensaje personalizado"
```

## 📊 Flujo del Deploy

1. **🔍 Verificación de Git**
   - Revisa configuración del repositorio remoto
   - Verifica si hay cambios pendientes

2. **📝 Commit Automático**
   - Agrega todos los cambios al staging
   - Realiza commit con timestamp automático
   - Permite mensaje personalizado

3. **📤 Push al Repositorio**
   - Envía cambios al repositorio remoto
   - Detecta automáticamente la rama actual

4. **🚀 Deploy en Render**
   - Render detecta cambios automáticamente
   - Inicia deploy sin intervención manual

## 📝 Logs

El script genera logs detallados en:
- **Consola**: Output en tiempo real
- **Archivo**: `deploy_simple.log`

## 🚨 Solución de Problemas

### Error: Git no configurado
```bash
# Verificar configuración de Git
git config --list
git remote -v
```

### Error: No hay repositorio remoto
```bash
# Agregar repositorio remoto
git remote add origin https://github.com/usuario/repositorio.git
```

### Error: Push falló
- Verifica que tengas acceso al repositorio
- Asegúrate de que la rama esté sincronizada
- Revisa los logs para más detalles

## 💡 Consejos de Uso

1. **Usa mensajes descriptivos** para tus commits
2. **Ejecuta el script** desde el directorio raíz del proyecto
3. **Verifica el estado** en Render después del push
4. **Mantén tu código sincronizado** con el repositorio

## 🔧 Personalización

### Modificar mensaje por defecto
```python
# En deploy_simple.py, línea ~60
commit_message = f"Deploy automático - {timestamp} - {os.environ.get('USER', 'Sistema')}"
```

### Agregar más validaciones
```python
# En la función check_git_status()
# Agregar validaciones personalizadas antes del deploy
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
Get-Content deploy_simple.log -Wait  # PowerShell
tail -f deploy_simple.log            # Linux/Mac
```

### Verificar configuración de Git
```bash
git remote -v
git branch --show-current
```

## 🤝 Ventajas del Enfoque Simple

- ✅ **Sin configuración compleja**
- ✅ **No requiere tokens de API**
- ✅ **Funciona con cualquier repositorio Git**
- ✅ **Deploy automático en Render**
- ✅ **Fácil de mantener y modificar**

## 📄 Flujo de Trabajo Típico

1. **Haces cambios** en tu código
2. **Ejecutas** el script de deploy
3. **El script automáticamente:**
   - Verifica cambios en Git
   - Hace commit con tu mensaje
   - Sube a GitHub
   - Render detecta cambios y se despliega

---

**¡Deploy simple y efectivo! 🚀✨**
