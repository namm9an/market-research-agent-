import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(req: NextRequest) {
    const basicAuth = req.headers.get('authorization')
    const url = req.nextUrl

    // Require basic auth for all routes
    if (basicAuth) {
        const authValue = basicAuth.split(' ')[1]
        const [user, pwd] = atob(authValue).split(':')

        // Using the requested password, any username works
        const validPassword = process.env.BASIC_AUTH_PASSWORD || 'Marketaiagente2e345'

        if (pwd === validPassword) {
            return NextResponse.next()
        }
    }

    url.pathname = '/api/auth'
    return new NextResponse('Auth required', {
        status: 401,
        headers: {
            'WWW-Authenticate': 'Basic realm="Secure Area"',
        },
    })
}

// Apply to all routes except static Next.js internal files
export const config = {
    matcher: [
        '/((?!_next/static|_next/image|favicon.ico).*)',
    ],
}
