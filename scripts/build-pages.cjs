'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { pages, esc } = require('../frontend/app.js');

const site = 'https://5bmath.vn/';
const frontend = path.resolve(__dirname, '../frontend');
const [destination, target = 'cloudflare'] = process.argv.slice(2);
if (!destination || !['cloudflare', 'github'].includes(target)) {
    throw new Error('Usage: node scripts/build-pages.cjs <empty-output-dir> [cloudflare|github]');
}
const output = path.resolve(destination);
fs.mkdirSync(output, { recursive: true });
if (fs.readdirSync(output).length) throw new Error('The output directory must be empty');

const template = fs.readFileSync(path.join(frontend, 'index.html'), 'utf8');
const sitemap = [];
for (const [id, page] of Object.entries(pages)) {
    const canonical = new URL(page.path, site).href;
    const metadata = [
        '<title>' + esc(page.title) + ' | 5BMath</title>',
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
    const html = template
        .replace('data-grading="server"', 'data-grading="browser" data-page="' + id + '"')
        .replace(/<title>[^<]*<\/title>/, () => metadata.join('\n    '))
        .replace('<main id="app"></main>', () => '<main id="app">' + page.render() + '</main>');
    const folder = path.join(output, page.path);
    fs.mkdirSync(folder, { recursive: true });
    fs.writeFileSync(path.join(folder, 'index.html'), html);
    if (!page.noindex) sitemap.push(canonical);
}

for (const asset of ['app.js', 'styles.css', '5bmath-logo.svg', '5bmath-icon.svg']) {
    fs.copyFileSync(path.join(frontend, asset), path.join(output, asset));
}

const root = target === 'github' ? '/5b/' : '/';
fs.writeFileSync(path.join(output, '404.html'), `<!doctype html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <meta name="robots" content="noindex">
    <title>Không tìm thấy trang | 5BMath</title>
    <link rel="stylesheet" href="${root}styles.css">
</head>
<body>
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

if (target === 'cloudflare') {
    fs.writeFileSync(path.join(output, 'robots.txt'), 'User-agent: *\nAllow: /\nSitemap: ' + site + 'sitemap.xml\n');
    const urls = sitemap.map(url => '  <url><loc>' + url + '</loc></url>').join('\n');
    fs.writeFileSync(path.join(output, 'sitemap.xml'),
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + '\n</urlset>\n');
}

console.log(`Built ${sitemap.length} public pages and a 404 page for ${target} at ${output}`);
