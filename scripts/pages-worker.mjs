const demoPath = '/api/database-demo';
const samplePath = '/api/database-demo/samples';
const sampleQuery = '__DEMO_REPORT_SQL__';
const headers = { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' };

export default {
    async fetch(request, env) {
        const pathname = new URL(request.url).pathname;
        if (pathname.startsWith('/api/v1/') || pathname.startsWith('/api/staff/') ||
            pathname === '/api/webhooks/sepay' || pathname === '/api/health' || pathname === '/api/grade') {
            if (!env.BACKEND) return Response.json({error:'Backend chưa được kết nối.'}, {status:503,headers});
            try { return await env.BACKEND.fetch(request); }
            catch { return Response.json({error:'Máy chủ đang bận. Em hãy thử lại.'}, {status:503,headers}); }
        }
        if (pathname !== demoPath && pathname !== samplePath) {
            if (pathname.startsWith('/api/database-demo/')) {
                return Response.json({ status: 'not_found' }, { status: 404, headers });
            }
            return env.ASSETS.fetch(request);
        }
        if (request.method !== 'GET' && request.method !== 'HEAD') {
            return new Response(null, { status: 405, headers: { ...headers, Allow: 'GET, HEAD' } });
        }

        let status = 200;
        let payload;
        try {
            if (pathname === samplePath) {
                const report = await env.DB.prepare(sampleQuery).first('report');
                payload = JSON.parse(report);
            } else {
                const count = await env.DB.prepare(
                    "SELECT COUNT(*) AS published_exams FROM exams WHERE status = 'published'"
                ).first('published_exams');
                payload = { status: 'ok', published_exams: count };
            }
        } catch {
            status = 503;
            payload = { status: 'unavailable' };
        }
        if (request.method === 'HEAD') {
            return new Response(null, { status, headers: { ...headers, 'Content-Type': 'application/json' } });
        }
        return Response.json(payload, { status, headers });
    }
};
