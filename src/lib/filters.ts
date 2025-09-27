import { DashboardFilters, Invoice, InvoiceStatus, Currency } from '@/types';

/**
 * Opciones de filtro predefinidas
 */
export const FILTER_OPTIONS = {
  estados: [
    { value: 'todos', label: 'Todos los estados' },
    { value: 'pagada', label: 'Pagadas' },
    { value: 'pendiente', label: 'Pendientes' },
    { value: 'vencida', label: 'Vencidas' },
    { value: 'cancelada', label: 'Canceladas' },
  ] as const,
  
  monedas: [
    { value: 'USD', label: 'Dólares (USD)' },
    { value: 'BS', label: 'Bolívares (Bs)' },
  ] as const,
  
  orden: [
    { value: 'fecha', label: 'Por fecha' },
    { value: 'monto', label: 'Por monto' },
    { value: 'numero', label: 'Por número' },
    { value: 'cliente', label: 'Por cliente' },
  ] as const,
  
  rangos_fecha: [
    { value: 'hoy', label: 'Hoy' },
    { value: 'semana', label: 'Esta semana' },
    { value: 'mes', label: 'Este mes' },
    { value: 'trimestre', label: 'Este trimestre' },
    { value: 'año', label: 'Este año' },
    { value: 'personalizado', label: 'Personalizado' },
  ] as const,
} as const;

/**
 * Obtiene el rango de fechas basado en la opción seleccionada
 */
export function getDateRange(range: string): { desde: string; hasta: string } {
  const hoy = new Date();
  const hoyStr = hoy.toISOString().split('T')[0];
  
  switch (range) {
    case 'hoy':
      return { desde: hoyStr, hasta: hoyStr };
    
    case 'semana': {
      const inicioSemana = new Date(hoy);
      inicioSemana.setDate(hoy.getDate() - hoy.getDay());
      return {
        desde: inicioSemana.toISOString().split('T')[0],
        hasta: hoyStr,
      };
    }
    
    case 'mes': {
      const inicioMes = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
      return {
        desde: inicioMes.toISOString().split('T')[0],
        hasta: hoyStr,
      };
    }
    
    case 'trimestre': {
      const trimestre = Math.floor(hoy.getMonth() / 3);
      const inicioTrimestre = new Date(hoy.getFullYear(), trimestre * 3, 1);
      return {
        desde: inicioTrimestre.toISOString().split('T')[0],
        hasta: hoyStr,
      };
    }
    
    case 'año': {
      const inicioAño = new Date(hoy.getFullYear(), 0, 1);
      return {
        desde: inicioAño.toISOString().split('T')[0],
        hasta: hoyStr,
      };
    }
    
    default:
      return { desde: '', hasta: '' };
  }
}

/**
 * Aplica filtros a una lista de facturas
 */
export function filterInvoices(
  invoices: Invoice[],
  filters: DashboardFilters
): Invoice[] {
  let filtered = [...invoices];
  
  // Filtro por rango de fechas
  if (filters.fecha_desde && filters.fecha_hasta) {
    filtered = filtered.filter(invoice => {
      const invoiceDate = new Date(invoice.fecha);
      const desde = new Date(filters.fecha_desde!);
      const hasta = new Date(filters.fecha_hasta!);
      
      return invoiceDate >= desde && invoiceDate <= hasta;
    });
  }
  
  // Filtro por estado
  if (filters.estado && filters.estado !== 'todos') {
    filtered = filtered.filter(invoice => 
      invoice.estado === filters.estado
    );
  }
  
  // Filtro por búsqueda de texto
  if (filters.busqueda) {
    const searchTerm = filters.busqueda.toLowerCase();
    filtered = filtered.filter(invoice =>
      invoice.numero.toLowerCase().includes(searchTerm) ||
      invoice.cliente.toLowerCase().includes(searchTerm) ||
      invoice.productos.some(producto => 
        producto.nombre.toLowerCase().includes(searchTerm)
      )
    );
  }
  
  // Ordenamiento
  if (filters.orden) {
    filtered.sort((a, b) => {
      switch (filters.orden) {
        case 'fecha':
          return new Date(b.fecha).getTime() - new Date(a.fecha).getTime();
        case 'monto':
          return b.total_usd - a.total_usd;
        case 'numero':
          return b.numero.localeCompare(a.numero);
        case 'cliente':
          return a.cliente.localeCompare(b.cliente);
        default:
          return 0;
      }
    });
  }
  
  return filtered;
}

/**
 * Aplica filtros a una lista de productos
 */
