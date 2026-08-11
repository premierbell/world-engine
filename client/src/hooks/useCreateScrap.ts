import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createScrap } from '../api/scrap';

export function useCreateScrap() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ url, userContext, force }: { url: string; userContext?: string; force?: boolean }) =>
      createScrap(url, userContext, force),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scraps'] });
    },
  });
}
