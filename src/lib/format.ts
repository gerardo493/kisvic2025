import { format, parseISO, isValid } from 'date-fns';
import { es } from 'date-fns/locale';
import { Currency } from '@/types';

/**
 * Formatea un número como moneda según la moneda especificada
 */
export function formatCurrency(
  amount: number,
  currency: Currency = 'USD',
  locale: string = 'es-VE'
): string {
  const formatter = new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: currency === 'USD' ? 'USD' : 'VES',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  return formatter.format(amount);
}

/**
 * Formatea un número con separadores de miles
 */
export function formatNumber(
  value: number,
  decimals: number = 0,
  locale: string = 'es-VE'
): string {
  return new Intl.NumberFormat(locale, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

/**
 * Formatea una fecha en formato dd/mm/yyyy
 */
export function formatDate(
  date: string | Date,
  pattern: string = 'dd/MM/yyyy'
): string {
  try {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    
    if (!isValid(dateObj)) {
      return 'Fecha inválida';
    }

    return format(dateObj, pattern, { locale: es });
  } catch (error) {
    console.error('Error formateando fecha:', error);
    return 'Fecha inválida';
  }
}

/**
 * Formatea una fecha relativa (ej: "hace 2 días")
 */
export function formatRelativeDate(date: string | Date): string {
  try {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    
    if (!isValid(dateObj)) {
      return 'Fecha inválida';
    }

    const now = new Date();
    const diffInDays = Math.floor((now.getTime() - dateObj.getTime()) / (1000 * 60 * 60 * 24));

    if (diffInDays === 0) {
      return 'Hoy';
    } else if (diffInDays === 1) {
      return 'Ayer';
    } else if (diffInDays < 7) {
      return `Hace ${diffInDays} días`;
    } else if (diffInDays < 30) {
      const weeks = Math.floor(diffInDays / 7);
      return `Hace ${weeks} semana${weeks > 1 ? 's' : ''}`;
    } else {
      return formatDate(dateObj);
    }
  } catch (error) {
    console.error('Error formateando fecha relativa:', error);
    return 'Fecha inválida';
  }
}

/**
 * Formatea un porcentaje
 */
export function formatPercentage(
  value: number,
  decimals: number = 1,
  locale: string = 'es-VE'
): string {
  return new Intl.NumberFormat(locale, {
    style: 'percent',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value / 100);
}

/**
 * Formatea un número de teléfono venezolano
 */
export function formatPhoneNumber(phone: string): string {
  // Remover todos los caracteres no numéricos
  const cleaned = phone.replace(/\D/g, '');
  
  // Formato venezolano: +58 (xxx) xxx-xxxx
  if (cleaned.length === 11 && cleaned.startsWith('58')) {
    return `+58 (${cleaned.slice(2, 5)}) ${cleaned.slice(5, 8)}-${cleaned.slice(8)}`;
  }
  
  // Formato local: (0xxx) xxx-xxxx
  if (cleaned.length === 10 && cleaned.startsWith('0')) {
    return `(${cleaned.slice(0, 4)}) ${cleaned.slice(4, 7)}-${cleaned.slice(7)}`;
  }
  
  return phone; // Devolver original si no coincide con formatos conocidos
}

/**
 * Formatea un RUC venezolano
 */
export function formatRUC(ruc: string): string {
  // Remover todos los caracteres no numéricos
  const cleaned = ruc.replace(/\D/g, '');
  
  // Formato: V-12345678-9
  if (cleaned.length >= 8) {
    return `V-${cleaned.slice(0, -1)}-${cleaned.slice(-1)}`;
  }
  
  return ruc;
}

/**
 * Trunca texto a una longitud específica
 */
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) {
    return text;
  }
  
  return text.slice(0, maxLength) + '...';
}

/**
 * Convierte bytes a formato legible
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Formatea un estado de factura con colores
 */
export function getStatusColor(status: string): string {
  switch (status.toLowerCase()) {
    case 'pagada':
      return 'text-green-600 bg-green-50 dark:text-green-400 dark:bg-green-900/20';
    case 'pendiente':
      return 'text-yellow-600 bg-yellow-50 dark:text-yellow-400 dark:bg-yellow-900/20';
    case 'vencida':
      return 'text-red-600 bg-red-50 dark:text-red-400 dark:bg-red-900/20';
    case 'cancelada':
      return 'text-gray-600 bg-gray-50 dark:text-gray-400 dark:bg-gray-900/20';
    default:
      return 'text-gray-600 bg-gray-50 dark:text-gray-400 dark:bg-gray-900/20';
  }
}

/**
 * Formatea un método de pago
 */
export function formatPaymentMethod(method: string): string {
  const methods: Record<string, string> = {
    efectivo: 'Efectivo',
    transferencia: 'Transferencia',
    cheque: 'Cheque',
    tarjeta: 'Tarjeta',
  };
  
  return methods[method.toLowerCase()] || method;
}
