import { Link } from 'react-router-dom';

export function BackLink() {
  return (
    <Link to="/" className="back-link">
      ← 목록으로
    </Link>
  );
}
