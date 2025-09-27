import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { StatsCardProps } from '@/types';
import { formatCurrency, formatNumber, formatPercentage } from '@/lib/format';
import { cn } from '@/lib/utils';
import { 
  TrendingUp, 
  TrendingDown, 
  Minus, 
  ArrowUpRight
} from 'lucide-react';

const StatsCard: React.FC<StatsCardProps> = ({
  title,
  value,
  subtitle,
  trend,
  trendValue,
  helpText,
  icon: Icon,
  color = 'blue',
  currency,
  tooltip,
  onClick,
  loading = false,
}) => {
  const formatValue = () => {
    if (typeof value === 'string') return value;
    
    if (currency) {
      return formatCurrency(value, currency);
    }
    
    return formatNumber(value);
  };

  const getTrendIcon = () => {
    if (!trend || !trendValue) return null;
    
    switch (trend) {
      case 'up':
        return <TrendingUp className="h-3 w-3" />;
      case 'down':
        return <TrendingDown className="h-3 w-3" />;
      default:
        return <Minus className="h-3 w-3" />;
    }
  };

  const getTrendColor = () => {
    if (!trend || !trendValue) return 'text-muted-foreground';
    
    switch (trend) {
      case 'up':
        return 'text-green-600 dark:text-green-400';
      case 'down':
        return 'text-red-600 dark:text-red-400';
      default:
        return 'text-muted-foreground';
    }
  };

  const getTrendText = () => {
    if (!trend || !trendValue) return null;
    
    const percentage = formatPercentage(Math.abs(trendValue));
    const prefix = trend === 'up' ? '+' : trend === 'down' ? '-' : '';
    
    return `${prefix}${percentage}`;
  };

  const getColorClasses = () => {
    switch (color) {
      case 'red':
        return {
          iconBg: 'bg-red-100 dark:bg-red-900/20',
          iconColor: 'text-red-500 dark:text-red-400',
          iconHover: 'group-hover:bg-red-200 dark:group-hover:bg-red-900/30'
        };
      case 'green':
        return {
          iconBg: 'bg-green-100 dark:bg-green-900/20',
          iconColor: 'text-green-500 dark:text-green-400',
          iconHover: 'group-hover:bg-green-200 dark:group-hover:bg-green-900/30'
        };
      case 'blue':
        return {
          iconBg: 'bg-blue-100 dark:bg-blue-900/20',
          iconColor: 'text-blue-500 dark:text-blue-400',
          iconHover: 'group-hover:bg-blue-200 dark:group-hover:bg-blue-900/30'
        };
      case 'yellow':
        return {
          iconBg: 'bg-yellow-100 dark:bg-yellow-900/20',
          iconColor: 'text-yellow-500 dark:text-yellow-400',
          iconHover: 'group-hover:bg-yellow-200 dark:group-hover:bg-yellow-900/30'
        };
      default:
        return {
          iconBg: 'bg-blue-100 dark:bg-blue-900/20',
          iconColor: 'text-blue-500 dark:text-blue-400',
          iconHover: 'group-hover:bg-blue-200 dark:group-hover:bg-blue-900/30'
        };
    }
  };

  const colorClasses = getColorClasses();

  if (loading) {
    return (
      <Card 
        className="group relative overflow-hidden transition-all duration-200 hover:shadow-lg motion-safe:hover:scale-105 rounded-2xl bg-white dark:bg-slate-800 shadow-md"
        role="region"
        aria-label={`Cargando ${title}`}
      >
        <CardContent className="p-5 flex flex-col gap-2">
          <div className="flex items-start justify-between">
            <div className="space-y-2 flex-1">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-8 w-20" />
              <Skeleton className="h-3 w-16" />
            </div>
            <Skeleton className="h-10 w-10 rounded-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card 
      className={cn(
        "group relative overflow-hidden transition-all duration-200 hover:shadow-lg motion-safe:hover:scale-105 rounded-2xl bg-white dark:bg-slate-800 shadow-md",
        onClick && "hover:ring-2 hover:ring-offset-2 hover:ring-indigo-500 cursor-pointer"
      )}
      role="region"
      aria-label={`${title}: ${formatValue()}`}
      onClick={onClick}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={(e) => {
        if (onClick && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          onClick();
        }
      }}
    >
      <CardContent className="p-5 flex flex-col gap-2">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">
              {title}
            </h3>
            
            <div className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-1">
              {formatValue()}
            </div>
            
            {subtitle && (
              <div className="text-sm text-gray-500 dark:text-gray-400">
                {subtitle}
              </div>
            )}
            
            {trend && trendValue && (
              <div className={cn("flex items-center gap-1 text-xs mt-2", getTrendColor())}>
                {getTrendIcon()}
                <span>{getTrendText()}</span>
              </div>
            )}
            
            {helpText && (
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                {helpText}
              </p>
            )}
          </div>
          
          <div className="flex-shrink-0">
            <div className={cn(
              "w-10 h-10 rounded-full flex items-center justify-center transition-all duration-200",
              colorClasses.iconBg,
              colorClasses.iconHover
            )}>
              <Icon className={cn("h-5 w-5", colorClasses.iconColor)} />
            </div>
          </div>
        </div>
        
        {/* Indicador de interacción */}
        {onClick && (
          <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
            <ArrowUpRight className="h-4 w-4 text-gray-400" />
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default StatsCard;

