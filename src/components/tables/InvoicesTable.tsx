import React, { useMemo } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  createColumnHelper,
  flexRender,
  type ColumnDef,
  type SortingState,
  type ColumnFiltersState,
} from '@tanstack/react-table';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Invoice, InvoiceStatus } from '@/types';
import { formatCurrency, formatDate, getStatusColor, formatPaymentMethod } from '@/lib/format';
import { cn } from '@/lib/utils';
import { 
  Search, 
  ChevronLeft, 
  ChevronRight, 
  ChevronUp, 
  ChevronDown,
  Eye,
  Download,
  Send,
  MoreHorizontal
} from 'lucide-react';

interface InvoicesTableProps {
  data: Invoice[];
  loading?: boolean;
  onView?: (invoice: Invoice) => void;
  onDownload?: (invoice: Invoice) => void;
  onResend?: (invoice: Invoice) => void;
}

const columnHelper = createColumnHelper<Invoice>();

const InvoicesTable: React.FC<InvoicesTableProps> = ({
  data,
  loading = false,
  onView,
  onDownload,
  onResend,
}) => {
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([]);
  const [globalFilter, setGlobalFilter] = React.useState('');

  const columns = useMemo<ColumnDef<Invoice>[]>(
    () => [
      columnHelper.accessor('numero', {
        header: 'Nº Factura',
        cell: ({ getValue }) => (
          <span className="font-mono text-sm font-medium">
            {getValue()}
          </span>
        ),
      }),
      columnHelper.accessor('fecha', {
        header: 'Fecha',
        cell: ({ getValue }) => (
          <span className="text-sm">
            {formatDate(getValue())}
          </span>
        ),
      }),
      columnHelper.accessor('cliente', {
        header: 'Cliente',
        cell: ({ getValue }) => (
          <span className="text-sm font-medium">
            {getValue()}
          </span>
        ),
      }),
      columnHelper.accessor('total_usd', {
        header: 'Monto USD',
        cell: ({ getValue }) => (
          <span className="font-mono text-sm">
            {formatCurrency(getValue(), 'USD')}
          </span>
        ),
      }),
      columnHelper.accessor('total_bs', {
        header: 'Monto Bs',
        cell: ({ getValue }) => (
          <span className="font-mono text-sm text-muted-foreground">
            {formatCurrency(getValue(), 'BS')}
          </span>
        ),
      }),
      columnHelper.accessor('estado', {
        header: 'Estado',
        cell: ({ getValue }) => {
          const status = getValue() as InvoiceStatus;
          return (
            <Badge 
              variant="outline" 
              className={cn("text-xs", getStatusColor(status))}
            >
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </Badge>
          );
        },
      }),
      columnHelper.display({
        id: 'actions',
        header: 'Acciones',
        cell: ({ row }) => (
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onView?.(row.original)}
              className="h-8 w-8 p-0"
              aria-label={`Ver factura ${row.original.numero}`}
            >
              <Eye className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onDownload?.(row.original)}
              className="h-8 w-8 p-0"
              aria-label={`Descargar factura ${row.original.numero}`}
            >
              <Download className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onResend?.(row.original)}
              className="h-8 w-8 p-0"
              aria-label={`Reenviar factura ${row.original.numero}`}
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        ),
      }),
    ],
    [onView, onDownload, onResend]
  );

  const table = useReactTable({
    data,
    columns,
    state: {
      sorting,
      columnFilters,
      globalFilter,
    },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    initialState: {
      pagination: {
        pageSize: 10,
      },
    },
  });

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Últimas Facturas</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Skeleton className="h-10 w-full" />
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Últimas Facturas</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <div className="text-muted-foreground mb-4">
              <Search className="h-12 w-12 mx-auto mb-2" />
              <p>No hay facturas disponibles</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Últimas Facturas</CardTitle>
          <div className="flex items-center gap-2">
            <Input
              placeholder="Buscar facturas..."
              value={globalFilter}
              onChange={(e) => setGlobalFilter(e.target.value)}
              className="w-64"
            />
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="rounded-md border">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                {table.getHeaderGroups().map(headerGroup => (
                  <tr key={headerGroup.id} className="border-b">
                    {headerGroup.headers.map(header => (
                      <th
                        key={header.id}
                        className="px-4 py-3 text-left text-sm font-medium text-muted-foreground"
                      >
                        {header.isPlaceholder ? null : (
                          <div
                            className={cn(
                              "flex items-center gap-2",
                              header.column.getCanSort() && "cursor-pointer select-none hover:text-foreground"
                            )}
                            onClick={header.column.getToggleSortingHandler()}
                          >
                            {flexRender(
                              header.column.columnDef.header,
                              header.getContext()
                            )}
                            {header.column.getCanSort() && (
                              <div className="flex flex-col">
                                <ChevronUp 
                                  className={cn(
                                    "h-3 w-3",
                                    header.column.getIsSorted() === 'asc' ? "text-foreground" : "text-muted-foreground"
                                  )}
                                />
                                <ChevronDown 
                                  className={cn(
                                    "h-3 w-3 -mt-1",
                                    header.column.getIsSorted() === 'desc' ? "text-foreground" : "text-muted-foreground"
                                  )}
                                />
                              </div>
                            )}
                          </div>
                        )}
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody>
                {table.getRowModel().rows.map(row => (
                  <tr
                    key={row.id}
                    className="border-b hover:bg-muted/50 transition-colors"
                  >
                    {row.getVisibleCells().map(cell => (
                      <td key={cell.id} className="px-4 py-3">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Paginación */}
        <div className="flex items-center justify-between mt-4">
          <div className="text-sm text-muted-foreground">
            Mostrando {table.getState().pagination.pageIndex * table.getState().pagination.pageSize + 1} a{' '}
            {Math.min(
              (table.getState().pagination.pageIndex + 1) * table.getState().pagination.pageSize,
              table.getFilteredRowModel().rows.length
            )}{' '}
            de {table.getFilteredRowModel().rows.length} facturas
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
              aria-label="Página anterior"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="text-sm">
              Página {table.getState().pagination.pageIndex + 1} de{' '}
              {table.getPageCount()}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
              aria-label="Página siguiente"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default InvoicesTable;
