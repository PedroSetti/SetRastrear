export function apiOrigin(value) {
  if (!value) throw new Error('Defina RMB_API_ORIGIN com a origem HTTPS do backend (ex.: https://sua-api.onrender.com).');
  const url = new URL(value);
  if (url.protocol !== 'https:' || !url.hostname || url.username || url.password || url.search || url.hash || !['', '/'].includes(url.pathname)) {
    throw new Error('RMB_API_ORIGIN deve ser uma origem HTTPS, sem caminho, credenciais, query ou fragmento.');
  }
  return url.origin;
}
export function redirects(value) {
  const origin = apiOrigin(value);
  return `/api/*  ${origin}/api/:splat  200!\n/*  /index.html  200\n`;
}
