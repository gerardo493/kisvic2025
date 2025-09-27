# 🚀 Inicio Rápido - Dashboard Sistema de Facturación

## Instalación y Ejecución

### 1. Instalar Dependencias
```bash
npm install
```

### 2. Ejecutar en Modo Desarrollo
```bash
npm run dev
```

### 3. Abrir en el Navegador
```
http://localhost:3000
```

## 🎯 Características Principales

### ✨ Dashboard Moderno
- **8 KPIs principales** con indicadores de tendencia
- **Filtros avanzados** con rango de fechas y búsqueda
- **Tasa BCV** con actualización en tiempo real
- **Tablas interactivas** con paginación y ordenamiento
- **Acciones rápidas** con atajos de teclado

### 📱 Responsive Design
- **Mobile**: 1 columna
- **Tablet**: 2 columnas  
- **Desktop**: 3-4 columnas

### 🌙 Dark Mode
- Cambio automático según preferencias del sistema
- Toggle manual disponible

### ♿ Accesibilidad
- Navegación completa por teclado
- Contraste AA en todos los elementos
- Roles ARIA implementados

## 🎮 Atajos de Teclado

- `C` - Nuevo Cliente
- `P` - Nuevo Producto
- `F` - Nueva Factura
- `Q` - Nueva Cotización
- `N` - Nueva Nota de Entrega

## 🔧 Scripts Disponibles

```bash
# Desarrollo
npm run dev

# Build para producción
npm run build

# Preview del build
npm run preview

# Linting
npm run lint

# Type checking
npm run type-check
```

## 📊 Datos Mock

El proyecto incluye datos de ejemplo para desarrollo:
- 3 clientes
- 5 productos
- 5 facturas
- Estadísticas calculadas automáticamente

## 🎨 Personalización

### Colores
Editar `tailwind.config.js` para cambiar la paleta de colores.

### Componentes
Todos los componentes están en `src/components/` y son completamente personalizables.

### Datos
Reemplazar los mocks en `src/mocks/data.ts` con llamadas a API reales.

## 🚀 Deploy

### Vercel
```bash
npm install -g vercel
vercel --prod
```

### Netlify
```bash
npm run build
# Subir carpeta dist/
```

## 🆘 Solución de Problemas

### Error de Dependencias
```bash
rm -rf node_modules package-lock.json
npm install
```

### Error de TypeScript
```bash
npm run type-check
```

### Error de Build
```bash
npm run build
```

## 📚 Documentación Completa

Ver `README.md` para documentación detallada y guías avanzadas.

---

**¡Listo para usar! 🎉**
