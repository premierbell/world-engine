interface LoadingCardProps {
  message?: string;
}

export function LoadingCard({ message = '불러오는 중...' }: LoadingCardProps) {
  return (
    <section className="card">
      <p className="result">{message}</p>
    </section>
  );
}
