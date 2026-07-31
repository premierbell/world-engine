import { useQuery } from '@tanstack/react-query';
import { fetchIslands } from '../api/island';

export function useIslands() {
  return useQuery({
    queryKey: ['islands'],
    queryFn: fetchIslands,
  });
}
