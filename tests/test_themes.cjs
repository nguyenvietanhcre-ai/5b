'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {test} = require('node:test');

const source = fs.readFileSync(path.join(__dirname,'../frontend/themes.js'),'utf8');
const apiSource = fs.readFileSync(path.join(__dirname,'../frontend/platform-api.js'),'utf8');
const ids = ['morning-garden','crayon-workshop','clay-sprout','garden-adventure','garden-notebook'];
const accountKey = '5bmath-appearance-v1';
const guestKey = '5bmath-guest-theme-v1';
const snapshot = (id,theme='garden-adventure',csrf='session-'+id) => ({
    authenticated:true,account:{id},csrf,state:{theme},
});

function eventTarget(extra={}) {
    const listeners = new Map();
    return Object.assign({
        addEventListener(type,fn) { if(!listeners.has(type))listeners.set(type,new Set());listeners.get(type).add(fn); },
        removeEventListener(type,fn) { listeners.get(type)?.delete(fn); },
        async emit(type,event={}) { await Promise.all([...listeners.get(type)||[]].map(fn=>fn(event))); },
        listenerCount(type) { return listeners.get(type)?.size||0; },
    },extra);
}
function formFixture() {
    const status = {textContent:'',classList:{values:new Set(),add(x){this.values.add(x);},remove(x){this.values.delete(x);}}};
    const controls = {
        '[type="submit"]':{disabled:true},
        '#appearance-cancel':eventTarget({disabled:true}),
        '#appearance-default':eventTarget({disabled:false}),
        '#appearance-status':status,
    };
    const radios = ids.map(value=>({name:'appearance-theme',value,checked:false,disabled:false}));
    return eventTarget({
        isConnected:true,radios,controls,attributes:{},
        querySelector:selector=>controls[selector]||null,
        querySelectorAll:selector=>selector==='[name="appearance-theme"]'?radios:[],
        setAttribute(name,value){this.attributes[name]=value;},
    });
}
function harness({database=false,seed={},blocked=false,fetch:fetchImpl}={}) {
    const store = new Map(Object.entries(seed));
    const writes = [];
    const events = [];
    let currentForm = null;
    const window = eventTarget();
    const document = {
        documentElement:{dataset:{backend:database?'database':'',theme:'garden-adventure'}},
        querySelector:selector=>selector==='#appearance-form'?currentForm:null,
        dispatchEvent:event=>{events.push(event);return true;},
    };
    const context = vm.createContext({
        window,document,console,AbortController,AbortSignal,DOMException,URLSearchParams,setTimeout,clearTimeout,
        CustomEvent:class {constructor(type,options){this.type=type;Object.assign(this,options);}},
        location:{search:'',pathname:'/tai-khoan/'},
        localStorage:{
            getItem(key){if(blocked)throw new Error('storage blocked');return store.get(key)??null;},
            setItem(key,value){if(blocked)throw new Error('storage blocked');writes.push({key,value});store.set(key,value);},
            removeItem(key){if(blocked)throw new Error('storage blocked');writes.push({key,remove:true});store.delete(key);},
        },
        fetch:fetchImpl||(()=>{throw new Error('Unexpected network request');}),
        module:{exports:{}},
    });
    vm.runInContext(source,context,{filename:'themes.js'});
    const manager = vm.runInContext('ThemeManager',context);
    return {
        manager,context,window,document,store,writes,events,
        form(){currentForm=formFixture();manager.mountSettings();return currentForm;},
        api(){vm.runInContext(apiSource,context,{filename:'platform-api.js'});return vm.runInContext('PlatformAPI',context);},
        storage(key,value){if(value===undefined)store.delete(key);else store.set(key,JSON.stringify(value));return window.emit('storage',{key});},
    };
}
function response(payload,ok=true){return {ok,json:async()=>payload};}
function deferred(){let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});return {promise,resolve,reject};}
function submit(form){return form.emit('submit',{preventDefault(){}});}

