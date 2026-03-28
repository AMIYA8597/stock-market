import { PublicLayout } from '@/layouts/PublicLayout';
import { BlogArticlePage } from '@/modules/blog/BlogPages';

export default function BlogArticleRoutePage({ params }: { params: { slug: string } }): JSX.Element {
  return (
    <PublicLayout>
      <BlogArticlePage slug={params.slug} />
    </PublicLayout>
  );
}
