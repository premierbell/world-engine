import { useQuery } from '@tanstack/react-query';
import { fetchScraps } from '../api/scrap';

export function usePendingScraps() {
  return useQuery({
    queryKey: ['scraps', { confirmed: false }],
    queryFn: () => fetchScraps(false),
  });
}
