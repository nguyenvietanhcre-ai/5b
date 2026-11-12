#!/usr/bin/env node
'use strict';
/*
 * Read-only production release gate; this script never deploys.
 *
 * Usage: node scripts/verify-release.cjs --sha <full40-character-commit-SHA>
 *
 * Requires Git, Node18+ with fetch, a clean runtime checkout, and public
 * GitHub API access. The SHA must equal local HEAD and origin/main and have
 * a completed successful pages.yml run (including checks/build/deploy).
 * Pending CI, skipped/failed jobs, missing evidence and network errors fail
 * closed. Public API only; no token is read. Output is one SUCCESS/FAILURE line.
 *
 * API contracts:
 * https://docs.github.com/en/rest/actions/workflow-runs
 * https://docs.github.com/en/rest/actions/workflow-jobs
 */
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const root = path.resolve(__dirname,'..');
const repository = 'nguyenvietanhcre-ai/5b';
const workflow = 'pages.yml';
const runtimePaths = [
    'backend/','frontend/','cloudflare/','scripts/','tests/','.github/',
    ':(glob)package*','Dockerfile','.dockerignore',
    ':(glob)compose*.y*ml',':(glob)wrangler*',
];

function fail(message) { throw new Error(message); }
function git(args) {
    const result = spawnSync('git',args,{
        cwd:root,encoding:'utf8',windowsHide:true,timeout:30000,maxBuffer:4 * 1024 * 1024,
        env:{...process.env,GIT_TERMINAL_PROMPT:'0',GCM_INTERACTIVE:'never'},
    });
    if(result.error || result.status !== 0)fail('Git verification unavailable.');
    return result.stdout.trim();
}
function verifyLocal(sha) {
    if(git(['rev-parse','--verify','HEAD']) !== sha)fail('Local HEAD does not match --sha.');
    const origin = git(['remote','get-url','origin']);
    if(![
        'https://github.com/' + repository + '.git',
        'https://github.com/' + repository,
        'git@github.com:' + repository + '.git',
        'git@github.com:' + repository,
        'ssh://git@github.com/' + repository + '.git',
        'ssh://git@github.com/' + repository,
    ].includes(origin))fail('Origin is not the approved repository.');
    if(git(['status','--porcelain=v1','-z','--untracked-files=all','--',...runtimePaths])) {
        fail('Runtime checkout contains staged, unstaged or untracked changes.');
    }
}
function verifyRemote(sha) {
    const ref = git(['ls-remote','--exit-code','origin','refs/heads/main']);
    if(ref !== sha + '\trefs/heads/main')fail('origin/main does not match --sha.');
}
async function api(route) {
    let response;
    try {
        response = await fetch('https://api.github.com/repos/' + repository + route,{
            headers:{
                Accept:'application/vnd.github+json',
                'User-Agent':'5bmath-release-gate',
                'X-GitHub-Api-Version':'2026-03-10',
            },
            redirect:'error',signal:AbortSignal.timeout(15000),
        });
    } catch { fail('Public GitHub API verification unavailable.'); }
    if(!response.ok)fail('Public GitHub API returned HTTP' + response.status + '.');
    try {return await response.json();}
    catch {fail('Public GitHub API returned invalid evidence.');}
}
async function latestRun(sha) {
    const result = await api('/actions/workflows/' + workflow + '/runs?' + new URLSearchParams({
        head_sha:sha,branch:'main',per_page:'100',exclude_pull_requests:'true',
    }));
    if(!Array.isArray(result.workflow_runs))fail('GitHub workflow evidence is missing.');
    const runs = result.workflow_runs.filter(run => run.head_sha === sha && run.head_branch === 'main' &&
        run.repository?.full_name?.toLowerCase() === repository.toLowerCase() &&
        run.path === '.github/workflows/' + workflow);
    runs.sort((a,b) => Number(b.run_number) - Number(a.run_number) || Number(b.id) - Number(a.id));
    const run = runs[0];
    if(!run || !Number.isSafeInteger(run.id) || !Number.isInteger(run.run_attempt)) {
        fail('No Pages workflow run exists for the exact SHA.');
    }
    if(run.status !== 'completed' || run.conclusion !== 'success') {
        fail('The latest Pages workflow for the SHA has not completed successfully.');
    }
    return run;
}
async function verifyJobs(run,sha) {
    const jobs = [];
    for(let page=1;;page++) {
        const result = await api('/actions/runs/' + run.id + '/attempts/' + run.run_attempt + '/jobs?' +
            new URLSearchParams({per_page:'100',page:String(page)}));
        if(!Array.isArray(result.jobs) || !Number.isInteger(result.total_count))fail('GitHub job evidence is missing.');
        jobs.push(...result.jobs);
        if(jobs.length >= result.total_count)break;
        if(!result.jobs.length || page >= 20)fail('GitHub job evidence is incomplete.');
    }
    if(!jobs.length || jobs.some(job => job.head_sha !== sha || job.status !== 'completed' || job.conclusion !== 'success')) {
        fail('Every job in the exact Pages workflow attempt must succeed.');
    }
    if(!jobs.some(job => job.name === 'build') || !jobs.some(job => job.name === 'deploy') ||
        !jobs.some(job => /^checks\s*\//.test(job.name))) {
        fail('Successful checks, build and deploy jobs are required.');
    }
}

(async () => {
    const args = process.argv.slice(2);
    if(args.length === 1 && ['--help','-h'].includes(args[0])) {
        console.log('Usage: node scripts/verify-release.cjs --sha <full40-character-commit-SHA>\nRead-only: verifies local HEAD, clean runtime, origin/main and successful Pages checks/build/deploy for the exact SHA. Network or pending CI fails closed. No deployment.');
        return;
    }
    const value = args.length === 2 && args[0] === '--sha' ? args[1] :
        args.length === 1 && args[0].startsWith('--sha=') ? args[0].slice(6) : '';
    if(!/^[a-fA-F0-9]{40}$/.test(value))fail('A full40-character --sha is required; use --help.');
    const sha = value.toLowerCase();
    verifyLocal(sha);
    verifyRemote(sha);
    const run = await latestRun(sha);
    await verifyJobs(run,sha);
    // Detect a rerun/new attempt, local edits, or a new main commit during verification.
    const final = await latestRun(sha);
    if(final.id !== run.id || final.run_attempt !== run.run_attempt)fail('Workflow evidence changed during verification.');
    verifyLocal(sha);
    verifyRemote(sha);
    console.log('SUCCESS');
})().catch(error => {
    console.error('FAILURE: ' + error.message);
    process.exitCode = 1;
});
