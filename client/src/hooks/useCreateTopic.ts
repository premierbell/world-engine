import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createTopic } from '../api/topic';

export function useCreateTopic() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ islandId, name, scrapIds }: { islandId: number; name: string; scrapIds: number[] }) =>
      createTopic(islandId, name, scrapIds),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['island', variables.islandId] });
      queryClient.invalidateQueries({ queryKey: ['islands'] });
    },
  });
}
