# Sistema de Facturación - Dashboard Moderno

Dashboard moderno, accesible y responsive para el Sistema de Facturación, construido con React + TypeScript y Tailwind CSS.

## 🚀 Características

### ✨ UI/UX Moderna
- **Diseño minimalista** con sombras suaves y bordes redondeados
- **Grid responsivo** que se adapta a diferentes tamaños de pantalla
- **Dark mode** completo con soporte automático
- **Animaciones sutiles** que mejoran la experiencia sin afectar el rendimiento
- **Estados de carga** con skeletons elegantes
- **Estados vacíos** con ilustraciones y CTAs claros

### 📊 Dashboard Inteligente
- **KPIs en tiempo real**: Cuentas por Cobrar, Pagos Recibidos, Total Clientes, etc.
- **Filtros avanzados** con rango de fechas, estado, moneda y búsqueda
- **Tasa BCV** con actualización en tiempo real
- **Acciones rápidas** con atajos de teclado
- **Tablas interactivas** con paginación, ordenamiento y filtros

### ♿ Accesibilidad
- **Contraste AA** en todos los elementos
- **Navegación por teclado** completa
- **Roles ARIA** en tarjetas y componentes
- **Soporte para lectores de pantalla**
- **Focus management** mejorado

### 🔧 Tecnologías
- **React 18** con TypeScript
- **Tailwind CSS** para estilos
- **TanStack Table** para tablas avanzadas
- **Lucide React** para iconografía
- **date-fns** para manejo de fechas
- **Vite** para desarrollo y build

## 📦 Instalación

### Prerrequisitos
- **Node.js 18+** y npm (para el frontend)
- **Python 3.10+** y pip (para el backend)
- Git (para clonar el repositorio)

### Instalación Rápida (Windows)

1. **Clonar el repositorio**
   ```bash
   git clone <repository-url>
   cd sistema-facturacion-dashboard
   ```

2. **Ejecutar script de instalación automática**
   ```bash
   instalar_dependencias.bat
   ```

Este script instalará automáticamente todas las dependencias necesarias.

### Instalación Manual

#### 1. Instalar dependencias de Node.js (Frontend)

```bash
npm install
```

Esto instalará todas las dependencias del frontend y generará el archivo `package-lock.json` que asegura versiones consistentes entre diferentes máquinas.

#### 2. Instalar dependencias de Python (Backend)

**Opción A: Con entorno virtual (Recomendado)**

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt
```

**Opción B: Sin entorno virtual**

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Verificación de Instalación

Verifica que todo esté instalado correctamente:

```bash
# Verificar Node.js
node --version
npm --version

# Verificar Python
python --version
pip --version

# Verificar módulos de Python
python -c "import flask; import requests; print('✅ Python OK')"
```

### Ejecutar la Aplicación

**Backend (Python/Flask):**
```bash
python app.py
```

**Frontend (React/Vite):**
```bash
npm run dev
```

Luego abre en el navegador:
- Frontend: `http://localhost:3000` (o el puerto que indique Vite)
- Backend: `http://localhost:5000` (o el puerto configurado en app.py)

### Solución de Problemas

**Error: "faltan dependencias" o "module not found"**

1. Asegúrate de haber ejecutado `npm install` y `pip install -r requirements.txt`
2. Verifica que `package-lock.json` esté presente en el repositorio
3. Si usas entorno virtual, asegúrate de activarlo antes de ejecutar el backend
4. En Windows, ejecuta `instalar_dependencias.bat` para una instalación completa

**Error: "Python no encontrado"**

- Instala Python desde https://www.python.org/
- Asegúrate de marcar "Add Python to PATH" durante la instalación

**Error: "Node.js no encontrado"**

- Instala Node.js desde https://nodejs.org/
- Reinicia la terminal después de la instalación

## 🏗️ Estructura del Proyecto

```
src/
├── components/
│   ├── dashboard/
│   │   ├── StatsCard.tsx          # Tarjeta de estadísticas reutilizable
│   │   ├── FiltersBar.tsx         # Barra de filtros avanzados
│   │   └── BcvRateCard.tsx        # Tarjeta de tasa BCV
│   ├── tables/
│   │   ├── InvoicesTable.tsx      # Tabla de facturas
│   │   └── LowStockTable.tsx      # Tabla de productos con bajo stock
│   └── ui/                        # Componentes base (Button, Card, etc.)
├── lib/
│   ├── format.ts                  # Utilidades de formateo
│   ├── filters.ts                 # Helpers para filtros
│   └── utils.ts                   # Utilidades generales
├── mocks/
│   └── data.ts                    # Datos mock para desarrollo
├── types/
│   └── index.ts                   # Definiciones de tipos TypeScript
├── pages/
│   └── Dashboard.tsx              # Página principal
├── main.tsx                       # Punto de entrada
└── index.css                      # Estilos globales
```

