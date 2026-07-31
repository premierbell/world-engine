import { BackLink } from '../components/BackLink';
import { ErrorCard } from '../components/ErrorCard';

export function NotFoundPage() {
  return (
    <div className="layout">
      <BackLink />
      <ErrorCard message="페이지를 찾을 수 없어요." />
    </div>
  );
}
