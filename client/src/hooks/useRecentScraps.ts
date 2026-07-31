import { useQuery } from '@tanstack/react-query';
import { fetchScraps } from '../api/scrap';

export function useRecentScraps() {
  return useQuery({
    queryKey: ['scraps', 'all'],
    queryFn: () => fetchScraps(),
  });
}
