// Tipos principales del sistema
export interface Invoice {
  id: string;
  numero: string;
  fecha: string;
  cliente: string;
  cliente_id: string;
  total_usd: number;
  total_bs: number;
  total_abonado: number;
  saldo: number;
  estado: InvoiceStatus;
  productos: InvoiceProduct[];
  pagos?: Payment[];
  vencimiento?: string;
  observaciones?: string;
  created_at: string;
  updated_at: string;
}

export interface InvoiceProduct {
  id: string;
  nombre: string;
  cantidad: number;
  precio_unitario: number;
  total: number;
  sku?: string;
}

export interface Payment {
  id: string;
  fecha: string;
  monto: number;
  metodo: PaymentMethod;
  referencia?: string;
  observaciones?: string;
}

export interface Customer {
  id: string;
  nombre: string;
  email?: string;
  telefono?: string;
  direccion?: string;
  ruc?: string;
  created_at: string;
  updated_at: string;
}

export interface Product {
  id: string;
  nombre: string;
  sku: string;
  descripcion?: string;
  precio: number;
  stock: number;
  punto_pedido: number;
  categoria?: string;
  imagen?: string;
  created_at: string;
  updated_at: string;
}

export interface Stats {
  total_clientes: number;
  total_productos: number;
  facturas_mes: number;
  total_cobrar_usd: number;
  total_cobrar_bs: number;
  total_pagos_recibidos_usd: number;
  total_pagos_recibidos_bs: number;
  total_facturado_usd: number;
  promedio_factura_usd: number;
  tasa_bcv: number;
  ultima_actualizacion: string;
}

export interface DashboardFilters {
  fecha_desde?: string;
  fecha_hasta?: string;
  estado?: InvoiceStatus | 'todos';
  moneda?: Currency;
  busqueda?: string;
  orden?: SortOption;
}

export interface BcvRate {
  tasa: number;
  fecha: string;
  ultima_actualizacion: string;
}

// Enums
export type InvoiceStatus = 'pagada' | 'pendiente' | 'vencida' | 'cancelada';
export type Currency = 'USD' | 'BS';
export type PaymentMethod = 'efectivo' | 'transferencia' | 'cheque' | 'tarjeta';
export type SortOption = 'fecha' | 'monto' | 'numero' | 'cliente';

// Props de componentes
export interface StatsCardProps {
  title: string;
  value: number | string;
  subtitle?: string;
  trend?: 'up' | 'down' | 'flat';
  trendValue?: number;
  helpText?: string;
  icon: React.ComponentType<{ className?: string }>;
  color?: 'red' | 'green' | 'blue' | 'yellow';
  currency?: Currency;
  tooltip?: string;
  onClick?: () => void;
  loading?: boolean;
}

export interface FiltersBarProps {
  filters: DashboardFilters;
  onFiltersChange: (filters: DashboardFilters) => void;
  onReset: () => void;
  onExport: () => void;
  bcvRate: BcvRate;
  onUpdateBcvRate: () => void;
  loading?: boolean;
}

export interface BcvRateCardProps {
  rate: BcvRate;
  onUpdate: () => void;
  loading?: boolean;
}

export interface TableColumn<T> {
  key: keyof T;
  header: string;
  accessorKey?: string;
  cell?: (props: { getValue: () => any; row: { original: T } }) => React.ReactNode;
  sortable?: boolean;
  filterable?: boolean;
}

// Estados de carga
export interface LoadingState {
  stats: boolean;
  invoices: boolean;
  products: boolean;
  bcvRate: boolean;
}

// Respuestas de API
export interface ApiResponse<T> {
  data: T;
  success: boolean;
  message?: string;
  error?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
  totalPages: number;
}
