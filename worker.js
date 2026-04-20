const BTN_BASE = 'https://www.behindthename.com/name/';
const NAME_DEF_PATH = '/api/name-def';
const BLOCKED_PATHS = new Set([
  '/worker.js',
  '/wrangler.toml',
]);

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (request.method === 'OPTIONS' && url.pathname === NAME_DEF_PATH) {
      return new Response(null, {
        headers: {
          'Allow': 'GET, OPTIONS',
        },
      });
    }

    if (url.pathname === NAME_DEF_PATH) {
      return handleNameDef(request, ctx);
    }

    if (BLOCKED_PATHS.has(url.pathname)) {
      return new Response('Not found', { status: 404 });
    }

    return env.ASSETS.fetch(request);
  },
};

async function handleNameDef(request, ctx) {
  const url = new URL(request.url);
  const rawName = (url.searchParams.get('name') || '').trim();
  const slug = slugifyName(rawName);

  if (!slug) {
    return json({ error: 'Missing name' }, 400);
  }

  const cache = caches.default;
  const cacheKey = new Request(url.toString(), { method: 'GET' });
  const cached = await cache.match(cacheKey);
  if (cached) return cached;

  try {
    let pageHtml = await fetchBTNPage(slug);
    let text = extractDef(pageHtml);

    if (!text && pageHtml.includes(`/name/${slug}-1`)) {
      pageHtml = await fetchBTNPage(`${slug}-1`);
      text = extractDef(pageHtml);
    }

    if (!text) {
      return json({ text: null }, 404, {
        'Cache-Control': 'public, max-age=3600',
      });
    }

    const response = json(
      { text },
      200,
      { 'Cache-Control': 'public, max-age=86400, s-maxage=86400' },
    );
    ctx.waitUntil(cache.put(cacheKey, response.clone()));
    return response;
  } catch (error) {
    return json(
      { error: 'Lookup failed', detail: String(error && error.message ? error.message : error) },
      502,
      { 'Cache-Control': 'no-store' },
    );
  }
}

async function fetchBTNPage(slug) {
  const response = await fetch(BTN_BASE + encodeURIComponent(slug), {
    headers: {
      'Accept': 'text/html,application/xhtml+xml',
      'User-Agent': 'baby-namer-worker/1.0 (+https://names.wtadler.com)',
    },
    cf: {
      cacheTtl: 86400,
      cacheEverything: true,
    },
  });

  if (!response.ok) {
    throw new Error(`Behind the Name responded with ${response.status}`);
  }

  return response.text();
}

function extractDef(html) {
  const match = html.match(/<div[^>]*class="[^"]*\bnamedef\b[^"]*"[^>]*>([\s\S]*?)<\/div>/i);
  if (!match) return null;

  let text = match[1];
  text = text.replace(/<div[^>]*id="expanded_links"[\s\S]*?<\/div>/gi, '');
  text = text.replace(/<p[^>]*>/gi, '\n\n');
  text = text.replace(/<br\s*\/?>/gi, '\n');
  text = text.replace(/<\/?(a|i|b|span|em|strong)[^>]*>/gi, '');
  text = text.replace(/<[^>]+>/g, ' ');
  text = decodeEntities(text);
  text = text.replace(/[ \t]+\n/g, '\n');
  text = text.replace(/\n[ \t]+/g, '\n');
  text = text.replace(/[ \t]{2,}/g, ' ');
  text = text.replace(/\n{3,}/g, '\n\n');
  text = text.trim();

  return text || null;
}

function decodeEntities(text) {
  return text
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&quot;/gi, '"')
    .replace(/&#39;|&apos;/gi, "'")
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>');
}

function slugifyName(name) {
  return name
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function json(payload, status, extraHeaders = {}) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      ...extraHeaders,
    },
  });
}
