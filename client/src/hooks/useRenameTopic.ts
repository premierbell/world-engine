import { useMutation, useQueryClient } from '@tanstack/react-query';
import { renameTopic } from '../api/topic';

export function useRenameTopic(islandId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ topicId, name }: { topicId: number; name: string }) => renameTopic(topicId, name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['island', islandId] });
    },
  });
}