## 🎨 Componentes Principales

### StatsCard
Tarjeta reutilizable para mostrar KPIs con:
- Icono personalizable
- Formateo de moneda automático
- Indicadores de tendencia
- Tooltips informativos
- Estados de carga

### FiltersBar
Barra de filtros avanzada con:
- Búsqueda global
- Filtros por estado y moneda
- Rango de fechas (predefinido y personalizado)
- Exportación a CSV
- Reset de filtros

### InvoicesTable
Tabla de facturas con:
- Paginación automática
- Ordenamiento por columnas
- Filtros por columna
- Acciones (ver, descargar, reenviar)
- Búsqueda global

### LowStockTable
Tabla de productos con bajo stock:
- Alertas visuales
- Indicadores de estado
- Acciones de reposición
- Filtros inteligentes

## 🔧 Configuración

### Variables de Entorno
Crear archivo `.env.local`:
```env
VITE_API_URL=http://localhost:5000/api
VITE_BCV_API_URL=https://api.bcv.org.ve
```

### Personalización de Temas
Los colores y estilos se pueden personalizar en `tailwind.config.js`:

```javascript
theme: {
  extend: {
    colors: {
      primary: {
        DEFAULT: "hsl(var(--primary))",
        foreground: "hsl(var(--primary-foreground))",
      },
      // ... más colores
    }
  }
}
```

## 📱 Responsive Design

El dashboard se adapta automáticamente a diferentes tamaños:

- **Mobile (< 640px)**: 1 columna
- **Tablet (640px - 1024px)**: 2 columnas  
- **Desktop (1024px - 1280px)**: 3 columnas
- **Large Desktop (> 1280px)**: 4 columnas

## ♿ Accesibilidad

### Características Implementadas
- **Contraste AA**: Todos los colores cumplen con WCAG 2.1 AA
- **Navegación por teclado**: Tab, Enter, Escape, flechas
- **Roles ARIA**: region, button, table, etc.
- **Labels descriptivos**: Para todos los controles
- **Focus visible**: Indicadores claros de foco
- **Motion respect**: Respeta preferencias de movimiento reducido

### Atajos de Teclado
- `C`: Nuevo Cliente
- `P`: Nuevo Producto  
- `F`: Nueva Factura
- `Q`: Nueva Cotización
- `N`: Nueva Nota de Entrega

## 🚀 Scripts Disponibles

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

## 🔄 Integración con Backend

### API Endpoints Esperados

```typescript
// Obtener estadísticas
GET /api/dashboard/stats

// Obtener facturas
GET /api/invoices?page=1&limit=10&filters=...

// Obtener productos
GET /api/products?low_stock=true

// Actualizar tasa BCV
POST /api/bcv/update-rate
```

### Formato de Respuesta

```typescript
interface ApiResponse<T> {
  data: T;
  success: boolean;
  message?: string;
  error?: string;
}
```

## 🧪 Testing

```bash
# Ejecutar tests (cuando se implementen)
npm run test

# Tests con coverage
npm run test:coverage

# Tests E2E
npm run test:e2e
```

## 📦 Build y Deploy

### Build para Producción
```bash
npm run build
```

### Deploy en Vercel
```bash
npm install -g vercel
vercel --prod
```

### Deploy en Netlify
```bash
npm run build
# Subir carpeta dist/ a Netlify
```

## 🤝 Contribución

1. Fork el proyecto
2. Crear branch para feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## 🆘 Soporte

Para soporte técnico o preguntas:
- Crear un issue en GitHub
- Contactar al equipo de desarrollo
- Revisar la documentación de componentes

## 🔮 Roadmap

### Próximas Características
- [ ] Gráficos interactivos con Chart.js
- [ ] Notificaciones en tiempo real
- [ ] Exportación a PDF
- [ ] Modo offline con PWA
- [ ] Tests unitarios y E2E
- [ ] Internacionalización (i18n)
- [ ] Temas personalizables
- [ ] Dashboard personalizable por usuario

---

**Desarrollado con ❤️ para el Sistema de Facturación**