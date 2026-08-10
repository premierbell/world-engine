import { useMutation, useQueryClient } from '@tanstack/react-query';
import { renameIsland } from '../api/island';

export function useRenameIsland() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ islandId, name }: { islandId: number; name: string }) => renameIsland(islandId, name),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['island', variables.islandId] });
      queryClient.invalidateQueries({ queryKey: ['islands'] });
    },
  });
}
