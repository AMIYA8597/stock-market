"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Calendar, Tag } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { blogApi } from '@/lib/api-client';

const seedPosts = [
  {
    slug: 'ai-macro-regime-playbook',
    title: 'Building an AI Macro Regime Playbook',
    excerpt: 'How we combine signal clustering, factor timing, and portfolio risk overlays for resilient strategies.',
    date: 'Mar 18, 2026',
    tags: ['AI', 'Macro', 'Risk'],
  },
  {
    slug: 'model-drift-in-production',
    title: 'Detecting Model Drift in Production Trading',
    excerpt: 'A practical architecture for low-latency drift detection and policy-based mitigation.',
    date: 'Mar 12, 2026',
    tags: ['MLOps', 'Monitoring'],
  },
  {
    slug: 'feature-store-for-quants',
    title: 'Designing a Feature Store for Quant Teams',
    excerpt: 'A framework for making features reproducible, debuggable, and strategy-safe at scale.',
    date: 'Mar 2, 2026',
    tags: ['Data', 'Research'],
  },
];

export function BlogIndexPage(): JSX.Element {
  const [posts, setPosts] = useState(seedPosts);

  useEffect(() => {
    let mounted = true;
    blogApi.listPosts(20).then((response) => {
      if (!mounted) return;
      setPosts(
        response.items.map((item) => ({
          slug: item.slug,
          title: item.title,
          excerpt: item.excerpt,
          date: item.published_at ? new Date(item.published_at).toLocaleDateString() : 'Draft',
          tags: ['Research'],
        }))
      );
    }).catch(() => {
      if (!mounted) return;
    });
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <section className="mx-auto grid max-w-7xl gap-6 px-4 py-10 sm:px-6 lg:grid-cols-[1.7fr_0.8fr] lg:px-8">
      <div className="space-y-4">
        <h1 className="text-[var(--ds-heading-2)] font-semibold">Research Journal</h1>
        {posts.map((post) => (
          <Card key={post.slug} className="bg-[var(--ds-surface-1)]/90">
            <CardContent className="p-5">
              <Link href={`/blog/${post.slug}`} className="text-lg font-semibold leading-tight transition hover:text-[var(--ds-color-primary-300)]">{post.title}</Link>
              <p className="mt-2 text-sm text-[var(--ds-text-secondary)]">{post.excerpt}</p>
              <div className="mt-3 flex items-center gap-3 text-xs text-[var(--ds-text-muted)]">
                <span className="inline-flex items-center gap-1"><Calendar className="h-3.5 w-3.5" />{post.date}</span>
                <span className="inline-flex items-center gap-1"><Tag className="h-3.5 w-3.5" />{post.tags.join(' · ')}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      <aside className="space-y-4">
        <Card className="bg-[var(--ds-surface-1)]/90">
          <CardContent className="p-5">
            <p className="text-xs uppercase tracking-[0.1em] text-[var(--ds-text-muted)]">Categories</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {['AI Models', 'Risk', 'Signals', 'Portfolio', 'MLOps'].map((tag) => (
                <Badge key={tag} variant="outline">{tag}</Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      </aside>
    </section>
  );
}

export function BlogArticlePage({ slug }: { slug: string }): JSX.Element {
  const [title, setTitle] = useState('Market Intelligence Notes');
  const [content, setContent] = useState('This article explores practical patterns for institutional teams building resilient quant systems.');

  useEffect(() => {
    let mounted = true;
    blogApi.getPost(slug).then((post) => {
      if (!mounted) return;
      setTitle(post.title);
      setContent(post.content);
    }).catch(() => {
      if (!mounted) return;
    });
    return () => {
      mounted = false;
    };
  }, [slug]);

  return (
    <article className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="text-[var(--ds-heading-2)] font-semibold">{title}</h1>
      <p className="mt-4 text-base leading-7 text-[var(--ds-text-secondary)]">
        {content}
      </p>
      <p className="mt-4 text-base leading-7 text-[var(--ds-text-secondary)]">
        At scale, consistency beats novelty. A durable process links data quality, feature reliability, model governance, and execution discipline. This stack is where modern SaaS UX directly compounds research outcomes.
      </p>
    </article>
  );
}
