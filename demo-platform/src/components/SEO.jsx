import { Helmet } from 'react-helmet-async';

const DEFAULTS = {
  siteName: 'AgentNexLiFy',
  siteUrl: 'https://agentnexlify.com',
  image: 'https://agentnexlify.com/og-image.png',
};

export default function SEO({ title, description, canonical, image }) {
  const ogImage = image || DEFAULTS.image;
  const fullCanonical = canonical
    ? (canonical.startsWith('http') ? canonical : `${DEFAULTS.siteUrl}${canonical}`)
    : undefined;

  return (
    <Helmet>
      <title>{title}</title>
      <meta name="description" content={description} />
      {fullCanonical && <link rel="canonical" href={fullCanonical} />}
      <meta property="og:title" content={title} />
      <meta property="og:description" content={description} />
      <meta property="og:image" content={ogImage} />
      {fullCanonical && <meta property="og:url" content={fullCanonical} />}
      <meta property="og:type" content="website" />
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={title} />
      <meta name="twitter:description" content={description} />
      <meta name="twitter:image" content={ogImage} />
    </Helmet>
  );
}
