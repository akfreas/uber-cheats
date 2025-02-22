import {
  ArrowDownward as ArrowDownwardIcon,
  ArrowUpward as ArrowUpwardIcon,
} from '@mui/icons-material';
import {
  Box,
  Container,
  IconButton,
  Link,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable
} from '@tanstack/react-table';
import React, { useEffect, useMemo, useState } from 'react';
import { useLocation } from 'react-router-dom';
import config from '../config';

interface Deal {
  restaurant: string;
  item_name: string;
  price: number;
  description: string;
  promotion_type: string;
  delivery_fee: string;
  rating_and_reviews: string;
  delivery_time: string;
  url: string;
  timestamp: string;
}

const columnHelper = createColumnHelper<Deal>();

const DealsTable: React.FC = () => {
  const [data, setData] = useState<Deal[]>([]);
  const [globalFilter, setGlobalFilter] = useState('');
  const [error, setError] = useState('');
  const location = useLocation();

  useEffect(() => {
    const fetchDeals = async () => {
      try {
        // Get hash from URL if present
        const hash = location.hash.slice(1); // Remove the # character
        
        // Choose endpoint based on whether we have a hash
        const endpoint = hash ? config.endpoints.dealsByHash(hash) : config.endpoints.deals;
        
        const response = await fetch(endpoint);
        if (!response.ok) {
          if (response.status === 404) {
            throw new Error('No deals found for this link');
          }
          throw new Error('Failed to fetch deals');
        }
        const deals = await response.json();
        setData(deals);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      }
    };

    fetchDeals();
  }, [location.hash]);

  const columns = useMemo(() => [
    columnHelper.accessor((row) => row.restaurant, {
      id: 'restaurant',
      header: 'Restaurant',
      cell: info => info.getValue(),
    }),
    columnHelper.accessor((row) => row.item_name, {
      id: 'item_name',
      header: 'Item',
      cell: info => info.getValue(),
    }),
    columnHelper.accessor((row) => row.price, {
      id: 'price',
      header: 'Price',
      cell: info => `€${info.getValue().toFixed(2)}`,
    }),
    columnHelper.accessor((row) => row.promotion_type, {
      id: 'promotion_type',
      header: 'Promotion',
      cell: info => info.getValue(),
    }),
    columnHelper.accessor((row) => row.delivery_fee, {
      id: 'delivery_fee',
      header: 'Delivery Fee',
      cell: info => info.getValue(),
    }),
    columnHelper.accessor((row) => row.rating_and_reviews, {
      id: 'rating_and_reviews',
      header: 'Rating',
      cell: info => info.getValue(),
    }),
    columnHelper.accessor((row) => row.delivery_time, {
      id: 'delivery_time',
      header: 'Delivery Time',
      cell: info => info.getValue(),
    }),
    columnHelper.accessor((row) => row.url, {
      id: 'url',
      header: 'Link',
      cell: info => (
        <Link href={info.getValue()} target="_blank" rel="noopener noreferrer">
          View
        </Link>
      ),
    }),
  ], []);

  const table = useReactTable({
    data,
    columns,
    state: {
      globalFilter,
    },
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  return (
    <Container maxWidth="xl">
      <Box sx={{ py: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Found Deals
        </Typography>

        <TextField
          fullWidth
          label="Search deals..."
          variant="outlined"
          value={globalFilter}
          onChange={e => setGlobalFilter(e.target.value)}
          sx={{ mb: 2 }}
        />

        {error ? (
          <Typography color="error">{error}</Typography>
        ) : (
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                {table.getHeaderGroups().map(headerGroup => (
                  <TableRow key={headerGroup.id}>
                    {headerGroup.headers.map(header => (
                      <TableCell
                        key={header.id}
                        onClick={header.column.getToggleSortingHandler()}
                        sx={{ 
                          cursor: 'pointer',
                          fontWeight: 'bold',
                          '&:hover': {
                            backgroundColor: 'rgba(0, 0, 0, 0.04)',
                          },
                        }}
                      >
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          {flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                          {header.column.getIsSorted() && (
                            <IconButton size="small">
                              {header.column.getIsSorted() === 'asc' ? (
                                <ArrowUpwardIcon />
                              ) : (
                                <ArrowDownwardIcon />
                              )}
                            </IconButton>
                          )}
                        </Box>
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableHead>
              <TableBody>
                {table.getRowModel().rows.map(row => (
                  <TableRow key={row.id}>
                    {row.getVisibleCells().map(cell => (
                      <TableCell key={cell.id}>
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext()
                        )}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Box>
    </Container>
  );
};

export default DealsTable; 