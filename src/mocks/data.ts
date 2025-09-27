import { Invoice, Customer, Product, Stats, BcvRate } from '@/types';

// Datos mock para desarrollo y testing
export const mockCustomers: Customer[] = [
  {
    id: '1',
    nombre: 'Empresa ABC C.A.',
    email: 'contacto@empresaabc.com',
    telefono: '+58 212 555-0123',
    direccion: 'Av. Principal, Torre ABC, Piso 10, Caracas',
    ruc: 'J-12345678-9',
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
  },
  {
    id: '2',
    nombre: 'Comercial XYZ S.R.L.',
    email: 'ventas@comercialxyz.com',
    telefono: '+58 212 555-0456',
    direccion: 'Calle Comercio #123, Valencia',
    ruc: 'J-87654321-0',
    created_at: '2024-01-20T14:30:00Z',
    updated_at: '2024-01-20T14:30:00Z',
  },
  {
    id: '3',
    nombre: 'Distribuidora Norte',
    email: 'info@distribuidoranorte.com',
    telefono: '+58 212 555-0789',
    direccion: 'Zona Industrial Norte, Maracay',
    ruc: 'J-11223344-5',
    created_at: '2024-02-01T09:15:00Z',
    updated_at: '2024-02-01T09:15:00Z',
  },
];

export const mockProducts: Product[] = [
  {
    id: '1',
    nombre: 'Laptop Dell Inspiron 15',
    sku: 'DELL-INS15-001',
    descripcion: 'Laptop Dell Inspiron 15 pulgadas, Intel i5, 8GB RAM, 256GB SSD',
    precio: 1200,
    stock: 5,
    punto_pedido: 3,
    categoria: 'Computadoras',
    created_at: '2024-01-10T08:00:00Z',
    updated_at: '2024-01-10T08:00:00Z',
  },
  {
    id: '2',
    nombre: 'Mouse Inalámbrico Logitech',
    sku: 'LOG-MOUSE-001',
    descripcion: 'Mouse inalámbrico Logitech M705, 3 años de batería',
    precio: 45,
    stock: 2,
    punto_pedido: 5,
    categoria: 'Accesorios',
    created_at: '2024-01-12T10:30:00Z',
    updated_at: '2024-01-12T10:30:00Z',
  },
  {
    id: '3',
    nombre: 'Teclado Mecánico RGB',
    sku: 'TEC-MEC-001',
    descripcion: 'Teclado mecánico con retroiluminación RGB, switches azules',
    precio: 85,
    stock: 8,
    punto_pedido: 4,
    categoria: 'Accesorios',
    created_at: '2024-01-15T11:45:00Z',
    updated_at: '2024-01-15T11:45:00Z',
  },
  {
    id: '4',
    nombre: 'Monitor Samsung 24"',
    sku: 'SAM-MON24-001',
    descripcion: 'Monitor Samsung 24 pulgadas, Full HD, 75Hz',
    precio: 180,
    stock: 1,
    punto_pedido: 2,
    categoria: 'Monitores',
    created_at: '2024-01-18T13:20:00Z',
    updated_at: '2024-01-18T13:20:00Z',
  },
  {
    id: '5',
    nombre: 'Impresora HP LaserJet',
    sku: 'HP-LJ-001',
    descripcion: 'Impresora láser HP LaserJet Pro, impresión a doble cara',
    precio: 250,
    stock: 0,
    punto_pedido: 1,
    categoria: 'Impresoras',
    created_at: '2024-01-20T16:00:00Z',
    updated_at: '2024-01-20T16:00:00Z',
  },
];

