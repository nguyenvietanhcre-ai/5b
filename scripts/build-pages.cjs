'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { pages, esc } = require('../frontend/app.js');
const { manifest } = require('../frontend/runtime-assets.js');

const site = 'https://5bmath.vn/';
const frontend = path.resolve(__dirname, '../frontend');
const [destination, target = 'cloudflare'] = process.argv.slice(2);
if (!destination || !['cloudflare', 'github', 'python', 'cloudflare-live'].includes(target)) {
    throw new Error('Usage: node scripts/build-pages.cjs <empty-output-dir> [cloudflare|github|python|cloudflare-live]');
}
const output = path.resolve(destination);
fs.mkdirSync(output, { recursive: true });
if (fs.readdirSync(output).length) throw new Error('The output directory must be empty');

const live = ['python', 'cloudflare-live'].includes(target);
const template = fs.readFileSync(path.join(frontend, 'index.html'), 'utf8');
const sitemap = [];
for (const [id, page] of Object.entries(pages)) {
    const canonical = new URL(page.path, site).href;
    const metadata = [
        '<title>' + esc(page.title) + (id==='home'?'':' | 5BMath') + '</title>',
        '<meta name="description" content="' + esc(page.description) + '">',
        page.noindex
            ? '<meta name="robots" content="noindex">'
            : '<link rel="canonical" href="' + canonical + '">'
    ];
    if (id !== 'home') metadata.unshift('<base href="../">');
    if (id === 'home') {
        const siteName = { '@context': 'https://schema.org', '@type': 'WebSite', name: '5BMath', url: site };
        metadata.push('<script type="application/ld+json">' + JSON.stringify(siteName) + '</script>');
    }
    const html = id==='entrance' ? fs.readFileSync(path.join(frontend,'admissions.html'),'utf8').replace('data-backend="database"', 'data-backend="' + (live ? 'database' : 'static') + '"').replace('data-grading="server"', 'data-grading="' + (live ? 'server' : 'browser') + '"') : template
        .replace(/\s*<meta name="description"[^>]*>/, '')
        .replace(/\s*<link rel="canonical"[^>]*>/, '')
        .replace('data-grading="server"', 'data-grading="' + (live ? 'server' : 'browser') + '" data-backend="' + (live ? 'database' : 'static') + '" data-page="' + id + '"')
        .replace(/<title>[^<]*<\/title>/, () => metadata.join('\n    '))
        .replace('<body>', id.startsWith('staff-') ? '<body class="staff-mode">' : page.noindex ? '<body class="learning-mode">' : '<body>')
        .replace('<main id="app"></main>', () => '<main id="app">' +
            page.render() + '</main>');
    const folder = path.join(output, page.path);
    fs.mkdirSync(folder, { recursive: true });
    fs.writeFileSync(path.join(folder, 'index.html'), html.replace(/[ \t]+$/gm, ''));
    if (!page.noindex) sitemap.push(canonical);
}

if (target !== 'python') {
const core = ['app.js', 'nickname-policy.js', 'platform-api.js', 'themes.js', 'themes.css',
    'styles.css', '5bmath-logo.svg', '5bmath-icon.svg', 'demo-rectangle.svg',
    'mascots.webp', 'admissions.js', 'admissions.css'];
for (const asset of new Set([...core, ...manifest.files])) {
    const source = path.resolve(frontend, asset);
    if (!source.startsWith(frontend + path.sep)) throw new Error('Invalid public asset: ' + asset);
    fs.copyFileSync(source, path.join(output, asset));
}
for (const directory of ['arena-art', 'theme-art']) {
    fs.cpSync(path.join(frontend, directory), path.join(output, directory), {recursive: true});
}
}
const root = target === 'github' ? '/5b/' : '/';
fs.writeFileSync(path.join(output, '404.html'), `<!doctype html>
<html lang="vi" data-theme="garden-adventure">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <meta name="robots" content="noindex">
    <title>Không tìm thấy trang | 5BMath</title>
    <script src="${root}themes.js"></script>
    <script src="${root}page-loading.js"></script>
    <link rel="stylesheet" href="${root}styles.css">
    <link rel="stylesheet" href="${root}themes.css">
</head>
<body>
    ${template.match(/<aside class="page-loader"[\s\S]*?<\/aside>/)[0]}
    <main class="wrap">
        <div class="page-head">
            <h1 class="title">Không tìm thấy trang</h1>
            <p>Đường dẫn có thể đã thay đổi. Em có thể quay về trang chủ hoặc chọn một bài Toán lớp 5.</p>
            <div class="actions">
                <a class="btn dark" href="${root}">Về trang chủ</a>
                <a class="btn outline" href="${root}${pages.courses.path}">Xem bài học</a>
            </div>
        </div>
    </main>
</body>
</html>
`);

if (['cloudflare', 'cloudflare-live'].includes(target)) {
    const worker = fs.readFileSync(path.join(__dirname, 'pages-worker.mjs'), 'utf8')
        .replace("'__DEMO_REPORT_SQL__'", JSON.stringify(fs.readFileSync(path.join(frontend, '../backend/demo-report.sql'), 'utf8')));
    fs.writeFileSync(path.join(output, '_worker.js'), worker);
    fs.writeFileSync(path.join(output, '_routes.json'),
        JSON.stringify({ version: 1, include: target === 'cloudflare-live'
            ? ['/api/database-demo', '/api/database-demo/*', '/api/v1/*', '/api/staff/*', '/api/webhooks/sepay', '/api/health', '/api/grade']
            : ['/api/database-demo', '/api/database-demo/*'], exclude: [] }));
}
if (target !== 'github') {
    fs.writeFileSync(path.join(output, 'robots.txt'), 'User-agent: *\nAllow: /\nSitemap: ' + site + 'sitemap.xml\n');
    const urls = sitemap.map(url => '  <url><loc>' + url + '</loc></url>').join('\n');
    fs.writeFileSync(path.join(output, 'sitemap.xml'),
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + '\n</urlset>\n');
}

console.log(`Built ${sitemap.length} public pages and a 404 page for ${target} at ${output}`);
