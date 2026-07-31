import { useMutation, useQueryClient } from '@tanstack/react-query';
import { addScrapsToTopic } from '../api/topic';

export function useAddScrapsToTopic(islandId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ topicId, scrapIds }: { topicId: number; scrapIds: number[] }) =>
      addScrapsToTopic(topicId, scrapIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['island', islandId] });
    },
  });
}
