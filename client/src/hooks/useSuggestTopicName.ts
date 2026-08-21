import { useMutation } from '@tanstack/react-query';
import { suggestTopicName } from '../api/topic';

// "AI는 제안만, 확정은 사용자가" - 이 훅은 아무것도 저장하지 않는다.
// 제안받은 이름은 Topic 이름 입력창에 채워질 뿐, 그대로 눌러도
// 기존 "선택한 스크랩으로 Topic 생성" 버튼을 따로 눌러야 실제로
// 만들어진다.
export function useSuggestTopicName() {
  return useMutation({
    mutationFn: (scrapIds: number[]) => suggestTopicName(scrapIds),
  });
}
