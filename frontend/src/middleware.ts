import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(req: NextRequest) {
    const isAuth = req.cookies.get('docustory_auth')
    const url = req.nextUrl

    // Allow access to the login page and the login API route
    if (url.pathname.startsWith('/login') || url.pathname.startsWith('/api/auth')) {
        return NextResponse.next()
    }

    // Require the cookie for all other routes
    if (!isAuth || isAuth.value !== 'authenticated') {
        const loginUrl = new URL('/login', req.url)
        return NextResponse.redirect(loginUrl)
    }

    return NextResponse.next()
}

// Apply to all routes except static Next.js internal files
export const config = {
    matcher: [
        '/((?!_next/static|_next/image|favicon.ico).*)',
    ],
}