test('first paint uses04 default, validates cache, and keeps static/offline guest choice separate',()=>{
    const empty = harness();
    assert.equal(empty.manager.theme,'garden-adventure');
    assert.equal(empty.document.documentElement.dataset.theme,'garden-adventure');
    assert.equal(empty.writes.length,0);
    for(const bad of [null,123,{},'../custom.css','unknown']) {
        const h = harness({seed:{[guestKey]:JSON.stringify(bad),[accountKey]:'{bad json'}});
        assert.equal(h.manager.theme,'garden-adventure');
    }
    const cached = harness({database:true,seed:{[accountKey]:JSON.stringify({owner:'17',theme:'clay-sprout'})}});
    assert.equal(cached.manager.owner,'17');
    assert.equal(cached.manager.theme,'clay-sprout');
    const offline = harness({seed:{[accountKey]:JSON.stringify({owner:'17',theme:'clay-sprout'}),[guestKey]:JSON.stringify('morning-garden')}});
    assert.equal(offline.manager.owner,null);
    assert.equal(offline.manager.theme,'morning-garden');
    for(const owner of [17,'abc',null,{},'<script>']) {
        assert.equal(harness({database:true,seed:{[accountKey]:JSON.stringify({owner,theme:'clay-sprout'})}}).manager.theme,'garden-adventure');
    }
});

test('preview changes DOM without persistence, cancel and route unmount restore saved choice',async()=>{
    const h = harness();
    const form = h.form();
    const startWrites = h.writes.length;
    await form.emit('change',{target:{name:'appearance-theme',value:'crayon-workshop'}});
    assert.equal(h.manager.theme,'crayon-workshop');
    assert.equal(h.manager.savedTheme,'garden-adventure');
    assert.equal(form.controls['[type="submit"]'].disabled,false);
    assert.equal(h.writes.length,startWrites);
    h.manager.preview('../bad.css');
    assert.equal(h.manager.theme,'crayon-workshop');
    await form.controls['#appearance-cancel'].emit('click');
    assert.equal(h.manager.theme,'garden-adventure');
    assert.equal(form.controls['[type="submit"]'].disabled,true);
    h.manager.preview('clay-sprout');
    h.manager.unmountSettings();
    assert.equal(h.manager.theme,'garden-adventure');
    assert.equal(form.listenerCount('change'),0);
    assert.equal(form.listenerCount('submit'),0);
    assert.equal(h.writes.length,startWrites);
});

test('guest Apply persists once and default button previews until Apply',async()=>{
    const h = harness();
    const form = h.form();
    h.manager.preview('garden-notebook');
    await submit(form);
    assert.equal(JSON.parse(h.store.get(guestKey)),'garden-notebook');
    assert.equal(h.manager.savedTheme,'garden-notebook');
    assert.match(form.controls['#appearance-status'].textContent,/Đã lưu/);
    const writes = h.writes.length;
    await form.controls['#appearance-default'].emit('click');
    assert.equal(h.manager.theme,'garden-adventure');
    assert.equal(h.manager.savedTheme,'garden-notebook');
    assert.equal(h.writes.length,writes);
    h.manager.cancelPreview();
    assert.equal(h.manager.theme,'garden-notebook');
});

test('same-owner snapshots and storage sync saved choice while retaining dirty preview',async()=>{
    const h = harness({database:true});
    h.manager.sync(snapshot(7,'morning-garden'));
    const form = h.form();
    h.manager.preview('clay-sprout');
    h.manager.sync(snapshot(7,'crayon-workshop'));
    assert.equal(h.manager.savedTheme,'crayon-workshop');
    assert.equal(h.manager.theme,'clay-sprout');
    assert.equal(form.controls['[type="submit"]'].disabled,false);
    await h.storage(accountKey,{owner:'7',theme:'garden-notebook'});
    assert.equal(h.manager.savedTheme,'garden-notebook');
    assert.equal(h.manager.theme,'clay-sprout');
    h.manager.cancelPreview();
    assert.equal(h.manager.theme,'garden-notebook');
    h.manager.sync(snapshot(7,'morning-garden'));
    assert.equal(h.manager.theme,'morning-garden');
    await h.storage(accountKey,{owner:'8',theme:'clay-sprout'});
    assert.equal(h.manager.theme,'morning-garden');
    assert.equal(h.manager.owner,'7');
});

