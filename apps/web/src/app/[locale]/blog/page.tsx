import { PublicLayout } from '@/layouts/PublicLayout';
import { BlogIndexPage } from '@/modules/blog/BlogPages';

export default function BlogRoutePage(): JSX.Element {
  return (
    <PublicLayout>
      <BlogIndexPage />
    </PublicLayout>
  );
}
