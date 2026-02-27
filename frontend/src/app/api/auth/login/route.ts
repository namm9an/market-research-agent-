import { NextResponse } from 'next/server';

export async function POST(request: Request) {
    const formData = await request.formData();
    const password = formData.get('password');

    const validPassword = process.env.BASIC_AUTH_PASSWORD || 'Marketaiagente2e345';

    if (password === validPassword) {
        const response = NextResponse.redirect(new URL('/', request.url));
        response.cookies.set('docustory_auth', 'authenticated', {
            httpOnly: true,
            secure: process.env.NODE_ENV === 'production',
            sameSite: 'lax',
            maxAge: 60 * 60 * 24, // 24 hours
            path: '/',
        });
        return response;
    }

    // Redirect back to login with error
    return NextResponse.redirect(new URL('/login?error=1', request.url));
}
