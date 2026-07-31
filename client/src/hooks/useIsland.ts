import { useQuery } from '@tanstack/react-query';
import { fetchIsland } from '../api/island';

export function useIsland(id: number, enabled = true) {
  return useQuery({
    queryKey: ['island', id],
    queryFn: () => fetchIsland(id),
    enabled,
  });
}