export const mockInvoices: Invoice[] = [
  {
    id: '1',
    numero: 'F-2024-001',
    fecha: '2024-01-15',
    cliente: 'Empresa ABC C.A.',
    cliente_id: '1',
    total_usd: 1250,
    total_bs: 43750,
    total_abonado: 1250,
    saldo: 0,
    estado: 'pagada',
    productos: [
      {
        id: '1',
        nombre: 'Laptop Dell Inspiron 15',
        cantidad: 1,
        precio_unitario: 1200,
        total: 1200,
        sku: 'DELL-INS15-001',
      },
      {
        id: '2',
        nombre: 'Mouse Inalámbrico Logitech',
        cantidad: 1,
        precio_unitario: 45,
        total: 45,
        sku: 'LOG-MOUSE-001',
      },
    ],
    pagos: [
      {
        id: '1',
        fecha: '2024-01-15',
        monto: 1250,
        metodo: 'transferencia',
        referencia: 'TXN-001234',
      },
    ],
    vencimiento: '2024-02-15',
    observaciones: 'Pago recibido el mismo día',
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
  },
  {
    id: '2',
    numero: 'F-2024-002',
    fecha: '2024-01-20',
    cliente: 'Comercial XYZ S.R.L.',
    cliente_id: '2',
    total_usd: 265,
    total_bs: 9275,
    total_abonado: 100,
    saldo: 165,
    estado: 'pendiente',
    productos: [
      {
        id: '3',
        nombre: 'Teclado Mecánico RGB',
        cantidad: 2,
        precio_unitario: 85,
        total: 170,
        sku: 'TEC-MEC-001',
      },
      {
        id: '4',
        nombre: 'Monitor Samsung 24"',
        cantidad: 1,
        precio_unitario: 180,
        total: 180,
        sku: 'SAM-MON24-001',
      },
    ],
    pagos: [
      {
        id: '2',
        fecha: '2024-01-20',
        monto: 100,
        metodo: 'efectivo',
        observaciones: 'Anticipo recibido',
      },
    ],
    vencimiento: '2024-02-20',
    observaciones: 'Pendiente de pago del saldo',
    created_at: '2024-01-20T14:30:00Z',
    updated_at: '2024-01-20T14:30:00Z',
  },
  {
    id: '3',
    numero: 'F-2024-003',
    fecha: '2024-01-25',
    cliente: 'Distribuidora Norte',
    cliente_id: '3',
    total_usd: 500,
    total_bs: 17500,
    total_abonado: 0,
    saldo: 500,
    estado: 'vencida',
    productos: [
      {
        id: '5',
        nombre: 'Impresora HP LaserJet',
        cantidad: 2,
        precio_unitario: 250,
        total: 500,
        sku: 'HP-LJ-001',
      },
    ],
    vencimiento: '2024-01-30',
    observaciones: 'Factura vencida, contactar cliente',
    created_at: '2024-01-25T09:15:00Z',
    updated_at: '2024-01-25T09:15:00Z',
  },
  {
    id: '4',
    numero: 'F-2024-004',
    fecha: '2024-02-01',
    cliente: 'Empresa ABC C.A.',
    cliente_id: '1',
    total_usd: 90,
    total_bs: 3150,
    total_abonado: 90,
    saldo: 0,
    estado: 'pagada',
    productos: [
      {
        id: '2',
        nombre: 'Mouse Inalámbrico Logitech',
        cantidad: 2,
        precio_unitario: 45,
        total: 90,
        sku: 'LOG-MOUSE-001',
      },
    ],
    pagos: [
      {
        id: '3',
        fecha: '2024-02-01',
        monto: 90,
        metodo: 'cheque',
        referencia: 'CHQ-001234',
      },
    ],
    vencimiento: '2024-03-01',
    observaciones: 'Pago recibido por cheque',
    created_at: '2024-02-01T11:00:00Z',
    updated_at: '2024-02-01T11:00:00Z',
  },
  {
    id: '5',
    numero: 'F-2024-005',
    fecha: '2024-02-05',
    cliente: 'Comercial XYZ S.R.L.',
    cliente_id: '2',
    total_usd: 340,
    total_bs: 11900,
    total_abonado: 0,
    saldo: 340,
    estado: 'pendiente',
    productos: [
      {
        id: '1',
        nombre: 'Laptop Dell Inspiron 15',
        cantidad: 1,
        precio_unitario: 1200,
        total: 1200,
        sku: 'DELL-INS15-001',
      },
    ],
    vencimiento: '2024-03-05',
    observaciones: 'Factura pendiente de pago',
    created_at: '2024-02-05T16:30:00Z',
    updated_at: '2024-02-05T16:30:00Z',
  },
];

export const mockStats: Stats = {
  total_clientes: 3,
  total_productos: 5,
  facturas_mes: 2,
  total_cobrar_usd: 1005,
  total_cobrar_bs: 35175,
  total_pagos_recibidos_usd: 1340,
  total_pagos_recibidos_bs: 46900,
  total_facturado_usd: 2445,
  promedio_factura_usd: 489,
  tasa_bcv: 35,
  ultima_actualizacion: '2024-02-10T08:00:00Z',
};

export const mockBcvRate: BcvRate = {
  tasa: 35.0,
  fecha: '2024-02-10',
  ultima_actualizacion: '2024-02-10T08:00:00Z',
};

// Función para simular delay de API
export const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// Función para simular error de API
export const simulateApiError = (probability: number = 0.1) => {
  if (Math.random() < probability) {
    throw new Error('Error simulado de API');
  }
};

// Función para obtener datos con delay simulado
export const fetchMockData = async <T>(data: T, delayMs: number = 500): Promise<T> => {
  await delay(delayMs);
  simulateApiError(0.05); // 5% de probabilidad de error
  return data;
};
