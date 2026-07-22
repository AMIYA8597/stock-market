// apps/web/src/components/seo/Meta.tsx
import Head from 'next/head';

type MetaProps = {
  title?: string;
  description?: string;
  imageUrl?: string;
};

export const Meta = ({ title = 'NeuroQuant', description = 'Advanced stock market analytics platform', imageUrl }: MetaProps) => {
  const ogTitle = title;
  const ogDescription = description;
  const ogImage = imageUrl || '/og-image.png';

  return (
    <Head>
      <title>{title}</title>
      <meta name="description" content={description} />
      <meta property="og:title" content={ogTitle} />
      <meta property="og:description" content={ogDescription} />
      <meta property="og:image" content={ogImage} />
      <meta property="og:type" content="website" />
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={title} />
      <meta name="twitter:description" content={description} />
      <meta name="twitter:image" content={ogImage} />
    </Head>
  );
};