export function filterProducts(
  products: any[],
  filters: DashboardFilters
): any[] {
  let filtered = [...products];
  
  // Filtro por búsqueda de texto
  if (filters.busqueda) {
    const searchTerm = filters.busqueda.toLowerCase();
    filtered = filtered.filter(product =>
      product.nombre.toLowerCase().includes(searchTerm) ||
      product.sku.toLowerCase().includes(searchTerm) ||
      (product.descripcion && product.descripcion.toLowerCase().includes(searchTerm))
    );
  }
  
  return filtered;
}

/**
 * Convierte filtros a query string para URL
 */
export function filtersToQueryString(filters: DashboardFilters): string {
  const params = new URLSearchParams();
  
  if (filters.fecha_desde) params.set('fecha_desde', filters.fecha_desde);
  if (filters.fecha_hasta) params.set('fecha_hasta', filters.fecha_hasta);
  if (filters.estado && filters.estado !== 'todos') params.set('estado', filters.estado);
  if (filters.moneda) params.set('moneda', filters.moneda);
  if (filters.busqueda) params.set('busqueda', filters.busqueda);
  if (filters.orden) params.set('orden', filters.orden);
  
  return params.toString();
}

/**
 * Convierte query string a filtros
 */
export function queryStringToFilters(searchParams: URLSearchParams): DashboardFilters {
  return {
    fecha_desde: searchParams.get('fecha_desde') || undefined,
    fecha_hasta: searchParams.get('fecha_hasta') || undefined,
    estado: (searchParams.get('estado') as InvoiceStatus) || 'todos',
    moneda: (searchParams.get('moneda') as Currency) || 'USD',
    busqueda: searchParams.get('busqueda') || undefined,
    orden: (searchParams.get('orden') as any) || 'fecha',
  };
}

/**
 * Resetea filtros a valores por defecto
 */
export function getDefaultFilters(): DashboardFilters {
  return {
    estado: 'todos',
    moneda: 'USD',
    orden: 'fecha',
  };
}

/**
 * Valida si un filtro está activo
 */
export function isFilterActive(filters: DashboardFilters): boolean {
  return !!(
    filters.fecha_desde ||
    filters.fecha_hasta ||
    (filters.estado && filters.estado !== 'todos') ||
    (filters.moneda && filters.moneda !== 'USD') ||
    filters.busqueda ||
    (filters.orden && filters.orden !== 'fecha')
  );
}

/**
 * Obtiene el texto descriptivo de los filtros activos
 */
export function getActiveFiltersDescription(filters: DashboardFilters): string {
  const descriptions: string[] = [];
  
  if (filters.fecha_desde && filters.fecha_hasta) {
    descriptions.push(`Fechas: ${filters.fecha_desde} - ${filters.fecha_hasta}`);
  }
  
  if (filters.estado && filters.estado !== 'todos') {
    const estadoLabel = FILTER_OPTIONS.estados.find(e => e.value === filters.estado)?.label;
    if (estadoLabel) descriptions.push(`Estado: ${estadoLabel}`);
  }
  
  if (filters.moneda && filters.moneda !== 'USD') {
    const monedaLabel = FILTER_OPTIONS.monedas.find(m => m.value === filters.moneda)?.label;
    if (monedaLabel) descriptions.push(`Moneda: ${monedaLabel}`);
  }
  
  if (filters.busqueda) {
    descriptions.push(`Búsqueda: "${filters.busqueda}"`);
  }
  
  if (filters.orden && filters.orden !== 'fecha') {
    const ordenLabel = FILTER_OPTIONS.orden.find(o => o.value === filters.orden)?.label;
    if (ordenLabel) descriptions.push(`Orden: ${ordenLabel}`);
  }
  
  return descriptions.join(' • ');
}

/**
 * Exporta datos filtrados a CSV
 */
export function exportToCSV<T>(
  data: T[],
  columns: Array<{ key: keyof T; header: string }>,
  filename: string = 'export.csv'
): void {
  if (data.length === 0) {
    alert('No hay datos para exportar');
    return;
  }
  
  // Crear encabezados
  const headers = columns.map(col => col.header).join(',');
  
  // Crear filas de datos
  const rows = data.map(item => 
    columns.map(col => {
      const value = item[col.key];
      // Escapar comillas y envolver en comillas si contiene comas
      const stringValue = String(value || '');
      return stringValue.includes(',') ? `"${stringValue.replace(/"/g, '""')}"` : stringValue;
    }).join(',')
  );
  
  // Combinar encabezados y filas
  const csvContent = [headers, ...rows].join('\n');
  
  // Crear y descargar archivo
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  
  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  link.style.visibility = 'hidden';
  
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
