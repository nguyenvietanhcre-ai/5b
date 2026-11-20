const demoPath = '/api/database-demo';
const samplePath = '/api/database-demo/samples';
const sampleQuery = '__DEMO_REPORT_SQL__';
const headers = { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' };
const liveBackend = false; // BUILD_LIVE_BACKEND
const maintenanceUnavailable=()=>new Response('<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>Hệ thống đang được cập nhật | 5BMath</title><body style="margin:0;padding:24px;background:#FFF9ED;color:#203A32;font:18px/1.6 Arial;text-align:center"><main style="max-width:640px;margin:15vh auto"><p>5BMath · Gieo Mầm Toán</p><h1>Hệ thống đang được cập nhật</h1><p>Vui lòng quay lại sau.</p></main></body></html>',{status:503,headers:{...headers,'Content-Type':'text/html; charset=utf-8','Retry-After':'300','X-Robots-Tag':'noindex','X-5BMath-Maintenance':'1'}});

export default {
    async fetch(request, env) {
        const pathname = new URL(request.url).pathname;
        if(liveBackend){
            if(!env.BACKEND)return maintenanceUnavailable();
            const recovery=pathname==='/quan-tri/bao-tri/'||pathname==='/quan-tri/bao-tri'||['/api/staff/site-visibility','/api/staff/site-visibility/login','/api/staff/site-visibility/session','/api/staff/site-visibility/logout'].includes(pathname);
            if(recovery){try{return await env.BACKEND.fetch(request);}catch{return maintenanceUnavailable();}}
            const operational=(pathname==='/api/health'&&['GET','HEAD'].includes(request.method))||(pathname==='/api/webhooks/sepay'&&request.method==='POST');
            if(!operational){
                try{
                    const target=new URL(request.url);target.pathname='/api/site-visibility/check';target.search='';
                    const status=await env.BACKEND.fetch(new Request(target,{method:'GET'}));
                    if(status.status!==204){const blocked=status.headers.get('X-5BMath-Maintenance')==='1'?status:maintenanceUnavailable();return request.method==='HEAD'?new Response(null,blocked):blocked;}
                }catch{return maintenanceUnavailable();}
            }
        }
        if(pathname==='/api/site-visibility/check')return env.BACKEND.fetch(request);
        if (pathname.startsWith('/api/v1/') || pathname.startsWith('/api/staff/') || pathname.startsWith('/api/local-pilot/') || pathname.startsWith('/api/family/') || pathname.startsWith('/api/trial/') || pathname.startsWith('/api/website/') ||
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
