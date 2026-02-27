import { redirect } from 'next/navigation';
import { cookies } from 'next/headers';

export default async function LoginPage({
    searchParams,
}: {
    searchParams: Promise<{ error?: string }>;
}) {
    const cookieStore = await cookies();
    const isAuth = cookieStore.get('docustory_auth');

    // If they already have the cookie, redirect away
    if (isAuth?.value === 'authenticated') {
        redirect('/');
    }

    const awaitedSearchParams = await searchParams;
    const error = awaitedSearchParams?.error;

    return (
        <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4">
            <div className="w-full max-w-sm rounded-2xl border border-white/10 bg-black/40 p-8 shadow-2xl backdrop-blur-xl">
                <div className="mb-8 text-center">
                    <h1 className="text-2xl font-bold tracking-tight text-white">
                        Access Restricted
                    </h1>
                    <p className="mt-2 text-sm text-foreground/60">
                        Please enter the access password to continue.
                    </p>
                </div>

                <form action="/api/auth/login" method="POST" className="space-y-6">
                    <div>
                        <input
                            type="password"
                            name="password"
                            required
                            placeholder="Enter Password"
                            autoComplete="current-password"
                            className="w-full rounded-xl border border-white/20 bg-black/20 px-4 py-3 text-white placeholder-white/40 shadow-inner focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                        />
                    </div>

                    {error && (
                        <p className="text-center text-sm text-red-500">
                            Incorrect password. Please try again.
                        </p>
                    )}

                    <button
                        type="submit"
                        className="w-full rounded-xl bg-primary px-4 py-3 font-semibold text-primary-foreground shadow-lg transition-all hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-black"
                    >
                        Unlock Access
                    </button>
                </form>
            </div>
        </div>
    );
}
