import { useMutation, useQueryClient } from '@tanstack/react-query';
import { resummarizeScrap } from '../api/scrap';

export function useResummarizeScrap() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (scrapId: number) => resummarizeScrap(scrapId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scraps'] });
    },
  });
}
