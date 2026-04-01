/**
 * Reusable JSON-LD structured data component.
 * Renders <script type="application/ld+json"> tags in the document head.
 *
 * Usage:
 *   <SchemaOrg schemas={[organizationSchema, softwareAppSchema]} />
 */

import { useEffect, useRef } from 'react';

const ORGANIZATION_SCHEMA = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: 'AgentNexLiFy',
  url: 'https://agentnexlify.com',
  logo: 'https://agentnexlify.com/logo.png',
  description: 'AI-powered customer service platform for local businesses',
  address: {
    '@type': 'PostalAddress',
    addressLocality: 'Clemson',
    addressRegion: 'SC',
    addressCountry: 'US',
  },
  contactPoint: {
    '@type': 'ContactPoint',
    contactType: 'sales',
    url: 'https://agentnexlify.com/contact',
  },
};

const SOFTWARE_APP_SCHEMA = {
  '@context': 'https://schema.org',
  '@type': 'SoftwareApplication',
  name: 'AgentNexLiFy',
  applicationCategory: 'BusinessApplication',
  operatingSystem: 'Web',
  description: 'AI-powered customer service chatbot for local businesses',
  url: 'https://agentnexlify.com',
  offers: [
    { '@type': 'Offer', name: 'Free', price: '0', priceCurrency: 'USD' },
    { '@type': 'Offer', name: 'Foundation', price: '99', priceCurrency: 'USD' },
    { '@type': 'Offer', name: 'Growth', price: '249', priceCurrency: 'USD' },
    { '@type': 'Offer', name: 'Operations', price: '499', priceCurrency: 'USD' },
  ],
};

export { ORGANIZATION_SCHEMA, SOFTWARE_APP_SCHEMA };

export default function SchemaOrg({ schemas }) {
  const scriptRefs = useRef([]);

  useEffect(() => {
    // Inject script tags into <head>
    const elements = schemas.map((schema) => {
      const script = document.createElement('script');
      script.type = 'application/ld+json';
      script.textContent = JSON.stringify(schema);
      document.head.appendChild(script);
      return script;
    });
    scriptRefs.current = elements;

    return () => {
      // Clean up on unmount
      elements.forEach((el) => {
        if (el.parentNode) el.parentNode.removeChild(el);
      });
    };
  }, [schemas]);

  return null;
}