test('account change removes draft and logout restores isolated guest style and clears account cache',()=>{
    const h = harness({database:true,seed:{[guestKey]:JSON.stringify('morning-garden')}});
    h.manager.sync(snapshot(3,'crayon-workshop'));
    const form = h.form();
    h.manager.preview('clay-sprout');
    h.manager.sync(snapshot(4,'garden-notebook'));
    assert.equal(h.manager.owner,'4');
    assert.equal(h.manager.theme,'garden-notebook');
    assert.equal(form.listenerCount('submit'),0);
    assert.deepEqual(JSON.parse(h.store.get(accountKey)),{owner:'4',theme:'garden-notebook'});
    h.manager.sync({authenticated:false});
    assert.equal(h.manager.owner,null);
    assert.equal(h.manager.theme,'morning-garden');
    assert.equal(h.store.has(accountKey),false);
});

test('guest storage event updates clean selection but preserves dirty preview',async()=>{
    const h = harness();
    h.form();
    await h.storage(guestKey,'morning-garden');
    assert.equal(h.manager.theme,'morning-garden');
    h.manager.preview('clay-sprout');
    await h.storage(guestKey,'garden-notebook');
    assert.equal(h.manager.theme,'clay-sprout');
    assert.equal(h.manager.savedTheme,'garden-notebook');
    h.manager.cancelPreview();
    assert.equal(h.manager.theme,'garden-notebook');
});

test('blocked localStorage starts safely; failed guest save stays unsaved and can cancel',async()=>{
    const h = harness({blocked:true});
    const form = h.form();
    h.manager.preview('garden-notebook');
    await submit(form);
    assert.equal(h.manager.theme,'garden-notebook');
    assert.equal(h.manager.savedTheme,'garden-adventure');
    assert.equal(form.controls['[type="submit"]'].disabled,false);
    assert.ok(form.controls['#appearance-status'].classList.values.has('is-error'));
    assert.match(form.controls['#appearance-status'].textContent,/Chưa lưu/);
    h.manager.cancelPreview();
    assert.equal(h.manager.theme,'garden-adventure');
});

test('API authenticated Apply saves snapshot, sends CSRF and unlocks settings',async()=>{
    const calls = [];
    const h = harness({database:true,fetch:async(url,request)=>{
        calls.push({url,request});
        return response(snapshot(12,url.endsWith('/preferences')?'clay-sprout':'morning-garden'));
    }});
    const api = h.api();
    await api.request('session');
    const form = h.form();
    h.manager.preview('clay-sprout');
    await submit(form);
    assert.equal(calls[1].url,'/api/v1/preferences');
    assert.equal(calls[1].request.headers['X-CSRF-Token'],'session-12');
    assert.deepEqual(JSON.parse(calls[1].request.body),{theme:'clay-sprout'});
    assert.equal(h.manager.theme,'clay-sprout');
    assert.equal(h.manager.savedTheme,'clay-sprout');
    assert.equal(api.snapshot.state.theme,'clay-sprout');
    assert.equal(form.attributes['aria-busy'],'false');
    assert.equal(form.controls['[type="submit"]'].disabled,true);
});

test('account server save succeeds even when local cache is blocked',async()=>{
    const h = harness({database:true,blocked:true,fetch:async(url)=>response(snapshot(12,url.endsWith('/preferences')?'clay-sprout':'morning-garden'))});
    const api = h.api();
    await api.request('session');
    const form = h.form();
    h.manager.preview('clay-sprout');
    await submit(form);
    assert.equal(h.manager.savedTheme,'clay-sprout');
    assert.match(form.controls['#appearance-status'].textContent,/Đã lưu/);
});

