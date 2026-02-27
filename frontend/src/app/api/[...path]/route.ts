import { NextRequest, NextResponse } from 'next/server';

const BACKEND = process.env.BACKEND_URL || 'http://127.0.0.1:8080';

async function proxy(req: NextRequest) {
    const { pathname, search } = req.nextUrl;
    const target = `${BACKEND}${pathname}${search}`;

    const headers = new Headers();
    req.headers.forEach((v, k) => {
        if (k !== 'host' && k !== 'connection') headers.set(k, v);
    });

    const init: RequestInit = {
        method: req.method,
        headers,
    };

    if (req.method !== 'GET' && req.method !== 'HEAD') {
        init.body = await req.arrayBuffer();
    }

    const upstream = await fetch(target, init);

    const res = new NextResponse(upstream.body, {
        status: upstream.status,
        statusText: upstream.statusText,
    });

    upstream.headers.forEach((v, k) => {
        if (k !== 'transfer-encoding') res.headers.set(k, v);
    });

    return res;
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const DELETE = proxy;
export const PATCH = proxy;
