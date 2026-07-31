import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createScrap } from '../api/scrap';

export function useCreateScrap() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ url, userContext }: { url: string; userContext?: string }) =>
      createScrap(url, userContext),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scraps'] });
    },
  });
}