test('late preference response cannot replace another account or a new session of same account',async()=>{
    for(const next of [snapshot(22,'garden-notebook'),snapshot(11,'garden-notebook','new-session-11')]) {
        const pending = deferred();
        let reads=0,saveSignal;
        const h = harness({database:true,fetch:async(url,request)=>{
            if(url.endsWith('/preferences')){saveSignal=request.signal;return pending.promise;}
            return response(reads++===0?snapshot(11,'morning-garden'):next);
        }});
        const api = h.api();
        await api.request('session');
        const form = h.form();
        h.manager.preview('clay-sprout');
        const saving = submit(form);
        assert.equal(form.attributes['aria-busy'],'true');
        await api.request('session');
        pending.resolve(response(snapshot(11,'clay-sprout')));
        await saving;
        assert.equal(api.snapshot.account.id,next.account.id);
        assert.equal(api.snapshot.csrf,next.csrf);
        assert.equal(h.manager.savedTheme,'garden-notebook');
        if(next.account.id===22) {
            assert.equal(saveSignal.aborted,true);
            assert.equal(h.manager.theme,'garden-notebook');
        } else {
            assert.equal(h.manager.theme,'clay-sprout');
            h.manager.cancelPreview();
            assert.equal(h.manager.theme,'garden-notebook');
        }
    }
});

test('logout during pending Apply prevents stale save from restoring account cache',async()=>{
    const pending = deferred();
    const h = harness({database:true,seed:{[guestKey]:JSON.stringify('crayon-workshop')},fetch:async(url)=>{
        if(url.endsWith('/preferences'))return pending.promise;
        return response(url.endsWith('/logout')?{authenticated:false}:snapshot(11,'morning-garden'));
    }});
    const api = h.api();
    await api.request('session');
    const form = h.form();
    h.manager.preview('clay-sprout');
    const saving = submit(form);
    await api.logout();
    pending.resolve(response(snapshot(11,'clay-sprout')));
    await saving;
    assert.equal(api.snapshot.authenticated,false);
    assert.equal(h.manager.owner,null);
    assert.equal(h.manager.theme,'crayon-workshop');
    assert.equal(h.store.has(accountKey),false);
});

test('generic session GET started before login cannot replace the newly authenticated account',async()=>{
    const pending = deferred();
    const h = harness({database:true,fetch:async(url)=>{
        if(url.endsWith('/auth/login'))return response(snapshot(22,'garden-notebook'));
        return pending.promise;
    }});
    const api = h.api();
    const reading = api.request('session');
    await api.authenticate('login',{login:'fixture-new-account',password:'synthetic-fixture'});
    assert.equal(api.snapshot.account.id,22);
    pending.resolve(response(snapshot(11,'morning-garden')));
    await assert.rejects(reading,error=>error.name==='AbortError');
    assert.equal(api.snapshot.account.id,22);
    assert.equal(h.manager.owner,'22');
    assert.equal(h.manager.theme,'garden-notebook');
    assert.deepEqual(JSON.parse(h.store.get(accountKey)),{owner:'22',theme:'garden-notebook'});
});

test('generic session GET started before logout cannot restore old authentication or cache',async()=>{
    const pending = deferred();
    let reads=0;
    const h = harness({database:true,seed:{[guestKey]:JSON.stringify('crayon-workshop')},fetch:async(url)=>{
        if(url.endsWith('/auth/logout'))return response({authenticated:false});
        if(reads++===0)return response(snapshot(11,'morning-garden'));
        return pending.promise;
    }});
    const api = h.api();
    await api.request('session');
    const reading = api.request('session');
    await api.logout();
    pending.resolve(response(snapshot(11,'morning-garden')));
    await assert.rejects(reading,error=>error.name==='AbortError');
    assert.equal(api.snapshot.authenticated,false);
    assert.equal(h.manager.owner,null);
    assert.equal(h.manager.theme,'crayon-workshop');
    assert.equal(h.store.has(accountKey),false);
});
