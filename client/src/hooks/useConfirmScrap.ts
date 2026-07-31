import { useMutation, useQueryClient } from '@tanstack/react-query';
import { confirmScrap } from '../api/scrap';

interface ConfirmScrapArgs {
  scrapId: number;
  islandId?: number;
  newIslandName?: string;
}

export function useConfirmScrap() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ scrapId, islandId, newIslandName }: ConfirmScrapArgs) =>
      confirmScrap(scrapId, islandId, newIslandName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['islands'] });
      queryClient.invalidateQueries({ queryKey: ['scraps'] });
    },
  });
}
